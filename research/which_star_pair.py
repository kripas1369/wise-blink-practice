"""Which star makes an eclipse that TESS-EBs lists under two nearby TIC stars? Measured with SPHEREx.

    PYTHONPATH=. .venv/bin/python research/which_star_pair.py TIC_A TIC_B [--cache-only] [--fov ARCMIN]

TESS's 21″ pixels mix the two stars; SPHEREx's 6.15″ pixels separate them. Every chosen SPHEREx exposure gets
an orbital phase from the TESS clock (the TESS-EBs entry with the smaller phase error in 2026), and two
independent tests are run on the same exposures:

1. Circles: each star in its own 2 px circle (sky ring 5-8 px), divided by its own normal brightness S(λ)
   per detector (fitted to out-of-eclipse exposures), then the mean in the middle of the primary eclipse.
2. Two-star fit: per detector, in-eclipse exposures are matched one-to-one in wavelength with out-of-eclipse
   ones and co-added. The out-of-eclipse co-add is fitted with both stars as Gaussians of one width (positions
   from Gaia/TIC, a common shift allowed); the difference (out - in) is then fitted with the same two shapes.
   depth = lost light / normal light, for each star separately. This works when the circles overlap.

The real binary has depth > 0; the other star's depth is ~0. Output: research/out/pair_<A>_<B>/
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from backend.app import archive
from backend.app import eclipse_build as B
from backend.app import eclipse_depth as M
from backend.app import eclipses as E
from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import DETECTORS
from backend.app.coords import mjd_to_year
from backend.app.gaia import gaia_stars, search_radius_deg, star_at
from backend.app.lightcurve import CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX
from backend.app.motion import separation_arcsec
from backend.app.render import MIN_COVERED_PCT

import dr1  # noqa: E402  (research/dr1.py)

archive.MAX_PARALLEL_DOWNLOADS = 6
OUT = Path(__file__).parent / "out"
CENTRAL = 0.5          # "middle of the eclipse": |φ| < CENTRAL × width / 2
FIT_RADIUS_PX = 4.0    # two-star fit uses pixels this close to either star
MASK_RADIUS_PX = 2.5   # ... minus pixels this close to other Gaia stars bright enough to matter


def normalise_all(det, wl, f, e, fit):
    g = np.full(f.shape, np.nan)
    ge = np.full(f.shape, np.nan)
    for d in np.unique(det):
        m = det == d
        st = M.fit_steady(wl[m & fit], f[m & fit], e[m & fit], M.RESOLVING_POWER[int(d)])
        if st is None:
            continue
        s = st(wl[m])
        g[m], ge[m] = f[m] / s, e[m] / s
    return g, ge


def clock(a: E.Ephemeris, b: E.Ephemeris, btjd: float) -> E.Ephemeris:
    return min((a, b), key=lambda e: e.phase_error(btjd))


def load(images, eph, ra, dec, fov, budget, cache_only):
    grid, size = target_grid(ra, dec, fov)
    size_deg = cutout_size_deg(fov)
    c = (size - 1) // 2
    chosen = {d: E.select_for_download(images.get(d, []), eph, ra, dec, budget) for d in DETECTORS}
    flat = [im for d in DETECTORS for im in chosen[d]]
    files = {im.did: archive.cutout_file(im, ra, dec, size_deg) for im in flat}
    missing = [im for im in flat if not files[im.did].exists()]
    if missing and not cache_only:
        print(f"  downloading {len(missing)} cutouts", flush=True)
        for i in range(0, len(missing), B.PATH_CHUNK):
            B._patiently(archive.attach_paths, missing[i:i + B.PATH_CHUNK], 100)
        files.update(archive.download_cutouts(missing, ra, dec, size_deg))
    rows = []
    for im in flat:
        p = files.get(im.did)
        if not isinstance(p, Path) or not p.exists():
            continue
        try:
            cleaned = clean_cutout(p, ra, dec)
        except Exception:
            continue
        a = align(cleaned, grid, size)
        if a["pct_covered"] < MIN_COVERED_PCT or not a["inside"][c, c]:
            continue
        rows.append({"det": im.detector, "mjd": cleaned["mjd"], "wl": cleaned["wl_um"], "bw": cleaned["bw_um"],
                     "aligned": a})
    rows.sort(key=lambda r: (r["det"], r["mjd"]))
    return rows, grid, size


def circle_test(rows, xy, det, wl, phi, eph):
    ms = B.photometry(rows, xy[0], xy[1], 0.0, CORE_RADIUS_PX, FIELD_SKY_ANNULUS_PX)
    f = np.array([np.nan if m.get("flux_mjy") is None else m["flux_mjy"] for m in ms], float)
    e = np.array([np.nan if m.get("err_mjy") is None else m["err_mjy"] for m in ms], float)
    fl = np.array([m.get("n_flagged", 1) for m in ms]) > 0
    return depth_test(f, e, fl, det, wl, phi, eph)


def depth_test(f, e, fl, det, wl, phi, eph):
    """Brightness / own normal brightness per exposure, and the mean depth in each eclipse's middle."""
    good = np.isfinite(wl) & np.isfinite(f) & np.isfinite(e) & (e > 0) & ~fl & (f > 3 * e)
    clear = E.out_of_eclipse(phi, eph)
    g, ge = normalise_all(det, wl, f, e, good & clear)
    g[~good] = np.nan
    ok = np.isfinite(g) & np.isfinite(ge)
    s = M.jitter(g[ok & clear], ge[ok & clear]) if (ok & clear).sum() > 5 else 0.0
    ge = np.sqrt(ge ** 2 + s ** 2)
    part = E.eclipse_part(phi, eph, CENTRAL)
    out = {"n_good": int(ok.sum()), "scatter_pct": round(100 * M.robust_std(g[ok & clear]), 2)
           if (ok & clear).sum() > 5 else None}
    for name, k in (("primary", 1), ("secondary", 2)):
        r = M.weighted_depth(g[ok & (part == k)], ge[ok & (part == k)])
        out[name] = None if r is None else {"depth": round(r["depth"], 4), "err": round(r["err"], 4),
                                             "n": int((ok & (part == k)).sum())}
    return out, g, ge


def gauss(shape, x, y, s):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    return np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s)) / (2 * np.pi * s * s)


def two_star_fit(rows, det_id, phi, eph, pA, pB, others):
    """Depth of each star from wavelength-matched in/out co-adds of one detector (see module doc)."""
    idx = [i for i, r in enumerate(rows) if r["det"] == det_id and r["wl"] is not None]
    part = E.eclipse_part(phi, eph, CENTRAL)
    clear = E.out_of_eclipse(phi, eph)
    inside = sorted((i for i in idx if part[i] == 1), key=lambda i: rows[i]["wl"])
    pool = [i for i in idx if clear[i]]
    pairs = []
    for i in inside:
        if not pool:
            break
        j = min(pool, key=lambda j: abs(rows[j]["wl"] - rows[i]["wl"]))
        if abs(rows[j]["wl"] - rows[i]["wl"]) < 0.5 * (rows[i]["bw"] or 0):
            pairs.append((i, j))
            pool.remove(j)
    if len(pairs) < 3:
        return {"n_pairs": len(pairs), "reason": "fewer than 3 wavelength-matched pairs"}
    cin = coadd([rows[i]["aligned"] for i, _ in pairs])
    cout = coadd([rows[j]["aligned"] for _, j in pairs])
    O, sO = cout["image"], cout["sigma"]
    D = cout["image"] - cin["image"]
    sD = np.hypot(cout["sigma"], cin["sigma"])
    shape = O.shape
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    near = (np.hypot(xx - pA[0], yy - pA[1]) < FIT_RADIUS_PX) | (np.hypot(xx - pB[0], yy - pB[1]) < FIT_RADIUS_PX)
    for ox, oy in others:
        near &= np.hypot(xx - ox, yy - oy) > MASK_RADIUS_PX
    ok = near & np.isfinite(O) & np.isfinite(D) & np.isfinite(sO) & (sO > 0) & np.isfinite(sD) & (sD > 0)
    if ok.sum() < 12:
        return {"n_pairs": len(pairs), "reason": "too few clean pixels around the pair"}
    # Sky: median of a ring 6-9 px from the pair's middle, so the fit only needs the stars.
    mid = ((pA[0] + pB[0]) / 2, (pA[1] + pB[1]) / 2)
    rr = np.hypot(xx - mid[0], yy - mid[1])
    ring = (rr > 6 + math.hypot(pA[0] - pB[0], pA[1] - pB[1]) / 2) & (rr < 9 + math.hypot(pA[0] - pB[0], pA[1] - pB[1]) / 2)
    O = O - np.nanmedian(O[ring & np.isfinite(O)])
    D = D - np.nanmedian(D[ring & np.isfinite(D)])

    def peak(p):
        return max(float(np.nanmax(np.where(np.hypot(xx - p[0], yy - p[1]) < 1.5, O, np.nan))), 1e-6) * 2 * np.pi

    def model(p):
        fa, fb, dx, dy, s = p
        return fa * gauss(shape, pA[0] + dx, pA[1] + dy, s) + fb * gauss(shape, pB[0] + dx, pB[1] + dy, s)

    res = least_squares(lambda p: ((O - model(p)) / sO)[ok], [peak(pA), peak(pB), 0.0, 0.0, 1.0],
                        bounds=([0, 0, -1, -1, 0.4], [np.inf, np.inf, 1, 1, 3.0]))
    fa, fb, dx, dy, s = res.x
    chi2_out = float(np.sum(res.fun ** 2) / max(ok.sum() - 5, 1))
    GA = gauss(shape, pA[0] + dx, pA[1] + dy, s)
    GB = gauss(shape, pB[0] + dx, pB[1] + dy, s)
    A = np.stack([GA[ok] / sD[ok], GB[ok] / sD[ok]], axis=1)
    coef, *_ = np.linalg.lstsq(A, D[ok] / sD[ok], rcond=None)
    resid = D[ok] / sD[ok] - A @ coef
    chi2 = float(np.sum(resid ** 2) / max(ok.sum() - 2, 1))
    cov = np.linalg.inv(A.T @ A) * max(chi2, 1.0)
    a, b = coef
    ea, eb = np.sqrt(np.diag(cov))
    wl = float(np.mean([rows[i]["wl"] for i, _ in pairs]))
    return {"n_pairs": len(pairs), "wl_um": round(wl, 3), "sigma_px": round(float(s), 3),
            "shift_px": [round(float(dx), 2), round(float(dy), 2)], "chi2_out": round(chi2_out, 2), "chi2_diff": round(chi2, 2),
            "flux_A": float(fa), "flux_B": float(fb),
            "depth_A": float(a / fa) if fa > 0 else None, "err_A": float(ea / fa) if fa > 0 else None,
            "depth_B": float(b / fb) if fb > 0 else None, "err_B": float(eb / fb) if fb > 0 else None,
            "lost_A": float(a), "lost_A_err": float(ea), "lost_B": float(b), "lost_B_err": float(eb)}


def psf_shape(rows, det_id, phi, eph, pA, pB, others):
    """Gaussian width and common shift of both stars, from the co-add of one detector's out-of-eclipse exposures."""
    clear = E.out_of_eclipse(phi, eph)
    idx = [i for i, r in enumerate(rows) if r["det"] == det_id and clear[i]]
    if len(idx) < 3:
        return None
    c = coadd([rows[i]["aligned"] for i in idx])
    O, sO = c["image"], c["sigma"]
    yy, xx = np.mgrid[:O.shape[0], :O.shape[1]]
    near = (np.hypot(xx - pA[0], yy - pA[1]) < FIT_RADIUS_PX) | (np.hypot(xx - pB[0], yy - pB[1]) < FIT_RADIUS_PX)
    for ox, oy in others:
        near &= np.hypot(xx - ox, yy - oy) > MASK_RADIUS_PX
    ok = near & np.isfinite(O) & np.isfinite(sO) & (sO > 0)
    if ok.sum() < 12:
        return None

    def model(p):
        fa, fb, dx, dy, s, bg = p
        return bg + fa * gauss(O.shape, pA[0] + dx, pA[1] + dy, s) + fb * gauss(O.shape, pB[0] + dx, pB[1] + dy, s)

    pk = lambda p: max(float(np.nanmax(np.where(np.hypot(xx - p[0], yy - p[1]) < 1.5, O, np.nan))), 1e-6) * 2 * np.pi
    res = least_squares(lambda p: ((O - model(p)) / sO)[ok], [pk(pA), pk(pB), 0, 0, 1.0, float(np.nanmedian(O[ok]))],
                        bounds=([0, 0, -1, -1, 0.4, -np.inf], [np.inf, np.inf, 1, 1, 3.0, np.inf]))
    return {"dx": float(res.x[2]), "dy": float(res.x[3]), "sigma": float(res.x[4])}


def psf_photometry(rows, det, pA, pB, others, shapes):
    """Both stars' fluxes in every exposure: fixed positions and width, free amplitudes and a constant sky."""
    n = len(rows)
    fA, eA, fB, eB = (np.full(n, np.nan) for _ in range(4))
    for i, r in enumerate(rows):
        sh = shapes.get(int(det[i]))
        if sh is None:
            continue
        a = r["aligned"]
        img, sig = a["image"], a["sigma"]
        yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
        near = (np.hypot(xx - pA[0], yy - pA[1]) < FIT_RADIUS_PX) | (np.hypot(xx - pB[0], yy - pB[1]) < FIT_RADIUS_PX)
        for ox, oy in others:
            near &= np.hypot(xx - ox, yy - oy) > MASK_RADIUS_PX
        ok = near & np.isfinite(img) & np.isfinite(sig) & (sig > 0) & ~a["bad"]
        coreA = ok & (np.hypot(xx - pA[0], yy - pA[1]) < 1.5)
        coreB = ok & (np.hypot(xx - pB[0], yy - pB[1]) < 1.5)
        if coreA.sum() < 4 or coreB.sum() < 4 or ok.sum() < 12:
            continue
        GA = gauss(img.shape, pA[0] + sh["dx"], pA[1] + sh["dy"], sh["sigma"])
        GB = gauss(img.shape, pB[0] + sh["dx"], pB[1] + sh["dy"], sh["sigma"])
        A = np.stack([GA[ok], GB[ok], np.ones(ok.sum())], axis=1) / sig[ok][:, None]
        coef, *_ = np.linalg.lstsq(A, img[ok] / sig[ok], rcond=None)
        resid = img[ok] / sig[ok] - A @ coef
        chi2 = float(np.sum(resid ** 2) / max(ok.sum() - 3, 1))
        cov = np.linalg.inv(A.T @ A) * max(chi2, 1.0)
        fA[i], fB[i] = coef[0], coef[1]
        eA[i], eB[i] = math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1])
    return fA, eA, fB, eB


def combine(vals):
    v = [(x, e) for x, e in vals if x is not None and e is not None and np.isfinite(x) and np.isfinite(e) and e > 0]
    if not v:
        return None
    w = np.array([1 / e ** 2 for _, e in v])
    x = np.array([x for x, _ in v])
    mean = float((w * x).sum() / w.sum())
    err = float(1 / math.sqrt(w.sum()))
    chi2 = float((((x - mean) ** 2) * w).sum() / max(len(v) - 1, 1))
    return {"depth": round(mean, 4), "err": round(err * max(1.0, math.sqrt(chi2)), 4), "n_detectors": len(v),
            "chi2_red": round(chi2, 2)}


def tic_star(tess_id, year, stars):
    e = E.by_tess_id(tess_id)
    ra, dec = e.position(year)
    best = min(stars, key=lambda s: separation_arcsec(*star_at(s, year), ra, dec))
    sep = separation_arcsec(*star_at(best, year), ra, dec)
    return e, (ra, dec), (best if sep < 3 else None), sep


def run(a_id, b_id, fov=None, cache_only=False, budget=E.BUDGET, centre_a=False, legacy=False):
    ea, eb = E.by_tess_id(a_id), E.by_tess_id(b_id)
    images = E.cached_images(ea) if legacy else dr1.images(ea)
    mjds = [im.mjd for ims in images.values() for im in ims]
    year = mjd_to_year(float(np.median(mjds)))
    pa, pb = ea.position(year), eb.position(year)
    sep = separation_arcsec(*pa, *pb)
    eph = clock(ea, eb, float(np.median(E.to_btjd(mjds[:50], *pa))))
    ra, dec = pa if centre_a else ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
    fov = fov or max(3.0, (sep + 80) / 60 * (2 if centre_a else 1))
    print(f"TIC {a_id} + TIC {b_id}: {sep:.1f}″ apart, clock from TIC {eph.tess_id} (P {eph.period} d, phase error "
          f"{eph.phase_error(4000):.4f}), field {fov:.1f}′, {len(mjds)} SPHEREx images", flush=True)
    rows, grid, size = load(images, eph, ra, dec, fov, budget, cache_only)
    print(f"  {len(rows)} exposures on the grid", flush=True)
    btjd = E.to_btjd([r["mjd"] for r in rows], ra, dec)
    phi = E.phase(btjd, eph)
    det = np.array([r["det"] for r in rows])
    wl = np.array([np.nan if r["wl"] is None else r["wl"] for r in rows], float)

    stars = gaia_stars(ra, dec, search_radius_deg(fov, year - 2016.0))
    out = {"pair": [a_id, b_id], "sep_arcsec": round(sep, 2), "clock": E.summary(eph), "fov_arcmin": fov,
           "n_exposures": len(rows), "n_images_archive": len(mjds), "year": round(year, 3), "stars": {},
           "collections": "website cache (QR2/QR3)" if legacy else list(dr1.COLLECTIONS),
           "time_range_mjd": [round(min(mjds), 2), round(max(mjds), 2)]}
    pix = {}
    gA = gB = None
    for tid, e, p in ((a_id, ea, pa), (b_id, eb, pb)):
        _, _, gs, gsep = tic_star(tid, year, stars)
        x, y = grid.world_to_pixel_values(*p)
        pix[tid] = (float(x), float(y))
        out["stars"][tid] = {"tmag": e.tmag, "tess_depth": e.prim_depth, "tess_sec_depth": e.sec_depth,
                             "period": e.period, "gaia": gs and {k: gs[k] for k in ("source_id", "g_mag", "parallax")},
                             "gaia_sep_arcsec": round(gsep, 2), "xy": [round(float(x), 2), round(float(y), 2)]}
        if tid == a_id:
            gA = gs
        else:
            gB = gs
    faint = max((s["g_mag"] for s in (gA, gB) if s and s["g_mag"] is not None), default=16)
    others = []
    for s in stars:
        if s in (gA, gB) or s["g_mag"] is None or s["g_mag"] > faint + 1.5:
            continue
        x, y = grid.world_to_pixel_values(*star_at(s, year))
        if min(math.hypot(x - pix[t][0], y - pix[t][1]) for t in pix) > 1.5:
            others.append((float(x), float(y)))

    lc = {}
    for tid in (a_id, b_id):
        res, g, ge = circle_test(rows, pix[tid], det, wl, phi, eph)
        out["stars"][tid]["circle"] = res
        lc[tid] = (g, ge)
        print(f"  circle TIC {tid}: primary {res['primary']}, secondary {res['secondary']}, scatter {res['scatter_pct']}%",
              flush=True)

    fits = {}
    for d in DETECTORS:
        try:
            fits[d] = two_star_fit(rows, d, phi, eph, pix[a_id], pix[b_id], others)
        except Exception as exc:
            fits[d] = {"reason": f"fit failed: {exc}"}
        f = fits[d]
        if "depth_A" in f:
            print(f"  D{d} {f['wl_um']} µm ({f['n_pairs']} pairs, σ {f['sigma_px']} px): A {f['depth_A']:.3f} ± {f['err_A']:.3f}, "
                  f"B {f['depth_B']:.3f} ± {f['err_B']:.3f}", flush=True)
    out["two_star_fit"] = {"per_detector": fits,
                           "A": combine([(f.get("depth_A"), f.get("err_A")) for f in fits.values()]),
                           "B": combine([(f.get("depth_B"), f.get("err_B")) for f in fits.values()])}
    print(f"  two-star fit, all detectors: A {out['two_star_fit']['A']}, B {out['two_star_fit']['B']}", flush=True)

    shapes = {}
    for d in DETECTORS:
        try:
            sh = psf_shape(rows, d, phi, eph, pix[a_id], pix[b_id], others)
        except Exception:
            sh = None
        if sh:
            shapes[d] = sh
    fA, eA, fB, eB = psf_photometry(rows, det, pix[a_id], pix[b_id], others, shapes)
    no_flag = np.zeros(len(rows), bool)
    psf = {}
    for tid, f, e in ((a_id, fA, eA), (b_id, fB, eB)):
        res, g, ge = depth_test(f, e, no_flag, det, wl, phi, eph)
        psf[tid] = (g, ge)
        out["stars"][tid]["psf"] = res
        print(f"  per-exposure two-star fit TIC {tid}: primary {res['primary']}, secondary {res['secondary']}, "
              f"scatter {res['scatter_pct']}%", flush=True)
    out["psf_shapes"] = {str(d): {k: round(v, 3) for k, v in s.items()} for d, s in shapes.items()}

    folder = OUT / f"pair_{a_id}_{b_id}"
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / "points.npz", btjd=btjd, phi=phi, det=det, wl=wl,
             gA=lc[a_id][0], geA=lc[a_id][1], gB=lc[b_id][0], geB=lc[b_id][1],
             pA=psf[a_id][0], peA=psf[a_id][1], pB=psf[b_id][0], peB=psf[b_id][1])
    (folder / "result.json").write_text(json.dumps(out, indent=1, default=float))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--fov", type=float)
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--centre-a", action="store_true", help="centre the grid on A (reuses eclipse_build cutouts)")
    p.add_argument("--legacy", action="store_true", help="image list from the website cache (QR2/QR3) instead of DR1+QR3")
    args = p.parse_args()
    run(args.a, args.b, args.fov, args.cache_only, centre_a=args.centre_a, legacy=args.legacy)


if __name__ == "__main__":
    main()
