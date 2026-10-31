"""Add up the aligned exposures of one visit, weighting each pixel by 1 / sigma².

coadd = sum(w × image) / sum(w),   sigma_coadd = 1 / sqrt(sum(w)),   w = 0 where bad or no value.
Noise drops roughly as 1 / sqrt(number of exposures), so faint objects show up.
"""
import numpy as np


def coadd(aligned: list[dict]) -> dict:
    """One picture from several aligned exposures (all on the same grid)."""
    if not aligned:
        raise ValueError("Nothing to add up")
    images = np.stack([a["image"] for a in aligned])
    sigmas = np.stack([a["sigma"] for a in aligned])
    usable = np.stack([a["covered"] & ~a["bad"] for a in aligned]) & np.isfinite(images) & (sigmas > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        weights = np.where(usable, 1.0 / sigmas ** 2, 0.0)
        total = weights.sum(axis=0)
        image = np.where(total > 0, (weights * np.nan_to_num(images)).sum(axis=0) / total, np.nan)
        sigma = np.where(total > 0, 1.0 / np.sqrt(total), np.nan)
    inside = np.any([a["inside"] for a in aligned], axis=0)
    covered = total > 0
    # No usable exposure: "bad" if some exposure had a value there but it was flagged,
    # otherwise "no value" (outside, or NaN in every exposure, e.g. a saturated core).
    had_value = np.any([a["covered"] for a in aligned], axis=0)
    bad = inside & ~covered & had_value
    n_inside = max(int(inside.sum()), 1)
    return {
        "image": image,
        "sigma": sigma,
        "bad": bad,
        "covered": covered,
        "inside": inside,
        "n_used": usable.sum(axis=0),
        "pct_flagged": round(100 * bad.sum() / n_inside, 1),
        "pct_no_value": round(100 * (inside & ~covered & ~had_value).sum() / n_inside, 1),
        "pct_covered": round(100 * inside.mean(), 1),
    }
