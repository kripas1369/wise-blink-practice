"""Feasibility check: is a water-ice (3.0 µm) or CO2-ice (4.27 µm) dip visible in SPHEREx spectra of
stars behind Barnard 68, and absent in unreddened stars beside it?

    python -m experiments.ice_check fetch     # download D4 + D5 cutouts (cached)
    python -m experiments.ice_check measure   # photometry, continuum fit, tau, plot

The plot needs matplotlib, which is not in requirements.txt (experiment only: pip install matplotlib).

Every point is one exposure: the star's light in a 2 px circle (lightcurve.measure) on IMAGE - ZODI with
the official bad-pixel mask, at the wavelength the filter passes at the star (clean.wavelength_at).
"""
import json
import sys
from pathlib import Path

import numpy as np

from backend.app.archive import attach_paths, download_cutouts, find_images
from backend.app.clean import clean_cutout
from backend.app.lightcurve import CORE_RADIUS_PX, SKY_ANNULUS_PX, measure

CLOUD = (260.659, -23.826)
SIZE_DEG = 0.15
BANDS = (4, 5)
OUT = Path(__file__).with_name("ice_b68")

# 2MASS PSC stars (K < 12.5); the field's unreddened colour is H-K ~ 0.2-0.3
STARS = [
    {"name": "behind A", "ra": 260.65794, "dec": -23.81429, "k": 10.23, "hk": 0.92},
    {"name": "behind B", "ra": 260.66782, "dec": -23.81542, "k": 11.20, "hk": 1.02},
    {"name": "behind C", "ra": 260.67331, "dec": -23.84060, "k": 11.94, "hk": 1.33},
    {"name": "outside D", "ra": 260.69846, "dec": -23.87995, "k": 8.17, "hk": 0.27},
    {"name": "outside E", "ra": 260.60772, "dec": -23.79570, "k": 9.24, "hk": 0.20},
]

FEATURES = {
    "H2O ice 3.0 um": {"band": 4, "dip": (2.90, 3.20), "continuum": [(2.42, 2.70), (3.62, 3.83)]},
    "CO2 ice 4.27 um": {"band": 5, "dip": (4.24, 4.30), "continuum": [(3.83, 4.18), (4.34, 4.42)]},
}


def images():
    return attach_paths([im for im in find_images(*CLOUD) if im.detector in BANDS])


def fetch():
    ims = images()
    for band in BANDS:
        some = [im for im in ims if im.detector == band]
        got = download_cutouts(some, *CLOUD, SIZE_DEG)
        failed = {k: str(v) for k, v in got.items() if isinstance(v, Exception)}
        print(f"D{band}: {len(some)} images, {len(some) - len(failed)} cutouts, {len(failed)} failed", flush=True)
        for k, v in list(failed.items())[:5]:
            print(" ", k, v[:120], flush=True)


def photometry():
    from backend.app.archive import cutout_file
    rows = []
    for im in images():
        path = cutout_file(im, *CLOUD, SIZE_DEG)
        if not path.exists():
            continue
        for s in STARS:
            c = clean_cutout(path, s["ra"], s["dec"])
            x, y = c["wcs"].world_to_pixel_values(s["ra"], s["dec"])
            ny, nx = c["image"].shape
            if not (14 < x < nx - 15 and 14 < y < ny - 15) or c["wl_um"] is None:
                continue
            m = measure(c["image"], c["sigma"], c["bad"], np.isfinite(c["image"]), float(x), float(y),
                        0.0, CORE_RADIUS_PX, SKY_ANNULUS_PX)
            if m["flux_mjy"] is None or m["n_flagged"]:
                continue
            rows.append({"star": s["name"], "band": im.detector, "obs_id": im.obs_id, "mjd": c["mjd"],
                         "wl_um": c["wl_um"], "bw_um": c["bw_um"], "flux_mjy": m["flux_mjy"],
                         "err_mjy": m["err_mjy"]})
    return rows


def tau(points, feature):
    """Fit ln(flux) linear in wavelength over the continuum windows; tau = ln(continuum / flux) in the dip."""
    wl = np.array([p["wl_um"] for p in points])
    f = np.array([p["flux_mjy"] for p in points])
    e = np.array([p["err_mjy"] for p in points])
    ok = f > 0
    wl, f, e = wl[ok], f[ok], e[ok]
    cont = np.zeros(len(wl), bool)
    for lo, hi in feature["continuum"]:
        cont |= (wl >= lo) & (wl < hi)
    dip = (wl >= feature["dip"][0]) & (wl <= feature["dip"][1])
    if cont.sum() < 4 or dip.sum() < 2:
        return None
    coef, cov = np.polyfit(wl[cont], np.log(f[cont]), 1, cov=True)
    resid = np.log(f[cont]) - np.polyval(coef, wl[cont])
    scatter = float(np.std(resid, ddof=2))
    t = np.polyval(coef, wl[dip]) - np.log(f[dip])
    t_err_point = np.hypot(e[dip] / f[dip], scatter)
    w = 1 / t_err_point ** 2
    mean = float(np.sum(w * t) / np.sum(w))
    err = float(np.sqrt(1 / np.sum(w)))
    return {"tau": round(mean, 3), "err": round(err, 3), "n_dip": int(dip.sum()), "n_cont": int(cont.sum()),
            "cont_scatter": round(scatter, 3), "coef": [float(c) for c in coef]}


def plot(rows, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(STARS), 2, figsize=(11, 2.3 * len(STARS)), sharex="col")
    for i, s in enumerate(STARS):
        for j, (name, feat) in enumerate(FEATURES.items()):
            ax = axes[i, j]
            pts = [p for p in rows if p["star"] == s["name"] and p["band"] == feat["band"]]
            if not pts:
                continue
            wl = np.array([p["wl_um"] for p in pts])
            f = np.array([p["flux_mjy"] for p in pts])
            e = np.array([p["err_mjy"] for p in pts])
            ax.errorbar(wl, f, e, fmt=".", ms=4, color="k", lw=0.6)
            ax.axvspan(*feat["dip"], color="gold", alpha=0.25)
            for lo, hi in feat["continuum"]:
                ax.axvspan(lo, hi, color="tab:blue", alpha=0.08)
            r = results[s["name"]].get(name)
            if r:
                xx = np.linspace(wl.min(), wl.max(), 100)
                ax.plot(xx, np.exp(np.polyval(r["coef"], xx)), color="tab:blue", lw=1)
                ax.set_title(f"{s['name']} (H-K {s['hk']}): {name} tau = {r['tau']} ± {r['err']}", fontsize=8)
            ax.set_ylabel("mJy", fontsize=8)
            ax.tick_params(labelsize=7)
    axes[-1, 0].set_xlabel("wavelength (µm)")
    axes[-1, 1].set_xlabel("wavelength (µm)")
    fig.suptitle("Barnard 68: SPHEREx D4/D5 points per exposure (IMAGE - ZODI, 2 px circle, flagged points dropped)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "spectra.png", dpi=110)


def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if step == "fetch":
        fetch()
        return
    OUT.mkdir(exist_ok=True)
    rows = photometry()
    results = {}
    for s in STARS:
        pts = [p for p in rows if p["star"] == s["name"]]
        results[s["name"]] = {n: tau([p for p in pts if p["band"] == f["band"]], f) for n, f in FEATURES.items()}
        line = f"{s['name']:10s} K {s['k']:5.2f} H-K {s['hk']:.2f}  points {len(pts):3d}"
        for n, r in results[s["name"]].items():
            line += f" | {n}: " + (f"tau {r['tau']:+.3f} ± {r['err']:.3f} (dip {r['n_dip']}, cont {r['n_cont']}, "
                                    f"scatter {r['cont_scatter']})" if r else "not enough points")
        print(line)
    (OUT / "points.json").write_text(json.dumps({"stars": STARS, "results": results, "points": rows}, indent=1))
    plot(rows, results)
    print("wrote", OUT / "spectra.png")


if __name__ == "__main__":
    main()
