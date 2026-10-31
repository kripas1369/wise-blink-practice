"""The spectrum panel's numbers (spectrum.json): the target's brightness against wavelength, per visit,
across every detector that has frames.

    python -m backend.app.spectrum frontend/frames/eps_ind_b

SPHEREx's six detectors see the same sky at the same time, each through its own wavelength range, so one
visit gives points from 0.75 to 5 µm. Every point is a light-curve point (lightcurve.json of one detector
folder: one exposure, its own wavelength, the same 2 px circle that follows the target); nothing is
measured again here. Points are grouped into visits with the archive's rule (archive.group_epochs).

The circle has no aperture correction, and the PSF is not equally wide in every detector (PSF_FWHM in the
exposure headers), so the circle catches a different share of the light in each detector: a step where
two detectors meet can come from that, not from the star. The file says so.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from astropy.io import fits

from backend.app.archive import EPOCH_GAP_DAYS, EPOCH_MAX_SPAN_DAYS
from backend.app.config import CACHE_DIR
from backend.app.coords import mjd_to_date

FORMAT = "spherex-blink-spectrum/1"
CUTOUTS = CACHE_DIR / "cutouts"


def psf_fwhm(obs_ids: list[str], band: int) -> dict | None:
    """Median PSF_FWHM (″) of the exposures' headers in the cutout cache; None if none is cached."""
    values = []
    for obs_id in obs_ids:
        path = next(iter(sorted(CUTOUTS.glob(f"{obs_id}_D{band}_*.fits"))), None)
        if path is not None:
            value = fits.getheader(path, "IMAGE").get("PSF_FWHM")
            if value is not None:
                values.append(float(value))
    if not values:
        return None
    return {"median_arcsec": round(median(values), 2), "min_arcsec": round(min(values), 2),
            "max_arcsec": round(max(values), 2), "n_exposures": len(values)}


def group_visits(points: list[dict]) -> list[dict]:
    """Visits across detectors, with the archive's rule: a new visit after a gap of more than
    EPOCH_GAP_DAYS, or when it would last longer than EPOCH_MAX_SPAN_DAYS."""
    visits: list[dict] = []
    for p in sorted(points, key=lambda p: p["mjd"]):
        if not visits or p["mjd"] - visits[-1]["mjd_max"] > EPOCH_GAP_DAYS \
                or p["mjd"] - visits[-1]["mjd_min"] > EPOCH_MAX_SPAN_DAYS:
            visits.append({"mjd_min": p["mjd"], "mjd_max": p["mjd"], "points": []})
        visits[-1]["mjd_max"] = p["mjd"]
        visits[-1]["points"].append(p)
    out = []
    for i, v in enumerate(visits):
        pts = sorted(v["points"], key=lambda p: (p["wl_um"] is None, p["wl_um"] or 0))
        mean = sum(p["mjd"] for p in pts) / len(pts)
        out.append({"visit": i, "date": mjd_to_date(mean)[:10], "mjd_range": [v["mjd_min"], v["mjd_max"]],
                    "bands": sorted({p["band"] for p in pts}), "n_points": len(pts), "points": pts})
    return out


def build_spectrum(target_dir: Path) -> dict:
    target_dir = Path(target_dir)
    detectors, points, label, target = [], [], None, target_dir.name
    for folder in sorted(target_dir.glob("d[1-6]")):
        lc_path = folder / "lightcurve.json"
        if not lc_path.exists():
            continue
        manifest = json.loads((folder / "manifest.json").read_text())
        lc = json.loads(lc_path.read_text())
        label = manifest["label"]
        band = manifest["band"]
        info = {"band": band, "band_range_um": manifest["band_range_um"], "method": lc["method"],
                "n_exposures": len(lc["points"]), "position_rule": lc["position_rule"]}
        if lc["method"] == "none":
            info["reason"] = lc["reason"]
        else:
            measured = [p for p in lc["points"] if p["flux_mjy"] is not None and p["wl_um"] is not None]
            info.update(n_measured=len(measured), r_out_px=lc["r_out_px"],
                        neighbours=lc.get("neighbours", []),
                        floor_pct=(lc.get("comparison") or {}).get("scatter_pct"),
                        psf_fwhm=psf_fwhm([p["obs_id"] for p in lc["points"]], band))
            points += [{"band": band, **{k: p[k] for k in ("obs_id", "mjd", "date_iso", "wl_um", "bw_um",
                                                            "flux_mjy", "err_mjy", "n_flagged")}}
                       for p in measured]
        detectors.append(info)
    if not detectors:
        raise FileNotFoundError(f"No detector folder with a light curve in {target_dir}")
    with_points = [d for d in detectors if d["method"] != "none"]
    fwhms = [d["psf_fwhm"]["median_arcsec"] for d in with_points if d.get("psf_fwhm")]
    radii = sorted({d["r_out_px"] for d in with_points}) or ["?"]
    warnings = [
        f"Each point is one exposure: a {'/'.join(map(str, radii))} px circle around the target minus the sky, "
        "with no aperture "
        "correction. The PSF is not equally wide in every detector"
        + (f" (median FWHM {min(fwhms)}–{max(fwhms)}″ here)" if len(fwhms) > 1 else "")
        + ", so the circle catches a different share of the light in each one: a step where two detectors "
        "meet can come from that, not from the star.",
        "The detectors' ranges do not overlap, so no wavelength is measured by two detectors to check them "
        "against each other.",
    ]
    missing = sorted(set(range(1, 7)) - {d["band"] for d in detectors})
    if missing:
        warnings.append("No frames prepared for " + ", ".join(f"D{b}" for b in missing) + ", so those "
                        "wavelengths are missing.")
    for d in detectors:
        if d["method"] == "none":
            warnings.append(f"D{d['band']}: no points. {d['reason']}")
        elif d["neighbours"]:
            stars = ", ".join(f"Gaia DR3 {n['source_id']} (G {n['g_mag']}) at {n['distance_px']} px"
                              for n in d["neighbours"])
            warnings.append(f"D{d['band']}: inside the circle as well: {stars}; its light is in these points.")
    return {
        "format": FORMAT, "target": target, "label": label, "unit": "mJy",
        "detectors": detectors, "visits": group_visits(points),
        "visit_rule": f"exposures closer than {EPOCH_GAP_DAYS:g} days in a row, at most {EPOCH_MAX_SPAN_DAYS:g} "
                      "days per visit (archive.group_epochs)",
        "warnings": warnings,
        "method": "every point comes from one detector's lightcurve.json (backend/app/lightcurve.py); "
                  "points of all detectors grouped into visits by time",
        "made_by": "backend/app/spectrum.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx",
    }


def write_spectrum(target_dir: Path) -> dict:
    spectrum = build_spectrum(target_dir)
    (Path(target_dir) / "spectrum.json").write_text(json.dumps(spectrum, indent=1, ensure_ascii=False) + "\n")
    return spectrum


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("targets", type=Path, nargs="+", help="e.g. frontend/frames/eps_ind_b")
    args = parser.parse_args()
    for target_dir in args.targets:
        s = write_spectrum(target_dir)
        bands = ", ".join(f"D{d['band']}" + ("" if d["method"] != "none" else " (none)") for d in s["detectors"])
        print(f"{target_dir}: {bands}; " + "; ".join(
            f"visit {v['visit'] + 1} {v['date']}: {v['n_points']} points in D{','.join(map(str, v['bands']))}"
            for v in s["visits"]))


if __name__ == "__main__":
    main()
