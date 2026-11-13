"""Leave-one-out stability of an H2O depth change (single bad exposure / single spectral region test).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/jackknife.py NAME

(1) every exposure inside the H2O fit range is removed in turn; (2) every 0.15 um block of channels is removed in
turn from all epochs. For each refit the per-epoch tau and the largest consecutive |z| are recorded.
Output: VALIDATION/jackknife_NAME.json
"""
import json
import sys

import numpy as np

import ice_fit as I

OUT = I.ROOT / "VALIDATION"


def summarise(fit):
    taus = [e["tau"] for e in fit["epochs"]]
    errs = [e["tau_err"] for e in fit["epochs"]]
    z = [(taus[k + 1] - taus[k]) / np.hypot(errs[k + 1], errs[k]) for k in range(len(taus) - 1)]
    return taus, z


def main():
    name = sys.argv[1]
    pts, _, _ = I.load(name)
    band = I.BANDS["H2O"]
    lo, hi = band["fit"]
    eps = [e for e in I.epochs_for(pts, band) if e["complete"]]
    base_t, base_z = summarise(I.joint_fit(eps, "H2O"))
    loo = []
    for k, e in enumerate(eps):
        for j, p in enumerate(e["pts"]):
            if not lo <= p["wl"] <= hi:
                continue
            e2 = [dict(x, pts=[q for i, q in enumerate(x["pts"]) if not (kk == k and i == j)])
                  for kk, x in enumerate(eps)]
            f = I.joint_fit(e2, "H2O")
            if f:
                t, z = summarise(f)
                loo.append({"epoch": e["epoch"], "wl": round(p["wl"], 3), "det": p["det"], "tau": t, "z": z})
    blocks = []
    for b0 in np.arange(lo, hi, 0.15):
        e2 = [dict(x, pts=[q for q in x["pts"] if not b0 <= q["wl"] < b0 + 0.15]) for x in eps]
        f = I.joint_fit(e2, "H2O")
        if f:
            t, z = summarise(f)
            blocks.append({"block_um": [round(float(b0), 2), round(float(b0) + 0.15, 2)], "tau": t, "z": z})
    zs = np.array([r["z"] for r in loo])
    zb = np.array([r["z"] for r in blocks])
    out = {"target": name, "baseline_tau": base_t, "baseline_z": base_z, "n_leave_one_out": len(loo),
           "loo_z_min": zs.min(0).tolist(), "loo_z_max": zs.max(0).tolist(),
           "loo_tau_range": [np.min([r["tau"] for r in loo], 0).tolist(), np.max([r["tau"] for r in loo], 0).tolist()],
           "block_z_min": zb.min(0).tolist(), "block_z_max": zb.max(0).tolist(),
           "blocks": blocks, "leave_one_out": loo}
    (OUT / f"jackknife_{name}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("blocks", "leave_one_out")}, indent=1))
    for b in blocks:
        print(b["block_um"], [round(v, 3) for v in b["tau"]], [round(v, 2) for v in b["z"]])


if __name__ == "__main__":
    main()
