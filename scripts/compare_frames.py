"""Compare two frame folders that follow docs/plan/FRAMES_FORMAT.md.

Used to check the data pipeline against Kripas's sample frames (or any two runs):
    python -m scripts.compare_frames frontend/frames/barnard/d2 scratch/frames/barnard/d2

Checks: same sky grid (centre, pixel size, image size, orientation); the same visits (by time);
then, per visit, the pictures. Two frames made from the same exposure should be almost identical;
add-ups of many exposures should still look alike (high correlation) but be less noisy.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

CENTRE_TOLERANCE_ARCSEC = 0.1
SAME_VISIT_DAYS = 2.0


def load(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("format") != "spherex-blink-frames/1":
        raise SystemExit(f"{folder}: unknown format {manifest.get('format')!r}")
    return manifest


def picture(folder: Path, png: str) -> tuple[np.ndarray, np.ndarray]:
    """Grey values 0-255 and a mask of pixels that have a value (alpha > 0)."""
    rgba = np.asarray(Image.open(folder / png).convert("RGBA"), dtype=float)
    return rgba[..., 0], rgba[..., 3] > 0


def separation_arcsec(ra1, dec1, ra2, dec2) -> float:
    d_ra = (ra1 - ra2) * math.cos(math.radians((dec1 + dec2) / 2))
    return math.hypot(d_ra, dec1 - dec2) * 3600


def compare(a_dir: Path, b_dir: Path) -> list[str]:
    a, b = load(a_dir), load(b_dir)
    problems = []
    print(f"A: {a_dir}  ({a['made_by']}, mode {a['mode']}, {len(a['frames'])} frames)")
    print(f"B: {b_dir}  ({b['made_by']}, mode {b['mode']}, {len(b['frames'])} frames)")

    sep = separation_arcsec(a["ra"], a["dec"], b["ra"], b["dec"])
    print(f"grid centre differs by {sep:.3f}″")
    if sep > CENTRE_TOLERANCE_ARCSEC:
        problems.append(f"grid centres differ by {sep:.3f}″ (more than {CENTRE_TOLERANCE_ARCSEC}″)")
    for key in ("band", "size_px", "pixel_arcsec", "orientation"):
        if a[key] != b[key]:
            problems.append(f"{key}: A has {a[key]!r}, B has {b[key]!r}")
    if problems:
        return problems  # different grids: comparing pixels would mean nothing

    for fa in a["frames"]:
        fb = min(b["frames"], key=lambda f: abs(f["mjd"] - fa["mjd"]))
        if abs(fb["mjd"] - fa["mjd"]) > SAME_VISIT_DAYS:
            problems.append(f"A visit {fa['date_iso']} has no B frame within {SAME_VISIT_DAYS} days")
            continue
        ga, ma = picture(a_dir, fa["png"])
        gb, mb = picture(b_dir, fb["png"])
        both = ma & mb
        same_exposure = fa.get("obs_id") and fa.get("obs_id") == fb.get("obs_id")
        diff = np.abs(ga[both] - gb[both])
        corr = float(np.corrcoef(ga[both], gb[both])[0, 1]) if both.sum() > 2 else float("nan")
        print(f"  {fa['date_iso'][:10]}: n_images A {fa['n_images']} / B {fb['n_images']}, "
              f"grey difference median {np.median(diff):.1f} max {diff.max():.0f} (of 255), "
              f"correlation {corr:.3f}, flagged A {fa['pct_flagged']}% / B {fb['pct_flagged']}%")
        if same_exposure and np.median(diff) > 1:
            problems.append(f"{fa['date_iso'][:10]}: same exposure but pictures differ (median {np.median(diff):.1f})")
        if corr < 0.8:
            problems.append(f"{fa['date_iso'][:10]}: pictures do not look alike (correlation {corr:.2f})")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    args = parser.parse_args()
    problems = compare(args.a, args.b)
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("\nOK: same grid, same visits, pictures agree.")


if __name__ == "__main__":
    main()
