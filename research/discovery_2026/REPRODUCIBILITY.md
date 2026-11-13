# Reproducibility

Everything in `research/discovery_2026/` was produced on 13 Nov 2026 (UTC) from public data without credentials.
No production code of the TimeLens application was modified; nothing was committed.

## Environment

| Item | Value |
|---|---|
| Repository | `wise-blink-practice`, branch `kripas-frontend`, HEAD `b03567e` (working tree has the owner's uncommitted changes; this directory is untracked) |
| OS | macOS (Darwin 25.4.0) |
| Python | 3.14.7 (`.venv`) |
| numpy / scipy / astropy / requests / matplotlib | 2.5.4 / 1.18.1 / 8.0.2 / 2.34.2 / 3.11.2 |
| Reused project code | `backend/app/flags.py` (`bad_pixel_bitmask`) |
| Environment for every command | `PYTHONPATH=.:research:research/discovery_2026/scripts MPLCONFIGDIR=/tmp/mpl` |

## External data (all public)

| Dataset | Access | Version / release | Used for |
|---|---|---|---|
| SPHEREx L2 spectral images | IRSA SIA2 `https://irsa.ipac.caltech.edu/SIA` (collections `spherex_dr1`, `spherex_dr1_deep`, `spherex_qr3`, `spherex_qr3_deep`) → S3 keys; bytes from `https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/` (HTTP Range) | DR1 `l2b-v27-2026-23x/24x`, QR3; file VERSION 7.0.5 | all SPHEREx measurements; the S3 key, MJD and version of every exposure are in `data/stamps/NAME.json` and `EXPERIMENTAL_RESULTS/photometry/NAME.csv` |
| SPHEREx calibration | S3 `…/{dr1,qr3}/calibration/…` (identical ETags in DR1 and QR3) | `cal-swcs-v5-2026-191`, `cal-sapm-v3-2026-191`, `cal-epsf-v1-2026-191` (D3 `v2`) | wavelength, bandwidth, solid angle, ePSF; SHA-256 in `data/calib/SHA256SUMS` |
| SPLICES | IRSA TAP async `https://irsa.ipac.caltech.edu/TAP/async`, table `splices` | v8.6 | sample selection; jobs 28122138 and 28122604; ADQL in `data/selection/*_query.json` |
| AllWISE | IRSA TAP `allwise_p3as_psd` | AllWISE | neighbour lists for forced photometry (`data/neighbours/`) |
| Gaia DR3 | ESA Gaia archive TAP `https://gea.esac.esa.int/tap-server/tap/sync` | DR3 | identifiers (`data/selection/simbad_xmatch.csv`) |
| 2MASS Ks | via SPLICES column `k` | 2MASS PSC | independent flux-scale check (`VALIDATION/flux_check.*`) |
| SIMBAD | CDS TAP `https://simbad.cds.unistra.fr/simbad/sim-tap/sync` (returned an HTML "Page unavailable" page all day on 13 Nov 2026) → Harvard mirror `https://simbad.harvard.edu/simbad/sim-tap/sync` | live database, queried 13 Nov 2026 | identifiers, object types, reference counts within 15″ (`data/selection/simbad_xmatch.csv`); reference lists of the two candidates |
| VizieR | CDS | — | not used (CDS unavailable) |

Calibration SHA-256 (from `data/calib/SHA256SUMS`):

```
027986f7d312e2392d4bae24f7cb3de4fbf2ddd195a438a429a348ce626df754  epsf_D3_spx_cal-epsf-v1-2026-191.fits
6c753e5e322e9905fe44be6505e492f1943e3b115e5dea49b010140570dad2a1  epsf_D3_spx_cal-epsf-v2-2026-191.fits
b37cb9423746477427121e2c3b3f4b8291c1df9cadba6f770ea1a7f962748b4c  epsf_D4_spx_cal-epsf-v1-2026-191.fits
73847447802363cbae37078d404a39f266ec3cca863461cacaae730e18facfe7  epsf_D5_spx_cal-epsf-v1-2026-191.fits
52f85faeb93d67ed2020b68a628fc947c1f0b78cbf9282ca193ec6d588ac1a36  epsf_D6_spx_cal-epsf-v1-2026-191.fits
4c731f195020b227ae05afc38463d30a0d18cab5a3786bc7af0bd49c46f87ea5  solid_angle_pixel_map_D3_spx_cal-sapm-v3-2026-191.fits
b5ede34463ab365ce4b97fdb10a98eba85c8d628141e7e6df1b3e84d50831204  solid_angle_pixel_map_D4_spx_cal-sapm-v3-2026-191.fits
1081fd45e39f96297589e9c4f8cec4fd212c081798fb62886dbb9607b8c865e2  solid_angle_pixel_map_D5_spx_cal-sapm-v3-2026-191.fits
0986595851aab50dcc984b2d2f1c66a57d7726c5996368ed449bf89cf44346f7  solid_angle_pixel_map_D6_spx_cal-sapm-v3-2026-191.fits
51750c8f948a30541d391e54930279aa067c62c398a7cc2679e592bc6044427a  spectral_wcs_D3_spx_cal-swcs-v5-2026-191.fits
dbdcb8addb4ffe817f31786c8cb359b1f47df3528173e9d4602b94c84f7d7c1a  spectral_wcs_D4_spx_cal-swcs-v5-2026-191.fits
3361428284bddad1dcdce42081ebfbd225acb0b19f6caa94fba3e133bbabfc1c  spectral_wcs_D5_spx_cal-swcs-v5-2026-191.fits
19195d253892883586aa2183cb66238b32f6032ade62d490b36b85b0dd18f212  spectral_wcs_D6_spx_cal-swcs-v5-2026-191.fits
```

## Commands, in order

```
P="env PYTHONPATH=.:research:research/discovery_2026/scripts MPLCONFIGDIR=/tmp/mpl .venv/bin/python research/discovery_2026/scripts"
$P/access_check.py                          # Stage C audit -> EXPERIMENTAL_RESULTS/access_check.json
$P/select_targets.py                        # SPLICES protostars (async TAP, ~8 min)
$P/select_targets.py background             # SPLICES background stars (async TAP, ~8 min)
$P/choose_sample.py                         # sample.csv (seed 20261113)
$P/run_targets.py research/discovery_2026/data/lists/pilot.csv           # EC 53 / V1647 Ori / Elias pilots
$P/run_targets.py research/discovery_2026/data/lists/batch0.csv --workers 16
$P/run_targets.py research/discovery_2026/data/lists/batch1.csv --workers 16
$P/run_targets.py research/discovery_2026/data/lists/batch2.csv --workers 16
$P/run_targets.py research/discovery_2026/data/lists/batch_bg.csv --workers 12
$P/ice_fit.py NAME ...                      # re-fit only (uses existing photometry)
$P/simbad_xmatch.py                         # Gaia DR3 ids, SIMBAD ids (CDS, else Harvard mirror), Karambelkar check (~6 min)
$P/timelines.py                             # OBSERVATION_TIMELINES/
$P/coverage_summary.py                      # OBSERVATION_TIMELINES/coverage_summary.json (ARCHIVE_COVERAGE.md tables)
$P/flux_check.py                            # VALIDATION/flux_check.*
$P/epoch_sensitivity.py                     # EXPERIMENTAL_RESULTS/population/epoch_sensitivity.csv
$P/population.py                            # EXPERIMENTAL_RESULTS/population/ (targets, pairs, summary, merged bias)
$P/intrinsic_scatter.py                     # EXPERIMENTAL_RESULTS/population/intrinsic_scatter.json
$P/co2_h2o_consistency.py                   # EXPERIMENTAL_RESULTS/population/co2_h2o_consistency.json
$P/colour_diagnostic.py                     # EXPERIMENTAL_RESULTS/colour/
$P/injection_test.py EC53 V1647Ori SJ06135925p1743210 SJ01163354p6449243 SJ07004057m0838494 \
    SJ23155741p6122411 SJ05442898p3025430 SJ15315679m5532126 SJ19084266p0748568
                                            # VALIDATION/injection_* (simulated perturbations; rewrites the summary)
$P/scatter_model.py SJ06135925p1743210 SJ20573116p4402374 SJ00381870p6306053 SJ18570951p0210407 \
    SJ06123374p1749238 SJ07051097m1105081 SJ22280291p6901168 SJ07142692m1203589 V1647Ori EC53
                                            # VALIDATION/scatter_model.csv (ice change vs unabsorbed light vs covering)
$P/crowding_check.py SJ06135925p1743210 0 1 2 3 7   # VALIDATION/crowding_*
$P/jackknife.py SJ06135925p1743210          # VALIDATION/jackknife_*
$P/candidate_figure.py SJ06135925p1743210   # EXPERIMENTAL_RESULTS/figures/candidate_*
$P/purity_check.py                          # EXPERIMENTAL_RESULTS/population/purity_check.json (needs simbad_xmatch.csv)
$P/make_catalog.py                          # CANDIDATE_CATALOG.csv (run last)
```

`population.py` must run before `intrinsic_scatter.py`, `co2_h2o_consistency.py`, `colour_diagnostic.py` and
`make_catalog.py`; `intrinsic_scatter.py` before `co2_h2o_consistency.py`. All later scripts read only saved
photometry and fits, and are deterministic apart from the bootstrap (seed 20261113).

`run_targets.py` skips the download when `data/stamps/NAME.npz` exists, so re-running reproduces photometry and fits
from the saved stamps. Stamps are 15 × 21 pixel cut-outs (IMAGE, FLAGS, VARIANCE) plus the full image header WCS.

## Fixed parameters

| Parameter | Value | Where |
|---|---|---|
| random seed (sample draw, bootstrap) | 20261113 | `choose_sample.py`, `population.py` |
| stamp half-size | 7 rows × 10 columns; edge rejection 4 px | `spx_s3.py` |
| ePSF fit box, neighbour radius, merge distance | ±6 px, 90″, 0.9 px | `phot.py` |
| neighbour limit | AllWISE W1 < 15.5 | `phot.py` |
| bad-pixel mask | `backend.app.flags.bad_pixel_bitmask` (SOURCE bit not bad) | `spx_s3.py` |
| core-quality cut | ≥ 6 unflagged pixels within 1.5 px | `ice_fit.py` |
| S/N cut | ≥ 3 per exposure | `ice_fit.py` |
| error floor | 2 % per exposure | `ice_fit.py` |
| visit / pass / same-day group gaps | 60 d / 20 d / 0.5 d | `ice_fit.py` |
| robust-change thresholds | |z| ≥ 3 baseline, ≥ 2 same sign in every variant | `population.py` |
| FDR | Benjamini–Hochberg 5 % | `population.py` |
| quality rule (fixed before population results) | ≥ 2 complete epochs and joint-fit χ²_red ≤ 15 | `population.py` |
| ice detection | mean depth / error ≥ 5 | `population.py` |
| extinction colour ratio, τ_H2O/A_K | 1/0.52 = 1.92, 0.55 | `colour_diagnostic.py` |
| intrinsic-scatter grid, upper limit | s ∈ [0, 1] (2001 steps), one-sided 95 % (Δ(−2 ln L) = 2.71) | `intrinsic_scatter.py` |
| unabsorbed-light colours tried | q = 4, 2, 0, and continuum-shaped (covering) | `scatter_model.py` |
| jackknife block width | 0.15 µm | `jackknife.py` |

## Timing

Pilot (EC 53): 280 exposures, 35 s. Sample: ~40–100 s per target for stamps, 4–40 s photometry, 30–60 s ice fits;
run log with timestamps in `EXPERIMENTAL_RESULTS/run_log.jsonl`.
