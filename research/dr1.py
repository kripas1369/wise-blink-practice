"""SPHEREx image lists from the current IRSA collections, kept apart from the website's cache.

IRSA now serves Data Release 1 (spherex_dr1, spherex_dr1_deep: May 2025 - May 2026) and Quick Release 3
(spherex_qr3, spherex_qr3_deep: from May 2026). The QR2 collections the website was built with return nothing
since DR1 (checked 13 Nov 2026), so new targets are asked for these four.
"""
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from backend.app import archive
from backend.app import eclipses as E
from backend.app.config import DETECTORS

COLLECTIONS = ("spherex_dr1", "spherex_dr1_deep", "spherex_qr3", "spherex_qr3_deep")
CACHE = Path(__file__).parent / "out" / "images"


def images(eph: E.Ephemeris, year: float = 2026.0, refresh: bool = False) -> dict[int, list[archive.SpherexImage]]:
    ra, dec = eph.position(year)
    return images_at(ra, dec, f"tic{eph.tess_id}", refresh, tess_id=eph.tess_id)


def images_at(ra: float, dec: float, key: str, refresh: bool = False,
              tess_id: str | None = None) -> dict[int, list[archive.SpherexImage]]:
    """All DR1 + QR3 images covering (ra, dec), per detector, cached as research/out/images/<key>.json."""
    path = CACHE / f"{key}.json"
    if path.exists() and not refresh:
        saved = json.loads(path.read_text())
        return {int(d): [archive.SpherexImage(**im) for im in ims] for d, ims in saved["images"].items()}
    found = {}
    for d in DETECTORS:
        ims = archive.find_images(ra, dec, collections=COLLECTIONS, detector=d)
        found[d] = [im for im in ims if im.detector == d]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "tess_id": tess_id, "ra": ra, "dec": dec, "collections": list(COLLECTIONS),
        "asked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "images": {d: [asdict(im) for im in ims] for d, ims in found.items()},
    }))
    return found
