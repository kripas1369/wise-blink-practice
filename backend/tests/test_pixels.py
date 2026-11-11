"""Scientist view (backend/app/pixels.py): categories, crop, sky model, and the prepared pixels<i>.json.gz files."""
import gzip
import json
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from backend.app.clean import clean_cutout
from backend.app.config import CACHE_DIR
from backend.app.flags import bad_pixel_bitmask, flag_bits
from backend.app.pixels import (BAD, CATEGORY_KEYS, FORMAT, GOOD, NO_VALUE, SOURCE, TRANSIENT, classify,
                                exposure_pixels, find_cutout, frame_corners)
from backend.tests.test_pipeline import DEC, HOT, RA, write_cutout

FRAMES = Path("frontend/frames")
FOLDERS = sorted(p.parent for p in FRAMES.glob("*/d*/manifest.json"))
BITS = {"TRANSIENT": 0, "OUTLIER": 19, "HOT": 10, "SOURCE": 21}


def read(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def test_categories_follow_the_add_up_rule_in_priority_order():
    header = fits.Header({f"HIERARCH MP_{k}": v for k, v in BITS.items()})
    mask = bad_pixel_bitmask(header)
    flags = np.array([0, 1 << 21, 1 << 10, (1 << 10) | (1 << 21), 1 | (1 << 21), 1 << 19, 1 << 21, 1])
    has_value = np.array([True] * 6 + [False, True])
    got = classify(flags, has_value, flag_bits(header), mask)
    # clean, SOURCE label, HOT, HOT beats SOURCE, TRANSIENT beats SOURCE, OUTLIER is information, NaN, TRANSIENT
    assert got.tolist() == [GOOD, SOURCE, BAD, BAD, TRANSIENT, GOOD, NO_VALUE, TRANSIENT]


def test_exposure_is_cropped_to_the_frame_and_keeps_every_number(tmp_path):
    image = np.full((21, 21), 5.0)
    image[10, 10] = np.nan
    flags = np.zeros((21, 21), int)
    flags[9, 11] = (1 << HOT) | (1 << 21)
    path = write_cutout(tmp_path / "2026W01_1A_0001_1_D2_150.00000_+20.00000_0.0800.fits", image, flags=flags)
    corners = frame_corners({"ra": RA, "dec": DEC, "fov_arcmin": 1.0})   # an 11 × 11 grid
    e = exposure_pixels(path, corners, (RA, DEC))
    assert e["shape"] == [11, 11] and e["box_in_cutout"] == [5, 5]
    assert e["obs_id"] == "2026W01_1A_0001_1"
    assert e["detector_origin"] is None and e["wavelength"] is None   # not in this file: unknown, not guessed
    i = 5 * 11 + 5   # cutout pixel (10, 10) = box pixel (5, 5): the NaN
    assert e["category"][i] == NO_VALUE and e["value"][i] is None
    j = 4 * 11 + 6   # cutout row 9, column 11
    assert e["flag_values"][e["flag_index"][j]] == (1 << HOT) | (1 << 21) and e["category"][j] == BAD
    assert e["value"][0] == pytest.approx(4.0) and e["sigma"][0] == pytest.approx(2.0)
    assert e["counts"] == {"good": 119, "source": 0, "bad": 1, "transient": 0, "no_value": 1}
    assert e["target_px"] == pytest.approx([5.0, 5.0])
    assert e["sky"]["ref_radec"] == pytest.approx([RA, DEC]) and e["sky"]["max_error_arcsec"] < 0.05
    assert e["sky"]["north_px"] == pytest.approx([0, 1], abs=1e-3) and e["sky"]["east_px"] == pytest.approx([-1, 0], abs=1e-3)
    assert [b["name"] for b in e["bits"]] == ["HOT", "SOURCE"] and e["bits"][0]["rejected"] and not e["bits"][1]["rejected"]


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_prepared_pixel_files_match_the_frames_and_the_rule(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    table = fits.getdata(folder / "exposures.fits", "EXPOSURES")
    for i, frame in enumerate(manifest["frames"]):
        path = folder / f"pixels{i}.json.gz"
        assert path.exists(), "run python -m backend.app.pixels on this folder"
        p = read(path)
        assert p["format"] == FORMAT and p["band"] == manifest["band"] and p["epoch_id"] == frame["epoch_id"]
        assert p["categories"] == list(CATEGORY_KEYS)
        assert sorted(e["obs_id"] for e in p["exposures"]) == sorted(
            str(r["OBS_ID"]).strip() for r in table if int(r["FRAME"]) == i)
        for e in p["exposures"]:
            n = e["shape"][0] * e["shape"][1]
            assert all(len(e[k]) == n for k in ("flag_index", "category", "value", "sigma"))
            assert sum(e["counts"].values()) == n
            bits = {b["name"]: b["bit"] for b in e["bits"]}
            for k, c, v in zip(e["flag_index"], e["category"], e["value"]):
                f = e["flag_values"][k]
                expect = (NO_VALUE if v is None else TRANSIENT if "TRANSIENT" in bits and f >> bits["TRANSIENT"] & 1
                          else BAD if f & e["bad_mask"] else SOURCE if f >> bits.get("SOURCE", 99) & 1 else GOOD)
                assert c == expect
            assert e["sky"]["max_error_arcsec"] < 0.5
            assert e["wavelength"] is None or e["wavelength"]["max_error_um"] < 0.001


needs_cache = pytest.mark.skipif(not (CACHE_DIR / "cutouts").exists(), reason="needs the cached cutouts")


@needs_cache
def test_the_618_mjy_wise0855_pixel_is_shown_as_transient_beside_the_ring():
    """Day 4 finding: one pixel next to WISE 0855 in 2025W46_1A_0076_2 D6 reads 618 MJy/sr, FLAGS 2228293."""
    e = next(e for i in range(3) for e in read(FRAMES / f"wise0855/d6/pixels{i}.json.gz")["exposures"]
             if e["obs_id"] == "2025W46_1A_0076_2")
    k = e["flag_values"].index(2228293)
    i = e["flag_index"].index(k)
    nx = e["shape"][1]
    assert e["value"][i] == pytest.approx(617.8, abs=0.1) and CATEGORY_KEYS[e["category"][i]] == "transient"
    assert abs(i % nx - e["target_px"][0]) <= 1.5 and abs(i // nx - e["target_px"][1]) <= 1.5


@pytest.mark.skipif(
    not any((CACHE_DIR / "cutouts").glob("2025W35_1A_0146_1_D2_*.fits")),
    reason="needs 2025W35_1A_0146_1 D2 in cutouts cache",
)
def test_kept_pixels_are_exactly_the_ones_clean_py_keeps():
    p = read(FRAMES / "barnard/d2/pixels0.json.gz")
    m = json.loads((FRAMES / "barnard/d2/manifest.json").read_text())
    e = p["exposures"][0]
    cleaned = clean_cutout(find_cutout(e["obs_id"], 2, m["ra"], m["dec"]))
    x0, y0 = e["box_in_cutout"]
    ny, nx = e["shape"]
    bad = cleaned["bad"][y0:y0 + ny, x0:x0 + nx] | ~np.isfinite(cleaned["image"][y0:y0 + ny, x0:x0 + nx])
    kept = np.array([CATEGORY_KEYS[c] in ("good", "source") for c in e["category"]]).reshape(ny, nx)
    assert np.array_equal(kept, ~bad)
    w = WCS(fits.getheader(find_cutout(e["obs_id"], 2, m["ra"], m["dec"]), "IMAGE"))
    ra, dec = w.pixel_to_world_values(x0 + 3, y0 + 7)
    assert e["detector_origin"] is not None
    assert e["sky"]["max_error_arcsec"] < 0.1 and np.isfinite([ra, dec]).all()
