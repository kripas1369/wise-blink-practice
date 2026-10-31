import pytest

from backend.app.archive import SpherexImage, _detector_number, cutout_file, group_epochs
from backend.app.motion import position_at, separation_arcsec


def test_barnard_2000_to_2016_matches_gaia():
    # SIMBAD J2000 position and Gaia DR3 proper motion of Barnard's Star.
    ra, dec = position_at(269.452077, 4.693365, -801.551, 10362.394, 2000.0, 2016.0)
    # Gaia DR3 position at epoch 2016.0: 269.448503, 4.739420.
    assert separation_arcsec(ra, dec, 269.448503, 4.739420) < 0.5


def test_no_motion_means_no_move():
    assert position_at(10.0, 20.0, 0.0, 0.0, 2000.0, 2026.0) == pytest.approx((10.0, 20.0))


def test_ra_wraps_around_360():
    ra, _ = position_at(359.9999, 0.0, 3.6e6, 0.0, 2000.0, 2001.0)  # +1 degree in RA
    assert ra == pytest.approx(0.9999, abs=1e-6)


def test_separation_one_degree():
    assert separation_arcsec(0, 0, 0, 1) == pytest.approx(3600.0)


def _image(mjd, det=1):
    return SpherexImage(
        obs_id=f"x{mjd}", did=f"ivo://irsa.ipac/spherex_qr2?x{mjd}/D{det}", detector=det,
        mjd_start=mjd, mjd_end=mjd, wl_min_um=0.75, wl_max_um=1.09, release_date="2026-01-01",
    )


def test_epochs_split_on_gaps():
    images = [_image(m) for m in (100, 105, 120, 300, 310, 500)]
    epochs = group_epochs(images)
    assert [ep["n_images"] for ep in epochs] == [3, 2, 1]


def test_continuous_coverage_is_split_by_max_span():
    images = [_image(100 + 5 * i) for i in range(40)]  # every 5 days for 200 days
    epochs = group_epochs(images, gap_days=30, max_span_days=60)
    assert len(epochs) == 4
    assert all(ep["mjd_max"] - ep["mjd_min"] <= 60 for ep in epochs)


def test_detector_number():
    assert _detector_number("SPHEREx-D3") == 3


def test_cutout_file_is_stable():
    im = _image(61000.5, det=6)
    assert cutout_file(im, 1.0, -2.0, 0.05) == cutout_file(im, 1.0, -2.0, 0.05)
    assert "D6" in cutout_file(im, 1.0, -2.0, 0.05).name
