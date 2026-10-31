"""Step 2b, part 1: Gaia DR3 stars in the frames' field, moved to the date of each visit.

Gaia gives every star's position for 2016.0 and its proper motion. Moving each star to the time of
each SPHEREx visit tells us where it *should* be in that frame; a star that sits on its markers in
every visit is moving as Gaia says. Parallax (the yearly wobble, at most the parallax value) is not
applied; for Barnard's Star that is 0.55″ = 0.09 SPHEREx pixels.

    python -m backend.app.gaia frontend/frames/barnard/d2      # writes gaia.json next to the manifest
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.app import archive
from backend.app.align import target_grid
from backend.app.config import GAIA_EPOCH, GAIA_TABLE, PIXEL_SCALE_ARCSEC
from backend.app.coords import mjd_to_year
from backend.app.motion import position_at, separation_arcsec

FORMAT = "spherex-blink-gaia/1"
TARGET_MATCH_ARCSEC = 3.0  # half a SPHEREx pixel
MAX_MOTION_ARCSEC_PER_YEAR = 11.0  # Barnard's Star, the fastest star, moves 10.4″/yr
MARGIN_PX = 1.0  # keep stars up to one pixel outside the frame


def gaia_stars(ra: float, dec: float, radius_deg: float) -> list[dict]:
    """Every Gaia DR3 source within radius_deg of (ra, dec), as Gaia lists it (positions for 2016.0).

    source_id is text, because it is larger than JavaScript can hold exactly as a number.
    pmra/pmdec/parallax are None for sources without a motion solution (Gaia "2-parameter" sources).
    """
    table = archive.run_query(f"""
        SELECT source_id, ra, dec, pmra, pmdec, parallax, phot_g_mean_mag, ref_epoch
        FROM {GAIA_TABLE}
        WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.8f}, {dec:.8f}, {radius_deg:.6f})) = 1
    """)

    def value(row, name):
        v = row[name]
        return None if np.ma.is_masked(v) or not np.isfinite(float(v)) else float(v)

    stars = []
    for row in table:
        epoch = value(row, "ref_epoch")
        if epoch != GAIA_EPOCH:
            raise archive.ArchiveError(f"Gaia source {row['source_id']} has ref_epoch {epoch}, expected {GAIA_EPOCH}")
        stars.append({
            "source_id": str(row["source_id"]),
            "ra": float(row["ra"]),
            "dec": float(row["dec"]),
            "pmra": value(row, "pmra"),
            "pmdec": value(row, "pmdec"),
            "parallax": value(row, "parallax"),
            "g_mag": value(row, "phot_g_mean_mag"),
        })
    return stars


def search_radius_deg(fov_arcmin: float, years_from_gaia: float) -> float:
    """Half the frame's diagonal plus the farthest any star could have moved since 2016.0."""
    half_diagonal = fov_arcmin / 60 / 2 * math.sqrt(2)
    return half_diagonal + (MAX_MOTION_ARCSEC_PER_YEAR * abs(years_from_gaia) + MARGIN_PX * PIXEL_SCALE_ARCSEC) / 3600


def star_at(star: dict, year: float) -> tuple[float, float]:
    if star["pmra"] is None or star["pmdec"] is None:
        return star["ra"], star["dec"]
    return position_at(star["ra"], star["dec"], star["pmra"], star["pmdec"], GAIA_EPOCH, year)


def markers(ra: float, dec: float, fov_arcmin: float, frames: list[dict], stars: list[dict],
            target_year: float | None = None) -> dict:
    """Where each Gaia star should be in each frame, in PNG pixels (x to the right, y down, 0 = first
    pixel's centre), plus which star is the target (nearest to the grid centre at target_year)."""
    grid, size = target_grid(ra, dec, fov_arcmin)
    years = [mjd_to_year(f["mjd"]) for f in frames]
    out, target = [], None
    for star in stars:
        xy = []
        for year in years:
            s_ra, s_dec = star_at(star, year)
            x, y = grid.world_to_pixel_values(s_ra, s_dec)
            xy.append([round(float(x), 3), round(float(size - 1 - y), 3)])  # PNG rows: north at the top
        if not any(-0.5 - MARGIN_PX <= x <= size - 0.5 + MARGIN_PX and -0.5 - MARGIN_PX <= y <= size - 0.5 + MARGIN_PX
                   for x, y in xy):
            continue
        entry = {
            "source_id": star["source_id"],
            "g_mag": None if star["g_mag"] is None else round(star["g_mag"], 2),
            "pmra": star["pmra"] and round(star["pmra"], 2),
            "pmdec": star["pmdec"] and round(star["pmdec"], 2),
            "parallax": star["parallax"] and round(star["parallax"], 2),
            "has_motion": star["pmra"] is not None,
            "xy": xy,
        }
        out.append(entry)
        if target_year is not None:
            sep = separation_arcsec(*star_at(star, target_year), ra, dec)
            if sep <= TARGET_MATCH_ARCSEC and (target is None or sep < target[1]):
                target = (entry, sep)
    if target:
        target[0]["target"] = True
    out.sort(key=lambda s: (s["g_mag"] is None, s["g_mag"] if s["g_mag"] is not None else 0))
    return {
        "stars": out,
        "target_match": {"source_id": target[0]["source_id"], "sep_arcsec": round(target[1], 3)} if target else None,
    }


def write_gaia(folder: Path) -> dict:
    """gaia.json for a frames folder (docs/plan/FRAMES_FORMAT.md, section 6)."""
    manifest = json.loads((folder / "manifest.json").read_text())
    ra, dec, fov = manifest["ra"], manifest["dec"], manifest["fov_arcmin"]
    frames = manifest["frames"]
    years = [mjd_to_year(f["mjd"]) for f in frames]
    radius = search_radius_deg(fov, max(abs(y - GAIA_EPOCH) for y in years))
    stars = gaia_stars(ra, dec, radius)
    # the grid centre is the SIMBAD position moved to 2026.0 (render.POSITION_YEAR)
    result = markers(ra, dec, fov, frames, stars, target_year=2026.0)
    gaia = {
        "format": FORMAT,
        "catalogue": f"Gaia DR3 ({GAIA_TABLE} at NASA/IPAC IRSA)",
        "catalogue_epoch": GAIA_EPOCH,
        "query": {"ra": ra, "dec": dec, "radius_deg": round(radius, 6), "n_returned": len(stars)},
        "method": f"each Gaia DR3 position (epoch {GAIA_EPOCH}) moved in a straight line with its proper "
                  "motion to the frame's MJD; parallax not applied; stars without a Gaia proper motion "
                  "stay at their 2016.0 position",
        "pixel_convention": "PNG pixels: x to the right (west), y down (south), 0 = centre of the first pixel",
        "target_match_rule": f"the Gaia star nearest the grid centre at 2026.0, if within {TARGET_MATCH_ARCSEC}″",
        "target_match": result["target_match"],
        "frames": [{"epoch_id": f["epoch_id"], "mjd": f["mjd"], "year": round(y, 4)} for f, y in zip(frames, years)],
        "stars": result["stars"],
        "made_by": "backend/app/gaia.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "ESA Gaia DR3, via NASA/IPAC IRSA",
    }
    (folder / "gaia.json").write_text(json.dumps(gaia, indent=1, ensure_ascii=False) + "\n")
    return gaia


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", type=Path, nargs="+", help="e.g. frontend/frames/barnard/d2")
    args = parser.parse_args()
    for folder in args.folders:
        g = write_gaia(folder)
        match = g["target_match"]
        target = next((s for s in g["stars"] if s.get("target")), None)
        moved = ""
        if target:
            (x0, y0), (x1, y1) = target["xy"][0], target["xy"][-1]
            moved = f", target moves {math.hypot(x1 - x0, y1 - y0):.2f} px first -> last visit"
        print(f"{folder}: {len(g['stars'])} Gaia stars in the frame ({g['query']['n_returned']} returned), "
              f"target match {match}{moved}")


if __name__ == "__main__":
    main()
