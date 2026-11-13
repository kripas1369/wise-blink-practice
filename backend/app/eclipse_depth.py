"""Eclipse mode, part 2: how deep an eclipse is at each wavelength, from exposures at scattered wavelengths.

SPHEREx's filter gives every exposure its own wavelength, so no two exposures see the binary at quite the
same colour. The recipe (docs: frontend/about.html, "Eclipse mode"):

1. Normal brightness S(λ): a smooth curve (cubic B-spline in ln λ, knots every KNOT_SPACING resolution
   elements) fitted, per detector, to the exposures taken outside both eclipses.
2. g = flux / S(λ): 1 = normal brightness, whatever the wavelength.
3. Close binaries also brighten and fade between eclipses (tidally stretched stars, reflected light). A
   cosine baseline B(φ) = c0 + a1 cos 2πφ + a2 cos 4πφ is fitted to g outside the eclipses and used only
   if some term is significant (> BASELINE_SIGNIFICANCE σ).
4. Depth in a wavelength bin = 1 - weighted mean of g / B(φ) over the exposures in the middle half of
   the eclipse (at least MIN_POINTS_PER_BIN), error from the weights, enlarged if the points scatter more.
5. Errors: VARIANCE-based errors are inflated by a "jitter" fraction s, chosen so that the out-of-eclipse
   exposures scatter as their errors say (robust: 1.4826 x MAD).

Checks built in: the same depth at quarter phase (should be 0), and the same depth for field stars
measured on the same exposures (should be 0).
"""
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import make_lsq_spline

# Resolving power λ/Δλ of each detector (SPHEREx Explanatory Supplement, section 2).
RESOLVING_POWER = {1: 41, 2: 41, 3: 41, 4: 35, 5: 110, 6: 130}
KNOT_SPACING = 2.0             # knots every 2 resolution elements: S(λ) cannot follow narrower features
MIN_POINTS_PER_KNOT = 6
CLIP_SIGMA = 4.0               # outliers (cosmic rays, missed flags) left out of S(λ), 3 rounds
CENTRAL = 0.5                  # depth uses the middle half of each eclipse (flat-ish bottom, phase errors matter less)
MIN_POINTS_PER_BIN = 3
BINS_PER_DETECTOR = 2
BASELINE_SIGNIFICANCE = 3.0
NULL_PHASE = 0.25              # quarter phase: between the eclipses


@dataclass
class Steady:
    """Normal brightness of one star on one detector, S(λ)."""
    spline: object | None
    poly: np.ndarray | None
    n_used: int
    n_knots: int
    wl_range: tuple[float, float]

    def __call__(self, wl) -> np.ndarray:
        x = np.log(np.asarray(wl, float))
        if self.spline is not None:
            return self.spline(np.clip(x, *np.log(self.wl_range)))
        return np.polyval(self.poly, x)


def fit_steady(wl, flux, err, resolving_power: float) -> Steady | None:
    """Weighted cubic B-spline of flux against ln λ, with outliers clipped; None with fewer than 8 points."""
    wl, flux, err = (np.asarray(a, float) for a in (wl, flux, err))
    keep = np.isfinite(wl) & np.isfinite(flux) & np.isfinite(err) & (err > 0) & (wl > 0)
    if keep.sum() < 8:
        return None
    model = None
    for _ in range(3):
        model = _fit_once(wl[keep], flux[keep], err[keep], resolving_power)
        resid = np.abs(flux - model(wl)) / err
        new = keep & (resid < CLIP_SIGMA * max(1.0, 1.4826 * float(np.median(resid[keep]))))
        if new.sum() < 8 or (new == keep).all():
            break
        keep = new
    return _fit_once(wl[keep], flux[keep], err[keep], resolving_power)


def _fit_once(wl, flux, err, resolving_power) -> Steady:
    x = np.log(wl)
    order = np.argsort(x)
    x, flux, err = x[order], flux[order], err[order]
    lo, hi = float(x[0]), float(x[-1])
    n_interior = int(min((hi - lo) / (KNOT_SPACING / resolving_power), len(x) / MIN_POINTS_PER_KNOT - 4))
    while n_interior >= 0:
        inner = np.linspace(lo, hi, n_interior + 2)[1:-1]
        t = np.r_[[lo] * 4, inner, [hi] * 4]
        try:
            spline = make_lsq_spline(x, flux, t, k=3, w=1 / err)
            if np.all(np.isfinite(spline.c)):
                return Steady(spline, None, len(x), n_interior, (float(np.exp(lo)), float(np.exp(hi))))
        except (ValueError, np.linalg.LinAlgError):
            pass
        n_interior -= 1
    deg = min(2, len(x) - 1)
    return Steady(None, np.polyfit(x, flux, deg, w=1 / err), len(x), 0, (float(np.exp(lo)), float(np.exp(hi))))


def robust_std(values) -> float:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if v.size < 3:
        return float("nan")
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


def jitter(g, g_err) -> float:
    """Fraction s so that (g - 1) / sqrt(g_err² + s²) has a robust spread of 1 (0 if it already does)."""
    g, g_err = np.asarray(g, float), np.asarray(g_err, float)
    ok = np.isfinite(g) & np.isfinite(g_err)
    g, g_err = g[ok], g_err[ok]
    if g.size < 5 or robust_std((g - 1) / g_err) <= 1:
        return 0.0
    lo, hi = 0.0, max(1.0, robust_std(g) * 3)
    for _ in range(60):
        mid = (lo + hi) / 2
        if robust_std((g - 1) / np.sqrt(g_err ** 2 + mid ** 2)) > 1:
            lo = mid
        else:
            hi = mid
    return hi


def fit_baseline(phi, g, g_err) -> dict:
    """c0 + a1 cos 2πφ + a2 cos 4πφ fitted to out-of-eclipse g; flat (1) unless a cosine is significant."""
    phi, g, g_err = (np.asarray(a, float) for a in (phi, g, g_err))
    ok = np.isfinite(g) & np.isfinite(g_err) & (g_err > 0)
    flat = {"used": False, "c0": 1.0, "a1": 0.0, "a2": 0.0, "a1_err": None, "a2_err": None}
    if ok.sum() < 10:
        return flat
    A = np.c_[np.ones(ok.sum()), np.cos(2 * np.pi * phi[ok]), np.cos(4 * np.pi * phi[ok])]
    w = 1 / g_err[ok]
    coef, *_ = np.linalg.lstsq(A * w[:, None], g[ok] * w, rcond=None)
    cov = np.linalg.inv((A * w[:, None]).T @ (A * w[:, None]))
    resid = (g[ok] - A @ coef) * w
    scale = max(1.0, float(np.sqrt(np.sum(resid ** 2) / max(1, ok.sum() - 3))))
    errs = np.sqrt(np.diag(cov)) * scale
    out = {"c0": float(coef[0]), "a1": float(coef[1]), "a2": float(coef[2]),
           "a1_err": float(errs[1]), "a2_err": float(errs[2])}
    out["used"] = bool(max(abs(coef[1]) / errs[1], abs(coef[2]) / errs[2]) > BASELINE_SIGNIFICANCE)
    return out if out["used"] else {**flat, "a1_err": out["a1_err"], "a2_err": out["a2_err"],
                                     "a1_fit": out["a1"], "a2_fit": out["a2"]}


def baseline_at(phi, base: dict) -> np.ndarray:
    phi = np.asarray(phi, float)
    if not base["used"]:
        return np.ones_like(phi)
    return base["c0"] + base["a1"] * np.cos(2 * np.pi * phi) + base["a2"] * np.cos(4 * np.pi * phi)


def weighted_depth(rel, rel_err) -> dict | None:
    """1 - weighted mean of rel (= g / baseline), error enlarged by sqrt(reduced χ²) when that is above 1."""
    rel, rel_err = np.asarray(rel, float), np.asarray(rel_err, float)
    ok = np.isfinite(rel) & np.isfinite(rel_err) & (rel_err > 0)
    n = int(ok.sum())
    if n < MIN_POINTS_PER_BIN:
        return None
    w = 1 / rel_err[ok] ** 2
    mean = float(np.sum(w * rel[ok]) / np.sum(w))
    err = float(1 / np.sqrt(np.sum(w)))
    chi2 = float(np.sum(w * (rel[ok] - mean) ** 2) / max(1, n - 1))
    return {"n": n, "depth": 1 - mean, "err": err * max(1.0, np.sqrt(chi2)), "chi2_red": chi2}


def bin_edges(detector: int, wl_range: tuple[float, float], n: int = BINS_PER_DETECTOR) -> np.ndarray:
    """n bins equally wide in ln λ across the wavelengths actually measured on this detector."""
    lo, hi = wl_range
    return np.exp(np.linspace(np.log(lo), np.log(hi) + 1e-9, n + 1))


def depth_spectrum(det, wl, rel, rel_err, select, ranges: dict) -> list[dict]:
    """Depth per wavelength bin (BINS_PER_DETECTOR per detector) for the exposures in `select`."""
    det, wl, rel, rel_err, select = (np.asarray(a) for a in (det, wl, rel, rel_err, select))
    out = []
    for d in sorted(ranges):
        edges = bin_edges(d, ranges[d])
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = select & (det == d) & (wl >= lo) & (wl < hi)
            res = weighted_depth(rel[m], rel_err[m])
            row = {"detector": int(d), "wl_lo": round(float(lo), 4), "wl_hi": round(float(hi), 4),
                   "wl_mid": round(float(np.sqrt(lo * hi)), 4)}
            if res is None:
                out.append({**row, "n": int(m.sum()), "depth": None, "err": None})
            else:
                out.append({**row, "n": res["n"], "depth": round(res["depth"], 5), "err": round(res["err"], 5),
                            "chi2_red": round(res["chi2_red"], 2),
                            "wl_mean": round(float(np.mean(wl[m & np.isfinite(rel)])), 4)})
    return out


def chi2_against_zero(rows: list[dict]) -> dict:
    """Is a set of depths consistent with zero? χ², degrees of freedom and the combined depth."""
    vals = [(r["depth"], r["err"]) for r in rows if r.get("depth") is not None]
    if not vals:
        return {"n_bins": 0}
    d, e = np.array(vals).T
    w = 1 / e ** 2
    return {"n_bins": len(d), "chi2": round(float(np.sum((d / e) ** 2)), 2),
            "combined": round(float(np.sum(w * d) / np.sum(w)), 5), "combined_err": round(float(1 / np.sqrt(np.sum(w))), 5)}


# ---------- when is the middle of the eclipse? ----------

FLAT_FRACTIONS = (0.0, 0.2, 0.4, 0.6)   # trapezoid shapes tried: flat bottom as a fraction of the full width


def trapezoid(dphi, width: float, flat: float) -> np.ndarray:
    """1 in the flat bottom, falling linearly to 0 at ±width/2 (0 outside)."""
    a = np.abs(dphi) / (width / 2)
    return np.clip((1 - a) / max(1e-9, 1 - flat), 0, 1)


def eclipse_timing(det, phi, rel, rel_err, width: float, search: float | None = None) -> dict | None:
    """Shift δ of the primary eclipse's middle from phase 0, fitting a trapezoid with one depth per detector.

    For each trial δ (and flat-bottom fraction) the depths are a weighted linear fit, so only δ is searched.
    Error: Δχ² = 1 after scaling χ² to a reduced χ² of 1. Uses exposures within one eclipse width of 0.
    """
    det, phi, rel, rel_err = (np.asarray(a, float) for a in (det, phi, rel, rel_err))
    near = np.isfinite(rel) & np.isfinite(rel_err) & (rel_err > 0) & (np.abs(phi) < width)
    if near.sum() < 10:
        return None
    det, phi, y, w = det[near], phi[near], 1 - rel[near], 1 / rel_err[near] ** 2
    dets = np.unique(det)
    search = width / 2 if search is None else search
    deltas = np.linspace(-search, search, 801)

    def chi2(delta, flat):
        total = 0.0
        for d in dets:
            m = det == d
            s = trapezoid(phi[m] - delta, width, flat)
            den = np.sum(w[m] * s * s)
            depth = np.sum(w[m] * s * y[m]) / den if den > 0 else 0.0
            total += np.sum(w[m] * (y[m] - depth * s) ** 2)
        return total

    best = None
    for flat in FLAT_FRACTIONS:
        curve = np.array([chi2(d, flat) for d in deltas])
        i = int(np.argmin(curve))
        if best is None or curve[i] < best[1][best[0]]:
            best = (i, curve, flat)
    i, curve, flat = best
    dof = max(1, near.sum() - len(dets) - 1)
    scaled = curve / max(1.0, curve[i] / dof)
    inside = deltas[scaled <= scaled[i] + 1]
    at_edge = i in (0, len(deltas) - 1)
    return {"delta_phase": float(deltas[i]), "err_phase": float((inside.max() - inside.min()) / 2),
            "flat_fraction": flat, "n": int(near.sum()), "reduced_chi2": float(curve[i] / dof), "at_search_edge": at_edge}


# ---------- period search without TESS (phase dispersion minimisation, Stellingwerf 1978) ----------

def pdm_theta(t, y, periods, n_bins: int = 10) -> np.ndarray:
    """θ = pooled variance within phase bins / total variance, for each trial period (lower = better)."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    total = np.var(y, ddof=1)
    out = np.empty(len(periods))
    for i, p in enumerate(periods):
        b = np.floor(((t / p) % 1.0) * n_bins).astype(int)
        n = np.bincount(b, minlength=n_bins)
        s = np.bincount(b, y, minlength=n_bins)
        s2 = np.bincount(b, y * y, minlength=n_bins)
        used = n > 1
        within = np.sum(s2[used] - s[used] ** 2 / n[used])
        out[i] = (within / max(1, n[used].sum() - used.sum())) / total
    return out


def trial_periods(t, p_min: float, p_max: float, oversample: float = 10.0) -> np.ndarray:
    """Evenly spaced in frequency, fine enough that phases drift by < 1/oversample over the time span."""
    span = float(np.nanmax(t) - np.nanmin(t))
    df = 1 / (oversample * span)
    freqs = np.arange(1 / p_max, 1 / p_min, df)
    return 1 / freqs[::-1]
