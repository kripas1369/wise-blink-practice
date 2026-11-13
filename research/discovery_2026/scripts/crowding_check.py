"""Crowding check: does a jointly fitted neighbour change when the target's H2O depth changes?

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/crowding_check.py NAME [K ...]

phot.py fits the target and its AllWISE neighbours simultaneously; the neighbour amplitudes are stored in
neigh_flux_jy in the order of data/neighbours/NAME.json, restricted to those inside the fit box. The check is only
valid when every stamp kept the same neighbours (constant n_src), which is verified. For each requested neighbour
index K the same H2O joint fit is run on the neighbour fluxes. Neighbour amplitude errors are not stored; the
target's error in the same exposure is used as a stand-in (both are background limited in the same pixels), so the
neighbour chi2 and p-values are indicative only.
Output: VALIDATION/crowding_NAME.json and crowding_NAME.png
"""
import json
import math
import sys
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import ice_fit as I

OUT = I.ROOT / "VALIDATION"


def main():
    name = sys.argv[1]
    ks = [int(k) for k in sys.argv[2:]] or [0, 1]
    nb = json.load(open(I.ROOT / "data" / "neighbours" / f"{name}.json"))
    rows = list(csv.DictReader(open(I.PHOT / f"{name}.csv")))
    nsrc = {r["n_src"] for r in rows if r["status"] == "ok"}
    if len(nsrc) != 1:
        raise SystemExit(f"n_src varies {nsrc}; neighbour order is not fixed")
    pts, _, _ = I.load(name)
    by_key = {(round(float(r["mjd"]), 6), round(float(r["wl_um"]), 6)): r for r in rows if r["status"] == "ok"}
    band = I.BANDS["H2O"]
    eps = [e for e in I.epochs_for(pts, band) if e["complete"]]
    for e in eps:
        for p in e["pts"]:
            r = by_key[(round(p["mjd"], 6), round(p["wl"], 6))]
            nf = [float(v) for v in r["neigh_flux_jy"].split(";")]
            for k in ks:
                p[f"n{k}"] = nf[k]
    out = {"target": name, "n_src": int(nsrc.pop()), "neighbours": {}}
    tf = I.joint_fit(eps, "H2O")
    out["target_tau"] = [round(e["tau"], 3) for e in tf["epochs"]]
    out["target_cont_3um_mjy"] = [round(1e3 * e["cont_jy"], 2) for e in tf["epochs"]]
    fig, ax = plt.subplots(1, len(ks) + 1, figsize=(5 * (len(ks) + 1), 4))
    cols = plt.cm.viridis(np.linspace(0, 0.85, len(eps)))
    for j, (key, label) in enumerate([("f", "target")] + [(f"n{k}", nb["neighbours"][k]["designation"]) for k in ks]):
        for e, c in zip(eps, cols):
            lam = np.array([p["wl"] for p in e["pts"]])
            f = np.array([p[key] for p in e["pts"]])
            ax[j].plot(lam, 1e3 * f, ".", color=c, label=f"epoch {e['epoch']} MJD {e['mjd'][0]:.0f}")
        ax[j].set_title(label, fontsize=9)
        ax[j].set_xlabel("wavelength (um)")
        ax[j].set_ylabel("PSF-fit flux (mJy)")
        ax[j].set_xlim(1.6, 5.0)
    ax[0].legend(fontsize=7)
    for k in ks:
        s = nb["neighbours"][k]
        t = nb["target"]
        sep = math.hypot((s["ra"] - t["ra"]) * math.cos(math.radians(t["dec"])), s["dec"] - t["dec"]) * 3600
        res = I.joint_fit(eps, "H2O", flux_key=f"n{k}", err_key="e")
        info = {"designation": s["designation"], "sep_arcsec": round(sep, 1), "w1": s.get("w1"), "w2": s.get("w2")}
        if res:
            info.update({"tau": [round(e["tau"], 3) for e in res["epochs"]],
                         "tau_err_indicative": [round(e["tau_err"], 3) for e in res["epochs"]],
                         "cont_3um_mjy": [round(1e3 * e["cont_jy"], 2) for e in res["epochs"]],
                         "chi2r": round(res["chi2r"], 2)})
            h0 = I.joint_fit(eps, "H2O", flux_key=f"n{k}", err_key="e", common_tau=True)
            ct = I.change_test(h0, res, len(eps))
            info["p_change_indicative"] = ct["p"] if ct else None
        out["neighbours"][k] = info
        print(info, flush=True)
    fig.tight_layout()
    fig.savefig(OUT / f"crowding_{name}.png", dpi=110)
    (OUT / f"crowding_{name}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "neighbours"}))


if __name__ == "__main__":
    main()
