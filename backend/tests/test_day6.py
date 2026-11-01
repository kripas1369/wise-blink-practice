"""Offline tests for Day 6: the flipbook GIF and the links to the original files at IRSA."""
import io
import json
from pathlib import Path

import pytest
from astropy.io import fits
from PIL import Image

from backend.app.gif import build_gif
from backend.app.originals import FORMAT as ORIGINALS_FORMAT

FRAMES = Path("frontend/frames")
FOLDERS = sorted(p.parent for p in FRAMES.glob("*/d*/manifest.json"))


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_gif_has_one_frame_per_visit_with_whole_pixel_enlargement(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    gif = Image.open(io.BytesIO(build_gif(folder)))
    assert gif.n_frames == len(manifest["frames"]) and gif.info.get("loop") == 0
    assert gif.size[0] % manifest["size_px"] == 0


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_originals_list_exactly_the_exposures_that_were_added_up(folder):
    path = folder / "originals.json"
    assert path.exists(), "run python -m backend.app.originals on this folder"
    o = json.loads(path.read_text())
    manifest = json.loads((folder / "manifest.json").read_text())
    table = fits.getdata(folder / "exposures.fits", "EXPOSURES")
    assert o["format"] == ORIGINALS_FORMAT and o["missing"] == [] and o["band"] == manifest["band"]
    for i, f in enumerate(o["frames"]):
        assert sorted(e["obs_id"] for e in f["exposures"]) == sorted(
            str(r["OBS_ID"]).strip() for r in table if int(r["FRAME"]) == i)
        for e in f["exposures"]:
            assert e["file_url"].startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/")
            assert e["file_url"].endswith(".fits") and f"D{manifest['band']}_spx" in e["file_url"]
            assert e["datalink_url"].endswith(f"{e['obs_id']}/D{manifest['band']}")
