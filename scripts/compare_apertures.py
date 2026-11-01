"""Which aperture gives the steadiest light curve of a steady star? Ours (2 px, sky 10-14 px median)
against the radii of IRSA's Source Discovery Tool (3, 4, 5 px, sky 7-16 px, sigma-clipped median).

Uses the exposures.fits and the target track already in lightcurve.json of each folder, so only the
aperture changes. Printed per radius and sky ring: number of same-wavelength pairs between visits and
their spread (lightcurve.log_scatter_pct, %). Lower spread on a steady star = less noise from the method.

    python scripts/compare_apertures.py frontend/frames/eps_ind_b/d2 frontend/frames/eps_ind_b/d5
"""
import json
import sys
from pathlib import Path

import numpy as np
from astropy.stats import sigma_clipped_stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import lightcurve as lcm  # noqa: E402

RADII = (2.0, 3.0, 4.0, 5.0)
SKIES = {"ours 10-14 median": ((10.0, 14.0), False), "IRSA 7-16 clipped": ((7.0, 16.0), True)}


def measure_clipped(image, sigma, bad, has_value, x, y, r_out, sky_annulus):
    """lightcurve.measure, with the sky as a 3-sigma clipped median (5 iterations) like IRSA's tool."""
    out = lcm.measure(image, sigma, bad, has_value, x, y, 0.0, r_out, sky_annulus)
    if out["flux_mjy"] is None:
        return out
    sky_w = lcm.ring_weights(image.shape, x, y, *sky_annulus)
    vals = image[(sky_w > 0.999) & has_value & ~bad & np.isfinite(image)]
    _, clipped, _ = sigma_clipped_stats(vals, sigma=3, maxiters=5)
    w = lcm.ring_weights(image.shape, x, y, 0.0, r_out)
    out["flux_mjy"] += (out["sky"] - float(clipped)) * float(w.sum()) * lcm.MJY_PER_PIXEL_UNIT
    return out


def main() -> None:
    for folder in map(Path, sys.argv[1:]):
        ex = lcm.load_exposures(folder)
        lc = json.loads((folder / "lightcurve.json").read_text())
        if lc["method"] != "core":
            print(f"{folder}: {lc['method']}, skipped")
            continue
        track = {p["obs_id"]: (p["x"], p["y"]) for p in lc["points"]}
        line = [f"{folder}:"]
        for label, (ring, clipped) in SKIES.items():
            for r in RADII:
                points = []
                for k, obs in enumerate(ex["obs_id"]):
                    x, y = track[obs]
                    args = (ex["image"][k], ex["sigma"][k], ex["bad"][k], ex["has_value"][k], x, y)
                    m = measure_clipped(*args, r, ring) if clipped else lcm.measure(*args, 0.0, r, ring)
                    points.append({**m, "frame": int(ex["frame"][k]), "mjd": float(ex["mjd"][k]),
                                   "wl_um": float(ex["wl_um"][k]), "bw_um": float(ex["bw_um"][k])})
                ratios = [q for _, _, q, _ in lcm.wavelength_pairs(points)]
                line.append(f"{label} r{r:g}: {len(ratios)} pairs {lcm.log_scatter_pct(ratios)}%")
        print("\n  ".join(line))


if __name__ == "__main__":
    main()
