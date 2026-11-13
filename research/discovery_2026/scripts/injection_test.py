"""Injection-recovery test of the joint ice fit (SIMULATED perturbations of real photometry; validation only).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/injection_test.py NAME [NAME ...]

For each target the real per-exposure fluxes are kept, and the LAST complete epoch is perturbed in one of these ways:
  * depth   : multiply by < exp(-(tau_e + dtau) phi) > / < exp(-tau_e phi) > with the target's fitted band shape and
              last-epoch depth tau_e (dtau = 0.05 ... 0.5 for H2O, 0.5 ... 4 for CO2), i.e. a pure change of the
              absorption depth (the ratio form is needed for the saturated, partly resolved CO2 band);
  * gray    : multiply by a constant (x2 and x0.5), a pure achromatic continuum change, true depth change 0;
  * colour  : multiply by (lam / lam0)^k (k = +-1), a continuum slope change, true depth change 0;
  * scatter : add a blue scattered-light component 0.3 * F_cont(lam0) * (lam / lam0)^-4 without absorption,
              true intrinsic depth change 0 (an apparent filling-in of the band is expected and is what is measured).
The joint fit and the no-change test are then repeated. Output: VALIDATION/injection_NAME.json and a summary table
VALIDATION/injection_summary.csv. Nothing produced here is an astronomical measurement.
"""
import copy
import csv
import json
import math
import sys

import numpy as np

import ice_fit as I

OUT = I.ROOT / "VALIDATION"
DEPTHS = {"H2O": [0.05, 0.1, 0.2, 0.3, 0.5], "CO2": [0.5, 1.0, 2.0, 4.0]}


def perturb(epoch, bname, shape, kind, val, cont_jy, tau_e):
    lam0 = I.BANDS[bname]["lam0"]
    e = copy.deepcopy(epoch)
    for p in e["pts"]:
        lam, bw = np.array([p["wl"]]), np.array([p["bw"]])
        if kind == "depth":
            fac = float(I.band_avg(lam, bw, np.array([tau_e + val]), bname, shape)[0]
                        / I.band_avg(lam, bw, np.array([tau_e]), bname, shape)[0])
        elif kind == "gray":
            fac = val
        elif kind == "colour":
            fac = (p["wl"] / lam0) ** val
        elif kind == "scatter":
            add = val * cont_jy * (p["wl"] / lam0) ** -4
            fac = (p["f"] + add) / p["f"]
        else:
            raise ValueError(kind)
        for k in ("f", "ap"):
            if np.isfinite(p[k]):
                p[k] *= fac
        for k in ("e", "ap_e"):
            if np.isfinite(p[k]):
                p[k] *= abs(fac)
    return e


def run(name):
    pts, _, _ = I.load(name)
    out = {"name": name, "note": "SIMULATED perturbations of real photometry; not an observation", "bands": {}}
    for bname, band in I.BANDS.items():
        good = [e for e in I.epochs_for(pts, band) if e["complete"]]
        if len(good) < 2:
            continue
        base = I.joint_fit(good, bname)
        if base is None:
            continue
        key, ekey = ("tau", "tau_err") if bname == "H2O" else ("ew_um", "ew_err_um")
        b0 = base["epochs"]
        d0 = b0[-1][key] - b0[0][key]
        trials = [("none", 0.0)] + [("depth", v) for v in DEPTHS[bname]] + [("gray", 2.0), ("gray", 0.5),
                                                                             ("colour", 1.0), ("colour", -1.0),
                                                                             ("scatter", 0.3)]
        rows = []
        for kind, val in trials:
            eps = list(good)
            if kind != "none":
                eps[-1] = perturb(good[-1], bname, base["shape"], kind, val, b0[-1]["cont_jy"], b0[-1]["tau"])
            f1 = I.joint_fit(eps, bname)
            f0 = I.joint_fit(eps, bname, common_tau=True)
            ct = I.change_test(f0, f1, len(eps))
            last, first = f1["epochs"][-1], f1["epochs"][0]
            d = last[key] - first[key]
            de = math.hypot(last[ekey], first[ekey])
            inj_tau = val if kind == "depth" else 0.0
            inj_ew = (I.equivalent_width(b0[-1]["tau"] + inj_tau, bname, base["shape"]) - I.equivalent_width(
                b0[-1]["tau"], bname, base["shape"])) if kind == "depth" else 0.0
            rows.append({"kind": kind, "value": val,
                         "injected_change": inj_tau if bname == "H2O" else inj_ew,
                         "recovered_change_minus_baseline": d - d0, "err": de,
                         "z_recovered_minus_baseline": (d - d0) / de if de else None,
                         "p_change": ct["p"] if ct else None, "chi2r": f1["chi2r"]})
        out["bands"][bname] = {"quantity": key, "baseline_last_minus_first": d0, "trials": rows}
    (OUT / f"injection_{name}.json").write_text(json.dumps(out, indent=1))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summ = []
    for name in sys.argv[1:]:
        res = run(name)
        for bname, b in res["bands"].items():
            for t in b["trials"]:
                summ.append({"name": name, "band": bname, "quantity": b["quantity"], **t})
                print(f"{name:22s} {bname} {t['kind']:7s} {t['value']:+5.2f} injected {t['injected_change']:+.4f} "
                      f"recovered {t['recovered_change_minus_baseline']:+.4f} ± {t['err']:.4f} "
                      f"p={t['p_change'] if t['p_change'] is None else round(t['p_change'], 4)}")
    path = OUT / "injection_summary.csv"
    old = list(csv.DictReader(open(path))) if path.exists() else []
    names = set(sys.argv[1:])
    rows = [r for r in old if r["name"] not in names] + summ
    with open(path, "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(summ[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
