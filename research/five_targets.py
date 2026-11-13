"""Writes research/five_target_catalog.csv from the cross-match, coverage and catalogue-check outputs.

    PYTHONPATH=.:research .venv/bin/python research/five_targets.py
"""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from astropy.coordinates import SkyCoord
import astropy.units as u

from backend.app import eclipses as E

HERE = Path(__file__).parent
OUT = HERE / "out"

REGIONS = [
    ("R1", "179637488", "R1_lmc_tic179637488",
     "LMC bar/LH 47 OB association: crowded young field, diffuse nebular light",
     "LH 47-237 (blue supergiant; Gaia DR3 4658741684445420032, VSX BE|GCAS|SDOR|WR)",
     "OGLE-LMC-ECL-13800 (P 3.2969676 d, I depth 0.481 / 0.319 mag)",
     "Hardest case: Gaia binary 12.6\" (2 SPHEREx px) from a brighter supergiant in a crowded field; tests the "
     "all-star PSF fit where the old two-star circle method cannot work."),
    ("R2", "349156098", "R2_tic349156098",
     "Isolated field near the south ecliptic pole (beta -82 deg), few stars",
     "TIC 349156098 (G 10.2, no variable designation)",
     "ASASSN-V J071248.16-644303.5 (EA, P 1.2015 d, V 15.43-16.61)",
     "Cleanest case: Gaia binary 5 mag fainter and 40.6\" (6.5 px) away; TESS depth only 0.22%, so the TESS "
     "signal must be strongly diluted if the binary is the source."),
    ("R3", "309659126", "R3_tic309659126",
     "Deep SPHEREx coverage near the south ecliptic pole (27,783 images)",
     "TYC 8878-311-1 (VSX places ASAS J051801-6041.4 here)",
     "UCAC4 147-005376 (Gaia DR3 EB, P 0.24827 d, G 11.38)",
     "Catalogue conflict at 7.4\" (1.2 px): VSX/ASAS name the TIC star, Gaia names the neighbour; contact binary "
     "(P 0.248 d), so many eclipses per SPHEREx visit."),
    ("R4", "160195393", "R4_tic160195393",
     "North celestial polar cap (Dec +85 deg), Galactic field; deep coverage of the north ecliptic pole region",
     "TYC 4651-1759-1 (high proper motion star)",
     "ASASSN-V J171505.23+851208.0 (EA|EB, P 0.572889 d, V 12.28-12.73)",
     "Northern counterpart: Gaia binary 41\" (6.6 px) away and 1.7 mag fainter; independent of the southern deep "
     "field."),
    ("R5", "31511621", "R5_sep_tic31511621",
     "SPHEREx south ecliptic pole deep field at the LMC edge (beta -88.9 deg)",
     "MACHO 71.12422.12 (SIMBAD: EclBin)",
     "OGLE-LMC-ECL-39123 (P 2.6288690 d, I depth 0.478 / 0.233 mag); OGLE-LMC-ECL-39130 (P 2.5643685 d) 25\" away",
     "Catalogue conflict plus a drifted clock: SIMBAD/MACHO call the TIC star an eclipsing binary, OGLE puts the "
     "2.63-d binary 18.3\" away; TESS-EBs period differs from OGLE by 6e-4 d, so SPHEREx is folded on the OGLE "
     "ephemeris (phase error 0.19 on the TESS clock)."),
]


def mjd_date(mjd):
    return (datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=mjd)).date().isoformat()


def main():
    cov = json.loads((OUT / "coverage_candidates.json").read_text())
    single = {str(x["tic"]): x for x in json.loads((OUT / "misattributed_singles.json").read_text())["singles"]}
    with open(HERE.parent / "cache" / "catalogs" / "tess_ebs_v1.0.csv") as f:
        sectors = {r["tess_id"]: r["sectors"] for r in csv.DictReader(f) if r["signal_id"] == "1"}
    rows = []
    for region, tic, run, env, tic_ids, eb_ids, why in REGIONS:
        e = E.by_tess_id(tic)
        c = cov[tic]
        g = c["gaia_eb"]
        sc = SkyCoord(e.ra * u.deg, e.dec * u.deg)
        meta_path = HERE / "experimental_results" / run / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        rows.append({
            "region": region, "tic": tic, "ra_deg": round(e.ra, 6), "dec_deg": round(e.dec, 6),
            "gal_l_deg": round(sc.galactic.l.deg, 3), "gal_b_deg": round(sc.galactic.b.deg, 3),
            "ecl_lat_deg": single[tic]["ecl_lat"], "tmag": e.tmag, "tic_identifiers": tic_ids,
            "tess_period_d": round(e.period, 7), "tess_bjd0_btjd": round(e.bjd0, 5), "tess_prim_depth": round(e.prim_depth, 5),
            "tess_sec_depth": e.sec_depth and round(e.sec_depth, 5), "tess_morph": e.morph,
            "tess_phase_error_2026": c["phase_error"],
            "gaia_eb_source_id": g["source_id"], "gaia_eb_ra_deg": round(g["ra"], 6), "gaia_eb_dec_deg": round(g["dec"], 6),
            "sep_arcsec": g["sep"], "gaia_eb_g": round(g["g_mag"], 3), "gaia_eb_bp_rp": round(g["bp_rp"], 3),
            "gaia_eb_period_d": round(g["gaia_p"], 7), "gaia_eb_identifiers": eb_ids,
            "spherex_images_dr1_qr3": c["n_images"], "spherex_in_primary": c["n_primary"],
            "spherex_in_secondary": c["n_secondary"],
            "spherex_first_utc": mjd_date(c["mjd_range"][0]), "spherex_last_utc": mjd_date(c["mjd_range"][1]),
            "spherex_images_per_detector": ";".join(f"D{k}:{v}" for k, v in c["per_detector"].items()),
            "exposures_analysed": meta.get("n_exposures"), "gaia_stars_fitted": None,
            "wavelength_um": "0.75-5.0 (D1 0.75-1.09, D2 1.10-1.62, D3 1.63-2.41, D4 2.42-3.82, D5 3.83-4.41, D6 4.42-5.00)",
            "environment": env, "on_website_catalog": c["on_website_catalog"], "rationale": why,
        })
        sp = HERE / "experimental_results" / run / "stars.json"
        if sp.exists():
            rows[-1]["gaia_stars_fitted"] = len(json.loads(sp.read_text()))
        rows[-1]["tess_sectors"] = sectors.get(tic)
        sh = meta.get("shapes") or {}
        if sh:
            rows[-1]["psf_core_sigma_px_by_detector"] = ";".join(f"D{d}:{s['sigma']:.2f}" for d, s in sorted(sh.items()))
            rows[-1]["psf_coadd_chi2_by_detector"] = ";".join(f"D{d}:{s['chi2_coadd']:.0f}" for d, s in sorted(sh.items()))
    with open(HERE / "five_target_catalog.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["region"], r["tic"], r["gal_l_deg"], r["gal_b_deg"], r["sep_arcsec"], r["spherex_first_utc"],
              r["spherex_last_utc"], r["exposures_analysed"], r["gaia_stars_fitted"])


if __name__ == "__main__":
    main()
