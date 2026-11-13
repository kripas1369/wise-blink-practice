"""Eclipse centre, depth and width in SPHEREx data for one star of a field_psf.py run, with bootstrap errors.

    PYTHONPATH=. .venv/bin/python research/eclipse_timing.py NAME SOURCE_ID TIC

Model near each eclipse (|phase - centre| < WINDOW): f = c - D exp(-(phase - phi0)^2 / (2 w^2)), with c, D, phi0, w
free (w bounded around the TESS width). An offset of phi0 from TESS's prediction (0 for the primary, TESS's secondary
phase for the secondary) means the eclipse came early or late: a wrong period, apsidal motion or a third body.
Errors: 1000 bootstrap resamples of the exposures. Writes timing_<SOURCE_ID>.json in the run folder.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

from backend.app import eclipses as E
from field_psf import ephemeris

RESULTS = Path(__file__).parent / "experimental_results"
WINDOW = 0.12
N_BOOT = 1000


def model(p, c, d, p0, w):
    return c - d * np.exp(-0.5 * ((p - p0) / w) ** 2)


def fit(x, f, e, w0):
    p0 = [1.0, min(0.9, max(0.02, 1 - np.nanpercentile(f, 5))), 0.0, w0]
    bounds = ([0.8, -0.5, -0.06, 0.25 * w0], [1.2, 1.0, 0.06, 3 * w0])
    popt, _ = curve_fit(model, x, f, p0=p0, sigma=e, absolute_sigma=False, bounds=bounds, maxfev=20000)
    return popt


def main(name, source_id, tic):
    folder = RESULTS / name
    lc = np.load(folder / "lightcurves.npz")
    stars = json.loads((folder / "stars.json").read_text())
    j = next(i for i, s in enumerate(stars) if s["source_id"] == source_id)
    meta = json.loads((folder / "meta.json").read_text())
    eph = ephemeris(tic, meta.get("eph_json"))
    phi = lc["phi"] % 1
    g, ge = lc["gc"][:, j], lc["ge"][:, j]
    analysis = json.loads((folder / "analysis.json").read_text())
    jit = (analysis["stars"][j].get("jitter_pct") or 0) / 100
    ge = np.sqrt(ge ** 2 + jit ** 2)
    sec = E.secondary_phase(eph) or 0.5
    w0 = eph.prim_width / 4          # TESS full width ~ 4 sigma of a Gaussian
    out = {"source_id": source_id, "tic_clock": tic, "period": eph.period, "tess_secondary_phase": sec, "eclipses": {}}
    rng = np.random.default_rng(1)
    for nm, centre in (("primary", 0.0), ("secondary", sec)):
        x = (phi - centre + 0.5) % 1 - 0.5
        m = np.isfinite(g) & np.isfinite(ge) & (ge > 0) & (np.abs(x) < WINDOW)
        if m.sum() < 15:
            out["eclipses"][nm] = {"n": int(m.sum()), "reason": "too few exposures near the eclipse"}
            continue
        xs, fs, es = x[m], g[m], ge[m]
        try:
            best = fit(xs, fs, es, w0)
        except Exception as exc:
            out["eclipses"][nm] = {"n": int(m.sum()), "reason": f"fit failed: {exc}"}
            continue
        boots = []
        for _ in range(N_BOOT):
            k = rng.integers(0, len(xs), len(xs))
            try:
                boots.append(fit(xs[k], fs[k], es[k], w0))
            except Exception:
                pass
        b = np.array(boots)
        lo, hi = np.percentile(b, [16, 84], axis=0)
        out["eclipses"][nm] = {
            "n": int(m.sum()), "n_boot": len(b),
            "depth": round(float(best[1]), 4), "depth_err": round(float((hi[1] - lo[1]) / 2), 4),
            "phase_offset": round(float(best[2]), 5), "phase_offset_err": round(float((hi[2] - lo[2]) / 2), 5),
            "offset_minutes": round(float(best[2] * eph.period * 1440), 1),
            "offset_minutes_err": round(float((hi[2] - lo[2]) / 2 * eph.period * 1440), 1),
            "width_sigma_phase": round(float(best[3]), 5), "tess_width_sigma_phase": round(w0, 5),
            "clock_error_phase": round(eph.phase_error(float(np.median(lc["btjd"]))), 5)}
    (folder / f"timing_{source_id}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
