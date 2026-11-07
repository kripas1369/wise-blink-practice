"""Planted-mover test (recovery.json): how often the 5σ spot finder finds a moving source of known brightness.

    python -m backend.app.recovery frontend/frames/*/d*

For every pair of visits in diff.json, copies of the two real frames (epoch<i>.fits) get fake point sources:
the same brightness in A and in B, STEP_PX apart (a source that moved). The difference is made again with
diff.difference and searched with the spot list's own rule (spots.groups, |z| >= 5). A fake is found when a
brighter-in-B spot has its centre within FOUND_PX of the fake's B position; "both ends" also needs the
fainter-in-B spot at its A position. Brightness is set as the fake's peak in the difference map in sigma of the
noise at that pixel (peak S/N), and turned into mJy and AB magnitude with the frames' PSF width.

What it measures: the spot finder on these frames' real noise, flags, no-value pixels and star residuals.
What it does not: the fake is added after the exposures were lined up and added up (it skips that smoothing),
and it has no photon noise of its own, so faint-source numbers are slightly optimistic.
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.special import erf

from backend.app.diff import difference, load_frame
from backend.app.lightcurve import MJY_PER_PIXEL_UNIT
from backend.app.spectrum import psf_fwhm
from backend.app.spots import groups

FORMAT = "spherex-blink-recovery/1"
LEVELS = (0, 3, 4, 5, 6, 8, 12, 20)   # peak S/N in the difference map; 0 = nothing planted (chance matches)
PER_LEVEL = 200
PER_TRIAL = 4
STEP_PX = 4.0                     # ours: far enough apart that the two ends do not overlap
FOUND_PX = 1.5                    # the same distance as the spot list's "near a Gaia star"
SEPARATION_PX = 6.0
SEED = 20261107
PSF_BOX_PX = 3.0
PSF_SKY_PX = (4.0, 7.0)
PSF_MIN_SNR = 20.0
PSF_MAX_G = 16.5
PSF_NEIGHBOUR_PX = 4.0            # no Gaia star less than 2.5 mag fainter this close
PSF_MIN_STARS = 5
BILINEAR_VARIANCE_PX2 = 1 / 6     # per axis, added by reproject_interp's bilinear resampling onto the grid
AB_ZERO_MJY = 16.40               # AB = 16.40 - 2.5 log10(flux in mJy)  (3631 Jy zero point)


def pixel_psf(x: float, y: float, s: float, shape: tuple[int, int]):
    """Fraction of a Gaussian (sigma s px) centred at column x, row y that falls in each pixel near it."""
    r = int(math.ceil(4 * s)) + 1
    k = math.sqrt(2) * s

    def axis(c: float, n: int):
        idx = np.arange(math.floor(c) - r, math.floor(c) + r + 2)
        f = 0.5 * (erf((idx + 0.5 - c) / k) - erf((idx - 0.5 - c) / k))
        keep = (idx >= 0) & (idx < n)
        return idx[keep], f[keep], float(f.max())

    rows, fy, peak_y = axis(y, shape[0])
    cols, fx, peak_x = axis(x, shape[1])
    return rows, cols, np.outer(fy, fx), peak_y * peak_x


def plant(image: np.ndarray, x: float, y: float, flux: float, s: float) -> None:
    rows, cols, frac, _ = pixel_psf(x, y, s, image.shape)
    if len(rows) and len(cols):
        image[np.ix_(rows, cols)] += flux * frac


def star_sigma(frame: dict, x: float, y: float) -> float | None:
    """Gaussian sigma (px) of one star from its second moments, or None when it is not clean enough."""
    image, sigma, usable = frame["image"], frame["sigma"], frame["usable"]
    yy, xx = np.indices(image.shape)
    r = np.hypot(xx - x, yy - y)
    core, sky = r <= PSF_BOX_PX, (r >= PSF_SKY_PX[0]) & (r <= PSF_SKY_PX[1])
    if not core.any() or not usable[core].all() or usable[sky].sum() < 10:
        return None
    w = np.clip(image - np.median(image[sky & usable]), 0, None) * core
    peak = np.unravel_index(np.argmax(w), w.shape)
    if w[peak] < PSF_MIN_SNR * sigma[peak] or w.sum() <= 0:
        return None
    cx, cy = (w * xx).sum() / w.sum(), (w * yy).sum() / w.sum()
    var = ((w * ((xx - cx) ** 2 + (yy - cy) ** 2)).sum() / w.sum()) / 2 - 1 / 12   # minus one pixel's width
    return math.sqrt(var) if var > 0 else None


def measure_psf(folder: Path, manifest: dict, frames: dict, gaia: dict | None) -> dict:
    """PSF width on the frames grid from clean Gaia stars; else the exposures' PSF_FWHM header (labelled)."""
    size = manifest["size_px"]
    values = []
    if gaia:
        for i, f in enumerate(gaia["frames"]):
            frame = frames.get(f["epoch_id"])
            if frame is None:
                continue
            for s in gaia["stars"]:
                if s["g_mag"] is None or s["g_mag"] > PSF_MAX_G:
                    continue
                x, y_png = s["xy"][i]
                crowded = any(o is not s and o["g_mag"] is not None and o["g_mag"] < s["g_mag"] + 2.5
                              and math.hypot(o["xy"][i][0] - x, o["xy"][i][1] - y_png) < PSF_NEIGHBOUR_PX
                              for o in gaia["stars"])
                if not crowded and 4 <= x <= size - 5 and 4 <= y_png <= size - 5:
                    v = star_sigma(frame, x, size - 1 - y_png)
                    if v is not None:
                        values.append(v)
    pixel = manifest["pixel_arcsec"]
    if len(values) >= PSF_MIN_STARS:
        s = float(np.median(values))
        return {"sigma_px": round(s, 3), "fwhm_arcsec": round(2.3548 * s * pixel, 2), "n_stars": len(values),
                "source": f"second moments of {len(values)} star images on these frames (Gaia G <= {PSF_MAX_G:g}, "
                          f"no brighter neighbour within {PSF_NEIGHBOUR_PX:g} px, peak above {PSF_MIN_SNR:g}σ)"}
    obs_ids = [str(o).strip() for o in fits.getdata(folder / "exposures.fits", "EXPOSURES")["OBS_ID"]]
    header = psf_fwhm(obs_ids, manifest["band"])
    if header is None:
        raise ValueError("fewer than 5 clean stars and no PSF_FWHM header to set the fakes' width")
    s = math.sqrt((header["median_arcsec"] / 2.3548 / pixel) ** 2 + BILINEAR_VARIANCE_PX2)
    return {"sigma_px": round(s, 3), "fwhm_arcsec": round(2.3548 * s * pixel, 2), "n_stars": len(values),
            "source": f"median PSF_FWHM of the exposures' headers ({header['median_arcsec']}″), widened by the bilinear "
                      f"resampling onto this grid (+1/6 px² per axis); fewer than {PSF_MIN_STARS} clean stars to "
                      "measure it here"}


def positions(rng: np.random.Generator, size: int, n: int) -> list[tuple[float, float, float, float]]:
    """n fakes as (xB, yB, xA, yA) inside the frame, every end at least SEPARATION_PX from the other fakes' ends."""
    out: list[tuple[float, float, float, float]] = []
    for _ in range(1000):
        if len(out) == n:
            break
        xb, yb = rng.uniform(0, size - 1, 2)
        angle = rng.uniform(0, 2 * math.pi)
        xa, ya = xb - STEP_PX * math.cos(angle), yb - STEP_PX * math.sin(angle)
        if not (0 <= xa <= size - 1 and 0 <= ya <= size - 1):
            continue
        ends = [(xb, yb), (xa, ya)]
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= SEPARATION_PX for o in out
               for p in ends for q in ((o[0], o[1]), (o[2], o[3]))):
            out.append((xb, yb, xa, ya))
    return out


def centres(z: np.ndarray, limit: float) -> list[tuple[int, np.ndarray, float, float]]:
    zz = np.nan_to_num(z)
    out = []
    for sign, mask in groups(zz, limit):
        ys, xs = np.nonzero(mask)
        w = np.abs(zz[mask])
        out.append((sign, mask, float((w * xs).sum() / w.sum()), float((w * ys).sum() / w.sum())))
    return out


def run_level(a: dict, b: dict, level: float, psf_sigma: float, limit: float, rng: np.random.Generator) -> dict:
    size = a["image"].shape[0]
    sigma_d = np.sqrt(a["sigma"] ** 2 + b["sigma"] ** 2)
    valid = a["usable"] & b["usable"]
    typical = float(np.median(sigma_d[valid]))
    counts = {"n": 0, "found": 0, "both": 0, "no_z": 0, "blended": 0, "too_faint": 0}
    peaks = []
    while counts["n"] < PER_LEVEL:
        fakes = positions(rng, size, min(PER_TRIAL, PER_LEVEL - counts["n"]))
        ia, ib = a["image"].copy(), b["image"].copy()
        for xb, yb, xa, ya in fakes:
            sd = sigma_d[round(yb), round(xb)]
            _, _, _, peak = pixel_psf(xb, yb, psf_sigma, ia.shape)
            peaks.append(peak)
            flux = level * (sd if np.isfinite(sd) else typical) / peak
            plant(ib, xb, yb, flux, psf_sigma)
            plant(ia, xa, ya, flux, psf_sigma)
        d = difference({**a, "image": ia}, {**b, "image": ib})
        spots = centres(d["z"], limit)
        for xb, yb, xa, ya in fakes:
            counts["n"] += 1
            near = lambda sign, x, y: any(s == sign and math.hypot(cx - x, cy - y) <= FOUND_PX for s, _, cx, cy in spots)
            if near(1, xb, yb):
                counts["found"] += 1
                counts["both"] += near(-1, xa, ya)
            elif not valid[round(yb), round(xb)]:
                counts["no_z"] += 1
            elif any(s == 1 and m[round(yb), round(xb)] for s, m, _, _ in spots):
                counts["blended"] += 1
            else:
                counts["too_faint"] += 1
    n = counts["n"]
    row = {"peak_sigma": level, "n": n,
           "found_pct": round(100 * counts["found"] / n, 1), "both_ends_pct": round(100 * counts["both"] / n, 1),
           "lost": {"no_z_pct": round(100 * counts["no_z"] / n, 1), "blended_pct": round(100 * counts["blended"] / n, 1),
                    "too_faint_pct": round(100 * counts["too_faint"] / n, 1)}}
    if level > 0:
        flux_mjy = level * typical / float(np.median(peaks)) * MJY_PER_PIXEL_UNIT
        row.update(flux_mjy=round(flux_mjy, 4), ab_mag=round(AB_ZERO_MJY - 2.5 * math.log10(flux_mjy), 2))
    return row


def half_found(rows: list[dict]) -> dict | None:
    """Where the found share crosses 50%, by straight lines between the planted levels."""
    planted = [r for r in rows if r["peak_sigma"] > 0]
    for lo, hi in zip(planted, planted[1:]):
        if lo["found_pct"] < 50 <= hi["found_pct"]:
            t = (50 - lo["found_pct"]) / (hi["found_pct"] - lo["found_pct"])
            level = lo["peak_sigma"] + t * (hi["peak_sigma"] - lo["peak_sigma"])
            flux = lo["flux_mjy"] * level / lo["peak_sigma"]
            return {"peak_sigma": round(level, 1), "flux_mjy": round(flux, 4),
                    "ab_mag": round(AB_ZERO_MJY - 2.5 * math.log10(flux), 2)}
    if planted and planted[0]["found_pct"] >= 50:
        return {"below_lowest": planted[0]["peak_sigma"]}
    return None


def build_recovery(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    diff = json.loads((folder / "diff.json").read_text())
    gaia_path = folder / "gaia.json"
    gaia = json.loads(gaia_path.read_text()) if gaia_path.exists() else None
    frames = {f["epoch_id"]: load_frame(folder / f["fits"]) for f in manifest["frames"]}
    psf = measure_psf(folder, manifest, frames, gaia)
    limit = diff["limit_sigma"]
    pairs = []
    for k, pair in enumerate(diff["pairs"]):
        rng = np.random.default_rng(SEED + k)
        rows = [run_level(frames[pair["a"]], frames[pair["b"]], level, psf["sigma_px"], limit, rng) for level in LEVELS]
        wls = [w for w in (pair["wl_a_um"], pair["wl_b_um"]) if w is not None]
        pairs.append({"a": pair["a"], "b": pair["b"], "wl_um": round(sum(wls) / len(wls), 3) if wls else None,
                      "levels": rows, "half_found": half_found(rows)})
    return {
        "format": FORMAT, "target": manifest["target"], "band": manifest["band"], "limit_sigma": limit,
        "rules": {"levels_peak_sigma": list(LEVELS), "per_level": PER_LEVEL, "step_px": STEP_PX, "found_px": FOUND_PX,
                  "fakes_per_map": PER_TRIAL, "separation_px": SEPARATION_PX, "seed": SEED, "source": "ours"},
        "psf": psf,
        "method": "fake moving point sources (same brightness in A and B, "
                  f"{STEP_PX:g} px apart) added to copies of the two frames; difference and {limit:g}σ spots made "
                  "with the same code as the difference panel and spot list; found = a brighter-in-B spot centred "
                  f"within {FOUND_PX:g} px of the fake",
        "limits": [
            "The fakes are added after the exposures were lined up and added up, so they skip that smoothing.",
            "The fakes have no photon noise of their own, so the faintest levels are slightly optimistic.",
            "mJy and AB magnitude use the typical noise of the pair and the PSF width above; at one place the "
            "noise can be higher (bright stars) or lower.",
            "Level 0 plants nothing: it is the chance that a real spot sits within "
            f"{FOUND_PX:g} px of a random place anyway.",
        ],
        "pairs": pairs,
        "made_by": "backend/app/recovery.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def write_recovery(folder: Path) -> dict:
    result = build_recovery(Path(folder))
    (Path(folder) / "recovery.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path, help="e.g. frontend/frames/barnard/d2")
    args = parser.parse_args()
    for folder in args.folders:
        r = write_recovery(folder)
        p = r["psf"]
        print(f"{folder}: PSF {p['fwhm_arcsec']}″ ({p['n_stars']} stars)")
        for pair in r["pairs"]:
            line = " ".join(f"{row['peak_sigma']:g}σ:{row['found_pct']:.0f}%" for row in pair["levels"])
            print(f"  {pair['a']}->{pair['b']}  {line}  half found: {pair['half_found']}")


if __name__ == "__main__":
    main()
