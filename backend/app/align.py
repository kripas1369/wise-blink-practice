"""Step 2a, part 2: put every cleaned cutout onto one north-up grid around the target.

Only on one shared grid does "the same pixel" mean "the same place in the sky"; without it any
"motion" in the flipbook would be fake. Grid rules: docs/plan/FRAMES_FORMAT.md, section 2.
"""
import numpy as np
from astropy.wcs import WCS
from reproject import reproject_interp

from backend.app.config import PIXEL_SCALE_ARCSEC


def target_grid(ra: float, dec: float, fov_arcmin: float = 3.0) -> tuple[WCS, int]:
    """North-up, east-left TAN grid of SPHEREx-sized pixels centred on (ra, dec)."""
    size = int(round(fov_arcmin * 60 / PIXEL_SCALE_ARCSEC)) | 1  # odd, so the target is a pixel centre
    grid = WCS(naxis=2)
    grid.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    grid.wcs.crval = [ra, dec]
    grid.wcs.crpix = [(size + 1) / 2, (size + 1) / 2]
    grid.wcs.cdelt = [-PIXEL_SCALE_ARCSEC / 3600, PIXEL_SCALE_ARCSEC / 3600]
    return grid, size


def cutout_size_deg(fov_arcmin: float) -> float:
    """A cutout that covers the grid's corners even when the exposure is rotated: diagonal + 5%."""
    return max(0.08, fov_arcmin / 60 * np.sqrt(2) * 1.05)


def align(cleaned: dict, grid: WCS, size: int) -> dict:
    """Reproject image, noise and bad mask onto the grid.

    The reproject footprint is 0 both outside the exposure and at NaN pixels, so an array of ones is
    reprojected too: `inside` = in the exposure, `covered` = in the exposure and has a value.
    """
    shape = (size, size)
    src = cleaned["wcs"]
    image, footprint = reproject_interp((cleaned["image"], src), grid, shape_out=shape)
    variance, _ = reproject_interp((cleaned["sigma"] ** 2, src), grid, shape_out=shape)
    bad, _ = reproject_interp((cleaned["bad"].astype(float), src), grid, shape_out=shape,
                              order="nearest-neighbor")
    _, inside = reproject_interp((np.ones_like(cleaned["image"]), src), grid, shape_out=shape,
                                 order="nearest-neighbor")
    inside = inside > 0
    covered = (footprint > 0) & np.isfinite(image)
    bad = covered & (np.nan_to_num(bad) > 0.5)
    n_inside = max(int(inside.sum()), 1)
    with np.errstate(invalid="ignore"):
        sigma = np.sqrt(variance)
    return {
        "image": np.where(covered, image, np.nan),
        "sigma": np.where(covered, sigma, np.nan),
        "bad": bad,
        "covered": covered,
        "inside": inside,
        "pct_flagged": round(100 * bad.sum() / n_inside, 1),
        "pct_no_value": round(100 * (inside & ~covered).sum() / n_inside, 1),
        "pct_covered": round(100 * inside.mean(), 1),
    }
