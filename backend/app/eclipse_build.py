"""Eclipse mode, part 3: one TESS eclipsing binary seen by SPHEREx, ready for frontend/eclipse.html.

    python -m backend.app.eclipse_build 233208885                 # -> frontend/frames/eclipse/tic233208885/
    python -m backend.app.eclipse_build --index                   # index.json + catalog.json only

Output folder:
  eclipse.json        everything the page shows: ephemeris, forecast, every measured exposure with its phase
                      and wavelength, depth spectra, the checks, and the list of frames
  d<det>/p<k>.png     every exposure, in phase order; p<k>_n.png is the same exposure divided by the
                      binary's normal brightness at that exposure's wavelength (so colour is not mistaken for dimming)
  d<det>/diff.png     exposures in the middle of the primary eclipse minus out-of-eclipse exposures at the same
                      wavelengths, in σ (blue = fainter during the eclipse)
"""
import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from backend.app import archive
from backend.app import eclipse_depth as M
from backend.app import eclipses as E
from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import CACHE_DIR, DETECTORS, PIXEL_SCALE_ARCSEC, REPO_ROOT
from backend.app.coords import mjd_to_date, mjd_to_year
from backend.app.diff import colour, difference, png_xy
from backend.app.gaia import gaia_stars, markers, search_radius_deg
from backend.app.lightcurve import (
    CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX, MAX_WING_INNER_PX, SKY_ANNULUS_PX, WING_WIDTH_PX, field_stars, measure,
    neighbours, ring_weights, wing_radius,
)
from backend.app.motion import separation_arcsec
from backend.app.render import MIN_COVERED_PCT, brightness_scale, save_png

FORMAT = "spherex-eclipse/1"
OUT_ROOT = REPO_ROOT / "frontend" / "frames" / "eclipse"
FOV_ARCMIN = 3.0
MIN_SNR = 5.0                  # fainter exposures are drawn but not used
MAX_FIELD_STARS = 8
SHOWCASE_RADIUS_DEG = 10.0     # catalog.json: TESS binaries this close to the north ecliptic pole
DATA_CREDIT = ("NASA/IPAC Infrared Science Archive (IRSA), SPHEREx; ESA Gaia DR3; TESS eclipsing binaries: "
               + E.TESS_EB_CITATION)


PATH_CHUNK = 100
PATIENT_TRIES = 6
PATIENT_WAIT_S = 30     # IRSA TAP answered "503 busy" for a minute at a time on 12 Nov 2026


def _patiently(fn, *args):
    """Call fn, waiting PATIENT_WAIT_S between tries while the archive says it is busy."""
    for attempt in range(PATIENT_TRIES):
        try:
            return fn(*args)
        except archive.ArchiveError:
            if attempt == PATIENT_TRIES - 1:
                raise
            time.sleep(PATIENT_WAIT_S)


def folder_for(eph: E.Ephemeris, root: Path = OUT_ROOT) -> Path:
    return root / f"tic{eph.tess_id}"


# ---------- download and measure ----------

def load_exposures(eph: E.Ephemeris, ra: float, dec: float, fov: float, budget: dict, detectors) -> tuple[list, dict]:
    """Chosen exposures, downloaded (cached), cleaned and aligned on one grid around the binary."""
    images = E.cached_images(eph)
    grid, size = target_grid(ra, dec, fov)
    size_deg = cutout_size_deg(fov)
    c = (size - 1) // 2
    chosen = {d: E.select_for_download(images.get(d, []), eph, ra, dec, budget) for d in detectors}
    flat = [im for d in detectors for im in chosen[d]]
    stats = {"n_chosen": {d: len(chosen[d]) for d in detectors}, "n_failed": 0, "n_off_grid": 0}
    if not flat:
        return [], stats
    results = {im.did: archive.cutout_file(im, ra, dec, size_deg) for im in flat}
    missing = [im for im in flat if not results[im.did].exists()]
    for i in range(0, len(missing), PATH_CHUNK):
        _patiently(archive.attach_paths, missing[i:i + PATH_CHUNK], 100)
    results.update(archive.download_cutouts(missing, ra, dec, size_deg))
    rows = []
    for im in flat:
        path = results.get(im.did)
        if not isinstance(path, Path) or not path.exists():
            stats["n_failed"] += 1
            continue
        cleaned = clean_cutout(path, ra, dec)
        aligned = align(cleaned, grid, size)
        if aligned["pct_covered"] < MIN_COVERED_PCT or not aligned["inside"][c, c]:
            stats["n_off_grid"] += 1
            continue
        rows.append({"det": im.detector, "obs_id": im.obs_id, "did": im.did, "collection": im.collection,
                     "mjd": cleaned["mjd"], "wl": cleaned["wl_um"], "bw": cleaned["bw_um"], "aligned": aligned})
    rows.sort(key=lambda r: (r["det"], r["mjd"]))
    return rows, stats


SATURATED_FRACTION = 0.5    # the core counts as saturated if most exposures have no value in it


def aperture_for(rows: list[dict], c: float) -> dict:
    """Core circle, or a ring outside a saturated core; 'none' if the core is too big.

    Unlike one visit's light curve, a detector here has ~100 exposures, and a few have no value near the star
    for other reasons (edge of the exposure, a missing pixel). Those are left out (measure() says no_value);
    only when most exposures lack the core is the star treated as saturated.
    """
    has_value = np.array([r["aligned"]["covered"] for r in rows])
    core = ring_weights(has_value[0].shape, c, c, 0, CORE_RADIUS_PX) > 0
    holed = np.array([(core & ~hv).any() for hv in has_value])
    if holed.mean() <= SATURATED_FRACTION:
        return {"method": "core", "r_in": 0.0, "r_out": CORE_RADIUS_PX, "n_core_without_value": int(holed.sum())}
    r_in = wing_radius(has_value[holed], [(c, c)] * int(holed.sum()))
    if r_in > MAX_WING_INNER_PX:
        return {"method": "none", "r_in": r_in, "r_out": None,
                "reason": f"saturated: the no-value core reaches {r_in - 0.75:.1f} px; only rings starting at most "
                          f"{MAX_WING_INNER_PX:g} px out were checked to follow a star's brightness"}
    return {"method": "wings", "r_in": r_in, "r_out": r_in + WING_WIDTH_PX}


def photometry(rows: list[dict], x: float, y: float, r_in: float, r_out: float, sky=SKY_ANNULUS_PX) -> list[dict]:
    out = []
    for r in rows:
        a = r["aligned"]
        m = measure(a["image"], a["sigma"], a["bad"], a["covered"], x, y, r_in, r_out, sky)
        out.append(m)
    return out


# ---------- the analysis (pure numbers, also used by the tests) ----------

def _arr(points, key):
    return np.array([np.nan if p.get(key) is None else p[key] for p in points], float)


def normalise(det, wl, flux, err, good, fit_mask, with_jitter: bool = True) -> tuple[np.ndarray, np.ndarray, dict]:
    """g = flux / S(λ) per detector (S from the exposures in fit_mask), errors with the jitter term if asked."""
    g = np.full(flux.shape, np.nan)
    g_err = np.full(flux.shape, np.nan)
    info = {}
    for d in sorted(set(det.tolist())):
        m = det == d
        fit = m & good & fit_mask
        steady = M.fit_steady(wl[fit], flux[fit], err[fit], M.RESOLVING_POWER[d])
        if steady is None:
            info[d] = {"usable": False, "reason": f"only {int(fit.sum())} good out-of-eclipse exposures (need 8)"}
            continue
        s_vals = steady(wl[m])
        g[m] = flux[m] / s_vals
        g_err[m] = err[m] / s_vals
        s = M.jitter(g[fit], g_err[fit]) if with_jitter else 0.0
        g_err[m] = np.sqrt(g_err[m] ** 2 + s ** 2)
        info[d] = {"usable": True, "jitter": round(s, 4), "n_fit": steady.n_used, "n_knots": steady.n_knots,
                   "steady": steady}
    return g, g_err, info


def add_jitter(det, rel, rel_err, fit, info) -> np.ndarray:
    """Per detector, inflate errors so the out-of-eclipse exposures (after the baseline) scatter as they say."""
    out = rel_err.copy()
    for d, i in info.items():
        if not i.get("usable"):
            continue
        m = det == d
        s = M.jitter(rel[m & fit], rel_err[m & fit])
        out[m] = np.sqrt(rel_err[m] ** 2 + s ** 2)
        i["jitter"] = round(s, 4)
    return out


def analyse(points: list[dict], eph: E.Ephemeris, field: list[dict] = (), pdm: bool = True) -> dict:
    """Depth spectra and checks from measured exposures.

    points: det, wl, btjd, flux, err, n_flagged per exposure. field: [{source_id, g_mag, flux: [...],
    err: [...], n_flagged: [...]}] for comparison stars on the same exposures.
    """
    det = np.array([p["det"] for p in points], int)
    wl, btjd, flux, err = (_arr(points, k) for k in ("wl", "btjd", "flux", "err"))
    flagged = _arr(points, "n_flagged") > 0
    good = np.isfinite(wl) & np.isfinite(flux) & np.isfinite(err) & (err > 0) & ~flagged & (flux > MIN_SNR * err)
    phi = E.phase(btjd, eph)
    part = E.eclipse_part(phi, eph)
    central = E.eclipse_part(phi, eph, M.CENTRAL)
    clear = E.out_of_eclipse(phi, eph)
    half_null = M.CENTRAL * eph.prim_width / 2
    quarter = clear & (np.abs(np.abs(phi) - M.NULL_PHASE) < half_null)
    fit_mask = clear & ~quarter     # quarter-phase exposures are held out, so the null check is independent

    g, g_err, info = normalise(det, wl, flux, err, good, fit_mask, with_jitter=False)
    usable = good & np.isfinite(g)
    fit_g_err = add_jitter(det, g, g_err, usable & fit_mask, {d: dict(i) for d, i in info.items()})
    base = M.fit_baseline(phi[usable & fit_mask], g[usable & fit_mask], fit_g_err[usable & fit_mask])
    bl = M.baseline_at(phi, base)
    rel = g / bl
    rel_err = add_jitter(det, rel, g_err / bl, usable & fit_mask, info)
    g_err = rel_err * bl
    ranges = {d: (float(np.nanmin(wl[usable & (det == d)])), float(np.nanmax(wl[usable & (det == d)])))
              for d in info if info[d]["usable"] and (usable & (det == d)).any()}

    prim = M.depth_spectrum(det, wl, rel, rel_err, usable & (central == 1), ranges)
    sec = M.depth_spectrum(det, wl, rel, rel_err, usable & (central == 2), ranges)
    null = M.depth_spectrum(det, wl, rel, rel_err, usable & quarter, ranges)
    whole = {}
    for d in ranges:
        m = usable & (det == d)
        whole[d] = {k: M.weighted_depth(rel[m & sel], rel_err[m & sel])
                    for k, sel in (("primary", central == 1), ("secondary", central == 2), ("null", quarter))}
    ratio = []
    for p, s in zip(prim, sec):
        if p.get("depth") and s.get("depth") is not None and p["depth"] > 0:
            r = s["depth"] / p["depth"]
            r_err = abs(r) * math.hypot(s["err"] / max(abs(s["depth"]), 1e-9), p["err"] / p["depth"])
            ratio.append({"detector": p["detector"], "wl_mid": p["wl_mid"], "ratio": round(r, 4), "err": round(r_err, 4)})

    tess = None
    d1 = whole.get(1, {}).get("primary")
    if d1:
        tess = {"tess_depth": round(eph.prim_depth, 4), "spherex_d1_depth": round(d1["depth"], 4),
                "spherex_d1_err": round(d1["err"], 4),
                "note": "TESS sees 0.6-1.0 µm through 21″ pixels, SPHEREx D1 0.75-1.09 µm through 6.15″ pixels: "
                        "different colours and different light from neighbours, so close but not equal is expected"}

    out = {
        "phase": phi, "part": part, "central": central, "good": usable, "g": g, "g_err": g_err, "rel": rel,
        "rel_err": rel_err, "quarter": quarter,
        "detectors": {d: {k: v for k, v in i.items() if k != "steady"} for d, i in info.items()},
        "steady": {d: i["steady"] for d, i in info.items() if i.get("usable")},
        "baseline": base,
        "depth": {"primary": prim, "secondary": sec, "null": null, "secondary_over_primary": ratio,
                  "whole_detector": {d: {k: None if v is None else {kk: round(vv, 5) for kk, vv in v.items()}
                                         for k, v in w.items()} for d, w in whole.items()}},
        "checks": {
            "null": {**M.chi2_against_zero(null), "rule": f"exposures at quarter phase (|φ| = {M.NULL_PHASE} ± "
                     f"{half_null:.3f}, between the eclipses), left out of the normal-brightness fit; depths should be 0"},
            "primary_combined": M.chi2_against_zero(prim),
            "secondary_combined": M.chi2_against_zero(sec),
            "tess_band": tess,
        },
    }
    timing = M.eclipse_timing(det[usable], phi[usable], rel[usable], rel_err[usable], eph.prim_width)
    if timing:
        minutes = eph.period * 1440
        drift = eph.phase_error(float(np.nanmedian(btjd)))
        timing.update(delta_min=round(timing["delta_phase"] * minutes, 2), err_min=round(timing["err_phase"] * minutes, 2),
                      tess_clock_err_min=round(drift * minutes, 2),
                      rule="trapezoid eclipse (depth per detector, flat-bottom fraction from "
                           f"{', '.join(map(str, M.FLAT_FRACTIONS))}) fitted to exposures within one eclipse width of "
                           "phase 0; δ = how far the eclipse's middle is from where TESS's clock puts it; error from "
                           "Δχ² = 1 with χ² scaled to reduced χ² = 1")
        for k in ("delta_phase", "err_phase", "reduced_chi2"):
            timing[k] = round(timing[k], 5)
    out["checks"]["timing"] = timing
    out["checks"]["field_stars"] = field_null(field, det, wl, phi, central, fit_mask, eph)
    if pdm:
        out["checks"]["period_search"] = period_search(det, wl, btjd, flux, err, good, eph)
    return out


def field_null(field, det, wl, phi, central, fit_mask, eph) -> dict:
    """Comparison stars measured on the same exposures, folded on the binary's clock: depth should be 0."""
    rows = []
    for s in field:
        f, e = np.array(s["flux"], float), np.array(s["err"], float)
        fl = np.array(s["n_flagged"], float) > 0
        good = np.isfinite(wl) & np.isfinite(f) & np.isfinite(e) & (e > 0) & ~fl & (f > MIN_SNR * e)
        g, g_err, info = normalise(det, wl, f, e, good, fit_mask)
        m = good & np.isfinite(g) & (central == 1)
        res = M.weighted_depth(g[m], g_err[m])
        clear_scatter = M.robust_std(g[good & np.isfinite(g) & fit_mask])
        rows.append({"source_id": s["source_id"], "g_mag": s["g_mag"], "x": s["x"], "y": s["y"],
                     "n_in_eclipse": int(m.sum()),
                     "depth": None if res is None else round(res["depth"], 5),
                     "err": None if res is None else round(res["err"], 5),
                     "scatter_pct": None if not np.isfinite(clear_scatter) else round(100 * clear_scatter, 2)})
    return {"rule": "isolated Gaia DR3 stars in the same frames (G <= 17), normalised and folded exactly like the "
                    "binary; their 'depth' in the middle of the binary's primary eclipse should be 0",
            "stars": rows, **M.chi2_against_zero([r for r in rows if r["depth"] is not None])}


def period_search(det, wl, btjd, flux, err, good, eph, p_min=0.2, p_max=20.0) -> dict:
    """Period from SPHEREx alone (no TESS clock): S(λ) fitted to all good exposures, then PDM on g."""
    g, _, _ = normalise(det, wl, flux, err, good, np.ones_like(good))
    ok = good & np.isfinite(g)
    if ok.sum() < 30:
        return {"n": int(ok.sum()), "reason": "fewer than 30 good exposures"}
    t, y = btjd[ok], g[ok]
    periods = M.trial_periods(t, p_min, p_max)
    theta = M.pdm_theta(t, y, periods, n_bins=20)
    order = np.argsort(theta)
    best = []
    for i in order:
        p = periods[i]
        if all(abs(p - b["period"]) / b["period"] > 0.01 for b in best):
            best.append({"period": round(float(p), 6), "theta": round(float(theta[i]), 4)})
        if len(best) == 5:
            break
    near = periods[np.argmin(np.abs(periods - eph.period))]
    fine = np.linspace(near * 0.999, near * 1.001, 201)
    theta_fine = M.pdm_theta(t, y, fine, n_bins=20)
    top = best[0]["period"]
    relation = next((name for name, f in (("TESS period", 1), ("half the TESS period", 0.5), ("twice the TESS period", 2))
                     if abs(top / (eph.period * f) - 1) < 0.002), None)
    return {"method": "phase dispersion minimisation (Stellingwerf 1978), 20 phase bins, on flux / S(λ) with "
                      "S fitted to all exposures (no TESS information used)",
            "n": int(ok.sum()), "p_min": p_min, "p_max": p_max, "n_trials": len(periods), "best": best,
            "theta_at_tess_period": round(float(theta_fine.min()), 4),
            "best_near_tess_period": round(float(fine[np.argmin(theta_fine)]), 6),
            "theta_median": round(float(np.median(theta)), 4), "best_is": relation}


# ---------- pictures ----------

def save_rgba(rgba: np.ndarray, path: Path) -> None:
    Image.fromarray(rgba, "RGBA").save(path)


def write_frames(folder: Path, rows: list[dict], points: list[dict], steady: dict, d: int) -> dict:
    """p<k>.png per exposure in phase order (+ _n.png divided by S(λ)), one brightness scale per detector."""
    sub = folder / f"d{d}"
    sub.mkdir(parents=True, exist_ok=True)
    idx = sorted((i for i, r in enumerate(rows) if r["det"] == d), key=lambda i: points[i]["phase"])
    pictures = [rows[i]["aligned"] for i in idx]
    scale = brightness_scale(pictures)
    st = steady.get(d)
    ref = float(np.median(st([rows[i]["wl"] for i in idx]))) if st is not None else None
    frames = []
    for k, i in enumerate(idx):
        a = rows[i]["aligned"]
        name = f"p{k:03d}"
        save_png(a["image"], a["covered"], scale, sub / f"{name}.png")
        entry = {"point": i, "png": f"d{d}/{name}.png", "png_n": None}
        if st is not None and rows[i]["wl"] is not None:
            factor = ref / float(st([rows[i]["wl"]])[0])
            save_png(a["image"] * factor, a["covered"], scale, sub / f"{name}_n.png")
            entry["png_n"] = f"d{d}/{name}_n.png"
            entry["factor"] = round(factor, 4)
        points[i]["png"] = entry["png"]
        frames.append(entry)
    return {"scale": scale, "frames": frames}


def write_diff(folder: Path, rows: list[dict], points: list[dict], d: int, size: int) -> dict | None:
    """Middle of the primary eclipse minus out-of-eclipse exposures matched one-to-one in wavelength."""
    inside = [i for i, p in enumerate(points) if p["det"] == d and p["used"] and p["central"] == 1]
    pool = [i for i, p in enumerate(points) if p["det"] == d and p["used"] and p["clear"]]
    pairs = []
    for i in sorted(inside, key=lambda i: points[i]["wl"]):
        if not pool:
            break
        j = min(pool, key=lambda j: abs(points[j]["wl"] - points[i]["wl"]))
        if abs(points[j]["wl"] - points[i]["wl"]) < 0.5 * (points[i]["bw"] or 0):
            pairs.append((i, j))
            pool.remove(j)
    if len(pairs) < 3:
        return None
    c_in = coadd([rows[i]["aligned"] for i, _ in pairs])
    c_out = coadd([rows[j]["aligned"] for _, j in pairs])
    as_frame = lambda c: {"image": c["image"], "sigma": c["sigma"], "flagged": c["bad"],
                          "usable": c["covered"] & np.isfinite(c["image"]) & (c["sigma"] > 0)}
    res = difference(as_frame(c_out), as_frame(c_in))
    z = res["z"]
    sub = folder / f"d{d}"
    sub.mkdir(parents=True, exist_ok=True)
    save_rgba(colour(z), sub / "diff.png")
    c = (size - 1) // 2
    zmin, (row, col) = res["min"]
    return {"png": f"d{d}/diff.png", "n_pairs": len(pairs),
            "max_wl_gap_um": round(max(abs(points[i]["wl"] - points[j]["wl"]) for i, j in pairs), 4),
            "z_at_binary": None if not np.isfinite(z[c, c]) else round(float(z[c, c]), 2),
            "z_min": round(zmin, 2), "min_xy": png_xy((row, col), size),
            "min_distance_px": round(float(math.hypot(row - c, col - c)), 2),
            "scatter": round(res["scatter"], 3), "pct_valid": res["pct_valid"],
            "rule": "co-add (1/σ² weights) of the exposures in the middle of the primary eclipse, minus a co-add "
                    "of out-of-eclipse exposures matched one-to-one in wavelength (within half a bandwidth), "
                    "divided by the combined noise; the median difference (sky change) is removed"}


# ---------- whole build ----------

def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def _r(v, n=5):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def build(tess_id: str, out_root: Path = OUT_ROOT, fov: float = FOV_ARCMIN, budget: dict = E.BUDGET,
          detectors=tuple(DETECTORS), log=print) -> dict:
    eph = E.by_tess_id(tess_id)
    if eph is None:
        raise LookupError(f"TIC {tess_id} is not in TESS-EBs v1.0")
    images = E.cached_images(eph)
    mjds = [im.mjd for ims in images.values() for im in ims]
    year = mjd_to_year(float(np.median(mjds))) if mjds else 2026.0
    ra, dec = eph.position(year)
    fc = E.forecast(eph, images, year)
    log(f"TIC {eph.tess_id}: {sum(map(len, images.values()))} images, {fc['n_primary']} in primary eclipse")

    rows, stats = load_exposures(eph, ra, dec, fov, budget, detectors)
    log(f"  {len(rows)} exposures usable ({stats}); measuring the binary and comparison stars")
    grid, size = target_grid(ra, dec, fov)
    c = (size - 1) // 2
    btjd = E.to_btjd([r["mjd"] for r in rows], ra, dec)

    stars = gaia_stars(ra, dec, search_radius_deg(fov, year - 2016.0))
    gaia = markers(ra, dec, fov, [{"mjd": float(np.median([r["mjd"] for r in rows]))}], stars, target_year=year)

    points, apertures, field_flux = [], {}, {}
    for d in detectors:
        drows = [r for r in rows if r["det"] == d]
        if not drows:
            continue
        ap = aperture_for(drows, c)
        apertures[d] = ap
        meas = photometry(drows, c, c, ap["r_in"], ap["r_out"]) if ap["method"] != "none" else [{}] * len(drows)
        for r, m in zip(drows, meas):
            r["meas"] = m
        r_out = ap["r_out"] or ap["r_in"]
        chosen = field_stars(gaia, size, [(c, c)], r_out)[:MAX_FIELD_STARS]
        for s in chosen:
            x, y_png = s["xy"][0]
            ms = photometry(drows, x, size - 1 - y_png, 0.0, CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX)
            for r, m in zip(drows, ms):
                r.setdefault("field", {})[s["source_id"]] = m
            field_flux[s["source_id"]] = {"g_mag": s["g_mag"], "x": x, "y": y_png}

    for r, t in zip(rows, btjd):
        m = r.get("meas", {})
        points.append({"det": r["det"], "obs_id": r["obs_id"], "collection": r["collection"],
                       "mjd": round(r["mjd"], 6), "date": mjd_to_date(r["mjd"])[:16].replace("T", " ") + " UTC",
                       "btjd": round(float(t), 6), "wl": r["wl"], "bw": r["bw"],
                       "flux": _r(m.get("flux_mjy"), 4), "err": _r(m.get("err_mjy"), 4),
                       "n_flagged": m.get("n_flagged", 0), "no_value": m.get("no_value", True)})
    field = [{"source_id": sid, **meta,
              "flux": [r.get("field", {}).get(sid, {}).get("flux_mjy") for r in rows],
              "err": [r.get("field", {}).get(sid, {}).get("err_mjy") for r in rows],
              "n_flagged": [r.get("field", {}).get(sid, {}).get("n_flagged", 1) for r in rows]}
             for sid, meta in field_flux.items()]

    res = analyse(points, eph, field)
    for i, p in enumerate(points):
        p.update(phase=round(float(res["phase"][i]), 5), part=int(res["part"][i]), central=int(res["central"][i]),
                 clear=bool(E.out_of_eclipse(res["phase"][i:i + 1], eph)[0]), used=bool(res["good"][i]),
                 g=_r(res["g"][i]), g_err=_r(res["g_err"][i]), rel=_r(res["rel"][i]))

    log("  drawing the frames and difference images")
    folder = folder_for(eph, out_root)
    folder.mkdir(parents=True, exist_ok=True)
    frames, diffs = {}, {}
    for d in apertures:
        frames[d] = write_frames(folder, rows, points, res["steady"], d)
        diffs[d] = write_diff(folder, rows, points, d, size)

    target_star = next((s for s in gaia["stars"] if s.get("target")), None)
    out = {
        "format": FORMAT, "made_by": "backend/app/eclipse_build.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "data_credit": DATA_CREDIT,
        "key": folder.name, "label": f"TIC {eph.tess_id}",
        "ra": round(ra, 7), "dec": round(dec, 7),
        "position_rule": f"TESS Input Catalog J2000 position moved with its proper motion to {year:.2f}, the "
                         "middle of the SPHEREx exposures",
        "distance_from_nep_deg": round(separation_arcsec(ra, dec, *E.NEP) / 3600, 2),
        "gaia_match": gaia.get("target_match"), "gaia_g": target_star and target_star["g_mag"],
        "neighbours": neighbours(gaia, [(c, c)], max((a["r_out"] or a["r_in"]) for a in apertures.values()))
        if apertures else [],
        "ephemeris": E.summary(eph),
        "phase_rule": "φ = frac((BTJD - bjd0) / P - prim_pos), shown from -0.5 to 0.5 with the primary eclipse at 0; "
                      "BTJD = BJD_TDB - 2457000 from each exposure's MJD-AVG (UTC) plus the light-travel time to "
                      "the solar-system barycentre (astropy)",
        "forecast": {**fc, "asked_at": json.loads(E.images_file(eph).read_text())["asked_at"]},
        "selection": {"budget_per_detector": budget, **stats, "n_usable": len(rows)},
        "fov_arcmin": fov, "size_px": size, "pixel_arcsec": PIXEL_SCALE_ARCSEC,
        "apertures": apertures,
        "detectors": res["detectors"],
        "baseline": res["baseline"],
        "depth": res["depth"],
        "checks": {**res["checks"], "difference_images": diffs},
        "frames": frames,
        "points": points,
        "method": {
            "photometry": "light inside a 2 px (12.3″) circle around the binary minus the median sky 10-14 px away, "
                          "in IMAGE - ZODI reprojected onto a north-up grid (ring outside the core if saturated); "
                          "exposures with a flagged pixel in the circle are drawn but not used",
            "normal_brightness": f"S(λ): cubic B-spline in ln λ per detector, knots every {M.KNOT_SPACING:g} resolution "
                                 "elements, fitted to out-of-eclipse exposures (quarter phase held out), 4σ clipping",
            "depth": f"1 - weighted mean of flux / S(λ) / baseline(φ) in the middle {M.CENTRAL:g} of each eclipse, "
                     f"{M.BINS_PER_DETECTOR} bins per detector, at least {M.MIN_POINTS_PER_BIN} exposures per bin",
            "errors": "VARIANCE-based, plus a per-detector jitter chosen so out-of-eclipse exposures scatter as their "
                      "errors say; bin errors enlarged by sqrt(reduced χ²) when above 1",
        },
    }
    (folder / "eclipse.json").write_text(json.dumps(out, default=_json_default, ensure_ascii=False) + "\n")
    (CACHE_DIR / "eclipse").mkdir(parents=True, exist_ok=True)
    write_index(out_root)
    return out


def summary_line(e: dict) -> dict:
    chk = e["checks"]
    return {"key": e["key"], "label": e["label"], "period": e["ephemeris"]["period"], "tmag": e["ephemeris"]["tmag"],
            "n_points": sum(p["used"] for p in e["points"]),
            "n_primary": sum(p["used"] and p["central"] == 1 for p in e["points"]),
            "primary": chk["primary_combined"], "null": chk["null"].get("combined"),
            "distance_from_nep_deg": e["distance_from_nep_deg"]}


def write_index(out_root: Path = OUT_ROOT) -> None:
    """index.json (built binaries) and catalog.json (TESS binaries near the NEP, with cached forecasts)."""
    out_root.mkdir(parents=True, exist_ok=True)
    built = []
    for path in sorted(out_root.glob("tic*/eclipse.json")):
        built.append(summary_line(json.loads(path.read_text())))
    (out_root / "index.json").write_text(json.dumps({"format": FORMAT + "-index", "binaries": built}, indent=1) + "\n")
    rows = []
    for eph, dist in E.near(*E.NEP, SHOWCASE_RADIUS_DEG):
        row = {"tess_id": eph.tess_id, "ra": round(eph.ra, 5), "dec": round(eph.dec, 5),
               "distance_deg": round(dist, 2), "tmag": _r(eph.tmag, 2), "period": eph.period,
               "morph": _r(eph.morph, 2), "prim_depth": round(eph.prim_depth, 3),
               "sec_depth": None if eph.sec_depth is None else round(eph.sec_depth, 3),
               "prim_width": round(eph.prim_width, 4), "phase_error": round(eph.phase_error(4000.0), 4),
               "built": (out_root / f"tic{eph.tess_id}" / "eclipse.json").exists()}
        if E.images_file(eph).exists():
            fc = E.forecast(eph, E.cached_images(eph))
            row.update(n_images=sum(v["n_images"] for v in fc["per_detector"].values()),
                       n_primary=fc["n_primary"], n_secondary=fc["n_secondary"])
        rows.append(row)
    (out_root / "catalog.json").write_text(json.dumps({
        "format": FORMAT + "-catalog", "source": E.TESS_EB_CITATION, "url": E.TESS_EB_URL,
        "rule": f"TESS-EBs v1.0 binaries (first signal of each star) within {SHOWCASE_RADIUS_DEG:g}° of the north "
                "ecliptic pole; phase_error = (N σ_P + σ_T0)/P at BTJD 4000 (2026-03-27)",
        "binaries": rows}, indent=1) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("tess_ids", nargs="*")
    parser.add_argument("--index", action="store_true", help="only write index.json and catalog.json")
    parser.add_argument("--fov", type=float, default=FOV_ARCMIN)
    parser.add_argument("--primary", type=int, default=E.BUDGET["primary"])
    parser.add_argument("--secondary", type=int, default=E.BUDGET["secondary"])
    parser.add_argument("--outside", type=int, default=E.BUDGET["outside"])
    parser.add_argument("--detectors", type=int, nargs="*", default=list(DETECTORS))
    args = parser.parse_args()
    if args.index:
        write_index()
        return
    budget = {"primary": args.primary, "secondary": args.secondary, "outside": args.outside}
    for tid in args.tess_ids:
        e = build(tid, fov=args.fov, budget=budget, detectors=tuple(args.detectors))
        chk = e["checks"]
        print(f"{e['label']}: primary {chk['primary_combined']}, null {chk['null']}")
        print(f"  field stars: {chk['field_stars'].get('combined')} ± {chk['field_stars'].get('combined_err')} "
              f"({len(chk['field_stars']['stars'])} stars)")
        print(f"  TESS band: {chk['tess_band']}")
        print(f"  period search: {chk['period_search'].get('best', [])[:3]} best is {chk['period_search'].get('best_is')}")
        for row in e["depth"]["primary"]:
            print(f"  D{row['detector']} {row['wl_lo']}-{row['wl_hi']} µm: n {row['n']}, depth {row['depth']} ± {row['err']}")


if __name__ == "__main__":
    main()
