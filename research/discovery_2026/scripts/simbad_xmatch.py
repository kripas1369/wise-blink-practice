"""Identifier cross-match of the sample and a positional check against the Karambelkar et al. 2026 SPHEREx transient
sample.

    PYTHONPATH=.:research:research/discovery_2026/scripts .venv/bin/python research/discovery_2026/scripts/simbad_xmatch.py

* Gaia DR3: ESA Gaia archive TAP, nearest source within 2" of the AllWISE position (Gaia epoch 2016 vs AllWISE 2010;
  proper motions of these distant embedded sources are far below 2" over 6 yr).
* SIMBAD (CDS TAP, falling back to the Harvard mirror), nearest object within 15" (IRAS-only identifications have
  positional errors of several arcsec): main id, object type, number of references, identifiers, separation. If no
  server answers the columns are left empty and `simbad_status` records it; otherwise it records the server used.
* Karambelkar et al. 2026 (ApJL 1000 L8) objects: positions from that paper or the discovery papers; any sample target
  within 60" is an overlap.

Output: data/selection/simbad_xmatch.csv, data/selection/karambelkar_check.json
"""
import csv
import json
import time
from datetime import datetime, timezone
from io import StringIO

import numpy as np
import requests
from astropy.coordinates import SkyCoord
import astropy.units as u

import ice_fit as I

SIMBAD_TAPS = ["https://simbad.cds.unistra.fr/simbad/sim-tap/sync", "https://simbad.harvard.edu/simbad/sim-tap/sync"]
SIMBAD_RADIUS = 15.0
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
SAMPLE = I.ROOT / "data" / "lists" / "sample.csv"
SEL = I.ROOT / "data" / "selection"
KARAMBELKAR = {  # name: (ra, dec, source of the position)
    "WTP16aakapb": (344.6562, 58.7708, "Karambelkar+2026"),
    "WTP15aaavof": (348.5257, 61.5151, "Karambelkar+2026"),
    "WTP24abacpo": (185.7955, -61.8313, "Karambelkar+2026 text"),
    "PGIR20dci / WTP14aabswi": (13.084208, 56.567750, "Hillenbrand+2021 AJ 161 220 (00:52:20.21 +56:34:03.9)"),
    "FUOr-Aur0544+3330 / WTP10aaktsc": (86.0, 33.5, "approximate, from the designation only; checked within 1 deg"),
    "FU Ori": (88.0730, 9.0687, "comparison object"),
    "V900 Mon": (101.4250, -8.4086, "comparison object"),
    "V1057 Cyg": (314.7963, 44.2589, "comparison object"),
}
# The three classical novae of that paper (PGIR19aetsqr, PGIR22agyklf, Gaia22alz) are not YSOs and cannot be in a
# SPLICES protostar sample selected by class; they are not position-checked.


def tap(url, adql, tries=3):
    for i in range(tries):
        try:
            r = requests.post(url, data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql},
                              timeout=120)
            r.raise_for_status()
            if r.text.lstrip().startswith("<"):
                raise requests.RequestException("HTML response")
            return list(csv.DictReader(StringIO(r.text)))
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def gaia(ra, dec):
    q = ("SELECT TOP 3 source_id, phot_g_mean_mag, "
         f"DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', {ra}, {dec})) * 3600 AS sep FROM gaiadr3.gaia_source "
         f"WHERE 1 = CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {2.0 / 3600})) ORDER BY sep")
    return tap(GAIA_TAP, q)


def simbad(ra, dec, url):
    q = (f"SELECT TOP 3 b.main_id, b.otype, b.nbref, i.ids, "
         f"DISTANCE(POINT('ICRS', b.ra, b.dec), POINT('ICRS', {ra}, {dec})) * 3600 AS sep "
         f"FROM basic AS b JOIN ids AS i ON i.oidref = b.oid "
         f"WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', {ra}, {dec}, {SIMBAD_RADIUS / 3600})) = 1 "
         f"ORDER BY sep")
    return tap(url, q)


def main():
    rows = list(csv.DictReader(open(SAMPLE)))
    servers = list(SIMBAD_TAPS)
    simbad_ok = True
    out = []
    for r in rows:
        ra, dec = float(r["ra"]), float(r["dec"])
        g = gaia(ra, dec)
        row = {"name": r["name"], "role": r["role"], "ra": ra, "dec": dec,
               "gaia_dr3": g[0]["source_id"] if g else "", "gaia_sep_arcsec": round(float(g[0]["sep"]), 2) if g else "",
               "gaia_g": g[0]["phot_g_mean_mag"] if g else "", "n_gaia_within_2as": len(g)}
        s = []
        while servers:
            try:
                s = simbad(ra, dec, servers[0])
                break
            except requests.RequestException:
                servers.pop(0)
        simbad_ok = bool(servers)
        best = s[0] if s else {}
        row.update({"simbad_status": servers[0].split("/")[2] if simbad_ok else "SIMBAD unavailable",
                    "simbad_main_id": best.get("main_id", ""), "simbad_otype": best.get("otype", ""),
                    "simbad_nbref": best.get("nbref", ""),
                    "simbad_sep_arcsec": round(float(best["sep"]), 1) if best.get("sep") else "",
                    "simbad_ids": "|".join((best.get("ids") or "").split("|"))[:300]})
        out.append(row)
        time.sleep(0.1)
    with open(SEL / "simbad_xmatch.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    sc = SkyCoord([r["ra"] for r in out] * u.deg, [r["dec"] for r in out] * u.deg)
    nearest, overlaps = {}, []
    for n, (ra, dec, src) in KARAMBELKAR.items():
        sep = sc.separation(SkyCoord(ra * u.deg, dec * u.deg)).arcsec
        k = int(np.argmin(sep))
        lim = 3600.0 if "approximate" in src else 60.0
        nearest[n] = {"ra": ra, "dec": dec, "position_source": src, "closest_sample_target": out[k]["name"],
                      "separation_arcsec": round(float(sep[k]), 1), "overlap_limit_arcsec": lim}
        if sep[k] < lim:
            overlaps.append(n)
    check = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "objects": nearest,
             "overlaps": overlaps, "simbad_available": simbad_ok}
    (SEL / "karambelkar_check.json").write_text(json.dumps(check, indent=1))
    print(json.dumps(check, indent=1))
    print(sum(1 for r in out if r["gaia_dr3"]), "of", len(out), "targets have a Gaia DR3 source within 2\"")


if __name__ == "__main__":
    main()
