"""The coverage timeline's data: /api/coverage and the saved frontend/frames/<target>/coverage.json."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import archive, coverage, main
from backend.app.archive import SpherexImage

TARGETS = ("barnard", "eps_ind_b", "r_dra", "rw_aur", "wise0855")


def image(obs_id: str, det: int, mjd: float) -> SpherexImage:
    return SpherexImage(obs_id=obs_id, did=f"{obs_id}_D{det}", detector=det, mjd_start=mjd, mjd_end=mjd + 0.001,
                        wl_min_um=1.1, wl_max_um=1.62, release_date="2026-04-21 00:00:00", collection="spherex_qr2")


def test_answer_lists_every_image_and_its_visits(monkeypatch):
    found = [image("2025W33_1A_0001_1", 2, 60900.0), image("2025W33_1A_0001_1", 6, 60900.0),
             image("2026W10_1A_0002_1", 2, 61100.0)]
    monkeypatch.setattr(archive, "find_images", lambda ra, dec, detector=None: found)
    a = coverage.coverage_answer(269.45, 4.77)
    assert a["format"] == coverage.FORMAT and a["band"] is None and "IRSA" in a["data_credit"]
    assert [(im["band"], im["release"]) for im in a["images"]] == [(2, "spherex_qr2"), (6, "spherex_qr2"),
                                                                   (2, "spherex_qr2")]
    assert a["summary"]["n_images"] == 3 and a["summary"]["n_epochs"] == 2


def test_endpoint_says_when_irsa_does_not_answer(monkeypatch):
    def down(ra, dec, detector=None):
        raise archive.ArchiveError("IRSA TAP did not answer after 3 tries")
    monkeypatch.setattr(archive, "find_images", down)
    r = TestClient(main.app).get("/api/coverage", params={"ra": 269.45, "dec": 4.77})
    assert r.status_code >= 500 and "IRSA" in r.json()["error"]


@pytest.mark.parametrize("target", TARGETS)
def test_saved_coverage_is_at_the_frames_position_and_counts_add_up(target):
    path = coverage.PREPARED_DIR / target / "coverage.json"
    c = json.loads(path.read_text())
    m = json.loads(next(iter(sorted(path.parent.glob("d*/manifest.json")))).read_text())
    assert c["format"] == coverage.FORMAT and (c["ra"], c["dec"]) == (m["ra"], m["dec"])
    s = c["summary"]
    assert s["n_images"] == len(c["images"]) == sum(s["per_detector"].values())
    assert sum(s["per_collection"].values()) == s["n_images"]
    assert all(1 <= im["band"] <= 6 for im in c["images"])
