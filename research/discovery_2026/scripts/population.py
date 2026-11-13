"""Population analysis of the per-epoch ice fits (EXPERIMENTAL_RESULTS/ice/*.json) for the sample in
data/lists/sample.csv: variable protostars (VAR), W2-matched non-variable protostars (CTRL), background stars (BGSTAR)
and the validation objects.

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/population.py

Quality selection (fixed before the population statistics were looked at): a target-band enters the primary analysis
if it has >= 2 complete epochs and the joint-fit chi2_red <= CHI2_MAX (model describes the photometry to within ~4x the
2 % floor; EC 53 and V1647 Ori have 4.5). The same statistics without the chi2 cut are reported as a sensitivity check.

Quantities (per target and band, H2O 3 um and CO2 4.27 um):
  * no-change F-test p (H0: one depth for all epochs); Benjamini-Hochberg FDR over all target-band tests.
  * pairwise depth changes between epochs, z = d/sigma. H2O uses tau, CO2 uses the equivalent width (saturated band).
  * robust change: baseline |z| >= 3 AND the same pair has the same sign with |z| >= 2 in every alternative analysis
    (aperture photometry; for H2O also no-drift, wider range with D3, no blue window, curved continuum, narrow red).
  * empirical systematic floor: the extra per-pair scatter s that makes the CTRL+BGSTAR z distribution unit-variance
    (MAD-based); every z is then re-evaluated as d / sqrt(sigma^2 + s^2).
  * ice response: for ice-detected targets, d ln(depth) against d ln(continuum) for consecutive epoch pairs;
    weighted slope with errors from a bootstrap over targets (pairs of one target are not independent).
  * merged-visit bias (secondary question H10): one fit to all complete epochs as if they were a single spectrum
    (no per-epoch continuum, one CO2 normalisation) compared with the per-epoch fit.

Output: EXPERIMENTAL_RESULTS/population/{targets.csv, pairs.csv, summary.json, *.png}.
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

import ice_fit as I

ROOT = I.ROOT
SAMPLE = ROOT / "data" / "lists" / "sample.csv"
OUT = ROOT / "EXPERIMENTAL_RESULTS" / "population"
SEED = 20261113
Z_ROBUST = 3.0
Z_VARIANT = 2.0
DETECT_SNR = 5.0
FDR = 0.05
CHI2_MAX = 15.0
H2O_VARIANTS = ("with_D3_2.10", "no_blue_window_2.80", "curved_continuum", "narrow_red_3.90")


def sample_rows():
    rows = list(csv.DictReader(open(SAMPLE)))
    return {r["name"]: r for r in rows}


def quantity(bname):
    return ("tau", "tau_err", "dtau", "dtau_err") if bname == "H2O" else ("ew_um", "ew_err_um", "dew_um", "dew_err_um")


def alt_pairs(b, bname):
    out = {"aperture": b.get("pairs_aperture")}
    if bname == "H2O":
        out["nodrift"] = b.get("pairs_nodrift")
        for v in H2O_VARIANTS:
            out[v] = ((b.get("variants") or {}).get(v) or {}).get("pairs")
    return out


def bh(p):
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    adj = np.empty(n)
    run = 1.0
    for rank, i in reversed(list(enumerate(o, 1))):
        run = min(run, p[i] * n / rank)
        adj[i] = run
    return adj


def collect():
    meta = sample_rows()
    targets, pairs = [], []
    for name, m in meta.items():
        f = I.OUT / f"{name}.json"
        if not f.exists():
            continue
        res = json.loads(f.read_text())
        for bname, b in res.get("bands", {}).items():
            fit = b.get("fit")
            val, err, dk, dek = quantity(bname)
            t = {"name": name, "role": m["role"], "pair": m.get("pair", ""), "w2var_class": m.get("w2var_class", ""),
                 "w2varamp": m.get("w2varamp", ""), "w2": m.get("w2", ""), "band": bname,
                 "n_complete": b["n_complete"], "p_change": (b.get("change_test") or {}).get("p"),
                 "chi2r": fit["chi2r"] if fit else None}
            if fit:
                v = np.array([e[val] for e in fit["epochs"]])
                ve = np.array([e[err] for e in fit["epochs"]])
                w = 1 / np.maximum(ve, 1e-9) ** 2
                t["mean_depth"] = float(np.sum(w * v) / np.sum(w))
                t["mean_depth_err"] = float(1 / math.sqrt(np.sum(w)))
                t["detected"] = t["mean_depth"] / t["mean_depth_err"] >= DETECT_SNR and t["mean_depth"] > 0
                cont = [e["cont_jy"] for e in fit["epochs"]]
                t["cont_min_mjy"], t["cont_max_mjy"] = 1e3 * min(cont), 1e3 * max(cont)
                t["max_abs_dlncont"] = float(math.log(max(cont) / min(cont))) if min(cont) > 0 else None
            targets.append(t)
            alts = alt_pairs(b, bname)
            for k, p in enumerate(b.get("pairs") or []):
                d, de = p[dk], p[dek]
                row = {"name": name, "role": m["role"], "band": bname, "a": p["a"], "b": p["b"],
                       "consecutive": k in consecutive_index(len(b["fit"]["epochs"])),
                       "d": d, "d_err": de, "z": d / de if de else None, "dlncont": p["dlncont"],
                       "detected": t.get("detected", False),
                       "mean_depth": t.get("mean_depth")}
                ok = row["z"] is not None and abs(row["z"]) >= Z_ROBUST
                agree, nalt = 0, 0
                for an, ap in alts.items():
                    if not ap or k >= len(ap):
                        ok = False
                        continue
                    q = ap[k]
                    qd, qe = q[dk], q[dek]
                    zq = qd / qe if qe else 0.0
                    row[f"z_{an}"] = zq
                    nalt += 1
                    if np.sign(zq) == np.sign(d) and abs(zq) >= Z_VARIANT:
                        agree += 1
                    else:
                        ok = False
                row["n_alt"], row["n_alt_agree"], row["robust"] = nalt, agree, bool(ok)
                pairs.append(row)
    return targets, pairs


def consecutive_index(E):
    """Indices of the (i, i+1) pairs in the order produced by ice_fit.pairs."""
    idx, k = [], 0
    for i in range(E):
        for j in range(i + 1, E):
            if j == i + 1:
                idx.append(k)
            k += 1
    return set(idx)


def systematic_floor(pairs, band):
    """Extra scatter s (same units as d) that makes control z unit-variance; consecutive pairs only."""
    c = [p for p in pairs if p["band"] == band and p["role"] in ("CTRL", "BGSTAR") and p["consecutive"]
         and p["z"] is not None and p["detected"]]
    if len(c) < 5:
        return {"n": len(c), "s": 0.0, "mad_z": None}
    d = np.array([p["d"] for p in c])
    e = np.array([p["d_err"] for p in c])
    madz = 1.4826 * np.median(np.abs(d / e - np.median(d / e)))

    def f(s):
        z = d / np.sqrt(e ** 2 + s ** 2)
        return 1.4826 * np.median(np.abs(z - np.median(z))) - 1.0

    s = 0.0
    if f(0.0) > 0:
        lo, hi = 0.0, 10 * np.median(np.abs(d)) + 1e-6
        while f(hi) > 0:
            hi *= 2
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
        s = 0.5 * (lo + hi)
    return {"n": len(c), "s": float(s), "mad_z": float(madz)}


def response(pairs, band, roles, floor, rng, nboot=2000):
    """Slope of d ln depth on d ln continuum for detected targets, consecutive pairs; bootstrap over targets."""
    rows = [p for p in pairs if p["band"] == band and p["role"] in roles and p["consecutive"] and p["detected"]
            and p["dlncont"] is not None and p["mean_depth"] and p["mean_depth"] > 0]
    if len(rows) < 4:
        return {"n_pairs": len(rows)}
    names = sorted({p["name"] for p in rows})
    x = np.array([p["dlncont"] for p in rows])
    y = np.array([p["d"] / p["mean_depth"] for p in rows])
    ye = np.array([math.hypot(p["d_err"], floor) / p["mean_depth"] for p in rows])

    def slope(ix):
        w = 1 / ye[ix] ** 2
        xm = np.sum(w * x[ix]) / np.sum(w)
        ym = np.sum(w * y[ix]) / np.sum(w)
        den = np.sum(w * (x[ix] - xm) ** 2)
        return np.nan if den <= 0 else np.sum(w * (x[ix] - xm) * (y[ix] - ym)) / den

    allix = np.arange(len(rows))
    s0 = slope(allix)
    byname = {n: np.array([i for i, p in enumerate(rows) if p["name"] == n]) for n in names}
    boots = []
    for _ in range(nboot):
        pick = rng.choice(names, len(names), replace=True)
        ix = np.concatenate([byname[n] for n in pick])
        boots.append(slope(ix))
    boots = np.array([b for b in boots if np.isfinite(b)])
    return {"n_pairs": len(rows), "n_targets": len(names), "slope": float(s0),
            "slope_err_boot": float(np.std(boots)), "slope_ci95": [float(np.percentile(boots, 2.5)),
                                                                   float(np.percentile(boots, 97.5))],
            "dlncont_range": [float(x.min()), float(x.max())]}


def merged_bias(name, bname):
    """Fit all complete epochs as one merged spectrum; compare with the per-epoch fit."""
    try:
        pts, _, _ = I.load(name)
    except FileNotFoundError:
        return None
    if not pts:
        return None
    band = I.BANDS[bname]
    good = [e for e in I.epochs_for(pts, band) if e["complete"]]
    if len(good) < 2:
        return None
    merged = [{"epoch": "merged", "pts": [p for e in good for p in e["pts"]]}]
    old = I.GROUP_DT
    try:
        if bname == "CO2":
            I.GROUP_DT = 1e6
        fm = I.joint_fit(merged, bname, drift=False)
    finally:
        I.GROUP_DT = old
    fe = I.joint_fit(good, bname, drift=False)
    if fm is None or fe is None:
        return None
    val, err, _, _ = quantity(bname)
    v = np.array([e[val] for e in fe["epochs"]])
    ve = np.array([e[err] for e in fe["epochs"]])
    w = 1 / np.maximum(ve, 1e-9) ** 2
    mean_e = float(np.sum(w * v) / np.sum(w))
    m = fm["epochs"][0]
    return {"merged": m[val], "merged_err": m[err], "per_epoch_mean": mean_e,
            "per_epoch_mean_err": float(1 / math.sqrt(np.sum(w))), "bias": m[val] - mean_e,
            "chi2r_merged": fm["chi2r"], "chi2r_epoch": fe["chi2r"], "n_epochs": len(good)}


def plots(targets, pairs, floors, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"VAR": "C3", "CTRL": "C0", "BGSTAR": "C2", "VALIDATION": "k"}
    fig, ax = plt.subplots(2, 2, figsize=(11, 8.5))
    for j, band in enumerate(("H2O", "CO2")):
        unit, scale = ("Δτ", 1.0) if band == "H2O" else ("ΔEW (nm)", 1e3)
        a = ax[0, j]
        for role in ("CTRL", "BGSTAR", "VAR", "VALIDATION"):
            r = [p for p in pairs if p["band"] == band and p["role"] == role and p["consecutive"] and p["z"] is not None
                 and p["detected"]]
            if r:
                a.errorbar([p["dlncont"] for p in r], [scale * p["d"] for p in r], [scale * p["d_err"] for p in r],
                           fmt="o", ms=3, color=col[role], alpha=0.7, label=f"{role} ({len(r)})")
        a.axhline(0, color="0.5", lw=0.8)
        a.set_xlabel("Δ ln continuum (consecutive epochs)")
        a.set_ylabel(unit)
        a.set_title(f"{band}: depth change vs continuum change (ice-detected)")
        a.legend(fontsize=7)
        a = ax[1, j]
        s = floors[band]["s"]
        bins = np.linspace(-6, 6, 25)
        for role in ("CTRL", "VAR"):
            z = [p["d"] / math.hypot(p["d_err"], s) for p in pairs if p["band"] == band and p["role"] == role
                 and p["consecutive"] and p["z"] is not None]
            if z:
                a.hist(np.clip(z, -6, 6), bins=bins, histtype="step", color=col[role], label=f"{role} ({len(z)})",
                       density=True)
        g = np.linspace(-6, 6, 200)
        a.plot(g, stats.norm.pdf(g), color="0.4", lw=0.8, ls="--", label="N(0,1)")
        a.set_xlabel(f"z with systematic floor s = {s:.3g}")
        a.set_title(f"{band}: distribution of consecutive-pair z")
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "population_dtau.png", dpi=95)
    plt.close(fig)


def summarise(targets, pairs, rng):
    """All population statistics for one selection of target-bands (pairs already restricted to it)."""
    floors = {b: systematic_floor(pairs, b) for b in ("H2O", "CO2")}
    for p in pairs:
        s = floors[p["band"]]["s"]
        p["z_floor"] = p["d"] / math.hypot(p["d_err"], s) if p["d_err"] else None
        p["robust_floor"] = bool(p["robust"] and p["z_floor"] is not None and abs(p["z_floor"]) >= Z_ROBUST)
    tests = [t for t in targets if t["p_change"] is not None]
    adj = bh([t["p_change"] for t in tests]) if tests else []
    for t, a in zip(tests, adj):
        t["p_bh"] = float(a)
        t["p_bonferroni"] = min(1.0, t["p_change"] * len(tests))
    for t in targets:
        rp = [p for p in pairs if p["name"] == t["name"] and p["band"] == t["band"]]
        t["n_pairs"] = len(rp)
        t["n_robust_pairs"] = sum(p["robust"] for p in rp)
        t["n_robust_floor_pairs"] = sum(p["robust_floor"] for p in rp)
        t["max_abs_z"] = max((abs(p["z"]) for p in rp if p["z"] is not None), default=None)
        t["max_abs_z_floor"] = max((abs(p["z_floor"]) for p in rp if p["z_floor"] is not None), default=None)
    out = {"n_target_bands": len(targets), "n_tests": len(tests), "floors": floors, "by_role": {},
           "comparison": {}, "response": {}}
    for band in ("H2O", "CO2"):
        for role in ("VAR", "CTRL", "BGSTAR", "VALIDATION"):
            ts = [t for t in targets if t["band"] == band and t["role"] == role]
            if not ts:
                continue
            ps = [t["p_change"] for t in ts if t["p_change"] is not None]
            out["by_role"][f"{band}/{role}"] = {
                "n_targets": len(ts), "n_ge3_epochs": sum(t["n_complete"] >= 3 for t in ts),
                "n_detected": sum(bool(t.get("detected")) for t in ts),
                "n_tested": len(ps), "n_p_lt_0.05": sum(p < 0.05 for p in ps),
                "n_bh_significant": sum(1 for t in ts if t.get("p_bh") is not None and t["p_bh"] < FDR),
                "bh_significant": [t["name"] for t in ts if t.get("p_bh") is not None and t["p_bh"] < FDR],
                "n_with_robust_pair": sum(t["n_robust_pairs"] > 0 for t in ts),
                "with_robust_pair": [t["name"] for t in ts if t["n_robust_pairs"] > 0],
                "n_with_robust_floor_pair": sum(t["n_robust_floor_pairs"] > 0 for t in ts),
                "with_robust_floor_pair": [t["name"] for t in ts if t["n_robust_floor_pairs"] > 0],
                "ks_uniform_p": float(stats.kstest(ps, "uniform").pvalue) if len(ps) >= 5 else None,
                "ks_uniform_p_detected": (lambda q: float(stats.kstest(q, "uniform").pvalue) if len(q) >= 5 else None)(
                    [t["p_change"] for t in ts if t["p_change"] is not None and t.get("detected")])}
        for lab, det in (("all", False), ("ice_detected", True)):
            zv = [abs(p["z_floor"]) for p in pairs if p["band"] == band and p["role"] == "VAR" and p["consecutive"]
                  and p["z_floor"] is not None and (p["detected"] or not det)]
            zc = [abs(p["z_floor"]) for p in pairs if p["band"] == band and p["role"] in ("CTRL", "BGSTAR")
                  and p["consecutive"] and p["z_floor"] is not None and (p["detected"] or not det)]
            pv = [t["p_change"] for t in targets if t["band"] == band and t["role"] == "VAR"
                  and t["p_change"] is not None and (t.get("detected") or not det)]
            pc = [t["p_change"] for t in targets if t["band"] == band and t["role"] in ("CTRL", "BGSTAR")
                  and t["p_change"] is not None and (t.get("detected") or not det)]
            c = {"n_var_pairs": len(zv), "n_ctrl_pairs": len(zc), "n_var_targets": len(pv), "n_ctrl_targets": len(pc),
                 "median_abs_z_var": float(np.median(zv)) if zv else None,
                 "median_abs_z_ctrl": float(np.median(zc)) if zc else None,
                 "frac_abs_z_gt3_var": float(np.mean(np.array(zv) > 3)) if zv else None,
                 "frac_abs_z_gt3_ctrl": float(np.mean(np.array(zc) > 3)) if zc else None,
                 "frac_p_lt_0.05_var": float(np.mean(np.array(pv) < 0.05)) if pv else None,
                 "frac_p_lt_0.05_ctrl": float(np.mean(np.array(pc) < 0.05)) if pc else None}
            if len(zv) >= 5 and len(zc) >= 5:
                c["mannwhitney_abs_z_var_gt_ctrl_p"] = float(stats.mannwhitneyu(zv, zc, alternative="greater").pvalue)
            if len(pv) >= 5 and len(pc) >= 5:
                c["mannwhitney_p_change_var_lt_ctrl_p"] = float(stats.mannwhitneyu(pv, pc, alternative="less").pvalue)
            out["comparison"][f"{band}/{lab}"] = c
        for lab, roles in (("VAR", ("VAR",)), ("CTRL", ("CTRL", "BGSTAR")), ("ALL", ("VAR", "CTRL", "BGSTAR"))):
            out["response"][f"{band}/{lab}"] = response(pairs, band, roles, floors[band]["s"], rng)
    return out, floors


def merged_summary(mb_rows):
    out = {}
    for band in ("H2O", "CO2"):
        for lab, roles in (("VAR", ("VAR",)), ("CTRL", ("CTRL", "BGSTAR")), ("VALIDATION", ("VALIDATION",))):
            r = [x for x in mb_rows if x["band"] == band and x["role"] in roles and x["detected"] and x["quality_ok"]]
            if not r:
                continue
            rel = np.array([x["bias"] / x["per_epoch_mean"] for x in r])
            out[f"{band}/{lab}"] = {
                "n": len(r), "median_bias": float(np.median([x["bias"] for x in r])),
                "median_abs_rel_bias": float(np.median(np.abs(rel))), "max_abs_rel_bias": float(np.max(np.abs(rel))),
                "median_abs_bias_over_epoch_err": float(np.median([abs(x["bias"]) / x["per_epoch_mean_err"] for x in r])),
                "median_err_ratio_merged_over_epoch": float(np.median([x["merged_err"] / x["per_epoch_mean_err"]
                                                                       for x in r])),
                "median_chi2r_ratio": float(np.median([x["chi2r_merged"] / x["chi2r_epoch"] for x in r])),
                "spearman_absrelbias_vs_dlncont": (lambda s: {"rho": float(s.statistic), "p": float(s.pvalue)})(
                    stats.spearmanr(np.abs(rel), [x["max_abs_dlncont"] for x in r])) if len(r) >= 5 else None,
                "spearman_chi2ratio_vs_dlncont": (lambda s: {"rho": float(s.statistic), "p": float(s.pvalue)})(
                    stats.spearmanr([x["chi2r_merged"] / x["chi2r_epoch"] for x in r],
                                    [x["max_abs_dlncont"] for x in r])) if len(r) >= 5 else None}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    targets, pairs = collect()
    for t in targets:
        t["quality_ok"] = bool(t["n_complete"] >= 2 and t["chi2r"] is not None and t["chi2r"] <= CHI2_MAX)
    ok = {(t["name"], t["band"]) for t in targets if t["quality_ok"]}
    for p in pairs:
        p["quality_ok"] = (p["name"], p["band"]) in ok

    import copy
    t_all, p_all = copy.deepcopy([t for t in targets if t["n_complete"] >= 2]), copy.deepcopy(pairs)
    summary_all, _ = summarise(t_all, p_all, np.random.default_rng(SEED))
    t_q = [t for t in targets if t["quality_ok"]]
    p_q = [p for p in pairs if p["quality_ok"]]
    summary_q, floors = summarise(t_q, p_q, np.random.default_rng(SEED))

    mb_rows = []
    for t in targets:
        if t["n_complete"] >= 2:
            r = merged_bias(t["name"], t["band"])
            if r:
                r.update({"name": t["name"], "role": t["role"], "band": t["band"], "quality_ok": t["quality_ok"],
                          "max_abs_dlncont": t.get("max_abs_dlncont"), "detected": t.get("detected")})
                mb_rows.append(r)

    roles = {}
    for t in targets:
        roles.setdefault(t["role"], set()).add(t["name"])
    detection = {}
    for band in ("H2O", "CO2"):
        dv = [bool(t.get("detected")) for t in targets if t["band"] == band and t["role"] == "VAR" and "mean_depth" in t]
        dc = [bool(t.get("detected")) for t in targets if t["band"] == band and t["role"] == "CTRL" and "mean_depth" in t]
        tab = [[sum(dv), len(dv) - sum(dv)], [sum(dc), len(dc) - sum(dc)]]
        detection[band] = {"VAR_detected": tab[0][0], "VAR_n": len(dv), "CTRL_detected": tab[1][0], "CTRL_n": len(dc),
                           "fisher_p": float(stats.fisher_exact(tab).pvalue) if dv and dc else None}
    summary = {"thresholds": {"Z_ROBUST": Z_ROBUST, "Z_VARIANT": Z_VARIANT, "DETECT_SNR": DETECT_SNR, "FDR": FDR,
                              "CHI2_MAX": CHI2_MAX},
               "n_targets_with_fits_by_role": {k: len(v) for k, v in roles.items()},
               "ice_detection_rate_any_quality": detection,
               "quality_selection": summary_q, "no_quality_cut": summary_all,
               "merged_bias": merged_summary(mb_rows)}

    def write(path, rows):
        keys = sorted({k for r in rows for k in r})
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

    write(OUT / "targets.csv", targets)
    write(OUT / "pairs.csv", pairs)
    if mb_rows:
        write(OUT / "merged_bias.csv", mb_rows)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    plots(t_q, p_q, floors, OUT)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
