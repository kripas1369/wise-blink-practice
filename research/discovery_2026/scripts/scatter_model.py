"""Physically distinct explanations of an apparent H2O depth change (mission section 7.6).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/scatter_model.py NAME [NAME ...]

Both models use the band shape of the baseline joint fit (fixed) and the same per-epoch continuum (a_e, alpha_e,
drift beta_e) over 2.42-4.15 um:
  A  "ice change"        F = C_e (lam/3)^alpha_e e^(beta_e t) < exp(-tau_e phi) >                 (tau per epoch)
  B  "unabsorbed light"  F = C_e (lam/3)^alpha_e e^(beta_e t) < exp(-tau phi) > + S_e (lam/3)^-q   (one tau, S_e >= 0)
B represents light that reaches us without crossing the icy column (scattered light from cavity walls, a variable
inner-disk component seen along a less extincted path). q = 4 (blue scattered light), q = 2, and q = 0 (grey) are
tried. B has one more free parameter than A.
  C  "partial covering"  F = C_e (lam/3)^alpha_e e^(beta_e t) [ c_e < exp(-tau phi) > + 1 - c_e ]  (one tau, 0 < c_e < 1)
C is B with the unabsorbed light having the continuum's own spectrum: a fixed ice column in front of a varying
fraction of the 3 um emitting region (rows with q = "covering"). Output: VALIDATION/scatter_model.csv
"""
import csv
import math
import sys

import numpy as np
from scipy.optimize import least_squares

import ice_fit as I

OUT = I.ROOT / "VALIDATION"


def data(name):
    pts, _, _ = I.load(name)
    band = I.BANDS["H2O"]
    good = [e for e in I.epochs_for(pts, band) if e["complete"]]
    lo, hi = band["fit"]
    lam, bw, y, s, ep, t = [], [], [], [], [], []
    for k, e in enumerate(good):
        p = [q for q in e["pts"] if lo <= q["wl"] <= hi]
        tm = np.mean([q["mjd"] for q in p])
        for q in p:
            lam.append(q["wl"]); bw.append(q["bw"]); y.append(math.log(q["f"]))
            s.append(math.hypot(q["e"] / q["f"], I.FLOOR)); ep.append(k); t.append(q["mjd"] - tm)
    return good, *map(np.asarray, (lam, bw, y, s, ep, t))


def fit(model, lam, bw, y, s, ep, t, E, shape, q):
    x = np.log(lam / 3.0)

    def unpack(par):
        a, al, be = par[:E], par[E:2 * E], par[2 * E:3 * E]
        rest = par[3 * E:]
        return a, al, be, rest

    def pred(par):
        a, al, be, rest = unpack(par)
        if model == "A":
            tau = rest[:E][ep]
            return a[ep] + al[ep] * x + be[ep] * t + np.log(I.band_avg(lam, bw, tau, "H2O", shape))
        tau = rest[0] * np.ones_like(lam)
        cont = np.exp(a[ep] + al[ep] * x + be[ep] * t)
        if model == "C":
            cov = (1.0 / (1.0 + np.exp(-rest[1:1 + E])))[ep]
            return np.log(cont * (cov * I.band_avg(lam, bw, tau, "H2O", shape) + 1.0 - cov))
        S = np.exp(rest[1:1 + E])[ep]
        return np.log(cont * I.band_avg(lam, bw, tau, "H2O", shape) + S * (lam / 3.0) ** (-q))

    a0 = [float(np.median(y[ep == k])) for k in range(E)]
    p0 = a0 + [2.0] * E + [0.0] * E
    lb = [-np.inf] * E + [-15.0] * E + [-0.1] * E
    ub = [np.inf] * E + [15.0] * E + [0.1] * E
    if model == "A":
        p0 += [1.0] * E
        lb += [0.0] * E
        ub += [15.0] * E
    elif model == "C":
        p0 += [1.0] + [3.0] * E
        lb += [0.0] + [-10.0] * E
        ub += [15.0] + [20.0] * E
    else:
        p0 += [1.0] + [min(a0) - 3.0] * E
        lb += [0.0] + [-30.0] * E
        ub += [15.0] + [5.0] * E
    best = None
    starts = {"A": [None], "B": [0.0, -2.0, -5.0], "C": [5.0, 1.0, -1.0]}[model]
    for start in starts:
        pp = list(p0)
        if model == "B":
            pp[3 * E + 1:] = [min(a0) + start] * E
        elif model == "C":
            pp[3 * E:] = [1.5] + [start] * E
        r = least_squares(lambda par: (y - pred(par)) / s, pp, bounds=(lb, ub), x_scale="jac")
        if best is None or r.cost < best.cost:
            best = r
    chi2 = float(np.sum(best.fun ** 2))
    _, _, _, rest = unpack(best.x)
    out = {"chi2": chi2, "n": int(len(y)), "k": int(len(best.x))}
    if model == "A":
        out["tau"] = [round(float(v), 3) for v in rest[:E]]
    elif model == "C":
        out["tau"] = round(float(rest[0]), 3)
        out["unabsorbed_frac_at_3um"] = [round(float(1.0 / (1.0 + np.exp(v))), 3) for v in rest[1:1 + E]]
    else:
        out["tau"] = round(float(rest[0]), 3)
        S = np.exp(rest[1:1 + E])
        cont3 = [float(np.exp(np.median(best.x[k]))) for k in range(E)]
        out["unabsorbed_frac_at_3um"] = [round(float(S[k] / (S[k] + cont3[k])), 3) for k in range(E)]
    return out


def main():
    rows = []
    for name in sys.argv[1:]:
        res = I.joint_fit([e for e in I.epochs_for(I.load(name)[0], I.BANDS["H2O"]) if e["complete"]], "H2O")
        shape = res["shape"]
        good, lam, bw, y, s, ep, t = data(name)
        E = len(good)
        A = fit("A", lam, bw, y, s, ep, t, E, shape, 0)
        for q in (4.0, 2.0, 0.0, "covering"):
            B = fit("C", lam, bw, y, s, ep, t, E, shape, 0) if q == "covering" else fit("B", lam, bw, y, s, ep, t, E, shape, q)
            n = A["n"]
            bic_a = A["chi2"] + A["k"] * math.log(n)
            bic_b = B["chi2"] + B["k"] * math.log(n)
            rows.append({"name": name, "q": q, "n": n, "chi2_A_ice_change": round(A["chi2"], 2),
                         "chi2_B_unabsorbed": round(B["chi2"], 2), "dBIC_B_minus_A": round(bic_b - bic_a, 2),
                         "tau_A": A["tau"], "tau_B": B["tau"], "unabsorbed_frac_B": B["unabsorbed_frac_at_3um"]})
            print(rows[-1], flush=True)
    path = OUT / "scatter_model.csv"
    with open(path, "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
