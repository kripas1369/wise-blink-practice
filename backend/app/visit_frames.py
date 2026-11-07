"""Inside one visit (visits.json): every single exposure of each visit, in time order, to flip through.

    python -m backend.app.visit_frames frontend/frames/*/d*  [--no-known]

The visit frames (epoch<i>.png) add up the 3-21 exposures SPHEREx took over hours to weeks; here each one is
shown alone, from exposures.fits (already lined up on the frames grid). For each exposure:
- visit<i>_exp<k>.png: the picture, with the frames' own brightness scale (manifest "scale");
- visit<i>_exp<k>_flags.png: its officially flagged pixels;
- visit<i>_exp<k>_res.png: the exposure minus the median of the visit's other exposures, divided by its noise
  (grey, ±RESIDUAL_SIGMA), only for visits with at least MIN_FOR_RESIDUAL exposures. Stars mostly cancel; a
  moving object leaves a bright spot where it is now (the dark spot where it was is spread over the median).
Known asteroids and comets inside the frame at each exposure time come from NASA JPL (field_objects.py).

Each exposure in a band is at a different wavelength (SPHEREx's linear variable filter), so a star that
changes brightness from one exposure to the next may be changing colour, not brightness.
"""
import argparse
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.time import Time

from backend.app.align import target_grid
from backend.app.field_objects import CLUSTER_HOURS, FIELD_VMAX, objects_in_exposures
from backend.app.lightcurve import load_exposures
from backend.app.render import save_flags_png, save_png
from backend.app.spots import exposure_state

FORMAT = "spherex-blink-visits/1"
RESIDUAL_SIGMA = 5.0
MIN_FOR_RESIDUAL = 3


def residual(images: np.ndarray, sigmas: np.ndarray, usable: np.ndarray, k: int) -> np.ndarray:
    """(exposure k − median of the others) / its sigma; NaN where k or all the others have no usable value."""
    others = np.delete(np.where(usable, images, np.nan), k, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        median = np.nanmedian(others, axis=0)
        z = (images[k] - median) / sigmas[k]
    return np.where(usable[k] & np.isfinite(z), z, np.nan)


def save_residual_png(z: np.ndarray, path: Path) -> None:
    save_png(z, np.isfinite(z), {"vmin": -RESIDUAL_SIGMA, "vmax": RESIDUAL_SIGMA, "stretch": "linear"}, path)


def build_visits(folder: Path, known: bool = True, write_pngs: bool = True) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    ex = load_exposures(folder)
    size = manifest["size_px"]
    usable = ex["has_value"] & ~ex["bad"] & np.isfinite(ex["image"]) & (ex["sigma"] > 0)
    exposures = []
    for k in range(len(ex["mjd"])):
        state = exposure_state(ex["obs_id"][k], manifest["band"]) if known else {"available": False}
        exposures.append({"k": k, "mjd": float(state.get("mjd", ex["mjd"][k])), "observer": state})

    answers = {}
    known_note = "not asked (--no-known)"
    if known:
        grid, _ = target_grid(manifest["ra"], manifest["dec"], manifest["fov_arcmin"])
        answers = objects_in_exposures(exposures, manifest["ra"], manifest["dec"], grid, size)
        known_note = (f"NASA JPL: small-body search (first pass) for candidates brighter than V {FIELD_VMAX:g} per "
                      f"group of exposures within {CLUSTER_HOURS:g} h, then Horizons positions at each exposure time "
                      "seen from SPHEREx (its position in the exposure header)")

    visits = []
    for i, frame in enumerate(manifest["frames"]):
        ks = [k for k in range(len(ex["mjd"])) if ex["frame"][k] == i]
        ks.sort(key=lambda k: ex["mjd"][k])
        rows = []
        for n, k in enumerate(ks):
            stem = f"visit{i}_exp{n}"
            res_png = None
            if write_pngs:
                save_png(ex["image"][k], ex["has_value"][k], manifest["scale"], folder / f"{stem}.png")
                save_flags_png(ex["bad"][k], folder / f"{stem}_flags.png")
            if len(ks) >= MIN_FOR_RESIDUAL:
                res_png = f"{stem}_res.png"
                if write_pngs:
                    z = residual(ex["image"][ks], ex["sigma"][ks], usable[ks], n)
                    save_residual_png(z, folder / res_png)
            wl, bw = ex["wl_um"][k], ex["bw_um"][k]
            n_pix = size * size
            rows.append({
                "png": f"{stem}.png", "flags_png": f"{stem}_flags.png", "residual_png": res_png,
                "obs_id": ex["obs_id"][k], "mjd": round(float(ex["mjd"][k]), 6),
                "date_iso": Time(ex["mjd"][k], format="mjd", scale="utc").isot[:19],
                "hours_from_first": round(float(ex["mjd"][k] - ex["mjd"][ks[0]]) * 24, 3),
                "wl_um": None if np.isnan(wl) else round(float(wl), 4),
                "bw_um": None if np.isnan(bw) else round(float(bw), 4),
                "pct_flagged": round(100 * float(ex["bad"][k].sum()) / n_pix, 2),
                "pct_no_value": round(100 * float((~ex["has_value"][k]).sum()) / n_pix, 2),
                "known": answers.get(k, {"outcome": "not_asked"}),
            })
        span = rows[-1]["hours_from_first"] if rows else 0.0
        visits.append({"frame": i, "epoch_id": frame["epoch_id"], "date_iso": frame["date_iso"],
                       "n_exposures": len(rows), "span_hours": span, "exposures": rows})

    return {
        "format": FORMAT, "target": manifest["target"], "band": manifest["band"], "size_px": size,
        "scale": manifest["scale"],
        "residual": {"sigma_range": RESIDUAL_SIGMA, "min_exposures": MIN_FOR_RESIDUAL,
                     "rule": "exposure minus the median of the visit's other exposures, divided by the exposure's "
                             "sigma (VARIANCE); flagged pixels left out"},
        "known_objects": known_note, "known_v_max": FIELD_VMAX if known else None,
        "notes": [
            "Each exposure is at a slightly different wavelength (SPHEREx's linear variable filter): a star "
            "that changes brightness between exposures may be changing colour, not brightness.",
            "A single exposure has about √n times the noise of the visit frame made from n exposures.",
            "Known-object positions are JPL predictions, not detections; an object fainter than SPHEREx's limit "
            "is marked but will not be seen.",
            "A moving spot with no JPL object is not a new object: it can be a cosmic ray, an artefact or an "
            "object fainter in JPL's lists than here.",
        ],
        "visits": visits,
        "made_by": "backend/app/visit_frames.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def write_visits(folder: Path, known: bool = True) -> dict:
    folder = Path(folder)
    for old in folder.glob("visit*_exp*.png"):
        old.unlink()
    result = build_visits(folder, known=known)
    (folder / "visits.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path, help="e.g. frontend/frames/rw_aur/d1")
    parser.add_argument("--no-known", action="store_true", help="skip the NASA JPL known-object lookup")
    args = parser.parse_args()
    for folder in args.folders:
        r = write_visits(folder, known=not args.no_known)
        for v in r["visits"]:
            names = sorted({o["name"] for e in v["exposures"] for o in e["known"].get("objects", [])})
            outcomes = sorted({e["known"]["outcome"] for e in v["exposures"]})
            print(f"{folder} visit {v['frame']}: {v['n_exposures']} exposures over {v['span_hours']:.1f} h; "
                  f"JPL {'/'.join(outcomes)} {', '.join(names[:6])}")


if __name__ == "__main__":
    main()
