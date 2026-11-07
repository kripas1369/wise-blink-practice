"""Offline tests for Day 7: the planted-mover test (recovery.py) and the single exposures inside a visit
(visit_frames.py, field_objects.py). NASA JPL is replaced by fakes; the real folders are checked for format."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from backend.app import field_objects
from backend.app.align import target_grid
from backend.app.known_objects import Unavailable
from backend.app.recovery import FORMAT as RECOVERY_FORMAT, LEVELS, half_found, plant, pixel_psf, run_level
from backend.app.visit_frames import FORMAT as VISITS_FORMAT, MIN_FOR_RESIDUAL, residual

FRAMES = Path("frontend/frames")
FOLDERS = sorted(p.parent for p in FRAMES.glob("*/d*/manifest.json"))
IDS = lambda p: f"{p.parent.name}/{p.name}"


# ---------- planted movers ----------

def noise_frame(rng, size=40, usable=None):
    return {"image": rng.normal(0, 1, (size, size)), "sigma": np.ones((size, size)),
            "flagged": np.zeros((size, size), bool),
            "usable": np.ones((size, size), bool) if usable is None else usable}


def test_planted_flux_adds_up_and_peak_matches():
    image = np.zeros((30, 30))
    plant(image, 14.3, 15.7, 100.0, 0.6)
    assert image.sum() == pytest.approx(100.0, rel=1e-4)
    _, _, _, peak = pixel_psf(14.3, 15.7, 0.6, image.shape)
    assert image.max() == pytest.approx(100 * peak, rel=1e-6)


def test_pure_noise_gives_about_half_at_the_limit_and_all_when_bright():
    rng = np.random.default_rng(1)
    a, b = noise_frame(rng), noise_frame(rng)
    rows = {lv: run_level(a, b, lv, 0.55, 5.0, np.random.default_rng(lv)) for lv in (0, 5, 12)}
    assert rows[0]["found_pct"] < 5
    assert 30 <= rows[5]["found_pct"] <= 85
    assert rows[12]["found_pct"] >= 97 and rows[12]["both_ends_pct"] >= 90
    assert rows[12]["flux_mjy"] > rows[5]["flux_mjy"] and rows[12]["ab_mag"] < rows[5]["ab_mag"]


def test_fakes_on_unusable_pixels_count_as_no_value():
    rng = np.random.default_rng(2)
    usable = np.ones((40, 40), bool)
    usable[:, :20] = False
    a, b = noise_frame(rng, usable=usable), noise_frame(rng, usable=usable)
    r = run_level(a, b, 20, 0.55, 5.0, np.random.default_rng(3))
    assert 30 <= r["lost"]["no_z_pct"] <= 70
    assert r["found_pct"] + r["lost"]["no_z_pct"] + r["lost"]["blended_pct"] >= 95


def test_half_found_interpolates_and_says_when_never_reached():
    row = lambda lv, pct: {"peak_sigma": lv, "found_pct": pct, "flux_mjy": 0.1 * lv if lv else None}
    h = half_found([row(0, 3), row(4, 30), row(6, 70)])
    assert h["peak_sigma"] == 5.0 and h["flux_mjy"] == pytest.approx(0.5)
    assert half_found([row(0, 3), row(4, 10), row(20, 40)]) is None
    assert half_found([row(0, 3), row(3, 60), row(4, 80)]) == {"below_lowest": 3}


@pytest.mark.parametrize("folder", FOLDERS, ids=IDS)
def test_recovery_file_matches_the_difference_pairs(folder):
    path = folder / "recovery.json"
    assert path.exists(), "run python -m backend.app.recovery on this folder"
    r = json.loads(path.read_text())
    diff = json.loads((folder / "diff.json").read_text())
    assert r["format"] == RECOVERY_FORMAT and r["limit_sigma"] == diff["limit_sigma"]
    assert [(p["a"], p["b"]) for p in r["pairs"]] == [(p["a"], p["b"]) for p in diff["pairs"]]
    assert 5 < r["psf"]["fwhm_arcsec"] < 15 and r["psf"]["source"]
    for p in r["pairs"]:
        assert [lv["peak_sigma"] for lv in p["levels"]] == list(LEVELS)
        for lv in p["levels"]:
            lost = lv["lost"]
            assert lv["found_pct"] + lost["no_z_pct"] + lost["blended_pct"] + lost["too_faint_pct"] == pytest.approx(100, abs=0.3)
            assert lv["both_ends_pct"] <= lv["found_pct"]
            assert ("ab_mag" in lv) == (lv["peak_sigma"] > 0)


# ---------- known objects in the field ----------

def test_horizons_command_for_each_kind_of_name():
    assert field_objects.horizons_command("32455 (2000 SW60)") == "32455;"
    assert field_objects.horizons_command("(2020 RL59)") == "DES=2020 RL59;"
    assert field_objects.horizons_command("29P/Schwassmann-Wachmann 1") == "DES=29P;CAP;NOFRAG;"
    assert field_objects.horizons_command("C/2023 A3 (Tsuchinshan-ATLAS)") == "DES=C/2023 A3;CAP;NOFRAG;"


def test_jpl_sexagesimal_positions():
    ra, dec = field_objects.parse_radec("05:07:34.57", "+30 27'38.4\"")
    assert ra == pytest.approx(76.894042, abs=1e-6) and dec == pytest.approx(30.460667, abs=1e-6)
    _, dec = field_objects.parse_radec("22:04:00", "-56 48'03\"")
    assert dec == pytest.approx(-(56 + 48 / 60 + 3 / 3600))


def test_parallax_moves_a_near_object_away_from_spherex():
    ra, dec = field_objects.from_spherex(0.0, 0.0, 1.0, [0.0, 7000.0, 0.0])
    shift = ((ra + 180) % 360 - 180) * 3600
    assert shift == pytest.approx(-7000 / field_objects.AU_KM * 206264.806, rel=1e-4)
    assert dec == pytest.approx(0.0, abs=1e-9)


def exposure(k, mjd):
    return {"k": k, "mjd": mjd, "observer": {"available": True, "mjd": mjd, "xyz_km": [0.0, 0.0, 0.0],
                                             "vxyz_kms": [0.0, 0.0, 0.0]}}


def test_field_objects_lands_on_the_grid_and_skips_far_ones(monkeypatch):
    ra0, dec0 = 76.9566, 30.4013
    grid, size = target_grid(ra0, dec0, 3)
    far = dec0 + 0.3
    monkeypatch.setattr(field_objects, "first_pass", lambda obs, ra, dec: ([
        {"name": "1 (Near)", "ra": ra0, "dec": dec0, "v_mag": 18.0, "ra_rate": 0.0, "dec_rate": 0.0},
        {"name": "2 (Far)", "ra": ra0, "dec": far, "v_mag": 18.0, "ra_rate": 0.0, "dec_rate": 0.0},
    ], obs["mjd"] + 2400000.5))
    asked = []

    def fake_horizons(name, jds):
        asked.append(name)
        return [{"ra": ra0, "dec": dec0, "delta_au": 100.0, "mag": 18.2, "ra_rate": 30.0, "dec_rate": -40.0}] * len(jds)

    monkeypatch.setattr(field_objects, "horizons", fake_horizons)
    answers = field_objects.objects_in_exposures([exposure(0, 61000.0), exposure(1, 61000.1)], ra0, dec0, grid, size)
    assert asked == ["1 (Near)"]
    for k in (0, 1):
        assert answers[k]["outcome"] == "objects"
        o = answers[k]["objects"][0]
        assert o["x"] == pytest.approx((size - 1) / 2, abs=0.05) and o["y"] == pytest.approx((size - 1) / 2, abs=0.05)
        assert o["rate_arcsec_per_h"] == 50.0


def test_field_objects_stops_asking_after_two_failures(monkeypatch):
    calls = []

    def down(obs, ra, dec):
        calls.append(obs["mjd"])
        raise Unavailable("JPL answered HTTP 500")

    monkeypatch.setattr(field_objects, "first_pass", down)
    grid, size = target_grid(10.0, 10.0, 3)
    exps = [exposure(k, 61000.0 + 2 * k) for k in range(4)]
    exps.append({"k": 4, "mjd": 61010.0, "observer": {"available": False, "reason": "no header"}})
    answers = field_objects.objects_in_exposures(exps, 10.0, 10.0, grid, size)
    assert len(calls) == 2
    assert all(answers[k]["outcome"] == "unavailable" for k in range(5))
    assert "not asked again" in answers[3]["reason"] and answers[4]["reason"] == "no header"


def test_clusters_split_at_twelve_hours():
    groups = field_objects.clusters([{"mjd": m} for m in (0.0, 0.2, 0.45, 1.0, 1.1)])
    assert [len(g) for g in groups] == [3, 2]


# ---------- single exposures ----------

def test_residual_cancels_the_steady_sky_and_keeps_what_changed():
    images = np.ones((4, 10, 10)) * 7.0
    images[2, 5, 5] += 10.0
    sigmas = np.full((4, 10, 10), 2.0)
    usable = np.ones((4, 10, 10), bool)
    usable[2, 0, 0] = False
    z = residual(images, sigmas, usable, 2)
    assert z[5, 5] == pytest.approx(5.0) and np.isnan(z[0, 0])
    assert np.nanmax(np.abs(np.delete(z.ravel(), [55]))) == 0


@pytest.mark.parametrize("folder", FOLDERS, ids=IDS)
def test_visits_file_lists_every_exposure_with_its_pictures(folder):
    path = folder / "visits.json"
    assert path.exists(), "run python -m backend.app.visit_frames on this folder"
    v = json.loads(path.read_text())
    manifest = json.loads((folder / "manifest.json").read_text())
    table = fits.getdata(folder / "exposures.fits", "EXPOSURES")
    assert v["format"] == VISITS_FORMAT and len(v["visits"]) == len(manifest["frames"])
    for i, visit in enumerate(v["visits"]):
        ids = [str(r["OBS_ID"]).strip() for r in table if int(r["FRAME"]) == i]
        assert sorted(e["obs_id"] for e in visit["exposures"]) == sorted(ids)
        hours = [e["hours_from_first"] for e in visit["exposures"]]
        assert hours == sorted(hours) and hours[0] == 0 and visit["span_hours"] == hours[-1]
        for e in visit["exposures"]:
            assert (folder / e["png"]).exists() and (folder / e["flags_png"]).exists()
            assert (e["residual_png"] is not None) == (visit["n_exposures"] >= MIN_FOR_RESIDUAL)
            if e["residual_png"]:
                assert (folder / e["residual_png"]).exists()
            known = e["known"]
            assert known["outcome"] in ("objects", "none", "unavailable", "not_asked")
            for o in known.get("objects", []):
                assert -1.5 <= o["x"] <= manifest["size_px"] + 0.5 and -1.5 <= o["y"] <= manifest["size_px"] + 0.5
                assert not math.isnan(o["rate_arcsec_per_h"])
