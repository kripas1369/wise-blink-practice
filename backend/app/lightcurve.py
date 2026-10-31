"""Day 4: the brightness of one sky position in every exposure (light curve), each with its own wavelength.

SPHEREx's filter (LVF) gives every exposure its own wavelength, so a light curve is only honest if each
point keeps its wavelength, and visits are compared at the same wavelength (same_wavelength()).

    python -m backend.app.lightcurve frontend/frames/rw_aur/d2     # exposures.fits + lightcurve.json

exposures.fits: every cached exposure of the frames, on the frames grid (FITS rows south first), so a
light curve can be measured at any pixel later (lightcurve_at, used by /api/lightcurve?x=&y=).

Brightness = sum of (value - sky) over a circle, times the pixel's solid angle, in mJy. No aperture
correction: it is the light inside the circle, not the star's total brightness, so it compares
exposures with each other, not with catalogues. When any exposure has no value inside the circle (a
saturated core), every exposure is measured in a ring outside the no-value pixels instead ("wings"),
which follows the star's brightness only if the PSF keeps its shape; check_wings() measures how well.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits

from backend.app.align import target_grid
from backend.app.config import PIXEL_SCALE_ARCSEC
from backend.app.coords import mjd_to_date
from backend.app.motion import position_at
from backend.app.rebuild import cached_visits

FORMAT = "spherex-blink-lightcurve/1"
CORE_RADIUS_PX = 2.0
WING_WIDTH_PX = 3.0
MAX_WING_INNER_PX = 3.0         # RW Aur (not saturated): a 3-6 px ring follows the core to ~10%, 6-9 px does not
SKY_ANNULUS_PX = (10.0, 14.0)
FIELD_SKY_ANNULUS_PX = (5.0, 8.0)
SUPERSAMPLE = 5
SAME_WAVELENGTH = 0.5           # exposures closer than half a bandwidth count as the same wavelength
MIN_SNR = 5.0                   # fainter points are drawn but not compared
FIELD_MAX_G = 17.0              # a 3′ frame has almost no isolated Gaia stars brighter than G 15
FIELD_ISOLATION_PX = 4.0
NEIGHBOUR_G_LIMIT = 3.0         # warn about Gaia stars inside the aperture up to 3 mag fainter than the target
PIXEL_SR = (PIXEL_SCALE_ARCSEC / 206264.806) ** 2
MJY_PER_PIXEL_UNIT = PIXEL_SR * 1e9   # 1 MJy/sr over one pixel, in mJy (0.889)


class NoExposures(LookupError):
    """No cached exposures behind these frames."""


# ---------- exposures.fits ----------

def write_exposures(folder: Path) -> Path:
    """Every cached exposure behind the frames, aligned on the frames grid, in time order."""
    manifest = json.loads((folder / "manifest.json").read_text())
    rows = [(i, c, a) for i, visit in enumerate(cached_visits(manifest)) for c, a in visit]
    if not rows:
        raise NoExposures(f"{folder}: no cached exposures (run render.py first)")
    rows.sort(key=lambda r: r[1]["mjd"])
    grid, _ = target_grid(manifest["ra"], manifest["dec"], manifest["fov_arcmin"])
    header = grid.to_header()
    header["BUNIT"] = "MJy/sr"
    cubes = [
        ("IMAGE", np.array([a["image"] for _, _, a in rows], np.float32), "IMAGE - ZODI per exposure"),
        ("SIGMA", np.array([a["sigma"] for _, _, a in rows], np.float32), "1 sigma from VARIANCE"),
        ("FLAGGED", np.array([a["bad"] for _, _, a in rows], np.uint8), "1 = flagged bad (official mask)"),
        ("HAS_VALUE", np.array([a["covered"] & np.isfinite(a["image"]) for _, _, a in rows], np.uint8),
         "1 = has a value"),
    ]
    hdus = [fits.PrimaryHDU()]
    for name, data, comment in cubes:
        hdu = fits.ImageHDU(data, header=header.copy(), name=name)
        hdu.header["COMMENT"] = comment
        hdus.append(hdu)
    nan = float("nan")
    table = fits.BinTableHDU.from_columns([
        fits.Column("OBS_ID", "40A", array=[c["obs_id"] for _, c, _ in rows]),
        fits.Column("MJD", "D", array=[c["mjd"] for _, c, _ in rows]),
        fits.Column("WL_UM", "D", array=[nan if c["wl_um"] is None else c["wl_um"] for _, c, _ in rows]),
        fits.Column("BW_UM", "D", array=[nan if c["bw_um"] is None else c["bw_um"] for _, c, _ in rows]),
        fits.Column("FRAME", "J", array=[i for i, _, _ in rows]),
    ], name="EXPOSURES")
    hdus.append(table)
    path = folder / "exposures.fits"
    fits.HDUList(hdus).writeto(path, overwrite=True)
    return path


def load_exposures(folder: Path) -> dict:
    with fits.open(folder / "exposures.fits") as hdul:
        table = hdul["EXPOSURES"].data
        return {
            "image": hdul["IMAGE"].data.astype(float),
            "sigma": hdul["SIGMA"].data.astype(float),
            "bad": hdul["FLAGGED"].data.astype(bool),
            "has_value": hdul["HAS_VALUE"].data.astype(bool),
            "obs_id": [str(s).strip() for s in table["OBS_ID"]],
            "mjd": np.array(table["MJD"], float),
            "wl_um": np.array(table["WL_UM"], float),
            "bw_um": np.array(table["BW_UM"], float),
            "frame": np.array(table["FRAME"], int),
        }


# ---------- photometry ----------

def ring_weights(shape: tuple, x: float, y: float, r_in: float, r_out: float) -> np.ndarray:
    """Fraction of each pixel with r_in <= distance < r_out from (x, y) (pixel centres at integers)."""
    sub = (np.arange(SUPERSAMPLE) + 0.5) / SUPERSAMPLE - 0.5
    yy, xx = np.indices(shape)
    dx = xx[..., None, None] + sub[None, None, None, :] - x
    dy = yy[..., None, None] + sub[None, None, :, None] - y
    r = np.hypot(dx, dy)
    return ((r >= r_in) & (r < r_out)).mean(axis=(-1, -2))


def measure(image, sigma, bad, has_value, x: float, y: float, r_in: float, r_out: float,
            sky_annulus: tuple = SKY_ANNULUS_PX) -> dict:
    """Light inside the ring r_in..r_out around (x, y), minus the median sky of sky_annulus, in mJy."""
    w = ring_weights(image.shape, x, y, r_in, r_out)
    sky_w = ring_weights(image.shape, x, y, *sky_annulus)
    inside = w > 0
    sky_pixels = image[(sky_w > 0.999) & has_value & ~bad & np.isfinite(image)]
    out = {"n_flagged": int((inside & bad).sum()), "flux_mjy": None, "err_mjy": None, "sky": None}
    if (inside & ~has_value).any() or len(sky_pixels) < 10:
        out["no_value"] = True
        return out
    sky = float(np.median(sky_pixels))
    sky_err = 1.4826 * float(np.median(np.abs(sky_pixels - sky))) * np.sqrt(np.pi / 2 / len(sky_pixels))
    total = float(np.sum(w * (image - sky), where=inside))
    var = float(np.sum((w * sigma) ** 2, where=inside)) + (float(w.sum()) * sky_err) ** 2
    out.update(no_value=False, sky=round(sky, 5),
               flux_mjy=total * MJY_PER_PIXEL_UNIT, err_mjy=float(np.sqrt(var)) * MJY_PER_PIXEL_UNIT)
    return out


def wing_radius(has_value: np.ndarray, track: list[tuple[float, float]]) -> float:
    """Inner radius of the wings ring: just outside the farthest no-value pixel near the star."""
    worst = 0.0
    for k, (x, y) in enumerate(track):
        yy, xx = np.indices(has_value[k].shape)
        r = np.hypot(xx - x, yy - y)
        holes = r[(~has_value[k]) & (r < SKY_ANNULUS_PX[0] - WING_WIDTH_PX)]
        if holes.size:
            worst = max(worst, float(holes.max()))
    return float(np.ceil(worst + 0.75))


# ---------- where the target is in each exposure ----------

def target_track(manifest: dict, gaia: dict | None, mjds: np.ndarray, simbad: dict | None = None):
    """(x, y) in FITS pixels for each exposure, and a sentence saying how it was found.

    Gaia match: Gaia's per-frame positions, extended in a straight line to each exposure's time.
    Else SIMBAD position and proper motion (simbad = resolve_name(...) answer), else the grid centre.
    """
    size = manifest["size_px"]
    frame_mjds = np.array([f["mjd"] for f in manifest["frames"]])
    target = next((s for s in (gaia or {}).get("stars", []) if s.get("target")), None)
    if target is not None and len(frame_mjds) > 1:
        xy = np.array(target["xy"])
        fx, fy = np.polyfit(frame_mjds, xy[:, 0], 1), np.polyfit(frame_mjds, size - 1 - xy[:, 1], 1)
        track = [(float(np.polyval(fx, t)), float(np.polyval(fy, t))) for t in mjds]
        return track, f"follows Gaia DR3 {target['source_id']} (proper motion, straight line)"
    if simbad and simbad.get("pmra") is not None and simbad.get("pmdec") is not None:
        grid, _ = target_grid(manifest["ra"], manifest["dec"], manifest["fov_arcmin"])
        track = []
        for t in mjds:
            ra, dec = position_at(simbad["ra"], simbad["dec"], simbad["pmra"], simbad["pmdec"], simbad["epoch"],
                                  2000.0 + (t - 51544.5) / 365.25)
            x, y = grid.world_to_pixel_values(ra, dec)
            track.append((float(x), float(y)))
        return track, f"follows SIMBAD {simbad.get('simbad_id', '')} proper motion (not in Gaia DR3)".replace("  ", " ")
    c = (size - 1) / 2
    return [(c, c)] * len(mjds), "fixed at the frame centre (no proper motion used)"


# ---------- comparing visits at the same wavelength ----------

def comparable(p: dict, allow_flagged: bool = False) -> bool:
    return (p["flux_mjy"] is not None and p["wl_um"] is not None and p["bw_um"] is not None
            and (allow_flagged or p["n_flagged"] == 0) and p["flux_mjy"] >= MIN_SNR * p["err_mjy"])


def wavelength_pairs(points: list[dict], allow_flagged: bool = False) -> list[tuple[int, int, float, float]]:
    """(frame a, frame b, flux b / flux a, wavelength gap) for every pair of comparable exposures of
    different visits whose wavelengths differ by less than SAME_WAVELENGTH x their bandwidth."""
    good = [p for p in points if comparable(p, allow_flagged)]
    out = []
    for i, p in enumerate(good):
        for q in good[i + 1:]:
            if p["frame"] == q["frame"]:
                continue
            if abs(p["wl_um"] - q["wl_um"]) >= SAME_WAVELENGTH * (p["bw_um"] + q["bw_um"]) / 2:
                continue
            a, b = (p, q) if p["mjd"] <= q["mjd"] else (q, p)
            out.append((a["frame"], b["frame"], b["flux_mjy"] / a["flux_mjy"], abs(p["wl_um"] - q["wl_um"])))
    return out


def log_scatter_pct(ratios) -> float | None:
    """Robust spread of ratios around their median, in % (1.4826 x MAD of the log)."""
    if len(ratios) < 3:
        return None
    logs = np.log(np.asarray(ratios))
    return round(float(np.expm1(1.4826 * np.median(np.abs(logs - np.median(logs))))) * 100, 1)


def visit_pairs(points: list[dict], allow_flagged: bool) -> list[dict]:
    by_pair: dict[tuple, list] = {}
    for fa, fb, ratio, gap in wavelength_pairs(points, allow_flagged):
        by_pair.setdefault((fa, fb), []).append((ratio, gap))
    pairs = []
    for (fa, fb), items in sorted(by_pair.items()):
        ratios = np.array([r for r, _ in items])
        pairs.append({"a": fa, "b": fb, "n": len(items), "median_ratio": round(float(np.median(ratios)), 3),
                      "min_ratio": round(float(ratios.min()), 3), "max_ratio": round(float(ratios.max()), 3),
                      "max_wl_gap_um": round(max(g for _, g in items), 4)})
    return pairs


def same_wavelength(points: list[dict]) -> dict:
    """Brightness ratios between visits, using only exposures at the same wavelength (the LVF rule).

    pairs: neither exposure has a flagged pixel in the aperture. pairs_incl_flagged: flagged allowed
    (more pairs, less certain).
    """
    return {"rule": f"two exposures of different visits are compared only if their wavelengths at the target "
                    f"differ by less than {SAME_WAVELENGTH} x their bandwidth and both are at least {MIN_SNR:g} "
                    "sigma; 'pairs' also needs no flagged pixel in either aperture",
            "n_excluded": sum(not comparable(p) for p in points),
            "n_excluded_incl_flagged": sum(not comparable(p, True) for p in points),
            "pairs": visit_pairs(points, False), "pairs_incl_flagged": visit_pairs(points, True)}


# ---------- field stars: how much does a star that should not change seem to change? ----------

def field_stars(gaia: dict | None, size: int, track_png: list[tuple[float, float]], r_out: float) -> list[dict]:
    """Isolated Gaia stars (G <= FIELD_MAX_G) far enough from the edge, the target and each other."""
    if not gaia:
        return []
    margin = CORE_RADIUS_PX + 1   # the aperture inside the frame; the sky ring may leave it (median of what is left)
    stars = [s for s in gaia["stars"] if s.get("g_mag") is not None]
    chosen = []
    for s in stars:
        if s.get("target") or s["g_mag"] > FIELD_MAX_G:
            continue
        xy = np.array(s["xy"])
        if not ((xy >= margin).all() and (xy <= size - 1 - margin).all()):
            continue
        tx, ty = track_png[0]
        if np.hypot(xy[0, 0] - tx, xy[0, 1] - ty) < max(r_out, CORE_RADIUS_PX) + FIELD_SKY_ANNULUS_PX[1]:
            continue
        crowded = any(o is not s and o["g_mag"] < s["g_mag"] + 3 and
                      np.hypot(o["xy"][0][0] - xy[0, 0], o["xy"][0][1] - xy[0, 1]) < FIELD_ISOLATION_PX
                      for o in stars)
        if not crowded:
            chosen.append(s)
    return chosen


def comparison(ex: dict, manifest: dict, gaia: dict | None, track_png: list[tuple[float, float]],
               r_out: float) -> dict:
    """Same-wavelength ratios of field stars measured like a core light curve: the noise floor."""
    size = manifest["size_px"]
    frame_mjds = np.array([f["mjd"] for f in manifest["frames"]])
    ratios, ratios_flagged, used = [], [], []
    for s in field_stars(gaia, size, track_png, r_out):
        xy = np.array(s["xy"])
        if len(frame_mjds) > 1:
            fx, fy = np.polyfit(frame_mjds, xy[:, 0], 1), np.polyfit(frame_mjds, size - 1 - xy[:, 1], 1)
            track = [(float(np.polyval(fx, t)), float(np.polyval(fy, t))) for t in ex["mjd"]]
        else:
            track = [(float(xy[0, 0]), float(size - 1 - xy[0, 1]))] * len(ex["mjd"])
        points = []
        for k, (x, y) in enumerate(track):
            m = measure(ex["image"][k], ex["sigma"][k], ex["bad"][k], ex["has_value"][k], x, y, 0.0,
                        CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX)
            points.append({"frame": int(ex["frame"][k]), "mjd": float(ex["mjd"][k]),
                           "wl_um": None if not np.isfinite(ex["wl_um"][k]) else float(ex["wl_um"][k]),
                           "bw_um": None if not np.isfinite(ex["bw_um"][k]) else float(ex["bw_um"][k]), **m})
        star_ratios = [r for _, _, r, _ in wavelength_pairs(points)]
        star_ratios_flagged = [r for _, _, r, _ in wavelength_pairs(points, True)]
        if star_ratios_flagged:
            ratios += star_ratios
            ratios_flagged += star_ratios_flagged
            used.append({"source_id": s["source_id"], "g_mag": s["g_mag"], "n_pairs": len(star_ratios),
                         "n_pairs_incl_flagged": len(star_ratios_flagged)})
    return {"rule": f"Gaia DR3 stars with G <= {FIELD_MAX_G:g}, no Gaia star less than 3 mag fainter within "
                    f"{FIELD_ISOLATION_PX:g} px, measured like the target (radius {CORE_RADIUS_PX:g} px, sky "
                    f"{FIELD_SKY_ANNULUS_PX[0]:g}-{FIELD_SKY_ANNULUS_PX[1]:g} px) with the same comparison rule",
            "n_stars": len(used),
            "n_pairs": len(ratios), "scatter_pct": log_scatter_pct(ratios),
            "median_ratio": round(float(np.median(ratios)), 3) if ratios else None,
            "n_pairs_incl_flagged": len(ratios_flagged), "scatter_pct_incl_flagged": log_scatter_pct(ratios_flagged),
            "median_ratio_incl_flagged": round(float(np.median(ratios_flagged)), 3) if ratios_flagged else None,
            "stars": used}


def neighbours(gaia: dict | None, track_png: list[tuple[float, float]], r_out: float) -> list[dict]:
    """Gaia stars whose light falls inside the aperture (within r_out + 1 px of the target)."""
    if not gaia:
        return []
    target = next((s for s in gaia["stars"] if s.get("target")), None)
    limit = (target["g_mag"] + NEIGHBOUR_G_LIMIT) if target and target.get("g_mag") is not None else 99
    tx, ty = track_png[len(track_png) // 2]
    out = []
    for s in gaia["stars"]:
        if s.get("target") or s.get("g_mag") is None or s["g_mag"] > limit:
            continue
        d = min(np.hypot(x - tx, y - ty) for x, y in s["xy"])
        if d < r_out + 1:
            out.append({"source_id": s["source_id"], "g_mag": s["g_mag"], "distance_px": round(float(d), 2)})
    return out


# ---------- light curve ----------

def lightcurve(ex: dict, manifest: dict, track: list[tuple[float, float]], position_rule: str,
               method: str | None = None, gaia: dict | None = None, check_wing_limit: bool = True) -> dict:
    """Measure every exposure at its track position; method 'core' or 'wings' (None: core unless saturated).

    Wings are used only with an inner radius <= MAX_WING_INNER_PX (the tested case); otherwise the
    answer has method 'none', a reason and no points.
    """
    n = len(ex["mjd"])
    size = manifest["size_px"]
    if method is None:
        core_holes = any((ring_weights(ex["image"][k].shape, *track[k], 0, CORE_RADIUS_PX) > 0)[~ex["has_value"][k]].any()
                         for k in range(n))
        method = "wings" if core_holes else "core"
    reason = None
    if method == "core":
        r_in, r_out = 0.0, CORE_RADIUS_PX
    else:
        r_in = wing_radius(ex["has_value"], track)
        r_out = r_in + WING_WIDTH_PX
        if check_wing_limit and r_in > MAX_WING_INNER_PX:
            reason = (f"The star's saturated (no-value) core reaches {r_in - 0.75:.1f} px from its centre in at least "
                      f"one exposure. Measuring the light around it would need a ring starting at {r_in:g} px, and "
                      f"only rings starting at most {MAX_WING_INNER_PX:g} px out were checked to follow a star's "
                      "brightness (RW Aur, 3-6 px: about 10%). So no light curve is given.")
    track_png = [(x, size - 1 - y) for x, y in track]
    base = {
        "format": FORMAT, "target": manifest["target"], "label": manifest["label"], "band": manifest["band"],
        "unit": "mJy", "position_rule": position_rule,
        "made_by": "backend/app/lightcurve.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx" + (", ESA Gaia DR3" if gaia else ""),
    }
    if reason:
        return {**base, "method": "none", "reason": reason, "points": [],
                "comparison": comparison(ex, manifest, gaia, track_png, CORE_RADIUS_PX)}
    points = []
    for k in range(n):
        x, y = track[k]
        m = measure(ex["image"][k], ex["sigma"][k], ex["bad"][k], ex["has_value"][k], x, y, r_in, r_out)
        frame = int(ex["frame"][k])
        wl = None if not np.isfinite(ex["wl_um"][k]) else round(float(ex["wl_um"][k]), 4)
        bw = None if not np.isfinite(ex["bw_um"][k]) else round(float(ex["bw_um"][k]), 4)
        points.append({
            "obs_id": ex["obs_id"][k], "mjd": round(float(ex["mjd"][k]), 5),
            "date_iso": mjd_to_date(float(ex["mjd"][k]))[:16].replace("T", " ") + " UTC",
            "frame": frame, "epoch_id": manifest["frames"][frame]["epoch_id"], "wl_um": wl, "bw_um": bw,
            "x": round(x, 3), "y": round(manifest["size_px"] - 1 - y, 3),   # PNG pixels, like gaia.json
            "flux_mjy": None if m["flux_mjy"] is None else round(m["flux_mjy"], 4),
            "err_mjy": None if m["err_mjy"] is None else round(m["err_mjy"], 4),
            "n_flagged": m["n_flagged"], "no_value": m["no_value"], "sky": m["sky"],
        })
    what = (f"light inside a circle of radius {r_out:g} px ({r_out * PIXEL_SCALE_ARCSEC:.1f}″)" if method == "core"
            else f"light in a ring {r_in:g}-{r_out:g} px from the star, outside its saturated (no-value) core")
    return {
        **base, "method": method, "r_in_px": r_in, "r_out_px": r_out, "sky_annulus_px": list(SKY_ANNULUS_PX),
        "method_text": f"{what}, minus the median sky {SKY_ANNULUS_PX[0]:g}-{SKY_ANNULUS_PX[1]:g} px away, in every "
                       "exposure behind the frames (IMAGE - ZODI, reprojected onto the frames grid). No aperture "
                       "correction: compare points with each other, not with catalogues." +
                       (" A ring around a saturated core follows the star's brightness only while the PSF keeps "
                        "its shape: on RW Aur (not saturated) a 3-6 px ring followed the core to about 10%."
                        if method == "wings" else ""),
        "error_text": "1 sigma from VARIANCE (pixels treated as independent, so a lower limit after "
                      "reprojection) plus the sky uncertainty",
        "points": points,
        "same_wavelength": same_wavelength(points),
        "comparison": comparison(ex, manifest, gaia, track_png, r_out) if method == "core" else None,
        "neighbours": neighbours(gaia, track_png, r_out),
    }


def target_simbad(manifest: dict) -> dict | None:
    """SIMBAD answer for an official target (for its proper motion), or None."""
    from backend.app.resolve import resolve_name
    from backend.app.targets import OFFICIAL_TARGETS
    target = next((t for t in OFFICIAL_TARGETS if t["key"] == manifest["target"]), None)
    return resolve_name(target["simbad"]) if target else None


def write_lightcurve(folder: Path, simbad: dict | None = None) -> dict:
    """exposures.fits (if missing) and lightcurve.json for the target of a frames folder."""
    manifest = json.loads((folder / "manifest.json").read_text())
    if not (folder / "exposures.fits").exists():
        write_exposures(folder)
    ex = load_exposures(folder)
    gaia_path = folder / "gaia.json"
    gaia = json.loads(gaia_path.read_text()) if gaia_path.exists() else None
    if simbad is None and not (gaia and gaia.get("target_match")):
        simbad = target_simbad(manifest)
    track, rule = target_track(manifest, gaia, ex["mjd"], simbad)
    lc = lightcurve(ex, manifest, track, rule, gaia=gaia)
    (folder / "lightcurve.json").write_text(json.dumps(lc, indent=1, ensure_ascii=False) + "\n")
    return lc


def lightcurve_at(folder: Path, x_png: float, y_png: float) -> dict:
    """Light curve of a fixed sky position given in PNG pixels (for a click on the flipbook)."""
    manifest = json.loads((folder / "manifest.json").read_text())
    ex = load_exposures(folder)
    gaia_path = folder / "gaia.json"
    gaia = json.loads(gaia_path.read_text()) if gaia_path.exists() else None
    size = manifest["size_px"]
    track = [(float(x_png), float(size - 1 - y_png))] * len(ex["mjd"])
    return lightcurve(ex, manifest, track, f"fixed at pixel ({x_png:g}, {y_png:g}), the clicked position "
                                           "(not moved for proper motion)", gaia=gaia)


def check_wings(lc_core: dict, lc_wings: dict) -> dict:
    """How well wings follow the core on an unsaturated star: scatter of wings/core between exposures."""
    ratios = [w["flux_mjy"] / c["flux_mjy"] for c, w in zip(lc_core["points"], lc_wings["points"])
              if c["flux_mjy"] and w["flux_mjy"] and c["flux_mjy"] > 0 and c["n_flagged"] == 0 and w["n_flagged"] == 0]
    r = np.array(ratios)
    return {"n": len(r), "median": round(float(np.median(r)), 4),
            "scatter_pct": round(float(1.4826 * np.median(np.abs(r - np.median(r))) / np.median(r) * 100), 1),
            "min": round(float(r.min()), 4), "max": round(float(r.max()), 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", type=Path, nargs="+")
    parser.add_argument("--rebuild-exposures", action="store_true", help="write exposures.fits again")
    args = parser.parse_args()
    for folder in args.folders:
        if args.rebuild_exposures or not (folder / "exposures.fits").exists():
            write_exposures(folder)
        lc = write_lightcurve(folder)
        if lc["method"] == "none":
            print(f"{folder}: no light curve. {lc['reason']}")
            continue
        good = [p for p in lc["points"] if p["flux_mjy"] is not None]
        sw, comp = lc["same_wavelength"], lc["comparison"]
        print(f"{folder}: {lc['method']} r {lc['r_in_px']}-{lc['r_out_px']} px, {len(good)}/{len(lc['points'])} "
              f"exposures measured, {sw['n_excluded']} not comparable; {lc['position_rule']}")
        if comp:
            print(f"  field stars: {comp['n_stars']} stars; clean: {comp['n_pairs']} pairs, ratio "
                  f"{comp['median_ratio']}, scatter {comp['scatter_pct']}%; incl. flagged: "
                  f"{comp['n_pairs_incl_flagged']} pairs, ratio {comp['median_ratio_incl_flagged']}, "
                  f"scatter {comp['scatter_pct_incl_flagged']}%")
        for nb in lc["neighbours"]:
            print(f"  neighbour inside the aperture: Gaia DR3 {nb['source_id']} G {nb['g_mag']} at {nb['distance_px']} px")
        for tier in ("pairs", "pairs_incl_flagged"):
            for p in sw[tier]:
                print(f"  {tier}: visit {p['a']} -> {p['b']}: {p['n']} same-wavelength pairs, ratio "
                      f"{p['median_ratio']} ({p['min_ratio']}-{p['max_ratio']})")


if __name__ == "__main__":
    main()
