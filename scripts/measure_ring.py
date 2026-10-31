"""How strong is the signal at the target ring, visit by visit? Works offline on a frames folder.

Rebuilds each visit's pictures from the cached cutouts of that position (written by render.py) and
prints, for the add-up and for the best single exposure, the brightest pixel in the 3 × 3 "ring":
    sky, noise  = median and 1.4826 × MAD of the good pixels (MJy/sr)
    sigma_mad   = (peak − sky) / noise                      the method of notes/DAY2_FINDINGS.md
    sigma_pipe  = (peak − sky) / the pipeline's own sigma at that pixel (from VARIANCE)
    offset      = where the peak is, in pixels from the ring centre (+x = west, +y = north)
"used" must equal the manifest's n_images, otherwise these are not the pictures the website shows.

    python -m scripts.measure_ring frontend/frames/wise0855/d6
"""
import argparse
import json
from pathlib import Path

import numpy as np

from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import CACHE_DIR
from backend.app.render import MIN_COVERED_PCT

SAME_VISIT_DAYS = 60


def ring_stats(picture: dict) -> dict:
    image, good = picture["image"], picture["covered"] & ~picture["bad"]
    sky = float(np.nanmedian(image[good]))
    noise = 1.4826 * float(np.nanmedian(np.abs(image[good] - sky)))
    stats = {"sky": round(sky, 4), "noise": round(noise, 4)}
    c = image.shape[0] // 2
    ring = np.where(good[c - 1:c + 2, c - 1:c + 2], image[c - 1:c + 2, c - 1:c + 2], np.nan)
    if np.isnan(ring).all():
        return {**stats, "sigma_mad": None, "sigma_pipe": None, "offset": None}
    r, k = np.unravel_index(np.nanargmax(ring), ring.shape)
    peak = float(ring[r, k])
    pipe = float(picture["sigma"][c - 1 + r, c - 1 + k])
    return {
        **stats,
        "sigma_mad": round((peak - sky) / noise, 1),
        "sigma_pipe": round((peak - sky) / pipe, 1) if np.isfinite(pipe) and pipe > 0 else None,
        "offset": (int(k - 1), int(r - 1)),  # column grows to the west (east is left), row grows north
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=Path, help="e.g. frontend/frames/wise0855/d6")
    args = parser.parse_args()

    m = json.loads((args.folder / "manifest.json").read_text())
    ra, dec, det = m["ra"], m["dec"], m["band"]
    grid, size = target_grid(ra, dec, m["fov_arcmin"])
    pattern = f"*_D{det}_{ra:.5f}_{dec:+.5f}_{cutout_size_deg(m['fov_arcmin']):.4f}.fits"
    usable = []
    for path in sorted((CACHE_DIR / "cutouts").glob(pattern)):
        cleaned = clean_cutout(path, ra, dec)
        aligned = align(cleaned, grid, size)
        if aligned["pct_covered"] >= MIN_COVERED_PCT:
            usable.append((cleaned, aligned))

    print(f"{m['label']} D{det} ({m['mode']}, {len(usable)} usable cached exposures)")
    times = np.array([f["mjd"] for f in m["frames"]])
    nearest = [int(np.argmin(np.abs(times - c["mjd"]))) for c, _ in usable]  # visits can be < 60 days apart
    for i, f in enumerate(m["frames"]):
        visit = [(c, a) for (c, a), n in zip(usable, nearest)
                 if n == i and abs(c["mjd"] - f["mjd"]) < SAME_VISIT_DAYS]
        if not visit:
            print(f"  {f['date_iso']}: no cached exposures")
            continue
        added = ring_stats(coadd([a for _, a in visit]))
        singles = [ring_stats(a) for _, a in visit]
        best = max(singles, key=lambda s: s["sigma_pipe"] or -1e9)
        check = "OK" if len(visit) == f["n_images"] else f"MISMATCH (manifest {f['n_images']})"
        print(f"  {f['date_iso']}: used {len(visit)} {check}\n"
              f"    add-up: {added}\n    best single: {best}")


if __name__ == "__main__":
    main()
