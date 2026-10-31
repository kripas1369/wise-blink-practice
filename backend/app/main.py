"""The data API and the website, from one server.

    uvicorn backend.app.main:app --port 8000        # then open http://localhost:8000

Endpoints (docs/plan/FACTS.md, section 7). Every error is {"error": "<plain message>"} with a
non-200 status; nothing is ever filled in with a default value.
    /api/health
    /api/resolve?name=                         SIMBAD position and proper motion
    /api/coverage?ra=&dec=[&band=]             SPHEREx images whose footprint contains the point
    /api/frames?target=&band=                  manifest of the prepared frames (5 official targets)
    /api/frames?ra=&dec=&band=[&fov_arcmin=]   any position: starts a background job (HTTP 202 and
                                               {"status": "working", "message"} meanwhile), then the same manifest
    /api/gaia, /api/diff                       the same location parameters; Gaia markers and difference maps
    /api/lightcurve[&x=&y=]                    the target's light curve, or one measured at a clicked pixel
"""
import json
import math
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app import archive
from backend.app.config import CACHE_DIR, DETECTORS, REPO_ROOT
from backend.app.diff import write_diff
from backend.app.gaia import write_gaia
from backend.app.lightcurve import lightcurve_at, write_lightcurve
from backend.app.motion import position_at, separation_arcsec
from backend.app.render import POSITION_YEAR, NoImages, render_frames
from backend.app.resolve import ResolverUnavailable, resolve_name
from backend.app.targets import OFFICIAL_TARGETS

FRONTEND_DIR = REPO_ROOT / "frontend"
PREPARED_DIR = FRONTEND_DIR / "frames"
JOBS_DIR = CACHE_DIR / "frames"
PREPARED_FOV = 3.0
SAME_TARGET_ARCSEC = 5.0
JOB_EXPOSURES_PER_VISIT = 4   # fewer than the prepared frames (8): each cutout is ~5 MB
COVERAGE_CACHE_SECONDS = 3600
FAILED_JOB_RETRY_SECONDS = 600

app = FastAPI(title="SPHEREx Blink API", docs_url="/api/docs", openapi_url="/api/openapi.json")


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


class Working(Exception):
    """A background job is still preparing this answer (HTTP 202; the website asks again)."""


@app.exception_handler(ApiError)
async def _api_error(_, exc: ApiError):
    return JSONResponse({"error": exc.message}, status_code=exc.status)


@app.exception_handler(Working)
async def _working(_, exc: Working):
    return JSONResponse({"status": "working", "message": str(exc)}, status_code=202)


@app.exception_handler(RequestValidationError)
async def _bad_request(_, exc: RequestValidationError):
    problems = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
    return JSONResponse({"error": f"Bad request ({problems})"}, status_code=400)


# ---------- where frames live ----------

def _official_positions() -> dict[str, tuple[float, float]]:
    """Grid centres of the prepared frames (from their manifests, so they match exactly)."""
    positions = {}
    for path in PREPARED_DIR.glob("*/d*/manifest.json"):
        m = json.loads(path.read_text())
        positions[m["target"]] = (m["ra"], m["dec"])
    return positions


def _job_key(ra: float, dec: float, fov: float) -> str:
    return f"pos_{ra:.4f}_{'p' if dec >= 0 else 'm'}{abs(dec):.4f}_fov{fov:g}"


def locate(target: str | None, ra: float | None, dec: float | None, band: int, fov: float) -> dict:
    """Which folder answers this request: a prepared official target, or a job folder for a position."""
    if band not in DETECTORS:
        raise ApiError(400, f"band must be 1-6, got {band}")
    if target is not None:
        if target not in {t["key"] for t in OFFICIAL_TARGETS}:
            raise ApiError(404, f"Unknown target {target!r}; official targets: "
                                + ", ".join(t["key"] for t in OFFICIAL_TARGETS))
        folder = PREPARED_DIR / target / f"d{band}"
        if not (folder / "manifest.json").exists():
            prepared = sorted(int(p.name[1:]) for p in (PREPARED_DIR / target).glob("d*") if (p / "manifest.json").exists())
            raise ApiError(404, f"No prepared frames for {target} in D{band}; prepared detectors: "
                                + (", ".join(f"D{d}" for d in prepared) or "none"))
        return {"kind": "prepared", "key": target, "folder": folder, "url": f"/frames/{target}/d{band}/"}
    if ra is None or dec is None:
        raise ApiError(400, "Give either target= or both ra= and dec=")
    if not (0 <= ra < 360 and -90 <= dec <= 90):
        raise ApiError(400, "ra must be 0-360 and dec -90..+90 degrees")
    if not 1 <= fov <= 15:
        raise ApiError(400, "fov_arcmin must be 1-15")
    if math.isclose(fov, PREPARED_FOV):
        for key, (tra, tdec) in _official_positions().items():
            if separation_arcsec(ra, dec, tra, tdec) < SAME_TARGET_ARCSEC and (PREPARED_DIR / key / f"d{band}" / "manifest.json").exists():
                return locate(key, None, None, band, fov)
    key = _job_key(ra, dec, fov)
    return {"kind": "job", "key": key, "folder": JOBS_DIR / key / f"d{band}", "url": f"/jobframes/{key}/d{band}/",
            "ra": round(ra, 4), "dec": round(dec, 4), "fov": fov, "band": band}


# ---------- background jobs (any position) ----------

_pool = ThreadPoolExecutor(max_workers=1)   # one job at a time: IRSA answers "503 busy" to more
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _run_job(loc: dict) -> None:
    job = _jobs[str(loc["folder"])]
    try:
        job["stage"] = "downloading SPHEREx cutouts and adding up each visit"
        render_frames(loc["ra"], loc["dec"], loc["key"], f"RA {loc['ra']:.4f}° Dec {loc['dec']:+.4f}°",
                      "typed position, rounded to 0.0001° (not moved for proper motion)", loc["band"],
                      "coadd", JOB_EXPOSURES_PER_VISIT, loc["fov"], JOBS_DIR)
        for stage, step in [("Gaia DR3 markers", write_gaia), ("difference maps", write_diff),
                            ("light curve", write_lightcurve)]:
            job["stage"] = stage
            try:
                step(loc["folder"])
            except Exception as exc:  # the frames are still worth showing; say what is missing
                job["warnings"].append(f"{stage} failed: {exc}")
        job.update(status="ready", stage="done")
    except NoImages as exc:
        job.update(status="none", error=str(exc))
    except Exception as exc:
        job.update(status="failed", error=f"{exc.__class__.__name__}: {exc}", failed_at=time.time())
        traceback.print_exc()


def job_status(loc: dict) -> dict:
    """Start the job if needed; returns its state."""
    folder = loc["folder"]
    with _jobs_lock:
        job = _jobs.get(str(folder))
        if job and job["status"] == "failed" and time.time() - job["failed_at"] > FAILED_JOB_RETRY_SECONDS:
            job = None
        if job is None:
            if (folder / "manifest.json").exists():
                return {"status": "ready", "warnings": []}
            job = {"status": "working", "stage": "waiting for the previous job", "warnings": [],
                   "started_at": datetime.now(timezone.utc).strftime("%H:%M UTC")}
            _jobs[str(folder)] = job
            _pool.submit(_run_job, loc)
        return job


def ensure_ready(loc: dict) -> list[str]:
    """Raise the right answer unless the folder is ready; returns warnings."""
    if loc["kind"] == "prepared":
        return []
    job = job_status(loc)
    if job["status"] == "working":
        raise Working(f"Preparing SPHEREx frames for this position (started {job['started_at']}): "
                      f"{job['stage']}. This takes a few minutes.")
    if job["status"] == "none":
        raise ApiError(404, job["error"])
    if job["status"] == "failed":
        raise ApiError(502, f"Could not prepare the frames: {job['error']}")
    return job["warnings"]


def _read(loc: dict, name: str, what: str) -> dict:
    path = loc["folder"] / name
    if not path.exists():
        raise ApiError(404, f"No {what} for this position and detector")
    return json.loads(path.read_text())


# ---------- endpoints ----------

@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/resolve")
def resolve(name: str = Query(..., min_length=1, max_length=100)):
    try:
        star = resolve_name(name)
    except LookupError as exc:
        raise ApiError(404, str(exc))
    except ResolverUnavailable as exc:
        raise ApiError(503, str(exc))
    moved = None
    if star["pmra"] is not None and star["pmdec"] is not None:
        ra, dec = position_at(star["ra"], star["dec"], star["pmra"], star["pmdec"], star["epoch"], POSITION_YEAR)
        moved = {"ra": ra, "dec": dec, "year": POSITION_YEAR,
                 "moved_arcsec": round(separation_arcsec(star["ra"], star["dec"], ra, dec), 2)}
    return {**star, "source": f"SIMBAD ({star['server']})", "position_now": moved}


_coverage_cache: dict[tuple, tuple[float, dict]] = {}


@app.get("/api/coverage")
def coverage(ra: float = Query(..., ge=0, lt=360), dec: float = Query(..., ge=-90, le=90),
             band: int | None = Query(None, ge=1, le=6)):
    key = (round(ra, 5), round(dec, 5), band)
    cached = _coverage_cache.get(key)
    if cached and time.time() - cached[0] < COVERAGE_CACHE_SECONDS:
        return cached[1]
    try:
        images = archive.find_images(ra, dec, detector=band)
    except archive.ArchiveError as exc:
        raise ApiError(502, f"IRSA did not answer: {exc}")
    answer = {
        "ra": ra, "dec": dec, "band": band,
        "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "summary": archive.summarize(images),
        "images": [{"obs_id": im.obs_id, "band": im.detector, "mjd": round(im.mjd, 5),
                    "wl_min_um": round(im.wl_min_um, 4), "wl_max_um": round(im.wl_max_um, 4),
                    "release": im.collection, "release_date": im.release_date} for im in images],
    }
    _coverage_cache[key] = (time.time(), answer)
    return answer


def location(target: str | None = Query(None, description="official target key, e.g. barnard"),
             ra: float | None = None, dec: float | None = None,
             band: int = Query(..., ge=1, le=6), fov_arcmin: float = PREPARED_FOV) -> dict:
    loc = locate(target, ra, dec, band, fov_arcmin)
    loc["warnings"] = ensure_ready(loc)
    return loc


@app.get("/api/frames")
def frames(loc: dict = Depends(location)):
    m = _read(loc, "manifest.json", "frames")
    for f in m["frames"]:
        f["png_url"] = loc["url"] + f["png"]
        if f.get("flags_png"):
            f["flags_png_url"] = loc["url"] + f["flags_png"]
    return {**m, "base_url": loc["url"], "source": loc["kind"], "warnings": loc["warnings"]}


@app.get("/api/gaia")
def gaia(loc: dict = Depends(location)):
    return _read(loc, "gaia.json", "Gaia markers")


@app.get("/api/diff")
def diff(loc: dict = Depends(location)):
    d = _read(loc, "diff.json", "difference maps")
    for p in d["pairs"]:
        p["png_url"] = loc["url"] + p["png"]
    return {**d, "base_url": loc["url"]}


@app.get("/api/lightcurve")
def lightcurve(loc: dict = Depends(location), x: float | None = None, y: float | None = None):
    if x is None and y is None:
        return _read(loc, "lightcurve.json", "light curve")
    if x is None or y is None:
        raise ApiError(400, "Give both x= and y= (pixels of the frame, 0 = first pixel), or neither")
    size = _read(loc, "manifest.json", "frames")["size_px"]
    if not (0 <= x <= size - 1 and 0 <= y <= size - 1):
        raise ApiError(400, f"x and y must be 0-{size - 1}")
    if not (loc["folder"] / "exposures.fits").exists():
        raise ApiError(404, "No per-exposure data for this position and detector")
    return lightcurve_at(loc["folder"], x, y)


@app.get("/api/{rest:path}")
def unknown(rest: str):
    raise ApiError(404, f"No such API endpoint: /api/{rest}")


JOBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/jobframes", StaticFiles(directory=JOBS_DIR), name="jobframes")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="site")
