"""C4 acceptance tests (docs/plan/HACKATHON_PLAN.md, part C4) on the 5 official targets.

Offline, from the prepared folders in frontend/frames:
    barnard    measured shift of the saturated core ("hole") from the first to the last visit vs Gaia
    eps_ind_b  measured shift of the brightness-weighted centre vs Gaia: size and direction
    wise0855   D6: Gaussian fit of the source in each visit vs SIMBAD's proper motion + parallax, and
               the same fit for the other candidate, the fixed Gaia star 1.1 px away; D2: is anything
               at WISE 0855's position once that Gaia star is fitted too?
    rw_aur     what the light curve measured (AAVSO not compared: unreachable on 31 Oct 2026)
    r_dra      why it cannot be checked
With --online, also for a few positions: our image search (archive.find_images) against IRSA's own
COUNT(*) of the same table.

    python -m scripts.acceptance [--online] [--json notes/acceptance_c4.json]

Thresholds marked "ours" are our choice, not a published standard.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from astropy.coordinates import get_body_barycentric
from astropy.time import Time
from scipy.optimize import least_squares

from backend.app.diff import load_frame
from scripts.measure_motion import centroid, hole_centre

FRAMES = Path("frontend/frames")
MAX_MOTION_ERROR_PX = 0.5          # HACKATHON_PLAN C4 (Barnard)
MAX_DIRECTION_ERROR_DEG = 30.0     # ours
ALIGNMENT_PX = 0.11                # 1 sigma, Gaia DR3 G 16.35 star in WISE 0855 D6 Nov 2025 (this script)
FIT_HALF_BOX = 3                   # 7 × 7 pixels
# WISE 0855: SIMBAD (simbad.harvard.edu / CDS, 31 Oct 2026), all from Kirkpatrick et al. 2021, ApJS 253, 7
WISE_PM_MAS = (-8123.7, 673.2)
WISE_PLX_MAS = 439.0
GRID_EPOCH_MJD = 51544.5 + 26 * 365.25   # J2026.0: the manifests' "moved to 2026.0"


def folder(target: str, band: int) -> Path:
    return FRAMES / target / f"d{band}"


def load(target: str, band: int, name: str) -> dict:
    return json.loads((folder(target, band) / name).read_text())


def north_up(frame: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return frame["image"][::-1], frame["sigma"][::-1], frame["usable"][::-1]


def angle_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    d = math.degrees(math.atan2(a[1], a[0]) - math.atan2(b[1], b[0]))
    return abs((d + 180) % 360 - 180)


def shift_check(target: str, band: int, how: str) -> dict:
    """First-to-last-visit shift of the target, measured (centroid or hole) vs Gaia, PNG pixels."""
    m, g = load(target, band, "manifest.json"), load(target, band, "gaia.json")
    star = next(s for s in g["stars"] if s.get("target"))
    measure = centroid if how == "centroid" else hole_centre
    ends = []
    for i in (0, len(m["frames"]) - 1):
        frame = load_frame(folder(target, band) / m["frames"][i]["fits"])
        gx, gy = star["xy"][i]
        p = measure(frame, gx, gy)
        if p is None:
            return {"status": "not measurable", "reason": f"{how} not usable in visit {i + 1}"}
        ends.append(((gx, gy), p[:2]))
    (g0, p0), (g1, p1) = ends
    gaia = (g1[0] - g0[0], g1[1] - g0[1])
    meas = (p1[0] - p0[0], p1[1] - p0[1])
    error = math.hypot(meas[0] - gaia[0], meas[1] - gaia[1])
    return {"method": how, "visits": [m["frames"][0]["date_iso"][:10], m["frames"][-1]["date_iso"][:10]],
            "gaia_shift_px": [round(v, 3) for v in gaia], "gaia_px": round(math.hypot(*gaia), 2),
            "measured_shift_px": [round(v, 3) for v in meas], "measured_px": round(math.hypot(*meas), 2),
            "difference_px": round(error, 2), "direction_difference_deg": round(angle_deg(meas, gaia), 1)}


def wise_predicted_xy(manifest: dict, mjd: float) -> tuple[float, float]:
    """WISE 0855 on the frames grid (PNG pixels: +x west, +y south) with proper motion and parallax."""
    ra, dec = math.radians(manifest["ra"]), math.radians(manifest["dec"])
    years = (mjd - GRID_EPOCH_MJD) / 365.25
    e = get_body_barycentric("earth", Time(mjd, format="mjd", scale="tdb")).xyz.to("AU").value
    p_ra = e[0] * math.sin(ra) - e[1] * math.cos(ra)
    p_dec = e[0] * math.cos(ra) * math.sin(dec) + e[1] * math.sin(ra) * math.sin(dec) - e[2] * math.cos(dec)
    d_ra = WISE_PM_MAS[0] * years + WISE_PLX_MAS * p_ra       # mas, east positive
    d_dec = WISE_PM_MAS[1] * years + WISE_PLX_MAS * p_dec     # mas, north positive
    c = (manifest["size_px"] - 1) / 2
    scale = manifest["pixel_arcsec"] * 1000
    return c - d_ra / scale, c - d_dec / scale


def fit_sources(frame: dict, centre: tuple[float, float], fixed: list[tuple[float, float]] | None):
    """Least-squares Gaussian fit in a 7 × 7 box around `centre`.

    fixed=None: one source with free position and width. Otherwise one source at each fixed position,
    free fluxes and a shared free width. Returns parameters, 1-sigma errors and reduced chi².
    """
    img, sig, usable = north_up(frame)
    cx, cy = int(round(centre[0])), int(round(centre[1]))
    ys, xs = np.mgrid[cy - FIT_HALF_BOX:cy + FIT_HALF_BOX + 1, cx - FIT_HALF_BOX:cx + FIT_HALF_BOX + 1]
    d, s, u = img[ys, xs], sig[ys, xs], usable[ys, xs]
    sky0 = float(np.median(d[u]))

    def gauss(x, y, w):
        return np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * w * w))

    if fixed is None:
        def model(p):
            return p[0] * gauss(p[1], p[2], p[4]) + p[3]
        p0 = [float(d.max() - sky0), centre[0], centre[1], sky0, 0.8]
        lo = [-np.inf, centre[0] - 2, centre[1] - 2, -np.inf, 0.3]
        hi = [np.inf, centre[0] + 2, centre[1] + 2, np.inf, 3.0]
    else:
        def model(p):
            return sum(a * gauss(x, y, p[-1]) for a, (x, y) in zip(p[:len(fixed)], fixed)) + p[len(fixed)]
        p0 = [float(d.max() - sky0) / len(fixed)] * len(fixed) + [sky0, 0.8]
        lo = [-np.inf] * (len(fixed) + 1) + [0.3]
        hi = [np.inf] * (len(fixed) + 1) + [3.0]
    r = least_squares(lambda p: ((model(p) - d) / s)[u], p0, bounds=(lo, hi))
    dof = int(u.sum()) - len(p0)
    chi2 = float((r.fun ** 2).sum() / dof)
    cov = np.linalg.pinv(r.jac.T @ r.jac) * max(1.0, chi2)
    return r.x, np.sqrt(np.diag(cov)), chi2


def wise0855() -> dict:
    out = {}
    m6, g6 = load("wise0855", 6, "manifest.json"), load("wise0855", 6, "gaia.json")
    neighbour = min((s for s in g6["stars"] if s["g_mag"] is not None),
                    key=lambda s: math.hypot(s["xy"][0][0] - 14, s["xy"][0][1] - 14))
    visits = []
    for i, f in enumerate(m6["frames"]):
        frame = load_frame(folder("wise0855", 6) / f["fits"])
        pred = wise_predicted_xy(m6, f["mjd"])
        gx, gy = neighbour["xy"][i]
        p, e, chi2 = fit_sources(frame, pred, None)
        two, two_e, two_chi2 = fit_sources(frame, pred, [pred, (gx, gy)])
        visits.append({
            "date": f["date_iso"][:10], "mjd": f["mjd"], "n_images": f["n_images"],
            "predicted_xy": [round(v, 3) for v in pred],
            "fit_xy": [round(p[1], 3), round(p[2], 3)], "fit_err_px": [round(e[1], 3), round(e[2], 3)],
            "fit_snr": round(p[0] / e[0], 1), "fit_width_px": round(p[4], 2), "fit_chi2": round(chi2, 2),
            "offset_from_wise_px": round(math.hypot(p[1] - pred[0], p[2] - pred[1]), 2),
            "offset_from_gaia_star_px": round(math.hypot(p[1] - gx, p[2] - gy), 2),
            "two_source_fit": {"wise_flux_snr": round(two[0] / two_e[0], 1),
                               "gaia_star_flux_snr": round(two[1] / two_e[1], 1),
                               "gaia_over_wise_flux": round(two[1] / two[0], 2) if two[0] > 0 else None,
                               "chi2": round(two_chi2, 2)},
        })
    out["d6_neighbour"] = {"source_id": neighbour["source_id"], "g_mag": neighbour["g_mag"],
                           "xy": neighbour["xy"][0]}
    out["d6_visits"] = visits
    detected = [v for v in visits if v["fit_snr"] >= 5]
    if len(detected) >= 2:
        a, b = detected[0], detected[-1]
        meas = (b["fit_xy"][0] - a["fit_xy"][0], b["fit_xy"][1] - a["fit_xy"][1])
        pred = (b["predicted_xy"][0] - a["predicted_xy"][0], b["predicted_xy"][1] - a["predicted_xy"][1])
        err = math.hypot(*a["fit_err_px"], *b["fit_err_px"])   # statistical only: same grid, same frames
        out["d6_shift"] = {
            "visits": [a["date"], b["date"]],
            "measured_px": [round(v, 3) for v in meas], "predicted_px": [round(v, 3) for v in pred],
            "difference_px": round(math.hypot(meas[0] - pred[0], meas[1] - pred[1]), 2),
            "fixed_star_would_be_px": 0.0, "measured_size_px": round(math.hypot(*meas), 2),
            "error_px": round(err, 2),
            "difference_sigma": round(math.hypot(meas[0] - pred[0], meas[1] - pred[1]) / err, 1),
            "against_fixed_star_sigma": round(math.hypot(*meas) / err, 1),
        }
        out["d6_absolute"] = [{"date": v["date"], "offset_from_wise_px": v["offset_from_wise_px"],
                               "offset_from_gaia_star_px": v["offset_from_gaia_star_px"],
                               "error_px": round(math.hypot(*v["fit_err_px"], ALIGNMENT_PX * math.sqrt(2)), 2)}
                              for v in detected]
    m2, g2 = load("wise0855", 2, "manifest.json"), load("wise0855", 2, "gaia.json")
    star2 = next(s for s in g2["stars"] if s["source_id"] == neighbour["source_id"])
    d2 = []
    for i, f in enumerate(m2["frames"]):
        frame = load_frame(folder("wise0855", 2) / f["fits"])
        pred = wise_predicted_xy(m2, f["mjd"])
        two, two_e, chi2 = fit_sources(frame, pred, [pred, tuple(star2["xy"][i])])
        d2.append({"date": f["date_iso"][:10], "wise_flux_snr": round(two[0] / two_e[0], 1),
                   "gaia_star_flux_snr": round(two[1] / two_e[1], 1), "chi2": round(chi2, 2)})
    out["d2_visits"] = d2
    out["d5"] = "not checked: no D5 frames are prepared (only D2 and D6)"
    return out


def coverage_counts(positions: list[tuple[str, float, float]]) -> list[dict]:
    """Our image search vs IRSA's own COUNT(*) of spherex.obscore at the same point."""
    from backend.app import archive
    from backend.app.config import COLLECTIONS
    in_list = ",".join(f"'{c}'" for c in COLLECTIONS)
    rows = []
    for name, ra, dec in positions:
        try:
            ours = len(archive.find_images(ra, dec))
            irsa = int(archive.run_query(
                f"SELECT COUNT(*) AS n FROM spherex.obscore WHERE CONTAINS(POINT('ICRS', {ra:.8f}, {dec:.8f}), "
                f"s_region) = 1 AND obs_collection IN ({in_list})")["n"][0])
            rows.append({"position": name, "ra": ra, "dec": dec, "ours": ours, "irsa_count": irsa,
                         "equal": ours == irsa})
        except archive.ArchiveError as exc:
            rows.append({"position": name, "ra": ra, "dec": dec, "error": str(exc)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--online", action="store_true", help="also compare coverage counts with IRSA")
    parser.add_argument("--json", type=Path, help="write the results here")
    args = parser.parse_args()
    results = {
        "barnard": shift_check("barnard", 2, "hole"),
        "eps_ind_b": shift_check("eps_ind_b", 2, "centroid"),
        "wise0855": wise0855(),
        "rw_aur": {k: load("rw_aur", 2, "lightcurve.json")[k] for k in ("method", "same_wavelength", "comparison")},
        "r_dra": {"reason": load("r_dra", 2, "lightcurve.json")["reason"]},
        "thresholds": {"max_motion_error_px": MAX_MOTION_ERROR_PX,
                       "max_direction_error_deg (ours)": MAX_DIRECTION_ERROR_DEG,
                       "alignment_px": ALIGNMENT_PX},
    }
    if args.online:
        results["coverage"] = coverage_counts([
            ("Barnard's Star", 269.446269, 4.768204),
            ("RA 200, Dec -30 (picked by us, nothing special)", 200.0, -30.0),
            ("RA 10, Dec +60 (picked by us, nothing special)", 10.0, 60.0),
        ])
    text = json.dumps(results, indent=1, default=float)
    print(text)
    if args.json:
        args.json.write_text(text + "\n")


if __name__ == "__main__":
    main()
