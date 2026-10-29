# Lesson 6 — The telescope: how SPHEREx works (the most important lesson)

> Goal of this lesson: you understand what SPHEREx is, why every pixel sees a
> different colour (the "LVF"), and why this is both our biggest problem and our
> biggest opportunity.

---

## 6.1 What is SPHEREx?

**SPHEREx** = **S**pectro-**P**hotometer for the **H**istory of the Universe, **E**poch of **R**eionization and Ices **Ex**plorer.

- NASA space telescope, launched **March 2025**, all-sky survey started **early May 2025**.
- Orbits the Earth, passing over the poles, and scans the sky strip by strip.
- Maps the **whole sky 4 times in 2 years** (about every 6 months).
- Takes **spectra** in **102 colours (channels)** from **0.75 to 5.0 µm** (near-infrared).
- Pixel size **6.15″** (we measured). Each detector image covers about **3.5° × 3.5°**.
- Sensitivity (5σ): about **19.5 – 19.9 AB mag** for most wavelengths.

### Why was it built? (its main science)

1. **Inflation** — how the universe expanded in its first fraction of a second (from the 3D positions of millions of galaxies).
2. **Galaxy history** — the total glow of all galaxies over cosmic time.
3. **Ices** — water and other ices in the clouds where stars and planets form.

**Planet X and asteroids are NOT its main goals** — they are **bonus science**. But because every image contains hundreds of moving Solar System objects, the SPHEREx team expects measurements of about **100,000 asteroids** (≈10,000 with good spectra). SPHEREx has already observed the interstellar comet **3I/ATLAS** and found **CO₂ gas** around it.

---

## 6.2 Photo vs spectrum

- A normal camera gives **one brightness per pixel** (or 3 for red/green/blue).
- A **spectrum** is brightness **at many wavelengths** — like splitting sunlight into a rainbow with a prism and measuring each colour.

A spectrum is a **fingerprint**: water ice, rock types, gases each absorb specific wavelengths.
Example: rocky (S-type) asteroids have a dip near 1 µm and 2 µm; water ice absorbs near 1.5, 2.0 and 3 µm; CO₂ gas shows at 4.3 µm.

---

## 6.3 The LVF: a rainbow glass over the detector

Most spectrometers use a prism or grating. SPHEREx uses a simpler trick: a **Linear Variable Filter (LVF)**.

Imagine a strip of coloured glass that changes colour smoothly from one end to the other,
placed directly on top of the camera sensor:

```
 detector rows ↓          colour let through
 ┌──────────────────┐
 │██████████████████│  ← 1.13 µm   (one edge)
 │██████████████████│
 │██████████████████│  ← 1.00 µm
 │██████████████████│
 │██████████████████│  ← 0.87 µm
 │██████████████████│
 │██████████████████│  ← 0.74 µm   (other edge)
 └──────────────────┘
```

So **each row of pixels sees a different wavelength**.

### Real numbers from our file (`WCS-WAVE` table)

Our file stores the wavelength on a **9 × 9 grid** of points across the detector (pixels 1, 256, 511, … 2040).
Between grid points you interpolate. Values for detector 1 in `2025W23_1C_0543_1.fits`:

| Position along the wavelength direction | Wavelength | Bandwidth |
|------------------------------------------|------------|-----------|
| one edge (pixel 1) | **1.126 µm** | 0.029 µm |
| middle (pixel ~1021) | **0.904 µm** | 0.023 µm |
| other edge (pixel 2040) | **0.735 µm** | 0.017 µm |

The wavelength changes along **one direction** of the detector and stays almost the same along the other (it only curves slightly: 1.126 at the corners vs 1.115 in the middle of the same row).

The **bandwidth** (how wide a colour slice each pixel sees) is about 0.02–0.03 µm, so the "sharpness" of the spectrum is λ / Δλ ≈ 1.126 / 0.029 ≈ **39** — matching the published "resolving power ~40".

---

## 6.4 Six detectors cover 0.75 – 5 µm

One LVF strip cannot cover everything, so SPHEREx has **6 detectors**, each 2040 × 2040 active pixels, each with its own LVF. Approximate ranges (check the Explanatory Supplement for exact values):

| Detector | Approx. wavelength range |
|----------|--------------------------|
| 1 | 0.75 – 1.1 µm (our files: 0.735 – 1.126 µm) |
| 2 | 1.1 – 1.6 µm |
| 3 | 1.6 – 2.4 µm |
| 4 | 2.4 – 3.8 µm |
| 5 | 3.8 – 4.4 µm |
| 6 | 4.4 – 5.0 µm |

6 detectors × 17 channels ≈ **102 channels**. All our 4 current files are **detector 1**.

---

## 6.5 How SPHEREx builds a spectrum for each point of the sky

In one exposure, a given star lands on **one row** → measured at **one wavelength** only.

Then the telescope **moves a little** and takes the next exposure. Now the same star lands on a **different row** → a **different wavelength**.

After many exposures over roughly **two weeks**, each sky point has been measured at all wavelengths → a full spectrum.

```
exposure 1:  star on row 200   → measured at 1.10 µm
exposure 2:  star on row 600   → measured at 1.02 µm
exposure 3:  star on row 1000  → measured at 0.91 µm
...
combine → spectrum of the star from 0.75 to 5 µm
```

---

## 6.6 PROBLEM: comparing two dates = comparing two colours

This is the most important point of the whole project.

Suppose we compare image A (April) and image B (June) at the same sky position (after alignment with WCS).
The star falls on **different rows** in A and B → it is measured at **different wavelengths**.

Most stars are brighter at some wavelengths than others. So the star can look **brighter or fainter just because of the colour**, not because it changed!

```
April:  star at 0.80 µm → brightness 10
June:   star at 1.05 µm → brightness 14
Difference = +4  → looks like "the star brightened"
Truth: the star did not change at all. We measured a different colour.
```

Our old prototype did not handle this → many of its "brightness change" candidates are probably **colour effects, not real changes**.

Also: the **zodiacal light** (dust glow, in the `ZODI` extension) changes with date and direction, so the background differs too.

**Solutions we will use:**

1. Compare only measurements taken at **similar wavelengths** (use `WCS-WAVE`).
2. Compare **catalogs of detected objects** rather than raw pixels, and correct for colour using many observations.
3. Look for **position changes** (motion) — position does not depend on colour!

---

## 6.7 OPPORTUNITY: free colour spectra of moving objects

Now the good news. An asteroid **moves**. In each exposure it appears at a new position and on a different row → **a new wavelength**.

So as we track a moving object across exposures, we automatically collect its brightness at many wavelengths → **its spectrum**, i.e. its **colour fingerprint**.

```
detection 1: position P1, wavelength 0.80 µm, brightness b1
detection 2: position P2, wavelength 0.95 µm, brightness b2
detection 3: position P3, wavelength 1.08 µm, brightness b3
→ track (motion)  +  spectrum (what it is made of)
```

The fingerprint helps:

- tell **rocky vs carbon-rich vs icy** objects,
- separate **real objects** (smooth, sensible spectrum) from **artifacts** (random jumps),
- make the project **novel**: motion + colour together, from SPHEREx alone.

(Care is needed: the object rotates and its distance changes during two weeks, which changes brightness too.)

---

## 6.8 The other parts of the file, in SPHEREx terms

| HDU | What it tells us | How we use it |
|-----|------------------|---------------|
| `IMAGE` | Calibrated sky brightness (MJy/sr) | Find objects, measure brightness |
| `VARIANCE` | Noise² per pixel | Real significance (SNR) of every detection |
| `FLAGS` | Warnings per pixel (Lesson 7) | Reject artifacts |
| `ZODI` | Model of zodiacal dust glow (not subtracted from IMAGE) | Background correction |
| `PSF` | 121 = 11 × 11 PSFs, one for each zone of the detector, 10× finer pixels (0.615″) | Precise positions and brightness (Lesson 8) |
| `WCS-WAVE` | Wavelength + bandwidth on a 9 × 9 grid | Know the colour of every measurement |

---

## 6.9 Where the data comes from

- **IRSA** (NASA/IPAC Infrared Science Archive) hosts SPHEREx data.
- **Quick Releases**: QR2 (our current files), **QR3** started releasing in September 2026.
- Ways to get data: IRSA search (by position), **cutouts** (small pieces), **AWS S3** public bucket (free download).
- Our 4 files came from the AWS bucket `nasa-irsa-spherex`.

---

## 6.10 Summary

- SPHEREx: all-sky, 4 times in 2 years, **102 colours, 0.75 – 5 µm**, 6.15″ pixels, ~19.5 mag depth.
- Main goals are cosmology and ices; asteroids/comets are bonus science (~100,000 asteroids).
- **LVF**: each detector row sees a **different wavelength** (our file: 0.735 → 1.126 µm).
- A spectrum is built by moving the telescope so each point lands on many rows.
- **Problem**: comparing dates also compares colours → fake "brightness changes".
- **Opportunity**: tracking a moving object gives its **spectrum for free**.

## 6.11 Self-check

1. Explain the LVF to a friend in two sentences.
2. Why can a star look "brighter" between two SPHEREx images even if it did not change?
3. Why is position (motion) safer than brightness for finding changes in SPHEREx?
4. Why is the LVF useful for studying moving asteroids?
5. What is in the `ZODI` extension, and why does it matter?
6. What are SPHEREx's three main science goals?

## 6.12 Try it yourself

```python
from astropy.io import fits
import numpy as np
with fits.open("data/raw/2025W23_1C_0543_1.fits") as h:
    t = h["WCS-WAVE"].data
    grid = t["VALUES"][0]            # shape (9, 9, 2)
    print(t["X"][0])                 # grid pixel positions
    print(np.round(grid[:, :, 0], 3))  # wavelength (µm) on the 9x9 grid
```

Look at the printed table: in which direction does the wavelength change?

## 6.13 Read next (official)

- SPHEREx Quick Release overview: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html
- SPHEREx Explanatory Supplement: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf
- SPHEREx Solar System science: https://arxiv.org/abs/2402.08705
