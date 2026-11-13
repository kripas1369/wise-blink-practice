"""Collects the per-region numbers into research/experimental_results/results_summary.json (and prints a table).

    PYTHONPATH=.:research .venv/bin/python research/collect_results.py
"""
import json
from pathlib import Path

RESULTS = Path(__file__).parent / "experimental_results"

REGIONS = [
    ("R1", "R1_lmc_tic179637488", "179637488", "4658741684445417856", "4658741684445420032"),
    ("R2", "R2_tic349156098", "349156098", "5282506656766565376", "5282509233747655168"),
    ("R3", "R3_tic309659126", "309659126", "4761080447161537664", "4761080447161537792"),
    ("R4", "R4_tic160195393", "160195393", "1724476407826709504", "1724476790079160704"),
    ("R5", "R5_sep_tic31511621", "31511621", "4659556972307750528", "4659556869228537216"),
]


def star(analysis, sid):
    return next(r for r in analysis["stars"] if r["source_id"] == sid)


def main():
    out = {}
    for reg, run, tic, eb, ts in REGIONS:
        f = RESULTS / run
        a = json.loads((f / "analysis.json").read_text())
        meta = json.loads((f / "meta.json").read_text())
        rec = {"run": run, "tic": tic, "gaia_eb": eb, "tic_star_gaia": ts, "n_exposures": meta["n_exposures"],
               "n_stars_fitted": a["n_stars"], "mjd_range": meta["mjd_range"], "clock": a.get("clock"),
               "eph_json": meta.get("eph_json")}
        for lab, sid in (("eb", eb), ("tic_star", ts)):
            r = star(a, sid)
            rec[lab] = {k: r.get(k) for k in ("g_mag", "primary", "secondary", "phase_scan", "ls_period_d",
                                              "ls_fap_bonferroni", "scatter_pct", "jitter_pct")}
        rec["significance"] = {}
        for p in sorted(f.glob("significance_*.json")):
            s = json.loads(p.read_text())
            rec["significance"][p.stem.split("_")[1]] = {k: {"depth": v["depth"], "z": v["z_empirical"],
                                                             "fap": round(v["fap_empirical"], 4)}
                                                         for k, v in s["stars"].items()}
        t = f / f"timing_{eb}.json"
        if t.exists():
            rec["timing"] = {k: {x: v.get(x) for x in ("depth", "depth_err", "offset_minutes", "offset_minutes_err",
                                                        "clock_error_phase")}
                             for k, v in json.loads(t.read_text())["eclipses"].items()}
        g = f / "figures.json"
        if g.exists():
            fig = json.loads(g.read_text())
            rec["difference_image"] = fig.get("difference")
            rec["difference_centroid"] = fig.get("difference_centroid")
        out[reg] = rec
        p, s = rec["eb"]["primary"] or {}, rec["eb"]["secondary"] or {}
        tp, tsec = rec["tic_star"]["primary"] or {}, rec["tic_star"]["secondary"] or {}
        print(f"{reg} TIC {tic}: Gaia EB P {p.get('depth')}±{p.get('err')} S {s.get('depth')}±{s.get('err')} | "
              f"TIC star P {tp.get('depth')}±{tp.get('err')} S {tsec.get('depth')}±{tsec.get('err')} | "
              f"LS {rec['eb']['ls_period_d']} | centroid {(rec.get('difference_centroid') or {}).get('dist_to_gaia_eb_px')}"
              f" / {(rec.get('difference_centroid') or {}).get('dist_to_tic_star_sigma')}σ")
    (RESULTS / "results_summary.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
