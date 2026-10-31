"""Step 2b, part 2: difference images, visit B minus visit A, measured in sigma.

For every pair of visits in a frames folder:
    z = (B − A − sky change) / sqrt(sigma_A² + sigma_B²)
sigma comes from the files' VARIANCE (epoch<i>.fits). "sky change" is one number: the median of B − A
over the usable pixels, so a small change in the leftover sky level does not paint the whole panel.
The pixel scatter of z (1.4826 × MAD) is given next to it: if VARIANCE describes the noise well it is
close to 1. Pixels that are flagged or have no value in either visit get no z (shown striped).

Each SPHEREx exposure sees its own wavelength (LVF), so a pair with different wavelengths leaves a
residual on every star; the pair with the closest wavelength at the target is the default.

    python -m backend.app.diff frontend/frames/barnard/d2    # writes diff.json and diff_<a>_<b>.png
"""
import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from PIL import Image

FORMAT = "spherex-blink-diff/1"
LIMIT_SIGMA = 5.0
BRIGHTER = np.array([255, 110, 40])   # B brighter than A
FAINTER = np.array([70, 140, 255])    # B fainter than A
ZERO = np.array([18, 20, 26])


def load_frame(path: Path) -> dict:
    with fits.open(path) as hdul:
        image = hdul["IMAGE"].data.astype(float)
        sigma = hdul["SIGMA"].data.astype(float)
        flagged = hdul["FLAGGED"].data.astype(bool)
        has_value = hdul["HAS_VALUE"].data.astype(bool)
    usable = has_value & ~flagged & np.isfinite(image) & np.isfinite(sigma) & (sigma > 0)
    return {"image": image, "sigma": sigma, "flagged": flagged, "usable": usable}


def robust_scatter(values: np.ndarray) -> float:
    return 1.4826 * float(np.median(np.abs(values - np.median(values))))


def difference(a: dict, b: dict) -> dict:
    """z map of B − A and its numbers. Arrays keep FITS row order (south first)."""
    valid = a["usable"] & b["usable"]
    if not valid.any():
        raise ValueError("The two visits have no usable pixel in common")
    raw = b["image"] - a["image"]
    sky_change = float(np.median(raw[valid]))
    with np.errstate(invalid="ignore"):
        z = np.where(valid, (raw - sky_change) / np.sqrt(a["sigma"] ** 2 + b["sigma"] ** 2), np.nan)
    flagged = ~valid & (a["flagged"] | b["flagged"])
    n = valid.size
    imax, imin = np.nanargmax(z), np.nanargmin(z)
    return {
        "z": z,
        "valid": valid,
        "flagged": flagged,
        "sky_change": sky_change,
        "scatter": robust_scatter(z[valid]),
        "max": (float(z.flat[imax]), np.unravel_index(imax, z.shape)),
        "min": (float(z.flat[imin]), np.unravel_index(imin, z.shape)),
        "pct_valid": round(100 * valid.sum() / n, 1),
        "pct_flagged": round(100 * flagged.sum() / n, 1),
        "pct_no_value": round(100 * (~valid & ~flagged).sum() / n, 1),
    }


def colour(z: np.ndarray) -> np.ndarray:
    """RGBA, north up: dark at 0, orange where B is brighter, blue where fainter, clipped at ±LIMIT_SIGMA;
    transparent where there is no z (the website stripes those pixels)."""
    t = np.clip(np.nan_to_num(z) / LIMIT_SIGMA, -1, 1)[..., None]
    rgb = np.where(t >= 0, ZERO + t * (BRIGHTER - ZERO), ZERO + (-t) * (FAINTER - ZERO))
    rgba = np.zeros(z.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = np.round(rgb).astype(np.uint8)
    rgba[..., 3] = np.where(np.isfinite(z), 255, 0)
    return np.flipud(rgba)


def png_xy(index: tuple, size: int) -> list[int]:
    """(row, col) in FITS order -> [x, y] in PNG pixels (north at the top)."""
    row, col = index
    return [int(col), int(size - 1 - row)]


def rows_north_first(values: np.ndarray, digits: int) -> list[list]:
    return [[None if not np.isfinite(v) else round(float(v), digits) for v in row] for row in values[::-1]]


def wavelength_gap(fa: dict, fb: dict) -> float | None:
    if fa.get("wl_target_um") is None or fb.get("wl_target_um") is None:
        return None
    return round(abs(fb["wl_target_um"] - fa["wl_target_um"]), 4)


def default_pair(pairs: list[dict]) -> dict:
    """Closest wavelength at the target; if equal, the longer time apart (more motion)."""
    known = [p for p in pairs if p["wl_gap_um"] is not None]
    if not known:
        best = max(pairs, key=lambda p: p["days"])
        return {"a": best["a"], "b": best["b"], "reason": "wavelengths unknown, so the two visits furthest apart"}
    best = min(known, key=lambda p: (p["wl_gap_um"], -p["days"]))
    return {"a": best["a"], "b": best["b"],
            "reason": f"closest mean wavelength at the target ({best['wl_gap_um']:.3f} µm apart)"}


def write_diff(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    frames = manifest["frames"]
    if any("fits" not in f for f in frames):
        raise SystemExit(f"{folder}: no epoch<i>.fits yet; run python -m backend.app.rebuild {folder}")
    size = manifest["size_px"]
    data = {f["epoch_id"]: load_frame(folder / f["fits"]) for f in frames}
    for old in folder.glob("diff_*.png"):
        old.unlink()

    pairs = []
    for fa, fb in itertools.combinations(frames, 2):
        a, b = data[fa["epoch_id"]], data[fb["epoch_id"]]
        d = difference(a, b)
        png = f"diff_{fa['epoch_id']}_{fb['epoch_id']}.png"
        Image.fromarray(colour(d["z"]), "RGBA").save(folder / png)
        pairs.append({
            "a": fa["epoch_id"], "b": fb["epoch_id"], "png": png,
            "days": round(fb["mjd"] - fa["mjd"], 1),
            "wl_a_um": fa.get("wl_target_um"), "wl_b_um": fb.get("wl_target_um"),
            "wl_gap_um": wavelength_gap(fa, fb),
            "sky_change": round(d["sky_change"], 5),
            "scatter_sigma": round(d["scatter"], 2),
            "max_sigma": round(d["max"][0], 1), "max_xy": png_xy(d["max"][1], size),
            "min_sigma": round(d["min"][0], 1), "min_xy": png_xy(d["min"][1], size),
            "pct_valid": d["pct_valid"], "pct_flagged": d["pct_flagged"], "pct_no_value": d["pct_no_value"],
            "z": rows_north_first(d["z"], 2),
        })

    def state(f):
        return ["".join("o" if u else ("f" if fl else "n") for u, fl in zip(ur, flr))
                for ur, flr in zip(f["usable"][::-1], f["flagged"][::-1])]

    diff = {
        "format": FORMAT,
        "target": manifest["target"],
        "band": manifest["band"],
        "size_px": size,
        "row_order": "north first, x to the right (west): the same as the PNGs",
        "unit": "MJy/sr",
        "limit_sigma": LIMIT_SIGMA,
        "colours": {"brighter": "#%02x%02x%02x" % tuple(BRIGHTER), "fainter": "#%02x%02x%02x" % tuple(FAINTER),
                    "zero": "#%02x%02x%02x" % tuple(ZERO)},
        "method": "z = (B − A − sky change) / sqrt(sigma_A² + sigma_B²), sigma from VARIANCE; sky change = "
                  "median of B − A over pixels usable in both; no z where either visit is flagged or has no value",
        "frames": [{"epoch_id": f["epoch_id"],
                    "value": rows_north_first(data[f["epoch_id"]]["image"], 4),
                    "sigma": rows_north_first(data[f["epoch_id"]]["sigma"], 4),
                    "state": state(data[f["epoch_id"]])} for f in frames],
        "state_codes": {"o": "usable", "f": "flagged bad", "n": "no value"},
        "pairs": pairs,
        "default_pair": default_pair(pairs),
        "made_by": "backend/app/diff.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    (folder / "diff.json").write_text(json.dumps(diff, separators=(",", ":"), ensure_ascii=False) + "\n")
    return diff


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", type=Path, nargs="+", help="e.g. frontend/frames/barnard/d2")
    args = parser.parse_args()
    for folder in args.folders:
        d = write_diff(folder)
        print(f"{folder}: default pair {d['default_pair']}")
        for p in d["pairs"]:
            print(f"  {p['a']}->{p['b']} {p['days']:6.1f} d  wl gap {p['wl_gap_um']}  sky {p['sky_change']:+.4f}  "
                  f"scatter {p['scatter_sigma']}  max {p['max_sigma']} at {p['max_xy']}  "
                  f"min {p['min_sigma']} at {p['min_xy']}  flagged {p['pct_flagged']}%  none {p['pct_no_value']}%")


if __name__ == "__main__":
    main()
