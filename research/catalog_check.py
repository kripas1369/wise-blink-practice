"""What is already known about each target: VSX, OGLE-IV eclipsing binaries (LMC/SMC), SIMBAD, Gaia DR3 variability.

    .venv/bin/python research/catalog_check.py NAME RA DEC [NAME RA DEC ...]   -> research/out/catalog_check.json

VizieR (Harvard mirror) cone searches: VSX (B/vsx/vsx) within 60″, OGLE-IV LMC eclipsing binaries
(J/AcA/66/421, Pawlak et al. 2016) within 10″; SIMBAD (Harvard mirror) sim-script within 30″.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "out"
VIZIER = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
SIMBAD = "https://simbad.cfa.harvard.edu/simbad/sim-script"
UA = {"User-Agent": "Mozilla/5.0 (research; SPHEREx TimeLens)"}


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def vizier(source, ra, dec, radius_arcsec, cols="**"):
    q = urllib.parse.urlencode({"-source": source, "-c": f"{ra} {dec}", "-c.rs": radius_arcsec, "-out": cols,
                                "-out.max": 200, "-sort": "_r", "-out.add": "_r"})
    text = get(f"{VIZIER}?{q}")
    lines = [l for l in text.splitlines() if l and not l.startswith("#")]
    if len(lines) < 3:
        return []
    head = lines[0].split("\t")
    return [dict(zip(head, (v.strip() for v in l.split("\t")))) for l in lines[2:] if not l.startswith("-")]


def simbad(ra, dec, radius_arcsec):
    script = (f"output console=off script=off\nformat object \"%IDLIST(1) | %OTYPE | %COO(d;A D) | %DIST\"\n"
              f"query coo {ra} {dec} radius={radius_arcsec}s\n")
    text = get(SIMBAD, urllib.parse.urlencode({"script": script}).encode())
    return [l.strip() for l in text.splitlines() if "|" in l]


def main(args):
    path = OUT / "catalog_check.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    for i in range(0, len(args), 3):
        name, ra, dec = args[i], float(args[i + 1]), float(args[i + 2])
        rec = {"ra": ra, "dec": dec}
        for key, fn in (("vsx", lambda: vizier("B/vsx/vsx", ra, dec, 60, "Name,Type,Period,max,min,n_max,_RA,_DE")),
                        ("ogle_lmc_ecl", lambda: vizier("J/AcA/66/421/ecl", ra, dec, 10)),
                        ("simbad", lambda: simbad(ra, dec, 30))):
            try:
                rec[key] = fn()
            except Exception as exc:
                rec[key] = f"failed: {exc}"
        done[name] = rec
        path.write_text(json.dumps(done, indent=1))
        print(name, json.dumps(rec, indent=1)[:2500])


if __name__ == "__main__":
    main(sys.argv[1:])
