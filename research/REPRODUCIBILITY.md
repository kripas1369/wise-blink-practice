# Reproducing the results

Everything runs from the repository root with the project's virtual environment. Network access to IRSA
(SPHEREx cutouts and archive), the ESA Gaia archive (TAP), VizieR and SIMBAD is needed; no account or payment.

```bash
cd wise-blink-practice
export PYTHONPATH=.:research MPLCONFIGDIR=/tmp/mpl
PY=.venv/bin/python
```

Software: Python 3.14 (`.venv`), numpy, scipy, astropy, astroquery, pyvo, matplotlib, Pillow (versions as installed
in `.venv`; `$PY -m pip freeze` lists them). Cutouts are cached in `cache/cutouts/` and archive queries in
`research/out/images/`, so a second run is offline and gives identical numbers (checked on R1).

## 1. Catalogue-level result (TESS-EBs vs Gaia DR3 eclipsing binaries)

```bash
$PY research/tessebs_gaia_xmatch.py          # ~10 min; ESA TAP, 12 uploads of 400 rows
$PY research/dilution_check.py
$PY research/misattribution_trends.py        # latitude / magnitude / depth / period trends (checked: identical output)
```

Inputs: `cache/catalogs/tess_ebs_v1.0.csv` (TESS-EBs, Prša et al. 2022, as used by the website) and the Gaia DR3
table `gaiadr3.vari_eclipsing_binary` joined with `gaiadr3.gaia_source`. Parameters (in the script): search radius
63″ (3 TESS pixels), period match P_Gaia/P_TESS ∈ {0.5, 1, 2} within 0.2%, "same star" if < 4″.
Outputs: `research/out/tessebs_gaia_xmatch.json`, `tessebs_gaia_xmatch_other.csv`, `misattributed_singles.json`,
`dilution_check.json`.

## 2. The five regions

```bash
$PY research/coverage_candidates.py           # SPHEREx coverage + 2026 clock error per candidate
$PY research/catalog_check.py                 # VSX / OGLE / SIMBAD around each target
$PY research/five_targets.py                  # five_target_catalog.csv

$PY research/field_psf.py R1_lmc_tic179637488 80.51578 -67.92467 --fov 4 --gmax 16.5 --tic 179637488 --budget 30,30,40
$PY research/field_psf.py R2_tic349156098     108.1835 -64.7090  --fov 4 --gmax 16.5 --tic 349156098 --budget 30,30,40
$PY research/field_psf.py R3_tic309659126     79.5068  -60.6899  --fov 4 --gmax 16.5 --tic 309659126 --budget 35,35,40
$PY research/field_psf.py R4_tic160195393     258.8506  85.2115  --fov 4 --gmax 16.5 --tic 160195393 --budget 30,30,40
$PY research/field_psf.py R5_sep_tic31511621  89.1576  -67.6069  --fov 5 --gmax 16.5 --tic 31511621 \
        --budget 35,35,50 --eph-json research/data/eph_ogle_lmc_ecl_39123.json
```

`--budget P,S,O` = exposures per detector inside primary eclipse, inside secondary eclipse, and outside, chosen by
`backend.app.eclipses.select_for_download` (spread in time and wavelength). Then, for each run NAME with TIC number
TIC and Gaia binary EB:

```bash
$PY research/field_analysis.py NAME --tic TIC
$PY research/eclipse_timing.py NAME EB TIC
$PY research/depth_spectrum.py NAME EB TIC --shift-from-timing
$PY research/make_figures.py NAME --tic TIC --eb EB [--target TIC_STAR_GAIA_ID]
$PY research/significance.py NAME --tic TIC --centre PHASE --stars EB TIC_STAR_GAIA_ID CONTROL1 CONTROL2
```

Outputs per run in `research/experimental_results/NAME/`:

| file | content |
|---|---|
| `meta.json` | position, field size, collections, numbers of images, wavelength range, PSF shape per detector, ephemeris override |
| `observation_log.csv` | every exposure used: MJD, UTC date, detector, wavelength, bandwidth, observation id, collection, flagged pixels, fit χ² |
| `fits_headers.json` | selected FITS header keys of every exposure |
| `stars.json` | Gaia DR3 stars fitted (id, G, BP−RP, pixel position at the epoch) |
| `photometry.npz` | flux and formal error of every star in every exposure |
| `analysis.json`, `lightcurves.npz` | normalised light curves, eclipse depths, variability statistics, clock |
| `timing_<EB>.json`, `depth_spectrum_<EB>.json` | eclipse timing, depth per wavelength |
| `fold.png`, `difference.png`, `flipbook.gif`, `figures.json` | figures and the difference-image numbers |
| `significance_<phase>.json` | empirical false-alarm probabilities |
| `coadds.npz`, `frames.npz` | per-detector co-adds and every aligned exposure |

## 3. PSF validation (code change 2 and 3)

```bash
$PY research/field_psf.py validate_140659978        72.46399 -72.46291 --fov 3 --gmax 16.5 --tic 140659978            # core + wing
$PY research/field_psf.py validate_140659978_nowing 72.46399 -72.46291 --fov 3 --gmax 16.5 --tic 140659978 --no-wing  # single Gaussian
```

(320 exposures; the selection is stored in each folder's `observation_log.csv`).

## Blind search and summaries

```bash
$PY research/blind_search.py        # experimental_results/blind_search_auto.txt (VizieR VSX queries)
$PY research/collect_results.py     # experimental_results/results_summary.json (every number in the report)
$PY research/five_targets.py        # five_target_catalog.csv
```

## Expected results (13 November 2026 data)

| | expected |
|---|---|
| Cross-match | 1,265 same star, 278 other star, 3,039 no Gaia EB; 242/245 possible by dilution |
| Trends | other-star fraction 0.298 at \|b\| < 5°, 0.080 at 30–50°; χ² p = 1.9 × 10⁻¹⁵ |
| R1 | Gaia binary 11.4 ± 2.3% / 8.9 ± 1.6%; TIC star −2.2 ± 2.3% / −0.2 ± 1.9%; LS 1.64856 d |
| R2 | 20.9 ± 2.9% at phase 0, 42% at 0.48 (z 11.1); TIC star −2.0 ± 1.4%; centroid 0.02 px from binary |
| R3 | 21.4 ± 0.9% / 16.1 ± 1.1%; TIC star −0.4 ± 0.8% / +0.3 ± 1.0%; centroid 15σ from TIC star |
| R4 | 30.5 ± 0.8% / 27.6 ± 1.0%; TIC star −1.4 ± 1.0% / −0.4 ± 1.3%; centroid 4.0σ from TIC star |
| R5 | 32.2 ± 2.7% / 14.8 ± 3.7%; TIC star +0.2 ± 0.5% / +0.6 ± 0.6%; z 11.5 / 5.2; timing +61 ± 24 min vs OGLE |

A fresh archive query may add SPHEREx images and change these numbers within their errors.

## Random seeds and determinism

- `significance.py`: `numpy.random.default_rng(1)`.
- `eclipse_timing.py`: 1,000 bootstrap resamples, `numpy.random.default_rng(1)`.
- `make_figures.diff_centroid`: 100 bootstrap resamples, seed 1.
- Exposure selection is deterministic given the cached archive query (`research/out/images/<key>.json`). A fresh
  archive query can return more images as IRSA adds data, which changes the selection slightly.

## Time systems

SPHEREx `MJD-AVG` (UTC, mid-exposure) → BTJD (BJD_TDB − 2457000) with `backend.app.eclipses.to_btjd`
(barycentric light-travel time toward the star). OGLE T0 is HJD − 2450000; HJD and BJD_TDB differ by < 0.001 d,
negligible here (≤ 0.0004 in phase for R5).
