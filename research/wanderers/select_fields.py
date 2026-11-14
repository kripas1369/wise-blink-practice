"""Rank candidate sky fields for the SPHEREx motion search from measured archive data.

    PYTHONPATH=.:research:research/wanderers .venv/bin/python research/wanderers/select_fields.py

Stage 1 (every sampled tile): SPHEREx DR1+QR3 coverage at the tile centre (images, visits, distinct dates,
time span, detectors, deep-field collections).
Stage 2 (the best STAGE2_N tiles by coverage): Gaia DR3, CatWISE2020 and SIMBAD inside the field, and six sample
cutouts (one per detector) for the flagged-pixel fraction and the noise level.
Output: results/field_scores.csv, results/field_selection.json (all numbers and the scoring rule).

Tiles: HEALPix nside 16 (3.7° pixels) centres with |b| > 30°, sampled at random (seed 20261113) in four bands
of ecliptic latitude |β| (0-30, 30-60, 60-75, 75-90°), because the number of SPHEREx visits rises toward the
ecliptic poles and a uniform sample would contain almost no high-|β| tiles.
Excluded: within 3° of the five official targets, 1.5° of the deep survey fields in common.DEEP_FIELDS, and
1° of any binary in the Eclipse catalogue (frontend/frames/eclipse/catalog.json, read only).
"""
import concurrent.futures as cf
import csv
import json
import math

import astropy.units as u
import numpy as np
import pyvo
from astropy.coordinates import BarycentricTrueEcliptic, SkyCoord
from astropy.io import fits
from astropy_healpix import HEALPix

import common as C
from backend.app import archive
from backend.app.flags import bad_pixel_bitmask

NAME = "select_fields"
SEED = 20261113
NSIDE = 16
PER_BAND = 18
BANDS = ((0, 30), (30, 60), (60, 75), (75, 90.1))
FIELD_RADIUS_DEG = 10 / 60     # the search field: 20′ across
STAGE2_N = 15
SIMBAD_TAP = "https://simbad.harvard.edu/simbad/sim-tap"

# Score weights (sum 100). Each term is a measured quantity mapped to 0..1, written out in score().
WEIGHTS = {"visits": 25, "span": 15, "detectors": 5, "usable": 10, "noise": 5, "registration": 10,
           "uncrowded": 10, "gaia_dark": 10, "less_studied": 10}


def tiles():
    hp = HEALPix(nside=NSIDE, order="nested", frame="icrs")
    lon, lat = hp.healpix_to_lonlat(np.arange(hp.npix))
    c = SkyCoord(lon, lat, frame="icrs")
    b = c.galactic.b.deg
    beta = c.transform_to(BarycentricTrueEcliptic()).lat.deg
    ra, dec = c.ra.deg, c.dec.deg
    ok = np.abs(b) > 30
    for (tra, tdec) in C.OFFICIAL_TARGETS.values():
        ok &= C.sep_deg(ra, dec, tra, tdec) > 3
    for (tra, tdec) in C.DEEP_FIELDS.values():
        ok &= C.sep_deg(ra, dec, tra, tdec) > 1.5
    ecl = json.loads((C.HERE.parents[1] / "frontend/frames/eclipse/catalog.json").read_text())["binaries"]
    for e in ecl:
        ok &= C.sep_deg(ra, dec, e["ra"], e["dec"]) > 1
    rng = np.random.default_rng(SEED)
    chosen = []
    for lo, hi in BANDS:
        idx = np.flatnonzero(ok & (np.abs(beta) >= lo) & (np.abs(beta) < hi))
        pick = rng.choice(idx, size=min(PER_BAND, len(idx)), replace=False)
        chosen += [{"hp": int(i), "ra": round(float(ra[i]), 5), "dec": round(float(dec[i]), 5),
                    "glat": round(float(b[i]), 2), "glon": round(float(c[i].galactic.l.deg), 2),
                    "elat": round(float(beta[i]), 2), "band": f"{lo}-{int(hi)}"} for i in pick]
    return chosen, int(ok.sum())


def coverage(t):
    ims = C.images_at(t["ra"], t["dec"], f"hp{NSIDE}_{t['hp']}")
    if not ims:
        return {**t, "n_images": 0, "n_visits": 0, "n_dates": 0, "span_days": 0, "detectors": "", "deep": False}
    eps = archive.group_epochs(ims)
    mjd = np.array([im.mjd for im in ims])
    return {**t, "n_images": len(ims), "n_visits": len(eps), "n_dates": len({int(m) for m in mjd}),
            "span_days": round(float(mjd.max() - mjd.min()), 1),
            "detectors": "".join(str(d) for d in sorted({im.detector for im in ims})),
            "deep": any(im.collection.endswith("_deep") for im in ims),
            "first": min(eps, key=lambda e: e["mjd_mean"])["date"], "last": max(eps, key=lambda e: e["mjd_mean"])["date"]}


def simbad_counts(ra, dec, radius):
    svc = pyvo.dal.TAPService(SIMBAD_TAP)
    t = svc.run_sync(f"""SELECT COUNT(*) AS n, SUM(nbref) AS refs FROM basic
        WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {radius})) = 1""").to_table()
    return int(t["n"][0]), int(t["refs"][0] or 0)


def sample_cutouts(t):
    """Flagged fraction and median noise in one cutout per detector (the visit nearest the middle of the span)."""
    ims = C.images_at(t["ra"], t["dec"], f"hp{NSIDE}_{t['hp']}")
    mid = np.median([im.mjd for im in ims])
    pick = [min((im for im in ims if im.detector == d), key=lambda im: abs(im.mjd - mid), default=None)
            for d in range(1, 7)]
    pick = [p for p in pick if p is not None]
    C.retry(archive.attach_paths, pick, what="paths")
    files = archive.download_cutouts(pick, t["ra"], t["dec"], 0.05)
    flagged, noise = [], []
    for im in pick:
        p = files.get(im.did)
        if not hasattr(p, "exists"):
            continue
        with fits.open(p) as h:
            bad = (h["FLAGS"].data & bad_pixel_bitmask(h["FLAGS"].header)) != 0
            var = h["VARIANCE"].data
            flagged.append(float(bad.mean()))
            good = (~bad) & np.isfinite(var) & (var > 0)
            noise.append(float(np.median(np.sqrt(var[good]))) if good.any() else np.nan)
    return float(np.mean(flagged)) if flagged else np.nan, float(np.nanmedian(noise)) if noise else np.nan, len(flagged)


def catalogue_stats(t):
    key = f"hp{NSIDE}_{t['hp']}"
    g = C.gaia(t["ra"], t["dec"], FIELD_RADIUS_DEG, key)
    cw = C.catwise(t["ra"], t["dec"], FIELD_RADIUS_DEG, key)
    n_ref = sum(1 for s in g if s["g_mag"] is not None and s["g_mag"] < 18 and s["pmra"] is not None)
    if cw:
        x, y = C.tangent([r["ra"] for r in cw], [r["dec"] for r in cw], t["ra"], t["dec"])
        bright = np.array([(r["w1mpro"] or 99) < 16 for r in cw])
        nbr = np.array([(r["w1mpro"] or 99) < 17 for r in cw])
        # crowding among sources SPHEREx can see: a W1<16 source with a W1<17 neighbour within 2 SPHEREx pixels
        d = np.hypot(x[bright][:, None] - x[nbr][None], y[bright][:, None] - y[nbr][None])
        d[d == 0] = 1e9
        crowded = float((d.min(1) < 2 * C.PIXEL_ARCSEC).mean()) if bright.any() else np.nan
        gx, gy = C.gaia_xy_at(g, 2015.4, t["ra"], t["dec"]) if g else (np.array([]), np.array([]))
        if len(gx):
            dg = np.hypot(x[:, None] - gx[None], y[:, None] - gy[None]).min(1)
        else:
            dg = np.full(len(x), np.inf)
        dark = int((bright & (dg > 3)).sum())
        n_bright = int(bright.sum())
    else:
        crowded, dark, n_bright = np.nan, 0, 0
    nsim, refs = C.retry(simbad_counts, t["ra"], t["dec"], FIELD_RADIUS_DEG, what="SIMBAD")
    flagged, noise, ncut = sample_cutouts(t)
    return {**t, "n_gaia": len(g), "n_gaia_ref": n_ref, "n_catwise": len(cw), "n_catwise_w1_16": n_bright,
            "n_catwise_no_gaia": dark, "frac_crowded": round(crowded, 3), "n_simbad": nsim, "simbad_refs": refs,
            "frac_flagged": round(flagged, 4), "noise_median": noise, "n_sample_cutouts": ncut}


def score(rows):
    """0..1 terms (documented in the report):
    visits = min(n_visits, 10)/10; span = min(span_days, 550)/550; detectors = n_detectors/6;
    usable = 1 - frac_flagged / max(frac_flagged); noise = 1 - rank(noise)/(N-1);
    registration = min(n_gaia_ref, 60)/60 (stationary-enough Gaia stars G<18 to tie each visit down);
    uncrowded = 1 - frac_crowded (CatWISE sources with a neighbour within 2 SPHEREx pixels);
    gaia_dark = n_catwise_no_gaia / max(n_catwise_no_gaia) (W1<16 CatWISE sources with no Gaia within 3″);
    less_studied = 1 - log10(1+simbad_refs)/max(log10(1+simbad_refs)), minus 0.5 if inside a SPHEREx deep field.
    """
    fmax = max(r["frac_flagged"] for r in rows) or 1
    dmax = max(r["n_catwise_no_gaia"] for r in rows) or 1
    lmax = max(math.log10(1 + r["simbad_refs"]) for r in rows) or 1
    order = np.argsort(np.argsort([r["noise_median"] for r in rows]))
    for r, o in zip(rows, order):
        terms = {
            "visits": min(r["n_visits"], 10) / 10, "span": min(r["span_days"], 550) / 550,
            "detectors": len(r["detectors"]) / 6, "usable": 1 - r["frac_flagged"] / fmax,
            "noise": 1 - o / max(len(rows) - 1, 1), "registration": min(r["n_gaia_ref"], 60) / 60,
            "uncrowded": 1 - r["frac_crowded"], "gaia_dark": r["n_catwise_no_gaia"] / dmax,
            "less_studied": max(0.0, 1 - math.log10(1 + r["simbad_refs"]) / lmax - (0.5 if r["deep"] else 0)),
        }
        r["terms"] = {k: round(v, 3) for k, v in terms.items()}
        r["score"] = round(sum(WEIGHTS[k] * v for k, v in terms.items()), 2)
    return sorted(rows, key=lambda r: -r["score"])


def main():
    chosen, n_ok = tiles()
    C.log(NAME, f"{len(chosen)} tiles sampled from {n_ok} allowed HEALPix nside={NSIDE} pixels")
    with cf.ThreadPoolExecutor(3) as pool:
        cov = list(pool.map(lambda t: C.retry(coverage, t, what=f"coverage {t['hp']}"), chosen))
    for c in cov:
        C.log(NAME, f"hp{c['hp']} ({c['ra']},{c['dec']}) |β|={abs(c['elat'])}: {c['n_images']} images, "
                    f"{c['n_visits']} visits, {c['span_days']} d, det {c['detectors']}, deep={c['deep']}")
    usable = [c for c in cov if c["n_visits"] >= 3 and len(c["detectors"]) == 6]
    usable.sort(key=lambda c: (-min(c["n_visits"], 10), -c["span_days"]))
    stage2 = []
    for c in usable[:STAGE2_N]:
        try:
            stage2.append(catalogue_stats(c))
            s = stage2[-1]
            C.log(NAME, f"hp{c['hp']}: Gaia {s['n_gaia']} (ref {s['n_gaia_ref']}), CatWISE {s['n_catwise']}, "
                        f"no-Gaia W1<16 {s['n_catwise_no_gaia']}, crowded {s['frac_crowded']}, SIMBAD {s['n_simbad']} "
                        f"({s['simbad_refs']} refs), flagged {s['frac_flagged']}, noise {s['noise_median']:.4g}")
        except Exception as exc:
            C.log(NAME, f"hp{c['hp']}: stage 2 failed: {exc}")
    ranked = score(stage2)
    keys = ["hp", "ra", "dec", "glon", "glat", "elat", "band", "n_images", "n_visits", "n_dates", "span_days", "first",
            "last", "detectors", "deep", "n_gaia", "n_gaia_ref", "n_catwise", "n_catwise_w1_16", "n_catwise_no_gaia",
            "frac_crowded", "n_simbad", "simbad_refs", "frac_flagged", "noise_median", "score"]
    with open(C.RESULTS / "field_scores.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys + [f"term_{k}" for k in WEIGHTS])
        for r in ranked:
            w.writerow([r.get(k) for k in keys] + [r["terms"][k] for k in WEIGHTS])
    (C.RESULTS / "field_selection.json").write_text(json.dumps({
        "made_at": C.now(), "seed": SEED, "nside": NSIDE, "bands_abs_elat": BANDS, "per_band": PER_BAND,
        "n_allowed_tiles": n_ok, "field_radius_deg": FIELD_RADIUS_DEG, "weights": WEIGHTS,
        "score_rule": score.__doc__, "stage1": cov, "stage2_ranked": ranked, "top3": ranked[:3]}, indent=1, default=str))
    for r in ranked[:3]:
        C.log(NAME, f"TOP hp{r['hp']} RA {r['ra']} Dec {r['dec']} score {r['score']} terms {r['terms']}")


if __name__ == "__main__":
    main()
