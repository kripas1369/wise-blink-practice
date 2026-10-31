"""Live tests against SIMBAD and IRSA. Run with:  RUN_NETWORK=1 python -m pytest backend/tests/test_network.py"""
import os

import pytest

from backend.app import archive
from backend.app.resolve import resolve_name

pytestmark = pytest.mark.skipif(not os.environ.get("RUN_NETWORK"), reason="set RUN_NETWORK=1")


def test_resolve_barnard():
    star = resolve_name("Barnard's Star")
    assert star["ra"] == pytest.approx(269.452, abs=0.01)
    assert star["pmdec"] > 10000


def test_unknown_name_raises():
    with pytest.raises(LookupError):
        resolve_name("notastar123xyz")


def test_barnard_has_spherex_images_in_all_detectors():
    images = archive.find_images(269.446269, 4.768204)
    assert len(images) > 100
    assert {im.detector for im in images} == {1, 2, 3, 4, 5, 6}


def test_known_object_check_finds_ceres():
    """A test spot 6″ east and 4″ north of Ceres (JPL Horizons, geocentric, 2026-08-21 17:17 UTC), seen from
    SPHEREx at Barnard's third visit. On 31 Oct 2026 JPL's first pass put Ceres 10.1″ away (its error: 13″)."""
    import json
    import math

    from backend.app import known_objects
    spots = json.loads(open("frontend/frames/barnard/d2/spots.json").read())
    ra0, dec0 = 93.17311, 22.56610
    spot = {"ra": ra0 + 6 / 3600 / math.cos(math.radians(dec0)), "dec": dec0 + 4 / 3600}
    r = known_objects.check(spot, spots["observers"][2], 6.15)
    if r["outcome"] == "unavailable":
        pytest.skip(f"JPL unavailable: {r['reason']}")
    assert r["outcome"] == "match" and r["matches"][0]["name"].startswith("1 Ceres")
