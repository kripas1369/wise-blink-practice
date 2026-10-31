"""Rough positions of a star in one frame (epoch<i>.fits loaded by diff.load_frame), PNG pixels.

    centroid  = brightness-weighted centre of the 5 × 5 pixels around a predicted position, after
                removing the median sky of the frame; only if all 25 pixels are usable
    hole      = centre of the flagged / no-value pixels within 3 px of the prediction (a saturated core
                is centred on the star, so this is a rough position for very bright stars)

SPHEREx pixels are 6.15″ and the PSF is about one pixel wide, so a centroid moves by less than the
star when the star is not centred on a pixel (pixel phase); treat these as rough.
"""
import numpy as np

BOX = 2      # 5 × 5 box
HOLE_RADIUS = 3


def north_up(a: np.ndarray) -> np.ndarray:
    return a[::-1]


def centroid(frame: dict, x0: float, y0: float):
    image, usable = north_up(frame["image"]), north_up(frame["usable"])
    cx, cy = int(round(x0)), int(round(y0))
    if not (BOX <= cx < image.shape[1] - BOX and BOX <= cy < image.shape[0] - BOX):
        return None
    box = (slice(cy - BOX, cy + BOX + 1), slice(cx - BOX, cx + BOX + 1))
    if not usable[box].all():
        return None
    sky = float(np.median(image[usable]))
    w = np.clip(image[box] - sky, 0, None)
    if w.sum() <= 0:
        return None
    ys, xs = np.mgrid[box]
    return float((w * xs).sum() / w.sum()), float((w * ys).sum() / w.sum())


def hole_centre(frame: dict, x0: float, y0: float):
    unusable = ~north_up(frame["usable"])
    ys, xs = np.nonzero(unusable)
    near = np.hypot(xs - x0, ys - y0) <= HOLE_RADIUS
    if near.sum() < 3:
        return None
    return float(xs[near].mean()), float(ys[near].mean()), int(near.sum())
