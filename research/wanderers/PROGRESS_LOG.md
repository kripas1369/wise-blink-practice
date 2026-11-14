# Progress log: SPHEREx Infrared Wanderers (SIWC)

Times are UTC (Nepal is UTC+5:45). Scope: `research/` and `backend/` only, with no frontend changes, no commits and no pushes.

## 13 Nov 2026

- **16:00, audit.**
  - HEAD is `d8441c2`.
  - Backend tests: 286 passed, 5 skipped, 1 failed. The failure is the known WISE 0855 detector test.
  - `photutils` is not installed, so detection and PSF fitting are written with scipy instead; nothing new was installed.
  - IRSA has `catwise_2020`. Its `pmra` is in arcsec/yr, and `ra_pm`/`dec_pm` are positions at MJD 57170.
  - `spherex.obscore` holds DR1 and QR3. Example coverage:
    - (60, −50): 436 images, 3 visits, 2025-07-03 to 2026-08-12.
    - (200, +40): 467 images, 4 visits.
    - (90, −60), the SEP deep field: 7,033 images, 9 visits.
- **16:13, field ranking started** (`select_fields.py`): 72 tiles out of 1,524 allowed, 18 in each band of ecliptic latitude.
- **16:15, control test started:** ε Indi B (10′ field). IRSA was slow, at about 7–18 cutouts per minute.
  - Each cutout is about 4.3 MB, because DR1 files carry the PSF as an `EPSF` extension. The website's download code only drops an extension named `PSF`, so this one is kept.
- **16:17, control restarted** with at most 6 exposures per detector-epoch (127 cutouts) to save time.
- **16:21, stage 1 of the ranking.** 72 tiles.
  - Away from the ecliptic poles: 3–4 visits over about 380–420 days.
  - Near the south ecliptic pole, outside the deep field: 6–8 visits over about 525 days.
  - Deep-field tiles: up to 20,645 images.
- **16:30, ε Indi B control measured:**
  - 144 sources, 130 with motion fits.
  - Registration rms 1.1–1.6″ (error floor 0.75–1.0″).
  - Negative control: 32 Gaia stars, error scale 0.96 (errors realistic), largest z 2.0.
- **16:42, classify fixes.**
  - The JPL check now asks once per visit, and only for candidates. It had taken 30–60 s per call, three times per visit, for every possible mover.
  - "Poor PSF fit" is now judged against stars of similar brightness. Before this, ε Indi B was rejected only because a Gaussian fits very bright stars worse.
  - Long-baseline (CatWISE) errors are calibrated on Gaia stars. The threshold is the largest Gaia-star z: 7.45σ in the ε Indi B field.
- **16:43, ε Indi B result.** Class 1, known mover.
  - SPHEREx: +3742 ± 137 and −2383 ± 88 mas/yr, 27σ.
  - Gaia DR3: +3982 and −2467 mas/yr.
  - Agreement z = 1.6. The positive control passes.
- **16:55, ranking finished.**
  - The first crowding measure counted every CatWISE source, most of them too faint for SPHEREx. It was redone for W1 < 16 sources with W1 < 17 neighbours; the first run is kept as `results/field_scores_run1_allcatwise_crowding.csv`.
  - Top 3 (`results/field_scores.csv`):
    - hp638 (256.5, +60.434), score 78.8: 9 visits, a deep-field tile.
    - hp735 (261.0, +75.341), score 74.6: 8 visits, deep.
    - hp2061 (52.5, −72.388), score 73.5: 6 visits, not deep.
  - The tiles closest to the LMC lost on crowding (Gaia counts of 15,000–20,000 in 20′).
- **16:56, controls started:** Barnard's Star and WISE 0855 (8′ fields).
- **17:04, pilots started** on the top 3 fields: 20′ fields, at most 4 exposures per detector-epoch.
