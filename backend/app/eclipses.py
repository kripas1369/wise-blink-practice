"""Eclipse mode, part 1: TESS's eclipse clock for SPHEREx exposures.

TESS timed hundreds of eclipsing binaries in its northern continuous viewing zone, which overlaps the
SPHEREx North deep field. With a TESS ephemeris (time of primary eclipse bjd0, period P), every SPHEREx
exposure gets an orbital phase, so exposures taken at many different wavelengths can be sorted by where
the binary is in its orbit instead of by date.

Times: SPHEREx headers and the archive use UTC (TIMESYS = 'UTC', MJD-AVG = exposure midpoint;
Explanatory Supplement v1.6). TESS uses BTJD = BJD_TDB - 2457000. to_btjd() converts: UTC -> TDB, plus
the light-travel time to the solar-system barycentre for the target's direction. SPHEREx is in low Earth
orbit, so using the geocentre costs at most ~23 ms.

    python -m backend.app.eclipses near 270 66.56 --radius 10       # TESS binaries near the NEP
    python -m backend.app.eclipses forecast 270.1 66.2              # SPHEREx exposures in eclipse, no download
"""
import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache

import astropy.constants as const
import astropy.units as u
import numpy as np
import requests
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time

from backend.app import archive
from backend.app.config import CACHE_DIR, DETECTORS
from backend.app.motion import position_at, separation_arcsec

TESS_EB_URL = ("https://archive.stsci.edu/hlsps/tess-ebs/"
               "hlsp_tess-ebs_tess_lcf-ffi_s0001-s0026_tess_v1.0_cat.csv")
TESS_EB_CITATION = "Prša et al. 2022, ApJS 258, 16 (TESS-EBs v1.0, MAST HLSP, doi:10.17909/t9-9gm4-fx30, CC BY 4.0)"
CATALOG_FILE = CACHE_DIR / "catalogs" / "tess_ebs_v1.0.csv"
BTJD_OFFSET = 2457000.0
TIC_EPOCH = 2000.0          # TESS Input Catalog positions are for J2000 (moved from Gaia with proper motion)
MATCH_ARCSEC = 10.0         # a TESS pixel is 21″; TIC positions themselves come from Gaia
NEP = (270.0, 66.560708)    # north ecliptic pole (J2000), centre of the SPHEREx North deep field
MAX_PHASE_ERROR = 0.01      # a target is usable only if TESS's clock is still this good in 2025-26


class CatalogUnavailable(RuntimeError):
    """The TESS-EB catalogue could not be downloaded and is not cached."""


@dataclass
class Ephemeris:
    tess_id: str
    ra: float               # J2000 (TIC)
    dec: float
    pmra: float             # mas/yr
    pmdec: float
    tmag: float
    bjd0: float             # BTJD of a primary eclipse (as listed)
    bjd0_err: float
    period: float           # days
    period_err: float
    morph: float            # 0 = well detached ... 1 = contact / ellipsoidal (Matijevič et al. 2012)
    prim_pos: float         # phase of the primary eclipse relative to bjd0 (model fit)
    prim_width: float       # full width of the primary eclipse, in phase
    prim_depth: float       # fractional depth in the TESS band (0.6-1.0 µm)
    sec_pos: float | None
    sec_width: float | None
    sec_depth: float | None
    model: str              # which TESS-EB light-curve model the eclipse numbers come from

    def position(self, year: float) -> tuple[float, float]:
        return position_at(self.ra, self.dec, self.pmra, self.pmdec, TIC_EPOCH, year)

    def phase_error(self, btjd: float) -> float:
        """How far TESS's clock can have drifted by `btjd`, in phase: (N σ_P + σ_T0) / P."""
        cycles = abs(btjd - self.bjd0) / self.period
        return (cycles * self.period_err + self.bjd0_err) / self.period


def _num(text: str) -> float | None:
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _eclipse_numbers(row: dict) -> tuple[str, dict] | None:
    """Eclipse widths, depths and positions from one model fit.

    "pf" (polyfit) widths are the full eclipse width in phase. "2g" (two Gaussians) widths came out about
    twice the polyfit ones where both exist (e.g. 0.141 vs 0.071), so they are halved to stay comparable.
    The polyfit numbers are used when they include a primary eclipse.
    """
    for model, width_factor in (("pf", 1.0), ("2g", 0.5)):
        pos, width, depth = (_num(row[f"prim_{k}_{model}"]) for k in ("pos", "width", "depth"))
        if None in (pos, width, depth) or width <= 0 or depth <= 0:
            continue
        s_pos, s_width, s_depth = (_num(row[f"sec_{k}_{model}"]) for k in ("pos", "width", "depth"))
        has_sec = None not in (s_pos, s_width, s_depth) and s_width > 0 and s_depth > 0
        return model, {
            "prim_pos": pos, "prim_width": width * width_factor, "prim_depth": depth,
            "sec_pos": s_pos if has_sec else None,
            "sec_width": s_width * width_factor if has_sec else None,
            "sec_depth": s_depth if has_sec else None,
        }
    return None


def _ephemeris(row: dict) -> Ephemeris | None:
    nums = {k: _num(row[k]) for k in ("ra", "dec", "pmra", "pmdec", "Tmag", "bjd0", "bjd0_uncert", "period",
                                      "period_uncert", "morph_coeff")}
    if None in (nums["ra"], nums["dec"], nums["bjd0"], nums["period"]) or nums["period"] <= 0:
        return None
    eclipse = _eclipse_numbers(row)
    if eclipse is None:
        return None
    model, numbers = eclipse
    return Ephemeris(
        tess_id=row["tess_id"], ra=nums["ra"], dec=nums["dec"],
        pmra=nums["pmra"] or 0.0, pmdec=nums["pmdec"] or 0.0, tmag=nums["Tmag"] or float("nan"),
        bjd0=nums["bjd0"], bjd0_err=nums["bjd0_uncert"] or 0.0,
        period=nums["period"], period_err=nums["period_uncert"] or 0.0,
        morph=nums["morph_coeff"] if nums["morph_coeff"] is not None else float("nan"),
        model=model, **numbers,
    )


def _download_catalog() -> None:
    try:
        resp = requests.get(TESS_EB_URL, timeout=120)
    except requests.RequestException as exc:
        raise CatalogUnavailable(f"MAST did not answer: {exc}") from exc
    if resp.status_code != 200 or not resp.text.startswith("tess_id,"):
        raise CatalogUnavailable(f"MAST answered HTTP {resp.status_code}")
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CATALOG_FILE.with_suffix(".part")
    tmp.write_text(resp.text)
    tmp.rename(CATALOG_FILE)


@lru_cache(maxsize=1)
def load_catalog() -> tuple[Ephemeris, ...]:
    """Every TESS-EB row with a usable ephemeris and primary eclipse (first signal of each star only)."""
    if not CATALOG_FILE.exists():
        _download_catalog()
    with CATALOG_FILE.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["signal_id"] == "1"]
    return tuple(e for e in map(_ephemeris, rows) if e is not None)


def near(ra: float, dec: float, radius_deg: float) -> list[tuple[Ephemeris, float]]:
    """TESS binaries within radius_deg, nearest first, with their distance in degrees."""
    found = [(e, separation_arcsec(ra, dec, e.ra, e.dec) / 3600) for e in load_catalog()]
    return sorted([(e, d) for e, d in found if d <= radius_deg], key=lambda x: x[1])


def find(ra: float, dec: float, radius_arcsec: float = MATCH_ARCSEC) -> Ephemeris | None:
    """The TESS binary at this position (J2000 or moved; 10″ covers both for these stars), or None."""
    hits = near(ra, dec, radius_arcsec / 3600)
    return hits[0][0] if hits else None


def by_tess_id(tess_id: str) -> Ephemeris | None:
    return next((e for e in load_catalog() if e.tess_id == str(tess_id)), None)


# ---------- time and phase ----------

def to_btjd(mjd_utc, ra: float, dec: float) -> np.ndarray:
    """SPHEREx MJD (UTC) -> BTJD (BJD_TDB - 2457000) for a target at (ra, dec).

    Light-travel time = (Earth's barycentric position · direction to the star) / c, with astropy's built-in
    ephemeris. At the geocentre this is what Time.light_travel_time gives, without its Earth-rotation
    (IERS) download.
    """
    tdb = Time(np.atleast_1d(np.asarray(mjd_utc, float)), format="mjd", scale="utc").tdb
    earth = get_body_barycentric("earth", tdb).xyz.to_value(u.m)
    star = SkyCoord(ra, dec, unit="deg").cartesian.xyz.value
    ltt_days = (star @ earth) / const.c.value / 86400
    return tdb.jd + ltt_days - BTJD_OFFSET


def phase(btjd, eph: Ephemeris) -> np.ndarray:
    """Orbital phase in [-0.5, 0.5), with the primary eclipse at 0."""
    raw = (np.asarray(btjd, float) - eph.bjd0) / eph.period - eph.prim_pos
    return (raw + 0.5) % 1.0 - 0.5


def secondary_phase(eph: Ephemeris) -> float | None:
    """Phase of the secondary eclipse on the same scale as phase() (about ±0.5 for a circular orbit)."""
    if eph.sec_pos is None:
        return None
    return (eph.sec_pos - eph.prim_pos + 0.5) % 1.0 - 0.5


def eclipse_part(phi, eph: Ephemeris, central: float = 1.0) -> np.ndarray:
    """0 = out of eclipse, 1 = in primary, 2 = in secondary; `central` < 1 keeps only the middle of each eclipse."""
    phi = np.asarray(phi, float)
    part = np.zeros(phi.shape, int)
    part[np.abs(phi) < central * eph.prim_width / 2] = 1
    sec = secondary_phase(eph)
    if sec is not None:
        d = np.abs((phi - sec + 0.5) % 1.0 - 0.5)
        part[(part == 0) & (d < central * eph.sec_width / 2)] = 2
    return part


def out_of_eclipse(phi, eph: Ephemeris, margin: float = 1.25) -> np.ndarray:
    """True where the exposure is clearly outside both eclipses (each eclipse widened by `margin`)."""
    return eclipse_part(phi, eph, margin) == 0


# ---------- what SPHEREx has, before any download ----------

def images_by_detector(ra: float, dec: float, detectors=tuple(DETECTORS)) -> dict[int, list[archive.SpherexImage]]:
    """SPHEREx images containing the point, one archive query per detector (deep fields time out otherwise)."""
    return {d: [im for im in archive.find_images(ra, dec, detector=d) if im.detector == d] for d in detectors}


def forecast(eph: Ephemeris, images: dict[int, list[archive.SpherexImage]], year: float = 2026.0) -> dict:
    """How many SPHEREx exposures fall in each eclipse, per detector, from the archive's times only."""
    ra, dec = eph.position(year)
    per_detector = {}
    all_btjd = []
    for d, ims in images.items():
        if not ims:
            per_detector[d] = {"n_images": 0, "n_primary": 0, "n_secondary": 0, "n_primary_central": 0}
            continue
        btjd = to_btjd([im.mjd for im in ims], ra, dec)
        all_btjd.extend(btjd.tolist())
        phi = phase(btjd, eph)
        part = eclipse_part(phi, eph)
        per_detector[d] = {
            "n_images": len(ims),
            "n_primary": int((part == 1).sum()),
            "n_secondary": int((part == 2).sum()),
            "n_primary_central": int((eclipse_part(phi, eph, 0.5) == 1).sum()),
        }
    latest = max(all_btjd) if all_btjd else eph.bjd0
    return {
        "per_detector": per_detector,
        "n_primary": sum(v["n_primary"] for v in per_detector.values()),
        "n_secondary": sum(v["n_secondary"] for v in per_detector.values()),
        "phase_error": round(eph.phase_error(latest), 5),
        "phase_error_rule": f"(N σ_P + σ_T0) / P at the last SPHEREx exposure; usable below {MAX_PHASE_ERROR}",
    }


def images_file(eph: Ephemeris):
    return CACHE_DIR / "eclipse" / f"tic{eph.tess_id}_images.json"


def cached_images(eph: Ephemeris, year: float = 2026.0, refresh: bool = False) -> dict[int, list[archive.SpherexImage]]:
    """images_by_detector() for this binary, kept on disk (the deep-field queries take minutes)."""
    path = images_file(eph)
    if path.exists() and not refresh:
        saved = json.loads(path.read_text())
        return {int(d): [archive.SpherexImage(**im) for im in ims] for d, ims in saved["images"].items()}
    ra, dec = eph.position(year)
    found = images_by_detector(ra, dec)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "tess_id": eph.tess_id, "ra": ra, "dec": dec, "asked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "collections": list(archive.COLLECTIONS),
        "images": {d: [asdict(im) for im in ims] for d, ims in found.items()},
    }))
    return found


def _spread(items: list, key, n: int) -> list:
    """n items spread evenly along `key` (all of them if there are no more than n)."""
    if len(items) <= n:
        return list(items)
    ordered = sorted(items, key=key)
    idx = np.unique(np.linspace(0, len(ordered) - 1, n).round().astype(int))
    return [ordered[i] for i in idx]


# Exposures downloaded per detector: most of the budget goes to the eclipses, where the signal is.
BUDGET = {"primary": 40, "secondary": 25, "outside": 50}


def select_for_download(ims: list[archive.SpherexImage], eph: Ephemeris, ra: float, dec: float,
                        budget: dict = BUDGET) -> list[archive.SpherexImage]:
    """Up to budget[...] exposures in the primary eclipse, the secondary eclipse and outside both.

    Each group is spread evenly in orbital phase, so the folded light curve covers ingress, middle and
    egress; ties in phase are broken by time. Wavelengths cannot be chosen before download (the archive
    lists only each image's full range), but the pointings, and so the wavelengths at the target, vary.
    """
    if not ims:
        return []
    phi = phase(to_btjd([im.mjd for im in ims], ra, dec), eph)
    part = eclipse_part(phi, eph)
    clear = out_of_eclipse(phi, eph)
    sec = secondary_phase(eph) or 0.5
    rows = list(zip(ims, phi, part, clear))
    chosen = (
        _spread([r for r in rows if r[2] == 1], lambda r: (r[1], r[0].mjd), budget["primary"])
        + _spread([r for r in rows if r[2] == 2], lambda r: ((r[1] - sec + 0.5) % 1.0, r[0].mjd), budget["secondary"])
        + _spread([r for r in rows if r[2] == 0 and r[3]], lambda r: (r[1] % 1.0, r[0].mjd), budget["outside"])
    )
    return sorted((r[0] for r in chosen), key=lambda im: im.mjd)


def summary(e: Ephemeris) -> dict:
    out = asdict(e)
    out["sec_phase"] = secondary_phase(e)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_near = sub.add_parser("near", help="TESS binaries near a position")
    p_near.add_argument("ra", type=float)
    p_near.add_argument("dec", type=float)
    p_near.add_argument("--radius", type=float, default=10.0, help="degrees")
    p_fc = sub.add_parser("forecast", help="SPHEREx exposures in eclipse for the binary at a position")
    p_fc.add_argument("ra", type=float)
    p_fc.add_argument("dec", type=float)
    args = parser.parse_args()
    if args.cmd == "near":
        for e, d in near(args.ra, args.dec, args.radius):
            print(f"TIC {e.tess_id:>10}  {d:5.2f}°  T {e.tmag:5.2f}  P {e.period:8.4f} d  morph {e.morph:.2f}  "
                  f"depth {e.prim_depth:.3f}  width {e.prim_width:.3f}  ({e.model})")
        return
    eph = find(args.ra, args.dec)
    if eph is None:
        raise SystemExit("No TESS-EB binary within 10″")
    fc = forecast(eph, cached_images(eph))
    print(f"TIC {eph.tess_id}: P {eph.period} d, phase error {fc['phase_error']}")
    for d, v in fc["per_detector"].items():
        print(f"  D{d}: {v['n_images']} images, {v['n_primary']} in primary ({v['n_primary_central']} central), "
              f"{v['n_secondary']} in secondary")


if __name__ == "__main__":
    main()
