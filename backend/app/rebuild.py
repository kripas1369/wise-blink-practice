"""Rebuild the pictures of a frames folder from the cached cutouts, without asking IRSA again.

render.py caches every cutout it downloads (cache/cutouts/), so the exposures behind each frame can
be found again by position, detector and time. The rebuilt picture is accepted only if it gives the
same PNG as the one the website shows; then its numbers (value, sigma, flags) are saved next to it
as epoch<i>.fits (render.py now writes these itself), which the difference images (diff.py) need.

    python -m backend.app.rebuild frontend/frames/barnard/d2
    python -m backend.app.rebuild frontend/frames/*/d* --exact-position

--exact-position: manifests written before 1 Nov 2026 rounded ra/dec to 6 decimals (up to 0.002″),
which moved the grid enough to flip one pixel of a nearest-neighbour flag mask. This asks SIMBAD for
the position again (the same rule as render.py), uses it only if it rounds to the manifest's values,
and writes it into the manifest.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import CACHE_DIR
from backend.app.render import (MIN_COVERED_PCT, brightness_scale, save_frame_fits, save_png, target_position,
                                to_grey)
from backend.app.targets import OFFICIAL_TARGETS

SAME_VISIT_DAYS = 60


class RebuildError(RuntimeError):
    """The cache does not hold exactly the exposures behind a frame."""


def cached_visits(manifest: dict) -> list[list[tuple[dict, dict]]]:
    """For each frame of the manifest, the (cleaned, aligned) cached exposures of that visit."""
    ra, dec, det = manifest["ra"], manifest["dec"], manifest["band"]
    grid, size = target_grid(ra, dec, manifest["fov_arcmin"])
    pattern = f"*_D{det}_{ra:.5f}_{dec:+.5f}_{cutout_size_deg(manifest['fov_arcmin']):.4f}.fits"
    usable = []
    for path in sorted((CACHE_DIR / "cutouts").glob(pattern)):
        cleaned = clean_cutout(path, ra, dec)
        cleaned["obs_id"] = path.name.split(f"_D{det}_")[0]
        aligned = align(cleaned, grid, size)
        if aligned["pct_covered"] >= MIN_COVERED_PCT:
            usable.append((cleaned, aligned))
    times = np.array([f["mjd"] for f in manifest["frames"]])
    nearest = [int(np.argmin(np.abs(times - c["mjd"]))) for c, _ in usable]  # visits can be < 60 days apart
    return [
        [(c, a) for (c, a), n in zip(usable, nearest) if n == i and abs(c["mjd"] - f["mjd"]) < SAME_VISIT_DAYS]
        for i, f in enumerate(manifest["frames"])
    ]


def frame_picture(manifest: dict, frame: dict, visit: list[tuple[dict, dict]]) -> dict:
    """The picture of one frame, exactly as render.py made it; raises RebuildError if it cannot be."""
    if manifest["mode"] == "single":
        # render.py used the one exposure closest to the visit's mean time; find it by its time
        match = [a for c, a in visit if abs(c["mjd"] - frame["mjd"]) < 1e-4]
        if len(match) != 1:
            raise RebuildError(f"{frame['png']}: {len(match)} cached exposures at MJD {frame['mjd']}")
        return match[0]
    if len(visit) != frame["n_images"]:
        raise RebuildError(f"{frame['png']}: {len(visit)} cached exposures, manifest says {frame['n_images']}")
    mean_mjd = float(np.mean([c["mjd"] for c, _ in visit]))
    if abs(mean_mjd - frame["mjd"]) > 1e-4:
        raise RebuildError(f"{frame['png']}: cached exposures have mean MJD {mean_mjd:.5f}, not {frame['mjd']}")
    return coadd([a for _, a in visit])


def png_matches(picture: dict, scale: dict, png_path: Path) -> tuple[bool, str]:
    """Does the picture give the website's PNG? (1 grey level allowed: the manifest scale is rounded.)"""
    shown = np.asarray(Image.open(png_path).convert("RGBA"))[::-1]  # back to FITS row order (south first)
    values = picture["image"]
    has_value = picture["covered"] & np.isfinite(values)
    if not np.array_equal(shown[..., 3] > 0, has_value):
        return False, "different 'no value' pixels"
    grey = to_grey(values, scale) * 255
    worst = float(np.max(np.abs(np.where(has_value, grey, 0).astype(np.uint8).astype(int)
                                - shown[..., 0].astype(int))[has_value], initial=0))
    return worst <= 1, f"largest grey difference {worst:.0f}"


def exact_position(manifest: dict) -> tuple[float, float]:
    target = next(t for t in OFFICIAL_TARGETS if t["key"] == manifest["target"])
    ra, dec, source = target_position(target)
    if source != manifest["position_source"] or round(ra, 6) != manifest["ra"] or round(dec, 6) != manifest["dec"]:
        raise RebuildError(f"SIMBAD now gives {ra}, {dec} ({source}); the manifest has "
                           f"{manifest['ra']}, {manifest['dec']} ({manifest['position_source']})")
    return ra, dec


def rebuild_folder(folder: Path, fix_position: bool = False, stretch: str | None = None) -> list[str]:
    """Write epoch<i>.fits for every frame of a folder; returns one line per frame.

    stretch: afterwards, draw the PNGs again with a new scale (render.brightness_scale), only once every
    rebuilt picture has been checked against the old PNG.
    """
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if fix_position:
        manifest["ra"], manifest["dec"] = exact_position(manifest)
    grid, _ = target_grid(manifest["ra"], manifest["dec"], manifest["fov_arcmin"])
    report, pictures = [], []
    for frame, visit in zip(manifest["frames"], cached_visits(manifest)):
        picture = frame_picture(manifest, frame, visit)
        ok, detail = png_matches(picture, manifest["scale"], folder / frame["png"])
        if not ok:
            raise RebuildError(f"{folder}/{frame['png']}: rebuilt picture differs from the PNG ({detail})")
        frame["fits"] = frame["png"].replace(".png", ".fits")
        save_frame_fits(picture, grid, frame["mjd"], frame["n_images"], manifest["band"], manifest["mode"],
                        folder / frame["fits"])
        pictures.append(picture)
        report.append(f"  {frame['fits']}: {frame['n_images']} exposures, PNG matches ({detail})")
    if stretch:
        manifest["scale"] = brightness_scale(pictures, stretch)
        for frame, picture in zip(manifest["frames"], pictures):
            save_png(picture["image"], picture["covered"], manifest["scale"], folder / frame["png"])
        report.append(f"  PNGs drawn again: {manifest['scale']['method']}")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", type=Path, nargs="+", help="e.g. frontend/frames/barnard/d2")
    parser.add_argument("--exact-position", action="store_true", help="see the module docstring")
    parser.add_argument("--stretch", choices=["linear", "asinh"], help="draw the PNGs again with this scale")
    args = parser.parse_args()
    for folder in args.folders:
        print(folder)
        for line in rebuild_folder(folder, args.exact_position, args.stretch):
            print(line)


if __name__ == "__main__":
    main()
