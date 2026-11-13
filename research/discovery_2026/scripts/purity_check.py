"""Sample-purity sensitivity check: repeat the key population statistics without targets that SIMBAD identifies as
objects that cannot be protostars (post hoc; the SIMBAD cross-match only became available after the population
analysis because CDS was down).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/purity_check.py

Excluded SIMBAD object types (nearest object within 15"): nova (No*), planetary nebula (PN, PN?), Mira (Mi*),
long-period variable (LP*, LP?), AGB candidate (AB?), high-proper-motion star (PM*), spectroscopic binary (SB*).
Applies to VAR and CTRL (BGSTAR are background stars by design). Recomputed: ice detection rates, VAR vs controls
(CTRL + BGSTAR, floor-corrected |z|, ice-detected, quality — as in population.py), apparent H2O scatter, CO2-inferred
column limit and its Δχ² at the H2O scatter.
Output: EXPERIMENTAL_RESULTS/population/purity_check.json
"""
import csv
import json

import numpy as np
from scipy import stats

import ice_fit as I
from co2_h2o_consistency import g_factor, profile

POP = I.ROOT / "EXPERIMENTAL_RESULTS" / "population"
NON_YSO = {"No*", "PN", "PN?", "Mi*", "LP*", "LP?", "AB?", "PM*", "SB*"}


def main():
    xm = list(csv.DictReader(open(I.ROOT / "data" / "selection" / "simbad_xmatch.csv")))
    excl = {r["name"]: f"{r['simbad_main_id']} ({r['simbad_otype']})" for r in xm
            if r["role"] in ("VAR", "CTRL") and r["simbad_otype"] in NON_YSO}
    targets = [t for t in csv.DictReader(open(POP / "targets.csv")) if t["name"] not in excl]
    pairs = [p for p in csv.DictReader(open(POP / "pairs.csv")) if p["name"] not in excl]
    out = {"excluded": excl, "n_excluded_var": sum(1 for r in xm if r["name"] in excl and r["role"] == "VAR"),
           "n_excluded_ctrl": sum(1 for r in xm if r["name"] in excl and r["role"] == "CTRL")}

    det = {}
    for band in ("H2O", "CO2"):
        def count(role):
            t = [x for x in targets if x["band"] == band and x["role"] == role and x["mean_depth"] not in ("", "None")]
            return sum(x["detected"] == "True" for x in t), len(t)
        vd, vn = count("VAR")
        cd, cn = count("CTRL")
        tab = [[vd, vn - vd], [cd, cn - cd]]
        det[band] = {"VAR": f"{vd}/{vn}", "CTRL": f"{cd}/{cn}",
                     "fisher_p_two_sided": float(stats.fisher_exact(tab)[1]),
                     "fisher_p_var_greater": float(stats.fisher_exact(tab, alternative="greater")[1])}
    out["ice_detection_rate"] = det

    good = [p for p in pairs if p["consecutive"] == "True" and p["quality_ok"] == "True" and p["detected"] == "True"]
    comp = {}
    for band in ("H2O", "CO2"):
        zv = [abs(float(p["z_floor"])) for p in good if p["band"] == band and p["role"] == "VAR"]
        zc = [abs(float(p["z_floor"])) for p in good if p["band"] == band and p["role"] in ("CTRL", "BGSTAR")]
        comp[band] = {"n_var": len(zv), "n_ctrl": len(zc), "median_absz_var": float(np.median(zv)),
                      "median_absz_ctrl": float(np.median(zc)),
                      "mannwhitney_p": float(stats.mannwhitneyu(zv, zc, alternative="greater").pvalue)}
    out["var_vs_ctrl_detected_quality"] = comp

    h = [p for p in good if p["band"] == "H2O" and p["role"] == "VAR"]
    r = np.array([float(p["d"]) / float(p["mean_depth"]) for p in h])
    e = np.array([float(p["d_err"]) / float(p["mean_depth"]) for p in h])
    s, s_ul, _ = profile(r, e, np.ones_like(r))
    c = [p for p in good if p["band"] == "CO2" and p["role"] == "VAR"]
    rc = np.array([float(p["d"]) / float(p["mean_depth"]) for p in c])
    ec = np.array([float(p["d_err"]) / float(p["mean_depth"]) for p in c])
    g = np.array([g_factor(p["name"])[0] for p in c])
    col, col_ul, L = profile(rc, ec, g)
    j = int(np.argmin(abs(np.linspace(0.0, 2.0, 4001) - s)))
    out["h2o_apparent_scatter_var"] = {"n_pairs": len(h), "s_mle": s, "s_upper95": s_ul}
    out["co2_column_var"] = {"n_pairs": len(c), "mle": col, "upper95": col_ul,
                             "delta_chi2_at_h2o_s": float(2 * (L[j] - L.min()))}
    print(json.dumps(out, indent=1))
    (POP / "purity_check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
