"""Scientist view: the raw pixels of every exposure behind a frame, with each pixel's FLAGS value.

    python -m backend.app.pixels frontend/frames/*/d*

The flipbook shows add-ups lined up north-up, where one pixel mixes several detector pixels. Flag bits
cannot be reprojected, so this reads the cached cutouts themselves (cache/cutouts/, written by render.py):
the detector pixels exactly as IRSA delivers them, one exposure at a time, cropped to the ones under the
flipbook frame. For each pixel it keeps the FLAGS integer, IMAGE − ZODI, sigma = sqrt(VARIANCE) and one
category. The category uses the same rule as the add-up (clean.py), so the website never applies a second one:

  no value   IMAGE is NaN: the file has no number here
  transient  TRANSIENT is set (in the official bad list, so left out of the add-up)
  bad        another flag from the official bad list (config.BAD_FLAG_NAMES)
  source     SOURCE is set and no bad flag: a known object is here; kept
  good       none of the above (information bits such as OUTLIER or FULLSAMPLE may be set); kept

Arrays are row-major in FITS order: row 0 is the bottom row, so detector y grows upwards. One gzip file per
visit (pixels<i>.json.gz); the website unpacks it in the browser.
"""
import argparse
import gzip
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS

from backend.app.align import target_grid
from backend.app.config import BAD_FLAG_NAMES, CACHE_DIR
from backend.app.flags import bad_pixel_bitmask, flag_bits
from backend.app.motion import position_at, separation_arcsec
from backend.app.render import POSITION_YEAR

FORMAT = "spherex-blink-pixels/1"
GOOD, SOURCE, BAD, TRANSIENT, NO_VALUE = range(5)
CATEGORY_KEYS = ("good", "source", "bad", "transient", "no_value")
SAME_POSITION_ARCSEC = 5.0


class CutoutMissing(FileNotFoundError):
    """An exposure behind a frame is not in the cutout cache."""


def classify(flags: np.ndarray, has_value: np.ndarray, bits: dict[str, int], bad_mask: int) -> np.ndarray:
    """One category per pixel (GOOD … NO_VALUE), in the priority order of the module docstring."""
    flags = flags.astype(np.int64)
    category = np.full(flags.shape, GOOD, np.uint8)
    if "SOURCE" in bits:
        category[(flags & (1 << bits["SOURCE"])) != 0] = SOURCE
    category[(flags & bad_mask) != 0] = BAD
    if "TRANSIENT" in bits:
        category[(flags & (1 << bits["TRANSIENT"])) != 0] = TRANSIENT
    category[~has_value] = NO_VALUE
    return category


def bit_table(header: fits.Header, flags: np.ndarray) -> list[dict]:
    """Every bit this file's FLAGS header defines: name, the header's own meaning, used to reject?, pixel count."""
    bits = flag_bits(header)
    meaning = {}
    for key in header:
        if key.startswith("MP_"):
            meaning[key[3:]] = header.comments[key]
        elif key.startswith("MSKN") and key[4:].isdigit():
            meaning[str(header[key]).strip()] = header.comments[key]
    flags = flags.astype(np.int64)
    return [{"bit": bit, "name": name, "meaning": meaning.get(name, ""), "rejected": name in BAD_FLAG_NAMES,
             "pixels": int(((flags & (1 << bit)) != 0).sum())}
            for name, bit in sorted(bits.items(), key=lambda kv: kv[1])]


def _rounded(values: np.ndarray, digits: int) -> list:
    """Significant digits, with null where the file has no number."""
    return [float(f"{v:.{digits}g}") if math.isfinite(v) else None for v in values.ravel().tolist()]


def _year(mjd: float) -> float:
    return float(Time(mjd, format="mjd").jyear)


def frame_box(wcs: WCS, shape: tuple[int, int], corners: list[tuple[float, float]]) -> tuple[int, int, int, int]:
    """(x0, x1, y0, y1), end exclusive: the cutout pixels that overlap the flipbook frame (its corners on the sky).

    Pixel c covers c − 0.5 … c + 0.5; a pixel that only touches the frame's edge is not included.
    """
    x, y = wcs.world_to_pixel_values([c[0] for c in corners], [c[1] for c in corners])
    eps = 1e-6
    x0, x1 = max(0, math.floor(min(x) - 0.5 + eps) + 1), min(shape[1], math.ceil(max(x) + 0.5 - eps))
    y0, y1 = max(0, math.floor(min(y) - 0.5 + eps) + 1), min(shape[0], math.ceil(max(y) + 0.5 - eps))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("the flipbook frame does not overlap this cutout")
    return x0, x1, y0, y1


def frame_corners(manifest: dict) -> list[tuple[float, float]]:
    """Sky positions of the four outer corners of the flipbook grid (render.py's grid)."""
    grid, size = target_grid(manifest["ra"], manifest["dec"], manifest["fov_arcmin"])
    edge = (-0.5, size - 0.5)
    return [tuple(float(v) for v in grid.pixel_to_world_values(x, y)) for x in edge for y in edge]


def sky_model(wcs: WCS, offset: tuple[int, int], shape: tuple[int, int]) -> dict:
    """A local linear sky model around the box centre, and its largest error against the full WCS.

    East and north offsets (arcsec) from ref_radec ≈ arcsec_per_px[0] · (x − x0) + arcsec_per_px[1] · (y − y0),
    where arcsec_per_px[0] is one step in x and [1] one step in y. The website uses this instead of carrying an
    RA and Dec for every pixel; max_error_arcsec says how far that can be from the file's own WCS.
    """
    ny, nx = shape
    ox, oy = offset
    x0, y0 = (nx - 1) / 2, (ny - 1) / 2
    ra0, dec0 = (float(v) for v in wcs.pixel_to_world_values(x0 + ox, y0 + oy))
    cos_dec = math.cos(math.radians(dec0))
    jac = []
    for dx, dy in ((1, 0), (0, 1)):
        ra1, dec1 = (float(v) for v in wcs.pixel_to_world_values(x0 + ox + dx, y0 + oy + dy))
        jac.append((((ra1 - ra0 + 180) % 360 - 180) * cos_dec * 3600, (dec1 - dec0) * 3600))
    yy, xx = np.mgrid[0:ny, 0:nx]
    ra, dec = wcs.pixel_to_world_values(xx + ox, yy + oy)
    east = jac[0][0] * (xx - x0) + jac[1][0] * (yy - y0)
    north = jac[0][1] * (xx - x0) + jac[1][1] * (yy - y0)
    lin_ra, lin_dec = ra0 + east / 3600 / cos_dec, dec0 + north / 3600
    err = np.hypot(((ra - lin_ra + 180) % 360 - 180) * np.cos(np.radians(dec)), dec - lin_dec) * 3600
    inv = np.linalg.inv(np.array([[jac[0][0], jac[1][0]], [jac[0][1], jac[1][1]]]))

    def unit(v):
        return [round(float(c), 4) for c in v / np.hypot(*v)]

    return {
        "ref_px": [x0, y0], "ref_radec": [round(ra0, 7), round(dec0, 7)],
        "arcsec_per_px": [[round(j, 5) for j in jac[0]], [round(j, 5) for j in jac[1]]],
        "max_error_arcsec": round(float(err.max()), 4),
        "north_px": unit(inv @ np.array([0.0, 1.0])), "east_px": unit(inv @ np.array([1.0, 0.0])),
    }


def wavelength_plane(hdul: fits.HDUList, offset: tuple[int, int], shape: tuple[int, int]):
    """The wavelength (µm) the filter passes, as a plane over the box, from WCS "W" with SIP off (clean.py).

    The filter's wavelength changes smoothly across the detector; a plane through every pixel of the box is
    stored with its largest error, instead of one number per pixel. None when the file has no spectral WCS.
    """
    try:
        spec = WCS(hdul["IMAGE"].header, fobj=hdul, key="W")
        spec.sip = None
        yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
        wl, _ = spec.pixel_to_world_values(xx + offset[0], yy + offset[1])
    except Exception:  # no spectral WCS in this file: unknown, never guessed
        return None
    wl = np.asarray(wl, float)
    if not np.isfinite(wl).all():
        return None
    x0, y0 = (shape[1] - 1) / 2, (shape[0] - 1) / 2
    a = np.c_[np.ones(wl.size), (xx - x0).ravel(), (yy - y0).ravel()]
    coef, *_ = np.linalg.lstsq(a, wl.ravel(), rcond=None)
    return {"at_ref_px": round(float(coef[0]), 5), "per_px": [float(f"{coef[1]:.4g}"), float(f"{coef[2]:.4g}")],
            "max_error_um": float(f"{np.abs(wl.ravel() - a @ coef).max():.2g}")}


def detector_pixel(header: fits.Header, x: int, y: int):
    """0-based active detector pixel of cutout pixel (x, y), from the cutout's WCS "A" (IRSA writes it)."""
    try:
        dx, dy = WCS(header, key="A").pixel_to_world_values(x, y)
    except Exception:
        return None
    return [int(round(float(dx))), int(round(float(dy)))]


def exposure_pixels(path: Path, corners: list[tuple[float, float]], target_radec: tuple[float, float] | None) -> dict:
    """Everything the scientist view shows for one cutout, cropped to the flipbook frame."""
    with fits.open(path) as hdul:
        header = hdul["IMAGE"].header
        wcs = WCS(header)
        x0, x1, y0, y1 = frame_box(wcs, hdul["IMAGE"].data.shape, corners)
        crop = (slice(y0, y1), slice(x0, x1))
        image = hdul["IMAGE"].data[crop].astype(float)
        value = image - hdul["ZODI"].data[crop].astype(float)
        variance = hdul["VARIANCE"].data[crop].astype(float)
        flags = np.asarray(hdul["FLAGS"].data[crop]).astype(np.int64)
        fh = hdul["FLAGS"].header
        bad_mask = bad_pixel_bitmask(fh)
        category = classify(flags, np.isfinite(image), flag_bits(fh), bad_mask)
        with np.errstate(invalid="ignore"):
            sigma = np.where(variance > 0, np.sqrt(variance), np.nan)
        shape = image.shape
        uniq, index = np.unique(flags, return_inverse=True)
        target = None
        if target_radec is not None:
            tx, ty = (float(v) - o for v, o in zip(wcs.world_to_pixel_values(*target_radec), (x0, y0)))
            if -0.5 <= tx < shape[1] - 0.5 and -0.5 <= ty < shape[0] - 0.5:
                target = [round(tx, 3), round(ty, 3)]
        mjd = float(header["MJD-AVG"])
        return {
            "obs_id": str(header.get("OBSID", path.name.split("_D")[0])),
            "mjd": round(mjd, 6),
            "date_iso": Time(mjd, format="mjd").to_datetime().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "cutout_file": path.name,
            "cutout_shape": [int(v) for v in hdul["IMAGE"].data.shape],
            "box_in_cutout": [x0, y0],
            "shape": [int(shape[0]), int(shape[1])],
            "detector_origin": detector_pixel(header, x0, y0),
            "bits": bit_table(fh, flags),
            "bad_mask": int(bad_mask),
            "flag_values": [int(v) for v in uniq],
            "flag_index": [int(i) for i in index.ravel()],
            "category": [int(c) for c in category.ravel()],
            "counts": {k: int((category == i).sum()) for i, k in enumerate(CATEGORY_KEYS)},
            "value": _rounded(value, 4),
            "sigma": _rounded(sigma, 3),
            "wavelength": wavelength_plane(hdul, (x0, y0), shape),
            "sky": sky_model(wcs, (x0, y0), shape),
            "target_px": target,
        }


def find_cutout(obs_id: str, band: int, ra: float, dec: float) -> Path:
    """The cached cutout of this exposure at this position (the largest, if several sizes were downloaded)."""
    found = []
    for path in (CACHE_DIR / "cutouts").glob(f"{obs_id}_D{band}_*.fits"):
        try:
            cra, cdec, size = (float(v) for v in path.stem.split(f"_D{band}_")[1].split("_"))
        except ValueError:
            continue
        if separation_arcsec(ra, dec, cra, cdec) < SAME_POSITION_ARCSEC:
            found.append((size, path))
    if not found:
        raise CutoutMissing(f"{obs_id} D{band} at {ra:.5f} {dec:+.5f} is not in {CACHE_DIR / 'cutouts'}")
    return max(found)[1]


def target_track(folder: Path, manifest: dict):
    """(function: MJD -> target ra, dec; sentence saying what the ring marks)."""
    gaia_path = folder / "gaia.json"
    star = None
    if gaia_path.exists():
        star = next((s for s in json.loads(gaia_path.read_text())["stars"] if s.get("target")), None)
    if star is not None and star["has_motion"]:
        def at(mjd):
            return position_at(manifest["ra"], manifest["dec"], star["pmra"], star["pmdec"], POSITION_YEAR, _year(mjd))
        return at, (f"The ring marks the target on this exposure's date: the frame centre ({POSITION_YEAR:.1f}) "
                    f"moved with Gaia DR3 {star['source_id']}'s proper motion (parallax not applied).")
    if "moved to" in manifest.get("position_source", ""):
        how = (f"The ring marks the target's {POSITION_YEAR:.1f} position (the frame centre). Gaia gives no motion "
               "for it, so on other dates the target can sit a little away from the ring.")
    else:
        how = "The ring marks the frame centre (the position asked for)."
    return (lambda _mjd: (manifest["ra"], manifest["dec"])), how


def build_visit(manifest: dict, i: int, rows: list[tuple[str, float, int]], corners, track, how) -> dict:
    frame = manifest["frames"][i]
    exposures = []
    for obs_id, mjd, _ in sorted((r for r in rows if r[2] == i), key=lambda r: r[1]):
        path = find_cutout(obs_id, manifest["band"], manifest["ra"], manifest["dec"])
        exposures.append(exposure_pixels(path, corners, track(mjd)))
    return {
        "format": FORMAT, "target": manifest["target"], "label": manifest["label"], "band": manifest["band"],
        "frame": i, "epoch_id": frame["epoch_id"], "date_iso": frame["date_iso"], "frame_mode": manifest["mode"],
        "categories": list(CATEGORY_KEYS),
        "bad_flag_names": list(BAD_FLAG_NAMES),
        "row_order": "row-major, FITS order: index = y * nx + x, row 0 at the bottom (detector y grows upwards)",
        "crop": f"the detector pixels under the flipbook's {manifest['fov_arcmin']:g}′ frame",
        "target_ring": how,
        "units": {"value": "MJy/sr (IMAGE − ZODI)", "sigma": "MJy/sr (sqrt VARIANCE)", "wavelength": "µm"},
        "exposures": exposures,
        "made_by": "backend/app/pixels.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx",
    }


def write_pixels(folder: Path) -> list[str]:
    """pixels<i>.json.gz for every frame of a folder; returns the file names. Raises CutoutMissing."""
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    table = fits.getdata(folder / "exposures.fits", "EXPOSURES")
    rows = [(str(r["OBS_ID"]).strip(), float(r["MJD"]), int(r["FRAME"])) for r in table]
    corners = frame_corners(manifest)
    track, how = target_track(folder, manifest)
    visits = [build_visit(manifest, i, rows, corners, track, how) for i in range(len(manifest["frames"]))]
    names = []
    for i, visit in enumerate(visits):
        name = f"pixels{i}.json.gz"
        text = json.dumps(visit, separators=(",", ":"), ensure_ascii=False).encode()
        (folder / name).write_bytes(gzip.compress(text, mtime=0))
        names.append(name)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path, help="e.g. frontend/frames/barnard/d2")
    for folder in parser.parse_args().folders:
        try:
            names = write_pixels(folder)
        except (CutoutMissing, FileNotFoundError, ValueError) as exc:
            print(f"{folder}: FAILED {exc}")
            continue
        size = sum((folder / n).stat().st_size for n in names) / 1024
        print(f"{folder}: {len(names)} files, {size:.0f} KB")


if __name__ == "__main__":
    main()
