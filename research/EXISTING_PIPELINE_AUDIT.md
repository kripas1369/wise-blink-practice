# Audit of the existing SPHEREx TimeLens science pipeline

*Written 13 Nov 2026 from the source code on branch `kripas-frontend` (uncommitted changes included). Every statement
about behaviour below comes from reading the code itself, or from a read-only check on cached files (marked
"verified on cache"). Notes in `notes/*.md` are quoted only as "documented". No file other than this one was changed.*

---

## Summary: the five limitations that matter most for science

1. **The website asks IRSA for data releases that no longer exist, and does not notice.** `config.COLLECTIONS` is
   still `("spherex_qr2", "spherex_qr2_deep", "spherex_qr3", "spherex_qr3_deep")`. IRSA now returns 0 rows for both
   QR2 collections, and the query does not fail, so every live search (`archive.find_images`) silently returns only
   QR3 data (May 2026 onwards) and never sees DR1 (`spherex_dr1`, `spherex_dr1_deep`), which holds 5 to 10 times more
   exposures. Only `research/dr1.py` uses the current collections. The cached image lists show the switch happened
   on 12 Nov 2026 between 17:10 and 18:57 UTC; every list cached after that is QR3-only. The two eclipse builds on
   the website and most flipbook frames rest on QR2 files that can no longer be downloaded or re-checked. The cutout
   cache key (`archive.cutout_file`) does not include the collection, so an old QR2 file and a new DR1 file of the
   same exposure would share one cache entry.
2. **Flagged pixels leak into "good" pixels, and the noise is propagated only roughly.** `clean.clean_cutout` builds
   the bad-pixel mask but does not blank the flagged values. `align.align` then resamples the image with bilinear
   interpolation (`reproject_interp`, default `order="bilinear"`) and the mask with nearest-neighbour. A finite
   flagged value (hot pixel, cosmic ray, persistence) therefore contributes up to about half of the value of
   neighbouring grid pixels that are marked good. Variance is also resampled bilinearly and neighbouring pixels are
   then treated as independent. The result: difference-image scatter of 0.7 to 0.8 instead of 1 (documented, Day 3),
   and the eclipse fits needing an extra 2 to 6% "jitter" per detector to make the scatter consistent with the errors.
3. **"Eclipse depth" is not the quantity TESS reports, and photometry ignores the PSF.** `eclipse_depth.weighted_depth`
   averages the flux over the middle half of the eclipse (`CENTRAL = 0.5`), which for a V-shaped or partial eclipse is
   shallower than the depth at minimum that TESS-EBs lists. `eclipse_build.analyse` nevertheless compares the two in
   `checks.tess_band` (TIC 219900027: 0.196 vs 0.245; TIC 233208885: 0.409 vs 0.477). All photometry uses a fixed
   2-pixel (12.3″) circle with no aperture correction, while the PSF width changes from about 5″ (D2) to about 9″ (D5)
   (verified on cache), and the PSF cube itself is discarded at download (`DROP_PSF_FROM_CUTOUTS = True`).
4. **The TESS "clock" quality check is reported but never enforced.** `eclipses.MAX_PHASE_ERROR = 0.01` only appears in
   a text label. Nothing compares the predicted phase drift with the eclipse width. For 36% of TESS-EBs binaries the
   drift by BTJD 4000 (27 Mar 2026) is larger than half the eclipse width, and for 50% it is larger than the "middle
   half" window used for depths. For narrow, long-period eclipses (TIC 233058262: width 0.0071, drift 0.0061) the
   selected "in-eclipse" exposures can sit partly or wholly outside the real eclipse, which pushes measured depths
   toward zero. Missing uncertainties in the catalogue are turned into 0, which makes the clock look perfect.
5. **Every exposure sees a different wavelength, and only the eclipse and light-curve code fully handles that.**
   SPHEREx's linear variable filter gives each exposure its own wavelength at the target. The flipbook co-adds up to
   8 exposures per visit (different wavelengths) into one frame, and `diff.difference` subtracts two such co-adds
   without PSF matching, flux scaling or wavelength matching; only the default pair is chosen by closest mean
   wavelength. In Eclipse Mode, the normal-brightness curve S(λ) has room for at most one or two interior spline knots
   per detector (about 30 out-of-eclipse points each) and is held constant beyond the fitted wavelength range, so real
   spectral features and edge exposures can leave wavelength-dependent residuals in the depth spectra.

## Source attribution: the limitation this investigation addressed

Eclipse Mode measures the star that TESS-EBs names: `eclipses.find()` matches the TESS-EBs entry within 10″, the
aperture (2 px = 12.3″) is centred on the TIC position, `lightcurve.neighbours()` warns only about Gaia stars up to
3 mag fainter than the target (`NEIGHBOUR_G_LIMIT`), and the ≤ 8 comparison stars are chosen for isolation, not
variability. If the eclipse belongs to a neighbour, a neighbour inside ~12″ (R3: 7.4″) is blended into the aperture
and its eclipse looks like the TIC star's; a neighbour further out (R2, R4: ~40″) leaves the TIC star flat, which the
page can only report as "not detected"; and a faint eclipsing neighbour (R2: 5.3 mag fainter) triggers no warning.
How `research/` addresses this, and the other limitations above:

| Limitation | Addressed in `research/` |
|---|---|
| One aperture on the named star; neighbours not modelled | forced PSF photometry of every Gaia star (`field_psf.py`) |
| No position test for the eclipse | difference-image centroid (`make_figures.diff_centroid`) |
| Only the TESS-EBs clock | `--eph-json` external ephemeris (R5: OGLE) |
| QR2 collections (summary item 1) | `dr1.py` uses DR1 + QR3; app change recommended, not applied |
| Significance from formal errors only | empirical false-alarm test against 1,000 random phases (`significance.py`) |
| PSF ignored (item 3) | pixel-integrated PSF with wing, fitted per detector |
| Flagged-pixel leakage (item 2) | **not fixed**: the research code reuses `clean`/`align`; its effect is extra random scatter, absorbed in the jitter term and checked by the random-phase test, not a phase-locked signal |
| Depth averaged over the middle half (item 3) | **not changed**: research depths use the same definition, so they are lower limits on the depth at minimum (stated in the report) |

## Test baseline (no network)

Command: `cd /Users/kripaskhatiwadaicloud.com/wise-blink-practice && .venv/bin/python -m pytest backend/tests -q -x 2>&1 | tail -20`

Result: **1 failed, 112 passed, 1 warning in 2.48 s.** Because of `-x`, pytest stopped at the first failure, so the
tests after it in collection order were not run. The full run without `-x` (13 Nov, 10:30 and again 11:15) gives
**286 passed, 5 skipped, 1 failed** (the same test); frontend `npm test`: 83/83. This is the baseline quoted in
`CODE_CHANGES.md`.

- Failure: `backend/tests/test_day5.py::test_spectrum_points_are_exactly_the_light_curve_points`, at line 143:
  `assert [d["band"] for d in spec["detectors"]] == [2, 5, 6]` got `[1, 2, 3, 4, 5, 6]`. The code is consistent (the
  first assertion, that spectrum points equal light-curve points, passed). The test hard-codes which detectors WISE
  0855 had frames for; D1, D3 and D4 have since been prepared (`frontend/frames/index.json`, uncommitted). This is a
  stale test expectation, not a pipeline bug.
- Warning: Starlette deprecation of `httpx` in `fastapi.testclient`.
- `notes/DAY6_FINDINGS.md` documents 128 backend tests passing on 1 Nov; the suite has grown since.

---

## How to read each section

Each of the 18 areas has the same parts: **Current implementation** (file and function, constants with values),
**Assumptions**, **Inputs and outputs**, **Limitations**, **Possible error sources**, **Improvements**, and
**Can it change scientific conclusions?** (yes / no / maybe, with the reason).

---

## 1. Backend architecture

**Current implementation.**
- One FastAPI app, `backend/app/main.py:app`, serves both the JSON API (`/api/...`) and the static website
  (`frontend/`, mounted at `/`, plus `/jobframes` for live jobs from `cache/frames/`). Static files are sent with
  `Cache-Control: no-cache` (`RevalidatedFiles`).
- Processing is a chain of command-line modules that each read and write files in a "frames folder"
  (`frontend/frames/<target>/d<detector>/`): `render.py` (download, clean, align, co-add, PNG + `epoch<i>.fits` +
  `manifest.json`) → `gaia.py` (`gaia.json`) → `diff.py` (`diff.json`, `diff_<a>_<b>.png`) → `lightcurve.py`
  (`exposures.fits`, `lightcurve.json`) → `proof.py`, `spots.py`, `recovery.py`, `gif.py`, `originals.py`,
  `pixels.py`, `visit_frames.py` → `spectrum.py` (per target). Eclipse Mode is `eclipses.py` (catalogue, time, phase,
  selection), `eclipse_depth.py` (pure statistics) and `eclipse_build.py` (orchestration, `eclipse.json`).
- Live work: `main._pool = ThreadPoolExecutor(max_workers=1)` runs one job at a time; job state lives in the
  in-memory dict `main._jobs` (lost on restart). `_pipeline_after_render` runs the after-render steps and turns any
  exception into a warning string, so a job can be "ready" with some products missing.
- Constants: `PREPARED_FOV = 3.0`, `SAME_TARGET_ARCSEC = 5.0`, `JOB_EXPOSURES_PER_VISIT = 4` (prepared frames use 8),
  `COVERAGE_CACHE_SECONDS = 3600`, `FAILED_JOB_RETRY_SECONDS = 600`, `ECLIPSE_LIVE_BUDGET = {"primary": 20,
  "secondary": 10, "outside": 25}`, `ECLIPSE_MIN_IN_PRIMARY = 12`.
- Typed positions become jobs keyed by `_job_key` (RA/Dec rounded to 0.0001°) and are **not** moved for proper motion
  (`render_frames(..., "typed position, rounded to 0.0001° (not moved for proper motion)")`).

**Assumptions.** One user at a time; IRSA is the only image source; files on disk are the single source of truth;
everything shown on the website was produced by these modules.

**Inputs and outputs.** Inputs: IRSA TAP and cutout service, SIMBAD, Gaia DR3 at IRSA, TESS-EBs CSV at MAST, JPL
SBIdent and Horizons, Google Gemini (`ask.py`). Outputs: JSON, PNG, FITS and GIF files per folder.

**Limitations.** Single worker; in-memory job state; no provenance hash tying a JSON output to the exact cutouts and
code version used (only `made_at` and `made_by`); partial pipelines are possible ("warnings"). Live jobs and prepared
frames use different depths (4 vs 8 exposures per visit).

**Possible error sources.** Steps that read the shared cutout cache by filename pattern (`rebuild.cached_visits`,
`spectrum.psf_fwhm`, `spots.exposure_state`, `methane.fetch_window --offline`) pick up any file that matches, including
files written by other steps (see section 18, item 5).

**Improvements.** Record collection, cutout file names and a code version (git hash) in every output; make
after-render failures visible as a status, not only a warning; persist job state.

**Can it change scientific conclusions?** **Maybe.** The architecture itself is sound, but cache sharing between steps
can change which exposures enter a light curve (section 18).

---

## 2. Frontend architecture

**Current implementation.**
- Plain HTML and ES modules with no build step (`frontend/package.json`: `"start": "python3 -m http.server 8000"`,
  tests with `node --test`). Pages: `index.html` (flipbook and analysis panels), `eclipse.html` (Eclipse Mode),
  `about.html`.
- `frontend/js/app.js` wires the panels: Aladin Lite sky map from CDNs (`ALADIN_SCRIPTS`, version 3.8.2) with ESA
  ESASky background surveys (2MASS, AllWISE, DSS2), target search through SIMBAD (`resolve.js`), the flipbook
  (`flipbook.js`), difference view (`diffview.js`), light curve, spectrum, proof, spots, recovery, scientist view,
  methane view, Gemini "ask" panel, coverage timeline (`timeline.js`).
- `frames.js:checkManifest` refuses a manifest whose frames are not in strictly increasing MJD, whose band differs
  from the folder, or whose brightness scale is invalid. Data come from `/api/...` when the API answers `/api/health`,
  otherwise from the prepared files in `frontend/frames/`.
- Computation done in the browser: positions moved to `VIEW_EPOCH = 2026.0` (`motion.js`), pixel-to-sky conversion
  (`sky.js`), visit grouping for the timeline (`timeline.js:groupVisits`, same rule as the backend), and in
  `eclipse.js` the re-folding with a user-typed period (`phaseOf`, same formula as `eclipses.phase`) and the PDM score
  (`pdmTheta`, 20 bins). Everything else is read from the JSON files.

**Assumptions.** Every number on screen comes from a backend file; the browser does not re-measure anything except
the re-fold and the PDM score.

**Inputs and outputs.** Reads `manifest.json`, `gaia.json`, `diff.json`, `lightcurve.json`, `spectrum.json`,
`spots.json`, `proof.json`, `recovery.json`, `eclipse.json`, `catalog.json`, `index.json`; writes nothing.

**Limitations.** The display is 8-bit PNG with one scale for all frames (section 7), so faint changes can be invisible
by eye even when `diff.json` shows them. The sky-map backgrounds are older than SPHEREx (documented in `app.js`).

**Possible error sources.** Mismatch between the browser and backend formulas if one is changed without the other
(phase, visit grouping). Both currently agree.

**Improvements.** Add a shared test that runs the Python and JavaScript phase functions on the same inputs.

**Can it change scientific conclusions?** **No.** The frontend displays results; it does not produce them.

---

## 3. SPHEREx data retrieval

**Current implementation.**
- Service addresses (`config.py`): `TAP_URL = "https://irsa.ipac.caltech.edu/TAP"`, `CUTOUT_URL =
  "https://irsa.ipac.caltech.edu/ibe/cutout"`.
- **Collections:** `config.COLLECTIONS = ("spherex_qr2", "spherex_qr2_deep", "spherex_qr3", "spherex_qr3_deep")`.
  This is the default of `archive.find_images` and is used by `render.py`, `coverage.py`, `proof.py`, `methane.py`,
  `eclipses.images_by_detector` and `scripts/acceptance.py`. Only `research/dr1.py` uses
  `("spherex_dr1", "spherex_dr1_deep", "spherex_qr3", "spherex_qr3_deep")`.
- **Position query** (`archive.find_images`): ADQL on `spherex.obscore`,
  `WHERE CONTAINS(POINT('ICRS', ra, dec), s_region) = 1 AND obs_collection IN (...)`, optionally
  `AND energy_bandpassname = 'SPHEREx-D<n>'` (one query per detector for deep fields, which otherwise time out).
  Columns: `obs_id, obs_publisher_did, obs_collection, energy_bandpassname, t_min, t_max, em_min, em_max,
  obs_release_date`. `maxrec=200_000`. The image time is `SpherexImage.mjd = (t_min + t_max) / 2`.
- **File paths** (`archive.attach_paths`): a second query joining `spherex.plane` and `spherex.artifact`
  (`producttype = 'science'`), 200 DIDs per query (`chunk=200`; eclipse code uses 100). Raises if any path is missing.
- **Cutouts** (`archive.download_cutout`): `GET CUTOUT_URL?ra=&dec=&size=&path=`, `timeout=180` s. Default size
  0.05° in the function signature; callers use `align.cutout_size_deg(fov) = max(0.08, fov/60 × √2 × 1.05)`, i.e.
  **0.08° (4.8′) for the standard 3′ field**. A 404 raises `NotInImage`; other failures are retried.
- **Retries:** `RETRIES = 4`, sleeping `2 ** attempt` s (1, 2, 4, 8 s) for both TAP (`archive._run`) and cutouts;
  TAP read timeout `TAP_TIMEOUT_SECONDS = 300` (`_TimedSession`). `eclipse_build._patiently` and
  `methane._patiently` add 6 tries × 30 s, but only around `attach_paths` / `find_images`, not around downloads.
- **Parallelism:** `MAX_PARALLEL_DOWNLOADS = 3` (IRSA answered 503 at 4+). `research/which_star_pair.py` overrides it
  to 6.
- **Caching:** cutouts in `cache/cutouts/<obs_id>_D<d>_<ra:.5f>_<dec:+.5f>_<size:.4f>.fits`
  (`archive.cutout_file`), written via a `.part` file. The PSF extension named `PSF` is dropped before saving
  (`DROP_PSF_FROM_CUTOUTS = True`). Image lists for eclipse targets are cached forever in
  `cache/eclipse/tic<id>_images.json` (`eclipses.cached_images`, refreshed only with `refresh=True`, which no caller
  passes); research lists in `research/out/images/tic<id>.json`. `/api/coverage` caches answers in memory for 1 hour.
  `archive.trim_cutout_cache` (LRU, `CUTOUT_CACHE_MAX_GB = 10.0`) runs only before live eclipse jobs; the cutout cache
  is currently **24 GB with 8,625 files** (verified on cache).

**Assumptions.** The obscore footprint test is enough to find every image; a cutout request at the same position
and size always returns the same file; the collection list is current.

**Inputs and outputs.** In: RA, Dec, optional detector. Out: `SpherexImage` records and cached FITS cutouts.

**Limitations.**
- QR2 collections return nothing now; the query succeeds with 0 QR2 rows, so the loss is silent. Verified on cache:
  image lists cached at 08:26–17:10 UTC on 12 Nov contain QR2 (e.g. TIC 233208885: 13,968 `qr2_deep` + 877 `qr2` +
  2,552 QR3), while every list cached from 18:57 UTC on contains QR3 only (e.g. TIC 150101476: 911 images, against
  6,938 from DR1 + QR3 via `research/dr1.py`).
- Cached image lists never expire, so a cached QR2-era list will keep requesting QR2 paths that IRSA no longer serves.
- The cache file name has no collection, so two releases of the same exposure share a name (QR2 and DR1 use the same
  `obs_id` naming scheme, e.g. `2025W17_4B_...`; a direct collision was not observed in the cache, but nothing prevents
  it).
- Download failures in `eclipse_build.load_exposures` are counted (`n_failed`) and dropped; in
  `render.visit_exposures` they raise. The two modes behave differently.
- Total retry wait for a cutout is only 15 s, shorter than the "503 busy for a minute" documented on 12 Nov.

**Possible error sources.** Silent release changes; stale cached lists; the obscore `t_min`/`t_max` time scale is not
stated in the code (the selection uses it, the measurement uses the header `MJD-AVG`; any offset is at most ~69 s,
negligible against eclipse widths).

**Improvements.** Change `COLLECTIONS` to the DR1 + QR3 set; fail loudly when a requested collection returns 0 rows
for a position where it used to; put the collection in the cutout cache key and in every output; give cached image
lists a date and refresh rule; wrap downloads in the same patient retry.

**Can it change scientific conclusions?** **Yes.** With QR2 gone the website analyses only QR3 (a fraction of the
data, and none before May 2026); eclipse coverage and error bars change by large factors. Results built on QR2 cannot
be reproduced from the archive today.

---

## 4. FITS processing

**Current implementation.**
- HDUs read: `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI` and the `WCS-WAVE` table (`clean.clean_cutout`,
  `clean.wavelength_at`). Verified on cache: `IMAGE` `BUNIT = MJy / sr`, `ZODI` `MJy / sr`, `VARIANCE` `MJy2 / sr2`;
  QR2 files carried a `PSF` cube (121 × 101 × 101) and DR1/QR3 files carry an `EPSF` extension instead. The `EPSF`
  extension is **not** dropped by `_save_without_psf` (it only drops the name `PSF`); nothing reads either one.
- Time: `float(header["MJD-AVG"])`, the exposure midpoint. Verified on cache: `TIMESYS = 'UTC'`,
  `TELAPSE = 118.19 s`, `XPOSURE = 113.58 s`. `DATE` (processing time) is explicitly not used.
- Celestial WCS: `WCS(hdul["IMAGE"].header)` with `RA---TAN-SIP` / `DEC--TAN-SIP` (`A_ORDER = 3`), `RADESYS = ICRS`.
- Wavelength WCS: `WCS(header, fobj=hdul, key="W")` (`CTYPE1W = CTYPE2W = WAVE-TAB`, a lookup table), with
  `spec.sip = None` (fixed 1 Nov, documented in `notes/PIPELINE_ALIGNMENT.md`: error fell from 2.0 nm median / 8.1 nm
  max to 0.3 / 0.83 nm). The wavelength and bandwidth are evaluated **only at the target's pixel**
  (`sky.world_to_pixel_values(ra, dec)` then `spec.pixel_to_world_values`), rounded to 0.1 nm; on any exception the
  wavelength is `None`.
- Unit conversion to flux: `lightcurve.PIXEL_SR = (6.15 / 206264.806)²`, `MJY_PER_PIXEL_UNIT = PIXEL_SR × 1e9 = 0.889`
  mJy per (MJy/sr) per grid pixel. Documented check against IRSA's solid-angle map: agrees within 0.05% on the 6.15″
  output grid.

**Assumptions.** The header WCS is accurate to well under a pixel; the wavelength at the star equals the value of the
lookup table at the star's detector pixel; output pixels are exactly 6.15″.

**Inputs and outputs.** In: a cutout file. Out: image (MJy/sr, IMAGE − ZODI), sigma, bad mask, WCS, MJD-AVG,
wavelength and bandwidth at the target.

**Limitations.** No use of the PSF/EPSF; wavelength known only at the target, not per pixel, so a field star used as
comparison is assigned the target's wavelength (the true wavelength at a star 1′ away differs, because the filter
changes across the detector). `wavelength_at` swallows every exception and returns `None`, which hides genuine
problems.

**Possible error sources.** Field-star "same wavelength" comparisons (`lightcurve.comparison`,
`eclipse_build.field_null`) use the target's wavelength for every star. The difference across a 3′ field is small for
D1–D4 (R ≈ 35–41) but larger relative to the bandwidth in D5–D6 (R ≈ 110–130).

**Improvements.** Evaluate the wavelength at each measured star's own pixel; log rather than swallow WCS errors; keep
the EPSF or use the official PSF model for photometry.

**Can it change scientific conclusions?** **Maybe.** Using the target's wavelength for comparison stars can add
scatter to field-star null tests, mainly in D5–D6.

---

## 5. Calibration and cleaning

**Current implementation.**
- Background: `image = IMAGE − ZODI` (`clean.clean_cutout`). No other background model; light-curve photometry later
  subtracts a local median sky (section 10), difference images subtract one global median (section 8).
- Noise: `sigma = sqrt(VARIANCE)` where `VARIANCE > 0`, else NaN.
- Bad pixels: `config.BAD_FLAG_NAMES` (19 names): `TRANSIENT, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD,
  PHANMISS, NONLINEAR, PERSIST, CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO`.
  `SOURCE` is deliberately not bad. Bit positions are read from each file's FLAGS header (`flags.flag_bits`: `MP_<NAME>`
  in QR2, `MSKN<nnnn>`/`MSKM<nnnn>` in QR3/DR1); names a release does not define are **silently skipped**
  (`flags.bad_pixel_bitmask`).
- Verified on cache, flags actually defined:

  | Release | Style | Bad names from the list that are missing |
  |---|---|---|
  | `spherex_qr2`, `spherex_qr2_deep` | `MP_*` | CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO (9 of 19) |
  | `spherex_dr1`, `spherex_dr1_deep`, `spherex_qr3`, `spherex_qr3_deep` | `MSKN*` | SATELLITE_HALO only |

  Information bits not treated as bad: `OUTLIER`, `FULLSAMPLE`, `OVERFLOW`, `PHANTOM` (QR2), `REFERENCE` (QR2), `SOURCE`.
- NaN pixels (e.g. saturated cores) stay NaN and are treated as "no value".

**Assumptions.** IRSA's ZODI model is the right background; VARIANCE is the full per-pixel noise; the 19 names are the
complete list of defects; a pixel without a bad flag is trustworthy.

**Inputs and outputs.** In: cutout HDUs. Out: cleaned image, sigma, boolean bad mask.

**Limitations.** Flag coverage depends on the release, so a QR2 frame and a QR3 frame of the same star are cleaned
by different rules; the eclipse builds on the website are about 89% QR2 points (TIC 219900027: 599 of 674; TIC 233208885:
606 of 680). Flagged values are not set to NaN before reprojection (see section 6). `OVERFLOW` is not in the bad list
(saturated pixels are usually NaN already, but this was not verified).

**Possible error sources.** Unflagged ghosts, streaks and crosstalk in QR2 data; persistence from earlier bright
exposures that is not flagged; documented: a single unflagged cosmic ray in the eclipse data (`ECLIPSE_FINDINGS.md`
section 4); documented: RW Aur intra-visit 10–20% spread with 16 of 24 exposures flagged in the circle (Day 4).

**Improvements.** Set flagged pixels to NaN before resampling; record which flag names were applied per exposure;
re-run with DR1 files, which define 18 of the 19 names; consider `OVERFLOW` as bad.

**Can it change scientific conclusions?** **Yes** for individual spots and outlier exposures (an unflagged artefact
can look like a moving or variable source); **maybe** for averaged eclipse depths, where outlier clipping and jitter
dilute single artefacts.

---

## 6. Reprojection and alignment

**Current implementation.**
- Grid (`align.target_grid`): north-up, east-left TAN projection centred on the target, `cdelt = ±6.15″`
  (`PIXEL_SCALE_ARCSEC = 6.15`), size `round(fov × 60 / 6.15) | 1` (odd), **29 × 29 pixels for 3′**, target at the
  central pixel centre.
- Resampling (`align.align`): `reproject_interp` (reproject 0.21.0, default `order="bilinear"`) for the image and for
  `sigma²`; `order="nearest-neighbor"` for the bad mask and for an array of ones that marks "inside the exposure".
  `covered = footprint > 0 & isfinite(image)`; `bad = covered & (resampled bad > 0.5)`.
- No registration step: alignment relies entirely on each file's WCS. No cross-correlation, no Gaia-based
  astrometric refinement, no sub-pixel shift fitting.
- Frames must have at least `MIN_COVERED_PCT = 90.0`% of the grid inside the exposure (`render.py`).
- Documented checks: `reproject_exact` vs `reproject_interp` gave mixed, insignificant differences in light-curve
  scatter (`PIPELINE_ALIGNMENT.md` 3b); RW Aur (not moving) shifts 0.04–0.07 px between visits measured by centroid
  (`frame_notes.py`); `proof.MIN_TESTABLE_PX = 0.3` cites "0.11 px alignment".

**Assumptions.** The archive WCS is accurate to about 0.1 px; bilinear interpolation of an undersampled image (PSF
FWHM ≈ 5″ in D2, smaller than one 6.15″ pixel; verified on cache) is acceptable; resampling `sigma²` bilinearly gives
the right noise.

**Inputs and outputs.** In: cleaned cutout and grid. Out: image, sigma, bad, covered, inside on the grid, plus
`pct_flagged`, `pct_no_value`, `pct_covered`.

**Limitations.**
- **Flagged-value leakage:** the image is interpolated with its flagged pixels still holding their (finite) values,
  while the mask is nearest-neighbour. A grid pixel whose nearest source pixel is good can still take up to about
  half of its value from a flagged neighbour.
- **Noise:** bilinear interpolation of `sigma²` gives Σwᵢσᵢ², while the variance of an interpolated value is Σwᵢ²σᵢ²
  (up to 4× smaller at the midpoint between four pixels). So per-pixel sigma is overestimated, while the covariance
  between neighbouring grid pixels is ignored (which underestimates the error of any sum of pixels). Documented
  symptom: difference-map scatter of 0.7–0.8 (Day 3).
- **Undersampling:** with a PSF narrower than a pixel, bilinear resampling changes the peak and shape of a star
  depending on where it falls inside a pixel (pixel phase), adding exposure-to-exposure scatter in small apertures.

**Possible error sources.** Residual WCS errors; SIP distortion near cutout edges; pixel phase; leaked flagged
values.

**Improvements.** NaN the flagged pixels before resampling (and treat the NaN footprint as "no value"); propagate
noise properly (e.g. resample with weights and keep a covariance estimate, or do photometry on detector pixels as
IRSA's tools do, with the solid-angle map); measure the residual registration per exposure against Gaia stars and
report it.

**Can it change scientific conclusions?** **Yes** for single-pixel spots and small-aperture photometry of faint
sources; **maybe** for eclipse depths (jitter absorbs much of it, but depth errors are then empirical, not modelled).

---

## 7. Flipbook ordering

**Current implementation.**
- Visits (`archive.group_epochs`): images sorted by `mjd`; a new visit starts after a gap > `EPOCH_GAP_DAYS = 30.0` or
  when the visit would exceed `EPOCH_MAX_SPAN_DAYS = 60.0` (needed near the ecliptic poles, where coverage is almost
  continuous).
- Per visit (`render.visit_exposures`): exposures sorted by distance from the visit's mean time; up to
  `max_per_visit` (default 8; live jobs 4; some prepared D6 folders were made with up to 21) that cover ≥ 90% of the
  grid. Mode `coadd` (default) adds them with 1/σ² weights (`coadd.coadd`); mode `single` keeps the closest one.
- Frame time = mean `MJD-AVG` of the exposures used; frames are written in visit order and the browser refuses
  non-increasing times (`frames.js:checkManifest`).
- Display (`render.brightness_scale`): one scale for all frames, linear from the 1st to the 99.5th percentile of good
  pixels (`SCALE_PERCENTILES = (1.0, 99.5)`), or asinh with `ASINH_SOFTENING = 0.002` (used for R Dra). 8-bit PNG,
  flipped so north is up.
- Blink default pair: first and last frame (`player.js:defaultBlinkPair`).
- Eclipse Mode flipbook (`eclipse_build.write_frames`): per detector, every exposure in **orbital-phase** order, one
  scale per detector, plus `_n.png` multiplied by `S(λ_ref)/S(λ)` so colour is not mistaken for dimming.

**Assumptions.** Exposures in one visit are close enough in time and similar enough to add; one brightness scale is
fair to all frames.

**Inputs and outputs.** In: image list and cutouts. Out: `epoch<i>.png`, `epoch<i>_flags.png`, `epoch<i>.fits`,
`manifest.json` with per-frame wavelength mean and range at the target.

**Limitations.** A co-add mixes exposures at different wavelengths (the manifest records `wl_target_range_um`), so a
star can look brighter or fainter between frames because of its spectrum (documented: Eps Ind B's factor of 2, Day 4).
Frames have different depths (e.g. 3, 8, 8 exposures). Exposures within a visit can span days to weeks, which blurs
fast movers.

**Possible error sources.** Colour changes shown as brightness changes; unequal noise between frames; 8-bit
quantisation.

**Improvements.** Offer a "same-wavelength" flipbook (exposures chosen by wavelength window, as `methane.py` does);
show each frame's noise level; equalise the number of exposures per frame.

**Can it change scientific conclusions?** **Maybe.** Visual impressions from the flipbook can mislead (colour vs
variability), but measured quantities use per-exposure data.

---

## 8. Difference imaging

**Current implementation.** `diff.difference`:
`z = (B − A − sky_change) / sqrt(σ_A² + σ_B²)`, where `sky_change = median(B − A)` over pixels usable in both, and σ
comes from the frames' SIGMA (resampled VARIANCE). No z where either frame is flagged or has no value. Scatter
reported as 1.4826 × MAD of z. Display limit `LIMIT_SIGMA = 5.0`. Every pair of visits is computed
(`itertools.combinations`); the default pair is the one with the closest mean wavelength at the target
(`diff.default_pair`). Spot detection (`spots.groups`): 8-connected groups with |z| ≥ 5; `MAX_SPOTS = 10`,
`NEAR_GAIA_PX = 1.5`, `LONG_THIN_RATIO = 3.0`, `LONG_THIN_MIN_PX = 4`, `LARGE_PX = 20`, `SCATTER_WARN = 1.5`.
Planted-source recovery test (`recovery.py`): `LEVELS = (0, 3, 4, 5, 6, 8, 12, 20)`, 200 per level, `STEP_PX = 4.0`,
`FOUND_PX = 1.5`, seed 20261107. In Eclipse Mode (`eclipse_build.write_diff`) the in-eclipse and out-of-eclipse
co-adds are matched one-to-one in wavelength (within half a bandwidth) before differencing.

**Assumptions.** Both frames have the same PSF and the same flux scale; only an additive offset differs; VARIANCE
describes the noise.

**Inputs and outputs.** In: `epoch<i>.fits`. Out: `diff.json` (z maps, pair statistics), `diff_<a>_<b>.png`,
`spots.json`, `recovery.json`.

**Limitations.** **No PSF matching** (PSF FWHM varies by detector, position and exposure); **no multiplicative
normalisation** (colour or calibration differences between co-adds at different wavelengths leave residuals on every
star); co-adds of different depths; the noise model is approximate (section 6), so z is not a calibrated significance
(documented: scatter 0.7–0.8 on most pairs, 7.9 on Barnard, 11–29 on R Dra). The planted test adds sources after
co-adding and without photon noise (documented as slightly optimistic in `recovery.py`).

**Possible error sources.** Bright-star residuals, wavelength mismatch, unflagged artefacts, leaked flagged values.

**Improvements.** PSF-matched differencing (e.g. Alard–Lupton or ZOGY style), a fitted flux scale per pair,
wavelength-matched pairs for the flipbook as already done in Eclipse Mode, and z rescaled by the measured scatter.

**Can it change scientific conclusions?** **Yes** for any claim based on a single spot (a 5σ spot may not be 5σ);
the code and notes already avoid calling spots new objects.

---

## 9. Gaia cross-match

**Current implementation.** `gaia.gaia_stars`: ADQL on IRSA `gaia_dr3_source` (`GAIA_TABLE`), cone search, columns
`source_id, ra, dec, pmra, pmdec, parallax, phot_g_mean_mag, ref_epoch`; raises if any `ref_epoch` ≠ 2016.0
(`GAIA_EPOCH`). Radius (`search_radius_deg`) = half the frame diagonal + `MAX_MOTION_ARCSEC_PER_YEAR (11.0) ×
|years since 2016|` + `MARGIN_PX (1.0) × 6.15″`. Epoch propagation (`gaia.star_at` → `motion.position_at`): straight
line in RA and Dec, `ra += pmra × Δt / cos(dec)`, `dec += pmdec × Δt`, with Δt from `coords.mjd_to_year` (Julian year
of the UTC MJD); **parallax is not applied**; stars without proper motion stay at 2016.0. Target match: the Gaia star
nearest the grid centre at year 2026.0 within `TARGET_MATCH_ARCSEC = 3.0`. Used for markers, motion proof
(`proof.py`), field stars (`lightcurve.field_stars`: `FIELD_MAX_G = 17.0`, `FIELD_ISOLATION_PX = 4.0`), neighbour
warnings (`NEIGHBOUR_G_LIMIT = 3.0` mag) and Eclipse Mode comparison stars (`MAX_FIELD_STARS = 8`).

**Assumptions.** Linear motion is accurate to well under a pixel over 10 years (it is, except within about 1e-6 of
the poles, where `position_at` raises); parallax is negligible (documented: 0.55″ = 0.09 px for Barnard's Star).

**Inputs and outputs.** In: frame centre, field size, frame MJDs. Out: `gaia.json` with per-frame pixel positions.

**Limitations.** No parallax (only matters for the nearest stars, below 0.1 px here); the target match uses one
epoch (2026.0) and fails for objects absent from Gaia (WISE 0855, documented); TESS targets are matched separately
(`eclipses.find`, `MATCH_ARCSEC = 10.0`) using TIC J2000 positions (`TIC_EPOCH = 2000.0`), which come from Gaia DR2.
Gaia is incomplete for very bright stars and very red or faint objects; such neighbours are invisible to the
blend checks.

**Possible error sources.** A wrong target match in crowded fields (3″ is half a pixel); missing neighbours brighter
in the infrared than in G.

**Improvements.** Add parallax for nearby stars; add 2MASS/AllWISE neighbours for red objects; match each frame at its
own epoch.

**Can it change scientific conclusions?** **Maybe.** Missing infrared-bright neighbours can contaminate apertures
without a warning; this matters for blend identifications.

---

## 10. Photometry

**Current implementation.** `lightcurve.measure`:
- Aperture: fractional pixel weights from 5 × 5 supersampling (`SUPERSAMPLE = 5`); core circle radius
  `CORE_RADIUS_PX = 2.0` (12.3″). For saturated cores, a "wings" ring of width `WING_WIDTH_PX = 3.0` starting just
  outside the no-value hole, allowed only if it starts at ≤ `MAX_WING_INNER_PX = 3.0` (tested on RW Aur: follows the
  core within about 10%).
- Sky: median of pixels fully inside the annulus `SKY_ANNULUS_PX = (10.0, 14.0)` for targets, `FIELD_SKY_ANNULUS_PX =
  (5.0, 8.0)` for field stars and for the two-star research tests; at least 10 sky pixels required; flagged pixels and
  no-value pixels excluded from the sky.
- Flux = Σ w × (image − sky) × 0.889 mJy (no aperture correction). Error² = Σ (w σ)² + (Σw × sky_err)², with
  `sky_err = 1.4826 × MAD × sqrt(π / 2 / N)` (standard error of a median). Pixels treated as independent.
- Flagged pixels inside the aperture are **counted** (`n_flagged`) but their values are **included** in the flux; any
  no-value pixel inside the aperture makes the point "no value".
- Target track (`lightcurve.target_track`): straight-line fit through Gaia's per-frame positions, else SIMBAD proper
  motion, else the grid centre. In Eclipse Mode the binary is measured at the fixed grid centre (TIC position moved to
  the median year).
- Comparison rule (`lightcurve.wavelength_pairs`): two exposures of different visits are compared only if
  `|Δλ| < SAME_WAVELENGTH (0.5) × mean bandwidth` and both are ≥ `MIN_SNR = 5.0` σ.
- Eclipse Mode (`eclipse_build.analyse`): points used only if not flagged, finite, and `flux > 5 × err`
  (`MIN_SNR = 5.0`). `aperture_for` switches to wings if more than `SATURATED_FRACTION = 0.5` of exposures have a hole
  in the core.
- Research two-star photometry (`research/which_star_pair.py`): circular Gaussian PSF with free width
  (`0.4–3.0` px) and a common shift (±1 px) fitted on the out-of-eclipse co-add per detector (`psf_shape`), then per
  exposure linear amplitudes for both stars plus a constant sky (`psf_photometry`), pixels within `FIT_RADIUS_PX = 4.0`
  of either star, minus pixels within `MASK_RADIUS_PX = 2.5` of other Gaia stars up to 1.5 mag fainter than the fainter
  of the pair; errors scaled by sqrt(reduced χ²) when above 1; points kept if `f > 3 × e`.

**Assumptions.** The fraction of light inside 2 px is the same in every exposure of a detector; the sky annulus is
free of stars; pixel noise is independent; a Gaussian describes the PSF well enough for deblending.

**Inputs and outputs.** In: aligned images, sigma, masks, positions. Out: fluxes in mJy with errors, per exposure.

**Limitations.**
- No aperture correction; the PSF FWHM varies (verified on cache: 5.15″ in a D2 header, 8.63″ in a D5 header), so the
  enclosed fraction differs between detectors and, through field position, between exposures.
- The PSF/EPSF from the files is never used; the research deblending uses a symmetric Gaussian on resampled (smoothed)
  co-adds, which does not match SPHEREx's undersampled, asymmetric PSF.
- A 10–14 px sky annulus is 61″–86″ from the star; in crowded fields it contains stars (median helps, but is biased
  upward).
- The S/N selection (`> 5σ` in Eclipse Mode, `> 3σ` in research) removes faint in-eclipse points preferentially,
  which biases depths of faint or deep eclipses low.
- Fixed-position measurement in Eclipse Mode ignores proper motion within the observing span (small for these stars).

**Possible error sources.** Blended neighbours inside 12.3″ (warned by `neighbours`), aperture losses varying with
PSF, sky contamination, pixel phase, leaked flagged values, correlated noise.

**Improvements.** Use the official PSF (keep EPSF) for forced PSF photometry (IRSA's Tractor-based tool is an
option); per-detector aperture corrections from field stars; sky from sigma-clipped annuli with stars masked; avoid
S/N cuts that depend on the measured flux (cut on the expected flux instead).

**Can it change scientific conclusions?** **Yes.** Depth values, depth ratios between stars in a blend, and the
"neighbour shows no dip" tests all depend on how light is apportioned between nearby stars.

---

## 11. TESS catalogue integration

**Current implementation.** `eclipses.py`:
- Source: `TESS_EB_URL = https://archive.stsci.edu/hlsps/tess-ebs/hlsp_tess-ebs_tess_lcf-ffi_s0001-s0026_tess_v1.0_cat.csv`
  (Prša et al. 2022, TESS-EBs v1.0, sectors 1–26), cached once at `cache/catalogs/tess_ebs_v1.0.csv` (no version or
  date check). 4,584 rows; only `signal_id == "1"` is kept (4,578 rows), giving 4,413 usable ephemerides.
- Columns used: `tess_id, signal_id, ra, dec, pmra, pmdec, Tmag, bjd0, bjd0_uncert, period, period_uncert,
  morph_coeff, prim_{pos,width,depth}_{pf,2g}, sec_{pos,width,depth}_{pf,2g}`. Not used: `date_added, date_modified,
  source, sectors`.
- Model choice (`_eclipse_numbers`): polyfit (`pf`) numbers if they include a primary eclipse, else two-Gaussian (`2g`)
  numbers with widths **halved** (`width_factor = 0.5`, an empirical rule from one comparison, 0.141 vs 0.071).
  4,065 entries use `pf`, 348 use `2g`.
- Missing values: `pmra`, `pmdec`, `bjd0_uncert`, `period_uncert` → `0.0` (`nums[...] or 0.0`).
- Lookup: `near()` (by distance), `find()` (within 10″), `by_tess_id()`. `catalog.json` lists binaries within
  `SHOWCASE_RADIUS_DEG = 10.0` of the north ecliptic pole `NEP = (270.0, 66.560708)`.

**Assumptions.** The catalogue's ephemeris belongs to the star it is listed under; `bjd0` is in BTJD (verified: values
1322–2139); TIC positions are J2000; one signal per star is enough.

**Inputs and outputs.** In: CSV. Out: `Ephemeris` objects.

**Limitations.** Verified on the cached CSV: 21 rows with missing or zero `bjd0_uncert` and 7 with missing or zero
`period_uncert` become a phase error of 0 (a "perfect clock"); 148 rows with missing or zero `pmra` get no proper
motion; 38 rows have `prim_depth_pf > 1` (physically impossible; documented case TIC 233058265 at 1.30) and are
accepted, because the code only checks `depth > 0`. Duplicated signals (the blend problem the research addresses)
are not flagged. The halving of 2g widths is a heuristic, not a documented catalogue convention.

**Possible error sources.** Wrong-star entries, unreliable widths and depths for contaminated entries, stale
ephemerides (sectors 1–26 only, 2018–2020).

**Improvements.** Reject or flag depths > 1 and missing uncertainties; use later TESS sectors or newer ephemerides
where available; record the catalogue file's date and checksum in outputs.

**Can it change scientific conclusions?** **Yes.** The eclipse windows and the clock quality both come straight from
this catalogue; a wrong width or a zero uncertainty changes which exposures count as "in eclipse".

---

## 12. Orbital phase and time systems

**Current implementation.** `eclipses.to_btjd(mjd_utc, ra, dec)`:
1. `Time(mjd, format="mjd", scale="utc").tdb` (UTC → TT → TDB, leap seconds included).
2. Earth's barycentric position from `get_body_barycentric("earth", tdb)` (astropy built-in ephemeris).
3. Rømer delay = (unit vector to the star · Earth position) / c, added in days.
4. `BTJD = tdb.jd + ltt − 2457000.0` (`BTJD_OFFSET`).

So SPHEREx `MJD-AVG` (UTC, verified `TIMESYS = 'UTC'`) **is converted to barycentric BTJD in TDB**, as required to
match TESS. The star direction uses the TIC position moved to the median year of the images. Observer = geocentre
(SPHEREx in low Earth orbit; ≤ ~23 ms error, documented in the module docstring). Shapiro and Einstein delays beyond
UTC→TDB are ignored (sub-millisecond).

Phase (`eclipses.phase`): `φ = ((BTJD − bjd0) / P − prim_pos + 0.5) mod 1 − 0.5`, primary at 0. Secondary at
`(sec_pos − prim_pos)` wrapped (`secondary_phase`). `prim_pos` is about 1.0 for most entries (median 1.000; range
−0.07 to 1.175), so subtracting it shifts the phase by a fraction of a percent. Phase error
(`Ephemeris.phase_error`): `(N σ_P + σ_T0) / P`, N = cycles since `bjd0` (a linear, worst-case sum, not a quadrature
sum). The browser uses the same formula (`eclipse.js:phaseOf`).

Selection and forecasting (`forecast`, `select_for_download`) use the archive's `(t_min + t_max) / 2`; the final
analysis uses each file's `MJD-AVG`.

**Assumptions.** The obscore times are close enough to `MJD-AVG` for choosing exposures; the exposure (118 s elapsed)
is short compared with the eclipse (phase smearing ≤ 0.005 even for the 0.279-day binary TIC 280033934).

**Inputs and outputs.** In: MJD (UTC), position, ephemeris. Out: BTJD and phase per exposure.

**Limitations.** No check that the obscore time scale is UTC; the time conversion is correct but the ephemeris
extrapolation (section 13) dominates the error budget by orders of magnitude.

**Possible error sources.** Ephemeris drift; wrong `prim_pos` for 2g entries; for `research/plot_phase.py`, see
section 18 item 9.

**Improvements.** Add a unit test comparing `to_btjd` with astropy's `Time.light_travel_time` for a known site; report
phase error in units of the eclipse width.

**Can it change scientific conclusions?** **No** for the time conversion itself (verified correct to well under a
second); the ephemeris drift is covered in section 13.

---

## 13. Eclipse selection and download budget

**Current implementation.**
- Eclipse membership (`eclipses.eclipse_part`): primary if `|φ| < central × prim_width / 2`, secondary likewise around
  the secondary phase; "middle of the eclipse" uses `central = CENTRAL = 0.5`. "Clearly outside"
  (`out_of_eclipse`) uses eclipses widened by `margin = 1.25`.
- Budget per detector (`eclipses.BUDGET = {"primary": 40, "secondary": 25, "outside": 50}`, up to 115 per detector,
  690 total). Live API jobs use `{"primary": 20, "secondary": 10, "outside": 25}` and need at least
  `ECLIPSE_MIN_IN_PRIMARY = 12` exposures in primary. `research/run_pairs.py` tests a pair only if `MIN_PRIMARY = 8`.
- Spreading (`_spread`): each group is sorted by phase (then time) and sampled evenly with `np.linspace`, so ingress,
  middle and egress are covered. Wavelengths cannot be chosen before download.
- Clock check: `forecast()` reports `phase_error` at the last exposure with the rule text "usable below 0.01", but
  **`MAX_PHASE_ERROR` is never compared with anything**. `catalog.json` reports the phase error at BTJD 4000.
- Research: `which_star_pair.clock()` picks, of the two TESS-EBs entries of a pair, the one with the smaller phase
  error at the median BTJD of the first 50 images in the list (detector 1, earliest first); `run_pairs.py` picks the
  clock with the phase error at BTJD 4000. These can differ.

**Assumptions.** The TESS widths are right; the clock has not drifted by more than a fraction of the eclipse width;
an even spread in phase is the best use of a fixed budget.

**Inputs and outputs.** In: image list, ephemeris. Out: chosen images (sorted by time).

**Limitations.** Verified on the catalogue: the phase error at BTJD 4000 exceeds half the primary width for 36% of
entries and a quarter of the width (the "middle half" window) for 50%. For TIC 233058262, width 0.0071 and phase
error 0.0061. Only a small fraction of the available exposures is used (e.g. TIC 150101476: 599 of 6,938;
TIC 233058262: 465 of 20,509). The two "eclipse" windows are fixed by TESS widths even though SPHEREx sees other
wavelengths (limb darkening changes the eclipse shape, not its duration, so this is mostly fine).

**Possible error sources.** Clock drift moving exposures out of the true eclipse (biases depths toward 0, and could
make the real binary look like the "non-eclipsing" neighbour); budget sampling noise.

**Improvements.** Enforce a rule such as `phase_error < 0.25 × prim_width` before claiming a non-detection; fit the
eclipse time from SPHEREx itself (`eclipse_depth.eclipse_timing` already does this) and re-fold before measuring
depths; increase the budget for the weak pairs (documented as a next step).

**Can it change scientific conclusions?** **Yes.** A null result ("this star shows no eclipse") is only meaningful if
the exposures really fall inside the eclipse; the current code does not guarantee that.

---

## 14. Multi-band measurement (S(λ) normalisation, per detector)

**Current implementation.** `eclipse_depth.py` and `eclipse_build.normalise`:
- Resolving power per detector: `RESOLVING_POWER = {1: 41, 2: 41, 3: 41, 4: 35, 5: 110, 6: 130}`.
- S(λ) (`fit_steady`): weighted cubic B-spline (`make_lsq_spline`, weights 1/err) of flux against ln λ, per detector,
  fitted to out-of-eclipse exposures with quarter-phase exposures held out. Interior knots:
  `min((ln λ range) / (KNOT_SPACING (2.0) / R), N / MIN_POINTS_PER_KNOT (6) − 4)`, reduced until the fit works; falls
  back to a quadratic polynomial. Needs ≥ 8 points. Clipping at `CLIP_SIGMA = 4.0` × robust scale, up to 3 rounds.
  Outside the fitted wavelength range S is **held at its edge value** (`np.clip(x, *log(wl_range))`).
- g = flux / S(λ); jitter (`jitter`) found by bisection so that `(g − 1) / sqrt(err² + s²)` has robust std 1.
- Baseline B(φ) = c0 + a1 cos 2πφ + a2 cos 4πφ, fitted to out-of-eclipse g, used only if a term exceeds
  `BASELINE_SIGNIFICANCE = 3.0` σ.
- Depth in a wavelength bin = 1 − weighted mean of g/B over the middle half of the eclipse, at least
  `MIN_POINTS_PER_BIN = 3` points, `BINS_PER_DETECTOR = 2` bins equal in ln λ over the measured range; error × sqrt(χ²ᵣ)
  when above 1.
- Multi-detector spectrum for the flipbook targets (`spectrum.py`): light-curve points from each detector folder,
  grouped by visit; explicit warnings that there is no aperture correction and no overlap between detectors.
- Methane vision (`methane.py`): D4 window 3.15–3.50 µm vs D5 3.90–4.20 µm, each exposure scaled by
  `(λ / 4.0 µm)^2` (Rayleigh–Jeans), `k` from field calibrators (`MIN_CALIBRATORS = 3`, else k = 1),
  `SYSTEMATIC = 0.05`, `GLOW_SIGMA = 5.0`, `METHANE_EXCESS = 2.0`, `MAX_IMAGES_PER_BAND = 150`.

**Assumptions.** The star's spectrum is smooth on the scale of 2 resolution elements; the PSF/aperture fraction
varies smoothly with wavelength (absorbed into S); the out-of-eclipse sample covers the same wavelengths as the
in-eclipse sample.

**Inputs and outputs.** In: per-exposure flux, error, wavelength, detector, phase. Out: g, depth spectra
(primary, secondary, null), secondary/primary ratio, per-detector jitter.

**Limitations.** With about 27–36 out-of-eclipse points per detector (verified on the two website builds), the knot
rule allows at most `36/6 − 4 = 2` interior knots, usually 0–1: S(λ) is close to a single cubic across a detector and
cannot follow narrower spectral structure. Constant extrapolation beyond the fitted range biases g for in-eclipse
exposures at the detector edges. Only 2 bins per detector. The jitter assumes g is centred on 1, so a mis-fit S
inflates the jitter rather than being flagged. Measured jitter on the website builds: 1.9–5.7% per detector.

**Possible error sources.** Spectral features in eclipsing stars (e.g. molecular bands in M dwarfs) not followed by S;
wavelength-dependent aperture losses; different wavelength coverage in and out of eclipse.

**Improvements.** Fit S(λ) jointly with the eclipse model on all points; use a stellar template as a prior shape;
refuse in-eclipse exposures outside the out-of-eclipse wavelength range; report the residual of S around the
in-eclipse wavelengths.

**Can it change scientific conclusions?** **Maybe.** The quarter-phase null test checks the method (TIC 219900027:
1.3 ± 0.7%, χ² 14.0 for 11 bins; TIC 233208885: 0.4 ± 0.5%, χ² 29.6 for 9 bins); the second has a χ² well above the
number of bins, so per-bin depth spectra (temperature-ratio claims) are less secure than their errors say.

---

## 15. Statistics (jitter, errors, checks)

**Current implementation.**
- Robust scatter everywhere: 1.4826 × MAD (`diff.robust_scatter`, `eclipse_depth.robust_std`,
  `lightcurve.log_scatter_pct`).
- Error inflation: per-detector jitter (`eclipse_depth.jitter`), bin errors × sqrt(χ²ᵣ) (`weighted_depth`), baseline
  covariance × max(1, sqrt(χ²ᵣ)) (`fit_baseline`), two-star fits × sqrt(χ²ᵣ) (`which_star_pair`).
- Built-in null tests: quarter-phase depth (`NULL_PHASE = 0.25`), field-star depth folded on the binary's clock
  (`field_null`), field-star same-wavelength floor for light curves (`lightcurve.comparison`), planted-mover recovery
  (`recovery.py`), wings-vs-core check (`check_wings`).
- Timing: trapezoid fit (`eclipse_timing`, flat-bottom fractions `(0.0, 0.2, 0.4, 0.6)`, 801 trial shifts over ±half
  width), error from Δχ² = 1 after scaling to χ²ᵣ = 1.
- Period search: PDM (Stellingwerf 1978) with 20 bins, trial frequencies spaced for 10× oversampling, 0.2–20 days.
- Research blind scan (`plot_phase.scan`): window ±0.012 in phase, step 0.005, leaves out the single lowest point.

**Assumptions.** Errors are Gaussian after inflation; jitter is the same for every exposure of a detector; exposures
are independent.

**Limitations.** Verified on the website builds: timing fits have χ²ᵣ of 14.8 (TIC 219900027) and 4.0
(TIC 233208885), so the trapezoid model does not describe the data well and Δχ² errors are only indicative. PDM did
not recover the TESS period for TIC 219900027 (best 0.345 d; TESS 0.515 d) and found half the period for TIC 233208885.
Documented: the TIC 233058262 fold has χ²ᵣ ≈ 10 (`ECLIPSE_FINDINGS.md`). The blind scan's "σ" is a maximum over about
200 phase windows, so its significance is overstated by the look-elsewhere effect (a 2.9σ maximum is not a 2.9σ
detection). No correction for multiple testing across 11 pairs × 2 stars × several methods.

**Possible error sources.** Correlated errors between exposures of the same visit (same pointing, same sky,
persistence); jitter absorbing real variability; look-elsewhere effect.

**Improvements.** Bootstrap or permutation tests for the blind scan (shuffle phases); errors from the scatter of
visit-level averages; report false-alarm probabilities; correct for the number of pairs tested.

**Can it change scientific conclusions?** **Yes** for the weak identifications (documented 2.9–4.3σ blind-scan values
for TIC 420114772, 258918831, 269696430, 150101476), whose real significance is lower once the scan's many trials are
counted.

---

## 16. Existing research targets

Flipbook targets (`backend/app/targets.py:OFFICIAL_TARGETS`, positions from SIMBAD moved to 2026.0 by
`render.target_position`; values from the manifests):

| Folder | Object | RA, Dec (deg) | Detectors prepared | Frames (exposures per frame) | Light curve |
|---|---|---|---|---|---|
| `barnard` | Barnard's Star | 269.446269, +4.768204 | D2 | 3 (8, 8, 8), Aug 2025 – Aug 2026 | none (saturated core) |
| `eps_ind_b` | Epsilon Indi B | 331.096644, −56.800660 | D1–D6 | 3–5 per detector | core (D1–D5), none (D6) |
| `r_dra` | R Draconis | 248.167233, +66.755024 | D2 (asinh scale) | 3 (8, 8, 8) | none (saturated core) |
| `rw_aur` | RW Aurigae | 76.956587, +30.401291 | D1–D6 | 3 per detector | core (D1–D3, D5–D6), none (D4) |
| `wise0855` | WISE 0855−0714 | 133.759765, −7.242186 | D1–D6 | 3–4 (D6: 3, 19, 21) | core |

Each target folder also has `coverage.json`, `spectrum.json` and a `methane/` folder (uncommitted).

Eclipse Mode builds (`frontend/frames/eclipse/`, made 12 Nov 2026 with the QR2-era collections):

| Folder | Position (deg) | P (d) | Exposures (used) | Release mix | Primary depth (combined) | TESS depth vs SPHEREx D1 | Timing shift |
|---|---|---|---|---|---|---|---|
| `tic219900027` | 263.838544, +68.638726 | 0.51526 | 674 (557) | 550 `qr2_deep`, 49 `qr2`, 72 `qr3_deep`, 3 `qr3` | 0.171 ± 0.006 | 0.245 vs 0.196 ± 0.014 | −11.1 ± 3.0 min (clock ±5.3) |
| `tic233208885` | 266.351645, +69.306286 | 0.49374 | 680 (570) | 562 `qr2_deep`, 44 `qr2`, 73 `qr3_deep`, 1 `qr3` | 0.399 ± 0.007 | 0.477 vs 0.409 ± 0.022 | −4.0 ± 0.4 min (clock ±1.7) |

`catalog.json`: 112 TESS-EBs binaries within 10° of the north ecliptic pole, 2 built, 4 with cached forecasts.
`index.json`: the two built binaries.

Not on the website (documented in `notes/ECLIPSE_FINDINGS.md`, outputs in git-ignored `scratch/`): TIC 233058262 and
TIC 233233639 builds.

---

## 17. Previously tested coordinates

**Flipbook and API.** The five targets above; a typed test position RA 133.8000°, Dec −7.2000° (D2) run as a live job
(documented, Day 3).

**TESS-EB pair folders in `research/out/pair_*`** (TIC A / TIC B, catalogue J2000 positions of A, separation, clock
entry used, exposures used / in the image list, data):

| Folder | TIC A (RA, Dec) | TIC B | Sep (″) | Clock | Exposures | Data |
|---|---|---|---|---|---|---|
| `pair_124712820_124712813` | 124712820 (104.7646, −11.7275) | 124712813 | 12.9 | 124712813 | 270 / 323 | DR1+QR3 |
| `pair_140659978_140659980` | 140659978 (72.4533, −72.4632) | 140659980 | 20.8 | 140659978 | 320 / 635 | DR1+QR3 |
| `pair_150101476_150101472` | 150101476 (92.0942, −63.2614) | 150101472 | 32.2 | 150101472 | 599 / 6,938 | DR1+QR3 |
| `pair_150101476_150101472_qr3only` | same | same | 32.2 | 150101472 | 257 / 911 | QR3 only |
| `pair_16805617_16805614` | 16805617 (141.8682, +39.5050) | 16805614 | 56.1 | 16805617 | 244 / 246 | DR1+QR3 |
| `pair_198242676_198242678` | 198242676 (249.7670, +60.7019) | 198242678 | 8.3 | 198242678 | 389 / 493 | DR1+QR3 |
| `pair_198242676_198242678_qr3only` | same | same | 8.3 | 198242678 | 152 / 166 | QR3 only |
| `pair_233058262_233058265` | 233058262 (269.4962, +64.0686) | 233058265 | 29.8 | 233058262 | 465 / 20,509 | QR2+QR3 |
| `pair_243391171_243391162` | 243391171 (205.0603, −45.7099) | 243391162 | 23.7 | 243391171 | 330 / 360 | DR1+QR3 |
| `pair_258918831_258918835` | 258918831 (288.6383, +69.4431) | 258918835 | 40.8 | 258918831 | 363 / 3,824 | DR1+QR3 |
| `pair_258918831_258918835_qr3only` | same | same | 40.8 | 258918831 | 271 / 755 | QR3 only |
| `pair_269696430_269696438` | 269696430 (301.6201, +68.2782) | 269696438 | 49.0 | 269696438 | 309 / 460 | DR1+QR3 |
| `pair_276935987_276935996` | 276935987 (83.7004, −69.7101) | 276935996 | 26.3 | 276935996 | 283 / 623 | cache list made after QR2 vanished, so QR3 only |
| `pair_279569707_279569718` | 279569707 (105.9680, −57.6292) | 279569718 | 67.2 | 279569707 | 62 / 62 | QR3 only (same reason) |
| `pair_280033934_280033918_qr3only` | 280033934 (297.5895, +70.2877) | 280033918 | 68.2 | 280033934 | 126 / 170 | QR3 only |
| `pair_420114776_420114772` | 420114776 (290.4289, +74.7681) | 420114772 | 20.1 | 420114772 | 345 / 569 | DR1+QR3 |
| `pair_99028324_99028319` | 99028324 (181.3075, −25.5632) | 99028319 | 14.6 | 99028324 | 315 / 351 | DR1+QR3 |

Pair TIC IDs from these folder names: 124712820, 124712813, 140659978, 140659980, 150101476, 150101472, 16805617,
16805614, 198242676, 198242678, 233058262, 233058265, 243391171, 243391162, 258918831, 258918835, 269696430,
269696438, 276935987, 276935996, 279569707, 279569718, 280033934, 280033918, 420114776, 420114772, 99028324, 99028319.

**Image lists queried but with no pair folder** (`research/out/images/`): TIC 356974629 (314.3262, +44.7251; pair
partner 356974639, documented "not testable: 2 exposures in primary"). **Eclipse image lists in `cache/eclipse/`**
(website collections) for further TICs: 159854359, 161687311, 164558072, 199574208, 202442974, 219900027,
220402294, 233058262, 233208885, 233233639, 233532554, 259006185, 294092960, 377192658, 441804888, 55753808, plus the
pair stars above.

Documented outcomes (`notes/SPHEREX_BLEND_SURVEY.md`, `research/out/summary.md`): identified sources 233058262,
140659978, 420114772 (probable), 150101476, 258918831, 269696430; validated on 276935987, 233058262 and WW Dra
(198242678); unsettled 243391171, 99028324, 16805617; untestable 124712820 (clock drift 0.27 of an orbit) and
356974629.

---

## 18. Known bugs and limitations

Documented issues (from `notes/`):

| # | Issue | Source | Status |
|---|---|---|---|
| D1 | QR2 collections return nothing; `COLLECTIONS` should become DR1 + QR3 | `SPHEREX_BLEND_SURVEY.md` | Open in `config.py` |
| D2 | SPHEREx eclipse depths shallower than TESS (31% vs 42%, 18% vs 30%) | `ECLIPSE_FINDINGS.md` §3 | Unexplained (see item 4 below) |
| D3 | Fold χ²ᵣ ≈ 10, errors statistical only | `ECLIPSE_FINDINGS.md` §3 | Open |
| D4 | Difference scatter 0.7–0.8 (VARIANCE too large after resampling) or ≫ 1 near bright stars | `DAY3_FINDINGS.md` §2 | "Which noise to quote is still open" |
| D5 | Field-star floor unknown in most 3′ frames (no isolated bright Gaia star) | `DAY4_FINDINGS.md` | Open |
| D6 | RW Aur 10–20% spread within 2 hours; many flagged pixels in the circle | `DAY4_FINDINGS.md` §6 | Open |
| D7 | JPL offset sign assumed; JPL second pass failing; spacecraft axes assumed ICRF | `DAY5_FINDINGS.md` §7, `spots.py` | Open |
| D8 | Saturated stars (Barnard, R Dra): no light curve | `DAY4_FINDINGS.md` | By design |
| D9 | Crowding-correction explanation for pair 420114776/420114772 unchecked (needs CROWDSAP) | `SPHEREX_BLEND_SURVEY.md` | Open |
| D10 | No independent TESS-pixel check (TESS-Localize) | `SPHEREX_BLEND_SURVEY.md` | Open |
| D11 | Eclipse research scripts for TIC 233058262 live in git-ignored `scratch/` | `ECLIPSE_FINDINGS.md` §6 | Open |
| D12 | `notes/REVIEW_NOTES.md` has no entries yet (template only) | file | — |

Issues found in the code during this audit:

1. **Stale collections, silent data loss** — `config.COLLECTIONS`, used by `archive.find_images`,
   `eclipses.images_by_detector`, `render.render_frames`, `coverage.coverage_answer`, `proof.releases`,
   `methane.fetch_window`. Science impact: yes (section 3).
2. **Cache keys without release; never-expiring image lists** — `archive.cutout_file` (name from the DID's query part
   only), `eclipses.cached_images` (no refresh caller). Science impact: maybe (mixing or reusing superseded files).
3. **Flagged values leak through bilinear resampling** — `clean.clean_cutout` does not blank flagged pixels;
   `align.align` interpolates image bilinearly and mask nearest-neighbour. Also `lightcurve.measure` includes flagged
   pixel values in the flux (counted in `n_flagged` only). Science impact: yes for single-pixel spots and flagged
   light-curve pairs.
4. **Depth definition vs TESS depth** — `eclipse_depth.weighted_depth` with `CENTRAL = 0.5` measures the mean over the
   middle half of the eclipse; `eclipse_build.analyse` compares it with the TESS-EBs depth at minimum in
   `checks.tess_band`. A likely, untested contributor to documented issue D2. Science impact: yes for absolute depths;
   smaller for ratios.
5. **Light-curve exposure set depends on the cache contents** — `rebuild.cached_visits` (used by
   `lightcurve.write_exposures`) takes every cached cutout matching `*_D<d>_<ra>_<dec>_<size>.fits` and assigns it to
   the nearest frame within `SAME_VISIT_DAYS = 60`. `methane.fetch_window` downloads up to 150 D4 and D5 cutouts with
   the same position and size, so re-running `lightcurve --rebuild-exposures` or `rebuild` on a D4/D5 folder after
   methane vision would include exposures that are not in the frames (and `rebuild.frame_picture` would raise on the
   count mismatch). Science impact: maybe (changes which points are in a light curve).
6. **Clock quality never enforced** — `eclipses.MAX_PHASE_ERROR = 0.01` used only in a label; no comparison of phase
   error with eclipse width anywhere (`forecast`, `select_for_download`, `which_star_pair.run`, `run_pairs.main`).
   Science impact: yes for non-detections.
7. **Missing catalogue uncertainties become 0; impossible depths accepted** — `eclipses._ephemeris`
   (`bjd0_err = ... or 0.0`, `period_err = ... or 0.0`), `_eclipse_numbers` (accepts `depth > 1`). 21 + 7 and 38 rows
   affected. Science impact: maybe.
8. **Noise propagation** — `align.align` resamples `sigma²` bilinearly; `lightcurve.measure` treats pixels as
   independent ("a lower limit after reprojection", stated in `error_text`); empirical jitter of 2–6% per detector
   then absorbs the gap (`eclipse_build.add_jitter`). Science impact: maybe (errors are empirical, not modelled).
9. **Secondary-eclipse panel phase in `research/plot_phase.py:main`** — `sec = clock.sec_pos` (raw catalogue value)
   while `phi` already has `prim_pos` subtracted; the backend uses `secondary_phase() = sec_pos − prim_pos`. The offset
   equals `prim_pos − 1` (or `prim_pos` itself when it is near 0): up to 0.0076 for the pair clocks (e.g. TIC
   420114776 has `prim_pos = 0.9924`; TIC 233058265 has 0.0036). It shifts only the plotted secondary window and its
   binned means, not the blind scan. Science impact: no for the scan; maybe for reading the secondary-eclipse panel of
   narrow eclipses.
10. **Inconsistent clock choice in research** — `which_star_pair.run` picks the clock at the median BTJD of
    `mjds[:50]` (the first 50 images in dict order, i.e. the earliest detector-1 images), `run_pairs.main` at BTJD
    4000. Science impact: no in practice (both pick the better-timed entry), but undocumented.
11. **S/N selection bias** — `eclipse_build.analyse` keeps points with `flux > 5 × err`, `which_star_pair.depth_test`
    with `f > 3 × e`; faint in-eclipse points drop out first. Science impact: maybe for faint, deep eclipses.
12. **Gaussian PSF on smoothed co-adds for deblending** — `which_star_pair.two_star_fit`, `psf_shape`,
    `psf_photometry`; the PSF cube that could be used is discarded at download (`config.DROP_PSF_FROM_CUTOUTS`), and
    the DR1/QR3 `EPSF` extension is kept but never read. Science impact: maybe for pairs closer than about 20″.
13. **Comparison stars get the target's wavelength** — `lightcurve.comparison`, `eclipse_build.field_null`. Science
    impact: maybe (null tests), mainly D5–D6.
14. **Flag coverage differs by release** — `flags.bad_pixel_bitmask` silently skips 9 of 19 names for QR2. Science
    impact: maybe.
15. **Download parallelism above the documented limit in research** — `which_star_pair.py` sets
    `archive.MAX_PARALLEL_DOWNLOADS = 6` (config says IRSA answers 503 at 4+). Failed downloads are dropped silently by
    `eclipse_build.load_exposures`, so the exposure set can depend on server load. Science impact: no (random loss),
    but reduces data.
16. **Hard-coded values worth re-checking**: `PIXEL_SCALE_ARCSEC = 6.15` (true pixel areas 37.4–38.4 arcsec²,
    documented); `config.DETECTORS` band edges; `RESOLVING_POWER`; the 2g width factor 0.5; the 2026.0 target-match
    year in `gaia.write_gaia`; `MAX_WING_INNER_PX = 3.0` from one star (RW Aur).
17. **Cache size above its own limit** — 24 GB in `cache/cutouts/` against `CUTOUT_CACHE_MAX_GB = 10.0`, because
    `trim_cutout_cache` runs only before live eclipse jobs. Science impact: no.
18. **Stale test** — `backend/tests/test_day5.py:143` expects WISE 0855 spectra from D2, D5, D6 only. Science impact:
    no.

No unit mismatches were found: MJy/sr is used throughout until the single conversion to mJy
(`MJY_PER_PIXEL_UNIT = 0.889`), VARIANCE is in MJy²/sr², wavelengths are in µm (obscore `em_min`/`em_max` in metres
× 1e6), proper motions in mas/yr with the cos(Dec) convention, times in MJD (UTC) converted once to BTJD (TDB).

---

## Priority list of improvements

1. Switch `COLLECTIONS` to DR1 + QR3; add the collection to the cutout cache key and to every output; rebuild the two
   eclipse folders and the flipbook frames from DR1.
2. Blank flagged pixels before resampling; quantify how many "good" grid pixels change.
3. Enforce a clock rule relative to eclipse width, and re-fold on the SPHEREx-fitted eclipse time before measuring
   depths.
4. Report depth at minimum (from the trapezoid fit) next to the middle-half mean, and compare the former with TESS.
5. Use the official PSF (EPSF) for forced photometry and deblending; add per-detector aperture corrections.
6. Replace the blind-scan σ with a permutation-based false-alarm probability.
