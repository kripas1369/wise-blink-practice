"""Methane vision (<target>/methane/): cold brown dwarfs glow, ordinary stars fade away.

    python -m backend.app.methane frontend/frames/eps_ind_b [--absorbed 3.15 3.50] [--window 3.90 4.20] [--offline]

Brown dwarfs cooler than about 1300 K have methane, which absorbs strongly around 3.3 µm (the CH4 ν3 band),
while 3.9-4.2 µm is a window where they shine. Backyard Worlds' orange WISE W1/W2 movers rest on the same
physics with broad filters; SPHEREx's D4 sees the methane band itself and D5 the window.

SPHEREx's filter gives every exposure its own wavelength at the target, so the exposures are chosen by
wavelength, not by time: every D4 and D5 image of the position is downloaded (cached, at most
MAX_IMAGES_PER_BAND spread over time) and only those whose wavelength at the target lies inside a window are
kept (methane/d4/exposures.fits, methane/d5/exposures.fits; the flipbook's own frames are not touched).

Each exposure is multiplied by (wavelength / REF_UM)^2, which makes a normal star (Rayleigh-Jeans,
F_nu ~ wavelength^-2) equally bright in both windows. Then, per visit:

    methane vision = (window - k x absorbed) / noise

k is the median window/absorbed ratio of the field's own sources detected in both, or 1 when the field has
fewer than MIN_CALIBRATORS (the file says which). The noise includes a SYSTEMATIC share of the predicted star
light, because the PSF differs a little between detectors and a bright star never cancels perfectly.
Ordinary stars fade to about zero; a source whose 4 µm light is far above what its 3.3 µm light predicts glows.

The official flag mask is kept: flagged pixels are left out of every add-up. A glow is a colour, not an
identification: dusty young stars, red galaxies and a star blended with a brown dwarf can glow too.
"""
import argparse
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits

from backend.app import archive
from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.archive import EPOCH_GAP_DAYS, EPOCH_MAX_SPAN_DAYS
from backend.app.clean import clean_cutout
from backend.app.coords import mjd_to_date
from backend.app.lightcurve import CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX, load_exposures, measure, ring_weights
from backend.app.render import MIN_COVERED_PCT, SCALE_PERCENTILES, save_png

FORMAT = "spherex-blink-methane/1"
ABSORBED = {"band": 4, "range_um": (3.15, 3.50), "what": "methane (CH4) absorption band"}
WINDOW = {"band": 5, "range_um": (3.90, 4.20), "what": "4 µm window, short of CO2 at 4.26 µm"}
REF_UM = 4.0
STAR_SLOPE = 2.0                # Rayleigh-Jeans: F_nu ~ wavelength^-2 for a normal star at 3-4 µm
MAX_IMAGES_PER_BAND = 150       # deep fields near the ecliptic poles have hundreds; spread evenly over time
MIN_CALIBRATORS = 3
CALIBRATOR_SNR = 10.0
SYSTEMATIC = 0.05               # share of a star's predicted light that may be left after subtraction
EDGE_PX = 3
TARGET_EXCLUSION_PX = 4.0
SATURATED_FRACTION = 0.5        # the target counts as saturated if most exposures have no value in its core
MIN_WINDOW_SNR = 5.0            # the target must be seen at 4 µm to be tested
GLOW_SIGMA = 5.0
METHANE_EXCESS = 2.0            # at least twice the 4 µm light a normal star with its 3.3 µm light would have
NORMAL_SIGMA = 3.0
GLOW_SEARCH_PX = 2.5
NULL_STEP_PX = 2
MIN_NULL_PLACES = 20
Z_RANGE = 10.0
BASE_DETECTORS = (5, 4, 2, 3, 1, 6)
PATIENT_TRIES = 6
PATIENT_WAIT_S = 30


class NotTestable(LookupError):
    """The target folder lacks what methane vision needs."""


def _patiently(fn):
    """Call fn(), waiting PATIENT_WAIT_S between tries while the archive says it is busy."""
    for attempt in range(PATIENT_TRIES):
        try:
            return fn()
        except archive.ArchiveError:
            if attempt == PATIENT_TRIES - 1:
                raise
            time.sleep(PATIENT_WAIT_S)


def base_manifest(target_dir: Path) -> dict:
    """The grid (position, field of view) and label come from the target's frames."""
    for band in BASE_DETECTORS:
        path = Path(target_dir) / f"d{band}" / "manifest.json"
        if path.exists():
            return json.loads(path.read_text())
    raise NotTestable(f"No frames in {target_dir} yet, so there is no grid to put methane vision on.")


# ---------- choosing exposures by wavelength ----------

def spread(images: list, n: int) -> list:
    if len(images) <= n:
        return images
    return [images[i] for i in sorted({int(round(v)) for v in np.linspace(0, len(images) - 1, n)})]


def write_window_exposures(rows: list[tuple], grid, path: Path) -> None:
    """The same layout as lightcurve.write_exposures, so lightcurve.load_exposures reads it."""
    header = grid.to_header()
    header["BUNIT"] = "MJy/sr"
    hdus = [fits.PrimaryHDU()]
    for name, data in [("IMAGE", np.array([a["image"] for _, _, a in rows], np.float32)),
                       ("SIGMA", np.array([a["sigma"] for _, _, a in rows], np.float32)),
                       ("FLAGGED", np.array([a["bad"] for _, _, a in rows], np.uint8)),
                       ("HAS_VALUE", np.array([a["covered"] & np.isfinite(a["image"]) for _, _, a in rows], np.uint8))]:
        hdus.append(fits.ImageHDU(data, header=header.copy(), name=name))
    hdus.append(fits.BinTableHDU.from_columns([
        fits.Column("OBS_ID", "40A", array=[im.obs_id for im, _, _ in rows]),
        fits.Column("MJD", "D", array=[c["mjd"] for _, c, _ in rows]),
        fits.Column("WL_UM", "D", array=[c["wl_um"] for _, c, _ in rows]),
        fits.Column("BW_UM", "D", array=[c["bw_um"] if c["bw_um"] is not None else np.nan for _, c, _ in rows]),
        fits.Column("FRAME", "J", array=[-1] * len(rows)),
        fits.Column("COLLECTION", "24A", array=[im.collection for im, _, _ in rows]),
    ], name="EXPOSURES"))
    path.parent.mkdir(parents=True, exist_ok=True)
    fits.HDUList(hdus).writeto(path, overwrite=True)


def fetch_window(target_dir: Path, band: int, lo: float, hi: float, offline: bool = False, log=print) -> dict:
    """Every image of the position in this detector (cached cutouts first); keep those at lo-hi µm at the target."""
    m = base_manifest(target_dir)
    ra, dec, fov = m["ra"], m["dec"], m["fov_arcmin"]
    grid, size = target_grid(ra, dec, fov)
    size_deg = cutout_size_deg(fov)
    c = (size - 1) // 2
    if offline:
        pattern = f"*_D{band}_{ra:.5f}_{dec:+.5f}_{size_deg:.4f}.fits"
        paths = sorted((archive.CACHE_DIR / "cutouts").glob(pattern))
        images = [archive.SpherexImage(obs_id=p.name.split(f"_D{band}_")[0], did=p.name, detector=band, mjd_start=0,
                                       mjd_end=0, wl_min_um=0, wl_max_um=0, release_date="") for p in paths]
        found = {im.did: p for im, p in zip(images, paths)}
        n_archive = None
    else:
        everything = _patiently(lambda: archive.find_images(ra, dec, detector=band))
        everything = [im for im in everything if im.detector == band]
        n_archive = len(everything)
        images = spread(everything, MAX_IMAGES_PER_BAND)
        found = {im.did: archive.cutout_file(im, ra, dec, size_deg) for im in images}
        missing = [im for im in images if not found[im.did].exists()]
        log(f"D{band}: {n_archive} images in the archive, {len(images)} considered, {len(missing)} to download")
        for i in range(0, len(missing), 100):
            _patiently(lambda: archive.attach_paths(missing[i:i + 100], 100))
        found.update(archive.download_cutouts(missing, ra, dec, size_deg))
    rows, stats = [], {"n_in_archive": n_archive, "n_considered": len(images), "n_failed": 0, "n_off_grid": 0,
                       "n_outside_window": 0, "cap": MAX_IMAGES_PER_BAND}
    for im in images:
        path = found.get(im.did)
        if not isinstance(path, Path) or not path.exists():
            stats["n_failed"] += 1
            continue
        cleaned = clean_cutout(path, ra, dec)
        if cleaned["wl_um"] is None or not lo <= cleaned["wl_um"] < hi:
            stats["n_outside_window"] += 1
            continue
        aligned = align(cleaned, grid, size)
        if aligned["pct_covered"] < MIN_COVERED_PCT or not aligned["inside"][c, c]:
            stats["n_off_grid"] += 1
            continue
        if offline:
            im.obs_id = path.name.split(f"_D{band}_")[0]
        rows.append((im, cleaned, aligned))
    rows.sort(key=lambda r: r[1]["mjd"])
    stats["n_in_window"] = len(rows)
    if rows:
        write_window_exposures(rows, grid, Path(target_dir) / "methane" / f"d{band}" / "exposures.fits")
    stats["releases"] = sorted({im.collection for im, _, _ in rows if im.collection})
    return stats


# ---------- stacking ----------

def usable(ex: dict) -> np.ndarray:
    return ex["has_value"] & ~ex["bad"] & np.isfinite(ex["image"]) & (ex["sigma"] > 0)


def star_scale(wl_um: float) -> float:
    """Multiplier that gives a Rayleigh-Jeans star the same value at every wavelength."""
    return (wl_um / REF_UM) ** STAR_SLOPE


def stack(ex: dict, ks: list[int]) -> dict:
    """1/variance add-up of the exposures ks, each scaled by star_scale; NaN where none is usable."""
    good = usable(ex)
    num = np.zeros(ex["image"].shape[1:])
    den = np.zeros_like(num)
    for k in ks:
        s = star_scale(ex["wl_um"][k])
        w = np.where(good[k], 1 / np.where(good[k], ex["sigma"][k] * s, 1) ** 2, 0)
        num += w * np.where(good[k], ex["image"][k] * s, 0)
        den += w
    with np.errstate(invalid="ignore", divide="ignore"):
        return {"image": np.where(den > 0, num / den, np.nan), "sigma": np.where(den > 0, 1 / np.sqrt(den), np.nan),
                "n": len(ks)}


def vision(a: dict, b: dict, k: float, systematic: float = SYSTEMATIC) -> np.ndarray:
    """(window - k x absorbed) / noise, NaN where either has no value."""
    with np.errstate(invalid="ignore"):
        star = k * a["image"]
        noise = np.sqrt(b["sigma"] ** 2 + (k * a["sigma"]) ** 2 + (systematic * np.clip(star, 0, None)) ** 2)
        return (b["image"] - star) / noise


def flux(picture: dict, x: float, y: float) -> dict:
    """Light inside the light curves' core circle around (x, y) (FITS pixels), minus the field sky ring."""
    img = picture["image"]
    m = measure(np.nan_to_num(img), np.nan_to_num(picture["sigma"]), np.zeros(img.shape, bool), np.isfinite(img),
                x, y, 0.0, CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX)
    return {"flux_mjy": m["flux_mjy"], "err_mjy": m["err_mjy"], "no_value": m["no_value"]}


def picture_scale(pictures: list[dict]) -> dict:
    """One linear scale for both windows (after star_scale a normal star looks the same in both)."""
    good = np.concatenate([p["image"][np.isfinite(p["image"])] for p in pictures])
    vmin, vmax = (float(v) for v in np.percentile(good, SCALE_PERCENTILES))
    return {"vmin": round(vmin, 4), "vmax": round(vmax, 4), "unit": "MJy/sr x (wavelength/4 µm)^2", "stretch": "linear"}


# ---------- where the target is ----------

def target_track(target_dir: Path, size: int):
    """x(mjd), y(mjd) in FITS pixels: a straight line through the light curves' target positions (they follow
    Gaia DR3 or SIMBAD proper motion), else through the Gaia DR3 target's frame positions; else the grid centre."""
    pts = []
    rule = "a straight line through the light curves' target positions (Gaia DR3 or SIMBAD proper motion)"
    for path in sorted(Path(target_dir).glob("d[1-6]/lightcurve.json")):
        pts += [(p["mjd"], p["x"], size - 1 - p["y"]) for p in json.loads(path.read_text())["points"]]
    if not pts:
        for path in sorted(Path(target_dir).glob("d[1-6]/gaia.json")):
            star = next((s for s in json.loads(path.read_text())["stars"] if s.get("target") and s["has_motion"]), None)
            if star:
                frames = json.loads((path.parent / "manifest.json").read_text())["frames"]
                pts = [(f["mjd"], x, size - 1 - y) for f, (x, y) in zip(frames, star["xy"])]
                rule = f"Gaia DR3 {star['source_id']} moved with its proper motion (no light curve to follow)"
                break
    c = (size - 1) / 2
    if not pts:
        return lambda t: (c, c), "the grid centre (no light curve or Gaia DR3 target to follow)"
    t, x, y = (np.array(v, float) for v in zip(*pts))
    if np.ptp(t) < 1:
        return lambda _t: (float(x.mean()), float(y.mean())), rule
    fx, fy = np.polyfit(t, x, 1), np.polyfit(t, y, 1)
    return (lambda tt: (float(np.polyval(fx, tt)), float(np.polyval(fy, tt)))), rule


def saturated_share(ex: dict, track, missing: str = "has_value") -> float:
    """Share of exposures with a no-value pixel inside the target's core circle (missing="bad": a flagged one)."""
    if not len(ex["mjd"]):
        return 0.0
    holes = 0
    for k in range(len(ex["mjd"])):
        w = ring_weights(ex["image"][k].shape, *track(ex["mjd"][k]), 0, CORE_RADIUS_PX)
        hole = ~ex["has_value"][k] if missing == "has_value" else ex["bad"][k]
        holes += bool(((w > 0) & hole).any())
    return holes / len(ex["mjd"])


# ---------- visits ----------

def group_visits(ex_a: dict, ex_b: dict) -> list[dict]:
    """Visits across both detectors with the archive's rule (archive.group_epochs)."""
    rows = sorted([(t, "a", k) for k, t in enumerate(ex_a["mjd"])] + [(t, "b", k) for k, t in enumerate(ex_b["mjd"])])
    groups: list[dict] = []
    for t, which, k in rows:
        if not groups or t - groups[-1]["mjd_max"] > EPOCH_GAP_DAYS or t - groups[-1]["mjd_min"] > EPOCH_MAX_SPAN_DAYS:
            groups.append({"mjd_min": t, "mjd_max": t, "a": [], "b": []})
        groups[-1]["mjd_max"] = t
        groups[-1][which].append(k)
    return groups


# ---------- calibration on the field's own stars ----------

def local_peaks(snr: np.ndarray, threshold: float) -> list[tuple[int, int]]:
    """(x, y) of pixels above threshold that are the highest of their 3x3 neighbourhood, highest first."""
    padded = np.pad(np.nan_to_num(snr, nan=-np.inf), 1, constant_values=-np.inf)
    h, w = snr.shape
    centre = padded[1:-1, 1:-1]
    highest = np.ones(snr.shape, bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                highest &= centre >= padded[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    ys, xs = np.nonzero(highest & (centre > threshold))
    return sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: -snr[p[1], p[0]])


def inside_edges(x: float, y: float, size: int) -> bool:
    return EDGE_PX <= x <= size - 1 - EDGE_PX and EDGE_PX <= y <= size - 1 - EDGE_PX


def calibrate(a: dict, b: dict, avoid: list[tuple[float, float]]) -> dict:
    """k = median window/absorbed ratio of sources detected above CALIBRATOR_SNR in both stacks."""
    size = a["image"].shape[0]
    with np.errstate(invalid="ignore", divide="ignore"):
        snr = np.fmin(a["image"] / a["sigma"], b["image"] / b["sigma"])
    stars = []
    for x, y in local_peaks(snr, CALIBRATOR_SNR):
        if not inside_edges(x, y, size) or any(np.hypot(x - ax, y - ay) < TARGET_EXCLUSION_PX for ax, ay in avoid):
            continue
        fa, fb = flux(a, x, y), flux(b, x, y)
        if fa["flux_mjy"] is None or fb["flux_mjy"] is None:
            continue
        if fa["flux_mjy"] < CALIBRATOR_SNR * fa["err_mjy"] or fb["flux_mjy"] < CALIBRATOR_SNR * fb["err_mjy"]:
            continue
        stars.append({"x": x, "y": size - 1 - y, "ratio": round(fb["flux_mjy"] / fa["flux_mjy"], 3),
                      "absorbed_mjy": round(fa["flux_mjy"], 4), "window_mjy": round(fb["flux_mjy"], 4)})
    ratios = np.array([s["ratio"] for s in stars])
    if len(ratios) >= MIN_CALIBRATORS:
        k = float(np.median(ratios))
        rule = (f"median of {len(ratios)} field sources detected above {CALIBRATOR_SNR:g} sigma in both windows "
                "(the target left out)")
        spread_ = round(float(1.4826 * np.median(np.abs(ratios - k))), 3)
    else:
        k, spread_ = 1.0, None
        rule = (f"only {len(ratios)} field source(s) above {CALIBRATOR_SNR:g} sigma in both windows (need "
                f"{MIN_CALIBRATORS}), so a normal star is assumed to follow Rayleigh-Jeans exactly (k = 1)")
    return {"k": round(k, 4), "rule": rule, "n_sources": len(stars), "spread": spread_, "sources": stars}


# ---------- the target ----------

def combine(values: list[dict]) -> dict | None:
    """1/variance mean of per-visit fluxes (each measured where the target was that visit)."""
    good = [v for v in values if v["flux_mjy"] is not None and v["err_mjy"]]
    if not good:
        return None
    w = np.array([1 / v["err_mjy"] ** 2 for v in good])
    f = np.array([v["flux_mjy"] for v in good])
    return {"flux_mjy": float((w * f).sum() / w.sum()), "err_mjy": float(1 / np.sqrt(w.sum())), "n_visits": len(good)}


def colour(a: dict | None, b: dict | None, k: float, systematic: float = SYSTEMATIC, noise_factor: float = 1.0) -> dict:
    """The target's 4 µm light against what a normal star with its 3.3 µm light would have.

    noise_factor: how much wider the same measurement scatters at empty places than the noise maps say
    (null_test); the significance is divided by it."""
    if a is None or b is None or a["flux_mjy"] is None or b["flux_mjy"] is None or not a["err_mjy"] or not b["err_mjy"]:
        return {"testable": False}
    fa, ea, fb, eb = a["flux_mjy"], a["err_mjy"], b["flux_mjy"], b["err_mjy"]
    noise = noise_factor * float(np.sqrt(eb ** 2 + (k * ea) ** 2 + (systematic * max(k * fa, 0)) ** 2))
    out = {"testable": True, "absorbed_mjy": round(fa, 4), "absorbed_err_mjy": round(ea, 4),
           "window_mjy": round(fb, 4), "window_err_mjy": round(eb, 4),
           "glow_sigma": round((fb - k * fa) / noise, 1), "window_snr": round(fb / eb, 1)}
    if fa > 3 * ea:
        excess = fb / (k * fa)
        rel = float(np.sqrt((ea / fa) ** 2 + (eb / fb) ** 2 + systematic ** 2))
        out.update(excess=round(excess, 2), excess_err=round(excess * rel, 2), excess_is_lower_limit=False)
    else:
        out.update(excess=round(fb / (k * (max(fa, 0) + 3 * ea)), 2), excess_err=None, excess_is_lower_limit=True)
    return out


def methane_verdict(c: dict, reason: str | None = None) -> dict:
    if not c.get("testable"):
        return {"status": "not_testable", "text": reason or "No measurement in one of the two windows."}
    if c["window_snr"] < MIN_WINDOW_SNR:
        return {"status": "too_faint", "text": f"Too faint at 4 µm to test ({c['window_snr']:g} sigma, need "
                                               f"{MIN_WINDOW_SNR:g})."}
    more = "at least " if c["excess_is_lower_limit"] else ""
    if c["excess"] >= METHANE_EXCESS and c["glow_sigma"] >= GLOW_SIGMA:
        return {"status": "glows", "text": f"Glows: {more}{c['excess']:g}x the 4 µm light a normal star with its "
                                           f"3.3 µm light would have ({c['glow_sigma']:g} sigma). That is the colour "
                                           "of methane absorption, as in cold brown dwarfs."}
    if abs(c["glow_sigma"]) < NORMAL_SIGMA:
        return {"status": "normal", "text": f"Normal colour: its 4 µm light is what its 3.3 µm light predicts for a "
                                            f"normal star (within {NORMAL_SIGMA:g} sigma)."}
    if c["glow_sigma"] <= -NORMAL_SIGMA:
        return {"status": "bluer", "text": f"Bluer than a normal star ({c['excess']:g}x, {c['glow_sigma']:g} sigma): "
                                           "no sign of methane."}
    return {"status": "unclear", "text": f"Redder than a normal star ({more}{c['excess']:g}x, {c['glow_sigma']:g} "
                                         f"sigma) but short of the methane rule (at least {METHANE_EXCESS:g}x and "
                                         f"{GLOW_SIGMA:g} sigma)."}


def null_test(a: dict, b: dict, k: float, systematic: float, avoid: list[tuple[float, float]]) -> dict:
    """The target's measurement repeated on a grid of places away from it: neighbouring pixels share noise after
    reprojection, so the real scatter is usually wider than the noise maps say. factor = robust scatter, at least 1."""
    size = a["image"].shape[0]
    away = CORE_RADIUS_PX + FIELD_SKY_ANNULUS_PX[1]   # the target's own wings glow too
    values = []
    for y in range(EDGE_PX, size - EDGE_PX, NULL_STEP_PX):
        for x in range(EDGE_PX, size - EDGE_PX, NULL_STEP_PX):
            if any(np.hypot(x - ax, y - ay) < away for ax, ay in avoid):
                continue
            c = colour(flux(a, x, y), flux(b, x, y), k, systematic)
            if c.get("testable"):
                values.append(c["glow_sigma"])
    if len(values) < MIN_NULL_PLACES:
        return {"n_places": len(values), "scatter": None, "largest": None, "factor": 1.0}
    v = np.array(values)
    scatter = float(1.4826 * np.median(np.abs(v - np.median(v))))
    return {"n_places": len(values), "scatter": round(scatter, 2), "largest": round(float(v.max()), 1),
            "factor": round(max(1.0, scatter), 2)}


def glow_centre(z: np.ndarray, x: float, y: float) -> tuple[float, float] | None:
    """Centroid of the positive methane-vision signal within GLOW_SEARCH_PX of (x, y) (FITS pixels)."""
    yy, xx = np.indices(z.shape)
    near = (np.hypot(xx - x, yy - y) <= GLOW_SEARCH_PX) & np.isfinite(z) & (z > 0)
    if not near.any() or np.max(z[near]) < GLOW_SIGMA:
        return None
    w = np.where(near, z, 0)
    return float((w * xx).sum() / w.sum()), float((w * yy).sum() / w.sum())


def motion_summary(target_dir: Path) -> dict:
    """The proof panel's motion test (proof.py), from the first detector that could test it."""
    seen = []
    for band in BASE_DETECTORS:
        path = Path(target_dir) / f"d{band}" / "proof.json"
        if not path.exists():
            continue
        m = json.loads(path.read_text())["motion"]
        seen.append((band, m))
        if m.get("status") in ("agrees", "disagrees"):
            return {"status": m["status"], "band": band, "gaia_source_id": m.get("gaia_source_id"),
                    "expected_size_px": m.get("expected_size_px"), "measured_size_px": m.get("measured_size_px"),
                    "visits": m.get("visits")}
    if not seen:
        return {"status": "not_tested", "reason": "No proof panel for this position yet."}
    band, m = seen[0]
    return {"status": m.get("status", "not_tested"), "band": band, "reason": m.get("reason", "")}


def combined_text(methane_status: str, motion: dict) -> str:
    moves = motion["status"] == "agrees"
    if methane_status == "glows" and moves:
        return ("Moves the way Gaia DR3 predicts and glows in methane vision: the signature of a nearby cold brown "
                "dwarf. Check SIMBAD before calling it new; this tool claims no discovery.")
    if methane_status == "glows":
        reason = motion.get("reason", "").rstrip(".")
        return ("Glows in methane vision, but its motion could not be checked against Gaia DR3"
                + (f" ({reason})" if reason else "") + ". Cold brown dwarfs are often missing from Gaia because "
                "they are faint in visible light; play the methane-vision visits to see whether the glow moves.")
    if methane_status in ("normal", "bluer") and moves:
        return ("Moves the way Gaia DR3 predicts but has a normal star's 3-4 µm colour: a nearby star, not a "
                "methane brown dwarf.")
    if methane_status in ("normal", "bluer"):
        return "A normal star's 3-4 µm colour: nothing here looks like a methane brown dwarf."
    if methane_status == "unclear":
        return "Redder than a normal star but not clearly methane: dust, a blend or a warmer brown dwarf could do this."
    return "Methane vision cannot test this target; the motion test stands on its own."


# ---------- other glowing sources ----------

def other_glows(z: np.ndarray, a: dict, b: dict, k: float, systematic: float, noise_factor: float, grid,
                avoid: list[tuple[float, float]], gaia: dict | None) -> list[dict]:
    """Places away from the target and the edges that pass the target's own glow rule: places to look."""
    size = z.shape[0]
    out = []
    stars = (gaia or {}).get("stars", [])
    for x, y in local_peaks(z, GLOW_SIGMA):
        if not inside_edges(x, y, size) or any(np.hypot(x - ax, y - ay) < TARGET_EXCLUSION_PX for ax, ay in avoid):
            continue
        c = colour(flux(a, x, y), flux(b, x, y), k, systematic, noise_factor)
        if methane_verdict(c)["status"] != "glows":
            continue
        ra, dec = (float(v) for v in grid.pixel_to_world_values(x, y))
        near = [s for s in stars if s.get("g_mag") is not None
                and np.hypot(s["xy"][-1][0] - x, s["xy"][-1][1] - (size - 1 - y)) < 1.5]
        out.append({"x": x, "y": size - 1 - y, "sigma": c["glow_sigma"], "excess": c["excess"],
                    "excess_is_lower_limit": c["excess_is_lower_limit"], "ra": round(ra, 5), "dec": round(dec, 5),
                    "gaia": [{"source_id": s["source_id"], "g_mag": s["g_mag"]} for s in near]})
    return out[:10]


# ---------- the folder ----------

def save_vision_png(z: np.ndarray, path: Path) -> None:
    save_png(z, np.isfinite(z), {"vmin": -Z_RANGE, "vmax": Z_RANGE, "stretch": "linear"}, path)


def load_window(target_dir: Path, band: int) -> dict:
    folder = Path(target_dir) / "methane" / f"d{band}"
    if not (folder / "exposures.fits").exists():
        raise NotTestable(f"No D{band} exposures in the window yet (run without --offline to download them).")
    return load_exposures(folder)


def blend_notes(target_dir: Path, gaia: dict | None, centre, size: int) -> list[dict]:
    """Gaia stars inside the target's circle (the light curves' neighbours) and how far the glow is from each."""
    neighbours = {}
    for path in sorted(Path(target_dir).glob("d[1-6]/lightcurve.json")):
        for n in json.loads(path.read_text()).get("neighbours", []):
            neighbours[n["source_id"]] = n
    out = []
    for n in neighbours.values():
        star = next((s for s in (gaia or {}).get("stars", []) if s["source_id"] == n["source_id"]), None)
        if star is None:
            continue
        sx, sy = star["xy"][-1][0], size - 1 - star["xy"][-1][1]
        out.append({"source_id": n["source_id"], "g_mag": n["g_mag"],
                    "glow_to_star_px": None if centre is None else round(float(np.hypot(centre[0] - sx, centre[1] - sy)), 2)})
    return out


def build_methane(target_dir: Path, absorbed=ABSORBED["range_um"], window=WINDOW["range_um"],
                  downloads: dict | None = None) -> dict:
    target_dir = Path(target_dir)
    out_dir = target_dir / "methane"
    m = base_manifest(target_dir)
    size = m["size_px"]
    grid, _ = target_grid(m["ra"], m["dec"], m["fov_arcmin"])
    ex_a, ex_b = load_window(target_dir, ABSORBED["band"]), load_window(target_dir, WINDOW["band"])
    track, track_rule = target_track(target_dir, size)
    gaia = next((json.loads(p.read_text()) for p in sorted(target_dir.glob("d[1-6]/gaia.json"))), None)
    for old in out_dir.glob("*.png"):
        old.unlink()

    all_a, all_b = stack(ex_a, list(range(len(ex_a["mjd"])))), stack(ex_b, list(range(len(ex_b["mjd"]))))
    groups = [g for g in group_visits(ex_a, ex_b) if g["a"] and g["b"]]
    visits = []
    for g in groups:
        x, y = track((g["mjd_min"] + g["mjd_max"]) / 2)
        visits.append({"g": g, "a": stack(ex_a, g["a"]), "b": stack(ex_b, g["b"]), "x": x, "y": y})
    avoid = [(v["x"], v["y"]) for v in visits] or [track(float(np.mean(ex_b["mjd"])))]
    cal = calibrate(all_a, all_b, avoid)
    k = cal["k"]
    systematic = max(SYSTEMATIC, (cal["spread"] or 0) / k)
    scale = picture_scale([all_a, all_b])
    null_all = null_test(all_a, all_b, k, systematic, avoid)

    rows, per_a, per_b = [], [], []
    for i, v in enumerate(visits):
        g, a, b, x, y = v["g"], v["a"], v["b"], v["x"], v["y"]
        z = vision(a, b, k, systematic)
        save_vision_png(z, out_dir / f"visit{i}_methane.png")
        save_png(a["image"], np.isfinite(a["image"]), scale, out_dir / f"visit{i}_absorbed.png")
        save_png(b["image"], np.isfinite(b["image"]), scale, out_dir / f"visit{i}_window.png")
        fa, fb = flux(a, x, y), flux(b, x, y)
        per_a.append(fa)
        per_b.append(fb)
        null = null_test(a, b, k, systematic, [(x, y)])
        c = colour(fa if fa["flux_mjy"] is not None else None, fb if fb["flux_mjy"] is not None else None, k,
                   systematic, null["factor"])
        centre = glow_centre(z, x, y)
        rows.append({
            "visit": i, "date": mjd_to_date((g["mjd_min"] + g["mjd_max"]) / 2)[:10],
            "mjd_range": [round(g["mjd_min"], 5), round(g["mjd_max"], 5)],
            "methane_png": f"visit{i}_methane.png", "absorbed_png": f"visit{i}_absorbed.png",
            "window_png": f"visit{i}_window.png",
            "absorbed": {"n": len(g["a"]), "obs_ids": [ex_a["obs_id"][j] for j in g["a"]],
                         "wl_um": [round(float(ex_a["wl_um"][j]), 4) for j in g["a"]]},
            "window": {"n": len(g["b"]), "obs_ids": [ex_b["obs_id"][j] for j in g["b"]],
                       "wl_um": [round(float(ex_b["wl_um"][j]), 4) for j in g["b"]]},
            "target_xy": [round(x, 2), round(size - 1 - y, 2)],
            "glow_xy": None if centre is None else [round(centre[0], 2), round(size - 1 - centre[1], 2)],
            "colour": c, "null_test": null,
        })

    z_all = vision(all_a, all_b, k, systematic)
    save_vision_png(z_all, out_dir / "all_methane.png")
    save_png(all_a["image"], np.isfinite(all_a["image"]), scale, out_dir / "all_absorbed.png")
    save_png(all_b["image"], np.isfinite(all_b["image"]), scale, out_dir / "all_window.png")

    shares = {f"D{ABSORBED['band']}": saturated_share(ex_a, track), f"D{WINDOW['band']}": saturated_share(ex_b, track)}
    too_bright = [d for d, s in shares.items() if s > SATURATED_FRACTION]
    reason = None
    target_colour = colour(combine(per_a), combine(per_b), k, systematic, null_all["factor"])
    if too_bright:
        target_colour = {"testable": False}
        reason = (f"The target is too bright: its core has no value (saturated) in "
                  + ", ".join(f"{round(100 * shares[d])}% of the {d} exposures" for d in too_bright) + ".")
    elif not visits:
        reason = "No visit has exposures in both windows."
    elif not target_colour.get("testable"):
        flagged = {f"D{ABSORBED['band']}": saturated_share(ex_a, track, "bad"),
                   f"D{WINDOW['band']}": saturated_share(ex_b, track, "bad")}
        reason = ("The target's core is left out: its pixels carry the official bad-quality flags (often a star too "
                  "bright for the detector) in " + ", ".join(f"{round(100 * s)}% of the {d} exposures"
                                                            for d, s in flagged.items() if s > 0) + "."
                  if any(flagged.values()) else None)
    verdict = methane_verdict(target_colour, reason)
    motion = motion_summary(target_dir)
    mid_x, mid_y = avoid[len(avoid) // 2]
    centre = glow_centre(z_all, mid_x, mid_y)
    blend = blend_notes(target_dir, gaia, centre, size)

    notes = []
    for b in blend:
        notes.append(f"Gaia DR3 {b['source_id']} (G {b['g_mag']}) is inside the target's circle, so its light is in "
                     "the numbers above; a normal star fades in methane vision."
                     + (f" The glow's centre is {b['glow_to_star_px']} px from it." if b["glow_to_star_px"] is not None else ""))
    if cal["n_sources"] < MIN_CALIBRATORS:
        notes.append("Too few field stars to measure k here, so the normal-star colour is the Rayleigh-Jeans "
                     "assumption: a cool red star can look slightly redder than k = 1 without any methane.")
    notes.append("A glow is a colour, not an identification: dusty young stars, red galaxies and a star blended "
                 "with a brown dwarf can glow too. Nothing here is a discovery.")

    return {
        "format": FORMAT, "target": m["target"], "label": m["label"], "size_px": size,
        "pixel_arcsec": m["pixel_arcsec"], "ra": m["ra"], "dec": m["dec"], "fov_arcmin": m["fov_arcmin"],
        "settings": {
            "absorbed": {"band": ABSORBED["band"], "range_um": list(absorbed), "what": ABSORBED["what"]},
            "window": {"band": WINDOW["band"], "range_um": list(window), "what": WINDOW["what"]},
            "ref_um": REF_UM, "star_slope": STAR_SLOPE, "z_range": Z_RANGE, "glow_sigma": GLOW_SIGMA,
            "methane_excess": METHANE_EXCESS, "normal_sigma": NORMAL_SIGMA, "min_window_snr": MIN_WINDOW_SNR,
            "systematic": round(systematic, 3), "aperture_px": CORE_RADIUS_PX,
            "sky_annulus_px": list(FIELD_SKY_ANNULUS_PX), "saturated_fraction": SATURATED_FRACTION,
        },
        "downloads": downloads,
        "picture_scale": scale,
        "calibration": cal,
        "track_rule": track_rule,
        "saturated_share": {d: round(s, 2) for d, s in shares.items()},
        "visits": rows,
        "all": {"methane_png": "all_methane.png", "absorbed_png": "all_absorbed.png", "window_png": "all_window.png",
                "n_absorbed": len(ex_a["mjd"]), "n_window": len(ex_b["mjd"]),
                "glow_xy": None if centre is None else [round(centre[0], 2), round(size - 1 - centre[1], 2)]},
        "target": {"colour": target_colour, "verdict": verdict, "blend": blend},
        "motion": motion,
        "summary": combined_text(verdict["status"], motion),
        "null_test": null_all,
        "other_glows": other_glows(z_all, all_a, all_b, k, systematic, null_all["factor"], grid, avoid, gaia),
        "notes": notes,
        "method": (f"each exposure x (wavelength/{REF_UM:g} µm)^{STAR_SLOPE:g}, so a Rayleigh-Jeans star is equally "
                   f"bright at {absorbed[0]}-{absorbed[1]} µm (D{ABSORBED['band']}) and {window[0]}-{window[1]} µm "
                   f"(D{WINDOW['band']}); 1/variance add-up per visit with the official flag mask; methane vision = "
                   f"(window - k x absorbed) / noise, noise including {round(100 * systematic)}% of the predicted "
                   f"star light, shown from -{Z_RANGE:g} to +{Z_RANGE:g} sigma; target light in a {CORE_RADIUS_PX:g} "
                   f"px circle minus the {FIELD_SKY_ANNULUS_PX[0]:g}-{FIELD_SKY_ANNULUS_PX[1]:g} px sky ring at "
                   "the target's position that visit"),
        "made_by": "backend/app/methane.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx" + (", ESA Gaia DR3" if gaia else ""),
    }


def write_methane(target_dir: Path, absorbed=ABSORBED["range_um"], window=WINDOW["range_um"],
                  offline: bool = False, log=print) -> dict:
    """Download (or reuse) the window exposures, then write methane/methane.json and its pictures."""
    target_dir = Path(target_dir)
    base_manifest(target_dir)
    downloads = {}
    for spec, rng in ((ABSORBED, absorbed), (WINDOW, window)):
        downloads[f"D{spec['band']}"] = fetch_window(target_dir, spec["band"], *rng, offline=offline, log=log)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = build_methane(target_dir, absorbed, window, downloads)
    (target_dir / "methane" / "methane.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("targets", type=Path, nargs="+", help="e.g. frontend/frames/eps_ind_b")
    parser.add_argument("--absorbed", type=float, nargs=2, default=ABSORBED["range_um"], metavar=("LO", "HI"))
    parser.add_argument("--window", type=float, nargs=2, default=WINDOW["range_um"], metavar=("LO", "HI"))
    parser.add_argument("--offline", action="store_true", help="use only cutouts already in the cache")
    args = parser.parse_args()
    for target_dir in args.targets:
        try:
            r = write_methane(target_dir, tuple(args.absorbed), tuple(args.window), args.offline)
        except NotTestable as exc:
            print(f"{target_dir}: {exc}")
            continue
        c = r["target"]["colour"]
        print(f"{target_dir}: {r['target']['verdict']['status']} | k {r['calibration']['k']} "
              f"({r['calibration']['n_sources']} field sources) | "
              + (f"excess {c['excess']}x, glow {c['glow_sigma']} sigma, 4 µm {c['window_snr']} sigma | "
                 if c.get("testable") else "")
              + f"{len(r['visits'])} visits | motion {r['motion']['status']} | saturated {r['saturated_share']}")
        print(f"   downloads {r['downloads']}")
        print(f"   {r['target']['verdict']['text']}")
        print(f"   {r['summary']}")
        for v in r["visits"]:
            vc = v["colour"]
            print(f"   visit {v['visit'] + 1} {v['date']}: {v['absorbed']['n']}+{v['window']['n']} exposures, "
                  + (f"glow {vc['glow_sigma']} sigma" if vc.get("testable") else "no measurement")
                  + f", target {v['target_xy']}, glow centre {v['glow_xy']}")
        for n in r["notes"][:-1]:
            print(f"   note: {n}")
        for o in r["other_glows"]:
            print(f"   other glow {o['sigma']} sigma at {o['x']},{o['y']} gaia {o['gaia']}")


if __name__ == "__main__":
    main()
