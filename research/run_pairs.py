"""Coverage, which-star test and figure for a list of TESS-EBs duplicate pairs, one after another (DR1 + QR3).

    PYTHONPATH=. .venv/bin/python research/run_pairs.py A1 B1 A2 B2 ...

A pair is tested only if SPHEREx has at least MIN_PRIMARY exposures in the primary eclipse.
"""
import json
import shutil
import sys
import time
from pathlib import Path

import dr1
import plot_pair
import which_star_pair as W
from backend.app import eclipses as E

MIN_PRIMARY = 8
OUT = Path(__file__).parent / "out"


def main(ids):
    log = OUT / f"run_pairs_{ids[0]}.json"
    done = json.loads(log.read_text()) if log.exists() else {}
    for a, b in zip(ids[::2], ids[1::2]):
        t0 = time.time()
        ea, eb = E.by_tess_id(a), E.by_tess_id(b)
        clock = min((ea, eb), key=lambda e: e.phase_error(4000))
        try:
            ims = dr1.images(ea)
        except Exception as exc:
            print(f"TIC {a}: archive failed: {exc}", flush=True)
            continue
        fc = E.forecast(clock, ims)
        n = sum(v["n_images"] for v in fc["per_detector"].values())
        print(f"\n=== TIC {a} / TIC {b}: {n} images (DR1+QR3), {fc['n_primary']} in primary, {fc['n_secondary']} in "
              f"secondary, clock TIC {clock.tess_id} phase error {fc['phase_error']} [{time.time() - t0:.0f} s]", flush=True)
        entry = {"n_images": n, "n_primary": fc["n_primary"], "n_secondary": fc["n_secondary"],
                 "phase_error": fc["phase_error"], "tested": False}
        if fc["n_primary"] >= MIN_PRIMARY:
            folder = OUT / f"pair_{a}_{b}"
            if folder.exists() and "collections" not in json.loads((folder / "result.json").read_text()):
                shutil.move(folder, OUT / f"pair_{a}_{b}_qr3only")
            try:
                W.run(a, b)
                plot_pair.main(a, b)
                entry["tested"] = True
            except Exception as exc:
                print(f"  test failed: {exc!r}", flush=True)
                entry["error"] = repr(exc)
        done[f"{a}_{b}"] = entry
        log.write_text(json.dumps(done, indent=1))
        print(f"  [{time.time() - t0:.0f} s]", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
