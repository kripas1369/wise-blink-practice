"""Offline tests for Day 3: Gaia markers, difference maps and the API (no network)."""
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.diff import colour, default_pair, difference
from backend.app.gaia import markers, search_radius_deg

RA, DEC = 180.0, 10.0


def star(**kw):
    return {"source_id": "1", "ra": RA, "dec": DEC, "pmra": None, "pmdec": None, "parallax": None,
            "g_mag": 12.0, **kw}


def test_still_star_sits_on_the_centre_pixel():
    out = markers(RA, DEC, 3.0, [{"mjd": 61000.0}], [star()], target_year=2026.0)
    (x, y), = out["stars"][0]["xy"]
    assert (x, y) == pytest.approx((14, 14), abs=1e-6)
    assert out["target_match"]["source_id"] == "1"


def test_star_moving_north_moves_up_and_east_moves_left():
    # 6150 mas/yr = one 6.15″ pixel per year; MJD 57388.5 = 2016.0, 57753.75 = 2017.0
    north = star(pmra=0.0, pmdec=6150.0)
    east = star(source_id="2", pmra=6150.0, pmdec=0.0)
    out = markers(RA, DEC, 3.0, [{"mjd": 57388.5}, {"mjd": 57753.75}], [north, east])
    by_id = {s["source_id"]: s["xy"] for s in out["stars"]}
    (x0, y0), (x1, y1) = by_id["1"]
    assert x1 - x0 == pytest.approx(0, abs=0.01) and y1 - y0 == pytest.approx(-1.0, abs=0.01)
    (x0, y0), (x1, y1) = by_id["2"]
    assert x1 - x0 == pytest.approx(-1.0, abs=0.01) and y1 - y0 == pytest.approx(0, abs=0.01)


def test_star_far_outside_the_frame_is_dropped_and_no_target_claimed():
    out = markers(RA, DEC, 3.0, [{"mjd": 61000.0}], [star(dec=DEC + 0.1)], target_year=2026.0)
    assert out["stars"] == [] and out["target_match"] is None


def test_search_radius_covers_corner_and_motion():
    assert search_radius_deg(3.0, 10.0) > 3.0 / 60 / 2 * np.sqrt(2) + 100 / 3600


def frame(image, sigma=1.0, flagged=None):
    image = np.asarray(image, float)
    flagged = np.zeros(image.shape, bool) if flagged is None else flagged
    usable = np.isfinite(image) & ~flagged
    return {"image": image, "sigma": np.full(image.shape, sigma), "flagged": flagged, "usable": usable}


def test_difference_in_sigma_removes_sky_change_and_masks_bad_pixels():
    a = np.full((5, 5), 1.0)
    b = np.full((5, 5), 1.5)          # sky 0.5 brighter everywhere
    b[2, 2] += 3 * np.sqrt(2)         # and one pixel 3 sigma (of the difference) brighter
    a[0, 0] = np.nan                  # no value in A
    bad = np.zeros((5, 5), bool)
    bad[4, 4] = True                  # flagged in B
    d = difference(frame(a), frame(b, flagged=bad))
    assert d["sky_change"] == pytest.approx(0.5)
    assert d["z"][2, 2] == pytest.approx(3.0)
    assert np.isnan(d["z"][0, 0]) and np.isnan(d["z"][4, 4])
    assert d["flagged"][4, 4] and not d["flagged"][0, 0]
    assert d["max"][0] == pytest.approx(3.0)


def test_colour_is_north_up_and_transparent_without_value():
    z = np.zeros((3, 3))
    z[0, 0] = 10.0     # FITS row 0 = south -> bottom row of the PNG
    z[2, 2] = np.nan
    rgba = colour(z)
    assert rgba[2, 0, 0] == 255 and rgba[2, 0, 3] == 255   # clipped at +5 sigma: full "brighter" colour
    assert rgba[0, 2, 3] == 0


def test_default_pair_prefers_closest_wavelength_then_longest_time():
    pairs = [{"a": 0, "b": 1, "wl_gap_um": 0.05, "days": 300}, {"a": 0, "b": 2, "wl_gap_um": 0.01, "days": 100},
             {"a": 1, "b": 2, "wl_gap_um": 0.01, "days": 200}]
    assert (default_pair(pairs)["a"], default_pair(pairs)["b"]) == (1, 2)


# ---------- API ----------

client = TestClient(main.app)


def test_frames_for_prepared_target_have_urls():
    r = client.get("/api/frames", params={"target": "barnard", "band": 2})
    assert r.status_code == 200
    m = r.json()
    assert m["format"] == "spherex-blink-frames/1" and m["source"] == "prepared"
    assert m["frames"][0]["png_url"] == "/frames/barnard/d2/" + m["frames"][0]["png"]


def test_position_of_official_target_uses_prepared_frames():
    m = json.loads((main.PREPARED_DIR / "barnard" / "d2" / "manifest.json").read_text())
    r = client.get("/api/frames", params={"ra": m["ra"] + 1 / 3600, "dec": m["dec"], "band": 2})
    assert r.status_code == 200 and r.json()["target"] == "barnard"


def test_gaia_and_diff_for_prepared_target():
    g = client.get("/api/gaia", params={"target": "barnard", "band": 2}).json()
    assert g["target_match"] is not None
    d = client.get("/api/diff", params={"target": "barnard", "band": 2}).json()
    assert d["pairs"][0]["png_url"].startswith("/frames/barnard/d2/diff_")


@pytest.mark.parametrize("params,status", [
    ({"target": "pluto", "band": 2}, 404),
    ({"target": "barnard", "band": 5}, 404),
    ({"target": "barnard", "band": 9}, 400),
    ({"band": 2}, 400),
    ({"ra": 400, "dec": 0, "band": 2}, 400),
    ({"ra": 10, "dec": 0, "band": 2, "fov_arcmin": 30}, 400),
])
def test_errors_are_plain_messages(params, status):
    r = client.get("/api/frames", params=params)
    assert r.status_code == status
    assert set(r.json()) == {"error"} and r.json()["error"]


def test_unknown_endpoint():
    r = client.get("/api/nothing")
    assert r.status_code == 404 and "error" in r.json()


def test_any_position_starts_a_job_then_reports_its_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "JOBS_DIR", tmp_path)
    calls = []

    def fake_render(*args, **kwargs):
        calls.append(args)
        raise main.NoImages("No SPHEREx images of RA 10.0000° Dec +20.0000° in D2")

    monkeypatch.setattr(main, "render_frames", fake_render)
    monkeypatch.setattr(main, "_pool", type("Now", (), {"submit": staticmethod(lambda f, *a: f(*a))})())
    monkeypatch.setattr(main, "_jobs", {})
    r = client.get("/api/frames", params={"ra": 10, "dec": 20, "band": 2})
    assert r.status_code == 404 and "No SPHEREx images" in r.json()["error"]
    assert len(calls) == 1


def test_working_job_answers_202(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(main, "_pool", type("Later", (), {"submit": staticmethod(lambda f, *a: None)})())
    monkeypatch.setattr(main, "_jobs", {})
    r = client.get("/api/frames", params={"ra": 10, "dec": -20, "band": 2})
    assert r.status_code == 202 and r.json()["status"] == "working"
