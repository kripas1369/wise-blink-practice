"""Spot evidence (spots.json): the strongest spots of each difference map, and what each could be.

    python -m backend.app.spots frontend/frames/*/d*

A spot is a connected group of pixels (8 neighbours) with |z| >= 5 in one difference map (diff.json),
brighter in B (z > 0) or fainter in B (z < 0). For each: position, peak and size, how stretched it is,
the nearest Gaia DR3 star on the date it belongs to (B for brighter, A for fainter), "possible
artifact" flags, and three plain notes: why it was selected, what else could explain it, what would
confirm it. A spot is never called a new object.

Each frame also gets its observer: SPHEREx's position and velocity (X_SC ... VZ_SC, km and km/s,
"GEOCENTER" in the SPHEREx headers; we assume ICRF axes, the header does not say) for the exposure
closest to the frame's mean time, read from the cached cutouts, for the known-object check
(backend/app/known_objects.py).
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy import ndimage

from backend.app.align import target_grid
from backend.app.config import CACHE_DIR

FORMAT = "spherex-blink-spots/1"
MAX_SPOTS = 10            # per pair, strongest |z| first
NEAR_GAIA_PX = 1.5        # ours
LONG_THIN_RATIO = 3.0     # ours: major / minor axis of the |z|-weighted shape
LONG_THIN_MIN_PX = 4
LARGE_PX = 20             # ours: SPHEREx's PSF is about one pixel wide, a point source leaves a few pixels
SCATTER_WARN = 1.5        # the same limit as the website's difference warnings
STATE_KEYS = ("X_SC", "Y_SC", "Z_SC", "VX_SC", "VY_SC", "VZ_SC")


def observer(folder: Path, manifest: dict, frame_index: int) -> dict:
    """SPHEREx's state for the exposure closest to the frame's mean time, from the cached cutout."""
    path = folder / "exposures.fits"
    if not path.exists():
        return {"available": False, "reason": "no exposures.fits for these frames"}
    table = fits.getdata(path, "EXPOSURES")
    rows = [r for r in table if int(r["FRAME"]) == frame_index]
    if not rows:
        return {"available": False, "reason": "no exposures listed for this visit"}
    mjds = [float(r["MJD"]) for r in rows]
    ref = min(rows, key=lambda r: abs(float(r["MJD"]) - manifest["frames"][frame_index]["mjd"]))
    obs_id = str(ref["OBS_ID"]).strip()
    out = {"obs_id": obs_id, "exposures_mjd_range": [round(min(mjds), 5), round(max(mjds), 5)],
           "exposures_span_hours": round((max(mjds) - min(mjds)) * 24, 2)}
    cutout = next((CACHE_DIR / "cutouts").glob(f"{obs_id}_D{manifest['band']}_*.fits"), None)
    if cutout is None:
        return {**out, "available": False, "reason": f"the cutout of {obs_id} is not in the cache"}
    h = fits.getheader(cutout, "IMAGE")
    if any(k not in h for k in STATE_KEYS + ("MJD-AVG",)):
        return {**out, "available": False, "reason": f"{obs_id} has no spacecraft position in its header"}
    return {**out, "available": True, "mjd": float(h["MJD-AVG"]),
            "xyz_km": [round(float(h[k]), 3) for k in STATE_KEYS[:3]],
            "vxyz_kms": [round(float(h[k]), 6) for k in STATE_KEYS[3:]],
            "system": f"{h.get('XYZ_SC_SYSTEM', '?')} (axes assumed ICRF)"}


def shape(z: np.ndarray, mask: np.ndarray) -> float | None:
    """Major / minor axis ratio of the |z|-weighted pixels, None for fewer than 3 pixels."""
    ys, xs = np.nonzero(mask)
    if len(xs) < 3:
        return None
    w = np.abs(z[mask])
    cx, cy = (w * xs).sum() / w.sum(), (w * ys).sum() / w.sum()
    cov = np.cov(np.vstack([xs - cx, ys - cy]), aweights=w) + np.eye(2) / 12   # a pixel has width
    lo, hi = np.linalg.eigvalsh(cov)
    return round(float(math.sqrt(hi / lo)), 2)


def gaia_star(gaia: dict | None, frame_index: int, xy: tuple[float, float]) -> dict | None:
    """The brightest Gaia star within NEAR_GAIA_PX (a faint neighbour cannot explain a big spot), else the nearest."""
    if not gaia or not gaia["stars"]:
        return None
    dist = [(math.hypot(s["xy"][frame_index][0] - xy[0], s["xy"][frame_index][1] - xy[1]), s) for s in gaia["stars"]]
    near = [(d, s) for d, s in dist if d <= NEAR_GAIA_PX]
    if near:
        d, best = min(near, key=lambda ds: (ds[1]["g_mag"] is None, ds[1]["g_mag"] or 0, ds[0]))
        chosen = f"brightest of {len(near)} within {NEAR_GAIA_PX} px"
    else:
        d, best = min(dist, key=lambda ds: ds[0])
        chosen = "nearest"
    return {"source_id": best["source_id"], "g_mag": best["g_mag"], "distance_px": round(d, 2),
            "target": bool(best.get("target")), "chosen": chosen}


def notes(spot: dict, pair: dict, star: dict | None) -> dict:
    sign = "brighter" if spot["sign"] > 0 else "fainter"
    visit = "B" if spot["sign"] > 0 else "A"
    why = (f"{spot['n_pixels']} pixel{'s' if spot['n_pixels'] > 1 else ''} at {spot['peak_sigma']:+.1f}σ: "
           f"{sign} in B than in A by more than 5σ of the noise the files give (VARIANCE).")
    near = star is not None and star["distance_px"] <= NEAR_GAIA_PX
    if near:
        g = f"G {star['g_mag']}" if star["g_mag"] is not None else "no G magnitude"
        else_ = [f"It sits {star['distance_px']} px from Gaia DR3 {star['source_id']} ({g}"
                 + (", the target" if star["target"] else "") + f"; {star['chosen']}) on visit " + visit + "'s date.",
                 "A star leaves spots like this when it moves, changes brightness, or when the two visits see "
                 "different wavelengths or PSF shapes (worse for bright stars)."]
    else:
        else_ = ["No Gaia DR3 star within 1.5 px on visit " + visit + "'s date.",
                 "It could be a solar-system object, a source too faint or too red for Gaia that changed, "
                 "a cosmic ray or detector artifact that survived the add-up, or noise."]
    if pair["scatter_sigma"] > SCATTER_WARN:
        else_.append(f"This pair scatters {pair['scatter_sigma']}× more than the files' noise predicts, so 5σ here is "
                     "weaker evidence than it sounds.")
    confirm = ["It appears in several single exposures of visit " + visit + " (click the pixel in the flipbook for its light curve).",
               "It appears in another detector on the same visit."]
    if not near:
        confirm.append("For a solar-system object: a known object at this place and time (check below), and a shift "
                       "between the exposures of one visit.")
    return {"why": why, "what_else": else_, "confirm": confirm}


def spots_for_pair(pair: dict, gaia: dict | None, grid, size: int, limit: float) -> dict:
    z = np.array([[np.nan if v is None else v for v in row] for row in pair["z"]], float)
    striped = np.isnan(z)
    zz = np.nan_to_num(z)
    found = []
    for sign in (1, -1):
        labels, n = ndimage.label(sign * zz >= limit, structure=np.ones((3, 3)))
        for k in range(1, n + 1):
            mask = labels == k
            ys, xs = np.nonzero(mask)
            w = np.abs(zz[mask])
            peak = int(np.argmax(w))
            cx, cy = float((w * xs).sum() / w.sum()), float((w * ys).sum() / w.sum())
            frame = pair["b"] if sign > 0 else pair["a"]
            sky = grid.pixel_to_world(cx, size - 1 - cy)
            grown = ndimage.binary_dilation(mask, structure=np.ones((3, 3)))
            ratio = shape(zz, mask)
            flags = []
            if ratio is not None and ratio >= LONG_THIN_RATIO and mask.sum() >= LONG_THIN_MIN_PX:
                flags.append(f"long and thin (axis ratio {ratio})")
            if mask.sum() >= LARGE_PX:
                flags.append(f"very large ({int(mask.sum())} pixels)")
            if (grown & striped).any():
                flags.append("next to flagged or no-value pixels")
            if xs.min() == 0 or ys.min() == 0 or xs.max() == size - 1 or ys.max() == size - 1:
                flags.append("touches the frame edge")
            spot = {"sign": sign, "peak_sigma": round(float(zz[ys[peak], xs[peak]]), 1),
                    "peak_xy": [int(xs[peak]), int(ys[peak])], "xy": [round(cx, 2), round(cy, 2)],
                    "ra": round(float(sky.ra.deg), 6), "dec": round(float(sky.dec.deg), 6),
                    "n_pixels": int(mask.sum()), "axis_ratio": ratio, "frame": frame, "artifact_flags": flags}
            star = gaia_star(gaia, _index(gaia, frame), (cx, cy)) if gaia else None
            spot["gaia_star"] = star
            spot.update(notes(spot, pair, star))
            found.append(spot)
    found.sort(key=lambda s: -abs(s["peak_sigma"]))
    return {"a": pair["a"], "b": pair["b"], "n_spots": len(found), "spots": found[:MAX_SPOTS]}


def _index(gaia: dict, epoch_id: int) -> int:
    return next(i for i, f in enumerate(gaia["frames"]) if f["epoch_id"] == epoch_id)


def build_spots(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    diff = json.loads((folder / "diff.json").read_text())
    gaia_path = folder / "gaia.json"
    gaia = json.loads(gaia_path.read_text()) if gaia_path.exists() else None
    grid, size = target_grid(manifest["ra"], manifest["dec"], manifest["fov_arcmin"])
    index = {f["epoch_id"]: i for i, f in enumerate(manifest["frames"])}
    return {
        "format": FORMAT, "target": manifest["target"], "band": manifest["band"], "limit_sigma": diff["limit_sigma"],
        "rules": {"max_spots_per_pair": MAX_SPOTS, "near_gaia_px": NEAR_GAIA_PX, "long_thin_ratio": LONG_THIN_RATIO,
                  "large_px": LARGE_PX, "source": "ours"},
        "observers": [{"epoch_id": f["epoch_id"], **observer(folder, manifest, index[f["epoch_id"]])}
                      for f in manifest["frames"]],
        "pairs": [spots_for_pair(p, gaia, grid, size, diff["limit_sigma"]) for p in diff["pairs"]],
        "made_by": "backend/app/spots.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def write_spots(folder: Path) -> dict:
    spots = build_spots(folder)
    (folder / "spots.json").write_text(json.dumps(spots, indent=1, ensure_ascii=False) + "\n")
    return spots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path)
    args = parser.parse_args()
    for folder in args.folders:
        s = write_spots(folder)
        n_obs = sum(o["available"] for o in s["observers"])
        print(f"{folder}: " + ", ".join(f"{p['a']}-{p['b']}: {p['n_spots']}" for p in s["pairs"])
              + f" spots; spacecraft position for {n_obs}/{len(s['observers'])} visits")


if __name__ == "__main__":
    main()
