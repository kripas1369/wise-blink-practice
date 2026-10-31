"""Offline tests for Day 5: the proof panel (proof.json), spot evidence (spots.json), the known-object check,
the spectrum (spectrum.json)."""
import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import known_objects, main
from backend.app.archive import EPOCH_GAP_DAYS, EPOCH_MAX_SPAN_DAYS
from backend.app.proof import MAX_MOTION_ERROR_PX, build_proof
from backend.app.spectrum import build_spectrum
from backend.app.spots import MAX_SPOTS, build_spots

FRAMES = Path("frontend/frames")


def prepared(target: str, band: int) -> Path:
    return FRAMES / target / f"d{band}"


def test_barnard_and_eps_ind_b_agree_with_gaia_like_the_c4_tests():
    barnard = build_proof(prepared("barnard", 2))["motion"]
    assert barnard["status"] == "agrees"
    assert barnard["method"] == "saturated-core centre"   # the centroid box is not fully usable
    assert barnard["difference_px"] == pytest.approx(0.18, abs=0.01)   # notes/acceptance_c4.json
    eps = build_proof(prepared("eps_ind_b", 2))["motion"]
    assert eps["status"] == "agrees" and eps["method"] == "centroid"
    assert eps["direction_difference_deg"] < 30 and eps["difference_px"] <= MAX_MOTION_ERROR_PX


def test_tiny_or_missing_gaia_motion_is_not_called_a_pass():
    for target in ("rw_aur", "r_dra"):
        m = build_proof(prepared(target, 2))["motion"]
        assert m["status"] == "too_small", target
        assert "cannot test" in m["reason"]
    for band in (2, 6):
        m = build_proof(prepared("wise0855", band))["motion"]
        assert m["status"] == "no_gaia_target" and "expected_px" not in m


def test_data_counts_match_the_manifest():
    for folder in sorted(FRAMES.glob("*/d*")):
        m = json.loads((folder / "manifest.json").read_text())
        d = build_proof(folder)["data"]
        assert d["n_visits"] == len(m["frames"])
        assert d["n_exposures_used"] == sum(f["n_images"] for f in m["frames"])
        assert d["n_exposures_used"] <= d["n_exposures_taken"]
        assert d["releases"] is None and d["releases_reason"] == "not looked up (made offline)"


def test_saved_proof_files_have_irsa_releases_for_every_exposure():
    for folder in sorted(FRAMES.glob("*/d*")):
        p = json.loads((folder / "proof.json").read_text())
        d = p["data"]
        assert d["releases"], folder
        assert "releases_reason" not in d, f"{folder}: {d.get('releases_reason')}"
        assert sum(r["n_exposures"] for r in d["releases"].values()) == d["n_exposures_used"]
        assert p["motion"]["status"] == build_proof(folder)["motion"]["status"]


def test_proof_endpoint():
    client = TestClient(main.app)
    r = client.get("/api/proof", params={"target": "barnard", "band": 2})
    assert r.status_code == 200 and r.json()["motion"]["status"] == "agrees"
    assert client.get("/api/proof", params={"target": "barnard", "band": 5}).status_code == 404


# ---------- spots and the known-object check ----------

def test_spots_match_the_difference_maps():
    for folder in sorted(FRAMES.glob("*/d*")):
        diff = json.loads((folder / "diff.json").read_text())
        saved = json.loads((folder / "spots.json").read_text())
        fresh = build_spots(folder)
        assert [p["n_spots"] for p in fresh["pairs"]] == [p["n_spots"] for p in saved["pairs"]], folder
        for pair, d in zip(fresh["pairs"], diff["pairs"]):
            assert len(pair["spots"]) <= MAX_SPOTS
            for s in pair["spots"]:
                x, y = s["peak_xy"]
                assert d["z"][y][x] == pytest.approx(s["peak_sigma"], abs=0.051)
                assert abs(s["peak_sigma"]) >= 5
                assert s["frame"] == (pair["b"] if s["sign"] > 0 else pair["a"])
                text = " ".join([s["why"], *s["what_else"], *s["confirm"]]).lower()
                assert "new object" not in text and "planet x" not in text


def test_every_prepared_visit_has_the_spacecraft_position():
    for folder in sorted(FRAMES.glob("*/d*")):
        for o in json.loads((folder / "spots.json").read_text())["observers"]:
            assert o["available"], f"{folder} visit {o['epoch_id']}: {o.get('reason')}"
            assert 6500 < math.hypot(*o["xyz_km"]) < 7500   # low Earth orbit, ~700 km up


def test_wise0855_d6_spot_is_next_to_the_gaia_star_not_called_wise():
    pair = next(p for p in build_spots(prepared("wise0855", 6))["pairs"] if (p["a"], p["b"]) == (1, 2))
    near = [s for s in pair["spots"] if s["gaia_star"]["distance_px"] <= 1.5]
    assert len(near) == 1 and near[0]["gaia_star"]["source_id"] == "5756956644387831296"


def test_jpl_box_centre_is_whole_seconds():
    assert known_objects.ra_text(269.4462685) == ("17-57-47", pytest.approx(64667 / 240))
    text, value = known_objects.dec_text(-7.24236)
    assert text == "M07-14-32" and value == pytest.approx(-7.242222, abs=1e-6)


def test_jpl_rows_are_measured_from_the_spot():
    body = {"fields_first": ["Object name", "Astrometric RA (hh:mm:ss)", "Astrometric Dec (dd mm'ss\")",
                             "Dist. from center RA (\")", "Dist. from center Dec (\")", "Dist. from center Norm (\")",
                             "Visual magnitude (V)", "RA rate (\"/h)", "Dec rate (\"/h)", "Est. error RA (\")",
                             "Est. error Dec (\")"],
            "data_first_pass": [["1 Ceres (A801 AA)", "06:12:41", "+22 33'56\"", "5.0", "3.0", "5.8", "8.96",
                                 "-52.9", "1.2", "13.24", "13.24"]]}
    r = known_objects.rows(body, "first", (2.0, -1.0))
    assert r[0]["distance_arcsec"] == pytest.approx(math.hypot(3.0, 4.0))
    assert r[0]["est_error_arcsec"] == [13.24, 13.24] and r[0]["v_mag"] == 8.96


def test_known_objects_endpoint_never_fakes_an_answer(monkeypatch):
    def fail(params):
        raise known_objects.Unavailable("JPL answered HTTP 500 (unexpected error)")
    monkeypatch.setattr(known_objects, "ask", fail)
    monkeypatch.setattr(known_objects, "CACHE", Path("/nonexistent-cache-dir"))
    client = TestClient(main.app)
    r = client.get("/api/known-objects", params={"target": "wise0855", "band": 6, "a": 1, "b": 2, "spot": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "unavailable" and "HTTP 500" in body["reason"]
    assert client.get("/api/known-objects", params={"target": "wise0855", "band": 6, "a": 1, "b": 2,
                                                    "spot": 99}).status_code == 404


def test_spectrum_points_are_exactly_the_light_curve_points():
    spec = build_spectrum(FRAMES / "wise0855")
    got = {(p["band"], p["obs_id"], p["flux_mjy"]) for v in spec["visits"] for p in v["points"]}
    want = set()
    for d in spec["detectors"]:
        lc = json.loads((prepared("wise0855", d["band"]) / "lightcurve.json").read_text())
        want |= {(d["band"], p["obs_id"], p["flux_mjy"]) for p in lc["points"]
                 if p["flux_mjy"] is not None and p["wl_um"] is not None}
    assert got == want and len(got) > 0
    assert [d["band"] for d in spec["detectors"]] == [2, 6]


def test_spectrum_visits_follow_the_archive_rule():
    for target in ("wise0855", "eps_ind_b"):
        visits = build_spectrum(FRAMES / target)["visits"]
        for v in visits:
            assert v["mjd_range"][1] - v["mjd_range"][0] <= EPOCH_MAX_SPAN_DAYS
        for a, b in zip(visits, visits[1:]):
            assert b["mjd_range"][0] - a["mjd_range"][1] > EPOCH_GAP_DAYS \
                or b["mjd_range"][0] - a["mjd_range"][0] > EPOCH_MAX_SPAN_DAYS


def test_spectrum_says_what_can_bias_its_shape():
    warnings = build_spectrum(FRAMES / "wise0855")["warnings"]
    assert any("no aperture correction" in w and "not from the star" in w for w in warnings)
    assert any(w.startswith("D2: inside the circle as well: Gaia DR3 5756956644387831296") for w in warnings)
    barnard = build_spectrum(FRAMES / "barnard")
    assert barnard["visits"] == [] and any(w.startswith("D2: no points.") for w in barnard["warnings"])


def test_spectrum_endpoint():
    client = TestClient(main.app)
    r = client.get("/api/spectrum", params={"target": "wise0855", "band": 6})
    assert r.status_code == 200 and r.json()["format"] == "spherex-blink-spectrum/1"
    assert client.get("/api/spectrum", params={"target": "barnard", "band": 5}).status_code == 404
