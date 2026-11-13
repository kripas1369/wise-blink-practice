# Code changes

**No file of the existing application was changed.** Blink Flipbook, Eclipse Mode, the backend (`backend/app/`),
the frontend and their tests are untouched by this investigation; everything new lives in `research/`, which is
outside the application and imports the existing modules (`backend.app.eclipses`, `backend.app.eclipse_depth`,
`backend.app.archive`) read-only. Nothing was committed.

Test baseline, run after the changes (13 Nov, 10:30):

- backend: `.venv/bin/python -m pytest -q backend/tests` → 286 passed, 5 skipped, **1 failed**:
  `test_day5.py::test_spectrum_points_are_exactly_the_light_curve_points` expects detectors `[2, 5, 6]` in
  `frontend/frames/wise0855/spectrum.json`, which (in the owner's uncommitted work of 7 Nov) now has `[1…6]`.
  This failure predates the investigation and is not caused by it.
- frontend: `npm test` in `frontend/` → 83 passed, 0 failed.

Each change below answers: what limitation it solves, why it matters, the supporting reference, how improvement was
measured, and whether it improved.

## 1. Forced photometry of every Gaia star at once (`research/field_psf.py`)

- **Limitation.** The application's eclipse-depth code (`backend/app/eclipse_depth.py`) measures circles around one
  or two stars. With SPHEREx's 6.2″ pixels, any neighbour within ~3 pixels leaks light into the circle, and a third
  star is ignored completely. The overnight two-star fit (`which_star_pair.py`) also models only two stars.
- **Why it matters.** The question "which star is eclipsing" in a crowded field (R1: 134 Gaia stars in 4′) cannot be
  answered if the neighbours' light is not modelled.
- **Reference.** Forced PSF photometry at catalogue positions: Stetson 1987 (DAOPHOT, PASP 99, 191); Lang, Hogg &
  Schlegel 2016 (WISE forced photometry, AJ 151, 36). SPHEREx instrument: Doré et al. 2014 (arXiv:1412.4872) and the IRSA SPHEREx Explanatory Supplement.
- **How measured.** On TIC 140659978 (the overnight survey's validated pair): eclipse depth on the source and on its
  neighbour, against the earlier two-star result.
- **Result.** Same answer as the validated method: source secondary 16.4 ± 1.3% (two-star: 18.8 ± 1.8%), neighbour
  −1.4 ± 3.5% (two-star: −0.4 ± 1.2%); and it now works in fields with up to 134 stars. **Kept.**

## 2. Pixel-integrated PSF with a wide wing (`field_psf.psf`, `fit_shape`)

- **Limitation.** A single Gaussian sampled at pixel centres leaves large residuals in the undersampled SPHEREx
  images (core σ ≈ 0.6 px).
- **Why it matters.** Residual light from bright stars biases the photometry of faint neighbours.
- **Reference.** Pixel integration for undersampled PSFs: Anderson & King 2000 (PASP 112, 1360). Extended PSF
  wings: Racine 1996 (PASP 108, 699).
- **How measured.** Same 320 exposures of TIC 140659978; co-add χ², detection significance of the source's
  secondary eclipse, scatter of the neighbour (which should be constant).
- **Result.** Co-add χ² halved in D1–D4 (from ~600–1000), detection 11.4σ → 14.1σ, neighbour scatter
  3.62% → 2.97%. **Kept** (switch off with `--no-wing` to reproduce the comparison;
  `research/experimental_results/validate_140659978_nowing`). Limitation: in the LMC (R1) the wing reaches its
  bound (60%, ~4–5 px) because it absorbs nebular light.

## 3. PSF shape interpolated in wavelength within a detector (`--by_wavelength`, off) — negative result

- **Limitation addressed.** The PSF width grows with wavelength; one shape per detector might be too coarse.
- **Reference.** Diffraction: σ ∝ λ/D.
- **How measured.** Shapes fitted separately for the blue and red halves of each detector, then interpolated.
- **Result.** σ changes by < 4% within a detector; no change in χ², depths or detection
  (`validate_140659978_wl`). **Not improved → switched off by default.** Recorded as a rejected idea.

## 4. Formal uncertainties and ensemble correction (`research/field_analysis.py`)

- **Limitation.** The application's depth errors are scaled by a global χ²; long-term drifts common to all stars
  (calibration, background) are not removed.
- **Reference.** Ensemble photometry: Honeycutt 1992 (PASP 104, 435); variability indices: von Neumann 1941,
  Stetson 1996; Lomb 1976 / Scargle 1982 periodograms with Bonferroni-corrected false-alarm probability.
- **How measured.** Scatter of constant stars; recovered depths on the validation star.
- **Result.** Comparable depths, and per-star variability statistics for the whole field (needed for a blind search).
  **Kept** (research-only).

## 5. SPHEREx DR1 collections (`research/dr1.py`)

- **Limitation.** `backend/app/config.py` `COLLECTIONS` still lists the quick-release collections; IRSA now serves
  `spherex_dr1`, `spherex_dr1_deep`, `spherex_qr3`, `spherex_qr3_deep` (QR2 returns nothing).
- **Why it matters.** More epochs per star (e.g. R3: 27,783 images).
- **Result.** Used in `research/` only. **Recommendation, not applied**: updating the application's `COLLECTIONS`
  would change the website's data, which needs the owner's decision.

## 6. External ephemeris (`--eph-json` in `field_psf.py`; read by `field_analysis.py`, `eclipse_timing.py`, `make_figures.py`, `significance.py`)

- **Limitation.** The TESS-EBs clock for TIC 31511621 (R5) has drifted by 0.19 in phase by 2026 (TESS period
  2.6294860 d vs OGLE 2.6288690 d), so the eclipse times are unknown on the TESS clock.
- **Reference.** OGLE-IV LMC eclipsing binaries, Pawlak et al. 2016 (AcA 66, 421), ~10-year baseline.
- **How measured.** Whether SPHEREx recovers the eclipse at the OGLE-predicted times (see R5 in the report).
- **Result.** Primary eclipse recovered at the OGLE time (32.2 ± 2.7%, empirical z 11.5); on the TESS-EBs clock
  it falls at TESS phase −0.24, where the TESS window would have missed it. **Kept.** Bug found and fixed: the
  override first kept TESS-EBs' secondary position (0.03), so the "secondary" window overlapped the primary;
  `sec_pos = 0.5` (circular orbit, as OGLE's light curve shows) was added to the JSON and the region re-run: the
  secondary is now measured on 50 exposures instead of 12 (14.8 ± 3.7%, z 5.2; before 16.1 ± 6.0%, z 2.6).

## 7. Analysis and validation scripts (new, research only)

| script | purpose |
|---|---|
| `tessebs_gaia_xmatch.py` | all 4,582 TESS-EBs entries vs the Gaia DR3 eclipsing-binary table (ESA archive, chunked uploads) |
| `dilution_check.py` | is a Gaia-neighbour attribution physically possible given the TESS depth and the flux ratio? |
| `coverage_candidates.py` | SPHEREx coverage and 2026 clock error for candidate regions |
| `catalog_check.py` | VSX, OGLE-LMC-ECL and SIMBAD around each target |
| `eclipse_timing.py` | eclipse centre (bootstrap) vs the TESS prediction |
| `depth_spectrum.py` | eclipse depth per detector / wavelength |
| `make_figures.py` | phase-folded light curves (binary, TIC star, controls), wavelength-matched difference image, Eclipse-Mode flipbook GIF |
| `significance.py` | empirical false-alarm probability from 1,000 random eclipse-free phases |
| `five_targets.py` | `five_target_catalog.csv` |
| `collect_results.py` | `experimental_results/results_summary.json` (all numbers quoted in the report) |
| `misattribution_trends.py` | trends of the other-star fraction with latitude, magnitude, depth, period (first run inline; saved as a script and checked to reproduce `out/misattribution_trends.txt` byte for byte) |
| `blind_search.py` | blind Lomb–Scargle search with VSX check, split-half and per-detector tests (first run inline; script reproduces the per-detector numbers exactly) |

`field_psf.py` was changed once more during the work: `frames.npz` now holds every aligned exposure (it held 24),
because the difference images need the in-eclipse frames themselves. R1–R4 were re-run with the new version; the
photometry is identical.

## 8. Ensemble reference stars: exclude variables (`field_analysis.py`, `REF_SCAN_SNR = 6`) — bug fix

- **Limitation.** Reference stars were chosen by low scatter *out of eclipse of the target clock*. In sparse fields
  (R4: 8 stars) the Gaia eclipsing binary itself was chosen as a reference, because its out-of-eclipse frames are
  quiet; its eclipses then entered the ensemble correction and made every other star appear to *brighten* at the
  binary's eclipse phases (R4 TIC star −8.7%).
- **Why it matters.** A spurious anti-correlated signal on the TIC star is exactly the wrong sign of evidence for
  the attribution question, and it would bias all depths in sparse fields.
- **Reference.** Ensemble photometry assumes non-variable references (Honeycutt 1992; Broeg, Fernández & Neuhäuser
  2005, AN 326, 134, iterative rejection of variable comparison stars).
- **How measured.** TIC-star depth in R4 and the validation neighbour of TIC 140659978 (both should be ≈ 0).
- **Result.** References now chosen by scatter over *all* exposures, then any reference with a phase-scan
  signal-to-noise > 6 is dropped (`references_dropped_for_phase_signal` in `analysis.json`). R4 TIC star −8.7% →
  −1.4 ± 1.0%; validation neighbour −4.3% → −1.1 ± 3.5%; R1 and R2 depths changed by < 0.002. **Kept.**

## 9. Jitter-weighted empirical significance (`significance.py`)

- **Limitation.** Formal photometric errors ignore visit-to-visit calibration scatter; a weighted mean with
  formal errors only is dominated by a few bright, over-confident points.
- **Why it matters.** Without jitter, a bright R4 control star showed a 5% "dip" at the binary's phase.
- **Reference.** Extra-variance ("jitter") term: Gregory 2005 (ApJ 631, 1198); empirical false-alarm probability by
  random phase centres as a bootstrap over eclipse-free data (Efron & Tibshirani 1993).
- **How measured.** Control-star z-values in all five regions.
- **Result.** Weights 1/(σ² + jitter²); controls within |z| < 2 except one bright R4 field-edge star (4.4%, z 3.2 at
  phase 0.5 only), identified as visit-correlated scatter (single exposures 0.60–1.16). **Kept.**

## 10. Difference-image centroid (`make_figures.diff_centroid`)

- **Limitation.** Photometry at fixed Gaia positions can only say *how much* each catalogued star dims; it cannot
  show *where* the missing light is, which is the standard test used for Kepler/TESS (Bryson et al. 2013).
- **Why it matters.** It is an independent test of attribution that does not depend on the PSF photometry of the
  TIC star, and it is decisive when the two stars are close (R3: 1.26 px).
- **Reference.** Bryson, S. T. et al. 2013, PASP 125, 889 (difference-image centroiding).
- **How measured.** Distance of the fitted position from the Gaia binary and from the TIC star, with 100 bootstrap
  resamples of the in/out pairs.
- **Result.** R2 0.02 px from the binary (TIC star excluded at 3.9σ), R3 0.17 ± 0.09 px (15σ), R4 0.03 px (4.0σ).
  Fails in R1 (crowded nebular field: best residual 11.6 px away). First version got stuck in local minima and was
  dominated by bright-star residuals → grid search at 0.2 px with a negative amplitude required, and weighting by
  the standard error of each pixel. **Kept.**

## 11. `eclipse_timing.py` starting value

- **Limitation.** For faint stars with negative fluxes the starting depth could fall outside the fit bounds
  ("Initial guess outside bounds"; R5 primary).
- **Result.** Start value clipped to [0.02, 0.9]. R5 primary timing now measured (+53 ± 22 min vs OGLE on the
  first R5 run, +61 ± 24 min after the re-run); other regions unchanged. **Kept.**

## Tests after all changes

No file outside `research/` changed, so the application tests are unaffected; the baseline above (backend 286
passed / 5 skipped / 1 pre-existing failure; frontend 83/83) was re-run after the research tools were in place.
