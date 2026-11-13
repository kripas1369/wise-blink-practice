"""How the fraction of TESS-EBs entries whose period-matched Gaia DR3 eclipsing binary is another star depends on
galactic latitude, ecliptic latitude, TESS magnitude, TESS depth and period.

    PYTHONPATH=.:research .venv/bin/python research/misattribution_trends.py    # -> research/out/misattribution_trends.txt

Input: research/out/tessebs_gaia_xmatch.json (tessebs_gaia_xmatch.py). Only entries with a period-matched Gaia EB
within 63″ ("same star" or "other star") enter the fractions; the χ² test is on the 2 × k table other/same.
"""
import json
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
from scipy.stats import chi2_contingency

OUT = Path(__file__).resolve().parent / "out"

BINS = {
    "|galactic latitude| (deg)": ("glat", [0, 5, 10, 20, 30, 50, 91]),
    "|ecliptic latitude| (deg)": ("elat", [0, 30, 60, 75, 91]),
    "TESS magnitude": ("tmag", [0, 8, 9, 10, 11, 12, 13, 20]),
    "TESS primary depth": ("tess_depth", [0, 0.01, 0.03, 0.1, 0.3, 1.01]),
    "period (d)": ("period", [0, 0.5, 1, 3, 10, 1000]),
}


def table(entries: list[dict]) -> dict[str, np.ndarray]:
    ra = np.array([e["ra"] for e in entries])
    dec = np.array([e["dec"] for e in entries])
    c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg)
    num = lambda k: np.array([np.nan if e.get(k) is None else float(e[k]) for e in entries])
    return {
        "glat": np.abs(c.galactic.b.deg),
        "elat": np.abs(c.barycentrictrueecliptic.lat.deg),
        "tmag": num("tmag"),
        "tess_depth": num("tess_depth"),
        "period": num("period"),
        "cls": np.array([e["class"] for e in entries]),
    }


def fmt_edge(v: float) -> str:
    return f"{v:g}"


def trends(t: dict[str, np.ndarray]) -> list[str]:
    matched = (t["cls"] == "same star") | (t["cls"] == "other star")
    other = t["cls"] == "other star"
    lines = [f'entries with a period-matched Gaia DR3 EB within 63": {matched.sum()}; on another star: '
             f'{other.sum()} ({other.sum() / matched.sum():.3f})', ""]
    for title, (key, edges) in BINS.items():
        lines.append(title)
        counts = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = matched & (t[key] >= lo) & (t[key] < hi)
            n, k = int(m.sum()), int((m & other).sum())
            f = k / n if n else float("nan")
            e = np.sqrt(f * (1 - f) / n) if n else float("nan")
            lines.append(f"  [{fmt_edge(lo):>5}, {fmt_edge(hi):>5}): n={n:5d} other={k:4d} frac={f:.3f} ± {e:.3f}")
            counts.append([k, n - k])
        chi2, p, dof, _ = chi2_contingency(np.array(counts))
        lines.append(f"  chi2 test of equal fractions: chi2={chi2:.1f}, dof={dof}, p={p:.2e}")
        lines.append("")
    lines.append("All TESS-EBs entries by depth (any class):")
    edges = BINS["TESS primary depth"][1]
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (t["tess_depth"] >= lo) & (t["tess_depth"] < hi)
        n = int(m.sum())
        k = int((m & other).sum())
        s = int((m & (t["cls"] == "same star")).sum())
        z = int((m & (t["cls"] == "no Gaia EB")).sum())
        lines.append(f"  [{fmt_edge(lo)},{fmt_edge(hi)}): n={n}, other star={k} ({k / n:.3f}), same={s}, no Gaia EB={z}")
    return lines


def main() -> None:
    entries = json.loads((OUT / "tessebs_gaia_xmatch.json").read_text())["entries"]
    text = "\n".join(trends(table(entries))) + "\n"
    (OUT / "misattribution_trends.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
