"""Stage E: candidate list for the multi-epoch ice-band test, from SPLICES (SPHEREx ices target list) at IRSA.

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/select_targets.py

Step 1 (this script, `query`): every SPLICES source that is a protostar or flat-spectrum YSO (by the literature
class_1 or the machine-learning stype_ml) and bright enough in W2 for per-exposure ice-band photometry.
The query is a fixed ADQL string run as an IRSA TAP async job; the result is saved verbatim with the query text.
Selection of variables and matched controls from that table is done in `choose` (see TARGET_SELECTION.md).
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from astropy.table import Table

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "selection"
TAP = "https://irsa.ipac.caltech.edu/TAP/async"
COLUMNS = ("designation, name, ra, dec, k, w1, w2, w3, w4, w1err, w2err, cc_flags, ext_flg, var_flg, sel_type, "
           "class_1, yso_pub, stype_ml, stype_ml_prob2, classvar, w1var_class, w2var_class, w1varavg, w2varavg, "
           "w1varamp, w2varamp, av, mc, mc_dist, mc_los, numiracnbors, mindistirac, fluxratioi1, fluxratioi2, "
           "sv_w1, sv_w2, sv_w2_v, sv_w2_t")
ADQL = (f"SELECT {COLUMNS} FROM splices WHERE w2 > 4.0 AND w2 < 10.5 AND "
        "(class_1 IN ('YSO_P', 'YSO_F') OR stype_ml IN ('Class I YSO', 'Flat spectrum YSO'))")


def async_query(adql, stem, poll=10, limit=3600):
    r = requests.post(TAP, data={"QUERY": adql, "LANG": "ADQL", "FORMAT": "csv", "PHASE": "RUN"},
                      allow_redirects=False, timeout=120)
    job = r.headers.get("Location") or r.url
    print("TAP job", job, flush=True)
    t0 = time.time()
    while time.time() - t0 < limit:
        phase = requests.get(f"{job}/phase", timeout=60).text.strip()
        if phase == "COMPLETED":
            res = requests.get(f"{job}/results/result", timeout=600)
            raw = OUT / f"{stem}.raw.csv"
            raw.write_bytes(res.content)
            return Table.read(raw, format="ascii.csv"), job
        if phase in ("ERROR", "ABORTED"):
            raise RuntimeError(f"TAP job {job} {phase}: {requests.get(f'{job}/error', timeout=60).text[:500]}")
        time.sleep(poll)
    raise TimeoutError(job)


ADQL_BACKGROUND = (f"SELECT {COLUMNS} FROM splices WHERE sel_type = 'MAIN' AND w2 > 6.0 AND w2 < 9.0 AND av > 25 "
                   "AND w2var_class = 'N' AND mc_los = 'BE'")


def main():
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "protostars"
    adql, stem = (ADQL, "splices_protostars_w2lt10p5") if which == "protostars" else \
        (ADQL_BACKGROUND, "splices_background_stars")
    t0 = time.time()
    t, job = async_query(adql, stem)
    t.write(OUT / f"{stem}.csv", overwrite=True)
    (OUT / f"{stem}_query.json").write_text(json.dumps(
        {"adql": adql, "service": TAP, "job": job, "rows": len(t), "seconds": round(time.time() - t0, 1),
         "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=1))
    print(len(t), "rows in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
