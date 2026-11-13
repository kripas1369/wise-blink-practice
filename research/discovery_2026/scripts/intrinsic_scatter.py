"""Population constraint on visit-to-visit changes of ice absorption depth (maximum likelihood).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/intrinsic_scatter.py

Input: EXPERIMENTAL_RESULTS/population/pairs.csv (consecutive pairs, quality_ok, ice detected). For each pair the
fractional change r = d / mean_depth (H2O: tau; CO2: equivalent width) with error e = d_err / mean_depth. Model:
r_i ~ N(0, (k e_i)^2 + s^2), s = rms intrinsic fractional change between consecutive independent epochs (visits or
same-visit passes, 0.5-12 months apart). k = 1 uses the fit errors as they are; k = control MAD z (from
summary.json floors where available) rescales them to the empirical scatter of ice-detected controls, which raises
s when the fit errors are conservative. The profile likelihood gives the MLE of s and a one-sided 95 % upper limit
(delta(-2 ln L) = 2.71). A bootstrap over targets gives the spread of the MLE.
Output: EXPERIMENTAL_RESULTS/population/intrinsic_scatter.json
"""
import csv
import json

import numpy as np

import ice_fit as I

POP = I.ROOT / "EXPERIMENTAL_RESULTS" / "population"
SEED = 20261113
GRID = np.linspace(0.0, 1.0, 2001)


def nll(r, e, s):
    v = e[:, None] ** 2 + s[None, :] ** 2
    return 0.5 * np.sum(r[:, None] ** 2 / v + np.log(v), 0)


def profile(r, e):
    L = nll(r, e, GRID)
    i = int(np.argmin(L))
    above = np.where((GRID > GRID[i]) & (L - L[i] >= 2.71 / 2))[0]
    return float(GRID[i]), float(GRID[above[0]]) if len(above) else float("nan")


def main():
    rows = [x for x in csv.DictReader(open(POP / "pairs.csv"))
            if x["consecutive"] == "True" and x["quality_ok"] == "True" and x["detected"] == "True"]
    summ = json.load(open(POP / "summary.json"))
    rng = np.random.default_rng(SEED)
    out = {}
    for band in ("H2O", "CO2"):
        for role in ("VAR", "CTRL", "BGSTAR", "VALIDATION"):
            sub = [x for x in rows if x["band"] == band and x["role"] == role]
            if len(sub) < 3:
                continue
            r = np.array([float(x["d"]) / float(x["mean_depth"]) for x in sub])
            e = np.array([float(x["d_err"]) / float(x["mean_depth"]) for x in sub])
            names = np.array([x["name"] for x in sub])
            dl = np.array([abs(float(x["dlncont"])) for x in sub])
            res = {"n_pairs": len(sub), "n_targets": int(len(set(names))),
                   "median_abs_dlncont": float(np.median(dl)), "max_abs_dlncont": float(dl.max()),
                   "median_frac_err": float(np.median(e))}
            ks = {"fit_errors": 1.0}
            mad = summ["quality_selection"]["floors"].get(band, {}).get("mad_z")
            if mad:
                ks["errors_x_control_MAD_z"] = float(mad)
            for kname, k in ks.items():
                mle, ul = profile(r, k * e)
                boots = []
                uniq = np.unique(names)
                for _ in range(1000):
                    pick = rng.choice(uniq, len(uniq))
                    idx = np.concatenate([np.where(names == u)[0] for u in pick])
                    boots.append(profile(r[idx], k * e[idx])[0])
                res[kname] = {"k": k, "s_mle": mle, "s_upper95": ul,
                              "s_mle_boot_16_84": [float(np.percentile(boots, 16)), float(np.percentile(boots, 84))]}
            big = dl >= 0.5
            if big.sum() >= 3:
                mle, ul = profile(r[big], e[big])
                res["pairs_with_abs_dlncont_ge_0.5"] = {"n": int(big.sum()), "s_mle": mle, "s_upper95": ul}
            out[f"{band}_{role}"] = res
            print(band, role, json.dumps(res), flush=True)
    (POP / "intrinsic_scatter.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
