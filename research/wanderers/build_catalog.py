"""Write the SPHEREx Infrared Wanderers Catalogue (SIWC) for one field, with evidence images.

    PYTHONPATH=.:research:research/wanderers .venv/bin/python research/wanderers/build_catalog.py NAME [--final]

Input: results/NAME/{classified,meta,detector_epochs,sources}.json and coadds.npz.
Output: results/NAME/siwc.json (same header layout as frontend/frames/eclipse/catalog.json: format, source, url,
rule, then one flat row per entry), results/NAME/siwc.csv, figures/NAME/<siwc_id>.png.
With --final the JSON and CSV are also written as results/siwc.json and results/siwc.csv.

Entries: every source of classes 1-7 (classified.py) and every checked one-visit detection. Class 0 (no significant
motion) is not an SIWC entry; those sources stay in classified.json. Fluxes: fitted PSF amplitude of each
detector-epoch co-add (MJy/sr x pixels) x pixel solid angle (6.15″)² -> µJy, median per detector band.
"""
import argparse
import csv
import json
import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from astropy.coordinates import SkyCoord  # noqa: E402
import astropy.units as u  # noqa: E402

import common as C  # noqa: E402
from backend.app.align import target_grid  # noqa: E402

PIX_SR = (C.PIXEL_ARCSEC / 206264.806) ** 2
UJY_PER_AMP = PIX_SR * 1e12
CLASS_NAMES = {1: "known moving source", 2: "known source, improved SPHEREx+CatWISE motion",
               3: "infrared mover without a convincing Gaia counterpart", 4: "unmatched moving-source candidate",
               5: "possible solar-system object", 6: "ambiguous / insufficient evidence", 7: "rejected: artifact"}
CONFIDENCE = {1: "high (independent catalogue agrees)", 2: "medium", 3: "candidate", 4: "candidate",
              5: "medium (JPL match)", 6: "low", 7: "rejected"}


def siwc_id(ra, dec):
    c = SkyCoord(ra * u.deg, dec * u.deg)
    s = c.to_string("hmsdms", sep="", precision=1, pad=True).replace(" ", "")
    return "SIWC J" + s.replace("h", "").replace("m", "").replace("s", "").replace("d", "")


def evidence_png(path, src, cls_row, meta, des, Z, visits_meta):
    ra0, dec0 = meta["ra"], meta["dec"]
    grid, size = target_grid(ra0, dec0, meta["fov_arcmin"])
    x0, y0 = src["x_px"], src["y_px"]
    h = 8
    ya, yb, xa, xb = max(0, int(y0) - h), min(size, int(y0) + h + 1), max(0, int(x0) - h), min(size, int(x0) + h + 1)
    vis = sorted({p["visit"] for p in src["points"]}) or sorted({de["visit"] for de in des})

    def visit_img(v):
        idx = [i for i, de in enumerate(des) if de["visit"] == v]
        W = sum(np.where(np.isfinite(Z["sigmas"][i]) & (Z["sigmas"][i] > 0) & ~Z["bad"][i], 1 / Z["sigmas"][i] ** 2, 0)
                for i in idx)
        S = sum(np.where(np.isfinite(Z["images"][i]) & np.isfinite(Z["sigmas"][i]) & ~Z["bad"][i],
                         Z["images"][i] / np.where(Z["sigmas"][i] > 0, Z["sigmas"][i], np.inf) ** 2, 0) for i in idx)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(W > 0, S / W, np.nan), np.where(W > 0, 1 / np.sqrt(W), np.nan)

    first, last = vis[0], vis[-1]
    A, sA = visit_img(first)
    B, sB = visit_img(last)
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.8))
    lo, hi = np.nanpercentile(np.concatenate([A[ya:yb, xa:xb].ravel(), B[ya:yb, xa:xb].ravel()]), [5, 99.5])
    date = {v["id"]: v["date"] for v in visits_meta}
    for a_, img, t in ((ax[0], A, f"visit {first} ({date.get(first)})"), (ax[1], B, f"visit {last} ({date.get(last)})")):
        a_.imshow(img[ya:yb, xa:xb], origin="lower", cmap="gray", vmin=lo, vmax=hi,
                  extent=(xa - 0.5, xb - 0.5, ya - 0.5, yb - 0.5))
        a_.set_title(t, fontsize=9)
    with np.errstate(invalid="ignore"):
        D = (B - A) / np.hypot(sA, sB)
    ax[2].imshow(D[ya:yb, xa:xb], origin="lower", cmap="RdBu_r", vmin=-6, vmax=6,
                 extent=(xa - 0.5, xb - 0.5, ya - 0.5, yb - 0.5))
    ax[2].set_title("difference (last - first), σ", fontsize=9)
    # per-visit mean registered positions -> pixel
    pts = src["points"]
    if pts:
        for v in vis:
            pv = [p for p in pts if p["visit"] == v]
            if not pv:
                continue
            w = np.array([1 / p["ex"] ** 2 for p in pv])
            mx = np.average([p["x"] for p in pv], weights=w)
            my = np.average([p["y"] for p in pv], weights=w)
            wra, wdec = C.untangent(mx, my, ra0, dec0)
            px, py = grid.world_to_pixel_values(wra, wdec)
            for a_ in ax[:3]:
                a_.plot(px, py, "o", mfc="none", mec="gold", ms=6)
        f = src.get("fit")
        if f:
            ts = np.array([min(p["year"] for p in pts), max(p["year"] for p in pts)])
            tx = f["x0"] + f["pmx"] * (ts - f["t0"])
            ty = f["y0"] + f["pmy"] * (ts - f["t0"])
            wra, wdec = C.untangent(tx, ty, ra0, dec0)
            px, py = grid.world_to_pixel_values(wra, wdec)
            for a_ in ax[:3]:
                a_.annotate("", xy=(px[1], py[1]), xytext=(px[0], py[0]),
                            arrowprops=dict(arrowstyle="->", color="cyan", lw=1.5))
            t = np.array([p["year"] for p in pts])
            for comp, col, key, pmk in (("x (east)", "C0", "x", "pmx"), ("y (north)", "C3", "y", "pmy")):
                v = np.array([p[key] for p in pts]) - (f["x0"] if key == "x" else f["y0"])
                e = np.array([p["ex" if key == "x" else "ey"] for p in pts])
                ax[3].errorbar(t, v, e, fmt="o", ms=3, color=col, label=comp, alpha=0.7)
                tt = np.linspace(t.min(), t.max(), 10)
                ax[3].plot(tt, f[pmk] * (tt - f["t0"]), color=col)
            ax[3].set_xlabel("year")
            ax[3].set_ylabel("offset from reference position (″)")
            ax[3].legend(fontsize=8)
            ax[3].set_title(f"μ = {math.hypot(f['pmx'], f['pmy']) * 1000:.0f} mas/yr, {cls_row.get('pm_sig', 0):.1f}σ",
                            fontsize=9)
    for a_ in ax[:3]:
        a_.set_xticks([])
        a_.set_yticks([])
    fig.suptitle(f"{siwc_id(cls_row['ra'], cls_row['dec'])}  class {cls_row['class']}: {CLASS_NAMES[cls_row['class']]}",
                 fontsize=10)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    d = C.RESULTS / a.name
    cl = json.loads((d / "classified.json").read_text())
    meta = json.loads((d / "meta.json").read_text())
    des = json.loads((d / "detector_epochs.json").read_text())
    srcs = {s["id"]: s for s in json.loads((d / "sources.json").read_text())}
    Z = np.load(d / "coadds.npz")
    vdate = {v["id"]: v["date"] for v in meta["visits"]}
    rows = []
    for r in cl["sources"]:
        if r["class"] == 0:
            continue
        s = srcs[r["id"]]
        pts = s["points"]
        flux = {}
        for det in sorted({p["det"] for p in pts}):
            pv = [p for p in pts if p["det"] == det]
            flux[f"D{det}"] = [round(float(np.median([p["amp"] for p in pv])) * UJY_PER_AMP, 1),
                               round(float(np.median([p["eamp"] for p in pv])) * UJY_PER_AMP / math.sqrt(len(pv)), 1)]
        wl = {f"D{de['det']}": [de["wl_min"], de["wl_max"]] for de in des if de["det"] in r["detectors"]}
        sid = siwc_id(r["ra"], r["dec"])
        png = C.FIGURES / a.name / f"{sid.replace(' ', '_')}.png"
        if r["class"] in (1, 2, 3, 4, 6):
            try:
                evidence_png(png, s, r, meta, des, Z, meta["visits"])
            except Exception as exc:
                C.log(f"catalog_{a.name}", f"figure failed for {sid}: {exc}")
                png = None
        else:
            png = None
        obs = sorted({o for p in pts for o in des[p["k"]]["obs_ids"]})
        rows.append({
            "siwc_id": sid, "field": a.name, "ra": round(r["ra"], 6), "dec": round(r["dec"], 6),
            "epoch": r.get("t0"), "pmra": r.get("pmra"), "pmdec": r.get("pmdec"), "pm_total": r.get("pm_total"),
            "pmra_err": r.get("pmra_err"), "pmdec_err": r.get("pmdec_err"), "pm_sig": r.get("pm_sig"),
            "long_baseline": r.get("long"), "motion_used": r.get("motion_used"),
            "n_dates": r["n_visits"], "dates": [vdate[v] for v in r["visits"]], "baseline_yr": r.get("baseline_yr"),
            "detectors": r["detectors"], "wavelengths_um": wl, "flux_ujy": flux, "snr_deep": r["snr"],
            "gaia": r["gaia"], "catwise": r["catwise"], "simbad": r.get("simbad"), "jpl": r.get("jpl"),
            "known_pm": r.get("known_pm"), "class": r["class"], "class_name": CLASS_NAMES[r["class"]],
            "confidence": CONFIDENCE[r["class"]], "reason": r["reason"], "checks": r["checks"],
            "short_long_z": r.get("short_long_z"), "n_obs_ids": len(obs), "obs_ids": obs,
            "evidence_png": str(png.relative_to(C.HERE)) if png else None})
    for t in cl["one_visit"]:
        rows.append({
            "siwc_id": siwc_id(t["ra"], t["dec"]), "field": a.name, "ra": round(t["ra"], 6), "dec": round(t["dec"], 6),
            "epoch": None, "pmra": None, "pmdec": None, "pm_total": None, "pmra_err": None, "pmdec_err": None,
            "pm_sig": None, "long_baseline": None, "motion_used": None, "n_dates": 1, "dates": [vdate[t["visit"]]],
            "baseline_yr": 0, "detectors": None, "wavelengths_um": None, "flux_ujy": None, "snr_deep": round(t["snr"], 1),
            "gaia": None, "catwise": None, "simbad": None, "jpl": t["jpl"], "known_pm": None, "class": t["class"],
            "class_name": CLASS_NAMES[t["class"]], "confidence": CONFIDENCE[t["class"]], "reason": t["reason"],
            "checks": {"near_bright_star": t["near_bright_star"]}, "short_long_z": None, "n_obs_ids": None,
            "obs_ids": None, "evidence_png": None})
    rows.sort(key=lambda r: (r["class"] if r["class"] in (3, 4) else 10 + r["class"], -(r["pm_sig"] or 0)))
    summ = cl["summary"]
    v = meta["visits"]
    gal = SkyCoord(meta["ra"] * u.deg, meta["dec"] * u.deg).galactic
    from astropy.coordinates import BarycentricTrueEcliptic
    ecl = SkyCoord(meta["ra"] * u.deg, meta["dec"] * u.deg).transform_to(BarycentricTrueEcliptic())
    out = {
        "format": "spherex-siwc/1-catalog",
        "source": "SPHEREx DR1 + QR3 spectral images (NASA/IPAC IRSA), Gaia DR3, CatWISE2020, JPL SBIdent, SIMBAD; "
                  "measured by this project (research/wanderers)",
        "url": "https://irsa.ipac.caltech.edu/Missions/spherex.html",
        "rule": (f"Sources detected at S/N>5 in the all-epoch co-add of a {meta['fov_arcmin']}′ field; positions per "
                 f"(visit, detector) registered on Gaia DR3; listed if motion >= {summ['calibration']['threshold_sigma']}σ "
                 "(errors calibrated on Gaia stars) over >= 3 visits, or >= 5σ against CatWISE2020 (2015.4), or seen in "
                 "one visit only. Classes 1-7: research/wanderers/classify.py. Candidates are not confirmed discoveries."),
        "made_at": C.now(),
        "field": {"name": a.name, "ra": meta["ra"], "dec": meta["dec"], "fov_arcmin": meta["fov_arcmin"],
                  "glon": round(gal.l.deg, 3), "glat": round(gal.b.deg, 3), "elon": round(ecl.lon.deg, 3),
                  "elat": round(ecl.lat.deg, 3), "n_visits": meta["n_visits"],
                  "first_date": min(x["date"] for x in v), "last_date": max(x["date"] for x in v),
                  "n_cutouts_used": meta["n_cutouts_used"], "n_detector_epochs": meta["n_detector_epochs"],
                  "detectors": sorted({de["det"] for de in des}), "collections": meta["collections"]},
        "calibration": summ["calibration"], "counts": summ, "n_entries": len(rows), "sources": rows}
    (d / "siwc.json").write_text(json.dumps(out, indent=1, default=float))
    flat_keys = ["siwc_id", "field", "ra", "dec", "epoch", "pmra", "pmdec", "pm_total", "pmra_err", "pmdec_err",
                 "pm_sig", "motion_used", "n_dates", "baseline_yr", "snr_deep", "class", "class_name", "confidence",
                 "reason", "n_obs_ids", "evidence_png"]
    with open(d / "siwc.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(flat_keys + ["dates", "detectors", "gaia_id", "gaia_sep", "gaia_pmra", "gaia_pmdec", "catwise_name",
                                "catwise_sep", "catwise_pmra", "catwise_pmdec", "long_pmra", "long_pmdec", "long_err",
                                "long_sig", "jpl", "simbad_nearest", "flux_ujy"])
        for r in rows:
            g, c, lb = r["gaia"] or {}, r["catwise"] or {}, r["long_baseline"] or {}
            sim = (r["simbad"] or {}).get("rows") or []
            w.writerow([r[k] for k in flat_keys] + [
                ";".join(r["dates"]), ";".join(map(str, r["detectors"] or [])), g.get("source_id"), g.get("sep_arcsec"),
                g.get("pmra"), g.get("pmdec"), c.get("source_name"), c.get("sep_arcsec"), c.get("pmra"), c.get("pmdec"),
                lb.get("pmra"), lb.get("pmdec"), lb.get("err"), lb.get("sig"), json.dumps(r["jpl"]) if r["jpl"] else "",
                f"{sim[0]['main_id']} ({sim[0]['otype']}, {sim[0]['sep_arcsec']}″)" if sim else "",
                json.dumps(r["flux_ujy"]) if r["flux_ujy"] else ""])
    if a.final:
        (C.RESULTS / "siwc.json").write_text((d / "siwc.json").read_text())
        (C.RESULTS / "siwc.csv").write_text((d / "siwc.csv").read_text())
    C.log(f"catalog_{a.name}", f"{len(rows)} SIWC entries; classes "
                               f"{ {c_: sum(r['class'] == c_ for r in rows) for c_ in range(1, 8)} }")


if __name__ == "__main__":
    main()
