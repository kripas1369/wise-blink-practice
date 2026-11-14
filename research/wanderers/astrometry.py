"""Measure the position of every source in a SPHEREx field at every visit, and fit stationary and moving models.

    PYTHONPATH=.:research:research/wanderers .venv/bin/python research/wanderers/astrometry.py NAME RA DEC
        [--fov 20] [--max-per 0]

Steps (details in REPORT.md):
1. All DR1 + QR3 images containing the field centre; visits = backend.app.archive.group_epochs (a new visit after a
   30-day gap or 60 days of span). Six detectors are kept apart throughout: each (visit, detector) is one
   "detector-epoch". Inside one detector the linear variable filter gives a range of wavelengths; the co-add of a
   detector-epoch spans that detector's band, and the same band is compared between visits.
2. Each cutout: IMAGE - ZODI, sigma = sqrt(VARIANCE), official bad-pixel FLAGS mask, MJD-AVG (backend.app.clean),
   resampled onto one north-up grid of 6.15″ pixels (backend.app.align) and co-added per detector-epoch with
   1/sigma² weights (backend.app.coadd). A 15-pixel running median removes residual background.
3. Detection on the inverse-variance co-add of all detector-epochs (matched filter, S/N > DETECT_SNR); per-visit
   co-adds are searched as well for sources seen in one visit only.
4. Positions: pixel-integrated Gaussian PSF (width fitted per detector-epoch on isolated bright stars) plus a
   constant, neighbours fitted together; errors from the fit covariance.
5. Registration: per detector-epoch, an affine map onto Gaia DR3 positions moved to that date, using stars with
   Gaia proper motions below 100 mas/yr; a per-detector-epoch error floor makes the reference residuals' χ²/dof = 1.
6. Per source: weighted fits of a stationary and a linear-motion model to all detector-epoch positions;
   CatWISE2020 (2010-2018, epoch 2015.4) adds a ~10-year baseline.
Output: results/NAME/ (detector_epochs.json, sources.json, transients.json, registration.json, coadds.npz, meta.json)
"""
import argparse
import concurrent.futures as cf
import json
import math
import warnings

import numpy as np
from astropy.io import fits
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.special import erf

import common as C
from backend.app import archive
from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd

warnings.filterwarnings("ignore", category=RuntimeWarning)

DETECT_SNR = 5.0
TRANSIENT_SNR = 6.0
BOX = 4                     # fit box half-width (9x9 pixels)
NEIGHBOUR_PX = 5.0
BG_SIZE = 15
MIN_COVERED_PCT = 50
REF_MAX_PM = 100.0          # mas/yr; faster Gaia stars are not used to register visits
REF_MAX_G = 19.0
MATCH_PX = 1.0


def pixel_gauss(ny, nx, x, y, s, x_off=0, y_off=0):
    k = 1 / (math.sqrt(2) * s)
    xs = np.arange(nx) + x_off
    ys = np.arange(ny) + y_off
    gx = 0.5 * (erf((xs + 0.5 - x) * k) - erf((xs - 0.5 - x) * k))
    gy = 0.5 * (erf((ys + 0.5 - y) * k) - erf((ys - 0.5 - y) * k))
    return np.outer(gy, gx)


def spread(ims, n):
    ims = sorted(ims, key=lambda im: im.mjd)
    if not n or len(ims) <= n:
        return ims
    return [ims[int(i)] for i in np.linspace(0, len(ims) - 1, n).round()]


def background(img):
    filled = np.where(np.isfinite(img), img, np.nanmedian(img))
    return ndimage.median_filter(filled, size=BG_SIZE, mode="nearest")


def build_detector_epoch(args):
    """Co-add one (visit, detector); runs in a worker process."""
    paths, meta, ra, dec, fov = args
    grid, size = target_grid(ra, dec, fov)
    aligned, used = [], []
    for p, m in zip(paths, meta):
        try:
            cl = clean_cutout(p, ra, dec)
            a = align(cl, grid, size)
        except Exception:
            continue
        if a["pct_covered"] < MIN_COVERED_PCT:
            continue
        aligned.append(a)
        used.append({**m, "mjd": cl["mjd"], "wl_um": cl["wl_um"], "bw_um": cl["bw_um"],
                     "pct_flagged": a["pct_flagged"]})
    if not aligned:
        return None
    c = coadd(aligned)
    img = c["image"] - background(c["image"])
    flagged_frac = np.mean([a["bad"].astype(float) for a in aligned], axis=0)
    return {"image": img.astype(np.float32), "sigma": c["sigma"].astype(np.float32), "bad": c["bad"],
            "flagged_frac": flagged_frac.astype(np.float32), "n_used": c["n_used"].astype(np.int16), "exposures": used}


def snr_map(img, sig, s=0.9):
    r = 3
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = np.exp(-(xx ** 2 + yy ** 2) / (2 * s ** 2))
    k /= k.sum()
    w = np.where(np.isfinite(img) & np.isfinite(sig) & (sig > 0), 1 / sig ** 2, 0.0)
    num = ndimage.convolve(np.nan_to_num(img) * w, k, mode="constant")
    den = ndimage.convolve(w, k ** 2, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.sqrt(den), 0.0)


def peaks(snr, thresh, edge=3):
    mx = ndimage.maximum_filter(snr, size=3)
    yy, xx = np.nonzero((snr == mx) & (snr > thresh))
    ny, nx = snr.shape
    ok = (xx >= edge) & (xx < nx - edge) & (yy >= edge) & (yy < ny - edge)
    return [(float(x), float(y), float(snr[y, x])) for x, y in zip(xx[ok], yy[ok])]


def fit_sources(img, sig, bad, starts, s, free_px=3.0):
    """Fit PSF components at `starts` [(x, y), ...] (first = the target) plus a constant inside a box around
    the target. Returns x, y, flux amplitude, their 1σ errors and the reduced χ², or None."""
    x0, y0 = starts[0]
    ny, nx = img.shape
    ya, yb = max(0, int(round(y0)) - BOX), min(ny, int(round(y0)) + BOX + 1)
    xa, xb = max(0, int(round(x0)) - BOX), min(nx, int(round(x0)) + BOX + 1)
    sub, ssub, bsub = img[ya:yb, xa:xb], sig[ya:yb, xa:xb], bad[ya:yb, xa:xb]
    ok = np.isfinite(sub) & np.isfinite(ssub) & (ssub > 0) & ~bsub
    k = len(starts)
    if ok.sum() < 3 * k + 6:
        return None
    o, w = sub[ok], 1 / ssub[ok]
    shp = sub.shape

    def model(p):
        m = np.full(shp, p[-1])
        for j in range(k):
            m = m + p[3 * j + 2] * pixel_gauss(shp[0], shp[1], p[3 * j], p[3 * j + 1], s, xa, ya)
        return m

    def resid(p):
        return (o - model(p)[ok]) * w

    p0, lo, hi = [], [], []
    for j, (x, y) in enumerate(starts):
        fp = free_px if j == 0 else 1.5
        amp = max(float(np.nanmax(np.where(ok, sub, -np.inf))) * 2 * math.pi * s ** 2, 1e-6) if j == 0 else \
            max(float(img[int(np.clip(round(y), 0, ny - 1)), int(np.clip(round(x), 0, nx - 1))]) * 2 * math.pi * s ** 2, 1e-6)
        if not np.isfinite(amp):
            amp = 1e-3
        p0 += [x, y, amp]
        lo += [x - fp, y - fp, -np.inf]
        hi += [x + fp, y + fp, np.inf]
    p0.append(0.0)
    lo.append(-np.inf)
    hi.append(np.inf)
    try:
        res = least_squares(resid, p0, bounds=(lo, hi), x_scale="jac", max_nfev=200)
    except Exception:
        return None
    dof = max(ok.sum() - len(p0), 1)
    chi2 = float(np.sum(res.fun ** 2) / dof)
    try:
        cov = np.linalg.inv(res.jac.T @ res.jac) * max(1.0, chi2)
    except np.linalg.LinAlgError:
        return None
    e = np.sqrt(np.clip(np.diag(cov), 0, None))
    x, y, a = res.x[:3]
    ex, ey, ea = e[:3]
    if not (xa - 0.5 <= x <= xb - 0.5 and ya - 0.5 <= y <= yb - 0.5) or not np.all(np.isfinite([ex, ey, ea])):
        return None
    yy, xx = np.mgrid[ya:yb, xa:xb]
    core = np.hypot(xx - x, yy - y) < 1.5
    return {"x": float(x), "y": float(y), "ex": float(ex), "ey": float(ey), "amp": float(a), "eamp": float(ea),
            "chi2": chi2, "core_bad": int((core & ~ok).sum()), "core_n": int(core.sum())}


def psf_width(img, sig, bad, srcs):
    """Median Gaussian width of isolated bright sources (free width)."""
    xy = np.array([(s["x"], s["y"]) for s in srcs])
    widths = []
    for s in sorted(srcs, key=lambda s: -s["snr"])[:60]:
        if s["snr"] < 30:
            break
        d = np.hypot(xy[:, 0] - s["x"], xy[:, 1] - s["y"])
        if np.sum(d < 6) > 1:
            continue
        x0, y0 = s["x"], s["y"]
        ny, nx = img.shape
        ya, yb = max(0, int(y0) - BOX), min(ny, int(y0) + BOX + 1)
        xa, xb = max(0, int(x0) - BOX), min(nx, int(x0) + BOX + 1)
        sub, ssub = img[ya:yb, xa:xb], sig[ya:yb, xa:xb]
        ok = np.isfinite(sub) & np.isfinite(ssub) & (ssub > 0) & ~bad[ya:yb, xa:xb]
        if ok.sum() < 30:
            continue

        def r(p):
            m = p[4] + p[2] * pixel_gauss(sub.shape[0], sub.shape[1], p[0], p[1], p[3], xa, ya)
            return ((sub - m)[ok]) / ssub[ok]
        try:
            res = least_squares(r, [x0, y0, float(np.nanmax(sub)) * 6, 0.9, 0.0],
                                bounds=([x0 - 2, y0 - 2, 0, 0.4, -np.inf], [x0 + 2, y0 + 2, np.inf, 3.0, np.inf]))
            if res.success and 0.45 < res.x[3] < 2.9:
                widths.append(res.x[3])
        except Exception:
            continue
    return (float(np.median(widths)), len(widths)) if len(widths) >= 3 else (None, len(widths))


def affine_fit(src, dst, w):
    """dst ≈ A @ src + t with weights; returns 2x3 matrix."""
    n = len(src)
    X = np.column_stack([src, np.ones(n)])
    W = np.sqrt(w)[:, None]
    mx, *_ = np.linalg.lstsq(X * W, dst[:, 0] * W[:, 0], rcond=None)
    my, *_ = np.linalg.lstsq(X * W, dst[:, 1] * W[:, 0], rcond=None)
    return np.vstack([mx, my])


def register(meas, gaia_xy, err, min_affine=12):
    """meas, gaia_xy: (n, 2) arcsec; err: (n,) per-axis 1σ arcsec. Returns transform, floor, residuals, mask."""
    use = np.ones(len(meas), bool)
    floor = 0.0
    T = np.array([[1, 0, 0], [0, 1, 0]], float)
    for _ in range(4):
        tot = err ** 2 + floor ** 2
        if use.sum() >= min_affine:
            T = affine_fit(meas[use], gaia_xy[use], 1 / tot[use])
        elif use.sum() >= 3:
            sh = np.average(gaia_xy[use] - meas[use], axis=0, weights=1 / tot[use])
            T = np.array([[1, 0, sh[0]], [0, 1, sh[1]]])
        else:
            return None
        pred = meas @ T[:, :2].T + T[:, 2]
        r = gaia_xy - pred
        dof = max(2 * use.sum() - (6 if use.sum() >= min_affine else 2), 1)

        def chi2(f):
            return np.sum(r[use] ** 2 / (err[use, None] ** 2 + f ** 2)) / dof
        lo, hi = 0.0, 30.0
        if chi2(0.0) > 1:
            for _ in range(50):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if chi2(mid) > 1 else (lo, mid)
            floor = hi
        else:
            floor = 0.0
        z = np.hypot(*(r / np.sqrt(err[:, None] ** 2 + floor ** 2)).T) / math.sqrt(2)
        new = z < 3.5
        if np.array_equal(new, use):
            break
        use = new
    return {"T": T.tolist(), "floor": float(floor), "n_ref": int(use.sum()), "n_cand": int(len(meas)),
            "rms": float(np.sqrt(np.mean(r[use] ** 2))), "affine": bool(use.sum() >= min_affine), "used": use, "resid": r}


def motion_fit(t, x, y, ex, ey):
    """Weighted straight-line fits in x and y. Returns stationary and moving solutions."""
    out = {}
    wx, wy = 1 / ex ** 2, 1 / ey ** 2
    t0 = float(np.average(t, weights=wx + wy))
    dt = t - t0
    for name, v, w in (("x", x, wx), ("y", y, wy)):
        m0 = np.average(v, weights=w)
        chi_s = float(np.sum(w * (v - m0) ** 2))
        A = np.column_stack([np.ones_like(dt), dt])
        cov = np.linalg.inv(A.T @ (A * w[:, None]))
        p = cov @ (A.T @ (w * v))
        chi_m = float(np.sum(w * (v - A @ p) ** 2))
        out[name] = {"p": p, "cov": cov, "chi_s": chi_s, "chi_m": chi_m}
    n = len(t)
    chi_s = out["x"]["chi_s"] + out["y"]["chi_s"]
    chi_m = out["x"]["chi_m"] + out["y"]["chi_m"]
    dof_m = max(2 * n - 4, 1)
    red = chi_m / dof_m
    scale = math.sqrt(max(1.0, red))
    pmx, pmy = out["x"]["p"][1], out["y"]["p"][1]
    epx, epy = math.sqrt(out["x"]["cov"][1, 1]) * scale, math.sqrt(out["y"]["cov"][1, 1]) * scale
    sig = math.sqrt((pmx / epx) ** 2 + (pmy / epy) ** 2)
    return {"t0": t0, "x0": float(out["x"]["p"][0]), "y0": float(out["y"]["p"][0]),
            "ex0": math.sqrt(out["x"]["cov"][0, 0]) * scale, "ey0": math.sqrt(out["y"]["cov"][0, 0]) * scale,
            "pmx": float(pmx), "pmy": float(pmy), "epmx": epx, "epmy": epy, "pm_sig": sig,
            "chi2_stat": chi_s, "chi2_move": chi_m, "dof_stat": max(2 * n - 2, 1), "dof_move": dof_m,
            "delta_chi2": chi_s - chi_m, "scale": scale}


def run(name, ra, dec, fov, max_per):
    out = C.RESULTS / name
    out.mkdir(parents=True, exist_ok=True)
    tag = f"astrometry_{name}"
    grid, size = target_grid(ra, dec, fov)
    size_deg = cutout_size_deg(fov)
    ims = C.images_at(ra, dec, name)
    visits = archive.group_epochs(ims)
    C.log(tag, f"{name}: {len(ims)} DR1+QR3 images, {len(visits)} visits, fov {fov}′, grid {size}px")
    groups = []
    for v in visits:
        for d in range(1, 7):
            sel = spread([im for im in v["images"] if im.detector == d], max_per)
            if sel:
                groups.append((v["id"], d, sel))
    flat = [im for _, _, sel in groups for im in sel]
    files = {im.did: archive.cutout_file(im, ra, dec, size_deg) for im in flat}
    missing = [im for im in flat if not files[im.did].exists()]
    C.log(tag, f"{len(flat)} cutouts needed, {len(missing)} to download")
    for i in range(0, len(missing), 100):
        chunk = missing[i:i + 100]
        try:
            C.retry(archive.attach_paths, chunk, what="paths")
        except Exception as exc:
            C.log(tag, f"paths failed for {len(chunk)} images: {exc}")
            continue
        got = archive.download_cutouts(chunk, ra, dec, size_deg)
        nbad = sum(1 for v in got.values() if not hasattr(v, "exists"))
        C.log(tag, f"downloaded {i + len(chunk)}/{len(missing)} ({nbad} failed in this chunk)")

    # 1-2: detector-epoch co-adds (parallel)
    jobs = []
    for vid, d, sel in groups:
        ps = [files[im.did] for im in sel if files[im.did].exists()]
        meta = [{"obs_id": im.obs_id, "did": im.did, "collection": im.collection, "release": im.release_date,
                 "file": files[im.did].name} for im in sel if files[im.did].exists()]
        if ps:
            jobs.append(((vid, d), (ps, meta, ra, dec, fov)))
    des = []
    with cf.ProcessPoolExecutor(6) as pool:
        for (key, _), res in zip(jobs, pool.map(build_detector_epoch, [j[1] for j in jobs])):
            if res is not None:
                res["visit"], res["det"] = key
                res["mjd"] = float(np.mean([e["mjd"] for e in res["exposures"]]))
                wls = [e["wl_um"] for e in res["exposures"] if e["wl_um"] is not None]
                res["wl_min"], res["wl_max"] = (float(min(wls)), float(max(wls))) if wls else (None, None)
                des.append(res)
    des.sort(key=lambda r: (r["visit"], r["det"]))
    C.log(tag, f"{len(des)} detector-epochs co-added from {sum(len(r['exposures']) for r in des)} exposures")
    if not des:
        raise SystemExit("no usable data")

    # first-file header facts (processing versions) per detector
    versions = {}
    for r in des:
        if r["det"] in versions:
            continue
        p = files[next(im.did for im in flat if im.did == r["exposures"][0]["did"])]
        with fits.open(p) as h:
            hd = h["IMAGE"].header
            versions[r["det"]] = {k: str(hd[k]) for k in hd if any(s in k for s in ("VER", "PROC", "RELEASE", "PIPE"))}

    # 3: master detection on the all-epoch co-add
    W = np.zeros((size, size))
    S = np.zeros((size, size))
    for r in des:
        w = np.where(np.isfinite(r["image"]) & np.isfinite(r["sigma"]) & (r["sigma"] > 0) & ~r["bad"],
                     1 / np.asarray(r["sigma"], float) ** 2, 0)
        W += w
        S += w * np.nan_to_num(r["image"])
    deep = np.where(W > 0, S / np.where(W > 0, W, 1), np.nan)
    deep_sig = np.where(W > 0, 1 / np.sqrt(np.where(W > 0, W, 1)), np.nan)
    # detection images: all detectors, each detector alone, and D4-D6 together (very red sources such as cold brown
    # dwarfs are invisible at short wavelengths and would be diluted in the all-detector co-add)
    def stack(sel):
        Ws = np.zeros((size, size))
        Ss = np.zeros((size, size))
        for r in sel:
            w = np.where(np.isfinite(r["image"]) & np.isfinite(r["sigma"]) & (r["sigma"] > 0) & ~r["bad"],
                         1 / np.asarray(r["sigma"], float) ** 2, 0)
            Ws += w
            Ss += w * np.nan_to_num(r["image"])
        return (np.where(Ws > 0, Ss / np.where(Ws > 0, Ws, 1), np.nan),
                np.where(Ws > 0, 1 / np.sqrt(np.where(Ws > 0, Ws, 1)), np.nan))
    det_images = {"all": des, **{f"D{d}": [r for r in des if r["det"] == d] for d in range(1, 7)},
                  "D456": [r for r in des if r["det"] >= 4]}
    found = []
    for lab, sel in det_images.items():
        if not sel:
            continue
        im_, sg_ = (deep, deep_sig) if lab == "all" else stack(sel)
        found += [(x, y, s, lab) for x, y, s in peaks(snr_map(im_, sg_), DETECT_SNR)]
    found.sort(key=lambda f: -f[2])
    master = []
    for x, y, s, lab in found:
        hit = next((m for m in master if math.hypot(m["x"] - x, m["y"] - y) < 1.5), None)
        if hit:
            hit["found_in"].append(lab)
            continue
        master.append({"id": len(master), "x": x, "y": y, "snr": s, "found_in": [lab]})
    C.log(tag, f"{len(master)} sources at S/N > {DETECT_SNR} in any detection image "
               f"({sum(m['found_in'] == ['all'] or 'all' in m['found_in'] for m in master)} in the all-detector co-add)")

    # per-visit co-adds for one-visit sources
    transients = []
    mxy = np.array([(m["x"], m["y"]) for m in master]) if master else np.zeros((0, 2))
    for vid in sorted({r["visit"] for r in des}):
        Wv = np.zeros((size, size))
        Sv = np.zeros((size, size))
        for r in des:
            if r["visit"] != vid:
                continue
            w = np.where(np.isfinite(r["image"]) & np.isfinite(r["sigma"]) & (r["sigma"] > 0) & ~r["bad"],
                         1 / np.asarray(r["sigma"], float) ** 2, 0)
            Wv += w
            Sv += w * np.nan_to_num(r["image"])
        img_v = np.where(Wv > 0, Sv / np.where(Wv > 0, Wv, 1), np.nan)
        sig_v = np.where(Wv > 0, 1 / np.sqrt(np.where(Wv > 0, Wv, 1)), np.nan)
        for x, y, s in peaks(snr_map(img_v, sig_v), TRANSIENT_SNR):
            if len(mxy) and np.min(np.hypot(mxy[:, 0] - x, mxy[:, 1] - y)) < 2.5:
                continue
            transients.append({"visit": vid, "x": x, "y": y, "snr": s})
    C.log(tag, f"{len(transients)} one-visit detections (S/N > {TRANSIENT_SNR}, > 2.5 px from any deep source)")

    # 4: positions per detector-epoch
    width = {}
    for r in des:
        s, n = psf_width(r["image"], r["sigma"], r["bad"], master)
        width[(r["visit"], r["det"])] = s if s else {1: 0.75, 2: 0.75, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1}[r["det"]]
        r["psf_sigma"], r["psf_n"] = width[(r["visit"], r["det"])], n
    meas = {}  # (source id, de index) -> fit
    for k, r in enumerate(des):
        img = np.asarray(r["image"], float)
        sig = np.asarray(r["sigma"], float)
        for m in master:
            d = np.hypot(mxy[:, 0] - m["x"], mxy[:, 1] - m["y"])
            nb = [tuple(mxy[j]) for j in np.argsort(d)[1:5] if d[j] < NEIGHBOUR_PX]
            f = fit_sources(img, sig, r["bad"], [(m["x"], m["y"])] + nb, r["psf_sigma"])
            if f is not None and f["amp"] > 0:
                f["flag_frac"] = float(r["flagged_frac"][int(round(f["y"])), int(round(f["x"]))]) \
                    if 0 <= round(f["y"]) < size and 0 <= round(f["x"]) < size else 1.0
                f["n_neighbours"] = len(nb)
                meas[(m["id"], k)] = f
        C.log(tag, f"detector-epoch v{r['visit']} D{r['det']}: {sum(1 for (i, kk) in meas if kk == k)} positions, "
                   f"PSF σ {r['psf_sigma']:.2f}px ({r['psf_n']} stars)")

    # pixel -> tangent-plane arcsec (x east, y north) about the field centre
    def to_tan(x, y):
        wra, wdec = grid.pixel_to_world_values(np.atleast_1d(x), np.atleast_1d(y))
        return C.tangent(wra, wdec, ra, dec)

    # 5: registration on Gaia
    rad = fov / 60 / 2 * math.sqrt(2) + 0.02
    gstars = C.gaia(ra, dec, rad, name)
    g_ok = [g for g in gstars if g["pmra"] is not None and g["g_mag"] is not None and g["g_mag"] < REF_MAX_G
            and math.hypot(g["pmra"], g["pmdec"]) < REF_MAX_PM]
    raw = {key: tuple(float(v[0]) for v in to_tan(f["x"], f["y"])) for key, f in meas.items()}
    ref_pool = {}   # (source id, k) -> Gaia position at that date, for clean isolated references
    gaia_of = {}    # source id -> Gaia star (nearest, any)
    for k, r in enumerate(des):
        year = float(C.mjd_to_year(r["mjd"]))
        gx, gy = C.gaia_xy_at(g_ok, year, ra, dec)
        for m in master:
            f = meas.get((m["id"], k))
            if f is None or f["n_neighbours"] > 0 or f["core_bad"] > 0 or m["snr"] < 8 or not len(gx):
                continue
            tx, ty = raw[(m["id"], k)]
            dd = np.hypot(gx - tx, gy - ty)
            j = int(np.argmin(dd))
            if dd[j] > MATCH_PX * C.PIXEL_ARCSEC or np.sum(dd < 2 * C.PIXEL_ARCSEC) > 1:
                continue
            ref_pool[(m["id"], k)] = (gx[j], gy[j])
            gaia_of[m["id"]] = g_ok[j]

    def registrations(allowed):
        out = []
        for k in range(len(des)):
            keys = [(i, kk) for (i, kk) in ref_pool if kk == k and allowed(i)]
            if len(keys) < 3:
                out.append(None)
                continue
            f_err = np.array([math.hypot(meas[q]["ex"], meas[q]["ey"]) / math.sqrt(2) * C.PIXEL_ARCSEC for q in keys])
            reg = register(np.array([raw[q] for q in keys]), np.array([ref_pool[q] for q in keys]), f_err)
            if reg is not None:
                reg["ref_ids"] = [q[0] for q, u in zip(keys, reg["used"]) if u]
                reg["ref_all_ids"] = [q[0] for q in keys]
                reg["ref_resid"] = [[float(a), float(b)] for a, b in reg["resid"]]
                reg["ref_err"] = f_err.tolist()
            out.append(reg)
        return out

    regs = registrations(lambda i: True)
    for k, (r, reg) in enumerate(zip(des, regs)):
        if reg is None:
            C.log(tag, f"v{r['visit']} D{r['det']}: registration FAILED")
        else:
            C.log(tag, f"v{r['visit']} D{r['det']}: {reg['n_ref']}/{reg['n_cand']} refs, rms {reg['rms']:.2f}″, "
                       f"floor {reg['floor']:.2f}″, affine {reg['affine']}")
    years = np.array([float(C.mjd_to_year(r["mjd"])) for r in des])

    def series(sid, regset):
        pts = []
        for k, r in enumerate(des):
            f = meas.get((sid, k))
            reg = regset[k]
            if f is None or reg is None:
                continue
            tx, ty = raw[(sid, k)]
            T = np.array(reg["T"])
            px, py = T[:, :2] @ np.array([tx, ty]) + T[:, 2]
            ex = math.hypot(f["ex"] * C.PIXEL_ARCSEC, reg["floor"])
            ey = math.hypot(f["ey"] * C.PIXEL_ARCSEC, reg["floor"])
            if (f["amp"] / f["eamp"] if f["eamp"] > 0 else 0) < 3:
                continue
            pts.append({"k": k, "visit": r["visit"], "det": r["det"], "year": years[k], "x": float(px),
                        "y": float(py), "ex": ex, "ey": ey})
        return pts

    # negative control: every reference star measured with visits registered on the OTHER half of the references
    half = {0: registrations(lambda i: i % 2 == 1), 1: registrations(lambda i: i % 2 == 0)}
    controls = []
    for sid, g in gaia_of.items():
        pts = series(sid, half[sid % 2])
        if len({p["visit"] for p in pts}) < 2 or len(pts) < 3:
            continue
        a = np.array([[p["year"], p["x"], p["y"], p["ex"], p["ey"]] for p in pts])
        fit = motion_fit(*a.T)
        dx, dy = fit["pmx"] - g["pmra"] / 1000, fit["pmy"] - g["pmdec"] / 1000
        controls.append({"id": sid, "gaia_id": g["source_id"], "g_mag": g["g_mag"],
                         "snr": next(m["snr"] for m in master if m["id"] == sid),
                         "gaia_pmra": g["pmra"], "gaia_pmdec": g["pmdec"], "pmx": fit["pmx"], "pmy": fit["pmy"],
                         "epmx": fit["epmx"], "epmy": fit["epmy"], "pm_sig": fit["pm_sig"],
                         "resid_sig": math.hypot(dx / fit["epmx"], dy / fit["epmy"]), "n_points": len(pts),
                         "n_visits": len({p["visit"] for p in pts}), "baseline": float(np.ptp(a[:, 0]))})
    C.log(tag, f"negative control: {len(controls)} Gaia reference stars measured against the other half")

    # 6: per-source series and fits
    sources = []
    for m in master:
        pts = []
        for k, r in enumerate(des):
            f = meas.get((m["id"], k))
            reg = regs[k]
            if f is None or reg is None:
                continue
            tx, ty = raw[(m["id"], k)]
            T = np.array(reg["T"])
            px, py = T[:, :2] @ np.array([tx, ty]) + T[:, 2]
            ex = math.hypot(f["ex"] * C.PIXEL_ARCSEC, reg["floor"])
            ey = math.hypot(f["ey"] * C.PIXEL_ARCSEC, reg["floor"])
            snr_k = f["amp"] / f["eamp"] if f["eamp"] > 0 else 0
            if snr_k < 3:
                continue
            pts.append({"k": k, "visit": r["visit"], "det": r["det"], "year": years[k], "x": float(px), "y": float(py),
                        "ex": ex, "ey": ey, "amp": f["amp"], "eamp": f["eamp"], "chi2": f["chi2"],
                        "core_bad": f["core_bad"], "flag_frac": f["flag_frac"], "n_neighbours": f["n_neighbours"]})
        src = {"id": m["id"], "x_px": m["x"], "y_px": m["y"], "snr": m["snr"], "found_in": m["found_in"], "points": pts,
               "n_points": len(pts), "visits": sorted({p["visit"] for p in pts}),
               "detectors": sorted({p["det"] for p in pts})}
        if len({p["visit"] for p in pts}) >= 2 and len(pts) >= 3:
            a = np.array([[p["year"], p["x"], p["y"], p["ex"], p["ey"]] for p in pts])
            fit = motion_fit(*a.T)
            src["fit"] = fit
            for grp, dets in (("short", (1, 2, 3)), ("long", (4, 5, 6))):
                b = a[[p["det"] in dets for p in pts]]
                if len(b) >= 3 and len(set(np.round(b[:, 0], 2))) >= 2 and np.ptp(b[:, 0]) > 0.1:
                    src[f"fit_{grp}"] = motion_fit(*b.T)
            sra, sdec = C.untangent(fit["x0"], fit["y0"], ra, dec)
            src["ra"], src["dec"] = float(sra), float(sdec)
        else:
            tx, ty = to_tan(m["x"], m["y"])
            sra, sdec = C.untangent(tx, ty, ra, dec)
            src["ra"], src["dec"] = float(sra[0]), float(sdec[0])
        sources.append(src)
    for t in transients:
        tx, ty = to_tan(t["x"], t["y"])
        sra, sdec = C.untangent(tx, ty, ra, dec)
        t["ra"], t["dec"] = float(sra[0]), float(sdec[0])
        t["mjd_range"] = [min(e["mjd"] for r in des if r["visit"] == t["visit"] for e in r["exposures"]),
                          max(e["mjd"] for r in des if r["visit"] == t["visit"] for e in r["exposures"])]

    de_meta = [{"index": k, "visit": r["visit"], "det": r["det"], "mjd": r["mjd"], "year": years[k],
                "n_exposures": len(r["exposures"]), "wl_min": r["wl_min"], "wl_max": r["wl_max"],
                "psf_sigma_px": r["psf_sigma"], "psf_n": r["psf_n"],
                "pct_flagged_mean": float(np.mean([e["pct_flagged"] for e in r["exposures"]])),
                "collections": sorted({e["collection"] for e in r["exposures"]}),
                "obs_ids": [e["obs_id"] for e in r["exposures"]],
                "exposures": [{"obs_id": e["obs_id"], "file": e["file"], "mjd": e["mjd"], "wl_um": e["wl_um"]}
                              for e in r["exposures"]],
                "registration": None if regs[k] is None else {kk: regs[k][kk] for kk in
                                                             ("T", "floor", "n_ref", "n_cand", "rms", "affine")}}
               for k, r in enumerate(des)]

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if k not in ("used", "resid")}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, np.integer, np.bool_)):
            return o.item()
        return o
    (out / "detector_epochs.json").write_text(json.dumps(clean(de_meta), indent=1))
    (out / "sources.json").write_text(json.dumps(clean(sources)))
    (out / "transients.json").write_text(json.dumps(clean(transients), indent=1))
    (out / "controls.json").write_text(json.dumps(clean(controls), indent=1))
    (out / "registration.json").write_text(json.dumps(clean([
        None if g is None else {k: g[k] for k in ("ref_ids", "ref_all_ids", "ref_resid", "ref_err", "floor", "rms",
                                                   "n_ref", "affine")} for g in regs])))
    np.savez_compressed(out / "coadds.npz", deep=deep.astype(np.float32), deep_sig=deep_sig.astype(np.float32),
                        images=np.stack([r["image"] for r in des]), sigmas=np.stack([r["sigma"] for r in des]),
                        bad=np.stack([r["bad"] for r in des]))
    (out / "meta.json").write_text(json.dumps(clean({
        "name": name, "ra": ra, "dec": dec, "fov_arcmin": fov, "grid_size": size, "pixel_arcsec": C.PIXEL_ARCSEC,
        "made_at": C.now(), "collections": list(C.COLLECTIONS), "n_images_listed": len(ims), "n_visits": len(visits),
        "visits": [{"id": v["id"], "date": v["date"], "mjd_min": v["mjd_min"], "mjd_max": v["mjd_max"],
                    "n_images": v["n_images"]} for v in visits],
        "n_cutouts_used": sum(len(r["exposures"]) for r in des), "n_detector_epochs": len(des),
        "n_master": len(master), "n_transients": len(transients), "header_versions": versions,
        "n_gaia": len(gstars), "n_gaia_ref_pool": len(g_ok), "max_per_detector_epoch": max_per,
        "settings": {"DETECT_SNR": DETECT_SNR, "TRANSIENT_SNR": TRANSIENT_SNR, "BOX": BOX, "BG_SIZE": BG_SIZE,
                     "REF_MAX_PM": REF_MAX_PM, "REF_MAX_G": REF_MAX_G, "MATCH_PX": MATCH_PX}}), indent=1))
    C.log(tag, f"done: {len(sources)} sources, {sum('fit' in s for s in sources)} with motion fits")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("ra", type=float)
    ap.add_argument("dec", type=float)
    ap.add_argument("--fov", type=float, default=20.0)
    ap.add_argument("--max-per", type=int, default=0, help="max exposures per detector-epoch (0 = all)")
    a = ap.parse_args()
    run(a.name, a.ra, a.dec, a.fov, a.max_per)


if __name__ == "__main__":
    main()
