"""CANDIDATE_CATALOG.csv: one row per sample target with identifiers, observations, data quality and outcome.

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/make_catalog.py

Inputs: data/lists/sample.csv, data/selection/simbad_xmatch.csv, data/stamps/NAME.json,
EXPERIMENTAL_RESULTS/photometry/NAME.csv, EXPERIMENTAL_RESULTS/ice/NAME.json, EXPERIMENTAL_RESULTS/population/targets.csv.
"""
import csv
import json

import numpy as np

import ice_fit as I
from purity_check import NON_YSO

ROOT = I.ROOT
LITERATURE = {
    "EC53": "Kim et al. 2026 (arXiv:2604.08769, JWST ice, no change); Lee et al. 2026 ApJ (EPISODE II); periodic protostar",
    "V1647Ori": "Gibb et al. 2006; Aspin et al. 2008 AJ 135 423; Aspin et al. 2009 ApJ 692 L67 (ice in/after outburst)",
    "SJ06135925p1743210": "SIMBAD IRAS 06110+1744 (7.3\"), 4 references: 1988IRASP.C......0J (IRAS PSC); "
                          "1989ApJS...69..651C (lunar occultation predictions); 1995ApJ...450..201C (Gem OB1 star "
                          "formation); 2007PASJ...59.1185S (H2O maser survey); no ice spectroscopy or variability study",
    "SJ22280291p6901168": "SIMBAD 2MASS J22280298+6901166 (L1221 region), 5 references: 2009ApJ...702..340Y; "
                          "2009ApJS..185..198K; 2014A&A...572A..20L; 2015ApJS..220...11D; 2019MNRAS.488..495W; "
                          "no ice spectroscopy or variability study",
}
SELECTION = {
    "VAR": "SPLICES embedded protostar, NEOWISE W2 class {cls} amplitude {amp} mag (random draw, seed 20261113)",
    "CTRL": "SPLICES embedded protostar, NEOWISE non-variable, W2-matched control for pair {pair}",
    "BGSTAR": "SPLICES MAIN background star, Av {av}, behind cloud {mc}, NEOWISE non-variable",
    "VALIDATION": "published multi-epoch ice spectra (known-answer test)",
}


def read_csv(path, key="name"):
    try:
        return {r[key]: r for r in csv.DictReader(open(path))}
    except FileNotFoundError:
        return {}


def main():
    sample = list(csv.DictReader(open(ROOT / "data" / "lists" / "sample.csv")))
    xm = read_csv(ROOT / "data" / "selection" / "simbad_xmatch.csv")
    pop = {}
    for r in csv.DictReader(open(ROOT / "EXPERIMENTAL_RESULTS" / "population" / "targets.csv")):
        pop[(r["name"], r["band"])] = r
    rows = []
    for s in sample:
        n = s["name"]
        row = {"name": n, "role": s["role"], "ra": s["ra"], "dec": s["dec"],
               "gaia_dr3_id": xm.get(n, {}).get("gaia_dr3", ""),
               "other_ids": f"AllWISE {s['designation']}" + (f"; SPLICES {s['splices_name']}" if s.get("splices_name") else "")
                            + (f"; SIMBAD {xm[n]['simbad_main_id']}" if xm.get(n, {}).get("simbad_main_id") else ""),
               "source_type": "; ".join(x for x in (s.get("class_1"), s.get("stype_ml")) if x) or s["role"],
               "w1_mag": s.get("w1", ""), "w2_mag": s.get("w2", ""), "neowise_w2var_class": s.get("w2var_class", ""),
               "neowise_w2var_amp_mag": s.get("w2varamp", ""), "av": s.get("av", ""), "cloud": s.get("mc", "")}
        meta_f = ROOT / "data" / "stamps" / f"{n}.json"
        phot_f = I.PHOT / f"{n}.csv"
        reasons = []
        if meta_f.exists():
            meta = json.loads(meta_f.read_text())
            row["n_exposures_found"] = meta["n_images_found"]
            row["n_exposures_read"] = meta["n_accepted"]
            row["data_release"] = "+".join(f"{k.replace('spherex_', '')}:{v}" for k, v in
                                           meta["sia_rows_per_collection"].items() if v)
            vers = meta.get("versions") or meta.get("version_counts") or {}
            row["l2_versions"] = ";".join(sorted(vers)) if isinstance(vers, (dict, list)) else str(vers)
        if phot_f.exists():
            ph = list(csv.DictReader(open(phot_f)))
            ok = [r for r in ph if r["status"] == "ok"]
            mjd = [float(r["mjd"]) for r in ph]
            row["mjd_first"], row["mjd_last"] = round(min(mjd), 2), round(max(mjd), 2)
            row["detectors"] = ";".join(f"D{d}:{sum(int(r['det']) == d for r in ph)}" for d in (3, 4, 5, 6))
            wl = [float(r["wl_um"]) for r in ok]
            row["wavelength_coverage_um"] = f"{min(wl):.2f}-{max(wl):.2f}" if wl else ""
            snr = [float(r["flux_jy"]) / float(r["err_jy"]) for r in ok if float(r["err_jy"]) > 0]
            row["median_snr_per_exposure"] = round(float(np.median(snr)), 1) if snr else ""
            row["median_sources_in_fit_box"] = int(np.median([int(r["n_src"]) for r in ph]))
            row["median_psf_chi2r"] = round(float(np.median([float(r["chi2r"]) for r in ok])), 1) if ok else ""
            core = [r for r in ph if r["status"] == "ok" and int(r["n_core_good"]) < I.MIN_CORE_GOOD]
            row["n_exposures_flagged_core"] = len(core)
            row["n_exposures_not_ok"] = sum(r["status"] != "ok" for r in ph)
        else:
            reasons.append("no photometry")
        for b in ("H2O", "CO2"):
            p = pop.get((n, b))
            if p:
                row[f"{b}_n_epochs"] = p["n_complete"]
                row[f"{b}_fit_chi2r"] = round(float(p["chi2r"]), 2) if p["chi2r"] else ""
                row[f"{b}_mean_depth"] = round(float(p["mean_depth"]), 4) if p.get("mean_depth") else ""
                row[f"{b}_detected"] = p.get("detected", "")
                row[f"{b}_p_change"] = f"{float(p['p_change']):.3g}" if p.get("p_change") else ""
                row[f"{b}_quality_ok"] = p["quality_ok"]
                row[f"{b}_robust_pairs"] = p.get("n_robust_pairs", "")
                if p["quality_ok"] != "True":
                    reasons.append(f"{b}: " + (f"only {p['n_complete']} complete epoch(s)" if int(p["n_complete"]) < 2
                                               else f"joint-fit chi2_red {float(p['chi2r']):.1f} > 15"))
            else:
                row[f"{b}_n_epochs"] = 0
                reasons.append(f"{b}: no complete epoch")
        x = xm.get(n, {})
        if s["role"] in ("VAR", "CTRL") and x.get("simbad_otype") in NON_YSO:
            reasons.append(f"not a protostar per SIMBAD: {x['simbad_main_id']} ({x['simbad_otype']}); "
                           "removed in the purity sensitivity check")
        if n in LITERATURE:
            row["existing_literature"] = LITERATURE[n]
        elif x.get("simbad_main_id"):
            row["existing_literature"] = (f"SIMBAD {x['simbad_main_id']} ({x['simbad_otype']}, {x['simbad_nbref']} "
                                          f"references, {x['simbad_sep_arcsec']}\"); reference list not reviewed")
        else:
            row["existing_literature"] = "no SIMBAD object within 15\" (SPLICES/AllWISE only)"
        row["selection_reason"] = SELECTION.get(s["role"], "").format(cls=s.get("w2var_class"), amp=s.get("w2varamp"),
                                                                      pair=s.get("pair"), av=s.get("av"), mc=s.get("mc"))
        row["rejection_reason"] = "; ".join(reasons)
        rows.append(row)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(ROOT / "CANDIDATE_CATALOG.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
