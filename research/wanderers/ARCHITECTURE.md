# SPHEREx Infrared Wanderers: architecture and data flow

Written 13 Nov 2026 before any new results, after reading the repository.

## The existing project (unchanged by this work)

- **Backend:** Python with FastAPI (`backend/app/`, `uvicorn backend.app.main:app`). It is not Django, despite what the prompt says.
- **Frontend:** plain HTML/JS with Aladin Lite (`frontend/`). It is not React, Vite or Three.js.
  - Explore: `index.html`.
  - Eclipse Mode: `eclipse.html`, with its catalogue in `frontend/frames/eclipse/catalog.json`.
  - Methane Vision: `methane.js`.
- **Tests:** pytest in `backend/tests` and npm tests in `frontend/tests`.
  - On 13 Nov 2026 at about 22:00 local time: 286 passed, 5 skipped, 1 failed.
  - The failure is known: `test_day5.py::test_spectrum_points_are_exactly_the_light_curve_points` expects WISE 0855 on detectors [2, 5, 6], but the data now has 1–6.
- **Git:**
  - HEAD is `d8441c2`.
  - The working tree has uncommitted edits in `frontend/` (not touched here) and untracked research files.
- **Data releases:**
  - The website's `backend/app/config.py` still lists the QR2 collections, which IRSA no longer serves.
  - The research code (`research/dr1.py`) and this project use `spherex_dr1`, `spherex_dr1_deep`, `spherex_qr3` and `spherex_qr3_deep`.
  - QR2 files are never mixed in.

## Reused modules (imported, not edited)

| Module | Used for |
|---|---|
| `backend/app/archive.py` | IRSA TAP image search (`find_images`), file paths, cached cutouts, visit grouping (`group_epochs`) |
| `backend/app/clean.py` | IMAGE − ZODI, σ = √VARIANCE, official FLAGS bad-pixel mask, MJD-AVG, wavelength at a position |
| `backend/app/align.py`, `coadd.py` | Resampling onto one north-up 6.15″ grid; inverse-variance co-adds |
| `backend/app/gaia.py` | Gaia DR3 from IRSA (epoch 2016.0) |
| `backend/app/known_objects.py` | JPL Small-Body Identification, with SPHEREx's own position as the observer |

Two settings are redirected inside `research/wanderers/common.py` without editing the modules:
- `archive.CACHE_DIR` points to `research/wanderers/cache`, so the website's cutout cache and its size trimming never see these files.
- `known_objects.CACHE` points to `research/wanderers/cache/jpl`.

## New code (`research/wanderers/`)

```text
select_fields.py   sampled HEALPix tiles -> coverage, Gaia, CatWISE, SIMBAD, sample cutouts -> scored ranking
astrometry.py      one field: cutouts -> detector-epoch co-adds -> detection -> PSF positions -> Gaia registration
                   -> stationary / moving fits (+ negative control on Gaia stars, half/half registration)
classify.py        error calibration, Gaia/CatWISE/SIMBAD matches, CatWISE long baseline, artifact checks,
                   JPL check of one-visit detections and movers, classes 1-7
inject.py          fake moving sources in the real co-adds -> completeness, motion accuracy, false positives
build_catalog.py   siwc.json (catalog.json-style header + rows), siwc.csv, evidence PNGs
common.py          caches, archive retries, tangent-plane geometry, exclusion lists
```

Outputs:
- `results/` holds the field ranking and one folder per field, plus the final `siwc.json` and `siwc.csv`.
- `figures/` holds the evidence images.
- `logs/` holds the run logs.
- `PROGRESS_LOG.md` is the progress log, and `REPORT.md` the report.

## Data-handling decisions

- **The time unit is the detector-epoch: one visit times one detector.** The six detectors and 102 wavelength channels are never treated as separate times.
- **Wavelength.** Inside one detector the filter wavelength changes across the array, so a detector-epoch co-add covers that detector's band. The same band is compared between visits.
  - Wavelengths are recorded from the WCS-WAVE lookup, at the field centre, for each exposure. They are used only to label bands, never for spectral science; the prompt notes this lookup is for display.
  - Missing channels 51 and 52 don't matter for band co-adds.
- **PSF.** Positions come from a pixel-integrated Gaussian whose width is fitted for each detector-epoch on isolated bright stars.
  - DR1 cutouts include the official `EPSF` extension. It is kept in the cached files but not used by the fitter (a stated limitation).
  - The positional errors that are actually used come from the Gaia negative control, not from the PSF model.
- **Pixels used.** Flagged pixels (the official bad-flag list in `backend/app/config.py`) and pixels with no valid variance are excluded from every fit.
- **Timestamps.** Times come from `MJD-AVG` of each exposure, never from the processing date `DATE`.
