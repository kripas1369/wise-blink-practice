"""Stamps -> photometry -> ice fit for every row of a target list (CSV with columns name, ra, dec).

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/run_targets.py LIST.csv [--workers 24]

Targets whose stamp file already exists are not downloaded again. A failure of one target is logged and the run
continues. Log: EXPERIMENTAL_RESULTS/run_log.jsonl (one line per target and step).
"""
import argparse
import csv
import json
import time
import traceback
from datetime import datetime, timezone

import ice_fit
import phot
import spx_s3 as S

LOG = ice_fit.ROOT / "EXPERIMENTAL_RESULTS" / "run_log.jsonl"


def log(**kw):
    kw["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(LOG, "a") as f:
        f.write(json.dumps(kw) + "\n")


def one(name, ra, dec, workers):
    t0 = time.time()
    if not (S.STAMPS / f"{name}.npz").exists():
        _, meta = S.extract(name, ra, dec, workers=workers)
        log(name=name, step="stamps", n_found=meta["n_images_found"], n_ok=meta["n_accepted"],
            seconds=round(time.time() - t0, 1))
    t1 = time.time()
    rows, nb = phot.run(name)
    log(name=name, step="phot", n=len(rows), n_ok=sum(r.get("status") == "ok" for r in rows),
        target=nb["target"].get("designation"), seconds=round(time.time() - t1, 1))
    res, pts = ice_fit.analyse(name)
    (ice_fit.OUT / f"{name}.json").write_text(json.dumps(res, indent=1))
    ice_fit.plot(name, res, pts)
    log(name=name, step="ice", bands={b: {"n_complete": v["n_complete"],
                                          "p_change": (v.get("change_test") or {}).get("p")}
                                      for b, v in res["bands"].items()}, seconds=round(time.time() - t0, 1))
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("targets")
    p.add_argument("--workers", type=int, default=24)
    a = p.parse_args()
    ice_fit.OUT.mkdir(parents=True, exist_ok=True)
    for r in csv.DictReader(open(a.targets)):
        name = r["name"]
        try:
            res = one(name, float(r["ra"]), float(r["dec"]), a.workers)
            print(name, ice_fit.summary_line(res).replace("\n", "\n   "), flush=True)
        except Exception as exc:  # noqa: BLE001 - one bad target must not stop the batch; the error is logged
            log(name=name, step="error", error=repr(exc), tb=traceback.format_exc()[-1500:])
            print(name, "ERROR", repr(exc), flush=True)


if __name__ == "__main__":
    main()
