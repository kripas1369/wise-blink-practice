"""Independent flux-scale check: SPHEREx forced photometry at 2.00-2.30 um against 2MASS Ks (from SPLICES).

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/flux_check.py

2MASS Ks (2.16 um, 1997-2001, ~2" resolution) and SPHEREx (2025-2026, 6.2" pixels) are separated by ~25 yr and differ
in bandpass and resolution, so agreement is expected only for non-variable, isolated sources and only to the level of
the in-band spectral slope (~10-20 %). The quantity compared is the ratio of the per-visit median SPHEREx flux density
in 2.00-2.30 um to the 2MASS Ks flux density (zero point 666.7 Jy, Cohen et al. 2003).
Output: VALIDATION/flux_check.csv and flux_check.json
"""
import csv
import json
import math

import numpy as np

import ice_fit as I

SAMPLE = I.ROOT / "data" / "lists" / "sample.csv"
OUT = I.ROOT / "VALIDATION"
KS_ZP = 666.7
LO, HI = 2.00, 2.30


def ks_by_designation():
    out = {}
    for fn in ("splices_protostars_w2lt10p5.csv", "splices_background_stars.csv"):
        for r in csv.DictReader(open(I.ROOT / "data" / "selection" / fn)):
            try:
                out[r["designation"]] = float(r["k"])
            except (KeyError, ValueError):
                pass
    return out


def main():
    kmag = ks_by_designation()
    rows = []
    for s in csv.DictReader(open(SAMPLE)):
        f = I.PHOT / f"{s['name']}.csv"
        ks = kmag.get(s["designation"])
        if not f.exists() or ks is None or not math.isfinite(ks):
            continue
        pts, _, _ = I.load(s["name"])
        q = [p for p in pts if LO <= p["wl"] <= HI]
        if not q:
            continue
        for vi, v in enumerate(I.clusters([p["mjd"] for p in q], I.VISIT_GAP)):
            fl = np.array([q[i]["f"] for i in v])
            rows.append({"name": s["name"], "role": s["role"], "visit": vi, "n": len(fl),
                         "mjd": round(float(np.mean([q[i]["mjd"] for i in v])), 1), "ks_mag": ks,
                         "spherex_mjy": 1e3 * float(np.median(fl)), "twomass_mjy": 1e3 * KS_ZP * 10 ** (-0.4 * ks),
                         "log10_ratio": math.log10(float(np.median(fl)) / (KS_ZP * 10 ** (-0.4 * ks)))})
    with open(OUT / "flux_check.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summ = {}
    for role in ("CTRL", "BGSTAR", "VAR"):
        r = np.array([x["log10_ratio"] for x in rows if x["role"] == role])
        if len(r):
            summ[role] = {"n_visits": int(len(r)), "n_targets": len({x["name"] for x in rows if x["role"] == role}),
                          "median_log10_ratio": float(np.median(r)),
                          "robust_sigma_dex": float(1.4826 * np.median(np.abs(r - np.median(r))))}
    (OUT / "flux_check.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
