"""Light curves, eclipse tests and blind variability statistics from research/field_psf.py photometry.

    PYTHONPATH=. .venv/bin/python research/field_analysis.py NAME [--tic TIC]

Steps (all per star):
1. Normal brightness: a smooth curve S(λ) per detector (eclipse_depth.fit_steady, as in Eclipse Mode) through the
   exposures (out of eclipse only, with --tic); each flux is divided by S at its wavelength.
2. Ensemble correction: per exposure, the median normalised flux of the reference stars (measured in >= 80% of
   exposures, robust scatter below the field's 50th percentile, not the star being tested) is divided out. This
   removes exposure-wide calibration errors, as in differential photometry.
3. Errors: formal fit errors, plus a per-star jitter only for the eclipse test (so that out-of-eclipse points
   scatter as their errors say). The variability test uses formal errors and compares stars with each other.
4. Variability: reduced chi² about 1, robust scatter (1.4826 MAD) vs median error, von Neumann ratio η (low = smooth
   in time, Sokolovsky et al. 2017), and a Lomb-Scargle period search with its false-alarm probability.
   A star is flagged only if its excess scatter is an outlier among stars of similar brightness (> 5 robust σ of
   log χ² at that magnitude), its η is low, and the LS false-alarm probability after a Bonferroni correction for
   the number of stars is < 1e-3.
5. With --tic: TESS phase per exposure (UTC -> TDB at the barycentre), depth in the middle half of each eclipse,
   and the blind phase scan of research/plot_phase.py for every star.
Writes research/experimental_results/NAME/analysis.json, lightcurves.npz.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from astropy.timeseries import LombScargle

from backend.app import eclipse_depth as M
from backend.app import eclipses as E
from field_psf import ephemeris

RESULTS = Path(__file__).parent / "experimental_results"
CENTRAL = 0.5
SCAN_HALF_WIDTH = 0.012
FLAG_SIGMA = 5.0
FAP_LIMIT = 1e-3
REF_SCAN_SNR = 6.0


def normalise(f, e, det, wl, use):
    g, ge = np.full(f.shape, np.nan), np.full(f.shape, np.nan)
    for d in np.unique(det):
        m = (det == d) & np.isfinite(f) & np.isfinite(wl) & (e > 0)
        fit = m & use & (f > 3 * e)
        if fit.sum() < 8:
            continue
        st = M.fit_steady(wl[fit], f[fit], e[fit], M.RESOLVING_POWER[int(d)])
        if st is None:
            continue
        s = st(wl[m])
        g[m], ge[m] = f[m] / s, e[m] / s
    return g, ge


def robust_std(x):
    x = x[np.isfinite(x)]
    return float(1.4826 * np.median(np.abs(x - np.median(x)))) if len(x) > 3 else np.nan


def ensemble(G, use_star):
    """Per-exposure median of the reference stars' normalised fluxes (1 where undefined)."""
    ref = G[:, use_star]
    med = np.nanmedian(ref, axis=1) if ref.shape[1] else np.ones(G.shape[0])
    n = np.isfinite(ref).sum(axis=1) if ref.shape[1] else np.zeros(G.shape[0])
    return np.where((n >= 3) & np.isfinite(med), med, 1.0)


def scan(phi, f, e):
    ok = np.isfinite(f) & np.isfinite(e) & (e > 0)
    best = None
    for c in np.arange(0, 1, 0.005):
        m = ok & (np.abs((phi - c + 0.5) % 1 - 0.5) < SCAN_HALF_WIDTH)
        if m.sum() < 5:
            continue
        idx = np.flatnonzero(m)
        m[idx[np.argmax((1 - f[idx]) / e[idx])]] = False
        w = 1 / e[m] ** 2
        dep, err = 1 - np.sum(w * f[m]) / w.sum(), 1 / np.sqrt(w.sum())
        if best is None or dep / err > best[0]:
            best = (dep / err, c, dep, err, int(m.sum()))
    return None if best is None else {"snr": round(best[0], 2), "phase": round(best[1], 3), "depth": round(best[2], 4),
                                      "err": round(best[3], 4), "n": best[4]}


def von_neumann(t, x):
    o = np.argsort(t)
    x = x[o][np.isfinite(x[o])]
    if len(x) < 10:
        return np.nan
    return float(np.sum(np.diff(x) ** 2) / (len(x) - 1) / np.var(x))


def analyse(name, tic=None):
    folder = RESULTS / name
    z = np.load(folder / "photometry.npz")
    stars = json.loads((folder / "stars.json").read_text())
    meta = json.loads((folder / "meta.json").read_text())
    mjd, det, wl, F, Er = z["mjd"], z["det"], z["wl"], z["flux"], z["err"]
    n_exp, n_star = F.shape
    eph = ephemeris(tic, meta.get("eph_json")) if tic else None
    if eph:
        btjd = E.to_btjd(mjd, meta["ra"], meta["dec"])
        phi = E.phase(btjd, eph)
        clear = E.out_of_eclipse(phi, eph)
        part = E.eclipse_part(phi, eph, CENTRAL)
    else:
        btjd, phi, clear, part = None, None, np.ones(n_exp, bool), None
    G, GE = np.full(F.shape, np.nan), np.full(F.shape, np.nan)
    for j in range(n_star):
        G[:, j], GE[:, j] = normalise(F[:, j], Er[:, j], det, wl, clear)
    coverage = np.isfinite(G).mean(axis=0)
    scat = np.array([robust_std(G[clear, j]) for j in range(n_star)])
    scat_all = np.array([robust_std(G[:, j]) for j in range(n_star)])
    good_ref = (coverage >= 0.8) & np.isfinite(scat_all)
    good_ref &= scat_all <= np.nanpercentile(scat_all[good_ref], 50) if good_ref.any() else good_ref

    def corrected(ref):
        out_ = np.full(F.shape, np.nan)
        for j in range(n_star):
            use = ref.copy()
            use[j] = False
            out_[:, j] = G[:, j] / ensemble(G, use)
        return out_

    Gc = corrected(good_ref)
    dropped = []
    if eph:
        # A reference star must be constant at every phase of the binary being tested, not only outside its eclipses.
        for j in np.where(good_ref)[0]:
            mj = np.isfinite(Gc[:, j]) & np.isfinite(GE[:, j]) & (GE[:, j] > 0) & clear
            jit = M.jitter(Gc[mj, j], GE[mj, j]) if mj.sum() > 5 else 0.0
            s = scan(phi % 1, Gc[:, j], np.sqrt(GE[:, j] ** 2 + jit ** 2))
            if s and s["snr"] > REF_SCAN_SNR:
                dropped.append(stars[j]["source_id"])
                good_ref[j] = False
        if dropped:
            Gc = corrected(good_ref)
    out = {"name": name, "tic": tic, "n_exposures": n_exp, "n_stars": n_star,
           "references_dropped_for_phase_signal": dropped, "stars": []}
    # variability statistics
    chi = np.full(n_star, np.nan)
    for j in range(n_star):
        m = np.isfinite(Gc[:, j]) & clear & (GE[:, j] > 0)
        if m.sum() >= 15:
            chi[j] = float(np.sum(((Gc[m, j] - np.median(Gc[m, j])) / GE[m, j]) ** 2) / (m.sum() - 1))
    gmag = np.array([s["g_mag"] for s in stars])
    lchi = np.log10(chi)
    resid_sig = np.full(n_star, np.nan)
    for j in range(n_star):
        near = np.isfinite(lchi) & (np.abs(gmag - gmag[j]) < 1.5)
        near[j] = False
        if near.sum() >= 4 and np.isfinite(lchi[j]):
            mu, sd = np.median(lchi[near]), robust_std(lchi[near])
            resid_sig[j] = (lchi[j] - mu) / max(sd, 0.03)
    for j, s in enumerate(stars):
        m = np.isfinite(Gc[:, j]) & (GE[:, j] > 0)
        rec = {"source_id": s["source_id"], "g_mag": s["g_mag"], "x": round(s["x"], 2), "y": round(s["y"], 2),
               "merged": s["merged"], "n": int(m.sum()), "coverage": round(float(coverage[j]), 3),
               "scatter_pct": None if not np.isfinite(scat[j]) else round(100 * scat[j], 2),
               "median_err_pct": None if not m.any() else round(100 * float(np.median(GE[m, j])), 2),
               "chi2_red": None if not np.isfinite(chi[j]) else round(chi[j], 2),
               "chi2_excess_sigma": None if not np.isfinite(resid_sig[j]) else round(float(resid_sig[j]), 2),
               "is_reference": bool(good_ref[j])}
        if m.sum() >= 15:
            rec["von_neumann_eta"] = round(von_neumann(mjd[m], Gc[m, j]), 3)
            ls = LombScargle(mjd[m], Gc[m, j], GE[m, j])
            freq, power = ls.autopower(minimum_frequency=1 / 300, maximum_frequency=1 / 0.1, samples_per_peak=10)
            k = int(np.argmax(power))
            fap = float(ls.false_alarm_probability(power[k], minimum_frequency=1 / 300, maximum_frequency=1 / 0.1))
            rec["ls_period_d"] = round(float(1 / freq[k]), 5)
            rec["ls_power"] = round(float(power[k]), 4)
            rec["ls_fap"] = fap
            rec["ls_fap_bonferroni"] = min(1.0, fap * n_star)
            rec["amplitude_pct"] = round(100 * float(np.nanpercentile(Gc[m, j], 95) - np.nanpercentile(Gc[m, j], 5)) / 2, 2)
            rec["variable_flag"] = bool(np.isfinite(resid_sig[j]) and resid_sig[j] > FLAG_SIGMA
                                        and rec["von_neumann_eta"] < 1.5 and rec["ls_fap_bonferroni"] < FAP_LIMIT)
        if eph:
            mj = np.isfinite(Gc[:, j]) & np.isfinite(GE[:, j]) & (GE[:, j] > 0)
            jit = M.jitter(Gc[mj & clear, j], GE[mj & clear, j]) if (mj & clear).sum() > 5 else 0.0
            ge = np.sqrt(GE[:, j] ** 2 + jit ** 2)
            rec["jitter_pct"] = round(100 * jit, 2)
            for nm, k in (("primary", 1), ("secondary", 2)):
                r = M.weighted_depth(Gc[mj & (part == k), j], ge[mj & (part == k)])
                rec[nm] = None if r is None else {"depth": round(r["depth"], 4), "err": round(r["err"], 4),
                                                  "n": int((mj & (part == k)).sum())}
            rec["phase_scan"] = scan(phi % 1, Gc[:, j], ge)
        out["stars"].append(rec)
    if eph:
        out["clock"] = {"tess_id": eph.tess_id, "period": eph.period, "bjd0": eph.bjd0,
                        "phase_error_2026": round(eph.phase_error(float(np.median(btjd))), 5),
                        "sec_phase": E.secondary_phase(eph), "prim_width": eph.prim_width}
    (folder / "analysis.json").write_text(json.dumps(out, indent=1, default=float))
    np.savez(folder / "lightcurves.npz", mjd=mjd, det=det, wl=wl, g=G, ge=GE, gc=Gc,
             btjd=btjd if btjd is not None else np.zeros(0), phi=phi if phi is not None else np.zeros(0))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--tic")
    a = p.parse_args()
    out = analyse(a.name, a.tic)
    for s in out["stars"]:
        line = (f"{s['source_id']:>20} G {s['g_mag']:5.2f} n {s['n']:4d} scat {s['scatter_pct']}% err "
                f"{s['median_err_pct']}% chi2 {s['chi2_red']} ({s['chi2_excess_sigma']}σ) eta {s.get('von_neumann_eta')} "
                f"LS {s.get('ls_period_d')} d FAPb {s.get('ls_fap_bonferroni', float('nan')):.1e} flag {s.get('variable_flag')}")
        if a.tic:
            line += f" | prim {s.get('primary')} sec {s.get('secondary')} scan {s.get('phase_scan')}"
        print(line)


if __name__ == "__main__":
    main()
