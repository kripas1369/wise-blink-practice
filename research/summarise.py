"""One line per tested pair from research/out/pair_*/result.json and phase_scan.json -> research/out/summary.md"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"


def pct(d):
    return "–" if not d else f"{100 * d['depth']:.1f} ± {100 * d['err']:.1f}"


def main():
    lines = ["| pair (A vs B) | sep ″ | P d | data | exposures | eclipse | circle A | circle B | PSF A | PSF B | "
             "blind scan A | blind scan B |", "|" + "---|" * 12]
    for folder in sorted(OUT.glob("pair_*_*")):
        f = folder / "result.json"
        if not f.exists() or folder.name.endswith("qr3only"):
            continue
        r = json.loads(f.read_text())
        a, b = r["pair"]
        scan = json.loads((folder / "phase_scan.json").read_text()) if (folder / "phase_scan.json").exists() else {}
        data = "DR1+QR3" if isinstance(r.get("collections"), list) else "QR2/QR3"
        for part in ("primary", "secondary"):
            ca, cb = (r["stars"][t]["circle"].get(part) for t in (a, b))
            pa, pb = (r["stars"][t].get("psf", {}).get(part) for t in (a, b))
            if not any((ca, cb, pa, pb)):
                continue
            sa, sb = (scan.get(t) for t in (a, b))
            s = lambda x: "–" if not x else f"{100 * x['depth']:.1f}% @ {x['phase']:.2f} ({x['snr']:.1f}σ)"
            lines.append(f"| {a} vs {b} | {r['sep_arcsec']} | {r['clock']['period']:.4f} | {data} | {r['n_exposures']} | "
                         f"{part} | {pct(ca)} | {pct(cb)} | {pct(pa)} | {pct(pb)} | {s(sa)} | {s(sb)} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
