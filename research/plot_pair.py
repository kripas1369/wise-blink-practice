"""Figure for one pair tested by which_star_pair.py.

    MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python research/plot_pair.py TIC_A TIC_B

Left: each star's brightness (divided by its own normal brightness) against time from TESS's predicted primary
eclipse, in hours. Right: the two-star-fit depth of each star per SPHEREx detector (wavelength).
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path(__file__).parent / "out"


def main(a, b):
    folder = OUT / f"pair_{a}_{b}"
    res = json.loads((folder / "result.json").read_text())
    z = np.load(folder / "points.npz")
    P = res["clock"]["period"]
    w = res["clock"]["prim_width"]
    hours = z["phi"] * P * 24
    half = w * P * 24 / 2
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), gridspec_kw={"width_ratios": [1.6, 1]})
    lim = max(3 * half, 2.0)
    for row, (tid, key) in enumerate(((a, "A"), (b, "B"))):
        ax = axes[row, 0]
        g, ge = z[f"g{key}"], z[f"ge{key}"]
        m = np.isfinite(g) & (np.abs(hours) < lim)
        ax.axvspan(-half, half, color="#fde9c8", zorder=0)
        ax.errorbar(hours[m], g[m], ge[m], fmt="o", ms=3, lw=0.6, color="#c0392b" if row == 0 else "#2f6db5", alpha=0.8)
        ax.axhline(1, color="k", lw=0.7)
        s = res["stars"][tid]
        gaia = s.get("gaia") or {}
        circle = s["circle"]["primary"]
        ax.set_title(f"TIC {tid} (G {gaia.get('g_mag', float('nan')):.1f}, TESS-EBs depth {s['tess_depth']:.3f}); "
                     f"SPHEREx dip {circle['depth']:.3f} ± {circle['err']:.3f}" if circle else f"TIC {tid}", fontsize=9)
        ax.set_ylim(0.4 if np.nanmin(g[m]) < 0.75 else 0.8, 1.2)
        ax.set_xlim(-lim, lim)
        ax.set_ylabel("brightness / normal")
    axes[1, 0].set_xlabel("hours from TESS's predicted primary eclipse (shaded: eclipse)")
    ax = axes[0, 1]
    fits = res["two_star_fit"]["per_detector"]
    for key, col, off in (("A", "#c0392b", -0.04), ("B", "#2f6db5", 0.04)):
        xs, ys, es = [], [], []
        for f in fits.values():
            if f.get(f"depth_{key}") is not None:
                xs.append(f["wl_um"] + off)
                ys.append(f[f"depth_{key}"])
                es.append(f[f"err_{key}"])
        tid = a if key == "A" else b
        comb = res["two_star_fit"][key]
        ax.errorbar(xs, ys, es, fmt="o", color=col,
                    label=f"TIC {tid}: {comb['depth']:.3f} ± {comb['err']:.3f}" if comb else f"TIC {tid}")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xlabel("wavelength (µm)")
    ax.set_ylabel("depth (two-star fit)")
    ax.legend(fontsize=8)
    ax.set_title("which star loses light during the eclipse", fontsize=9)
    axes[1, 1].axis("off")
    txt = (f"{res['sep_arcsec']:.1f}″ apart (TESS pixel 21″, SPHEREx 6.15″)\n"
           f"period {P:.5f} d, clock from TIC {res['clock']['tess_id']}\n"
           f"{res['n_exposures']} SPHEREx exposures measured\n"
           f"(of {res['n_images_archive']} in the archive)")
    axes[1, 1].text(0, 0.9, txt, va="top", fontsize=9)
    fig.suptitle(f"SPHEREx: which star makes the {P:.3f}-day eclipse TESS-EBs lists under both TIC {a} and TIC {b}?",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(folder / "which_star.png", dpi=110)
    print(folder / "which_star.png")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
