"""Per-epoch ice optical depths (H2O 3 um, CO2 4.27 um) from the per-exposure photometry of phot.py, and the
test of whether they changed between epochs.

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/ice_fit.py NAME [NAME ...]

Epochs. Exposures are grouped into visits (gaps > VISIT_GAP days; SPHEREx revisits a position about every six
months) and each visit into passes (gaps > PASS_GAP days). A pass that alone meets a band's coverage rule is its own
epoch for that band; otherwise the visit is one epoch. Exposures are never merged across visits.

Joint model of all epochs of one source (weighted least squares in ln F). The band SHAPE is shared by all epochs and
fitted; only the depth and the continuum are free per epoch, so a template that is wrong in shape is wrong in the
same way at every epoch and the comparison of depths between epochs is what is tested.

  H2O (2.42-4.15 um):   ln F_i = a_e + alpha_e ln(lam_i/3 um) + beta_e (t_i - t_e) + ln < exp(-tau_e phi_H2O) >_i
     phi_H2O = G(nu; nu_c, w_c) + r * G(nu; 2950 cm-1, 350 cm-1)    (core + red wing; nu_c, w_c, r shared)
     beta_e: achromatic brightness drift within the epoch (the band centre and the continuum are observed on
     different days, so a drift would otherwise bias tau_e).
  CO2 (4.05-4.42 um):   ln F_i = a_g + alpha_e ln(lam_i/4.27 um) + ln < exp(-tau_e phi_CO2) >_i
     phi_CO2 = G(nu; nu_c, w) (nu_c, w shared); a_g is free for every same-day group of exposures (within
     GROUP_DT), so brightness changes between groups cannot mimic a depth change. Only groups with >= 2 channels
     in the fit range carry information.
G is a Gaussian in wavenumber with peak 1; < >_i averages over channel i's bandpass (Gaussian, FWHM = CBAND).
Templates are analytic, not laboratory profiles: absolute column densities are not derived.

The CO2 band is saturated at SPHEREx resolution for deep-ice sources, so besides tau_e the equivalent width
EW_e = integral (1 - exp(-tau_e phi)) d lam (um) is reported; EW is the better-constrained quantity.

Errors: per exposure sigma_lnF = sqrt((err/F)^2 + FLOOR^2); the covariance is scaled by chi2_red when > 1.
No-change test: H0 = one depth for all epochs, H1 = depth per epoch;
F = ((chi2_H0 - chi2_H1)/(E-1)) / (chi2_H1/dof_H1), p from the F distribution.

Output: EXPERIMENTAL_RESULTS/ice/NAME.json and NAME.png.
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
PHOT = ROOT / "EXPERIMENTAL_RESULTS" / "photometry"
OUT = ROOT / "EXPERIMENTAL_RESULTS" / "ice"
VISIT_GAP = 60.0
PASS_GAP = 20.0
GROUP_DT = 0.5
MIN_CORE_GOOD = 6
FLOOR = 0.02

BANDS = {
    "H2O": {"fit": (2.42, 4.15), "lam0": 3.0, "core": (2.95, 3.20), "blue": (2.42, 2.72), "red": (3.75, 4.15),
            "min": (2, 2, 2), "shape0": [3260.0, 360.0, 0.2], "lo": [3150.0, 200.0, 0.0], "hi": [3350.0, 550.0, 0.8]},
    "CO2": {"fit": (4.05, 4.42), "lam0": 4.27, "core": (4.235, 4.295), "blue": (4.05, 4.215), "red": (4.31, 4.42),
            "min": (1, 1, 1), "shape0": [2342.0, 20.0], "lo": [2330.0, 8.0], "hi": [2355.0, 45.0]},
}
WING = (2950.0, 350.0)

_GRID = np.linspace(-3, 3, 31)
_W = np.exp(-0.5 * _GRID ** 2)
_W /= _W.sum()


def gauss_nu(lam, nu_c, fwhm):
    return np.exp(-0.5 * ((1e4 / lam - nu_c) / (fwhm / 2.3548)) ** 2)


def profile(lam, bname, shape):
    if bname == "H2O":
        return gauss_nu(lam, shape[0], shape[1]) + shape[2] * gauss_nu(lam, *WING)
    return gauss_nu(lam, shape[0], shape[1])


def band_avg(lam, bw, tau, bname, shape):
    """< exp(-tau * phi) > over a Gaussian bandpass of FWHM bw centred on lam; tau may be per point."""
    l = lam[:, None] + _GRID[None, :] * (bw[:, None] / 2.3548)
    return (np.exp(-np.asarray(tau)[..., None] * profile(l, bname, shape)) * _W).sum(1)


def equivalent_width(tau, bname, shape):
    lam = np.linspace(4.15, 4.40, 2001) if bname == "CO2" else np.linspace(2.5, 4.0, 2001)
    return float(np.trapezoid(1 - np.exp(-tau * profile(lam, bname, shape)), lam))


def load(name):
    rows = list(csv.DictReader(open(PHOT / f"{name}.csv")))
    keep, cut = [], {}
    for r in rows:
        why = None
        if r["status"] != "ok":
            why = r["status"]
        elif int(r["n_core_good"]) < MIN_CORE_GOOD:
            why = "flagged core"
        else:
            f, e = float(r["flux_jy"]), float(r["err_jy"])
            if not (np.isfinite(f) and np.isfinite(e) and e > 0) or f <= 0:
                why = "non-positive flux"
            elif f / e < 3:
                why = "S/N < 3"
        if why:
            cut[why] = cut.get(why, 0) + 1
            continue
        keep.append({"mjd": float(r["mjd"]), "det": int(r["det"]), "wl": float(r["wl_um"]), "bw": float(r["bw_um"]),
                     "f": float(r["flux_jy"]), "e": float(r["err_jy"]),
                     "ap": float(r["ap_flux_jy"]) if r["ap_flux_jy"] not in ("", "nan") else float("nan"),
                     "ap_e": float(r["ap_err_jy"]) if r["ap_err_jy"] not in ("", "nan") else float("nan"),
                     "collection": r["collection"], "chi2r": float(r["chi2r"])})
    keep.sort(key=lambda r: r["mjd"])
    return keep, cut, len(rows)


def clusters(t, gap):
    t = np.asarray(t)
    o = np.argsort(t)
    out, cur = [], [int(o[0])]
    for a, b in zip(o[:-1], o[1:]):
        if t[b] - t[a] > gap:
            out.append(cur)
            cur = []
        cur.append(int(b))
    out.append(cur)
    return out


def coverage(pts, band):
    lam = np.array([p["wl"] for p in pts])
    n = [int(((lam >= lo) & (lam <= hi)).sum()) for lo, hi in (band["core"], band["blue"], band["red"])]
    return n, all(a >= b for a, b in zip(n, band["min"]))


def epochs_for(pts, band):
    visits = clusters([p["mjd"] for p in pts], VISIT_GAP)
    out = []
    for vi, v in enumerate(visits):
        vp = [pts[i] for i in v]
        passes = [[vp[i] for i in ps] for ps in clusters([p["mjd"] for p in vp], PASS_GAP)]
        if len(passes) > 1 and all(coverage(ps, band)[1] for ps in passes):
            units = [(f"{vi}.{k}", ps) for k, ps in enumerate(passes)]
        else:
            units = [(f"{vi}", vp)]
        for label, up in units:
            n, ok = coverage(up, band)
            out.append({"epoch": label, "visit": vi, "mjd": [min(p["mjd"] for p in up), max(p["mjd"] for p in up)],
                        "collections": sorted({p["collection"] for p in up}), "coverage_core_blue_red": n,
                        "complete": ok, "pts": up})
    return out


def joint_fit(epochs, bname, flux_key="f", err_key="e", common_tau=False, drift=True, fit_range=None,
              curvature=False):
    band = BANDS[bname]
    lo, hi = fit_range or band["fit"]
    E = len(epochs)
    lam, bw, y, s, ep, t, grp = [], [], [], [], [], [], []
    ngrp = 0
    for k, e in enumerate(epochs):
        p = [q for q in e["pts"] if lo <= q["wl"] <= hi and np.isfinite(q[flux_key]) and q[flux_key] > 0
             and np.isfinite(q[err_key]) and q[err_key] > 0]
        if bname == "CO2":
            gl = clusters([q["mjd"] for q in p], GROUP_DT) if p else []
            gid = np.empty(len(p), int)
            for g in gl:
                if len(g) >= 2:
                    gid[g] = ngrp
                    ngrp += 1
                else:
                    gid[g] = -1
            keep = gid >= 0
            p = [q for q, kk in zip(p, keep) if kk]
            grp += list(gid[keep])
        tm = np.mean([q["mjd"] for q in p]) if p else 0.0
        for q in p:
            lam.append(q["wl"]); bw.append(q["bw"]); y.append(math.log(q[flux_key]))
            s.append(math.hypot(q[err_key] / q[flux_key], FLOOR)); ep.append(k); t.append(q["mjd"] - tm)
    lam, bw, y, s, ep, t = map(np.asarray, (lam, bw, y, s, ep, t))
    grp = np.asarray(grp, int)
    if len(y) < 8:
        return None
    x = np.log(lam / band["lam0"])
    ns = len(band["shape0"])
    ntau = 1 if common_tau else E
    # parameter vector: shape | tau (ntau) | alpha (E) | then H2O: a (E), beta (E) ; CO2: a_g (ngrp)
    p0 = list(band["shape0"]) + [1.5] * ntau + [2.0] * E
    lb = list(band["lo"]) + [0.0] * ntau + [-15.0] * E
    ub = list(band["hi"]) + [15.0] * ntau + [15.0] * E
    if bname == "H2O":
        p0 += [float(np.median(y[ep == k])) if (ep == k).any() else 0.0 for k in range(E)] + [0.0] * E
        lb += [-np.inf] * E + ([-0.1] * E if drift else [-1e-9] * E)
        ub += [np.inf] * E + ([0.1] * E if drift else [1e-9] * E)
        if curvature:
            p0 += [0.0] * E
            lb += [-30.0] * E
            ub += [30.0] * E
    else:
        p0 += [float(y[grp == g].max()) for g in range(ngrp)]
        lb += [-np.inf] * ngrp
        ub += [np.inf] * ngrp

    def unpack(par):
        shape = par[:ns]
        tau = par[ns:ns + ntau]
        alpha = par[ns + ntau:ns + ntau + E]
        rest = par[ns + ntau + E:]
        return shape, tau, alpha, rest

    def model(par):
        shape, tau, alpha, rest = unpack(par)
        tau_i = tau[0] if common_tau else tau[ep]
        m = alpha[ep] * x + np.log(band_avg(lam, bw, tau_i * np.ones_like(lam), bname, shape))
        if bname == "H2O":
            m = m + rest[:E][ep] + rest[E:2 * E][ep] * t
            if curvature:
                m = m + rest[2 * E:3 * E][ep] * x ** 2
        else:
            m = m + rest[grp]
        return m

    r = least_squares(lambda par: (y - model(par)) / s, p0, bounds=(lb, ub), x_scale="jac")
    J = r.jac
    free = np.array([not (bname == "H2O" and not drift and ns + ntau + 2 * E <= i < ns + ntau + 3 * E)
                     for i in range(len(r.x))])
    Jf = J[:, free]
    dof = max(len(y) - int(free.sum()), 1)
    chi2 = float(np.sum(r.fun ** 2))
    chi2r = chi2 / dof
    try:
        covf = np.linalg.pinv(Jf.T @ Jf) * max(chi2r, 1.0)
    except np.linalg.LinAlgError:
        return None
    cov = np.zeros((len(r.x), len(r.x)))
    cov[np.ix_(free, free)] = covf
    np.fill_diagonal(cov, np.maximum(np.diag(cov), 0.0))
    shape, tau, alpha, rest = unpack(r.x)
    out = {"n": int(len(y)), "chi2": chi2, "dof": dof, "chi2r": chi2r, "shape": [float(v) for v in shape],
           "shape_err": [float(math.sqrt(cov[i, i])) for i in range(ns)], "epochs": []}
    for k in range(E):
        ti = 0 if common_tau else k
        sel = ep == k
        row = {"epoch": epochs[k]["epoch"], "n": int(sel.sum()), "tau": float(tau[ti]),
               "tau_err": float(math.sqrt(cov[ns + ti, ns + ti])), "alpha": float(alpha[k])}
        if bname == "H2O":
            row["cont_jy"] = float(math.exp(rest[k]))
            row["beta_per_day"] = float(rest[E + k])
            if curvature:
                row["curvature"] = float(rest[2 * E + k])
        else:
            gk = np.unique(grp[sel])
            row["cont_jy"] = float(math.exp(np.median(rest[gk]))) if len(gk) else float("nan")
            row["n_groups"] = int(len(gk))
        h = 1e-3
        ew = equivalent_width(tau[ti], bname, shape)
        dew = (equivalent_width(tau[ti] + h, bname, shape) - equivalent_width(max(tau[ti] - h, 0), bname, shape)) / (2 * h)
        row["ew_um"] = ew
        row["ew_err_um"] = abs(dew) * row["tau_err"]
        row["rms_resid_sigma"] = float(np.sqrt(np.mean(r.fun[sel] ** 2))) if sel.any() else None
        out["epochs"].append(row)
    out["_resid"] = r.fun
    out["_ep"] = ep
    return out


def change_test(h0, h1, E):
    if h0 is None or h1 is None or E < 2:
        return None
    F = ((h0["chi2"] - h1["chi2"]) / (E - 1)) / (h1["chi2"] / h1["dof"])
    p = float(stats.f.sf(max(F, 0), E - 1, h1["dof"]))
    return {"F": float(F), "df": [E - 1, h1["dof"]], "p": p}


def pairs(fit):
    out = []
    ep = fit["epochs"]
    for i in range(len(ep)):
        for j in range(i + 1, len(ep)):
            a, b = ep[i], ep[j]
            d, s = b["tau"] - a["tau"], math.hypot(a["tau_err"], b["tau_err"])
            de, se = b["ew_um"] - a["ew_um"], math.hypot(a["ew_err_um"], b["ew_err_um"])
            out.append({"a": a["epoch"], "b": b["epoch"], "dtau": d, "dtau_err": s, "z_tau": d / s if s else None,
                        "dew_um": de, "dew_err_um": se, "z_ew": de / se if se else None,
                        "dlncont": math.log(b["cont_jy"] / a["cont_jy"]) if a["cont_jy"] > 0 and b["cont_jy"] > 0
                        else None})
    return out


def clean(fit):
    return None if fit is None else {k: v for k, v in fit.items() if not k.startswith("_")}


def analyse(name):
    pts, cut, n_all = load(name)
    res = {"name": name, "n_exposures": n_all, "n_used": len(pts), "cuts": cut, "floor": FLOOR, "bands": {}}
    if not pts:
        return res
    for bname, band in BANDS.items():
        eps = epochs_for(pts, band)
        good = [e for e in eps if e["complete"]]
        b = {"epochs": [{k: v for k, v in e.items() if k != "pts"} for e in eps], "n_complete": len(good)}
        if len(good) >= 1:
            h1 = joint_fit(good, bname)
            b["fit"] = clean(h1)
            b["fit_nodrift"] = clean(joint_fit(good, bname, drift=False)) if bname == "H2O" else None
            b["fit_aperture"] = clean(joint_fit(good, bname, flux_key="ap", err_key="ap_e"))
            if len(good) >= 2 and h1:
                h0 = joint_fit(good, bname, common_tau=True)
                b["fit_common_tau"] = clean(h0)
                b["change_test"] = change_test(h0, h1, len(good))
                b["pairs"] = pairs(h1)
                if b["fit_aperture"]:
                    b["pairs_aperture"] = pairs(b["fit_aperture"])
                if b.get("fit_nodrift"):
                    b["pairs_nodrift"] = pairs(b["fit_nodrift"])
                if bname == "H2O":
                    b["variants"] = {}
                    for vname, kw in (("with_D3_2.10", {"fit_range": (2.10, 4.15)}),
                                      ("no_blue_window_2.80", {"fit_range": (2.80, 4.15)}),
                                      ("curved_continuum", {"curvature": True}),
                                      ("narrow_red_3.90", {"fit_range": (2.42, 3.90)})):
                        f = joint_fit(good, bname, **kw)
                        b["variants"][vname] = {"fit": clean(f), "pairs": pairs(f) if f else None}
        res["bands"][bname] = b
    return res, pts


def plot(name, res, pts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for k, bname in enumerate(("H2O", "CO2")):
        b = res["bands"][bname]
        eps = epochs_for(pts, BANDS[bname])
        good = [e for e in eps if e["complete"]]
        cols = plt.cm.viridis(np.linspace(0, 0.9, max(len(good), 1)))
        lo, hi = (2.3, 4.2) if bname == "H2O" else (4.0, 4.5)
        fit = b.get("fit")
        for c, e in zip(cols, good):
            q = [p for p in e["pts"] if lo <= p["wl"] <= hi]
            ax[k].errorbar([p["wl"] for p in q], [p["f"] * 1e3 for p in q], [p["e"] * 1e3 for p in q], fmt="o", ms=3,
                           color=c, label=f"epoch {e['epoch']} MJD {e['mjd'][0]:.0f}-{e['mjd'][1]:.0f}")
            if fit:
                fe = next(x for x in fit["epochs"] if x["epoch"] == e["epoch"])
                band = BANDS[bname]
                lam = np.linspace(band["fit"][0], band["fit"][1], 400)
                bwv = np.full_like(lam, 0.088 if bname == "H2O" else 0.037)
                m = fe["cont_jy"] * (lam / band["lam0"]) ** fe["alpha"] * band_avg(lam, bwv, fe["tau"] * np.ones_like(lam),
                                                                                  bname, fit["shape"])
                ax[k].plot(lam, m * 1e3, color=c, lw=1, label=f"  tau {fe['tau']:.2f}±{fe['tau_err']:.2f}, "
                                                                f"EW {fe['ew_um'] * 1e3:.1f}±{fe['ew_err_um'] * 1e3:.1f} nm")
        ct = b.get("change_test")
        ax[k].set_title(f"{name} {bname}" + (f": no-change test p = {ct['p']:.2g}" if ct else ""), fontsize=10)
        ax[k].set_yscale("log"); ax[k].set_xlabel("wavelength (µm)"); ax[k].set_ylabel("flux density (mJy)")
        ax[k].legend(fontsize=6.5)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=90)
    plt.close(fig)


def summary_line(res):
    out = []
    for bn, b in res["bands"].items():
        f = b.get("fit")
        if not f:
            out.append(f"  {bn}: {b['n_complete']} complete epochs, no fit")
            continue
        out.append(f"  {bn}: {b['n_complete']} epochs, shape {[round(v, 1) for v in f['shape']]}, chi2r {f['chi2r']:.2f}"
                   + (f", change p={b['change_test']['p']:.3g}" if b.get("change_test") else ""))
        for e in f["epochs"]:
            out.append(f"     {e['epoch']}: tau {e['tau']:.3f}±{e['tau_err']:.3f} EW {e['ew_um'] * 1e3:.2f}±"
                       f"{e['ew_err_um'] * 1e3:.2f} nm cont {e['cont_jy'] * 1e3:.1f} mJy n={e['n']}")
        for p in b.get("pairs", []):
            out.append(f"     {p['a']}->{p['b']}: dtau {p['dtau']:+.3f}±{p['dtau_err']:.3f} (z {p['z_tau']:+.1f}), "
                       f"dEW {p['dew_um'] * 1e3:+.2f}±{p['dew_err_um'] * 1e3:.2f} nm, dln cont {p['dlncont']:+.2f}")
        alt = [("aperture", b.get("pairs_aperture")), ("nodrift", b.get("pairs_nodrift"))]
        alt += [(k, v["pairs"]) for k, v in (b.get("variants") or {}).items()]
        for k, prs in alt:
            if prs:
                out.append(f"       [{k}] " + "  ".join(f"{p['a']}->{p['b']} {p['dtau']:+.3f}±{p['dtau_err']:.3f}"
                                                         for p in prs))
    return "\n".join(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[1:]:
        res, pts = analyse(name)
        (OUT / f"{name}.json").write_text(json.dumps(res, indent=1))
        plot(name, res, pts)
        print(name, "used", res["n_used"], "of", res["n_exposures"], res["cuts"])
        print(summary_line(res))


if __name__ == "__main__":
    main()
