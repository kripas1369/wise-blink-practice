"""The proof panel's numbers (proof.json): how far the target moved against Gaia, and what data it rests on.

    python -m backend.app.proof frontend/frames/*/d* [--online]

Motion: the target's position in the first and the last visit, measured with the centroid, or with
the centre of the saturated core when the centroid box is not fully usable (backend/app/measure.py),
compared with where Gaia DR3 puts the star on those dates (gaia.json). No Gaia star within 3″ of the
centre means there is nothing to compare with, and the file says so.

Data: visits, exposures used of those taken, flagged pixels per visit (manifest.json), the newest
exposure (exposures.fits). With --online (and in the API's jobs) the data release of every exposure
used is looked up at IRSA (spherex.obscore); without it, "releases" is null with the reason.
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from astropy.io import fits

from backend.app import archive
from backend.app.coords import mjd_to_date
from backend.app.diff import load_frame
from backend.app.measure import centroid, hole_centre

FORMAT = "spherex-blink-proof/1"
MAX_MOTION_ERROR_PX = 0.5         # HACKATHON_PLAN C4 (Barnard's Star)
MAX_DIRECTION_ERROR_DEG = 30.0    # ours
MIN_TESTABLE_PX = 0.3             # ours: below this the measurement error (pixel phase, 0.11 px alignment) is as large


def angle_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    d = math.degrees(math.atan2(a[1], a[0]) - math.atan2(b[1], b[0]))
    return abs((d + 180) % 360 - 180)


def measure_ends(folder: Path, manifest: dict, track: list) -> tuple[str, list] | None:
    """(method, [first xy, last xy]) with the first method that works in both end visits."""
    ends = [0, len(manifest["frames"]) - 1]
    frames = [load_frame(folder / manifest["frames"][i]["fits"]) for i in ends]
    for name, how in (("centroid", centroid), ("saturated-core centre", hole_centre)):
        found = [how(f, *track[i]) for f, i in zip(frames, ends)]
        if all(found):
            return name, [p[:2] for p in found]
    return None


def motion(folder: Path, manifest: dict, gaia: dict | None) -> dict:
    star = next((s for s in gaia["stars"] if s.get("target")), None) if gaia else None
    if star is None:
        return {"status": "no_gaia_target",
                "reason": "Gaia DR3 lists no star within 3″ of the centre, so there is no expected motion to compare with."}
    if len(manifest["frames"]) < 2:
        return {"status": "one_visit", "reason": "Only one visit: no motion to measure."}
    g0, g1 = star["xy"][0], star["xy"][-1]
    expected = (g1[0] - g0[0], g1[1] - g0[1])
    out = {"gaia_source_id": star["source_id"], "visits": [manifest["frames"][0]["date_iso"][:10],
                                                           manifest["frames"][-1]["date_iso"][:10]],
           "expected_px": [round(v, 3) for v in expected], "expected_size_px": round(math.hypot(*expected), 2),
           "limits": {"max_error_px": MAX_MOTION_ERROR_PX, "max_error_source": "HACKATHON_PLAN C4",
                      "max_direction_deg": MAX_DIRECTION_ERROR_DEG, "min_testable_px": MIN_TESTABLE_PX,
                      "direction_and_min_source": "ours"}}
    found = measure_ends(folder, manifest, star["xy"])
    if found is None:
        return {**out, "status": "not_measurable",
                "reason": "Neither the centroid nor the saturated-core centre could be measured in both the first and the last visit."}
    method, (p0, p1) = found
    measured = (p1[0] - p0[0], p1[1] - p0[1])
    error = math.hypot(measured[0] - expected[0], measured[1] - expected[1])
    out.update(method=method, measured_px=[round(v, 3) for v in measured],
               measured_size_px=round(math.hypot(*measured), 2), difference_px=round(error, 2))
    if math.hypot(*expected) < MIN_TESTABLE_PX:
        return {**out, "status": "too_small",
                "reason": f"Gaia's motion is below {MIN_TESTABLE_PX} px, smaller than our measurement error, "
                          "so this cannot test it; the measured shift shows the size of that error."}
    direction = angle_deg(measured, expected)
    agrees = error <= MAX_MOTION_ERROR_PX and direction <= MAX_DIRECTION_ERROR_DEG
    return {**out, "direction_difference_deg": round(direction, 1), "status": "agrees" if agrees else "disagrees"}


def releases(manifest: dict, obs_ids: set[str]) -> dict:
    """Data release of each exposure used, from IRSA."""
    try:
        images = archive.find_images(manifest["ra"], manifest["dec"], detector=manifest["band"])
    except archive.ArchiveError as exc:
        return {"releases": None, "releases_reason": f"IRSA did not answer: {exc}"}
    found = {im.obs_id: im for im in images if im.obs_id in obs_ids}
    per = {}
    for im in found.values():
        per.setdefault(im.collection, {"n_exposures": 0, "release_date": im.release_date})
        per[im.collection]["n_exposures"] += 1
        per[im.collection]["release_date"] = max(per[im.collection]["release_date"], im.release_date)
    out = {"releases": per, "asked_irsa_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    if len(found) != len(obs_ids):
        out["releases_reason"] = f"{len(obs_ids) - len(found)} of {len(obs_ids)} exposures not found at IRSA today"
    return out


def data(folder: Path, manifest: dict, online: bool) -> dict:
    frames = manifest["frames"]
    table = fits.getdata(folder / "exposures.fits", "EXPOSURES") if (folder / "exposures.fits").exists() else None
    out = {
        "n_visits": len(frames),
        "span_days": round(frames[-1]["mjd"] - frames[0]["mjd"], 1),
        "n_exposures_used": sum(f["n_images"] for f in frames),
        "n_exposures_taken": sum(f.get("n_images_in_epoch", f["n_images"]) for f in frames),
        "pct_flagged_range": [min(f["pct_flagged"] for f in frames), max(f["pct_flagged"] for f in frames)],
        "visits": [{"date": f["date_iso"], "n_images": f["n_images"], "n_images_in_epoch": f.get("n_images_in_epoch"),
                    "pct_flagged": f["pct_flagged"], "pct_no_value": f.get("pct_no_value")} for f in frames],
        "frames_made_at": manifest["made_at"],
        "newest_exposure": mjd_to_date(float(table["MJD"].max()))[:10] if table is not None else frames[-1]["date_iso"][:10],
    }
    if table is None:
        return {**out, "releases": None, "releases_reason": "no exposures.fits, so the exposures used are not listed"}
    if not online:
        return {**out, "releases": None, "releases_reason": "not looked up (made offline)"}
    return {**out, **releases(manifest, {str(o).strip() for o in table["OBS_ID"]})}


def build_proof(folder: Path, online: bool = False) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    gaia_path = folder / "gaia.json"
    gaia = json.loads(gaia_path.read_text()) if gaia_path.exists() else None
    return {
        "format": FORMAT, "target": manifest["target"], "band": manifest["band"],
        "pixel_arcsec": manifest["pixel_arcsec"],
        "motion": motion(folder, manifest, gaia),
        "data": data(folder, manifest, online),
        "method": "motion: first to last visit, PNG pixels (+x west, +y south); centroid of the 5 × 5 pixels "
                  "around Gaia's position, or the centre of the saturated core when the box is not fully usable; "
                  "rough, because SPHEREx's PSF is about one 6.15″ pixel wide (pixel phase)",
        "made_by": "backend/app/proof.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def write_proof(folder: Path, online: bool = False) -> dict:
    proof = build_proof(folder, online)
    (folder / "proof.json").write_text(json.dumps(proof, indent=1, ensure_ascii=False) + "\n")
    return proof


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--online", action="store_true", help="look up the data release of each exposure at IRSA")
    args = parser.parse_args()
    for folder in args.folders:
        p = write_proof(folder, args.online)
        m, d = p["motion"], p["data"]
        print(f"{folder}: motion {m['status']}"
              + (f" ({m['method']}: measured {m['measured_size_px']} px vs Gaia {m['expected_size_px']} px, "
                 f"difference {m['difference_px']} px)" if "method" in m else "")
              + f"; {d['n_exposures_used']}/{d['n_exposures_taken']} exposures; releases "
              + (", ".join(d["releases"]) if d["releases"] else f"none ({d['releases_reason']})"))


if __name__ == "__main__":
    main()
