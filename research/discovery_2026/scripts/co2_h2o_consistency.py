"""Is the visit-to-visit H2O depth scatter of variable protostars a change of ice column? Test with CO2.

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/co2_h2o_consistency.py

If the ice column in front of the near-infrared continuum changes by a fraction c, CO2 changes by the same fraction
(CO2 ice is mixed with H2O ice in protostellar envelopes). The CO2 band is partly saturated, so its equivalent
width responds with g = d ln EW / d ln tau < 1, evaluated per target from its fitted band shape and mean tau.
CO2 consecutive pairs (quality_ok, detected) then constrain c through r_i ~ N(0, e_i^2 + (c g_i)^2), r = dEW/EW.
This is compared with the apparent H2O scatter s from intrinsic_scatter.py, on all VAR targets and on the targets
with both bands usable. Also reported: Spearman |z_H2O| vs |dln cont| in VAR, and VAR vs CTRL |z_H2O| at matched
|dln cont| (VAR pairs restricted to the CTRL range).
Output: EXPERIMENTAL_RESULTS/population/co2_h2o_consistency.json
"""
import csv
import json

import numpy as np
from scipy import stats

import ice_fit as I

POP = I.ROOT / "EXPERIMENTAL_RESULTS" / "population"
ICE = I.ROOT / "EXPERIMENTAL_RESULTS" / "ice"
GRID = np.linspace(0.0, 2.0, 4001)


def g_factor(name):
    fit = json.load(open(ICE / f"{name}.json"))["bands"]["CO2"]["fit"]
    shape = fit["shape"]
    tau = float(np.mean([e["tau"] for e in fit["epochs"]]))
    h = 0.01 * max(tau, 0.05)
    ew = I.equivalent_width(tau, "CO2", shape)
    d = (I.equivalent_width(tau + h, "CO2", shape) - I.equivalent_width(tau - h, "CO2", shape)) / (2 * h)
    return tau * d / ew, tau


def profile(r, e, g):
    v = e[:, None] ** 2 + (GRID[None, :] * g[:, None]) ** 2
    L = 0.5 * np.sum(r[:, None] ** 2 / v + np.log(v), 0)
    i = int(np.argmin(L))
    above = np.where((GRID > GRID[i]) & (L - L[i] >= 2.71 / 2))[0]
    return float(GRID[i]), float(GRID[above[0]]) if len(above) else float("nan"), L


def main():
    rows = [x for x in csv.DictReader(open(POP / "pairs.csv"))
            if x["consecutive"] == "True" and x["quality_ok"] == "True" and x["detected"] == "True"]
    scat = json.load(open(POP / "intrinsic_scatter.json"))
    h2o_var = {x["name"] for x in rows if x["band"] == "H2O" and x["role"] == "VAR"}
    out = {"H2O_apparent_scatter_VAR": scat["H2O_VAR"]}
    co2 = [x for x in rows if x["band"] == "CO2" and x["role"] == "VAR"]
    gs = {n: g_factor(n) for n in {x["name"] for x in co2}}
    out["co2_g_factor"] = {n: {"g": round(v[0], 3), "mean_tau": round(v[1], 3)} for n, v in gs.items()}
    for label, sel in (("all_CO2_VAR", co2), ("both_bands_usable", [x for x in co2 if x["name"] in h2o_var])):
        r = np.array([float(x["d"]) / float(x["mean_depth"]) for x in sel])
        e = np.array([float(x["d_err"]) / float(x["mean_depth"]) for x in sel])
        g = np.array([gs[x["name"]][0] for x in sel])
        c, cu, L = profile(r, e, g)
        s_h2o = scat["H2O_VAR"]["fit_errors"]["s_mle"]
        j = int(np.argmin(abs(GRID - s_h2o)))
        out[label] = {"n_pairs": len(sel), "n_targets": len({x["name"] for x in sel}), "median_g": float(np.median(g)),
                      "column_change_rms_mle": c, "column_change_rms_upper95": cu,
                      "delta_chi2_at_H2O_apparent_s": float(2 * (L[j] - L.min())), "H2O_apparent_s": s_h2o}
        print(label, out[label], flush=True)
    h = [x for x in rows if x["band"] == "H2O"]
    var = [x for x in h if x["role"] == "VAR"]
    ctrl = [x for x in h if x["role"] == "CTRL"]
    zv = np.array([abs(float(x["z"])) for x in var])
    dv = np.array([abs(float(x["dlncont"])) for x in var])
    rho = stats.spearmanr(zv, dv)
    out["H2O_VAR_absz_vs_absdlncont"] = {"rho": float(rho.statistic), "p": float(rho.pvalue), "n": len(var)}
    cmax = max(abs(float(x["dlncont"])) for x in ctrl)
    m = dv <= cmax
    zc = np.array([abs(float(x["z"])) for x in ctrl])
    mw = stats.mannwhitneyu(zv[m], zc, alternative="greater")
    out["H2O_matched_dlncont"] = {"ctrl_max_abs_dlncont": cmax, "n_var": int(m.sum()), "n_ctrl": len(zc),
                                  "median_absz_var": float(np.median(zv[m])), "median_absz_ctrl": float(np.median(zc)),
                                  "mannwhitney_p_var_greater": float(mw.pvalue)}
    print(json.dumps({k: out[k] for k in ("H2O_VAR_absz_vs_absdlncont", "H2O_matched_dlncont")}))
    (POP / "co2_h2o_consistency.json").write_text(json.dumps(out, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    curves = []
    for role, colr in (("VAR", "C3"), ("CTRL", "C0")):
        sel = [x for x in h if x["role"] == role]
        r = np.array([float(x["d"]) / float(x["mean_depth"]) for x in sel])
        e = np.array([float(x["d_err"]) / float(x["mean_depth"]) for x in sel])
        curves.append((f"H2O apparent depth, {role} ({len(sel)} pairs)", colr, "-", profile(r, e, np.ones_like(r))[2]))
    r = np.array([float(x["d"]) / float(x["mean_depth"]) for x in co2])
    e = np.array([float(x["d_err"]) / float(x["mean_depth"]) for x in co2])
    g = np.array([gs[x["name"]][0] for x in co2])
    curves.append((f"ice column from CO2, VAR ({len(co2)} pairs)", "k", "--", profile(r, e, g)[2]))
    for label, colr, ls, L in curves:
        ax.plot(GRID, 2 * (L - L.min()), color=colr, ls=ls, label=label)
    ax.axhline(2.71, color="0.5", lw=0.8, ls=":")
    ax.text(0.41, 2.9, "one-sided 95 %", fontsize=7, color="0.4")
    ax.set_xlim(0, 0.45)
    ax.set_ylim(0, 16)
    ax.set_xlabel("rms fractional change between consecutive epochs")
    ax.set_ylabel("Δ(−2 ln L)")
    ax.set_title("Visit-to-visit ice variability (quality, ice-detected pairs)", fontsize=10)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(POP / "co2_h2o_consistency.png", dpi=110)


if __name__ == "__main__":
    main()
