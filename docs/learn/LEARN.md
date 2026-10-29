# LEARN.md — Your Preparation Guide

Project: **SPHEREx moving-object search with colour spectra + Planet X sensitivity**

This guide tells you **what to learn, why, where to read, what to practise, and how to check yourself**.
Topics are in the **same order we will build the project**, so each topic prepares you for the next step of work.

## Beginner lessons (start here — no background needed)

Full lessons written from zero, in simple words, with worked examples using **our real SPHEREx files**:

| # | Lesson | Read when |
|---|--------|-----------|
| 1 | [Where is it? Sky coordinates and angles](01_sky_coordinates.md) | Now |
| 2 | [When was it? Time in astronomy](02_time.md) | Now |
| 3 | [How bright is it? Light, flux, magnitude](03_light_and_brightness.md) | Now |
| 4 | [What is inside the file? FITS](04_fits_files.md) | Before step 1 |
| 5 | [Which pixel is which star? WCS](05_wcs.md) | Before step 1 |
| 6 | [How SPHEREx works — the most important lesson](06_spherex.md) | Before step 1 |
| 7 | [Is it real? Noise, variance, flags, artifacts](07_noise_and_flags.md) | Week 1 |
| 8–17 | Written in the same style before we reach those weeks | Weeks 1–3 |

Each lesson ends with **self-check questions** (some with answers) and a **"try it yourself"** Python exercise.
The topic list below is the full map; the lessons above are the detailed explanations.

How to use it:

- Spend **1–2 hours per day** on this besides the project work.
- Read the "Why it matters for us" line first — it keeps you focused.
- Do the small practice task — reading alone is not enough.
- Answer the self-check questions **in your own words** (write them in a notebook). If you cannot answer, re-read.
- Use only **free/legal sources** (official docs, arXiv, NASA/IRSA, library copies). Do not download pirated books.

---

## Overview: learning path

```
Part A  Basics of the sky        (before / during week 1)
  1. Sky coordinates, angles, arcseconds
  2. Time in astronomy (UTC, MJD)
  3. Light: wavelength, flux, magnitude, signal-to-noise
Part B  Astronomical data         (week 1)
  4. FITS files
  5. WCS (pixel <-> sky)
  6. SPHEREx: the mission and its data
  7. Detectors, noise, flags, artifacts
Part C  Image processing          (week 1 – 2)
  8. Background, PSF, source detection, photometry
  9. Image alignment and difference imaging
Part D  Moving objects            (week 2)
  10. Solar System basics and apparent motion (parallax)
  11. Linking detections into tracks, fitting motion
  12. Catalogs and known objects (Gaia, JPL Horizons, SkyBoT, MPC)
  13. Asteroid spectra and colours
Part E  Science honesty           (week 3)
  14. Statistics: significance, false positives, look-elsewhere
  15. Injection–recovery and completeness
  16. Planet Nine: the hypothesis and how to test it
Part F  Presentation              (week 3, and before hackathon)
  17. Telling the science story
```

---

# PART A — Basics of the sky

## 1. Sky coordinates and angles

**Why it matters for us:** every detection, every moving object and every catalog match is described by a sky position (RA/Dec) and distances in arcseconds.

**Learn:**
- [ ] Celestial sphere; Right Ascension (RA) and Declination (Dec) in degrees
- [ ] Degrees, arcminutes (′), arcseconds (″): 1° = 60′ = 3600″
- [ ] Angular separation between two sky points (why you cannot just subtract RA values — RA shrinks by cos(Dec))
- [ ] Ecliptic (plane of the Solar System) vs Galactic plane (Milky Way) — asteroids live near the ecliptic, stars are crowded near the galactic plane
- [ ] Small-angle approximation: size ≈ distance × angle (in radians)

**Read:**
- Astropy coordinates: https://docs.astropy.org/en/stable/coordinates/
- Learn Astropy tutorials (coordinates section): https://learn.astropy.org/

**Practice:** with `astropy.coordinates.SkyCoord`, compute the separation between RA 304.69°, Dec 42.44° (our field) and RA 304.70°, Dec 42.45°. Convert our field to ecliptic and galactic coordinates. Is it near the ecliptic?

**Self-check:**
1. Why is 1° of RA smaller on the sky near the pole than at the equator?
2. SPHEREx pixels are 6.2″. How many pixels is 1 arcminute?
3. Why do we expect few asteroids in our current field?

---

## 2. Time in astronomy

**Why it matters for us:** motion = position change / time. A wrong time gives a wrong speed. (We already found our reports used the wrong date header.)

**Learn:**
- [ ] UTC, TAI, TDB (only the idea: different clocks)
- [ ] Julian Date (JD) and Modified Julian Date (MJD = JD − 2400000.5)
- [ ] FITS time keywords: `DATE` (file created) vs `DATE-OBS` / `MJD-OBS` / `MJD-AVG` (when the photo was taken)
- [ ] Exposure start, middle and end — which one to use for a moving object (middle)

**Read:**
- Astropy Time: https://docs.astropy.org/en/stable/time/

**Practice:** convert MJD 60794.0162 and 61201.3421 to calendar dates; compute the days between them.

**Self-check:**
1. Why do astronomers use MJD instead of calendar dates?
2. Why is `DATE` the wrong keyword for observation time?
3. An asteroid moves 30″ per hour. If our time is wrong by 1 minute, how big is the position error?

---

## 3. Light: wavelength, flux, magnitude, signal-to-noise

**Why it matters for us:** SPHEREx measures brightness at many wavelengths. "Can SPHEREx see Planet X?" is a brightness question.

**Learn:**
- [ ] Electromagnetic spectrum; near-infrared 0.75–5 µm
- [ ] Flux, flux density, surface brightness (SPHEREx images are in **MJy/sr**)
- [ ] Jansky (Jy) and AB magnitude: m_AB = −2.5 log10(f_ν / 3631 Jy)
- [ ] Magnitudes are backwards: bigger number = fainter; 5 magnitudes = 100× fainter
- [ ] Signal-to-noise ratio (SNR); what "5σ depth" means
- [ ] Reflected sunlight vs thermal emission (why distant cold objects are very faint in near-IR)
- [ ] Inverse-square law, and why reflected light from a distant planet falls roughly as 1/distance⁴

**Read:**
- Carroll & Ostlie, *An Introduction to Modern Astrophysics*, chapters on light, magnitudes and blackbody radiation (library copy)
- SPHEREx mission paper (depth and wavelengths): https://iopscience.iop.org/article/10.3847/1538-4357/ae2be2/meta

**Practice:** SPHEREx 5σ depth ≈ 19.5 AB. Planet Nine predicted V ≈ 20.6–23.1. How many times fainter than the SPHEREx limit is a V = 22 object (assume similar magnitude systems for this rough exercise)?

**Self-check:**
1. What does "5σ depth of 19.5 mag" mean in simple words?
2. Why does a planet 2× farther look about 16× fainter in reflected light?
3. Why is a 40 K planet bright in far-infrared but dark in near-infrared?

---

# PART B — Astronomical data

## 4. FITS files

**Why it matters for us:** all SPHEREx data comes as FITS. Step 1 of our work is inspecting FITS files.

**Learn:**
- [ ] What FITS is; HDU (Header + Data Unit)
- [ ] Primary HDU, ImageHDU, BinTableHDU
- [ ] Header keywords: `NAXIS`, `NAXIS1`, `NAXIS2`, `BUNIT`, `EXTNAME`
- [ ] Multi-extension FITS (MEF) — one file, many parts
- [ ] Opening files with `astropy.io.fits`, `hdul.info()`, reading headers, reading data
- [ ] Memory mapping for large files

**Read:**
- Astropy FITS docs: https://docs.astropy.org/en/stable/io/fits/
- FITS standard (skim sections 1–4 only): https://fits.gsfc.nasa.gov/fits_standard.html

**Practice:** open `data/raw/2025W18_1B_0074_1.fits`, print `hdul.info()`, print the header of `IMAGE`, and find `MJD-OBS`, `BUNIT`, `DETECTOR`, `PSF_FWHM`.

**Self-check:**
1. What is the difference between an ImageHDU and a BinTableHDU?
2. Our files have 7 HDUs. Name them and guess each purpose.
3. Why should we never modify files in `data/raw/`?

---

## 5. WCS — World Coordinate System

**Why it matters for us:** WCS converts pixel (x, y) to sky (RA, Dec). Without it we cannot align images or match catalogs.

**Learn:**
- [ ] Pixel coordinates vs world coordinates
- [ ] Header keys: `CTYPE`, `CRVAL`, `CRPIX`, `CDELT`, `CD`, `PC`
- [ ] Projections: TAN (gnomonic); SIP distortion (`RA---TAN-SIP`) — our files use this
- [ ] `WCS.pixel_to_world()` and `world_to_pixel()`
- [ ] 0-based (Python) vs 1-based (FITS) pixel indexing — a classic bug
- [ ] Pixel scale (arcsec/pixel)

**Read:**
- Astropy WCS docs: https://docs.astropy.org/en/stable/wcs/
- Calabretta & Greisen 2002, "Representations of celestial coordinates in FITS" (skim introduction): https://arxiv.org/abs/astro-ph/0207413

**Practice:** load the IMAGE WCS of one file, convert the four corners and centre pixel to RA/Dec; convert back and check you get the same pixel (round trip).

**Self-check:**
1. What does `CRVAL` mean, and what does `CRPIX` mean?
2. Why do we need SIP distortion for a wide-field telescope?
3. If two images have different WCS, why can't we subtract them pixel-by-pixel?

---

## 6. SPHEREx: the mission and its data

**Why it matters for us:** the most important idea of our project — **every SPHEREx pixel sees a different wavelength** (Linear Variable Filter). This is both our biggest problem (unfair image comparison) and our biggest opportunity (free colour spectra of moving objects).

**Learn:**
- [ ] Mission goals: inflation, galaxy history, interstellar ices; solar-system objects as bonus science
- [ ] All-sky, 4 times in 2 years, 102 spectral channels, 0.75–5 µm, 6.2″ pixels
- [ ] Linear Variable Filter (LVF): wavelength changes across the detector
- [ ] Six detectors and their wavelength ranges
- [ ] Level-2 spectral images: `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `PSF`, `WCS-WAVE`
- [ ] Zodiacal light (sunlight scattered by dust in the Solar System)
- [ ] Quick Releases (QR2, QR3) and data access: IRSA, cutouts, AWS S3
- [ ] How a sky point gets its spectrum: observed many times over ~2 weeks at different wavelengths

**Read (most important sources of the whole project):**
- SPHEREx Quick Release overview: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html
- SPHEREx Explanatory Supplement: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf
- SPHEREx cutout tool: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html
- IRSA Python tutorials (SPHEREx notebooks): https://caltech-ipac.github.io/irsa-tutorials/
- SPHEREx mission paper: https://iopscience.iop.org/article/10.3847/1538-4357/ae2be2/meta
- SPHEREx solar-system science: https://arxiv.org/abs/2402.08705

**Practice:** read the `WCS-WAVE` table in one file and find the wavelength at the centre pixel and at the four corners.

**Self-check:**
1. Explain the LVF to a friend in two sentences.
2. Why can a star look "brighter" between two SPHEREx images even if it did not change?
3. Why is the LVF useful for studying moving asteroids?
4. What is in the `ZODI` extension and why does it matter?

---

## 7. Detectors, noise, flags and artifacts

**Why it matters for us:** most "changes" in images are fake (noise, bad pixels, cosmic rays, ghosts). Rejecting them is the difference between science and false alarms.

**Learn:**
- [ ] Infrared detector basics (pixels collect charge; readout)
- [ ] Noise sources: photon (Poisson) noise, read noise, dark current
- [ ] Variance and standard deviation; how noise adds: σ_total² = σ₁² + σ₂²
- [ ] Bit flags: how one integer stores many yes/no flags (bitwise AND)
- [ ] SPHEREx flags in our files: `MP_TRANSIENT`, `MP_HOT`, `MP_COLD`, `MP_PERSIST`, `MP_OUTLIER`, `MP_SOURCE`, `MP_GHOST`, `MP_BLOOM`, `MP_SNOWBALL`, `MP_HALO`, `MP_NONLINEAR`, `MP_OVERFLOW`
- [ ] Artifacts: cosmic rays, saturation, persistence, ghosts, snowballs, edges

**Read:**
- Howell, *Handbook of CCD Astronomy* (library) — chapters on noise and calibration
- SPHEREx Explanatory Supplement — flags section

**Practice:** decode the FLAGS image of one file: for each `MP_*` bit, count how many pixels have it set.

**Self-check:**
1. If pixel A has variance 4 and pixel B has variance 9, what is the noise of A − B?
2. How do you test whether bit 10 (`MP_HOT`) is set in a flag value?
3. Name three artifacts that can look like a moving object.

---

# PART C — Image processing

## 8. Background, PSF, source detection and photometry

**Why it matters for us:** we find objects in each image before we can track them.

**Learn:**
- [ ] Background estimation (median, sigma-clipping, 2D background maps)
- [ ] Robust statistics: median, MAD (median absolute deviation), σ ≈ 1.4826 × MAD
- [ ] PSF (point spread function) and FWHM — how a point source spreads on the detector
- [ ] Thresholding and connected components (segmentation)
- [ ] DAOStarFinder, peak finding
- [ ] Aperture photometry vs PSF photometry; flux error from variance
- [ ] Centroiding (finding the precise centre of a star)

**Read:**
- Photutils docs (background, detection, photometry): https://photutils.readthedocs.io/
- SciPy ndimage: https://docs.scipy.org/doc/scipy/reference/ndimage.html

**Practice:** run photutils `DAOStarFinder` on a 200×200 cutout of one of our images; plot circles over the detected sources.

**Self-check:**
1. Why use median instead of mean for background?
2. What does the PSF tell us, and why do we need it for photometry?
3. What is SNR for a source with flux 100 and flux error 20?

---

## 9. Image alignment and difference imaging

**Why it matters for us:** our current prototype already does this; we must understand its limits.

**Learn:**
- [ ] Reprojection/resampling onto a common grid (`reproject`)
- [ ] Interpolation effects (smoothing, correlated noise)
- [ ] Difference image D = I₂ − I₁ and significance S = D / √(var₁ + var₂)
- [ ] PSF matching (why different PSFs create fake residuals)
- [ ] Why SPHEREx differences are hard (different wavelength per pixel, changing zodi)

**Read:**
- Reproject docs: https://reproject.readthedocs.io/
- Alard & Lupton 1998 (classic difference imaging): https://arxiv.org/abs/astro-ph/9712287
- Zackay, Ofek & Gal-Yam 2016 (ZOGY, optimal subtraction): https://arxiv.org/abs/1601.02655

**Practice:** open `data/thumbnails/alignment_before_after.png` and `demo_what_changed.png`; write down which residuals you think are real and which are artifacts, and why.

**Self-check:**
1. Why can't we subtract two images before aligning them?
2. Why does a bright star often leave a "+/−" pattern in a difference image?
3. Why is catalog-level comparison (detect first, then compare) often better for SPHEREx than pixel subtraction?

---

# PART D — Moving objects

## 10. Solar System basics and apparent motion

**Why it matters for us:** we need to predict how fast asteroids and a distant Planet X appear to move on the sky.

**Learn:**
- [ ] Astronomical Unit (AU); planets' distances
- [ ] Kepler's three laws; orbital period P² = a³ (P in years, a in AU)
- [ ] Orbital elements: a, e, i, Ω, ω, mean anomaly
- [ ] Main belt, Trojans, Centaurs, Kuiper belt, trans-Neptunian objects, sednoids
- [ ] **Parallax**: Earth moves ~30 km/s; a distant object appears to shift. Rate ≈ 206265″ × (Earth speed / distance)
- [ ] Why asteroids move ~0.25°/day but Planet X at 500 AU moves only ~7″/day
- [ ] Heliocentric vs geocentric vs barycentric positions
- [ ] Elongation: SPHEREx looks ~90° from the Sun

**Read:**
- Murray & Dermott, *Solar System Dynamics*, chapter 2 (library)
- Curtis, *Orbital Mechanics for Engineering Students*, two-body chapters (library)
- JPL Solar System Dynamics site: https://ssd.jpl.nasa.gov/

**Practice:** compute the apparent parallax rate (arcsec/day) for objects at 1, 3, 30, 100, 500 and 1000 AU, assuming Earth moves 0.0172 AU/day perpendicular to the line of sight. How many SPHEREx pixels per day is each?

**Self-check:**
1. What is the orbital period of an object at 500 AU?
2. Why is Planet X's apparent motion mostly due to Earth, not the planet itself?
3. Why do main-belt asteroids move so much faster on the sky than Kuiper belt objects?

---

## 11. Linking detections into tracks, fitting motion

**Why it matters for us:** a single detection is not a moving object; a consistent line of detections over time is.

**Learn:**
- [ ] Tangent-plane (gnomonic) projection for small fields
- [ ] Nearest-neighbour search and KD-trees (`scipy.spatial.cKDTree`)
- [ ] Linear least squares: fit position = p₀ + v·t
- [ ] χ² (chi-square), reduced χ², residuals
- [ ] Model comparison: AIC and BIC (don't prefer a model just because it has more parameters)
- [ ] RANSAC (robust fitting with outliers)
- [ ] Shift-and-stack idea for very faint slow movers (used in Planet Nine and KBO searches)

**Read:**
- Holman et al. 2018, HelioLinC: https://arxiv.org/abs/1805.02638
- Moeyens et al. 2021, THOR: https://arxiv.org/abs/2105.01056
- Whidden et al. 2019, KBMOD shift-and-stack: https://arxiv.org/abs/1901.07598
- Ivezić, Connolly, VanderPlas & Gray, *Statistics, Data Mining, and Machine Learning in Astronomy* (fitting chapters; library) and astroML: https://www.astroml.org/

**Practice:** generate 6 fake points moving 1″/hour with 0.3″ noise plus 20 random points; use RANSAC to find the line and recover the speed.

**Self-check:**
1. What does reduced χ² ≈ 1 mean? What about ≫ 1?
2. Why does BIC penalize extra parameters?
3. How does shift-and-stack let you detect objects too faint for a single image?

---

## 12. Catalogs and known objects

**Why it matters for us:** before calling anything "unknown", we must check known stars and known Solar System objects. Recovering known asteroids is also how we prove our tool works.

**Learn:**
- [ ] Gaia (positions of ~2 billion stars) — remove stationary stars
- [ ] JPL Horizons — predicted position of a known object at a given time
- [ ] SkyBoT (IMCCE) — "which known Solar System objects were in this field at this time?"
- [ ] Minor Planet Center (MPC) — official registry of asteroids and comets
- [ ] Cross-match radius and false matches
- [ ] astroquery modules for all of the above

**Read:**
- astroquery docs: https://astroquery.readthedocs.io/
- JPL Horizons: https://ssd.jpl.nasa.gov/horizons/
- Minor Planet Center: https://minorplanetcenter.net/
- Gaia archive: https://gea.esac.esa.int/archive/
- IRSA SPHEREx tools (Moving Object Search): https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html

**Practice:** use `astroquery.jplhorizons` to get the RA/Dec of asteroid (1) Ceres at MJD 60830.84; use SkyBoT to list known objects within 1° of a chosen position at that time.

**Self-check:**
1. Why is "not in one catalog" not the same as "new object"?
2. Why do we use JPL Horizons instead of computing orbits ourselves?
3. How would you choose a cross-match radius?

---

## 13. Asteroid spectra and colours

**Why it matters for us:** this is our novel part — the colour fingerprint of moving objects from SPHEREx's LVF.

**Learn:**
- [ ] Reflectance spectrum = measured spectrum / solar spectrum
- [ ] Asteroid taxonomy: S-type (rocky), C-type (carbon-rich), M-type (metallic), D/P types
- [ ] Absorption features: ~1 µm and ~2 µm (olivine, pyroxene), ~3 µm (water/hydrated minerals), CO₂ at 4.3 µm (comets)
- [ ] Thermal emission beyond ~3.5 µm for near asteroids
- [ ] Why rotation and changing distance affect spectra built over two weeks

**Read:**
- DeMeo et al. 2009, Bus–DeMeo taxonomy (Icarus) — search on NASA ADS: https://ui.adsabs.harvard.edu/
- SPHEREx solar-system science: https://arxiv.org/abs/2402.08705
- EPSC 2026 SPHEREx asteroid catalogue update: https://meetingorganizer.copernicus.org/EPSC2026/EPSC2026-797.html

**Practice:** find a published near-IR reflectance spectrum of an S-type and a C-type asteroid; sketch both and mark the 1 µm and 2 µm features.

**Self-check:**
1. Why divide by the solar spectrum?
2. How would an S-type and a C-type look different in SPHEREx data?
3. What makes building a spectrum of a moving object harder than for a star?

---

# PART E — Science honesty

## 14. Statistics: significance and false positives

**Why it matters for us:** if we search millions of pixels, noise alone will produce "5σ" events. We must know how many fakes to expect.

**Learn:**
- [ ] Gaussian distribution; σ levels and probabilities (5σ ≈ 1 in 3.5 million, one-sided)
- [ ] p-values and hypothesis testing (H0: noise/artifact/known; H1: real moving object)
- [ ] Multiple testing and the look-elsewhere effect
- [ ] False positive rate, false discovery rate (FDR)
- [ ] Bootstrap and Monte Carlo simulation

**Read:**
- Feigelson & Babu, *Modern Statistical Methods for Astronomy* (library)
- Ivezić et al., *Statistics, Data Mining, and Machine Learning in Astronomy* (library)

**Practice:** make a 2040×2040 image of pure Gaussian noise; count how many pixels exceed 5σ. Compare with the theoretical expectation.

**Self-check:**
1. Why is "5σ" not automatically a discovery when you search a whole image?
2. What is the look-elsewhere effect in one sentence?
3. How would you estimate the false positive rate of our pipeline?

---

## 15. Injection–recovery and completeness

**Why it matters for us:** it is the only honest way to say "our tool can detect objects down to brightness X and speed Y" — and it produces the Planet X sensitivity map.

**Learn:**
- [ ] Injecting a synthetic source using the real PSF into real images
- [ ] Recovery rate (completeness) vs brightness, speed, SNR
- [ ] Localization error, speed error
- [ ] Completeness curves and 50% / 90% limits

**Read:**
- Any survey paper's "completeness" section; e.g. the Planet Nine parallax search: https://arxiv.org/abs/2504.05473

**Practice:** add a fake star with flux F using a Gaussian PSF to a real cutout; run detection; repeat for fainter F until it disappears. Plot recovery vs F.

**Self-check:**
1. Why inject into real images rather than fully simulated ones?
2. What does "90% completeness at mag 18" mean?
3. How does injection–recovery answer "could SPHEREx see Planet X?"

---

## 16. Planet Nine: the hypothesis and how to test it

**Why it matters for us:** this is the motivation and final science question of the project.

**Learn:**
- [ ] Extreme trans-Neptunian objects and their orbital clustering
- [ ] Planet Nine predicted properties: ~5–10 Earth masses, a ~380–500 AU, i ~16°, V ~20.6–23.1
- [ ] Arguments against (observational bias; 2023 KQ14 stable sednoid)
- [ ] How searches work: parallax motion, multi-epoch catalogs, infrared surveys (IRAS/AKARI, WISE), upcoming Rubin Observatory
- [ ] Why SPHEREx may be too shallow — and why a sensitivity limit is still a result

**Read:**
- Batygin & Brown 2016, original hypothesis: https://arxiv.org/abs/1601.05438
- Batygin et al. 2019, review "The Planet Nine Hypothesis": https://arxiv.org/abs/1902.10103
- Brown & Batygin 2021, "The Orbit of Planet Nine": https://arxiv.org/abs/2108.09868
- Phan et al. 2025, IRAS + AKARI search: https://arxiv.org/abs/2504.17288
- Parallax-based targeted search 2025: https://arxiv.org/abs/2504.05473
- News on 2023 KQ14 (2026): https://www.sciencedaily.com/releases/2026/06/260608040009.htm

**Practice:** write one page: "What evidence suggests Planet Nine, what evidence argues against it, and what could SPHEREx add?"

**Self-check:**
1. What observation started the Planet Nine idea?
2. Why is Planet Nine so hard to see even though it is large?
3. What result from our project would be useful even if we never see Planet Nine?

---

# PART F — Presentation

## 17. Telling the science story

**Why it matters for us:** "Presentation" is one of five judging criteria. Good science badly explained does not win.

**Learn:**
- [ ] Problem → why it matters → what we built → proof it works → what's next
- [ ] Explaining a technical idea (LVF, parallax) with one picture
- [ ] Honest language: "candidate", "consistent with", "sensitivity limit" — never "discovered Planet X"
- [ ] 30-second video structure; one-slide summary

**Read:**
- NASA Space Apps judging criteria (impact, creativity, validity, relevance, presentation) and past winners: https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/

**Practice:** explain our project to a non-science friend in 60 seconds. Ask them to repeat it back. Fix the parts they got wrong.

**Self-check:**
1. Can you state our project in one sentence?
2. What is our "proof it works" moment?
3. What is the one image that best shows our idea?

---

## Suggested schedule (alongside project work)

| Week | Learn | Matches project step |
|------|-------|----------------------|
| Week 0 (now, before start) | Topics 1, 2, 3 | Preparation |
| Week 1, days 1–3 | Topics 4, 5, 6 | FITS inspection, WCS, wavelength map |
| Week 1, days 4–7 | Topics 7, 8, 9 | Flags, variance, detection, difference imaging |
| Week 2, days 8–11 | Topics 10, 11 | Linking and motion fitting |
| Week 2, days 12–14 | Topics 12, 13 | Known-asteroid recovery, spectra |
| Week 3, days 15–17 | Topics 14, 15, 16 | Injection–recovery, Planet X sensitivity |
| Week 3, days 18–21 | Topic 17 | Web app, story, final report |

## Python tools to be comfortable with

- `astropy` (fits, wcs, coordinates, time, units, table)
- `numpy`, `scipy` (ndimage, spatial, optimize)
- `photutils`, `reproject`
- `astroquery` (IRSA, Gaia, JPL Horizons, SkyBoT)
- `matplotlib` (with `astropy.visualization` for image stretching)
- `pandas` + `pyarrow` (Parquet tables)
- Jupyter notebooks

## Books (library / legal copies)

| Area | Book |
|------|------|
| Astronomy basics | Carroll & Ostlie — *An Introduction to Modern Astrophysics* |
| Detectors and photometry | Howell — *Handbook of CCD Astronomy* |
| Statistics + data | Ivezić, Connolly, VanderPlas & Gray — *Statistics, Data Mining, and Machine Learning in Astronomy* |
| Statistics | Feigelson & Babu — *Modern Statistical Methods for Astronomy* |
| Solar System dynamics | Murray & Dermott — *Solar System Dynamics* |
| Orbital mechanics | Curtis — *Orbital Mechanics for Engineering Students* |
| Numerical methods | Press et al. — *Numerical Recipes* |

## Where to search for papers

- NASA ADS: https://ui.adsabs.harvard.edu/
- arXiv astro-ph: https://arxiv.org/list/astro-ph/new

When reading a paper, write down: title, authors, year, link, problem, data, method, key equation, result, limitation, and how it relates to our project. (These notes will go into `docs/papers_to_read.md` in week 1.)

## Mini glossary

| Term | Meaning |
|------|---------|
| AU | Earth–Sun distance, ~150 million km |
| Arcsecond (″) | 1/3600 of a degree |
| MJD | Modified Julian Date, a day counter used in astronomy |
| FITS / HDU | Astronomy file format / one part (header + data) of it |
| WCS | Rules to convert pixel positions to sky positions |
| LVF | Linear Variable Filter — each SPHEREx pixel sees a different wavelength |
| PSF / FWHM | How a point of light spreads on the detector / its width |
| SNR | Signal-to-noise ratio |
| Parallax | Apparent shift of a nearby object as Earth moves |
| Ecliptic | Plane of the Solar System on the sky |
| Completeness | Fraction of real objects our pipeline recovers |
| Look-elsewhere effect | Searching many places makes rare-looking noise common |
| Sednoid / ETNO | Very distant objects whose orbits motivate Planet Nine |
