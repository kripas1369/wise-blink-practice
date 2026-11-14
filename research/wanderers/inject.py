"""Injection and recovery: fake point sources with known motion, added to the real detector-epoch co-adds of a field.

    PYTHONPATH=.:research:research/wanderers .venv/bin/python research/wanderers/inject.py NAME [--per-cell 12]

For a grid of brightness (S/N per detector-epoch: SNR_LEVELS) and motion (PM_LEVELS, arcsec/yr, random direction),
fake sources are added to copies of the real co-adds (results/NAME/coadds.npz) with each detector-epoch's fitted PSF
width, at positions that land on the true track after that detector-epoch's registration transform. Then the same
steps as astrometry.py run: detection on the all-epoch co-add, PSF fits per detector-epoch, registration, motion fit,
and the error scale and threshold of classify.py (summary.json). Recovered = detected within 2 px of the track's
mean position; "moving" = motion significance >= threshold with >= 3 visits.

Output: results/NAME/injection.json (per-source results and completeness / false-positive tables).
"""
import argparse
import json
import math

import numpy as np

import common as C
from astrometry import (DETECT_SNR, fit_sources, motion_fit, peaks, pixel_gauss, snr_map)
from backend.app.align import target_grid

SNR_LEVELS = (3, 5, 10, 20, 50)
PM_LEVELS = (0.0, 0.3, 1.0, 3.0, 8.0)
SEED = 20261114
BATCH = 15


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--per-cell", type=int, default=12)
    a = ap.parse_args()
    d = C.RESULTS / a.name
    meta = json.loads((d / "meta.json").read_text())
    des = json.loads((d / "detector_epochs.json").read_text())
    summ = json.loads((d / "summary.json").read_text())
    sources = json.loads((d / "sources.json").read_text())
    k_err = summ["calibration"]["applied_scale"]
    thr = summ["calibration"]["threshold_sigma"]
    Z = np.load(d / "coadds.npz")
    images, sigmas, bad = Z["images"].astype(float), Z["sigmas"].astype(float), Z["bad"]
    ra0, dec0 = meta["ra"], meta["dec"]
    grid, size = target_grid(ra0, dec0, meta["fov_arcmin"])
    years = np.array([de["year"] for de in des])
    t_mid = float(np.mean(years))
    ok_de = [i for i, de in enumerate(des) if de["registration"] is not None]
    rng = np.random.default_rng(SEED)
    existing = np.array([(s["x_px"], s["y_px"]) for s in sources]) if sources else np.zeros((0, 2))

    def tan_of_pix(x, y):
        wra, wdec = grid.pixel_to_world_values(np.atleast_1d(x), np.atleast_1d(y))
        return C.tangent(wra, wdec, ra0, dec0)

    def pix_of_tan(x, y):
        wra, wdec = C.untangent(x, y, ra0, dec0)
        return grid.world_to_pixel_values(np.atleast_1d(wra), np.atleast_1d(wdec))

    cells = [(s, p) for s in SNR_LEVELS for p in PM_LEVELS for _ in range(a.per_cell)]
    rng.shuffle(cells)
    results = []
    for b0 in range(0, len(cells), BATCH):
        batch = cells[b0:b0 + BATCH]
        imgs = images.copy()
        truth = []
        placed = []
        for snr, pm in batch:
            for _ in range(200):
                xp, yp = rng.uniform(8, size - 9, 2)
                far_real = not len(existing) or np.min(np.hypot(existing[:, 0] - xp, existing[:, 1] - yp)) > 5
                far_inj = all(math.hypot(xp - q[0], yp - q[1]) > 8 for q in placed)
                if far_real and far_inj:
                    break
            placed.append((xp, yp))
            ang = rng.uniform(0, 2 * math.pi)
            vx, vy = pm * math.sin(ang), pm * math.cos(ang)
            tx0, ty0 = (float(v[0]) for v in tan_of_pix(xp, yp))
            truth.append({"snr": snr, "pm": pm, "vx": vx, "vy": vy, "tx0": tx0, "ty0": ty0, "x_px": xp, "y_px": yp})
            for i in ok_de:
                de = des[i]
                T = np.array(de["registration"]["T"])
                tx = tx0 + vx * (years[i] - t_mid)
                ty = ty0 + vy * (years[i] - t_mid)
                raw = np.linalg.solve(T[:, :2], np.array([tx, ty]) - T[:, 2])   # registered -> raw tangent
                px, py = (float(v[0]) for v in pix_of_tan(raw[0], raw[1]))
                s_psf = de["psf_sigma_px"]
                sig_loc = np.nanmedian(sigmas[i][max(0, int(py) - 5):int(py) + 6, max(0, int(px) - 5):int(px) + 6])
                if not np.isfinite(sig_loc):
                    continue
                amp = snr * sig_loc * math.sqrt(4 * math.pi) * s_psf     # optimal-PSF S/N = snr
                imgs[i] += amp * pixel_gauss(size, size, px, py, s_psf)
        # detection on the all-epoch co-add
        W = np.zeros((size, size))
        S = np.zeros((size, size))
        for i in ok_de:
            w = np.where(np.isfinite(imgs[i]) & np.isfinite(sigmas[i]) & (sigmas[i] > 0) & ~bad[i], 1 / sigmas[i] ** 2, 0)
            W += w
            S += w * np.nan_to_num(imgs[i])
        deep = np.where(W > 0, S / np.where(W > 0, W, 1), np.nan)
        dsig = np.where(W > 0, 1 / np.sqrt(np.where(W > 0, W, 1)), np.nan)
        det = peaks(snr_map(deep, dsig), DETECT_SNR)
        dxy = np.array([(x, y) for x, y, _ in det]) if det else np.zeros((0, 2))
        for tr in truth:
            res = {**tr, "detected": False, "moving": False}
            if len(dxy):
                dd = np.hypot(dxy[:, 0] - tr["x_px"], dxy[:, 1] - tr["y_px"])
                j = int(np.argmin(dd))
                if dd[j] < 2.0:
                    res["detected"] = True
                    res["det_snr"] = det[j][2]
                    pts = []
                    for i in ok_de:
                        de = des[i]
                        f = fit_sources(imgs[i], sigmas[i], bad[i], [tuple(dxy[j])], de["psf_sigma_px"])
                        if f is None or f["eamp"] <= 0 or f["amp"] / f["eamp"] < 3:
                            continue
                        tx, ty = (float(v[0]) for v in tan_of_pix(f["x"], f["y"]))
                        T = np.array(de["registration"]["T"])
                        px, py = T[:, :2] @ np.array([tx, ty]) + T[:, 2]
                        fl = de["registration"]["floor"]
                        pts.append((years[i], px, py, math.hypot(f["ex"] * C.PIXEL_ARCSEC, fl),
                                    math.hypot(f["ey"] * C.PIXEL_ARCSEC, fl), de["visit"]))
                    nv = len({p[5] for p in pts})
                    res["n_visits"] = nv
                    if nv >= 2 and len(pts) >= 3:
                        arr = np.array([p[:5] for p in pts])
                        fit = motion_fit(*arr.T)
                        epx, epy = fit["epmx"] * k_err, fit["epmy"] * k_err
                        sig = math.hypot(fit["pmx"] / epx, fit["pmy"] / epy)
                        res.update({"pm_sig": sig, "pmx": fit["pmx"], "pmy": fit["pmy"], "epmx": epx, "epmy": epy,
                                    "pm_err_z": math.hypot((fit["pmx"] - tr["vx"]) / epx, (fit["pmy"] - tr["vy"]) / epy),
                                    "moving": bool(sig >= thr and nv >= 3)})
            results.append(res)
        C.log(f"inject_{a.name}", f"batch {b0 // BATCH + 1}/{math.ceil(len(cells) / BATCH)} done")

    table = []
    for snr in SNR_LEVELS:
        for pm in PM_LEVELS:
            r = [x for x in results if x["snr"] == snr and x["pm"] == pm]
            det = [x for x in r if x["detected"]]
            fitted = [x for x in det if "pm_sig" in x]
            table.append({"snr_per_detector_epoch": snr, "pm_arcsec_yr": pm, "n": len(r),
                          "detected": len(det), "moving": sum(x["moving"] for x in r),
                          "frac_detected": round(len(det) / len(r), 3) if r else None,
                          "frac_moving": round(sum(x["moving"] for x in r) / len(r), 3) if r else None,
                          "median_pm_err_mas": round(float(np.median([math.hypot(x["epmx"], x["epmy"]) / math.sqrt(2)
                                                                      for x in fitted])) * 1000, 1) if fitted else None,
                          "median_err_z": round(float(np.median([x["pm_err_z"] for x in fitted])), 2) if fitted else None})
    stationary = [x for x in results if x["pm"] == 0 and "pm_sig" in x]
    out = {"made_at": C.now(), "seed": SEED, "threshold_sigma": thr, "err_scale": k_err,
           "n_injected": len(results), "table": table,
           "false_positive_rate_stationary": round(sum(x["moving"] for x in stationary) / len(stationary), 4)
           if stationary else None, "n_stationary_fitted": len(stationary), "results": results}
    (d / "injection.json").write_text(json.dumps(out, indent=1, default=float))
    C.log(f"inject_{a.name}", f"done: {len(results)} injected; FP rate (stationary) {out['false_positive_rate_stationary']}")
    for row in table:
        C.log(f"inject_{a.name}", str(row))


if __name__ == "__main__":
    main()
