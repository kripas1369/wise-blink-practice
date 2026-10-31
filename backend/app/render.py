"""Step 2a, part 3: SPHEREx frames for the website flipbook (PNG per visit + manifest.json).

Run from the repo root:
    python -m backend.app.render barnard 2                  # add up to 8 exposures per visit
    python -m backend.app.render wise0855 6 --max-per-visit 20
    python -m backend.app.render barnard 2 --mode single --out scratch/frames
Writes <out>/<target>/d<detector>/ in the format of docs/plan/FRAMES_FORMAT.md, then <out>/index.json.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from PIL import Image

from backend.app import archive
from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import DETECTORS, PIXEL_SCALE_ARCSEC, REPO_ROOT
from backend.app.coords import mjd_to_date, parse_coordinates
from backend.app.frame_notes import NOTES
from backend.app.motion import position_at
from backend.app.resolve import ResolverUnavailable, resolve_name
from backend.app.targets import OFFICIAL_TARGETS

FORMAT = "spherex-blink-frames/1"
POSITION_YEAR = 2026.0
SCALE_PERCENTILES = (1.0, 99.5)
ASINH_SOFTENING = 0.002   # fraction of the range where asinh turns from linear to logarithmic
MIN_COVERED_PCT = 90.0
DEFAULT_OUT = REPO_ROOT / "frontend" / "frames"


def target_position(target: dict) -> tuple[float, float, str]:
    """SIMBAD position moved to POSITION_YEAR (the same rule as the website's ring)."""
    try:
        star = resolve_name(target["simbad"])
    except (LookupError, ResolverUnavailable):
        if "challenge_position" not in target:
            raise
        ra, dec = parse_coordinates(target["challenge_position"])
        return ra, dec, "challenge text (SIMBAD unavailable, not moved)"
    ra, dec = position_at(
        star["ra"], star["dec"], star["pmra"] or 0.0, star["pmdec"] or 0.0, star["epoch"], POSITION_YEAR
    )
    return ra, dec, f"SIMBAD ({star['server']}) {star['simbad_id']}, moved to {POSITION_YEAR}"


def visit_exposures(epoch: dict, ra, dec, grid, size, size_deg, wanted: int) -> list[tuple]:
    """Up to `wanted` usable exposures of a visit, closest to its mean time first.

    Usable = the position is in the image and at least MIN_COVERED_PCT of the grid is inside it.
    Returns [(image, cleaned, aligned), ...].
    """
    candidates = sorted(epoch["images"], key=lambda im: abs(im.mjd - epoch["mjd_mean"]))
    chosen = []
    start = 0
    while len(chosen) < wanted and start < len(candidates):
        batch = candidates[start:start + wanted - len(chosen)]
        start += len(batch)
        archive.attach_paths(batch)
        paths = archive.download_cutouts(batch, ra, dec, size_deg)
        for image in batch:  # keep the closest-in-time order
            path = paths[image.did]
            if isinstance(path, archive.NotInImage):
                continue
            if isinstance(path, Exception):  # a failed download must not silently shrink the add-up
                raise path
            cleaned = clean_cutout(path, ra, dec)
            aligned = align(cleaned, grid, size)
            if aligned["pct_covered"] >= MIN_COVERED_PCT:
                chosen.append((image, cleaned, aligned))
    return chosen


def frame_for_visit(exposures: list[tuple], mode: str) -> dict:
    """The picture and its numbers for one visit."""
    if mode == "single":
        image, cleaned, aligned = exposures[0]
        picture = aligned
    else:
        picture = coadd([a for _, _, a in exposures])
    wls = [c["wl_um"] for _, c, _ in exposures if c["wl_um"] is not None]
    bws = [c["bw_um"] for _, c, _ in exposures if c["bw_um"] is not None]
    images = [im for im, _, _ in exposures]
    frame = {
        "picture": picture,
        "mjd": float(np.mean([c["mjd"] for _, c, _ in exposures])),
        "wl_target_um": round(float(np.mean(wls)), 4) if len(wls) == len(exposures) else None,
        "bw_target_um": round(float(np.mean(bws)), 4) if len(bws) == len(exposures) else None,
        "wl_min_um": round(min(im.wl_min_um for im in images), 3),
        "wl_max_um": round(max(im.wl_max_um for im in images), 3),
        "n_images": len(exposures),
    }
    if len(wls) == len(exposures) and len(exposures) > 1:
        frame["wl_target_range_um"] = [round(min(wls), 4), round(max(wls), 4)]
    if mode == "single":
        frame["obs_id"] = images[0].obs_id
        frame["collection"] = images[0].collection
    return frame


def to_grey(values: np.ndarray, scale: dict) -> np.ndarray:
    """0-1 grey from MJy/sr with the manifest's scale (FRAMES_FORMAT.md, "PNG rules")."""
    with np.errstate(invalid="ignore"):
        t = np.clip((values - scale["vmin"]) / (scale["vmax"] - scale["vmin"]), 0, 1)
    if scale.get("stretch", "linear") == "asinh":
        a = scale["asinh_softening"]
        t = np.arcsinh(t / a) / np.arcsinh(1 / a)
    return t


def save_png(values: np.ndarray, has_value: np.ndarray, scale: dict, path: Path) -> None:
    """Grey PNG, north at the top (array row 0 is south, so flip), transparent where there is no value."""
    grey = to_grey(values, scale)
    rgba = np.zeros(values.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = np.nan_to_num(grey * 255)[..., None].astype(np.uint8)
    rgba[..., 3] = np.where(has_value & np.isfinite(values), 255, 0)
    Image.fromarray(np.flipud(rgba), "RGBA").save(path)


def save_flags_png(bad: np.ndarray, path: Path) -> None:
    rgba = np.zeros(bad.shape + (4,), dtype=np.uint8)
    rgba[bad] = (255, 40, 40, 200)
    Image.fromarray(np.flipud(rgba), "RGBA").save(path)


def save_frame_fits(picture: dict, grid, mjd: float, n_images: int, detector: int, mode: str,
                    path: Path) -> None:
    """Value, sigma, flagged and has-value maps on the frames grid (FITS rows: south first)."""
    header = grid.to_header()
    header["BUNIT"] = "MJy/sr"
    header["MJD-AVG"] = (mjd, "mean MJD-AVG of the exposures in this picture")
    header["NIMAGES"] = (n_images, "exposures added")
    header["DETECTOR"] = detector
    header["MODE"] = mode
    hdus = [fits.PrimaryHDU()]
    for name, data, comment in [
        ("IMAGE", picture["image"].astype(np.float32), "IMAGE - ZODI, NaN where no usable value"),
        ("SIGMA", picture["sigma"].astype(np.float32), "1 sigma noise from VARIANCE"),
        ("FLAGGED", picture["bad"].astype(np.uint8), "1 = flagged bad (official mask)"),
        ("HAS_VALUE", picture["covered"].astype(np.uint8), "1 = has a usable value"),
    ]:
        hdu = fits.ImageHDU(data, header=header.copy(), name=name)
        hdu.header["COMMENT"] = comment
        hdus.append(hdu)
    fits.HDUList(hdus).writeto(path, overwrite=True)


def brightness_scale(pictures: list[dict], stretch: str = "linear") -> dict:
    """One scale for every frame, from the good pixels of all frames together.

    linear: 1st-99.5th percentile, the default.
    asinh: 1st percentile to the brightest good pixel, compressed so that a star thousands of times
    brighter than the sky (R Dra's core) and the faint sky both stay visible.
    """
    good = np.concatenate([p["image"][p["covered"] & ~p["bad"]] for p in pictures])
    good = good[np.isfinite(good)]
    if stretch == "linear":
        vmin, vmax = (float(v) for v in np.percentile(good, SCALE_PERCENTILES))
        return {"vmin": round(vmin, 4), "vmax": round(vmax, 4), "unit": "MJy/sr", "stretch": "linear",
                "method": f"linear, {SCALE_PERCENTILES[0]}-{SCALE_PERCENTILES[1]} percentile of good pixels "
                          "of all frames (same scale for every frame)"}
    if stretch != "asinh":
        raise ValueError(f"unknown stretch {stretch!r}")
    vmin, vmax = float(np.percentile(good, SCALE_PERCENTILES[0])), float(good.max())
    a = ASINH_SOFTENING
    return {"vmin": round(vmin, 4), "vmax": round(vmax, 4), "unit": "MJy/sr", "stretch": "asinh",
            "asinh_softening": a,
            "method": f"asinh: grey = asinh(t/{a}) / asinh(1/{a}), t = (value - vmin)/(vmax - vmin); vmin = "
                      f"{SCALE_PERCENTILES[0]} percentile, vmax = brightest good pixel of all frames (same scale "
                      "for every frame). Faint parts are brightened, so grey levels are not proportional to "
                      "brightness"}


METHODS = {
    "single": "one exposure per visit (the one closest to the visit's mean time); IMAGE - ZODI; official "
              "flag mask; reprojected (reproject_interp) onto this grid",
    "coadd": "up to {max} exposures per visit (closest to the visit's mean time), each IMAGE - ZODI with "
             "the official flag mask, reprojected onto this grid and added up with 1/variance weights",
}


class NoImages(LookupError):
    """SPHEREx has no usable image of this position in this detector (yet)."""


def make_frames(key: str, detector: int, mode: str = "coadd", max_per_visit: int = 8,
                fov_arcmin: float = 3.0, out_root: Path = DEFAULT_OUT, stretch: str = "linear") -> dict:
    """Frames for one of the 5 official targets (position from SIMBAD, moved to 2026.0)."""
    target = next(t for t in OFFICIAL_TARGETS if t["key"] == key)
    ra, dec, position_source = target_position(target)
    return render_frames(ra, dec, key, target["label"], position_source, detector, mode, max_per_visit,
                         fov_arcmin, out_root, NOTES.get((key, detector), []), stretch)


def render_frames(ra: float, dec: float, key: str, label: str, position_source: str, detector: int,
                  mode: str = "coadd", max_per_visit: int = 8, fov_arcmin: float = 3.0,
                  out_root: Path = DEFAULT_OUT, notes: list[str] | None = None,
                  stretch: str = "linear") -> dict:
    """Frames for any position; writes <out_root>/<key>/d<detector>/ and returns the manifest."""
    grid, size = target_grid(ra, dec, fov_arcmin)
    size_deg = cutout_size_deg(fov_arcmin)
    wanted = 1 if mode == "single" else max_per_visit

    images = [im for im in archive.find_images(ra, dec, detector=detector) if im.detector == detector]
    if not images:
        raise NoImages(f"No SPHEREx images of {label} in D{detector}")
    frames = []
    for epoch in archive.group_epochs(images):
        exposures = visit_exposures(epoch, ra, dec, grid, size, size_deg, wanted)
        if not exposures:
            print(f"  visit {epoch['id']} {epoch['date']}: no usable exposure, skipped")
            continue
        frame = frame_for_visit(exposures, mode)
        frame.update(epoch_id=epoch["id"], n_images_in_epoch=epoch["n_images"])
        frames.append(frame)
        p = frame["picture"]
        print(f"  visit {epoch['id']} {epoch['date']}: {frame['n_images']} of {epoch['n_images']} exposures, "
              f"{p['pct_flagged']}% flagged, {p['pct_no_value']}% no value, {frame['wl_target_um']} µm")
    if not frames:
        raise NoImages(f"{len(images)} SPHEREx images of {label} in D{detector}, but none covers the whole frame")

    scale = brightness_scale([f["picture"] for f in frames], stretch)
    out_dir = Path(out_root) / key / f"d{detector}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in [*out_dir.glob("epoch*.png"), *out_dir.glob("epoch*.fits"), *out_dir.glob("diff*")]:
        old.unlink()

    manifest_frames = []
    for f in frames:
        p = f.pop("picture")
        png, flags_png = f"epoch{f['epoch_id']}.png", f"epoch{f['epoch_id']}_flags.png"
        save_png(p["image"], p["covered"], scale, out_dir / png)
        save_flags_png(p["bad"], out_dir / flags_png)
        save_frame_fits(p, grid, round(f["mjd"], 5), f["n_images"], detector, mode,
                        out_dir / f"epoch{f['epoch_id']}.fits")
        manifest_frames.append({
            "png": png,
            "flags_png": flags_png,
            "fits": f"epoch{f['epoch_id']}.fits",
            "epoch_id": f["epoch_id"],
            "mjd": round(f["mjd"], 5),
            "date_iso": mjd_to_date(f["mjd"])[:16].replace("T", " ") + " UTC",
            "band": detector,
            "wl_min_um": f["wl_min_um"],
            "wl_max_um": f["wl_max_um"],
            "wl_target_um": f["wl_target_um"],
            "bw_target_um": f["bw_target_um"],
            **({"wl_target_range_um": f["wl_target_range_um"]} if "wl_target_range_um" in f else {}),
            "n_images": f["n_images"],
            "n_images_in_epoch": f["n_images_in_epoch"],
            "pct_flagged": p["pct_flagged"],
            "pct_no_value": p["pct_no_value"],
            "pct_covered": p["pct_covered"],
            **({"obs_id": f["obs_id"], "collection": f["collection"]} if "obs_id" in f else {}),
        })

    manifest = {
        "format": FORMAT,
        "target": key,
        "label": label,
        "ra": ra,  # not rounded: the grid must be rebuilt exactly (rebuild.py, diff.py)
        "dec": dec,
        "position_source": position_source,
        "fov_arcmin": fov_arcmin,
        "pixel_arcsec": PIXEL_SCALE_ARCSEC,
        "size_px": size,
        "orientation": "north up, east left",
        "band": detector,
        "band_range_um": list(DETECTORS[detector]),
        "mode": mode,
        "scale": scale,
        "method": METHODS[mode].format(max=max_per_visit),
        "made_by": "backend/app/render.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx",
        "notes": notes or [],
        "frames": manifest_frames,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_index(Path(out_root))
    print(f"wrote {out_dir}/manifest.json ({len(manifest_frames)} frames, mode {mode})")
    return manifest


def write_index(out_root: Path = DEFAULT_OUT) -> None:
    """<out>/index.json: which target/detector folders have a manifest."""
    available: dict[str, list[int]] = {}
    for path in sorted(Path(out_root).glob("*/d*/manifest.json")):
        available.setdefault(path.parent.parent.name, []).append(int(path.parent.name[1:]))
    index = {"format": "spherex-blink-frames-index/1", "available": available}
    (Path(out_root) / "index.json").write_text(json.dumps(index, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("target", choices=[t["key"] for t in OFFICIAL_TARGETS])
    parser.add_argument("detector", type=int, choices=sorted(DETECTORS))
    parser.add_argument("--mode", choices=["coadd", "single"], default="coadd")
    parser.add_argument("--max-per-visit", type=int, default=8, help="exposures added per visit (coadd)")
    parser.add_argument("--fov", type=float, default=3.0, help="field of view in arcmin (default 3)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stretch", choices=["linear", "asinh"], default="linear",
                        help="asinh for very bright stars (brightness_scale)")
    args = parser.parse_args()
    print(f"{args.target} D{args.detector} ({args.mode})")
    make_frames(args.target, args.detector, args.mode, args.max_per_visit, args.fov, args.out, args.stretch)


if __name__ == "__main__":
    main()
