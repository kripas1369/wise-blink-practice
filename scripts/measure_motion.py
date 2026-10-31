"""Measured position of the target in each visit, compared with Gaia. Works offline on a frames folder.

Needs epoch<i>.fits (rebuild.py / render.py) and gaia.json (gaia.py). For each visit it measures:
    centroid  = brightness-weighted centre of the 5 × 5 pixels around Gaia's predicted position,
                after removing the median sky of the frame; only if all 25 pixels are usable
    hole      = centre of the flagged / no-value pixels within 3 px of the prediction (a saturated core
                is centred on the star, so this is a rough position for very bright stars)
and prints the shift from the first visit next to Gaia's shift, in pixels (+x = west, +y = south,
PNG convention). SPHEREx pixels are 6.15″ and the PSF is about one pixel wide, so a centroid moves by
less than the star when the star is not centred on a pixel (pixel phase); treat these as rough.

    python -m scripts.measure_motion frontend/frames/eps_ind_b/d2
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from backend.app.diff import load_frame

BOX = 2      # 5 × 5 box
HOLE_RADIUS = 3


def north_up(a: np.ndarray) -> np.ndarray:
    return a[::-1]


def centroid(frame: dict, x0: float, y0: float):
    image, usable = north_up(frame["image"]), north_up(frame["usable"])
    cx, cy = int(round(x0)), int(round(y0))
    box = (slice(cy - BOX, cy + BOX + 1), slice(cx - BOX, cx + BOX + 1))
    if not usable[box].all():
        return None
    sky = float(np.median(image[usable]))
    w = np.clip(image[box] - sky, 0, None)
    if w.sum() <= 0:
        return None
    ys, xs = np.mgrid[box]
    return float((w * xs).sum() / w.sum()), float((w * ys).sum() / w.sum())


def hole_centre(frame: dict, x0: float, y0: float):
    unusable = ~north_up(frame["usable"])
    ys, xs = np.nonzero(unusable)
    near = np.hypot(xs - x0, ys - y0) <= HOLE_RADIUS
    if near.sum() < 3:
        return None
    return float(xs[near].mean()), float(ys[near].mean()), int(near.sum())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    m = json.loads((args.folder / "manifest.json").read_text())
    g = json.loads((args.folder / "gaia.json").read_text())
    target = next((s for s in g["stars"] if s.get("target")), None)
    print(f"{m['label']} D{m['band']} ({m['mode']})")
    if target is None:
        print("  no Gaia match for the target, nothing to compare")
        return
    first = None
    for f, (gx, gy) in zip(m["frames"], target["xy"]):
        frame = load_frame(args.folder / f["fits"])
        c, h = centroid(frame, gx, gy), hole_centre(frame, gx, gy)
        if first is None:
            first = (gx, gy, c, h)
        fx, fy, fc, fh = first
        line = f"  {f['date_iso'][:10]}  Gaia ({gx:6.2f},{gy:6.2f}) shift {math.hypot(gx - fx, gy - fy):4.2f} px"
        if c:
            line += f" | centroid ({c[0]:6.2f},{c[1]:6.2f})"
            if fc:
                line += (f" shift ({c[0] - fc[0]:+5.2f},{c[1] - fc[1]:+5.2f}) = "
                         f"{math.hypot(c[0] - fc[0], c[1] - fc[1]):4.2f} px vs Gaia ({gx - fx:+5.2f},{gy - fy:+5.2f})")
        else:
            line += " | centroid: box not fully usable"
        if h:
            line += f" | hole ({h[0]:6.2f},{h[1]:6.2f}) {h[2]} px"
            if fh:
                line += f" shift ({h[0] - fh[0]:+5.2f},{h[1] - fh[1]:+5.2f})"
        print(line)


if __name__ == "__main__":
    main()
