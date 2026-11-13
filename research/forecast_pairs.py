"""SPHEREx coverage of TESS-EBs "duplicate" pairs (one eclipse period listed under two nearby TIC stars).

    PYTHONPATH=. .venv/bin/python research/forecast_pairs.py [tess_id ...]

For each pair, the archive is asked (once, cached) which SPHEREx images contain the first star; the forecast
says how many fall in the primary and secondary eclipse. Output: research/out/forecast_pairs.json
"""
import json
import sys
import time
from pathlib import Path

from backend.app import eclipses as E

OUT = Path(__file__).parent / "out"

PAIRS = [
    ("150101476", "150101472", "SEP"),
    ("276935987", "276935996", "SEP"),
    ("140659978", "140659980", "SEP"),
    ("279569707", "279569718", "SEP"),
    ("356015357", "356015361", "NEP"),
    ("258918831", "258918835", "NEP"),
    ("420114776", "420114772", "NEP"),
    ("280033934", "280033918", "NEP"),
    ("198242676", "198242678", "NEP"),
    ("377192658", "377192659", "NEP"),
    # all-sky survey, short periods with wide eclipses (research/out/all_duplicate_pairs.json)
    ("220402294", "220402290", "south"),
    ("161687311", "161687316", "north"),
    ("55753808", "55753802", "north"),
    ("159854359", "159854358", "north"),
    ("164558072", "164558055", "north"),
    ("294092960", "294092966", "south"),
    ("199574208", "199574211", "north"),
    # Gaia DR3 does not flag either star with the TESS period (research/out/gaia_pairs.json)
    ("269696430", "269696438", "north"),
    ("202442974", "202442982", "north"),
    ("259006185", "259006174", "north"),
    ("146601322", "146601318", "south"),
    ("238896417", "238896431", "south"),
    ("389754101", "389754103", "south"),
    ("159864583", "159864610", "north"),
    ("243391171", "243391162", "north"),
    ("48227278", "48227288", "north"),
    ("16805617", "16805614", "north"),
    # no VSX, Gaia or TESS Ten Thousand answer either (research/out/vsx_pairs.json)
    ("99028324", "99028319", "?"),
    ("356974629", "356974639", "?"),
    ("124712820", "124712813", "?"),
]


def main() -> None:
    only = set(sys.argv[1:])
    OUT.mkdir(exist_ok=True)
    path = OUT / "forecast_pairs.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    for a, b, field in PAIRS:
        if only and a not in only:
            continue
        if a in done and not only:
            continue
        eph = E.by_tess_id(a)
        clock = min((eph, E.by_tess_id(b)), key=lambda e: e.phase_error(4000))
        t0 = time.time()
        try:
            fc = E.forecast(clock, E.cached_images(eph))
        except Exception as exc:  # keep going; the archive is sometimes busy
            print(f"TIC {a}: failed {exc}", flush=True)
            continue
        done[a] = {"partner": b, "field": field, "period": eph.period, "tmag": eph.tmag,
                   "prim_depth": eph.prim_depth, "sec_depth": eph.sec_depth, **fc}
        n = sum(v["n_images"] for v in fc["per_detector"].values())
        print(f"TIC {a} ({field}): {n} images, {fc['n_primary']} primary, {fc['n_secondary']} secondary, "
              f"phase error {fc['phase_error']}  [{time.time() - t0:.0f} s]", flush=True)
        path.write_text(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
