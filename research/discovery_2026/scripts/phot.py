"""Forced ePSF photometry of one target (plus its AllWISE neighbours) in every stamp written by spx_s3.py.

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/phot.py NAME

Model per exposure, on the pixels within FIT_HALF of the target that are not flagged bad:
    image = sum_k A_k * PSF(x_k + dx, y_k + dy) + b0 + bx*(x - xt) + by*(y - yt)
PSF is the official SPHEREx ePSF of the nearest zone (photutils ImagePSF convention: array [y, x], oversampling 5,
centre (n-1)/2, cubic spline, times 25), renormalised to unit total over its full footprint. (dx, dy) is one shift
common to all sources with a Gaussian prior of PRIOR_PX, fitted only when the target is detected at S/N >= 20.
Flux density F_nu [Jy] = A [MJy/sr] * Omega_pix [sr] * 1e6, with Omega from the solid-angle pixel map.

A second, model-light estimate: aperture sum within AP_R px minus the fitted background, divided by the PSF fraction
inside the aperture (neighbour light inside the aperture is subtracted using the PSF fit).

Output: EXPERIMENTAL_RESULTS/photometry/NAME.csv and NAME_neighbours.json.
"""
import argparse
import csv
import json
import math
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import least_squares

import spx_s3 as S

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "EXPERIMENTAL_RESULTS" / "photometry"
NEIGH = ROOT / "data" / "neighbours"
TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
FIT_HALF = 6            # fit pixels with |x - xt| <= 6 and |y - yt| <= 6
NEIGH_RADIUS = 90.0     # arcsec searched for AllWISE neighbours
NEIGH_KEEP_PX = 3.5     # a neighbour is modelled if within FIT_HALF + 3.5 px of the target in x and y
MERGE_PX = 0.9          # sources closer than this are one component
W1_LIMIT = 15.5         # AllWISE neighbours fainter than this in W1 and W2 are ignored
PRIOR_PX = 0.5
AP_R = 2.0
SR_PER_ARCSEC2 = (math.pi / 648000) ** 2


def tap(adql, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(TAP, params={"QUERY": adql, "FORMAT": "csv", "LANG": "ADQL"}, timeout=300)
            if r.status_code == 200:
                return Table.read(r.text, format="ascii.csv")
            last = f"HTTP {r.status_code}"
        except requests.RequestException as exc:
            last = exc
        time.sleep(2 ** i)
    raise RuntimeError(f"TAP failed: {last}")


def neighbours(name, ra, dec):
    """AllWISE sources within NEIGH_RADIUS; the one nearest (ra, dec) within 3" is the target (index 0)."""
    NEIGH.mkdir(parents=True, exist_ok=True)
    f = NEIGH / f"{name}.json"
    if f.exists():
        return json.loads(f.read_text())
    t = tap(f"SELECT designation, ra, dec, w1mpro, w2mpro, w1sigmpro, w2sigmpro, cc_flags, ext_flg FROM allwise_p3as_psd "
            f"WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {NEIGH_RADIUS / 3600}))=1")
    rows = []
    for r in t:
        d = math.hypot((float(r["ra"]) - ra) * math.cos(math.radians(dec)), float(r["dec"]) - dec) * 3600
        w1 = float(r["w1mpro"]) if r["w1mpro"] is not np.ma.masked else 99.0
        w2 = float(r["w2mpro"]) if r["w2mpro"] is not np.ma.masked else 99.0
        rows.append({"designation": str(r["designation"]), "ra": float(r["ra"]), "dec": float(r["dec"]), "w1": w1,
                     "w2": w2, "sep_arcsec": d, "cc_flags": str(r["cc_flags"]), "ext_flg": int(r["ext_flg"])})
    rows.sort(key=lambda r: r["sep_arcsec"])
    if rows and rows[0]["sep_arcsec"] < 3.0:
        target = rows.pop(0)
        target["role"] = "target"
    else:
        target = {"designation": None, "ra": ra, "dec": dec, "w1": None, "w2": None, "sep_arcsec": 0.0,
                  "role": "target (input position; no AllWISE source within 3\")"}
    keep = [r for r in rows if min(r["w1"], r["w2"]) <= W1_LIMIT]
    out = {"target": target, "neighbours": keep, "n_allwise_in_radius": len(rows) + 1,
           "w1_limit": W1_LIMIT, "radius_arcsec": NEIGH_RADIUS}
    f.write_text(json.dumps(out, indent=1))
    return out


@lru_cache(maxsize=None)
def epsf_table(det):
    t = fits.getdata(S.CALIB / S.EPSF_FILES[det], "EPSF")
    return np.asarray(t["XCENTER"], float), np.asarray(t["YCENTER"], float), np.asarray(t["EPSF"], float)


@lru_cache(maxsize=4096)
def epsf_spline(det, zone):
    psf = epsf_table(det)[2][zone]
    n = psf.shape[0]
    return RectBivariateSpline(np.arange(psf.shape[0]), np.arange(psf.shape[1]), psf, kx=3, ky=3), n


def zone_of(det, x, y):
    xc, yc, _ = epsf_table(det)
    return int(np.argmin((xc - x) ** 2 + (yc - y) ** 2))


def psf_on(det, zone, X, Y, xs, ys):
    """Unit-total native-pixel PSF of a source at (xs, ys), evaluated at pixel centres X, Y (same shape)."""
    spl, n = epsf_spline(det, zone)
    c, ov = (n - 1) / 2, 5

    def ev(XX, YY):
        u, v = c + ov * (XX - xs), c + ov * (YY - ys)
        inside = (u >= 0) & (u <= n - 1) & (v >= 0) & (v <= n - 1)
        val = np.zeros(XX.shape)
        if inside.any():
            val[inside] = spl.ev(v[inside], u[inside]) * ov * ov
        return val

    g = np.arange(-4, 5)
    GX, GY = np.meshgrid(round(xs) + g, round(ys) + g)
    total = ev(GX.astype(float), GY.astype(float)).sum()
    return ev(X, Y) / total


def fit_one(det, img, var, bad, X, Y, xt, yt, src_xy, zone, shift=True):
    ok = ~bad & np.isfinite(img) & np.isfinite(var) & (var > 0)
    o, w = img[ok], 1 / np.sqrt(var[ok])
    Xo, Yo = X[ok], Y[ok]
    nsrc = len(src_xy)

    def design(dx, dy, XX, YY):
        cols = [psf_on(det, zone, XX, YY, sx + dx, sy + dy) for sx, sy in src_xy]
        cols += [np.ones(XX.shape), XX - xt, YY - yt]
        return np.stack(cols, -1)

    def solve(dx, dy):
        A = design(dx, dy, Xo, Yo) * w[:, None]
        coef, *_ = np.linalg.lstsq(A, o * w, rcond=None)
        return A, coef, o * w - A @ coef

    if ok.sum() < nsrc + 3 + 5:
        return None
    A, coef, res = solve(0.0, 0.0)
    dxy = (0.0, 0.0)
    cov = np.linalg.pinv(A.T @ A)
    snr0 = coef[0] / math.sqrt(cov[0, 0]) if cov[0, 0] > 0 else 0
    if shift and snr0 >= 20:
        r = least_squares(lambda p: np.r_[solve(*p)[2], np.asarray(p) / PRIOR_PX], [0.0, 0.0],
                          bounds=([-1.5, -1.5], [1.5, 1.5]))
        dxy = tuple(float(v) for v in r.x)
        A, coef, res = solve(*dxy)
        cov = np.linalg.pinv(A.T @ A)
    dof = max(ok.sum() - nsrc - 3 - (2 if dxy != (0.0, 0.0) else 0), 1)
    chi2 = float(np.sum(res ** 2) / dof)
    # aperture estimate around the target, neighbours and background removed with the fit
    full = design(*dxy, X, Y)
    model_other = full[..., 1:] @ coef[1:]
    p_t = full[..., 0]
    ap = (np.hypot(X - xt - dxy[0], Y - yt - dxy[1]) <= AP_R)
    ap_ok = ap & ok
    frac = p_t[ap_ok].sum()
    ap_flux = float((img[ap_ok] - model_other[ap_ok]).sum() / frac) if frac > 0.3 else np.nan
    ap_var = float(var[ap_ok].sum() / frac ** 2) if frac > 0.3 else np.nan
    core = np.hypot(X - xt - dxy[0], Y - yt - dxy[1]) <= 1.5
    return {"amp": float(coef[0]), "amp_err": float(math.sqrt(cov[0, 0])), "chi2r": chi2, "dx": dxy[0], "dy": dxy[1],
            "n_fit": int(ok.sum()), "n_core_good": int((core & ok).sum()), "n_core": int(core.sum()),
            "ap_amp": ap_flux, "ap_err": math.sqrt(ap_var) if np.isfinite(ap_var) else np.nan, "ap_frac": float(frac),
            "bg": float(coef[nsrc]), "neigh_amp": [float(c) for c in coef[1:nsrc]]}


def run(name, shift=True):
    d = S.load(S.STAMPS / f"{name}.npz")
    meta = json.loads((S.STAMPS / f"{name}.json").read_text())
    nb = neighbours(name, meta["ra"], meta["dec"])
    tgt = nb["target"]
    srcs = [tgt] + nb["neighbours"]
    n = len(d["mjd_avg"])
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(n):
        det = int(d["det"][i])
        w = WCS(fits.Header.fromstring(str(d["wcs"][i])))
        x0, y0 = int(d["x0"][i]), int(d["y0"][i])
        img, var, flg = d["image"][i], d["variance"][i], d["flags"][i]
        ny, nx = img.shape
        Y, X = np.mgrid[y0:y0 + ny, x0:x0 + nx].astype(float)
        xt, yt = (float(v) for v in w.all_world2pix(tgt["ra"], tgt["dec"], 0))
        bad = (flg < 0) | ((flg & int(d["bad_mask"][i])) != 0)
        region = (np.abs(X - xt) <= FIT_HALF) & (np.abs(Y - yt) <= FIT_HALF)
        src_xy = [(xt, yt)]
        kept = [tgt.get("designation")]
        for s in nb["neighbours"]:
            sx, sy = (float(v) for v in w.all_world2pix(s["ra"], s["dec"], 0))
            if abs(sx - xt) > FIT_HALF + NEIGH_KEEP_PX or abs(sy - yt) > FIT_HALF + NEIGH_KEEP_PX:
                continue
            if any(math.hypot(sx - px, sy - py) < MERGE_PX for px, py in src_xy):
                continue
            src_xy.append((sx, sy))
            kept.append(s["designation"])
        zone = zone_of(det, xt, yt)
        iy, ix = int(round(yt)) - y0, int(round(xt)) - x0
        omega = float(d["sapm"][i][iy, ix]) * SR_PER_ARCSEC2 * 1e6   # MJy/sr -> Jy
        core_flags = int(np.bitwise_or.reduce(flg[max(iy - 1, 0):iy + 2, max(ix - 1, 0):ix + 2].ravel()))
        sub = region
        r = fit_one(det, img[sub], var[sub], bad[sub], X[sub], Y[sub], xt, yt, src_xy, zone, shift)
        row = {"i": i, "key": str(d["key"][i]), "collection": str(d["collection"][i]), "det": det,
               "mjd": float(d["mjd_avg"][i]), "wl_um": float(d["cwave"][i][iy, ix]),
               "bw_um": float(d["cband"][i][iy, ix]), "x": round(xt, 3), "y": round(yt, 3), "zone": zone,
               "n_src": len(src_xy), "core_flags": core_flags, "omega_jy_per_mjysr": omega}
        if r is None:
            row.update({"status": "too few good pixels"})
        else:
            row.update({"status": "ok", "flux_jy": r["amp"] * omega, "err_jy": r["amp_err"] * omega,
                        "ap_flux_jy": r["ap_amp"] * omega, "ap_err_jy": r["ap_err"] * omega, "chi2r": r["chi2r"],
                        "dx": r["dx"], "dy": r["dy"], "n_fit": r["n_fit"], "n_core_good": r["n_core_good"],
                        "ap_frac": r["ap_frac"], "bg_mjysr": r["bg"],
                        "neigh_flux_jy": ";".join(f"{a * omega:.4g}" for a in r["neigh_amp"])})
        rows.append(row)
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(OUT / f"{name}.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, keys)
        wr.writeheader()
        wr.writerows(rows)
    return rows, nb


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--no-shift", action="store_true")
    a = p.parse_args()
    rows, nb = run(a.name, not a.no_shift)
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"{a.name}: {len(ok)}/{len(rows)} fitted; target {nb['target'].get('designation')} "
          f"W1 {nb['target'].get('w1')} W2 {nb['target'].get('w2')}; {len(nb['neighbours'])} neighbours W<={W1_LIMIT}")


if __name__ == "__main__":
    main()
