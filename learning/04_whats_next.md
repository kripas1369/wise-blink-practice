# 04. What comes next (Step 2a, Step 2b, Day 4), from the basics

After Day 1 we can **find** every SPHEREx image of a spot and **download** a small cutout.
But raw cutouts cannot be blinked yet. This page explains why, and what each next step does.

---

## Step 2a (Day 2, Sun 1 Nov): clean and line up the epochs

### Problem 1: raw cutouts are not pictures yet
A cutout has several layers (extensions). Read [`docs/learn/04_fits_files.md`](../docs/learn/04_fits_files.md) and [`07_noise_and_flags.md`](../docs/learn/07_noise_and_flags.md) first.

| Layer | What it is | What we do with it |
|---|---|---|
| IMAGE | brightness per pixel (MJy/sr) | the picture |
| ZODI | modelled glow of dust in our solar system | subtract it: `IMAGE − ZODI` |
| VARIANCE | noise² per pixel | `sigma = sqrt(VARIANCE)`; used for weights and for "is this change real?" |
| FLAGS | a number per pixel; each bit = one problem | mask pixels with a bad bit (official list); keep SOURCE as a label only |
| PSF | how a point of light is spread out | later, for measuring brightness |
| WCS-WAVE | wavelength at each pixel | to label frames and build spectra |

**Function to write:** `clean_cutout(path) -> (image, sigma, bad_mask, mjd, wcs, info)`.
- Time from the header keyword `MJD-AVG` (not `DATE`).
- Bad pixels: `flags & flags.bad_pixel_bitmask(header) != 0`. The bit numbers come from the
  header (QR2 `MP_*`, QR3 `MSKN*`/`MSKM*`; already written and tested on Day 1).
- `% flagged` = bad pixels / all pixels, shown under each frame (honesty).

### Problem 2: every image is turned a different way
SPHEREx images are **not north-up**. The cutout's axes follow the detector, and the spacecraft
points differently on each visit (IRSA's cutout page says this too). If you blink two raw cutouts,
the whole sky seems to rotate and jump, and nobody can see a star move.

**Fix: reprojection.** Make one common grid for the target: north up, east left, centred on the
target, pixel size 6.15″, width = the field of view. Then use the `reproject` package
(`reproject_interp`) to move every cutout onto that grid. Now pixel (10, 12) is the same piece of
sky in every frame.

**Check (proof, not hope):** background stars must sit on the same pixel in every frame. If they
do not, the alignment is wrong, and any "motion" we see is fake.

**Function to write:** `target_grid(ra, dec, fov_arcmin) -> WCS` and `align(image, wcs, grid)`.

### Problem 3: one image is noisy; a visit has many
In one visit, the same spot is photographed many times per detector. Adding them reduces noise.
Use a **weighted mean**: good (low-noise) pixels count more.
```
weight = 1 / variance        (bad pixels get weight 0)
coadd  = sum(weight * image) / sum(weight)
sigma_coadd = 1 / sqrt(sum(weight))
```
**Function to write:** `coadd_epoch(aligned_images) -> (image, sigma, n_images)`.

**Watch out (SPHEREx-specific):** SPHEREx has a filter whose wavelength changes across the
detector (an "LVF"). So in two exposures in the same detector, our star sits at **different
wavelengths**. Adding a whole detector mixes ~0.5 µm of wavelength. That is fine for a picture,
but for brightness measurements we must keep track of the wavelength of each measurement
(see the light curve and spectrum parts below).

### Problem 4: brightness must be honest
If each frame gets its own automatic contrast, a constant star can look like it brightens.
**Rule:** one brightness scale (for example the 1st and 99.5th percentile of all frames together)
for every frame of one target and detector. Then save PNGs.

**Done when:** Barnard's Star frames from different epochs play in the flipbook, lined up, with
date, detector, wavelength, number of images and % flagged under each frame.

---

## Step 2b (Day 3, Mon 2 Nov): compare epochs with proof

### Gaia markers: "where the star should be"
Gaia (ESA) measured positions and motions of ~1.8 billion stars at the date 2016.0.
1. Query IRSA's `gaia_dr3_source` table for stars in our field (a cone search).
2. For each epoch, move each star from 2016.0 to that epoch's date with `position_at` (the same
   function we already wrote and tested).
3. The website draws a small circle at those positions on each frame.

If Barnard's Star in the SPHEREx frames sits on its moving Gaia circle, we have **independent
proof** that the motion is real. This is our strongest "validity" argument for the judges.

### Difference image in sigma: "what changed?"
```
diff_sigma = (epoch_B − epoch_A) / sqrt(sigma_A² + sigma_B²)
```
A value of +5 means "brighter by 5 times the noise": very unlikely to be noise. A moving star
gives a black-white pair (gone from the old place, new at the new place). Colour scale from −5 to
+5 sigma.

### Measured motion vs Gaia (Level 3)
Find the star's centre (centroid) in the first and last epoch, convert pixels to arcseconds
(× 6.15″), divide by the years between them, and compare with Gaia's proper motion. Expected sizes
(proper motion × time between first and last visit ÷ 6.15″ per pixel) are in
[03](03_archive_facts_and_mistakes.md). Barnard's Star should move about 2 pixels: small but
visible after alignment.

### The API (the meeting point with the website)
FastAPI turns Python functions into web addresses that return JSON or PNG:

| Address | Returns |
|---|---|
| `/api/resolve?name=` | position + proper motion, or an honest error |
| `/api/coverage?ra&dec` | images, epochs, detectors, releases (Day 1 code!) |
| `/api/frames?ra&dec&fov&det` | list of PNG frames with labels |
| `/api/gaia?ra&dec&fov&mjds=` | Gaia stars moved to each epoch's date |
| `/api/diff?ra&dec&fov&det&epochA&epochB` | difference PNG in sigma + numbers |

Agree the exact JSON on the morning call (`docs/plan/FACTS.md` section 7) and do not change it
without telling each other.

---

## Day 4 (Tue 3 Nov): connect, online, test

### Light curve (brightness over time)
For the variable stars (RW Aur, R Dra): measure the star's brightness in each image (sum of
`IMAGE − ZODI` in a small circle minus the local background; error from VARIANCE), and plot it
against time. Because of the LVF, also store the **wavelength** of each point, and colour the
points by wavelength (or compare only points at similar wavelengths). Otherwise a change of colour
could look like a change of brightness. Check the shape against AAVSO (an amateur variable-star
database) for R Dra.

**Smart validity check:** IRSA's own Spectrophotometry Tool measures brightness with a proper PSF
fit. Run it once for one target and compare with our numbers. If they agree, we can say so in the
pitch.

### Spectrum (brightness vs wavelength) and "spectrum per epoch"
Each visit covers all 102 colours, so for each epoch we can plot brightness vs wavelength.
WISE 0855: near zero at short wavelengths, rising at 4–5 µm (it is cold: published estimates are roughly 250–285 K, about room temperature
or colder; check the number in a paper before saying it in the pitch).
R Dra: compare the spectrum at two epochs; the change between them is the variability. This is
"spectra on the fly", which the challenge gives extra kudos for.

### Pre-cache, deploy, acceptance tests
- Download the cutouts for the 5 targets ahead of time (5 MB each, a few hundred per target;
  IRSA allows ~3 at a time), so the demo never waits for IRSA.
- Deploy (Render, Railway or a VPS); test on a phone.
- Run the acceptance tests (`HACKATHON_PLAN.md` C4) and write the results with numbers.

**Done when:** a public link works and all 5 targets pass: Barnard's Star moves onto its Gaia
markers; WISE 0855 shows only in D5–D6; R Dra and RW Aur change brightness.
