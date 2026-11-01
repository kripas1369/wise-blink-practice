"""When SPHEREx looked at a position: every image whose footprint contains it, grouped into visits.

/api/coverage answers with coverage_answer(); for the 5 official targets the same answer is saved as
frontend/frames/<target>/coverage.json, so the website's timeline works without the data API too.

    python -m backend.app.coverage barnard eps_ind_b      # writes coverage.json for these targets
"""
import argparse
import json
from datetime import datetime, timezone

from backend.app import archive
from backend.app.config import REPO_ROOT

FORMAT = "spherex-blink-coverage/1"
PREPARED_DIR = REPO_ROOT / "frontend" / "frames"


def coverage_answer(ra: float, dec: float, band: int | None = None) -> dict:
    """Raises archive.ArchiveError when IRSA does not answer."""
    images = archive.find_images(ra, dec, detector=band)
    return {
        "format": FORMAT,
        "ra": ra, "dec": dec, "band": band,
        "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "summary": archive.summarize(images),
        "images": [{"obs_id": im.obs_id, "band": im.detector, "mjd": round(im.mjd, 5),
                    "wl_min_um": round(im.wl_min_um, 4), "wl_max_um": round(im.wl_max_um, 4),
                    "release": im.collection, "release_date": im.release_date} for im in images],
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx spherex.obscore",
    }


def write_coverage(target: str) -> dict:
    """coverage.json for a prepared target, at the position of its frames (any detector folder)."""
    manifest_path = next(iter(sorted((PREPARED_DIR / target).glob("d*/manifest.json"))), None)
    if manifest_path is None:
        raise FileNotFoundError(f"{PREPARED_DIR / target}: no prepared frames")
    manifest = json.loads(manifest_path.read_text())
    answer = coverage_answer(manifest["ra"], manifest["dec"])
    (PREPARED_DIR / target / "coverage.json").write_text(json.dumps(answer, indent=1) + "\n")
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("targets", nargs="+")
    for target in parser.parse_args().targets:
        s = write_coverage(target)["summary"]
        print(f"{target}: {s['n_images']} images, {s['n_epochs']} visits, {s['first']} to {s['last']}, "
              f"latest release {s.get('latest_release')}")


if __name__ == "__main__":
    main()
