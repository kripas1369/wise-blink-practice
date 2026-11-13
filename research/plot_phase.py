"""Blind phase scan of one tested pair: per-exposure two-star (PSF) brightness of both stars folded on TESS's period.

    MPLCONFIGDIR=/tmp/mpl PYTHONPATH=. .venv/bin/python research/plot_phase.py TIC_A TIC_B

Top: whole orbit. Bottom: zoom on the primary and the secondary eclipse. Black squares are binned means.
The dip search uses no knowledge of where the eclipse should be, so it also catches a wrong period or phase.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from backend.app import eclipses as E  # noqa: E402

OUT = Path(__file__).parent / "out"
SCAN_HALF_WIDTH = 0.012   # phase


def scan(phi, f, e):
    """Weighted dip depth / error in a sliding window, at every 0.005 in phase, leaving out the lowest point."""
    ok = np.isfinite(f) & np.isfinite(e) & (e > 0)
    best = None
    for c in np.arange(0, 1, 0.005):
        m = ok & (np.abs((phi - c + 0.5) % 1 - 0.5) < SCAN_HALF_WIDTH)
        if m.sum() < 5:
            continue
        idx = np.flatnonzero(m)
        m[idx[np.argmax((1 - f[idx]) / e[idx])]] = False   # one bad exposure must not make a dip
        w = 1 / e[m] ** 2
        dep, err = 1 - np.sum(w * f[m]) / w.sum(), 1 / np.sqrt(w.sum())
        if best is None or dep / err > best[0]:
            best = (dep / err, c, dep, err, int(m.sum()))
    return best


def binned(x, f, e, edges):
    xs, ys, es = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (x >= lo) & (x < hi) & np.isfinite(f) & (e > 0)
        if m.sum() >= 2:
            w = 1 / e[m] ** 2
            xs.append((lo + hi) / 2), ys.append(np.sum(w * f[m]) / w.sum()), es.append(1 / np.sqrt(w.sum()))
    return np.array(xs), np.array(ys), np.array(es)


def main(a, b):
    folder = OUT / f"pair_{a}_{b}"
    res = json.loads((folder / "result.json").read_text())
    z = np.load(folder / "points.npz")
    clock = E.by_tess_id(res["clock"]["tess_id"])
    sec = clock.sec_pos if clock.sec_pos is not None else 0.5
    phi = z["phi"] % 1
    fig = plt.figure(figsize=(12, 7.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1])
    colours = {"A": "#c0392b", "B": "#2f6db5"}
    summary = {}
    ax_all = fig.add_subplot(gs[0, :])
    for k, tid in (("A", a), ("B", b)):
        f, e = z[f"p{k}"], z[f"pe{k}"]
        off = 0 if k == "A" else -0.25
        ax_all.errorbar(phi, f + off, e, fmt="o", ms=2.5, lw=0.4, alpha=0.5, color=colours[k],
                        label=f"TIC {tid}" + ("" if k == "A" else " (shifted −0.25)"))
        best = scan(phi, f, e)
        summary[tid] = None if best is None else {"snr": round(best[0], 2), "phase": round(best[1], 3),
                                                  "depth": round(best[2], 4), "err": round(best[3], 4), "n": best[4]}
    for x in (0, 1, sec):
        ax_all.axvline(x, color="k", lw=0.6, ls=":")
    ax_all.set_xlim(-0.02, 1.02)
    ax_all.set_ylim(0.45, 1.3)
    ax_all.set_xlabel("orbital phase (TESS period)")
    ax_all.set_ylabel("brightness / normal")
    ax_all.legend(loc="lower center", ncol=2, fontsize=9)
    for col, (centre, name) in enumerate(((0.0, "primary eclipse"), (sec, "secondary eclipse"))):
        ax = fig.add_subplot(gs[1, col])
        x = (phi - centre + 0.5) % 1 - 0.5
        for k, tid in (("A", a), ("B", b)):
            f, e = z[f"p{k}"], z[f"pe{k}"]
            m = np.abs(x) < 0.06
            ax.errorbar(x[m], f[m], e[m], fmt="o", ms=3, lw=0.5, alpha=0.55, color=colours[k])
            bx, by, be = binned(x, f, e, np.linspace(-0.06, 0.06, 13))
            ax.errorbar(bx, by, be, fmt="s", ms=6, mfc=colours[k], mec="k", ecolor="k", lw=1)
        ax.axhline(1, color="k", lw=0.6)
        ax.set_title(f"{name} (phase {centre:.3f})", fontsize=10)
        ax.set_xlabel("phase from eclipse centre")
        ax.set_ylim(0.6, 1.25)
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    lines = [f"{res['sep_arcsec']}″ apart, P = {clock.period:.5f} d", f"{len(phi)} SPHEREx exposures (DR1 + QR3)", "",
             "strongest dip anywhere in phase:"]
    for tid, s in summary.items():
        lines.append(f"TIC {tid}: " + ("none" if s is None else
                     f"{100 * s['depth']:.1f} ± {100 * s['err']:.1f} % at phase {s['phase']:.3f} ({s['snr']:.1f}σ)"))
    ax.text(0, 0.95, "\n".join(lines), va="top", fontsize=9.5)
    fig.suptitle(f"SPHEREx per-exposure two-star photometry: TIC {a} (red) vs TIC {b} (blue)")
    fig.tight_layout()
    out = folder / "phase_scan.png"
    fig.savefig(out, dpi=110)
    (folder / "phase_scan.json").write_text(json.dumps(summary, indent=1))
    print(out, summary)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
