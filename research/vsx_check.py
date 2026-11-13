"""Known variable stars (VSX, via the VizieR mirror B/vsx/vsx) within 2′ of each duplicate pair.

    PYTHONPATH=. .venv/bin/python research/vsx_check.py

A VSX eclipsing binary with the TESS period sitting on one star of a pair means the answer was already
public. Output: research/out/vsx_pairs.json
"""
import json
from pathlib import Path

import requests

from backend.app import eclipses as E

OUT = Path(__file__).parent / "out"
URL = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"


def cone(ra, dec, radius_arcsec=120):
    r = requests.get(URL, params={"-source": "B/vsx/vsx", "-c": f"{ra} {dec}", "-c.rs": radius_arcsec,
                                  "-out": "_r OID Name Type Period RAJ2000 DEJ2000 max min", "-sort": "_r"}, timeout=60)
    lines = [l for l in r.text.splitlines() if l and not l.startswith("#")]
    if len(lines) < 4:
        return []
    hdr = [h.strip() for h in lines[0].split("\t")]
    return [dict(zip(hdr, [v.strip() for v in l.split("\t")])) for l in lines[3:]]


def main():
    pairs = json.loads((OUT / "all_duplicate_pairs.json").read_text())
    out = []
    for p in pairs:
        ea, eb = E.by_tess_id(p["a"]), E.by_tess_id(p["b"])
        found = cone((ea.ra + eb.ra) / 2, (ea.dec + eb.dec) / 2)
        hits = []
        for v in found:
            try:
                per = float(v.get("Period") or "nan")
            except ValueError:
                per = float("nan")
            match = any(abs(per / (p["P"] * f) - 1) < 0.002 for f in (1, 2, 0.5)) if per == per else False
            sep = {k: E.separation_arcsec(e.ra, e.dec, float(v["RAJ2000"]), float(v["DEJ2000"]))
                   for k, e in (("a", ea), ("b", eb))} if v.get("RAJ2000") else {}
            hits.append({"name": v.get("Name"), "type": v.get("Type"), "period": v.get("Period"), "period_match": match,
                         "sep_a": round(sep.get("a", float("nan")), 1), "sep_b": round(sep.get("b", float("nan")), 1)})
        out.append({"a": p["a"], "b": p["b"], "P": p["P"], "sep": float(p["sep"]), "vsx": hits})
        m = [h for h in hits if h["period_match"]]
        print(f"{p['a']:>10} {p['b']:>10} P {p['P']:9.5f}: {len(hits)} VSX within 2′; period match: "
              + ("; ".join(f"{h['name']} {h['type']} P={h['period']} ({h['sep_a']}″ from A, {h['sep_b']}″ from B)" for h in m) or "none"),
              flush=True)
    (OUT / "vsx_pairs.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
