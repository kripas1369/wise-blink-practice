"""Archive coverage statistics for ARCHIVE_COVERAGE.md (from OBSERVATION_TIMELINES/index.csv and CANDIDATE_CATALOG.csv).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/coverage_summary.py

Prints Markdown tables to stdout and writes OBSERVATION_TIMELINES/coverage_summary.json.
"""
import collections
import csv
import json

import numpy as np

import ice_fit as I

ROLES = ("VAR", "CTRL", "BGSTAR", "VALIDATION")


def main():
    tl = list(csv.DictReader(open(I.ROOT / "OBSERVATION_TIMELINES" / "index.csv")))
    cat = {r["name"]: r for r in csv.DictReader(open(I.ROOT / "CANDIDATE_CATALOG.csv"))}
    by = collections.defaultdict(list)
    for r in tl:
        by[r["name"]].append(r)
    out = {}
    print("| Role | Targets | Exposures read (median, range) | Visits per target | Targets with ≥ 2 passes in a visit "
          "| H2O sweep per visit, days (median, range) | CO2 sweep, days | H2O complete epochs (0/1/2/3+) "
          "| CO2 complete epochs (0/1/2/3+) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for role in ROLES:
        names = [n for n, v in by.items() if v[0]["role"] == role]
        nexp = [int(cat[n]["n_exposures_read"]) for n in names if cat.get(n, {}).get("n_exposures_read")]
        nvis = collections.Counter(len(by[n]) for n in names)
        multi = sum(any(int(v["n_passes"]) > 1 for v in by[n]) for n in names)
        sw_h = [float(v["H2O_sweep_days"]) for n in names for v in by[n] if v["H2O_sweep_days"] not in ("", "nan")]
        sw_c = [float(v["CO2_sweep_days"]) for n in names for v in by[n] if v["CO2_sweep_days"] not in ("", "nan")]

        def hist(b):
            c = collections.Counter(min(int(cat[n].get(f"{b}_n_epochs") or 0), 3) for n in names if n in cat)
            return "/".join(str(c.get(k, 0)) for k in range(4))

        res = {"targets": len(names), "exposures_median": float(np.median(nexp)) if nexp else None,
               "exposures_range": [min(nexp), max(nexp)] if nexp else None,
               "visits": dict(sorted(nvis.items())), "targets_with_multi_pass_visit": multi,
               "h2o_sweep_days_median": float(np.median(sw_h)) if sw_h else None,
               "h2o_sweep_days_range": [min(sw_h), max(sw_h)] if sw_h else None,
               "co2_sweep_days_median": float(np.median(sw_c)) if sw_c else None,
               "h2o_epoch_hist": hist("H2O"), "co2_epoch_hist": hist("CO2")}
        out[role] = res
        vis = ", ".join(f"{k}: {v}" for k, v in sorted(nvis.items()))
        print(f"| {role} | {len(names)} | {res['exposures_median']:.0f} ({min(nexp)}–{max(nexp)}) | {vis} | {multi} "
              f"| {res['h2o_sweep_days_median']:.1f} ({min(sw_h):.1f}–{max(sw_h):.1f}) "
              f"| {res['co2_sweep_days_median']:.1f} | {res['h2o_epoch_hist']} | {res['co2_epoch_hist']} |")
    rel = collections.Counter(v["releases"] for v in tl)
    out["visit_rows_by_release"] = dict(rel)
    out["visit_rows"] = len(tl)
    print("\nvisit rows by release:", dict(rel))
    (I.ROOT / "OBSERVATION_TIMELINES" / "coverage_summary.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
