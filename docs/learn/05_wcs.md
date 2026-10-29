# Lesson 5 — Which pixel is which star? WCS (World Coordinate System)

> Goal of this lesson: you understand how a pixel (x, y) in an image is connected
> to a real sky position (RA, Dec), and why this is needed before comparing images.

---

## 5.1 The problem

An image is just a grid of numbers. Pixel (1000, 1000) has some brightness.
But **where on the sky** is that pixel pointing?

Without this information we cannot:

- say which star we see,
- compare two images taken with different pointings,
- look up an object in a catalog,
- measure how far something moved on the sky.

**WCS** is the "map legend" that converts:

```
pixel coordinates (x, y)   <-->   world coordinates (RA, Dec)
```

It is stored as keywords in the FITS header.

---

## 5.2 An analogy: a city map

Imagine a paper map of Kathmandu with a grid.

- You know that the **reference point** on the paper (e.g. the centre mark) is **Ratna Park**.
- You know the **scale**: 1 cm on paper = 100 m in the city.
- You know the map may be **rotated** (north is not straight up).

With these three facts, you can convert any paper position to a real place.

WCS stores exactly these three things for the sky:

| Map idea | WCS keyword | Meaning |
|----------|-------------|---------|
| Reference point on paper | `CRPIX1`, `CRPIX2` | Reference **pixel** (x, y) |
| Real place of that point | `CRVAL1`, `CRVAL2` | **RA, Dec** at the reference pixel (degrees) |
| Scale and rotation | `CDELT` / `CD` / `PC` matrix | Degrees per pixel, and rotation |
| Type of map projection | `CTYPE1`, `CTYPE2` | How the curved sky is flattened |

---

## 5.3 Our real WCS

From the IMAGE header of `2025W23_1C_0543_1.fits`:

```
CTYPE1 = 'RA---TAN-SIP'
CTYPE2 = 'DEC--TAN-SIP'
CRPIX1 = 1020.5
CRPIX2 = 1020.5
CRVAL1 = 303.368265969    (RA  in degrees)
CRVAL2 = 41.6605006349    (Dec in degrees)
A_ORDER = 3               (distortion polynomial order)
```

Meaning:

- The reference pixel is **(1020.5, 1020.5)** = the **centre** of the 2040 × 2040 image (FITS counting from 1).
- At that pixel the sky position is **RA 303.37°, Dec 41.66°**.
- Pixel scale (computed by Astropy from the header): **6.15″ per pixel**.

---

## 5.4 Projections: flattening a ball onto paper

The sky is a ball; an image is flat. You cannot flatten a ball without some stretching (like peeling an orange).

A **projection** is a rule for flattening. The most common for telescope images is **TAN** (gnomonic / tangent-plane):

```
      flat detector (tangent plane)
   ---------------------------------
            \      |      /
             \     |     /
              \    |    /
          .-"""\"""|"""/"""-.
        /       \  |  /       \      <- sky sphere
               (centre)
```

Imagine a flat sheet touching the sky ball at one point (the reference point). Each sky direction is projected onto the sheet.
Near the touching point, there is almost no stretching. Far away, stretching grows.

---

## 5.5 SIP: correcting the lens distortion

Real telescopes are not perfect. The optics bend the image a little, especially near the edges
(like a phone camera's wide-angle lens bending straight lines).

**SIP** (Simple Imaging Polynomial) is a small correction formula added on top of TAN.
`A_ORDER = 3` means it uses a polynomial up to power 3.

So `RA---TAN-SIP` means: "tangent projection + SIP distortion correction". Astropy handles this automatically.

---

## 5.6 The 0-based vs 1-based trap

- FITS standard: the first pixel is **1**.
- Python/NumPy/Astropy functions `pixel_to_world`: the first pixel is **0**.

So the image centre is:

| System | Centre pixel |
|--------|--------------|
| FITS (1-based) | 1020.5 |
| Python (0-based) | 1019.5 |

Mixing these up gives a **1-pixel error = 6″** — enough to confuse a moving object with a star!
Rule: in Python, always use Astropy's `pixel_to_world` / `world_to_pixel` (they use 0-based pixels).

---

## 5.7 Python: pixel ↔ sky

```python
from astropy.io import fits
from astropy.wcs import WCS

with fits.open("data/raw/2025W23_1C_0543_1.fits") as hdul:
    wcs = WCS(hdul["IMAGE"].header)

# pixel -> sky (0-based pixels)
sky = wcs.pixel_to_world(1019.5, 1019.5)
print(sky.ra.deg, sky.dec.deg)      # about 303.368, 41.658

# sky -> pixel
x, y = wcs.world_to_pixel(sky)
print(x, y)                         # back to ~1019.5, 1019.5  (round trip!)

# pixel scale
import numpy as np
scale = np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix))) * 3600
print(scale, "arcsec/pixel")        # ~6.15
```

Note: the centre gives RA 303.368°, Dec 41.658° — very close to CRVAL (the tiny difference, about one pixel, comes from the distortion terms stored in the header).

A **round trip** (pixel → sky → pixel) returning the same pixel is a good test that WCS is used correctly. We will write this as an automatic test.

---

## 5.8 Why WCS is essential for finding changes

Our 4 SPHEREx images were taken from **different pointings**. Their centres (CRVAL) are:

| File | Centre RA | Centre Dec |
|------|-----------|------------|
| 2025W18 | 303.96° | 40.36° |
| 2025W23 | 303.37° | 41.66° |
| 2025W45 | 306.67° | 42.95° |
| 2026W24 | 304.13° | 44.07° |

The same star falls on **different pixels** in each image. If we subtract image B − image A pixel by pixel, we subtract **different stars**. Garbage!

Solution (already in our prototype, `processing/register.py`):

1. Choose one common sky grid (a new WCS).
2. Use each image's WCS to **reproject** (resample) it onto that common grid.
3. Now the same pixel = the same sky position in all images → comparison makes sense.

(And in Lesson 6 you will see a SPHEREx-specific problem that remains even after this.)

---

## 5.9 Summary

- **WCS** converts pixel (x, y) ↔ sky (RA, Dec), using header keywords.
- `CRPIX` = reference pixel, `CRVAL` = its sky position, `CD`/`CDELT`/`PC` = scale and rotation, `CTYPE` = projection.
- Our files use **TAN-SIP**: tangent projection + distortion correction; scale **6.15″/pixel**.
- FITS pixels start at **1**, Astropy functions at **0**.
- Different pointings → reproject onto a **common grid** before comparing.

## 5.10 Self-check

1. What does `CRVAL` mean, and what does `CRPIX` mean?
2. Why do we need SIP distortion for a wide-field telescope?
3. What is the image centre in 0-based pixels for a 2040 × 2040 image?
4. If two images have different WCS, why can't we subtract them pixel by pixel?
5. What is a "round trip" test and why is it useful?

## 5.11 Try it yourself

Convert the 4 corner pixels (0,0), (2039,0), (0,2039), (2039,2039) of one image to RA/Dec.
How many degrees wide is the image? (Should be about 3.5°.)
