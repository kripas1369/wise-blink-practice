"""SPHEREx DR1+QR3 coverage and TESS-clock eclipse forecast for TESS-EBs entries whose Gaia EB is another star.

    PYTHONPATH=.:research .venv/bin/python research/coverage_candidates.py TIC [TIC ...]
-> research/out/coverage_candidates.json (one entry per TIC, skipped if already there)

The forecast uses the TIC entry's own clock: if the eclipse is on the Gaia neighbour, its timing is the same.
"""
import json
import sys
import time
from pathlib import Path

from backend.app import eclipses as E

import dr1

OUT = Path(__file__).parent / "out"
SITE_CATALOG = Path(__file__).resolve().parents[1] / "frontend/frames/eclipse/catalog.json"


def main(tics):
    path = OUT / "coverage_candidates.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    on_site = SITE_CATALOG.read_text()
    singles = {e["tic"]: e for e in json.loads((OUT / "misattributed_singles.json").read_text())["singles"]}
    for tic in tics:
        if tic in done:
            continue
        t0 = time.time()
        eph = E.by_tess_id(tic)
        try:
            ims = dr1.images(eph)
        except Exception as exc:
            print(f"TIC {tic}: archive failed: {exc}", flush=True)
            continue
        fc = E.forecast(eph, ims)
        mjd = [im.mjd for v in ims.values() for im in v]
        n = len(mjd)
        o = singles[tic]["other"][0] if tic in singles else None
        done[tic] = {"n_images": n, "n_primary": fc["n_primary"], "n_secondary": fc["n_secondary"],
                     "phase_error": fc["phase_error"], "mjd_range": [min(mjd), max(mjd)] if mjd else None,
                     "per_detector": {str(d): v["n_images"] for d, v in fc["per_detector"].items()},
                     "on_website_catalog": f'"{tic}"' in on_site or f": {tic}" in on_site,
                     "gaia_eb": o}
        path.write_text(json.dumps(done, indent=1))
        print(f"TIC {tic}: {n} images, {fc['n_primary']} primary, {fc['n_secondary']} secondary, phase error "
              f"{fc['phase_error']} [{time.time() - t0:.0f} s]", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
