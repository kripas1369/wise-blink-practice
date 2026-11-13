"""Summary figure of one candidate: ice depths in every analysis variant and the continuum, per epoch.

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/candidate_figure.py NAME

Reads EXPERIMENTAL_RESULTS/ice/NAME.json (measured values only). Output: EXPERIMENTAL_RESULTS/figures/candidate_NAME.png
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import ice_fit as I


def main():
    name = sys.argv[1]
    d = json.load(open(I.OUT / f"{name}.json"))
    h, c = d["bands"]["H2O"], d["bands"]["CO2"]
    tm = {e["epoch"]: np.mean(e["mjd"]) for e in h["epochs"] if e["complete"]}
    tc = {e["epoch"]: np.mean(e["mjd"]) for e in c["epochs"] if e["complete"]}
    fits = {"baseline": h["fit"], "aperture photometry": h["fit_aperture"], "no drift term": h["fit_nodrift"]}
    fits.update({k: v["fit"] for k, v in h["variants"].items()})
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    for k, (lab, f) in enumerate(fits.items()):
        x = np.array([tm[e["epoch"]] for e in f["epochs"]]) + (k - 3) * 2.5
        ax[0].errorbar(x, [e["tau"] for e in f["epochs"]], [e["tau_err"] for e in f["epochs"]], fmt="o-", ms=4,
                       lw=0.8, label=lab, color="k" if lab == "baseline" else None)
    ax[0].set_ylabel("τ (H2O, 3.05 µm)")
    ax[0].set_title(f"{name}: H2O depth, 7 analyses", fontsize=9)
    ax[0].legend(fontsize=6)
    for lab, f, key, scale, unit in (("τ", c["fit"], "tau", 1, ""), ("EW", c["fit"], "ew_um", 1e3, " (nm)")):
        if lab == "τ":
            a = ax[1]
            a.errorbar([tc[e["epoch"]] for e in f["epochs"]], [e["tau"] for e in f["epochs"]],
                       [e["tau_err"] for e in f["epochs"]], fmt="s-", color="C3", label="τ CO2")
            a.set_ylabel("τ (CO2, 4.27 µm)", color="C3")
        else:
            b = ax[1].twinx()
            b.errorbar(np.array([tc[e["epoch"]] for e in f["epochs"]]) + 3, [scale * e[key] for e in f["epochs"]],
                       [scale * e["ew_err_um"] for e in f["epochs"]], fmt="d--", color="C4", label="EW CO2")
            b.set_ylabel("EW CO2" + unit, color="C4")
    ax[1].set_title("CO2 depth and equivalent width", fontsize=9)
    ax[2].semilogy([tm[e["epoch"]] for e in h["fit"]["epochs"]], [1e3 * e["cont_jy"] for e in h["fit"]["epochs"]],
                   "o-", color="C0", label="continuum at 3.0 µm (H2O fit)")
    ax[2].semilogy([tc[e["epoch"]] for e in c["fit"]["epochs"]], [1e3 * e["cont_jy"] for e in c["fit"]["epochs"]],
                   "s-", color="C2", label="continuum at 4.27 µm (CO2 fit)")
    ax[2].set_ylabel("mJy")
    ax[2].set_title("Continuum", fontsize=9)
    ax[2].legend(fontsize=7)
    for a in ax:
        a.set_xlabel("MJD")
    fig.tight_layout()
    out = I.ROOT / "EXPERIMENTAL_RESULTS" / "figures"
    out.mkdir(exist_ok=True)
    fig.savefig(out / f"candidate_{name}.png", dpi=110)


if __name__ == "__main__":
    main()
