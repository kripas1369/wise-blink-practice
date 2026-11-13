"""Does Gaia DR3 already say which star of a TESS-EBs duplicate pair is the eclipsing binary?

    PYTHONPATH=. .venv/bin/python research/gaia_crosscheck.py

For each pair in research/out/all_duplicate_pairs.json: the Gaia DR3 source of each TIC star (nearest within 3″
of the TIC J2000 position moved to 2016.0), its colour, parallax, RUWE, variability flag, and whether it is in
gaiadr3.vari_eclipsing_binary (Mowlavi et al. 2023) and with what period. Output: research/out/gaia_pairs.json
"""
import json
from pathlib import Path

import pyvo

from backend.app import eclipses as E
from backend.app.motion import position_at

OUT = Path(__file__).parent / "out"
TAP = pyvo.dal.TAPService("https://gea.esac.esa.int/tap-server/tap")


def gaia_for(tess_id):
    e = E.by_tess_id(tess_id)
    ra, dec = position_at(e.ra, e.dec, e.pmra, e.pmdec, 2000.0, 2016.0)
    t = TAP.run_sync(f"""
        SELECT TOP 1 source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, ruwe, phot_variable_flag,
               DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', {ra}, {dec})) * 3600 AS sep
        FROM gaiadr3.gaia_source
        WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {3 / 3600})) = 1
        ORDER BY sep""").to_table()
    if not len(t):
        return None
    r = t[0]
    f = lambda k: None if hasattr(r[k], "mask") and r[k].mask else (float(r[k]) if k != "phot_variable_flag" else str(r[k]))
    return {"source_id": str(r["source_id"]), "sep": round(float(r["sep"]), 2), "g": f("phot_g_mean_mag"),
            "bp_rp": f("bp_rp"), "parallax": f("parallax"), "ruwe": f("ruwe"), "var_flag": f("phot_variable_flag")}


def main():
    pairs = json.loads((OUT / "all_duplicate_pairs.json").read_text())
    out = []
    for p in pairs:
        row = {**{k: (float(v) if hasattr(v, "dtype") else v) for k, v in p.items()}}
        ids = {}
        for k in ("a", "b"):
            g = gaia_for(p[k])
            row[f"gaia_{k}"] = g
            if g:
                ids[k] = g["source_id"]
        if ids:
            t = TAP.run_sync(f"SELECT source_id, frequency, global_ranking, model_type FROM gaiadr3.vari_eclipsing_binary "
                             f"WHERE source_id IN ({','.join(ids.values())})").to_table()
            ebs = {str(r["source_id"]): (1 / float(r["frequency"]) if float(r["frequency"]) > 0 else None,
                                         float(r["global_ranking"])) for r in t}
            for k, sid in ids.items():
                if sid in ebs:
                    row[f"gaia_{k}"]["gaia_eb_period"] = ebs[sid][0]
                    row[f"gaia_{k}"]["gaia_eb_rank"] = ebs[sid][1]
        out.append(row)
        ga, gb = row.get("gaia_a") or {}, row.get("gaia_b") or {}
        print(f"{p['a']:>10} {p['b']:>10} sep {p['sep']:6.1f}\" P {p['P']:9.5f}  "
              f"A: G {ga.get('g') or 0:5.2f} EB {ga.get('gaia_eb_period')}  B: G {gb.get('g') or 0:5.2f} EB {gb.get('gaia_eb_period')}",
              flush=True)
    (OUT / "gaia_pairs.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
