"""Offline tests for the frames pipeline (clean -> align -> coadd -> PNG), on synthetic files."""
import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from backend.app.align import align, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import PIXEL_SCALE_ARCSEC
from backend.app.render import brightness_scale, save_flags_png, save_png, to_grey

RA, DEC = 150.0, 20.0
SCALE = PIXEL_SCALE_ARCSEC / 3600
HOT, SOURCE = 10, 21


def sky_wcs(size: int, angle_deg: float = 0.0) -> WCS:
    """TAN WCS centred on (RA, DEC), SPHEREx pixel size, rotated by angle_deg."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [RA, DEC]
    w.wcs.crpix = [(size + 1) / 2, (size + 1) / 2]
    a = np.radians(angle_deg)
    w.wcs.cd = SCALE * np.array([[-np.cos(a), np.sin(a)], [np.sin(a), np.cos(a)]])
    return w


def write_cutout(path, image, zodi=1.0, variance=4.0, flags=None, angle_deg=0.0, mjd=61000.25):
    size = image.shape[0]
    header = sky_wcs(size, angle_deg).to_header()
    header["MJD-AVG"] = mjd
    header["DATE"] = "2030-01-01T00:00:00"  # processing time; must not be used
    flags_header = fits.Header()
    flags_header["HIERARCH MP_HOT"] = HOT
    flags_header["HIERARCH MP_SOURCE"] = SOURCE
    fits.HDUList([
        fits.PrimaryHDU(),
        fits.ImageHDU(image.astype(np.float32), header, name="IMAGE"),
        fits.ImageHDU(np.full(image.shape, zodi, np.float32), header, name="ZODI"),
        fits.ImageHDU(np.full(image.shape, variance, np.float32), header, name="VARIANCE"),
        fits.ImageHDU(np.zeros(image.shape, np.int32) if flags is None else flags.astype(np.int32),
                      flags_header, name="FLAGS"),
    ]).writeto(path)
    return path


def test_clean_subtracts_zodi_and_reads_noise_flags_and_time(tmp_path):
    image = np.full((21, 21), 5.0)
    image[3, 3] = np.nan
    flags = np.zeros((21, 21), int)
    flags[1, 1] = 1 << HOT
    flags[2, 2] = 1 << SOURCE
    c = clean_cutout(write_cutout(tmp_path / "c.fits", image, flags=flags), RA, DEC)
    assert c["image"][0, 0] == pytest.approx(4.0)
    assert c["sigma"][0, 0] == pytest.approx(2.0)
    assert c["bad"][1, 1] and not c["bad"][2, 2]  # HOT is a defect, SOURCE is a label
    assert np.isnan(c["image"][3, 3])  # no value stays no value
    assert c["mjd"] == 61000.25  # MJD-AVG, not DATE
    assert c["wl_um"] is None and c["bw_um"] is None  # no spectral WCS in this file: unknown, not a guess


def test_target_grid_is_odd_north_up_and_centred():
    grid, size = target_grid(RA, DEC, 3.0)
    assert size == 29
    x, y = grid.world_to_pixel_values(RA, DEC)
    assert (x, y) == pytest.approx((14, 14))
    assert grid.wcs.cdelt[0] < 0 < grid.wcs.cdelt[1]  # east left, north up


@pytest.mark.parametrize("angle", [0.0, 90.0, 180.0])
def test_align_puts_north_up_and_east_left_for_rotated_exposures(tmp_path, angle):
    size = 41
    image = np.zeros((size, size))
    # A bright pixel 2 pixels north and 3 pixels east of the target.
    ra = RA + 3 * SCALE / np.cos(np.radians(DEC))
    dec = DEC + 2 * SCALE
    x, y = sky_wcs(size, angle).world_to_pixel_values(ra, dec)
    image[int(round(float(y))), int(round(float(x)))] = 100.0
    c = clean_cutout(write_cutout(tmp_path / f"r{int(angle)}.fits", image, zodi=0.0, angle_deg=angle))
    grid, n = target_grid(RA, DEC, 3.0)
    a = align(c, grid, n)
    row, col = np.unravel_index(np.nanargmax(a["image"]), a["image"].shape)
    assert (row, col) == (14 + 2, 14 - 3)  # array row grows north; east is to the left
    assert a["pct_covered"] == 100.0 and a["pct_no_value"] == 0.0


def test_align_counts_nan_pixels_as_no_value_not_as_outside(tmp_path):
    image = np.ones((41, 41))
    image[20, 20] = np.nan  # the target pixel, like a saturated core
    a = align(clean_cutout(write_cutout(tmp_path / "n.fits", image)), *target_grid(RA, DEC, 3.0))
    assert a["inside"][14, 14] and not a["covered"][14, 14]
    assert a["pct_no_value"] > 0 and a["pct_covered"] == 100.0


def aligned(value, sigma, bad=False, covered=True):
    shape = (3, 3)
    return {
        "image": np.full(shape, value if covered else np.nan),
        "sigma": np.full(shape, sigma if covered else np.nan),
        "bad": np.full(shape, bad and covered),
        "covered": np.full(shape, covered),
        "inside": np.ones(shape, bool),
    }


def test_coadd_weights_by_inverse_variance():
    out = coadd([aligned(10.0, 1.0), aligned(20.0, 2.0)])
    # weights 1 and 1/4: (10 + 20/4) / 1.25 = 12; sigma = 1 / sqrt(1.25)
    assert out["image"][0, 0] == pytest.approx(12.0)
    assert out["sigma"][0, 0] == pytest.approx(1 / np.sqrt(1.25))
    assert (out["n_used"] == 2).all()


def test_coadd_skips_bad_pixels_and_reports_flagged_and_no_value():
    out = coadd([aligned(10.0, 1.0), aligned(999.0, 1.0, bad=True)])
    assert out["image"][0, 0] == pytest.approx(10.0) and out["pct_flagged"] == 0.0
    only_bad = coadd([aligned(999.0, 1.0, bad=True)])
    assert np.isnan(only_bad["image"]).all() and only_bad["pct_flagged"] == 100.0
    no_value = coadd([aligned(0.0, 1.0, covered=False)])
    assert no_value["pct_no_value"] == 100.0 and no_value["pct_flagged"] == 0.0


def test_png_has_north_at_top_and_is_transparent_without_value(tmp_path):
    values = np.zeros((3, 3))
    values[2, :] = 1.0  # last array row = north
    has_value = np.ones((3, 3), bool)
    has_value[0, 0] = False
    save_png(values, has_value, {"vmin": 0.0, "vmax": 1.0}, tmp_path / "f.png")
    rgba = np.array(Image.open(tmp_path / "f.png"))
    assert (rgba[0, :, 0] == 255).all() and (rgba[2, 1:, 0] == 0).all()
    assert rgba[2, 0, 3] == 0 and rgba[2, 1, 3] == 255  # south-east corner had no value
    bad = np.zeros((3, 3), bool)
    bad[2, 2] = True
    save_flags_png(bad, tmp_path / "b.png")
    assert np.array(Image.open(tmp_path / "b.png"))[0, 2, 3] > 0


def test_asinh_scale_keeps_ends_and_lifts_faint_values():
    picture = {"image": np.array([[0.0, 1.0, 10.0, 1000.0]]), "covered": np.ones((1, 4), bool),
               "bad": np.zeros((1, 4), bool)}
    linear = brightness_scale([picture], "linear")
    asinh = brightness_scale([picture], "asinh")
    assert asinh["vmax"] == 1000.0 and asinh["stretch"] == "asinh" and "not proportional" in asinh["method"]
    grey = to_grey(picture["image"], asinh)
    assert grey[0, 0] == 0 and grey[0, -1] == pytest.approx(1)
    assert grey[0, 2] > 0.3 > to_grey(picture["image"], linear)[0, 2]   # 1% of the range: visible only with asinh
    assert np.all(np.diff(grey[0]) > 0)                                  # order of brightness kept
    with pytest.raises(ValueError):
        brightness_scale([picture], "log")
