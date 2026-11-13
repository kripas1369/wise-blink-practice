"""Is a continuum change extinction-like or not, and does the H2O ice depth follow it? (H11 / mission section 7.6)

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/colour_diagnostic.py

For each H2O epoch of each target, three continuum points are taken from the same epoch:
    F_H  median forced-photometry flux at 1.60-1.80 um (D3)
    F_K  median flux at 2.05-2.35 um (D3)
    F_L  ice-fit continuum model at 3.95 um (cont_jy * (3.95/3)^alpha), i.e. outside the ice band
For consecutive epochs the colour ratio R = dlnF_K / dlnF_L is compared with an interstellar extinction law, for which
R_ext = A_K / A_3.95 (about 1.9; Indebetouw et al. 2005: A_[3.6]/A_K = 0.56, A_[4.5]/A_K = 0.43, interpolated). The
H2O ice depth change expected if the extra extinction were by cold dense-cloud material is
    dtau_pred = (tau_3.0 / A_K)_dense * dA_K,  dA_K = -dlnF_K / 0.921,
with tau_3.0/A_V = 0.06-0.07 above the ice threshold (Whittet et al.) and A_K/A_V = 0.112, i.e. tau/A_K ~ 0.55.
EC 53 (accretion-driven variability) gives an empirical non-extinction reference.
Output: EXPERIMENTAL_RESULTS/colour/colour_pairs.csv, colour_summary.json, colour_diagnostic.png
"""
import csv
import json
import math

import numpy as np
from scipy import stats

import ice_fit as I

OUT = I.ROOT / "EXPERIMENTAL_RESULTS" / "colour"
SAMPLE = I.ROOT / "data" / "lists" / "sample.csv"
R_EXT = 1.0 / 0.52
TAU_PER_AK = 0.55
POP = I.ROOT / "EXPERIMENTAL_RESULTS" / "population" / "targets.csv"


def band_flux(pts, lo, hi):
    f = np.array([p["f"] for p in pts if lo <= p["wl"] <= hi])
    if len(f) < 2:
        return None, None
    med = float(np.median(f))
    err = float(1.2533 * np.std(f) / math.sqrt(len(f))) if len(f) > 2 else float(abs(f[0] - f[1]) / 2)
    return med, err


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    roles = {r["name"]: r["role"] for r in csv.DictReader(open(SAMPLE))}
    qual = {}
    for r in csv.DictReader(open(POP)):
        if r["band"] == "H2O":
            qual[r["name"]] = (r["quality_ok"] == "True", r.get("detected") == "True")
    rows = []
    for name, role in roles.items():
        jf = I.OUT / f"{name}.json"
        if not jf.exists():
            continue
        res = json.loads(jf.read_text())
        b = res["bands"].get("H2O", {})
        fit = b.get("fit")
        if not fit or len(fit["epochs"]) < 2:
            continue
        pts, _, _ = I.load(name)
        eps = {e["epoch"]: e for e in I.epochs_for(pts, I.BANDS["H2O"]) if e["complete"]}
        per = []
        for fe in fit["epochs"]:
            e = eps.get(fe["epoch"])
            if e is None:
                per = []
                break
            fh, fhe = band_flux(e["pts"], 1.60, 1.80)
            fk, fke = band_flux(e["pts"], 2.05, 2.35)
            fl = fe["cont_jy"] * (3.95 / 3.0) ** fe["alpha"]
            per.append({"epoch": fe["epoch"], "tau": fe["tau"], "tau_err": fe["tau_err"], "F_H": fh, "F_K": fk,
                        "F_K_err": fke, "F_L": fl})
        for a, c in zip(per[:-1], per[1:]):
            if not (a["F_K"] and c["F_K"] and a["F_K"] > 0 and c["F_K"] > 0):
                continue
            dk = math.log(c["F_K"] / a["F_K"])
            dl = math.log(c["F_L"] / a["F_L"])
            dh = math.log(c["F_H"] / a["F_H"]) if a["F_H"] and c["F_H"] and a["F_H"] > 0 and c["F_H"] > 0 else None
            dtau = c["tau"] - a["tau"]
            rows.append({"name": name, "role": role, "a": a["epoch"], "b": c["epoch"],
                         "quality_ok": qual.get(name, (False, False))[0], "ice_detected": qual.get(name, (False, False))[1],
                         "tau_a": a["tau"], "dtau": dtau, "dtau_err": math.hypot(a["tau_err"], c["tau_err"]),
                         "dlnF_H": dh, "dlnF_K": dk, "dlnF_L": dl,
                         "colour_ratio_K_over_L": dk / dl if abs(dl) > 0.05 else None,
                         "dtau_pred_icy_extinction": -TAU_PER_AK * dk / 0.921})
    with open(OUT / "colour_pairs.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def sel(r, big=0.3):
        return r["ice_detected"] and r["quality_ok"] and abs(r["dlnF_L"]) >= big

    big = [r for r in rows if sel(r) and r["role"] in ("VAR", "VALIDATION")]
    summ = {"R_ext_predicted": R_EXT, "tau_per_AK_dense": TAU_PER_AK,
            "pairs_with_abs_dlnF_L_ge_0.3": len(big), "pairs": []}
    for r in big:
        summ["pairs"].append({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    sub = [r for r in rows if r["ice_detected"] and r["quality_ok"] and r["role"] == "VAR"]
    if len(sub) >= 5:
        x = np.array([r["dtau_pred_icy_extinction"] for r in sub])
        y = np.array([r["dtau"] for r in sub])
        e = np.array([r["dtau_err"] for r in sub])
        w = 1 / e ** 2
        k = float(np.sum(w * x * y) / np.sum(w * x * x))
        ke = float(1 / math.sqrt(np.sum(w * x * x)))
        chi = float(np.sum(w * (y - k * x) ** 2) / max(len(y) - 1, 1))
        summ["fraction_of_icy_extinction_prediction"] = {
            "n_pairs": len(sub), "k": k, "k_err": ke * math.sqrt(max(chi, 1)), "chi2r": chi,
            "spearman_dtau_vs_dlnFK": (lambda s: {"rho": float(s.statistic), "p": float(s.pvalue)})(
                stats.spearmanr(y, [r["dlnF_K"] for r in sub]))}
    (OUT / "colour_summary.json").write_text(json.dumps(summ, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
    col = {"VAR": "C3", "CTRL": "C0", "BGSTAR": "C2", "VALIDATION": "k"}
    for role in ("CTRL", "VAR", "VALIDATION"):
        r = [x for x in rows if x["role"] == role and x["ice_detected"]]
        if not r:
            continue
        ax[0].scatter([x["dlnF_L"] for x in r], [x["dlnF_K"] for x in r], s=14, color=col[role], label=role)
        ax[1].errorbar([x["dtau_pred_icy_extinction"] for x in r], [x["dtau"] for x in r],
                       [x["dtau_err"] for x in r], fmt="o", ms=3, color=col[role], label=role, alpha=0.8)
    g = np.linspace(-2.3, 1.2, 10)
    ax[0].plot(g, R_EXT * g, "k--", lw=0.8, label=f"extinction law (R = {R_EXT:.1f})")
    ax[0].plot(g, g, "k:", lw=0.8, label="grey (R = 1)")
    ax[0].set_xlabel("Δ ln F(3.95 µm)")
    ax[0].set_ylabel("Δ ln F(2.05–2.35 µm)")
    ax[0].set_title("Colour of the continuum change (consecutive visits, ice-detected)", fontsize=9)
    ax[0].legend(fontsize=7)
    h = np.linspace(-1.2, 1.5, 10)
    ax[1].plot(h, h, "k--", lw=0.8, label="ice follows extinction (dense-cloud τ/A_K)")
    ax[1].axhline(0, color="0.5", lw=0.6)
    ax[1].set_xlabel("Δτ predicted if the K-band change were icy extinction")
    ax[1].set_ylabel("measured Δτ(H2O)")
    ax[1].set_title("Does the ice depth follow the continuum change?", fontsize=9)
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "colour_diagnostic.png", dpi=95)
    plt.close(fig)
    print(json.dumps({k: v for k, v in summ.items() if k != "pairs"}, indent=1))
    for p in summ["pairs"]:
        print(p)


if __name__ == "__main__":
    main()
