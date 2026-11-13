"""Empirical significance of an eclipse depth (no Gaussian-error assumption).

    PYTHONPATH=.:research .venv/bin/python research/significance.py NAME --tic TIC --centre PHASE [--stars ID ID ...]

For each star: weighted mean of the normalised flux within |phase - centre| < half-width, as a depth, compared with
the same statistic at N_TRIALS random phase centres (weights 1/(formal error² + the star's jitter²), as in the
depth measurement) that stay clear of both eclipses (phase 0 and centre/0.5). The
empirical false-alarm probability is the fraction of random centres giving a depth at least as large; the
"z_empirical" is (depth - mean of trials) / std of trials. This keeps any red noise, wavelength systematics or
outliers of the real data in the comparison. Default stars: the most significant ones from analysis.json plus all
stars passed with --stars. Writes significance_<centre>.json in the run folder.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from field_psf import ephemeris

RESULTS = Path(__file__).parent / "experimental_results"
N_TRIALS = 1000


def depth_at(phi, g, w, c, half):
    m = (np.abs((phi - c + 0.5) % 1 - 0.5) < half) & np.isfinite(g)
    if m.sum() < 3:
        return np.nan, int(m.sum())
    return 1 - np.sum(w[m] * g[m]) / np.sum(w[m]), int(m.sum())


def main(name, tic, centre, ids, seed=1):
    folder = RESULTS / name
    meta = json.loads((folder / "meta.json").read_text())
    stars = json.loads((folder / "stars.json").read_text())
    lc = np.load(folder / "lightcurves.npz")
    eph = ephemeris(tic, meta.get("eph_json"))
    phi = lc["phi"] % 1
    half = eph.prim_width / 4
    rng = np.random.default_rng(seed)
    avoid = [0.0, centre % 1, 0.5]
    trial_c = []
    while len(trial_c) < N_TRIALS:
        c = rng.uniform(0, 1)
        if all(abs((c - a + 0.5) % 1 - 0.5) > 2.5 * half + eph.prim_width / 2 for a in avoid):
            trial_c.append(c)
    out = {"centre": centre, "half_width": half, "n_trials": N_TRIALS, "stars": {}}
    analysis = json.loads((folder / "analysis.json").read_text())
    for sid in ids:
        j = next(i for i, s in enumerate(stars) if s["source_id"] == sid)
        jit = (analysis["stars"][j].get("jitter_pct") or 0) / 100
        g, ge = lc["gc"][:, j], np.sqrt(lc["ge"][:, j] ** 2 + jit ** 2)
        w = np.where(np.isfinite(ge) & (ge > 0), 1 / np.maximum(ge, 1e-3) ** 2, 0)
        d, n = depth_at(phi, g, w, centre, half)
        trials = np.array([depth_at(phi, g, w, c, half)[0] for c in trial_c])
        trials = trials[np.isfinite(trials)]
        rec = {"g_mag": round(stars[j]["g_mag"], 2), "depth": round(float(d), 4), "n_in": n,
               "trials_mean": round(float(trials.mean()), 4), "trials_std": round(float(trials.std()), 4),
               "z_empirical": round(float((d - trials.mean()) / trials.std()), 2),
               "fap_empirical": float((np.sum(trials >= d) + 1) / (len(trials) + 1))}
        out["stars"][sid] = rec
        print(sid, rec)
    (folder / f"significance_{centre:.3f}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--tic", required=True)
    p.add_argument("--centre", type=float, default=0.0)
    p.add_argument("--stars", nargs="+", required=True)
    a = p.parse_args()
    main(a.name, a.tic, a.centre, a.stars)
