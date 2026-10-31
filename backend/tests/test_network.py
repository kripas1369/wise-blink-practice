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
