"""Eclipse depth against wavelength for one star of a field_psf.py run, for the primary and secondary eclipse.

    PYTHONPATH=. .venv/bin/python research/depth_spectrum.py NAME SOURCE_ID TIC [--shift-from-timing]

Depth per detector, split at the median wavelength of each detector (2 bins x 6 detectors = 0.75-5 µm), from
exposures in the middle half of each eclipse (|phase - centre| < width/4), against the star's own normal brightness
S(λ) (out-of-eclipse fit, field_analysis.py). With --shift-from-timing the eclipse centres come from
eclipse_timing.py (timing_<SOURCE_ID>.json) instead of the TESS clock.
The ratio secondary/primary depth is the ratio of the two stars' surface brightness (Planck), independent of
extra light from other stars, so its change with wavelength says how different the two temperatures are.
Writes depth_spectrum_<SOURCE_ID>.json and .png in the run folder.
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from backend.app import eclipse_depth as M  # noqa: E402
from backend.app import eclipses as E  # noqa: E402
from field_psf import ephemeris  # noqa: E402

RESULTS = Path(__file__).parent / "experimental_results"


def main(name, source_id, tic, shift):
    folder = RESULTS / name
    lc = np.load(folder / "lightcurves.npz")
    meta = json.loads((folder / "meta.json").read_text())
    stars = json.loads((folder / "stars.json").read_text())
    analysis = json.loads((folder / "analysis.json").read_text())
    j = next(i for i, s in enumerate(stars) if s["source_id"] == source_id)
    eph = ephemeris(tic, meta.get("eph_json"))
    phi = lc["phi"] % 1
    det, wl = lc["det"], lc["wl"]
    g, ge = lc["gc"][:, j], lc["ge"][:, j]
    jit = (analysis["stars"][j].get("jitter_pct") or 0) / 100
    ge = np.sqrt(ge ** 2 + jit ** 2)
    centres = {"primary": 0.0, "secondary": E.secondary_phase(eph) or 0.5}
    if shift:
        t = json.loads((folder / f"timing_{source_id}.json").read_text())["eclipses"]
        for k in centres:
            if "phase_offset" in t.get(k, {}):
                centres[k] = (centres[k] + t[k]["phase_offset"]) % 1
    half = eph.prim_width / 4
    out = {"source_id": source_id, "centres": centres, "half_window_phase": half, "bins": []}
    for d in sorted(np.unique(det)):
        m_d = (det == d) & np.isfinite(g) & np.isfinite(wl)
        if m_d.sum() < 10:
            continue
        cut = np.median(wl[m_d])
        for lo_hi, m_w in (("short", m_d & (wl <= cut)), ("long", m_d & (wl > cut))):
            rec = {"detector": int(d), "half": lo_hi, "wl_um": round(float(np.median(wl[m_w])), 3)}
            for k, c in centres.items():
                x = np.abs((phi - c + 0.5) % 1 - 0.5)
                m = m_w & (x < half)
                r = M.weighted_depth(g[m], ge[m]) if m.sum() >= 2 else None
                rec[k] = None if r is None else {"depth": round(r["depth"], 4), "err": round(r["err"], 4), "n": int(m.sum())}
            out["bins"].append(rec)
    (folder / f"depth_spectrum_{source_id}.json").write_text(json.dumps(out, indent=1))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, col in (("primary", "#c0392b"), ("secondary", "#2f6db5")):
        pts = [(b["wl_um"], b[k]["depth"], b[k]["err"]) for b in out["bins"] if b.get(k)]
        if pts:
            x, y, e = map(np.array, zip(*pts))
            ax.errorbar(x, 100 * y, 100 * e, fmt="o", color=col, label=f"{k} eclipse (phase {centres[k]:.3f})")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("wavelength (µm)")
    ax.set_ylabel("eclipse depth (%)")
    ax.set_title(f"SPHEREx eclipse depth vs wavelength, Gaia DR3 {source_id}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(folder / f"depth_spectrum_{source_id}.png", dpi=110)
    for b in out["bins"]:
        print(b)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("source_id")
    p.add_argument("tic")
    p.add_argument("--shift-from-timing", action="store_true")
    a = p.parse_args()
    main(a.name, a.source_id, a.tic, a.shift_from_timing)
