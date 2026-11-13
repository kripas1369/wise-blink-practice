"""Sensitivity of the no-change test to the epoch boundaries (mission section 13).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/epoch_sensitivity.py

For every target with a photometry file, the baseline joint fit and the common-depth fit are repeated with
alternative epoch definitions:
    baseline        VISIT_GAP 60 d, PASS_GAP 20 d (pass split only if every pass is complete)
    no_pass_split   passes never split (one epoch per visit)
    visit_gap_30    VISIT_GAP 30 d
    visit_gap_120   VISIT_GAP 120 d
    pass_gap_10     PASS_GAP 10 d
Output: EXPERIMENTAL_RESULTS/population/epoch_sensitivity.csv (one row per target, band and setting).
"""
import csv
import json

import ice_fit as I

SETTINGS = {"baseline": (60.0, 20.0), "no_pass_split": (60.0, 1e6), "visit_gap_30": (30.0, 20.0),
            "visit_gap_120": (120.0, 20.0), "pass_gap_10": (60.0, 10.0)}
SAMPLE = I.ROOT / "data" / "lists" / "sample.csv"
OUT = I.ROOT / "EXPERIMENTAL_RESULTS" / "population"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    roles = {r["name"]: r["role"] for r in csv.DictReader(open(SAMPLE))}
    rows = []
    for f in sorted(I.PHOT.glob("*.csv")):
        name = f.stem
        if name not in roles:
            continue
        pts, _, _ = I.load(name)
        if not pts:
            continue
        for sname, (vg, pg) in SETTINGS.items():
            I.VISIT_GAP, I.PASS_GAP = vg, pg
            for bname, band in I.BANDS.items():
                good = [e for e in I.epochs_for(pts, band) if e["complete"]]
                row = {"name": name, "role": roles[name], "band": bname, "setting": sname, "n_epochs": len(good),
                       "epochs": ";".join(e["epoch"] for e in good)}
                if len(good) >= 2:
                    h1 = I.joint_fit(good, bname)
                    h0 = I.joint_fit(good, bname, common_tau=True)
                    ct = I.change_test(h0, h1, len(good))
                    row["p_change"] = ct["p"] if ct else None
                    if h1:
                        key = "tau" if bname == "H2O" else "ew_um"
                        row["depths"] = json.dumps([round(e[key], 5) for e in h1["epochs"]])
                        prs = I.pairs(h1)
                        zk = "z_tau" if bname == "H2O" else "z_ew"
                        row["max_abs_z"] = max((abs(p[zk]) for p in prs if p[zk] is not None), default=None)
                rows.append(row)
        I.VISIT_GAP, I.PASS_GAP = SETTINGS["baseline"]
        print(name, flush=True)
    keys = ["name", "role", "band", "setting", "n_epochs", "epochs", "p_change", "max_abs_z", "depths"]
    with open(OUT / "epoch_sensitivity.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
