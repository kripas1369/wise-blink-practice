"""Shared helpers for the SPHEREx Infrared Wanderers search: caches, archive queries, field geometry.

Everything this project writes goes under research/wanderers/ (cache/, results/, logs/); nothing in
research/out/ or the website's cache index is changed. SPHEREx image lists come only from the DR1 and QR3
collections (research/dr1.py); the old QR2 collections are never mixed in.
"""
import json
import math
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.app import archive
from backend.app.gaia import gaia_stars

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
RESULTS = HERE / "results"
LOGS = HERE / "logs"
FIGURES = HERE / "figures"
for _d in (CACHE, RESULTS, LOGS, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

# Cutouts go to research/wanderers/cache/cutouts, not the website's cache/ (whose size trimming must not see them).
archive.CACHE_DIR = CACHE
archive.MAX_PARALLEL_DOWNLOADS = 3

COLLECTIONS = ("spherex_dr1", "spherex_dr1_deep", "spherex_qr3", "spherex_qr3_deep")
PIXEL_ARCSEC = 6.15
CATWISE_EPOCH_MJD = 57170.0   # CatWISE2020 positions (ra, dec, ra_pm, dec_pm) refer to MJD 57170 (2015.4)

# Positions of the challenge's official targets (frontend/frames/*/manifest.json) and of the deep survey fields
# a "blind" field must avoid. Deep fields: centres from the survey papers (COSMOS, GOODS, UDS, EGS, Lockman,
# ELAIS-N1, XMM-LSS, Bootes, HDF-S, Euclid Deep Fields).
OFFICIAL_TARGETS = {
    "barnard": (269.44627, 4.76820), "wise0855": (133.75976, -7.24219), "eps_ind_b": (331.09664, -56.80066),
    "r_dra": (248.16723, 66.75502), "rw_aur": (76.95659, 30.40129),
}
DEEP_FIELDS = {
    "COSMOS": (150.12, 2.21), "GOODS-N": (189.23, 62.24), "GOODS-S/CDF-S": (53.12, -27.81), "UDS": (34.40, -5.20),
    "EGS": (214.80, 52.80), "Lockman Hole": (161.25, 58.00), "ELAIS-N1": (242.75, 55.00), "XMM-LSS": (35.70, -4.75),
    "Bootes": (218.00, 34.50), "HDF-S": (338.24, -60.55), "Euclid DF South": (61.24, -48.42),
    "Euclid DF North / NEP": (269.73, 66.02), "Euclid DF Fornax": (52.93, -28.09),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(name: str, msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    with open(LOGS / f"{name}.log", "a") as f:
        f.write(line + "\n")


def sep_deg(ra1, dec1, ra2, dec2):
    r1, d1, r2, d2 = map(np.radians, (ra1, dec1, ra2, dec2))
    h = np.sin((d2 - d1) / 2) ** 2 + np.cos(d1) * np.cos(d2) * np.sin((r2 - r1) / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(np.clip(h, 0, 1))))


def retry(fn, *args, tries=4, what="query", **kw):
    """Call fn, retrying with back-off; archive outages must not kill a long run."""
    last = None
    for i in range(tries):
        try:
            return fn(*args, **kw)
        except Exception as exc:  # network and archive errors of every kind
            last = exc
            time.sleep(min(60, 5 * 2 ** i))
    raise RuntimeError(f"{what} failed after {tries} tries: {last}")


def cached_json(path: Path, fn, refresh=False):
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    out = fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps(out))
    tmp.rename(path)
    return out


def images_at(ra: float, dec: float, key: str, refresh=False) -> list[archive.SpherexImage]:
    """Every DR1 + QR3 image whose footprint contains (ra, dec); cached in cache/images/<key>.json with the query date."""
    def ask():
        try:
            ims = archive.find_images(ra, dec, collections=COLLECTIONS)
        except archive.ArchiveError:  # very deep fields can time out; ask one detector at a time
            ims = [im for d in range(1, 7) for im in archive.find_images(ra, dec, collections=COLLECTIONS, detector=d)]
        return {"ra": ra, "dec": dec, "collections": list(COLLECTIONS), "asked_at": now(),
                "images": [asdict(im) for im in ims]}
    saved = cached_json(CACHE / "images" / f"{key}.json", lambda: retry(ask, what=f"SPHEREx images {key}"), refresh)
    return [archive.SpherexImage(**im) for im in saved["images"]]


def catwise(ra: float, dec: float, radius_deg: float, key: str) -> list[dict]:
    """CatWISE2020 sources within radius (IRSA TAP), cached. pm in arcsec/yr, positions at MJD 57170."""
    cols = ("source_name, ra, dec, sigra, sigdec, ra_pm, dec_pm, sigra_pm, sigdec_pm, pmra, pmdec, sigpmra, sigpmdec, "
            "w1mpro, w1sigmpro, w2mpro, w2sigmpro, w1snr, w2snr, meanobsmjd, ab_flags, cc_flags, nb, par_pm, par_pmsig")

    def ask():
        t = archive.run_query(f"""SELECT {cols} FROM catwise_2020
            WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, {radius_deg:.5f})) = 1""")
        rows = []
        for r in t:
            d = {}
            for c in t.colnames:
                v = r[c]
                if np.ma.is_masked(v):
                    d[c] = None
                elif isinstance(v, (bytes, str, np.str_)):
                    d[c] = v.decode() if isinstance(v, bytes) else str(v)
                else:
                    d[c] = float(v) if np.isfinite(float(v)) else None
            rows.append(d)
        return {"asked_at": now(), "ra": ra, "dec": dec, "radius_deg": radius_deg, "rows": rows}
    return cached_json(CACHE / "catwise" / f"{key}.json", lambda: retry(ask, what=f"CatWISE {key}"))["rows"]


def gaia(ra: float, dec: float, radius_deg: float, key: str) -> list[dict]:
    """Gaia DR3 sources (IRSA copy, epoch 2016.0), cached."""
    return cached_json(CACHE / "gaia" / f"{key}.json",
                       lambda: {"asked_at": now(), "rows": retry(gaia_stars, ra, dec, radius_deg, what=f"Gaia {key}")}
                       )["rows"]


def mjd_to_year(mjd):
    return 2000.0 + (np.asarray(mjd, float) - 51544.5) / 365.25


def tangent(ra, dec, ra0, dec0):
    """Gnomonic projection (arcsec) of (ra, dec) about (ra0, dec0); x points east, y north."""
    ra, dec, ra0, dec0 = map(np.radians, (np.asarray(ra, float), np.asarray(dec, float), ra0, dec0))
    cosc = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(ra - ra0)
    x = np.cos(dec) * np.sin(ra - ra0) / cosc
    y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(ra - ra0)) / cosc
    return np.degrees(x) * 3600, np.degrees(y) * 3600


def untangent(x, y, ra0, dec0):
    x, y = np.radians(np.asarray(x, float) / 3600), np.radians(np.asarray(y, float) / 3600)
    ra0, dec0 = math.radians(ra0), math.radians(dec0)
    rho = np.hypot(x, y)
    c = np.arctan(rho)
    with np.errstate(invalid="ignore", divide="ignore"):
        dec = np.arcsin(np.cos(c) * np.sin(dec0) + np.where(rho > 0, y * np.sin(c) * np.cos(dec0) / rho, 0))
        ra = ra0 + np.arctan2(x * np.sin(c), rho * np.cos(dec0) * np.cos(c) - y * np.sin(dec0) * np.sin(c))
    return np.degrees(ra) % 360, np.degrees(dec)


def gaia_xy_at(stars: list[dict], year: float, ra0: float, dec0: float):
    """Gaia positions moved linearly to `year` (parallax ignored), projected about the field centre (arcsec)."""
    ra = np.array([s["ra"] for s in stars])
    dec = np.array([s["dec"] for s in stars])
    pmra = np.array([s["pmra"] or 0.0 for s in stars])
    pmdec = np.array([s["pmdec"] or 0.0 for s in stars])
    x, y = tangent(ra, dec, ra0, dec0)
    dt = year - 2016.0
    return x + pmra * dt / 1000, y + pmdec * dt / 1000
