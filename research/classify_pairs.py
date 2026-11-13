"""Sort the 68 TESS-EBs duplicate pairs by what public catalogues already say about which star eclipses.

    .venv/bin/python research/classify_pairs.py      -> research/out/pair_table.md, pair_classes.json
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"
SPHEREX_MIN_SEP = 12.0   # arcsec, about two SPHEREx pixels
POS_TOL = 3.0            # arcsec


def ratio_ok(p1, p2):
    return any(abs(p1 / p2 - k) < 0.002 * k for k in (0.5, 1.0, 2.0))


def vsx_vote(p):
    votes = set()
    for v in p["vsx"]:
        if not v["period"] or not ratio_ok(float(v["period"]), p["P"]):
            continue
        if v["sep_a"] < POS_TOL < v["sep_b"]:
            votes.add(p["a"])
        elif v["sep_b"] < POS_TOL < v["sep_a"]:
            votes.add(p["b"])
    return votes


def gaia_vote(p):
    votes = set()
    for key, tic in (("gaia_a", p["a"]), ("gaia_b", p["b"])):
        g = p.get(key) or {}
        if g.get("gaia_eb_period") and ratio_ok(g["gaia_eb_period"], p["P"]):
            votes.add(tic)
    return votes


def main():
    gaia = {(p["a"], p["b"]): p for p in json.loads((OUT / "gaia_pairs.json").read_text())}
    vsx = {(p["a"], p["b"]): p for p in json.loads((OUT / "vsx_pairs.json").read_text())}
    ttt = set()
    for name in ("ttt_table3.tsv", "ttt_table4.tsv"):
        f = Path(__file__).parent / "data" / name
        if f.exists():
            ttt |= {w for line in f.read_text().splitlines() for w in line.split() if w.isdigit()}
    rows, counts = [], {}
    for key, p in gaia.items():
        v, g = vsx_vote(vsx[key]), gaia_vote(p)
        both = v | g
        if p["sep"] < SPHEREX_MIN_SEP:
            cls = "too close for SPHEREx"
        elif len(both) == 1:
            cls = "answered by " + " + ".join(n for n, s in (("VSX", v), ("Gaia", g)) if s)
        elif len(both) > 1:
            cls = "catalogues disagree"
        else:
            cls = "open"
        in_ttt = bool({p["a"], p["b"]} & ttt)
        counts[cls] = counts.get(cls, 0) + 1
        rows.append({"a": p["a"], "b": p["b"], "sep": p["sep"], "P": p["P"], "class": cls,
                     "answer": sorted(both), "in_ttt": in_ttt, "eclat": p["eclat"],
                     "depth_a": p["da"], "depth_b": p["db"]})
    rows.sort(key=lambda r: (r["class"], -r["sep"]))
    (OUT / "pair_classes.json").write_text(json.dumps({"counts": counts, "pairs": rows}, indent=1))
    lines = ["| TIC A | TIC B | sep (″) | P (d) | status | catalogue answer |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['a']} | {r['b']} | {r['sep']} | {r['P']:.5f} | {r['class']} | {', '.join(r['answer']) or '–'} |"
              for r in rows]
    (OUT / "pair_table.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(counts, indent=1))
    print(f"in TESS Ten Thousand: {sum(r['in_ttt'] for r in rows)}")
    for r in rows:
        if r["class"] in ("open", "catalogues disagree"):
            print(r["a"], r["b"], r["sep"], r["P"], r["class"], r["answer"])


if __name__ == "__main__":
    main()
