"""Blind periodicity search over every fitted Gaia star in the five regions (no TESS information used).

    PYTHONPATH=.:research .venv/bin/python research/blind_search.py   # -> experimental_results/blind_search_auto.txt

For each region: stars with a Lomb–Scargle Bonferroni FAP < 1e-3 (from field_analysis.py), the region's Gaia
eclipsing binary listed separately, VSX entries within 10″ (VizieR B/vsx). Stars with no VSX entry get two tests a
real periodic star must pass: the same period in both halves of the data (split at the median date), and the signal
present in more than one detector. The verdicts in experimental_results/blind_variability.txt were written from
these numbers.
"""
import json
from pathlib import Path

import numpy as np
from astropy.timeseries import LombScargle

from catalog_check import vizier

HERE = Path(__file__).resolve().parent
RES = HERE / "experimental_results"
FAP_LIMIT = 1e-3
VSX_RADIUS_ARCSEC = 10.0
F_MIN, F_MAX = 1 / 300, 1 / 0.1
REGIONS = {
    "R1_lmc_tic179637488": "4658741684445417856",
    "R2_tic349156098": "5282506656766565376",
    "R3_tic309659126": "4761080447161537664",
    "R4_tic160195393": "1724476407826709504",
    "R5_sep_tic31511621": "4659556972307750528",
}


def power_at(t, y, e, period):
    """LS power at one period and its false-alarm probability over the full search range."""
    ls = LombScargle(t, y, e)
    p = float(ls.power(1 / period))
    return p, float(ls.false_alarm_probability(p, minimum_frequency=F_MIN, maximum_frequency=F_MAX))


def best(t, y, e):
    ls = LombScargle(t, y, e)
    f, p = ls.autopower(minimum_frequency=F_MIN, maximum_frequency=F_MAX, samples_per_peak=10)
    return float(1 / f[np.argmax(p)])


def semi_amplitude(t, y, e, period):
    theta = LombScargle(t, y, e).model_parameters(1 / period)
    return float(np.hypot(theta[1], theta[2]))


def region(run: str, eb: str) -> list[str]:
    folder = RES / run
    meta = json.loads((folder / "meta.json").read_text())
    stars = json.loads((folder / "analysis.json").read_text())["stars"]
    pos = {s["source_id"]: s for s in json.loads((folder / "stars.json").read_text())}
    lc = np.load(folder / "lightcurves.npz")
    mjd, det, gc, ge = lc["mjd"], lc["det"], lc["gc"], lc["ge"]
    size = meta["grid_size_px"]
    order = [s["source_id"] for s in stars]
    out = []
    for s in stars:
        fap = s.get("ls_fap_bonferroni")
        if fap is None or not np.isfinite(fap) or fap >= FAP_LIMIT:
            continue
        sid = s["source_id"]
        edge = min(s["x"], s["y"], size - 1 - s["x"], size - 1 - s["y"])
        tag = "TARGET BINARY " if sid == eb else ""
        out.append(f"{run} {tag}{sid} G {s['g_mag']:.2f} LS {s['ls_period_d']} d FAPb {fap:.1e} "
                   f"amp {s['amplitude_pct']}% cov {s['coverage']} edge {edge:.1f} px")
        if sid == eb:
            continue
        p = pos.get(sid, {})
        try:
            vsx = vizier("B/vsx/vsx", p.get("ra"), p.get("dec"), VSX_RADIUS_ARCSEC, "Name,Type,Period")
            vsx = [(v.get("Name"), v.get("Type"), v.get("Period"), v.get("_r")) for v in vsx]
        except Exception as exc:
            vsx = f"VSX query failed: {exc}"
        out.append(f"    VSX within {VSX_RADIUS_ARCSEC:g}\": {vsx or 'none'}")
        if vsx:
            continue
        j = order.index(sid)
        m = np.isfinite(gc[:, j]) & (ge[:, j] > 0)
        t, y, e = mjd[m], gc[m, j], ge[m, j]
        period = s["ls_period_d"]
        half = t < np.median(t)
        for name, h in (("first half", half), ("second half", ~half)):
            pw, fp = power_at(t[h], y[h], e[h], period)
            out.append(f"    {name}: n={h.sum()}, best period {best(t[h], y[h], e[h]):.5f} d, "
                       f"power at {period} d = {pw:.3f}, FAP of that power {fp:.2e}")
        for d in sorted(set(det[m].tolist())):
            k = det[m] == d
            if k.sum() < 10:
                continue
            pw, _ = power_at(t[k], y[k], e[k], period)
            out.append(f"    D{d} n={k.sum()} power {pw:.3f} semi-amp {100 * semi_amplitude(t[k], y[k], e[k], period):.1f}%")
    return out


def main() -> None:
    lines = [f"Blind periodicity search: Lomb–Scargle Bonferroni FAP < {FAP_LIMIT:g}, all fitted Gaia stars", ""]
    for run, eb in REGIONS.items():
        lines += region(run, eb) + [""]
    text = "\n".join(lines)
    (RES / "blind_search_auto.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
