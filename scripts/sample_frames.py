"""Sample SPHEREx frames for the website flipbook (Kripas, Day 2).

Real data, simplest honest method, so the flipbook can be built before the full pipeline exists:
  - for each epoch, ONE exposure in the chosen detector (no add-up yet, so n_images = 1);
  - IMAGE - ZODI, official flag mask (SOURCE is a label, not a defect);
  - reprojected onto one north-up, east-left grid centred on the target's 2026.0 position;
  - one brightness scale (percentiles of the good pixels of all frames) for every frame.

[Friend's name]'s pipeline (clean.py / align.py / render.py, Day 2) replaces this with add-ups of
every exposure, and must write the same manifest format: docs/plan/FRAMES_FORMAT.md.

Run from the repo root:
    python -m scripts.sample_frames barnard 2
    python -m scripts.sample_frames wise0855 6
Writes frontend/frames/<target>/d<detector>/manifest.json and one PNG pair per epoch.
"""
import argparse
import json
import logging
import math
import warnings
from datetime import datetime, timezone

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from PIL import Image
from reproject import reproject_interp

from backend.app import archive
from backend.app.config import DETECTORS, PIXEL_SCALE_ARCSEC, REPO_ROOT
from backend.app.coords import mjd_to_date, parse_coordinates
from backend.app.flags import bad_pixel_bitmask
from backend.app.motion import position_at
from backend.app.resolve import ResolverUnavailable, resolve_name
from backend.app.targets import OFFICIAL_TARGETS

POSITION_YEAR = 2026.0
SCALE_PERCENTILES = (1.0, 99.5)
OUT_ROOT = REPO_ROOT / "frontend" / "frames"

# What a visitor must know before trusting their eyes. Each line was measured on these frames;
# the numbers and method are in notes/DAY2_FINDINGS.md.
NOTES = {
    ("barnard", 2): [
        "From its known motion (10.4″ a year, mostly north), Barnard's Star should move about 1.7 pixels "
        "between the first and last visit. Its centre is saturated (striped), so the shift is hard to judge by "
        "eye; measuring it against Gaia comes with the data pipeline (Day 3).",
    ],
    ("eps_ind_b", 2): [
        "The Apr 2026 visit has 30% of its pixels flagged (the other visits 1–9%); treat that frame with care.",
        "The two brown dwarfs are far closer together than one SPHEREx pixel (6.15″), so they show as one dot.",
    ],
    ("rw_aur", 2): [
        "Each visit sees a different wavelength (1.179, 1.533 and 1.225 µm at the star), and a single pixel's "
        "brightness depends on where the star falls inside it, so these frames cannot say how much RW Aurigae "
        "itself changed. That needs measured brightness at matching wavelengths (light curve, Day 4).",
    ],
    ("r_dra", 2): [
        "R Draconis is so bright that its centre is saturated (striped) in all 3 visits, so its brightness "
        "cannot be measured from these D2 frames.",
    ],
    ("wise0855", 2): [
        "The bright dot inside the ring is NOT WISE 0855. It sits about 9″ north-west of the ring's centre, "
        "on the same pixel in all 4 visits, so it is a background object (WISE 0855 moves about 1.3 pixels a "
        "year). It is not in SIMBAD; what it is has not been checked yet.",
    ],
    ("wise0855", 6): [
        "WISE 0855 is not clearly seen in these single exposures (2 to 5 sigma at the ring, not at the same "
        "spot each time). Adding up all exposures of a visit is needed before we can call it a detection.",
    ],
}

warnings.simplefilter("ignore", FITSFixedWarning)
logging.getLogger("astropy").setLevel(logging.WARNING)


def target_position(target: dict) -> tuple[float, float, str]:
    """SIMBAD position moved to POSITION_YEAR (the same rule as the Day 1 report and the website)."""
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


def target_grid(ra: float, dec: float, fov_arcmin: float) -> tuple[WCS, int]:
    """North-up, east-left grid of SPHEREx-sized pixels centred on (ra, dec)."""
    size = int(round(fov_arcmin * 60 / PIXEL_SCALE_ARCSEC)) | 1  # odd, so the target is a pixel centre
    grid = WCS(naxis=2)
    grid.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    grid.wcs.crval = [ra, dec]
    grid.wcs.crpix = [(size + 1) / 2, (size + 1) / 2]
    grid.wcs.cdelt = [-PIXEL_SCALE_ARCSEC / 3600, PIXEL_SCALE_ARCSEC / 3600]
    return grid, size


def wavelength_at(hdul: fits.HDUList, ra: float, dec: float) -> tuple[float | None, float | None]:
    """Wavelength and bandwidth (µm) at the target pixel, from the file's spectral WCS (key W)."""
    try:
        sky = WCS(hdul["IMAGE"].header)
        spec = WCS(hdul["IMAGE"].header, fobj=hdul, key="W")
        x, y = sky.world_to_pixel_values(ra, dec)
        wl, bw = spec.pixel_to_world_values(x, y)
        return round(float(wl), 4), round(float(bw), 4)
    except Exception:  # some files may lack the lookup table; then we say "unknown", not a guess
        return None, None


def frame_from_cutout(path, ra, dec, grid, size) -> dict:
    with fits.open(path) as hdul:
        header = hdul["IMAGE"].header
        image = hdul["IMAGE"].data.astype(float) - hdul["ZODI"].data.astype(float)
        flags = hdul["FLAGS"].data
        bad = (flags & bad_pixel_bitmask(hdul["FLAGS"].header)) != 0
        wcs = WCS(header)
        aligned, footprint = reproject_interp((image, wcs), grid, shape_out=(size, size))
        bad_aligned, _ = reproject_interp(
            (bad.astype(float), wcs), grid, shape_out=(size, size), order="nearest-neighbor"
        )
        # The footprint is 0 both outside the cutout and at NaN pixels; reprojecting ones tells them apart.
        _, inside = reproject_interp(
            (np.ones_like(image), wcs), grid, shape_out=(size, size), order="nearest-neighbor"
        )
        wl, bw = wavelength_at(hdul, ra, dec)
        covered = footprint > 0
        inside = inside > 0
        bad_on_grid = covered & (np.nan_to_num(bad_aligned) > 0.5)
        return {
            "image": np.where(covered, aligned, np.nan),
            "bad": bad_on_grid,
            "covered": covered,
            "mjd": float(header["MJD-AVG"]),
            "wl_target_um": wl,
            "bw_target_um": bw,
            "pct_flagged": round(100 * bad_on_grid.sum() / max(inside.sum(), 1), 1),
            # Inside the image but NaN (e.g. a saturated star core): the file has no value there.
            "pct_no_value": round(100 * (inside & ~covered).sum() / max(inside.sum(), 1), 1),
            "pct_covered": round(100 * inside.mean(), 1),
        }


def save_png(values: np.ndarray, covered: np.ndarray, vmin: float, vmax: float, path) -> None:
    """Grey PNG, north at the top (array row 0 is south, so flip), transparent where there is no value."""
    grey = np.clip((values - vmin) / (vmax - vmin), 0, 1)
    rgba = np.zeros(values.shape + (4,), dtype=np.uint8)
    rgba[..., :3] = np.nan_to_num(grey * 255)[..., None].astype(np.uint8)
    rgba[..., 3] = np.where(covered & np.isfinite(values), 255, 0)
    Image.fromarray(np.flipud(rgba), "RGBA").save(path)


def save_flags_png(bad: np.ndarray, path) -> None:
    rgba = np.zeros(bad.shape + (4,), dtype=np.uint8)
    rgba[bad] = (255, 40, 40, 200)
    Image.fromarray(np.flipud(rgba), "RGBA").save(path)


def make_frames(key: str, detector: int, fov_arcmin: float = 3.0) -> dict:
    target = next(t for t in OFFICIAL_TARGETS if t["key"] == key)
    ra, dec, position_source = target_position(target)
    grid, size = target_grid(ra, dec, fov_arcmin)
    # The cutout must cover the grid's corners even when the image is rotated: the diagonal + 5%.
    cutout_deg = max(0.08, fov_arcmin / 60 * math.sqrt(2) * 1.05)

    images = [im for im in archive.find_images(ra, dec) if im.detector == detector]
    if not images:
        raise SystemExit(f"No SPHEREx images of {target['label']} in D{detector}")
    epochs = archive.group_epochs(images)
    out_dir = OUT_ROOT / key / f"d{detector}"
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for epoch in epochs:
        candidates = sorted(epoch["images"], key=lambda im: abs(im.mjd - epoch["mjd_mean"]))
        for image in candidates:
            archive.attach_paths([image])
            try:
                path = archive.download_cutout(image, ra, dec, cutout_deg)
            except archive.NotInImage:
                continue
            frame = frame_from_cutout(path, ra, dec, grid, size)
            if frame["pct_covered"] < 90:
                continue  # target too close to the image edge for a full frame; try another exposure
            frame.update(source=image, epoch=epoch)
            frames.append(frame)
            print(f"  epoch {epoch['id']} {epoch['date']}: {image.did.rsplit('?', 1)[-1]} "
                  f"({frame['pct_flagged']}% flagged, {frame['wl_target_um']} µm)")
            break
        else:
            print(f"  epoch {epoch['id']} {epoch['date']}: no usable exposure, skipped")

    good = np.concatenate([f["image"][f["covered"] & ~f["bad"]] for f in frames])
    vmin, vmax = (float(v) for v in np.nanpercentile(good, SCALE_PERCENTILES))

    manifest_frames = []
    for f in frames:
        im, ep = f["source"], f["epoch"]
        png, flags_png = f"epoch{ep['id']}.png", f"epoch{ep['id']}_flags.png"
        save_png(f["image"], f["covered"], vmin, vmax, out_dir / png)
        save_flags_png(f["bad"], out_dir / flags_png)
        manifest_frames.append({
            "png": png,
            "flags_png": flags_png,
            "epoch_id": ep["id"],
            "mjd": round(f["mjd"], 5),
            "date_iso": mjd_to_date(f["mjd"])[:16].replace("T", " ") + " UTC",
            "band": detector,
            "wl_min_um": round(im.wl_min_um, 3),
            "wl_max_um": round(im.wl_max_um, 3),
            "wl_target_um": f["wl_target_um"],
            "bw_target_um": f["bw_target_um"],
            "n_images": 1,
            "n_images_in_epoch": ep["n_images"],
            "pct_flagged": f["pct_flagged"],
            "pct_no_value": f["pct_no_value"],
            "pct_covered": f["pct_covered"],
            "obs_id": im.obs_id,
            "collection": im.collection,
        })

    manifest = {
        "format": "spherex-blink-frames/1",
        "target": key,
        "label": target["label"],
        "ra": round(ra, 6),
        "dec": round(dec, 6),
        "position_source": position_source,
        "fov_arcmin": fov_arcmin,
        "pixel_arcsec": PIXEL_SCALE_ARCSEC,
        "size_px": size,
        "orientation": "north up, east left",
        "band": detector,
        "band_range_um": list(DETECTORS[detector]),
        "mode": "single",
        "scale": {
            "vmin": round(vmin, 4), "vmax": round(vmax, 4), "unit": "MJy/sr",
            "method": f"linear, {SCALE_PERCENTILES[0]}-{SCALE_PERCENTILES[1]} percentile of good pixels "
                      "of all frames (same scale for every frame)",
        },
        "method": "one exposure per epoch (closest to the epoch's mean time); IMAGE - ZODI; official "
                  "flag mask; reprojected (reproject_interp) onto this grid",
        "made_by": "scripts/sample_frames.py (Kripas's sample; the full pipeline replaces it)",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx",
        "notes": NOTES.get((key, detector), []),
        "frames": manifest_frames,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {out_dir.relative_to(REPO_ROOT)}/manifest.json ({len(manifest_frames)} frames)")
    write_index()
    return manifest


def write_index() -> None:
    """frontend/frames/index.json: which target/detector folders have a manifest."""
    available: dict[str, list[int]] = {}
    for path in sorted(OUT_ROOT.glob("*/d*/manifest.json")):
        available.setdefault(path.parent.parent.name, []).append(int(path.parent.name[1:]))
    index = {"format": "spherex-blink-frames-index/1", "available": available}
    (OUT_ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("target", choices=[t["key"] for t in OFFICIAL_TARGETS])
    parser.add_argument("detector", type=int, choices=sorted(DETECTORS))
    parser.add_argument("--fov", type=float, default=3.0, help="field of view in arcmin (default 3)")
    args = parser.parse_args()
    print(f"{args.target} D{args.detector}")
    make_frames(args.target, args.detector, args.fov)


if __name__ == "__main__":
    main()
