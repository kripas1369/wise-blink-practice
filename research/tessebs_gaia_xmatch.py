"""Every TESS-EBs entry against the Gaia DR3 eclipsing-binary table: is the same-period Gaia EB a *different* star?

    .venv/bin/python research/tessebs_gaia_xmatch.py     -> research/out/tessebs_gaia_xmatch.json / .csv

TESS pixels are 21″, Gaia resolves 0.4″. For each TESS-EBs entry, all Gaia DR3 EBs (Mowlavi et al. 2023) within
RADIUS are found with one uploaded-table query to the ESA Gaia archive. The entry is

- "same star"       a period-matched Gaia EB lies within SAME_STAR_ARCSEC of the TIC position;
- "other star"      no period-matched Gaia EB on the TIC star, but one on another star within RADIUS;
- "no Gaia EB"      no period-matched Gaia EB nearby (most entries: Gaia's EB table is incomplete).

Period match: P_Gaia / P_TESS within PERIOD_TOL of 1, 2 or 1/2 (Gaia often finds half or double the period).
"other star" entries are candidates for a TESS eclipse listed under the wrong star.
"""
import csv
import io
import json
from pathlib import Path

import numpy as np
import pyvo
from astropy.table import Table

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).parent / "out"
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap"
RADIUS = 63.0              # arcsec, three TESS pixels
SAME_STAR_ARCSEC = 4.0     # TIC J2000 vs Gaia J2016 positions differ by proper motion x 16 yr
PERIOD_TOL = 0.002
CHUNK = 400                # rows per uploaded query; the whole table at once is aborted by the archive


def ratio(p_gaia, p_tess):
    for k in (1.0, 2.0, 0.5):
        if abs(p_gaia / p_tess / k - 1) < PERIOD_TOL:
            return k
    return None


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "cache/catalogs/tess_ebs_v1.0.csv"))
            if r["period"] and float(r["period"]) > 0]
    t = Table({"tic": np.array([int(r["tess_id"]) for r in rows]),
               "ra": np.array([float(r["ra"]) for r in rows]), "dec": np.array([float(r["dec"]) for r in rows]),
               "p": np.array([float(r["period"]) for r in rows])})
    print(f"{len(t)} TESS-EBs entries uploaded", flush=True)
    q = f"""SELECT t.tic, t.ra AS tic_ra, t.dec AS tic_dec, t.p, g.source_id, g.ra, g.dec, g.pmra, g.pmdec,
                   g.phot_g_mean_mag AS g_mag, g.bp_rp, 1.0/eb.frequency AS gaia_p, eb.global_ranking,
                   DISTANCE(POINT(t.ra, t.dec), POINT(g.ra, g.dec)) * 3600 AS sep
            FROM tap_upload.t AS t
            JOIN gaiadr3.gaia_source AS g ON 1 = CONTAINS(POINT(g.ra, g.dec), CIRCLE(t.ra, t.dec, {RADIUS / 3600}))
            JOIN gaiadr3.vari_eclipsing_binary AS eb ON eb.source_id = g.source_id"""
    svc = pyvo.dal.TAPService(GAIA_TAP)
    by_tic = {}
    n_found = 0
    for start in range(0, len(t), CHUNK):
        part = t[start:start + CHUNK]
        for attempt in range(4):
            job = svc.submit_job(q, uploads={"t": part}, maxrec=200000)
            job.run()
            try:
                job.wait(phases=["COMPLETED", "ERROR", "ABORTED"], timeout=1800)
            except pyvo.dal.DALServiceError:
                pass   # already finished
            if job.phase == "COMPLETED":
                break
            msg = getattr(job.job.errorsummary, "message", None)
            print(f"  rows {start}-{start + len(part)}: {job.phase} ({msg}), retrying", flush=True)
        else:
            raise RuntimeError(f"Gaia archive failed for rows {start}-{start + len(part)}")
        res = job.fetch_result().to_table()
        n_found += len(res)
        for r in res:
            by_tic.setdefault(int(r["tic"]), []).append(r)
        print(f"  rows {start}-{start + len(part)}: {len(res)} Gaia EBs", flush=True)
    print(f"{n_found} Gaia EBs within {RADIUS}″ of an entry", flush=True)
    out = []
    counts = {}
    for r in rows:
        tic, p = int(r["tess_id"]), float(r["period"])
        ebs = by_tic.get(tic, [])
        matched = [(e, ratio(float(e["gaia_p"]), p)) for e in ebs if np.isfinite(e["gaia_p"])]
        matched = [(e, k) for e, k in matched if k]
        same = [e for e, _ in matched if e["sep"] < SAME_STAR_ARCSEC]
        other = sorted(((e, k) for e, k in matched if e["sep"] >= SAME_STAR_ARCSEC), key=lambda x: x[0]["sep"])
        cls = "same star" if same else ("other star" if other else "no Gaia EB")
        counts[cls] = counts.get(cls, 0) + 1
        entry = {"tic": str(tic), "ra": float(r["ra"]), "dec": float(r["dec"]), "period": p, "tmag": float(r["Tmag"] or "nan"),
                 "tess_depth": float(r["prim_depth_pf"] or r["prim_depth_2g"] or "nan"), "class": cls,
                 "other": [{"source_id": str(e["source_id"]), "sep": round(float(e["sep"]), 2), "g_mag": float(e["g_mag"]),
                            "bp_rp": float(e["bp_rp"]) if np.isfinite(e["bp_rp"]) else None,
                            "gaia_p": float(e["gaia_p"]), "ratio": k, "ra": float(e["ra"]), "dec": float(e["dec"]),
                            "rank": float(e["global_ranking"])} for e, k in other]}
        out.append(entry)
    (OUT / "tessebs_gaia_xmatch.json").write_text(json.dumps({"counts": counts, "radius_arcsec": RADIUS,
                                                             "entries": out}, indent=1))
    with open(OUT / "tessebs_gaia_xmatch_other.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tic", "ra", "dec", "period", "tmag", "tess_depth", "gaia_source_id", "sep_arcsec", "gaia_g",
                    "gaia_period", "period_ratio", "gaia_rank"])
        for e in out:
            if e["class"] == "other star":
                o = e["other"][0]
                w.writerow([e["tic"], e["ra"], e["dec"], e["period"], e["tmag"], e["tess_depth"], o["source_id"],
                            o["sep"], round(o["g_mag"], 2), o["gaia_p"], o["ratio"], o["rank"]])
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
