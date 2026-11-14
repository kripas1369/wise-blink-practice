"""Cross-match, check and classify every source measured by astrometry.py in one field.

    PYTHONPATH=.:research:research/wanderers .venv/bin/python research/wanderers/classify.py NAME [--jpl-max 40]

Inputs: results/NAME/{meta,sources,transients,controls,detector_epochs}.json
Output: results/NAME/classified.json (every source, its matches, checks and class) and results/NAME/summary.json.

Error calibration (negative control, astrometry.py): every Gaia reference star is measured with visits registered on
the other half of the references, and its SPHEREx motion compared with Gaia's. ERR_SCALE = median(z) / 1.1774
(the median of a 2-D unit Gaussian's length); motion errors of all sources are multiplied by max(1, ERR_SCALE).
The motion threshold is max(5, the largest scaled control z): no reference star would pass it.

Long baseline: CatWISE2020 positions refer to MJD 57170 (2015.4). For each source, the SPHEREx position at its own
reference epoch t0 minus the CatWISE PM-fit position, divided by (t0 - 2015.4), is its long-baseline motion. The
positional systematic between the two catalogues (different PSFs, wavelengths, blends) is measured on stationary
Gaia stars (|pm| < 10 mas/yr) and added in quadrature.

Classes (prompt Part 5F):
 1 known moving source            significant motion, Gaia or CatWISE lists a consistent motion
 2 known source, improved motion  no Gaia motion; CatWISE match; SPHEREx+CatWISE motion significant and more precise
                                  than CatWISE's own
 3 IR mover, no convincing Gaia   significant motion, no Gaia counterpart, CatWISE counterpart whose own motion is
                                  insignificant or inconsistent
 4 unmatched moving candidate     significant SPHEREx-only motion, no Gaia and no CatWISE counterpart
 5 possible solar-system object   seen in one visit only and a JPL known object passes within 2 px
 6 ambiguous / insufficient       motion 3σ..threshold, or < 3 visits, or blended / extended / one-visit without JPL match
 7 artifact                       fails an instrumental check (single detector, flagged core, detector groups disagree,
                                  bright-star halo)
 0 not a candidate                no significant motion (kept in the full table, not in SIWC)
"""
import argparse
import concurrent.futures as cf
import json
import math

import numpy as np
import pyvo
from astropy.io import fits

import common as C
from backend.app import known_objects as KO

KO.CACHE = C.CACHE / "jpl"
SIMBAD_TAP = "https://simbad.harvard.edu/simbad/sim-tap"
RAYLEIGH_MEDIAN = math.sqrt(2 * math.log(2))
GAIA_R = 4.0          # arcsec, at least
CATWISE_R = 6.0
PREDECESSOR_R = 60.0
BRIGHT_W1 = 8.0
BRIGHT_RADIUS_PX = 6
CW_EPOCH = 2015.4
STATE_KEYS = ("X_SC", "Y_SC", "Z_SC", "VX_SC", "VY_SC", "VZ_SC")


def load(name):
    d = C.RESULTS / name
    return {k: json.loads((d / f"{k}.json").read_text())
            for k in ("meta", "sources", "transients", "controls", "detector_epochs")}


def observer_for(de_meta, visit, mjd_target):
    """SPHEREx geocentric state from the header of the cached exposure closest in time within this visit."""
    exps = [e for de in de_meta if de["visit"] == visit for e in de.get("exposures", [])]
    if not exps:
        return {"available": False, "reason": "no exposure list"}
    e = min(exps, key=lambda e: abs(e["mjd"] - mjd_target))
    p = C.CACHE / "cutouts" / e["file"]
    h = fits.getheader(p, "IMAGE")
    if any(k not in h for k in STATE_KEYS):
        return {"available": False, "reason": "no spacecraft state in header"}
    mj = [x["mjd"] for x in exps]
    return {"available": True, "mjd": float(h["MJD-AVG"]), "obs_id": e["obs_id"],
            "xyz_km": [float(h[k]) for k in STATE_KEYS[:3]], "vxyz_kms": [float(h[k]) for k in STATE_KEYS[3:]],
            "system": f"{h.get('XYZ_SC_SYSTEM', '?')} (axes assumed ICRF)",
            "exposures_span_hours": round((max(mj) - min(mj)) * 24, 2)}


def jpl_check(ra, dec, de_meta, visit, mid_only=False):
    """Ask JPL at the start, middle and end of the visit (middle only for multi-visit movers, which an asteroid cannot
    mimic across months); 'match' if a known object is within 2 px at any of them."""
    exps = sorted(e["mjd"] for de in de_meta if de["visit"] == visit for e in de.get("exposures", []))
    if not exps:
        return {"outcome": "unavailable", "reason": "no exposures"}
    times = [exps[len(exps) // 2]] if mid_only else sorted({exps[0], exps[len(exps) // 2], exps[-1]})
    answers = []
    for t in times:
        obs = observer_for(de_meta, visit, t)
        try:
            answers.append(KO.check({"ra": ra, "dec": dec}, obs, C.PIXEL_ARCSEC))
        except Exception as exc:
            answers.append({"outcome": "unavailable", "reason": str(exc)})
    outs = [a["outcome"] for a in answers]
    outcome = "match" if "match" in outs else ("no_match" if all(o == "no_match" for o in outs) else
                                                ("partial" if "no_match" in outs else "unavailable"))
    matches = [m for a in answers for m in a.get("matches", [])]
    return {"outcome": outcome, "times_mjd": times, "per_time": outs, "matches": matches[:5],
            "pass_used": [a.get("pass_used") for a in answers]}


def simbad_near(ra, dec, r_arcsec=15):
    try:
        svc = pyvo.dal.TAPService(SIMBAD_TAP)
        t = svc.run_sync(f"""SELECT main_id, otype, ra, dec, pmra, pmdec, nbref FROM basic
            WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {r_arcsec / 3600})) = 1""").to_table()
        out = []
        for r in t:
            d = C.sep_deg(ra, dec, float(r["ra"]), float(r["dec"])) * 3600
            out.append({"main_id": str(r["main_id"]), "otype": str(r["otype"]), "sep_arcsec": round(float(d), 1),
                        "pmra": None if np.ma.is_masked(r["pmra"]) else float(r["pmra"]),
                        "pmdec": None if np.ma.is_masked(r["pmdec"]) else float(r["pmdec"]),
                        "nbref": int(r["nbref"])})
        return {"ok": True, "rows": sorted(out, key=lambda x: x["sep_arcsec"])}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--jpl-max", type=int, default=40)
    a = ap.parse_args()
    name = a.name
    tag = f"classify_{name}"
    D = load(name)
    meta, sources, transients, controls, de_meta = (D[k] for k in ("meta", "sources", "transients", "controls",
                                                                   "detector_epochs"))
    ra0, dec0 = meta["ra"], meta["dec"]
    rad = meta["fov_arcmin"] / 60 / 2 * math.sqrt(2) + 0.02

    # --- error calibration from the negative control
    z = np.array([c["resid_sig"] for c in controls if c["n_visits"] >= 2])
    err_scale = float(np.median(z) / RAYLEIGH_MEDIAN) if len(z) >= 5 else 1.0
    k = max(1.0, err_scale)
    zs = z / k
    threshold = float(max(5.0, zs.max() if len(zs) else 5.0))
    calib = {"n_controls": int(len(z)), "err_scale": round(err_scale, 3), "applied_scale": round(k, 3),
             "threshold_sigma": round(threshold, 2), "max_control_z_scaled": round(float(zs.max()), 2) if len(zs) else None,
             "frac_controls_above_5": round(float(np.mean(zs >= 5)), 4) if len(zs) else None,
             "frac_controls_above_3": round(float(np.mean(zs >= 3)), 4) if len(zs) else None}
    C.log(tag, f"calibration: {calib}")

    # --- catalogues
    gaia = C.gaia(ra0, dec0, rad, name)
    cw = C.catwise(ra0, dec0, rad, name)
    gx16, gy16 = C.tangent([g["ra"] for g in gaia], [g["dec"] for g in gaia], ra0, dec0)
    gpm = np.array([[g["pmra"] or 0.0, g["pmdec"] or 0.0] for g in gaia]) / 1000.0
    cwx, cwy = C.tangent([r["ra_pm"] if r["ra_pm"] is not None else r["ra"] for r in cw],
                         [r["dec_pm"] if r["dec_pm"] is not None else r["dec"] for r in cw], ra0, dec0)
    cwpm = np.array([[r["pmra"] or 0.0, r["pmdec"] or 0.0] for r in cw])
    cwepm = np.array([[r["sigpmra"] or 9.0, r["sigpmdec"] or 9.0] for r in cw])
    cwepos = np.array([math.hypot(r["sigra_pm"] or 1.0, r["sigdec_pm"] or 1.0) / math.sqrt(2) for r in cw])
    w1 = np.array([r["w1mpro"] if r["w1mpro"] is not None else 99 for r in cw])
    bx, by = cwx[w1 < BRIGHT_W1], cwy[w1 < BRIGHT_W1]

    def gaia_at(t):
        return gx16 + gpm[:, 0] * (t - 2016.0), gy16 + gpm[:, 1] * (t - 2016.0)

    def nearest(x, y, X, Y):
        if not len(X):
            return -1, np.inf
        d = np.hypot(X - x, Y - y)
        j = int(np.argmin(d))
        return j, float(d[j])

    # --- long-baseline systematic floor from stationary Gaia stars
    offs = []
    for s in sources:
        f = s.get("fit")
        if not f or s["snr"] < 10:
            continue
        gx, gy = gaia_at(f["t0"])
        j, d = nearest(f["x0"], f["y0"], gx, gy)
        if j < 0 or d > GAIA_R or gaia[j]["pmra"] is None or math.hypot(gaia[j]["pmra"], gaia[j]["pmdec"]) > 10:
            continue
        cj, cd = nearest(gx16[j], gy16[j], cwx, cwy)
        if cj < 0 or cd > 3:
            continue
        dt = f["t0"] - CW_EPOCH
        offs.append((f["x0"] - cwx[cj] - gpm[j, 0] * dt, f["y0"] - cwy[cj] - gpm[j, 1] * dt,
                     math.hypot(f["ex0"], f["ey0"]) / math.sqrt(2), cwepos[cj]))
    offs = np.array(offs) if offs else np.zeros((0, 4))
    if len(offs) >= 5:
        r = np.hypot(offs[:, 0], offs[:, 1]) / math.sqrt(2)
        stat = np.sqrt(np.median(offs[:, 2] ** 2 + offs[:, 3] ** 2))
        robust = 1.4826 * np.median(np.abs(np.concatenate([offs[:, 0], offs[:, 1]])))
        lb_floor = float(math.sqrt(max(robust ** 2 - stat ** 2, 0.0)))
        lb_median_offset = [float(np.median(offs[:, 0])), float(np.median(offs[:, 1]))]
    else:
        lb_floor, lb_median_offset, robust = 1.0, [0.0, 0.0], float("nan")
    calib.update({"long_baseline_n_stars": int(len(offs)), "long_baseline_floor_arcsec": round(lb_floor, 3),
                  "long_baseline_robust_scatter_arcsec": round(float(robust), 3),
                  "long_baseline_median_offset_arcsec": [round(v, 3) for v in lb_median_offset]})
    C.log(tag, f"long-baseline floor {lb_floor:.3f}″ from {len(offs)} stationary Gaia stars")

    out = []
    for s in sources:
        row = {"id": s["id"], "ra": s["ra"], "dec": s["dec"], "snr": round(s["snr"], 1), "n_points": s["n_points"],
               "visits": s["visits"], "detectors": s["detectors"], "checks": {}, "notes": []}
        f = s.get("fit")
        t_ref = f["t0"] if f else float(np.mean([de["year"] for de in de_meta]))
        x0, y0 = (f["x0"], f["y0"]) if f else C.tangent(s["ra"], s["dec"], ra0, dec0)
        x0, y0 = float(x0), float(y0)
        epos = math.hypot(f["ex0"], f["ey0"]) / math.sqrt(2) if f else C.PIXEL_ARCSEC / 2
        # Gaia
        gx, gy = gaia_at(t_ref)
        j, d = nearest(x0, y0, gx, gy)
        rg = max(GAIA_R, 3 * epos)
        row["gaia"] = None
        if j >= 0 and d <= rg:
            g = gaia[j]
            row["gaia"] = {"source_id": g["source_id"], "sep_arcsec": round(d, 2), "g_mag": g["g_mag"],
                           "pmra": g["pmra"], "pmdec": g["pmdec"], "parallax": g["parallax"]}
        row["gaia_nearest_arcsec"] = round(d, 2) if j >= 0 else None
        # CatWISE (moved with its own motion when significant)
        cwx_t = cwx + np.where(np.abs(cwpm[:, 0]) > 3 * cwepm[:, 0], cwpm[:, 0], 0) * (t_ref - CW_EPOCH)
        cwy_t = cwy + np.where(np.abs(cwpm[:, 1]) > 3 * cwepm[:, 1], cwpm[:, 1], 0) * (t_ref - CW_EPOCH)
        cj, cd = nearest(x0, y0, cwx_t, cwy_t)
        row["catwise"] = None
        if cj >= 0 and cd <= max(CATWISE_R, 3 * epos):
            r_ = cw[cj]
            row["catwise"] = {"source_name": r_["source_name"], "sep_arcsec": round(cd, 2), "w1mpro": r_["w1mpro"],
                              "w2mpro": r_["w2mpro"], "pmra": r_["pmra"], "pmdec": r_["pmdec"],
                              "sigpmra": r_["sigpmra"], "sigpmdec": r_["sigpmdec"], "ab_flags": r_["ab_flags"],
                              "cc_flags": r_["cc_flags"], "nb": r_["nb"]}
        row["catwise_nearest_arcsec"] = round(cd, 2) if cj >= 0 else None
        # bright-star proximity
        if len(bx):
            row["checks"]["near_bright_star"] = bool(np.min(np.hypot(bx - x0, by - y0)) < BRIGHT_RADIUS_PX * C.PIXEL_ARCSEC
                                                     and (row["catwise"] is None or (row["catwise"]["w1mpro"] or 99) >= BRIGHT_W1))
        else:
            row["checks"]["near_bright_star"] = False
        row["checks"]["single_detector"] = len(s["detectors"]) <= 1
        pts = s["points"]
        row["checks"]["flagged_core"] = bool(pts and np.median([p.get("flag_frac", 0) for p in pts]) > 0.5) \
            if pts and "flag_frac" in pts[0] else False
        row["checks"]["blended"] = bool(pts and np.mean([p.get("n_neighbours", 0) > 0 for p in pts]) > 0.5) \
            if pts and "n_neighbours" in pts[0] else False
        row["n_visits"] = len(s["visits"])
        if f:
            pmx, pmy = f["pmx"], f["pmy"]
            epx, epy = f["epmx"] * k, f["epmy"] * k
            sig = math.hypot(pmx / epx, pmy / epy)
            row.update({"t0": round(t_ref, 4), "pmra": round(pmx * 1000, 1), "pmdec": round(pmy * 1000, 1),
                        "pmra_err": round(epx * 1000, 1), "pmdec_err": round(epy * 1000, 1),
                        "pm_total": round(math.hypot(pmx, pmy) * 1000, 1), "pm_sig": round(sig, 2),
                        "pos_err_arcsec": round(epos, 3), "chi2_stat": round(f["chi2_stat"], 1),
                        "chi2_move": round(f["chi2_move"], 1), "dof_move": f["dof_move"],
                        "delta_chi2": round(f["delta_chi2"], 1)})
            yrs = [p["year"] for p in pts]
            row["baseline_yr"] = round(max(yrs) - min(yrs), 3)
            # detector-group consistency
            fs, fl = s.get("fit_short"), s.get("fit_long")
            if fs and fl:
                dz = math.hypot((fs["pmx"] - fl["pmx"]) / math.hypot(fs["epmx"], fl["epmx"]) / k,
                                (fs["pmy"] - fl["pmy"]) / math.hypot(fs["epmy"], fl["epmy"]) / k)
                row["short_long_z"] = round(dz, 2)
                row["checks"]["detector_groups_disagree"] = dz > 4
            else:
                row["checks"]["detector_groups_disagree"] = False
            # long baseline with CatWISE
            if row["catwise"] is not None:
                dt = t_ref - CW_EPOCH
                ex = math.sqrt(epos ** 2 + cwepos[cj] ** 2 + lb_floor ** 2)
                lx = (x0 - cwx[cj] - lb_median_offset[0]) / dt
                ly = (y0 - cwy[cj] - lb_median_offset[1]) / dt
                row["long"] = {"pmra": round(lx * 1000, 1), "pmdec": round(ly * 1000, 1),
                               "err": round(ex / dt * 1000, 1), "sig": round(math.hypot(lx, ly) / (ex / dt), 2),
                               "baseline_yr": round(dt, 2)}
        out.append(row)

    # --- PSF-fit quality relative to sources of similar brightness (a Gaussian PSF fits bright stars worse)
    def med_chi2(sid):
        pts = by_id[sid]["points"]
        return float(np.median([p["chi2"] for p in pts])) if pts and "chi2" in pts[0] else np.nan
    by_id = {s["id"]: s for s in sources}
    ref = np.array([(math.log10(r["snr"]), med_chi2(r["id"])) for r in out
                    if r["gaia"] is not None and not r["checks"].get("blended") and np.isfinite(med_chi2(r["id"]))])
    for r in out:
        c2 = med_chi2(r["id"])
        if len(ref) >= 10 and np.isfinite(c2):
            near = ref[np.abs(ref[:, 0] - math.log10(r["snr"])) < 0.3, 1]
            base = float(np.median(near)) if len(near) >= 5 else float(np.median(ref[:, 1]))
            r["chi2_ratio"] = round(c2 / base, 2)
            r["checks"]["poor_fit"] = c2 > 3 * base
        else:
            r["checks"]["poor_fit"] = bool(np.isfinite(c2) and c2 > 4)

    # --- long-baseline error calibration on Gaia stars with Gaia motions (same rule as the SPHEREx-only motions)
    zl = []
    for r in out:
        g = r["gaia"]
        if r.get("long") and g and g["pmra"] is not None and not r["checks"]["blended"] and not r["checks"]["poor_fit"]:
            e = r["long"]["err"]
            zl.append(math.hypot((r["long"]["pmra"] - g["pmra"]) / e, (r["long"]["pmdec"] - g["pmdec"]) / e))
    zl = np.array(zl)
    l_scale = max(1.0, float(np.median(zl) / RAYLEIGH_MEDIAN)) if len(zl) >= 5 else 1.0
    l_thr = float(max(5.0, (zl / l_scale).max())) if len(zl) else 5.0
    # sources without Gaia (at high latitude mostly galaxies, whose SPHEREx and WISE centroids can differ): their own
    # median z sets their error scale; true movers are rare, so the median is a robust reference
    zn = np.array([r["long"]["sig"] for r in out if r.get("long") and r["gaia"] is None
                   and not r["checks"]["blended"] and not r["checks"]["poor_fit"]])
    n_scale = max(l_scale, float(np.median(zn) / RAYLEIGH_MEDIAN)) if len(zn) >= 10 else l_scale
    for r in out:
        if r.get("long"):
            s_ = l_scale if r["gaia"] is not None else n_scale
            r["long"]["err"] = round(r["long"]["err"] * s_, 1)
            r["long"]["sig"] = round(r["long"]["sig"] / s_, 2)
            r["long"]["err_scale"] = round(s_, 3)
    calib.update({"long_n_gaia_checks": int(len(zl)), "long_err_scale": round(l_scale, 3),
                  "long_threshold_sigma": round(l_thr, 2), "long_n_no_gaia": int(len(zn)),
                  "long_err_scale_no_gaia": round(n_scale, 3)})
    C.log(tag, f"long-baseline calibration: {len(zl)} Gaia stars, scale {l_scale:.2f}, threshold {l_thr:.2f}σ; "
               f"{len(zn)} non-Gaia sources, scale {n_scale:.2f}")

    # --- classification
    for row in out:
        cls, why = 0, "no significant motion"
        sig = row.get("pm_sig", 0.0)
        lsig = row.get("long", {}).get("sig", 0.0) if row.get("long") else 0.0
        ck = row["checks"]
        artifact = [k_ for k_ in ("single_detector", "flagged_core", "detector_groups_disagree", "near_bright_star")
                    if ck.get(k_)]
        g = row["gaia"]
        c = row["catwise"]
        moving_int = sig >= threshold and row["n_visits"] >= 3
        moving_long = lsig >= l_thr
        if g is None:
            moving_long = lsig >= 5.0          # non-Gaia sources: errors already scaled on their own population
        if moving_int or moving_long:
            use = ("SPHEREx", row["pmra"], row["pmdec"], row["pmra_err"], row["pmdec_err"]) if moving_int else \
                ("SPHEREx+CatWISE", row["long"]["pmra"], row["long"]["pmdec"], row["long"]["err"], row["long"]["err"])
            row["motion_used"] = use[0]

            def zdiff(p, q):
                return math.hypot((p[1] - q[1]) / math.hypot(p[3], q[3]), (p[2] - q[2]) / math.hypot(p[4], q[4]))
            # independent measurements of the same motion must agree
            if moving_long and not moving_int and "pmra" in row:
                row["long_vs_spherex_z"] = round(zdiff(use, ("SPHEREx", row["pmra"], row["pmdec"], row["pmra_err"],
                                                             row["pmdec_err"])), 2)
            cw_pm = None
            if c and c["pmra"] is not None and c["sigpmra"] and c["sigpmdec"]:
                cw_pm = ("CatWISE2020", c["pmra"] * 1000, c["pmdec"] * 1000, c["sigpmra"] * 1000, c["sigpmdec"] * 1000)
                row["catwise_pm_sig"] = round(math.hypot(cw_pm[1] / cw_pm[3], cw_pm[2] / cw_pm[4]), 2)
                row["vs_catwise_z"] = round(zdiff(use, cw_pm), 2)
            if artifact:
                cls, why = 7, "fails: " + ", ".join(artifact)
            elif ck.get("blended") or ck.get("poor_fit"):
                cls, why = 6, "significant motion but blended or poor PSF fit"
            elif row.get("long_vs_spherex_z", 0) > 3:
                cls, why = 6, f"CatWISE-anchored motion disagrees with the SPHEREx-only fit (z={row['long_vs_spherex_z']})"
            elif g and g["pmra"] is not None:
                dz = zdiff(use, ("Gaia DR3", g["pmra"], g["pmdec"], 0.5, 0.5))
                row["known_pm"] = {"source": "Gaia DR3", "pmra": g["pmra"], "pmdec": g["pmdec"], "z": round(dz, 2)}
                cls, why = (1, f"motion agrees with Gaia DR3 (z={dz:.1f})") if dz <= 3 else \
                    (6, f"Gaia counterpart but motion disagrees with Gaia DR3 (z={dz:.1f})")
            elif g:
                cls, why = 6, "Gaia counterpart without a Gaia motion; SPHEREx motion significant"
            elif cw_pm is not None:
                row["known_pm"] = {"source": "CatWISE2020", "pmra": cw_pm[1], "pmdec": cw_pm[2],
                                   "z": row["vs_catwise_z"]}
                if row["vs_catwise_z"] > 3:
                    cls, why = 6, (f"motion contradicts CatWISE's own measurement (z={row['vs_catwise_z']}); "
                                   "likely a centroid difference (extended or blended source)")
                elif row["catwise_pm_sig"] >= 5:
                    cls, why = (2, "no Gaia counterpart; known CatWISE mover; SPHEREx motion agrees and is more precise") \
                        if math.hypot(use[3], use[4]) < math.hypot(cw_pm[3], cw_pm[4]) else \
                        (1, "no Gaia counterpart; motion agrees with CatWISE2020")
                else:
                    cls, why = 3, ("significant motion; no Gaia counterpart; CatWISE counterpart's own motion is "
                                   "consistent but not significant")
            elif c is not None:
                cls, why = 3, "significant motion; no Gaia counterpart; CatWISE counterpart without a motion"
            else:
                cls, why = 4, "significant SPHEREx motion; no Gaia or CatWISE counterpart"
        elif row.get("pm_sig") is not None and 3 <= sig < threshold and not (g and g["pmra"] is not None) and row["n_visits"] >= 3:
            cls, why = 6, f"motion {sig:.1f}σ: between 3σ and the {threshold:.1f}σ threshold"
        elif "pm_sig" not in row and (g is not None or c is not None):
            cls, why = 0, "catalogued source with fewer than 2 measurable visits"
        elif "pm_sig" not in row and row["n_visits"] == 0:
            cls, why = 0, "no usable per-visit position (edge, saturation or flagged pixels)"
        elif "pm_sig" not in row and row["n_visits"] == 1:
            cls, why = 6, "uncatalogued; measurable in one visit only"
        row["class"], row["reason"] = cls, why
        row["artifact_checks_failed"] = artifact

    # --- one-visit detections: JPL, then class 5 / 6 / 7
    for row in out:   # uncatalogued deep-co-add sources measurable in one visit: same JPL test as one-visit detections
        if row["class"] == 6 and row["reason"].startswith("uncatalogued; measurable in one visit"):
            j = jpl_check(row["ra"], row["dec"], de_meta, row["visits"][0])
            row["jpl"] = j
            if j["outcome"] == "match":
                row["class"], row["reason"] = 5, "one visit only; a JPL known object within 2 px"
    trans_rows = []
    chosen = sorted(transients, key=lambda t: -t["snr"])[:a.jpl_max]
    with cf.ThreadPoolExecutor(3) as pool:
        jpls = list(pool.map(lambda t: jpl_check(t["ra"], t["dec"], de_meta, t["visit"]), chosen))
    for t, jpl in zip(chosen, jpls):
        x, y = C.tangent(t["ra"], t["dec"], ra0, dec0)
        near_b = bool(len(bx) and np.min(np.hypot(bx - x, by - y)) < BRIGHT_RADIUS_PX * C.PIXEL_ARCSEC)
        cls = 5 if jpl["outcome"] == "match" else (7 if near_b else 6)
        why = {5: "one visit only; a JPL known object within 2 px", 7: "one visit only, next to a bright star",
               6: "one visit only; no JPL match (asteroid not in JPL, artifact, or variable source)"}[cls]
        trans_rows.append({**t, "jpl": jpl, "near_bright_star": near_b, "class": cls, "reason": why})
        C.log(tag, f"one-visit S/N {t['snr']:.1f} at {t['ra']:.5f},{t['dec']:+.5f} v{t['visit']}: JPL {jpl['outcome']}")

    # --- JPL for candidates (classes 3, 4); SIMBAD for every moving entry
    for row in out:
        if row["class"] in (3, 4):
            with cf.ThreadPoolExecutor(3) as pool:
                res = list(pool.map(lambda v: jpl_check(row["ra"], row["dec"], de_meta, v, mid_only=True)["outcome"],
                                    row["visits"]))
            row["jpl"] = {f"v{v}": o for v, o in zip(row["visits"], res)}
        if row["class"] in (1, 2, 3, 4) or (row["class"] == 6 and row.get("motion_used")):
            row["simbad"] = simbad_near(row["ra"], row["dec"])

    counts = {str(c_): sum(r["class"] == c_ for r in out) for c_ in range(8)}
    counts_t = {str(c_): sum(r["class"] == c_ for r in trans_rows) for c_ in range(8)}
    summary = {"name": name, "made_at": C.now(), "calibration": calib, "n_sources": len(out),
               "n_with_motion_fit": sum("pm_sig" in r for r in out),
               "n_gaia_matched": sum(r["gaia"] is not None for r in out),
               "n_catwise_matched": sum(r["catwise"] is not None for r in out),
               "n_unmatched_both": sum(r["gaia"] is None and r["catwise"] is None for r in out),
               "class_counts_sources": counts, "n_one_visit": len(transients), "n_one_visit_checked": len(trans_rows),
               "class_counts_one_visit": counts_t, "n_gaia_field": len(gaia), "n_catwise_field": len(cw)}
    d = C.RESULTS / name
    (d / "classified.json").write_text(json.dumps({"summary": summary, "sources": out, "one_visit": trans_rows},
                                                  indent=1, default=float))
    (d / "summary.json").write_text(json.dumps(summary, indent=1))
    C.log(tag, json.dumps(summary))


if __name__ == "__main__":
    main()
