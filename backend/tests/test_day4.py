"""Offline tests for Day 4: light curves (photometry, same-wavelength rule, wings limit) and the asinh frames."""
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from scripts import acceptance
from backend.app.lightcurve import (MJY_PER_PIXEL_UNIT, lightcurve, measure, ring_weights, same_wavelength,
                                    target_track)

SIZE = 29
C = (SIZE - 1) / 2


def star_image(flux: float, x: float = C, y: float = C, sky: float = 0.5, width: float = 0.6):
    """Sky plus a Gaussian star whose pixel values add up to `flux` (MJy/sr x pixels)."""
    yy, xx = np.indices((SIZE, SIZE))
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * width ** 2))
    return sky + flux * g / g.sum()


def exposures(fluxes, wls, frames, holes=0.0, bw=0.03):
    n = len(fluxes)
    image = np.array([star_image(f) for f in fluxes])
    has_value = np.ones_like(image, bool)
    if holes:
        yy, xx = np.indices((SIZE, SIZE))
        has_value[:, np.hypot(xx - C, yy - C) <= holes] = False
        image[~has_value] = np.nan
    return {"image": image, "sigma": np.full_like(image, 0.01), "bad": np.zeros_like(image, bool),
            "has_value": has_value, "obs_id": [f"e{i}" for i in range(n)], "mjd": 60800.0 + np.arange(n) * 50,
            "wl_um": np.array(wls, float), "bw_um": np.full(n, bw), "frame": np.array(frames)}


MANIFEST = {"target": "test", "label": "Test", "band": 2, "size_px": SIZE,
            "frames": [{"epoch_id": 0, "mjd": 60800.0}, {"epoch_id": 1, "mjd": 60900.0}]}


def test_ring_weights_cover_the_circle_area():
    assert ring_weights((SIZE, SIZE), C, C, 0, 2).sum() == pytest.approx(np.pi * 4, rel=0.03)
    assert ring_weights((SIZE, SIZE), C + 0.3, C - 0.2, 3, 6).sum() == pytest.approx(np.pi * 27, rel=0.03)


def test_measure_recovers_the_star_and_removes_the_sky():
    image = star_image(100.0)
    m = measure(image, np.full_like(image, 0.01), np.zeros_like(image, bool), np.ones_like(image, bool), C, C, 0, 2)
    assert m["flux_mjy"] == pytest.approx(100.0 * MJY_PER_PIXEL_UNIT, rel=0.01)
    assert m["sky"] == pytest.approx(0.5) and m["err_mjy"] > 0 and not m["no_value"]


def test_no_value_inside_the_circle_gives_no_number():
    image = star_image(100.0)
    has_value = np.ones_like(image, bool)
    has_value[int(C), int(C)] = False
    m = measure(image, np.full_like(image, 0.01), np.zeros_like(image, bool), has_value, C, C, 0, 2)
    assert m["no_value"] and m["flux_mjy"] is None


def points(rows):
    return [{"frame": f, "mjd": 60800.0 + 100 * f + i, "wl_um": wl, "bw_um": 0.03, "flux_mjy": flux,
             "err_mjy": err, "n_flagged": flagged} for i, (f, wl, flux, err, flagged) in enumerate(rows)]


def test_visits_are_compared_only_at_the_same_wavelength():
    sw = same_wavelength(points([
        (0, 1.200, 10.0, 0.1, 0), (1, 1.205, 12.0, 0.1, 0),   # 0.005 µm apart: compared (limit 0.015)
        (0, 1.300, 10.0, 0.1, 0), (1, 1.330, 30.0, 0.1, 0),   # 0.03 µm apart: not compared
        (0, 1.400, 10.0, 0.1, 0), (1, 1.401, 20.0, 0.1, 3),   # flagged: only in pairs_incl_flagged
        (0, 1.500, 1.0, 0.5, 0), (1, 1.500, 9.0, 0.1, 0),     # 2 sigma: never compared
    ]))
    assert sw["pairs"] == [{"a": 0, "b": 1, "n": 1, "median_ratio": 1.2, "min_ratio": 1.2, "max_ratio": 1.2,
                            "max_wl_gap_um": 0.005}]
    assert sw["pairs_incl_flagged"][0]["n"] == 2 and sw["pairs_incl_flagged"][0]["max_ratio"] == 2.0


def test_core_light_curve_keeps_each_exposure_and_its_wavelength():
    ex = exposures([100, 100, 150, 150], [1.2, 1.4, 1.2, 1.4], [0, 0, 1, 1])
    lc = lightcurve(ex, MANIFEST, [(C, C)] * 4, "test")
    assert lc["method"] == "core" and [p["wl_um"] for p in lc["points"]] == [1.2, 1.4, 1.2, 1.4]
    assert lc["same_wavelength"]["pairs"][0]["median_ratio"] == pytest.approx(1.5, rel=0.01)


def test_small_saturated_core_uses_wings_and_large_one_gives_no_light_curve():
    small = lightcurve(exposures([100, 150], [1.2, 1.2], [0, 1], holes=1.0, ), MANIFEST, [(C, C)] * 2, "test")
    assert small["method"] == "wings" and small["r_in_px"] <= 3
    assert small["same_wavelength"]["pairs"][0]["median_ratio"] == pytest.approx(1.5, rel=0.02)
    big = lightcurve(exposures([100, 150], [1.2, 1.2], [0, 1], holes=4.0), MANIFEST, [(C, C)] * 2, "test")
    assert big["method"] == "none" and big["points"] == [] and "saturated" in big["reason"]


def test_track_follows_gaia_between_and_beyond_the_frames():
    gaia = {"stars": [{"target": True, "source_id": "9", "xy": [[10.0, 14.0], [12.0, 14.0]]}]}
    track, rule = target_track(MANIFEST, gaia, np.array([60800.0, 60850.0, 61000.0]))
    assert [round(x, 3) for x, _ in track] == [10.0, 11.0, 14.0] and "Gaia DR3 9" in rule
    assert track[0][1] == pytest.approx(SIZE - 1 - 14.0)   # PNG y (down) -> FITS y (up)


client = TestClient(main.app)


def test_lightcurve_api_for_a_prepared_target_and_a_clicked_pixel():
    lc = client.get("/api/lightcurve", params={"target": "eps_ind_b", "band": 2}).json()
    assert lc["format"] == "spherex-blink-lightcurve/1" and lc["method"] == "core" and len(lc["points"]) > 10
    at = client.get("/api/lightcurve", params={"target": "eps_ind_b", "band": 2, "x": 3, "y": 25})
    assert at.status_code == 200 and "clicked position" in at.json()["position_rule"]
    assert client.get("/api/lightcurve", params={"target": "barnard", "band": 2}).json()["method"] == "none"


@pytest.mark.parametrize("params", [{"x": 3}, {"x": 40, "y": 3}, {"x": -1, "y": 3}])
def test_lightcurve_api_errors(params):
    r = client.get("/api/lightcurve", params={"target": "eps_ind_b", "band": 2, **params})
    assert r.status_code == 400 and set(r.json()) == {"error"}


def test_r_dra_frames_use_the_asinh_scale_and_say_so():
    m = json.loads((main.PREPARED_DIR / "r_dra" / "d2" / "manifest.json").read_text())
    assert m["mode"] == "coadd" and m["scale"]["stretch"] == "asinh" and "not proportional" in m["scale"]["method"]
    assert any("asinh" in note for note in m["notes"])


def test_c4_barnard_and_eps_ind_b_move_with_gaia():
    for target, how in [("barnard", "hole"), ("eps_ind_b", "centroid")]:
        r = acceptance.shift_check(target, 2, how)
        assert r["difference_px"] <= acceptance.MAX_MOTION_ERROR_PX, target
        assert r["direction_difference_deg"] <= acceptance.MAX_DIRECTION_ERROR_DEG, target


def test_wise_prediction_is_the_grid_centre_at_2026_apart_from_parallax():
    m = json.loads((main.PREPARED_DIR / "wise0855" / "d6" / "manifest.json").read_text())
    x, y = acceptance.wise_predicted_xy(m, acceptance.GRID_EPOCH_MJD)
    assert np.hypot(x - 14, y - 14) <= acceptance.WISE_PLX_MAS / 1000 / m["pixel_arcsec"] * 1.02
    x1, _ = acceptance.wise_predicted_xy(m, acceptance.GRID_EPOCH_MJD + 365.25)
    assert 1.2 < x1 - x < 1.45, "8.12″/yr west is 1.32 px/yr, +x is west"


def test_c4_wise0855_d6_source_moves_like_wise0855_and_is_absent_in_d2():
    r = acceptance.wise0855()
    shift = r["d6_shift"]
    assert shift["difference_sigma"] < 3 and shift["against_fixed_star_sigma"] > 3
    assert all(v["offset_from_wise_px"] < 3 * v["error_px"] for v in r["d6_absolute"])
    assert all(v["wise_flux_snr"] < 3 for v in r["d2_visits"])
    assert all(v["gaia_star_flux_snr"] > 10 for v in r["d2_visits"])
