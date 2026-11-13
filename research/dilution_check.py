"""Is "the eclipse is on the Gaia neighbour" physically possible for each misattributed TESS-EBs entry?

    .venv/bin/python research/dilution_check.py      -> research/out/dilution_check.json

If the neighbour (TESS magnitude T_eb) makes the eclipse and the TIC star (T_tic) is in the same TESS aperture,
the depth TESS measures is d = D f F_eb / (F_tic + f F_eb), where D is the neighbour's true depth and f <= 1 the
fraction of its light inside the aperture. So D >= d (1 + F_tic / F_eb) = D_min. D_min > 1 would mean the
neighbour cannot be the source (unless the TESS light curve was over-corrected for crowding).
T_eb from Gaia G and BP-RP with the Stassun et al. (2019) TIC-8 relation.
Also compares TESS depths of "other star" and "same star" entries (Mann-Whitney U test): if the eclipse is
borrowed from a neighbour, the measured depths should be smaller.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import ks_2samp, mannwhitneyu

OUT = Path(__file__).parent / "out"


def g_to_t(g, bp_rp):
    if bp_rp is None or not np.isfinite(bp_rp):
        return g - 0.43
    c = bp_rp
    return g - 0.00522555 * c ** 3 + 0.0891337 * c ** 2 - 0.633923 * c + 0.0324473


def main():
    d = json.loads((OUT / "tessebs_gaia_xmatch.json").read_text())
    singles = json.loads((OUT / "misattributed_singles.json").read_text())["singles"]
    rows = []
    for e in singles:
        o = e["other"][0]
        if not np.isfinite(e["tess_depth"]) or e["tess_depth"] <= 0 or e["tess_depth"] >= 1:
            continue
        t_eb = g_to_t(o["g_mag"], o["bp_rp"])
        ratio = 10 ** (-0.4 * (t_eb - e["tmag"]))      # F_eb / F_tic
        dmin = e["tess_depth"] * (1 + 1 / ratio)
        rows.append({"tic": e["tic"], "tmag": e["tmag"], "t_eb": round(t_eb, 2), "sep": o["sep"],
                     "tess_depth": e["tess_depth"], "flux_ratio_eb_to_tic": round(ratio, 4), "true_depth_min": round(dmin, 4)})
    dm = np.array([r["true_depth_min"] for r in rows])
    other_depth = np.array([r["tess_depth"] for r in rows])
    same = np.array([x["tess_depth"] for x in d["entries"] if x["class"] == "same star"
                     and np.isfinite(x["tess_depth"]) and 0 < x["tess_depth"] < 1])
    none = np.array([x["tess_depth"] for x in d["entries"] if x["class"] == "no Gaia EB"
                     and np.isfinite(x["tess_depth"]) and 0 < x["tess_depth"] < 1])
    u = mannwhitneyu(other_depth, same, alternative="less")
    ks_implied = ks_2samp(dm[dm <= 1], same)
    brighter_tic = np.array([r["flux_ratio_eb_to_tic"] < 1 for r in rows])
    summary = {
        "n_singles_with_depth": len(rows),
        "n_possible (D_min <= 1)": int((dm <= 1).sum()),
        "n_impossible (D_min > 1)": int((dm > 1).sum()),
        "fraction_tic_brighter_than_neighbour": round(float(brighter_tic.mean()), 3),
        "median_tess_depth": {"other star": float(np.median(other_depth)), "same star": float(np.median(same)),
                              "no Gaia EB": float(np.median(none))},
        "mann_whitney_other_less_than_same": {"U": float(u.statistic), "p": float(u.pvalue)},
        "median_true_depth_min": float(np.median(dm)),
        "ks_implied_depth_vs_same_star_depth": {"D": float(ks_implied.statistic), "p": float(ks_implied.pvalue),
                                                "note": "implied depths are lower bounds (f = 1)"},
    }
    (OUT / "dilution_check.json").write_text(json.dumps({"summary": summary, "entries": rows}, indent=1))
    print(json.dumps(summary, indent=1))
    for r in sorted(rows, key=lambda r: -r["true_depth_min"])[:12]:
        print(r)


if __name__ == "__main__":
    main()
