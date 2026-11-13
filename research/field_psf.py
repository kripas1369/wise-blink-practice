"""Forced PSF photometry of every Gaia star in a SPHEREx field, one exposure at a time.

    PYTHONPATH=. .venv/bin/python research/field_psf.py NAME RA DEC [--fov 5] [--gmax 16.5] [--per-det 70]
                                                          [--tic TIC] [--budget P,S,O]

Improves on research/which_star_pair.py, which fits two stars and blanks out pixels near any other star:

- all Gaia DR3 stars brighter than --gmax in the cutout are fitted together (plus a constant sky), so light from
  neighbours is assigned to them instead of being ignored or masked;
- the star image is a Gaussian integrated over each pixel (SPHEREx's PSF is ~1.5 px FWHM, i.e. undersampled, and a
  point-sampled Gaussian biases the flux with sub-pixel position);
- the Gaussian width and a common position shift are fitted per detector on the co-add of all chosen exposures,
  with the star amplitudes solved linearly inside the fit (variable projection);
- stars closer than MERGE_PX are one component (SPHEREx cannot tell them apart); the merged ids are recorded.

With --tic, exposures are chosen by the TESS clock (primary / secondary / outside budget, E.select_for_download).
Without it, PER_DET exposures per detector are spread evenly in time (blind variability search).

Output: research/experimental_results/NAME/  photometry.npz (mjd, det, wl, flux, err per exposure x star),
stars.json, meta.json, observation_log.csv, fits_headers.json (metadata of the first exposure per detector).
"""
import argparse
import csv
import dataclasses
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.optimize import least_squares
from scipy.special import erf

from backend.app import archive
from backend.app import eclipse_build as B
from backend.app import eclipses as E
from backend.app.align import align, cutout_size_deg, target_grid
from backend.app.clean import clean_cutout
from backend.app.coadd import coadd
from backend.app.config import DETECTORS
from backend.app.coords import mjd_to_year
from backend.app.gaia import gaia_stars, search_radius_deg, star_at
from backend.app.render import MIN_COVERED_PCT

import dr1  # noqa: E402

archive.MAX_PARALLEL_DOWNLOADS = 6
RESULTS = Path(__file__).parent / "experimental_results"
MERGE_PX = 0.9          # stars closer than this (5.5″) are one component
EDGE_PX = 1.5           # keep stars up to this far outside the grid (their wings fall inside)
CORE_PX = 1.5           # a star needs >= 3 good pixels this close to be measured in an exposure
HEADER_KEYS = ("MJD-AVG", "MJD-BEG", "MJD-END", "DATE-AVG", "TIMESYS", "DETECTOR", "OBSID", "EXPTIME", "BUNIT",
               "PSF_FWHM", "ZODI", "CTYPE1", "CTYPE2", "CDELT1", "CDELT2", "CD1_1", "CD1_2", "RADESYS")


def pixel_gauss(shape, x, y, s):
    """Unit-flux Gaussian integrated over each pixel (pixel centres at integer coordinates)."""
    k = 1 / (math.sqrt(2) * s)
    gx = 0.5 * (erf((np.arange(shape[1]) + 0.5 - x) * k) - erf((np.arange(shape[1]) - 0.5 - x) * k))
    gy = 0.5 * (erf((np.arange(shape[0]) + 0.5 - y) * k) - erf((np.arange(shape[0]) - 0.5 - y) * k))
    return np.outer(gy, gx)


def spread_in_time(ims, n):
    ims = sorted(ims, key=lambda im: im.mjd)
    if len(ims) <= n:
        return ims
    return [ims[int(i)] for i in np.linspace(0, len(ims) - 1, n).round()]


def load(flat, ra, dec, fov):
    grid, size = target_grid(ra, dec, fov)
    size_deg = cutout_size_deg(fov)
    c = (size - 1) // 2
    files = {im.did: archive.cutout_file(im, ra, dec, size_deg) for im in flat}
    missing = [im for im in flat if not files[im.did].exists()]
    if missing:
        print(f"  downloading {len(missing)} cutouts", flush=True)
        for i in range(0, len(missing), B.PATH_CHUNK):
            B._patiently(archive.attach_paths, missing[i:i + B.PATH_CHUNK], 100)
        files.update(archive.download_cutouts(missing, ra, dec, size_deg))
    rows, headers = [], {}
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
        if im.detector not in headers:
            with fits.open(p) as h:
                hd = {k: h[i].header.get(k) for i in range(min(len(h), 2)) for k in HEADER_KEYS if k in h[i].header}
                headers[im.detector] = {"file": p.name, "hdus": [x.name for x in h], **{k: str(v) for k, v in hd.items()}}
        rows.append({"det": im.detector, "mjd": cleaned["mjd"], "wl": cleaned["wl_um"], "bw": cleaned["bw_um"],
                     "obs_id": im.obs_id, "collection": im.collection, "aligned": a})
    rows.sort(key=lambda r: r["mjd"])
    return rows, grid, size, headers


def field_stars(ra, dec, fov, year, grid, size, gmax):
    stars = gaia_stars(ra, dec, search_radius_deg(fov, year - 2016.0))
    keep = []
    for s in sorted((s for s in stars if s["g_mag"] is not None and s["g_mag"] <= gmax), key=lambda s: s["g_mag"]):
        x, y = (float(v) for v in grid.world_to_pixel_values(*star_at(s, year)))
        if not (-EDGE_PX <= x <= size - 1 + EDGE_PX and -EDGE_PX <= y <= size - 1 + EDGE_PX):
            continue
        host = next((k for k in keep if math.hypot(k["x"] - x, k["y"] - y) < MERGE_PX), None)
        if host:
            host["merged"].append(s["source_id"])
            continue
        ra_s, dec_s = star_at(s, year)
        keep.append({"source_id": s["source_id"], "g_mag": s["g_mag"], "parallax": s["parallax"], "x": x, "y": y,
                     "ra": ra_s, "dec": dec_s, "merged": []})
    return keep


def psf(shape, x, y, s, wing_frac=0.0, wing_sigma=2.0):
    """Core Gaussian plus an optional wide wing (fraction wing_frac of the light), both pixel-integrated."""
    core = pixel_gauss(shape, x, y, s)
    return core if wing_frac <= 0 else (1 - wing_frac) * core + wing_frac * pixel_gauss(shape, x, y, wing_sigma)


def design(shape, xy, dx, dy, s, wing_frac=0.0, wing_sigma=2.0):
    return np.stack([psf(shape, x + dx, y + dy, s, wing_frac, wing_sigma).ravel() for x, y in xy]
                    + [np.ones(shape[0] * shape[1])], 1)


def fit_shape(rows, xy, wing=True):
    """Core width, wing (fraction, width) and common shift on the co-add of these exposures.

    Amplitudes are solved linearly inside the fit (variable projection). The wing describes SPHEREx's extended
    PSF halo; without it a bright star's halo is absorbed by its neighbours' amplitudes.
    """
    c = coadd([r["aligned"] for r in rows])
    O, sO = c["image"], c["sigma"]
    ok = (np.isfinite(O) & np.isfinite(sO) & (sO > 0) & ~c["bad"]).ravel()
    if ok.sum() < 3 * (len(xy) + 1):
        return None
    o, w = O.ravel()[ok], 1 / sO.ravel()[ok]

    def resid(p):
        A = design(O.shape, xy, *p)[ok] * w[:, None]
        coef, *_ = np.linalg.lstsq(A, o * w, rcond=None)
        return o * w - A @ coef

    p0, lo, hi = [0.0, 0.0, 0.7], [-1, -1, 0.3], [1, 1, 2.5]
    if wing:
        p0, lo, hi = p0 + [0.15, 2.0], lo + [0.0, 1.2], hi + [0.6, 6.0]
    res = least_squares(resid, p0, bounds=(lo, hi))
    chi2 = float(np.sum(res.fun ** 2) / max(ok.sum() - len(xy) - len(p0) - 1, 1))
    out = {"dx": float(res.x[0]), "dy": float(res.x[1]), "sigma": float(res.x[2]), "chi2_coadd": round(chi2, 2),
           "n_exposures": len(rows), "wing_frac": 0.0, "wing_sigma": 2.0}
    if wing:
        out["wing_frac"], out["wing_sigma"] = float(res.x[3]), float(res.x[4])
    return out


SHAPE_KEYS = ("dx", "dy", "sigma", "wing_frac", "wing_sigma")


def shape_at(sh, wl):
    """Shape for one exposure: interpolated in wavelength between the short- and long-wavelength halves."""
    if "halves" not in sh or wl is None or not np.isfinite(wl):
        return [sh[k] for k in SHAPE_KEYS]
    lo, hi = sh["halves"]
    t = float(np.clip((wl - lo["wl_um"]) / (hi["wl_um"] - lo["wl_um"]), 0, 1)) if hi["wl_um"] > lo["wl_um"] else 0.5
    return [lo[k] + t * (hi[k] - lo[k]) for k in SHAPE_KEYS]


def photometry(rows, xy, shapes):
    n, m = len(rows), len(xy)
    F, Er = np.full((n, m), np.nan), np.full((n, m), np.nan)
    chi = np.full(n, np.nan)
    for i, r in enumerate(rows):
        sh = shapes.get(r["det"])
        if sh is None:
            continue
        a = r["aligned"]
        img, sig = a["image"], a["sigma"]
        D = design(img.shape, xy, *shape_at(sh, r["wl"]))
        ok = (np.isfinite(img) & np.isfinite(sig) & (sig > 0) & ~a["bad"]).ravel()
        if ok.sum() < 2 * (m + 1):
            continue
        w = 1 / sig.ravel()[ok]
        A = D[ok] * w[:, None]
        coef, *_ = np.linalg.lstsq(A, img.ravel()[ok] * w, rcond=None)
        res = img.ravel()[ok] * w - A @ coef
        c2 = float(np.sum(res ** 2) / max(ok.sum() - m - 1, 1))
        try:
            # formal errors: a global chi2 scaling would charge bright-star model residuals to faint stars
            cov = np.linalg.inv(A.T @ A)
        except np.linalg.LinAlgError:
            continue
        yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
        good2d = ok.reshape(img.shape)
        for j, (x, y) in enumerate(xy):
            if (good2d & (np.hypot(xx - x, yy - y) < CORE_PX)).sum() >= 3:
                F[i, j], Er[i, j] = coef[j], math.sqrt(cov[j, j])
        chi[i] = c2
    return F, Er, chi


def ephemeris(tic, override=None):
    """The TESS-EBs clock of `tic`, optionally with fields replaced from a JSON file (e.g. an OGLE ephemeris:
    {"period": ..., "bjd0": BTJD, "prim_pos": 0, "period_err": ..., "bjd0_err": ...})."""
    eph = E.by_tess_id(tic)
    if override:
        eph = dataclasses.replace(eph, **json.loads(Path(override).read_text())["fields"])
    return eph


def run(name, ra, dec, fov, gmax, per_det, tic=None, budget=None, wing=True, by_wavelength=False, eph_json=None):
    folder = RESULTS / name
    folder.mkdir(parents=True, exist_ok=True)
    eph = ephemeris(tic, eph_json) if tic else None
    images = dr1.images(eph) if eph else dr1.images_at(ra, dec, name)
    n_all = sum(len(v) for v in images.values())
    if eph:
        b = dict(zip(("primary", "secondary", "outside"), budget)) if budget else E.BUDGET
        chosen = {d: E.select_for_download(images.get(d, []), eph, ra, dec, b) for d in DETECTORS}
    else:
        chosen = {d: spread_in_time(images.get(d, []), per_det) for d in DETECTORS}
    flat = [im for d in DETECTORS for im in chosen[d]]
    print(f"{name}: RA {ra:.5f} Dec {dec:.5f}, {n_all} DR1+QR3 images, {len(flat)} chosen", flush=True)
    rows, grid, size, headers = load(flat, ra, dec, fov)
    print(f"  {len(rows)} exposures on the {size}x{size} grid", flush=True)
    year = mjd_to_year(float(np.median([r["mjd"] for r in rows])))
    stars = field_stars(ra, dec, fov, year, grid, size, gmax)
    xy = [(s["x"], s["y"]) for s in stars]
    print(f"  {len(stars)} Gaia stars G <= {gmax}", flush=True)
    det = np.array([r["det"] for r in rows])
    shapes = {}
    for d in DETECTORS:
        sub = [r for r in rows if r["det"] == d]
        if len(sub) >= 3:
            try:
                sh = fit_shape(sub, xy, wing)
            except Exception as exc:
                print(f"  D{d} shape fit failed: {exc}", flush=True)
                sh = None
            if sh:
                shapes[d] = sh
                print(f"  D{d}: sigma {sh['sigma']:.3f} px, wing {sh['wing_frac']:.2f} x {sh['wing_sigma']:.2f} px, "
                      f"shift ({sh['dx']:+.2f}, {sh['dy']:+.2f}), co-add chi2 {sh['chi2_coadd']}", flush=True)
                if by_wavelength and len(sub) >= 12:
                    wls = np.array([r["wl"] if r["wl"] is not None else np.nan for r in sub], float)
                    mid = np.nanmedian(wls)
                    halves = []
                    for part in ([r for r, w in zip(sub, wls) if w <= mid], [r for r, w in zip(sub, wls) if w > mid]):
                        h = fit_shape(part, xy, wing) if len(part) >= 5 else None
                        if h is None:
                            break
                        h["wl_um"] = float(np.nanmedian([r["wl"] for r in part]))
                        halves.append(h)
                    if len(halves) == 2:
                        sh["halves"] = halves
                        print(f"      {halves[0]['wl_um']:.2f} µm sigma {halves[0]['sigma']:.3f} -> "
                              f"{halves[1]['wl_um']:.2f} µm sigma {halves[1]['sigma']:.3f}", flush=True)
    F, Er, chi = photometry(rows, xy, shapes)
    mjd = np.array([r["mjd"] for r in rows])
    wl = np.array([np.nan if r["wl"] is None else r["wl"] for r in rows], float)
    np.savez(folder / "photometry.npz", mjd=mjd, det=det, wl=wl, flux=F, err=Er, chi2=chi)
    (folder / "stars.json").write_text(json.dumps(stars, indent=1))
    with open(folder / "observation_log.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mjd_utc", "date_utc", "detector", "wavelength_um", "bandwidth_um", "obs_id", "collection",
                    "pct_flagged", "fit_chi2"])
        for r, c2 in zip(rows, chi):
            t = datetime(1858, 11, 17, tzinfo=timezone.utc).timestamp() + r["mjd"] * 86400
            w.writerow([round(r["mjd"], 6), datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds"),
                        r["det"], r["wl"] and round(r["wl"], 4), r["bw"] and round(r["bw"], 4), r["obs_id"],
                        r["collection"], r["aligned"]["pct_flagged"], None if not np.isfinite(c2) else round(float(c2), 3)])
    (folder / "fits_headers.json").write_text(json.dumps(headers, indent=1))
    meta = {"name": name, "ra": ra, "dec": dec, "fov_arcmin": fov, "grid_size_px": size, "gmax": gmax, "tic": tic,
            "eph_json": eph_json,
            "n_images_archive": n_all, "n_chosen": len(flat), "n_exposures": len(rows),
            "collections": list(dr1.COLLECTIONS), "mjd_range": [float(mjd.min()), float(mjd.max())],
            "wavelength_range_um": [float(np.nanmin(wl)), float(np.nanmax(wl))],
            "per_detector": {str(d): {"n": int((det == d).sum()),
                                      "wl_um": [float(np.nanmin(wl[det == d])), float(np.nanmax(wl[det == d]))]
                                      if (det == d).any() else None} for d in DETECTORS},
            "shapes": {str(d): s for d, s in shapes.items()}, "year": year,
            "made": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (folder / "meta.json").write_text(json.dumps(meta, indent=1))
    np.savez_compressed(folder / "coadds.npz", **{f"d{d}": coadd([r["aligned"] for r in rows if r["det"] == d])["image"]
                                                  for d in shapes})
    _save_frames(folder, rows)
    print(f"  saved {folder}", flush=True)
    return folder


def _save_frames(folder, rows):
    """Every aligned exposure (same order as photometry.npz) for flipbooks and difference images."""
    idx = np.arange(len(rows))
    np.savez_compressed(folder / "frames.npz", image=np.stack([rows[i]["aligned"]["image"] for i in idx]),
                        mjd=np.array([rows[i]["mjd"] for i in idx]), det=np.array([rows[i]["det"] for i in idx]),
                        wl=np.array([rows[i]["wl"] or np.nan for i in idx], float))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("ra", type=float)
    p.add_argument("dec", type=float)
    p.add_argument("--fov", type=float, default=5.0)
    p.add_argument("--gmax", type=float, default=16.5)
    p.add_argument("--per-det", type=int, default=70)
    p.add_argument("--tic")
    p.add_argument("--budget", help="primary,secondary,outside exposures per detector (with --tic)")
    p.add_argument("--no-wing", action="store_true", help="single Gaussian PSF (for comparison)")
    p.add_argument("--eph-json", help="replace clock fields of --tic (e.g. an OGLE ephemeris)")
    a = p.parse_args()
    budget = tuple(int(x) for x in a.budget.split(",")) if a.budget else None
    run(a.name, a.ra, a.dec, a.fov, a.gmax, a.per_det, a.tic, budget, wing=not a.no_wing, eph_json=a.eph_json)


if __name__ == "__main__":
    main()
