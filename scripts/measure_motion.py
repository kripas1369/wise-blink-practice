"""Measured position of the target in each visit, compared with Gaia. Works offline on a frames folder.

Needs epoch<i>.fits (rebuild.py / render.py) and gaia.json (gaia.py). For each visit it measures the
centroid and the saturated-core ("hole") centre (backend/app/measure.py) and prints the shift from the
first visit next to Gaia's shift, in pixels (+x = west, +y = south, PNG convention).

    python -m scripts.measure_motion frontend/frames/eps_ind_b/d2
"""
import argparse
import json
import math
from pathlib import Path

from backend.app.diff import load_frame
from backend.app.measure import centroid, hole_centre


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
