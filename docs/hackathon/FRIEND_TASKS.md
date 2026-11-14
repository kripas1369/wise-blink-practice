# Friend's tasks: Space Apps 2026, "Planet X and SPHEREx"

You own the **data pipeline**: finding SPHEREx images, reading the pixels from AWS, cleaning, lining up, adding up, and every measurement file the website shows. Kripas owns the API (`main.py`), the website and the final checks. He reviews and merges every pull request you open.

## How to use this file
1. Each block is 2 hours: **20 min study** (read the old files listed and answer the questions for yourself), **70 min** pasting the prompt into Antigravity and working through it with the agent, and **30 min** running the tests, opening the pull request and fixing what Kripas asks.
2. Paste the **Session prompt** below once at the start of every new Antigravity chat, then paste the block's prompt.
3. Before you push, read every changed file yourself. You must be able to explain it if a judge asks.
4. Write the commit messages yourself, short and in your own words ("port flags reader for QR3 headers").
5. Put the answers to the block's study questions in the pull request description.
6. If something in a prompt is wrong (a file is missing, a test cannot pass), stop and tell Kripas. Don't guess around it.

Replace `<OLD>` with the path of `wise-blink-practice` on your machine, for example `/Users/you/wise-blink-practice`.

---

## Session prompt (paste once per Antigravity chat)
```text
Project: NASA Space Apps 2026 "Planet X and SPHEREx". A public web tool that shows a SPHEREx
flipbook of any sky position (RA/Dec) so people can spot moving and changing objects.

Two repos:
- OLD (reference, read only): <OLD>   (our own practice repo "wise-blink-practice")
- NEW (this folder, repo "blinkit"): the hackathon repo. backend/ (Python FastAPI + pipeline), frontend/ (plain JS),
  docs/ (FACTS.md, FRAMES_FORMAT.md, API.md, VALIDATION.md).

My role: the data pipeline in backend/app/ and scripts/. I must NOT edit backend/app/main.py,
backend/app/resolve.py, backend/app/targets.py or anything in frontend/ (Kripas owns those).

Rules:
- Port by copying the old file, then apply only the changes I list. Keep the old style: short
  docstrings that say what and why, no comment on obvious lines, same naming.
- Data: SPHEREx collections spherex_qr3, spherex_qr3_deep, spherex_dr1, spherex_dr1_deep.
  QR2 is no longer listed by IRSA search. Pixels come from IRSA's public AWS bucket
  https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com (anonymous HTTPS, no keys, no AWS account).
  Search (which images cover a position) uses IRSA TAP spherex.obscore. Gaia DR3 and CatWISE2020
  come from IRSA TAP.
- Never use paid services, never read .env files, never commit cache/ or .venv/.
- Timestamps: MJD-AVG, never DATE. Flags: bit positions from the FLAGS header; SOURCE is a label,
  never a defect.
- Never write "discovered" or "new object"; say "candidate" or "spot".
- After changes run: .venv/bin/python -m pytest backend/tests -q
- Show me a short summary of every file you changed and why.
```

---

# PHASE 1 (Sat 14 Nov): a flipbook for every detector

## B0, 11:00 to 11:30: setup (no prompt)
- Accept Kripas's GitHub invite and clone the new repo `blinkit`.
- `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Read `docs/API.md`, the challenge page, and `<OLD>/docs/plan/FRAMES_FORMAT.md` sections 1–3.

## B1, 11:30 to 13:30: find the data
**Study (20 min):** `<OLD>/backend/app/config.py`, `archive.py` (functions `find_images`, `group_epochs`, `download_cutout`), `flags.py`, `coverage.py`; `<OLD>/docs/plan/FACTS.md` sections 1–3; `<OLD>/research/discovery_2026/DATA_RELEASE_AND_ACCESS_AUDIT.md` sections 1 and 4.

**Prompt:**
```text
Block B1 (find the data). Branch: friend/b1-data.

1. Read <OLD>/backend/app/config.py, coords.py, motion.py, flags.py, archive.py, coverage.py and
   <OLD>/docs/plan/FACTS.md sections 1-3. Explain them to me in 6 bullet points before changing anything.
2. Copy those 6 files into backend/app/ (create backend/app/__init__.py and backend/__init__.py if missing).
3. config.py:
   - COLLECTIONS = ("spherex_qr3", "spherex_qr3_deep", "spherex_dr1", "spherex_dr1_deep")
     with a comment that QR2 is no longer listed by IRSA search (checked 13 Nov 2026).
   - The SPHEREX_COLLECTIONS environment variable (comma separated) overrides it.
   - Add S3_BUCKET_URL = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com" and
     SPHEREX_PIXELS = os.environ.get("SPHEREX_PIXELS", "s3")  # "s3" or "cutout".
4. archive.py:
   - discover_collections(): SELECT DISTINCT obs_collection FROM spherex.obscore, keep names starting
     with "spherex_" that do not end with "_cal"; cache the answer for 1 hour.
   - releases(): for each collection, image count and first/last observation date (MJD-AVG based
     column of obscore), cached 1 hour. Return a list of dicts.
   - find_images() must also return each image's S3 key. Look at how
     <OLD>/research/discovery_2026/scripts/spx_s3.py gets it (the cloud_access column,
     json -> ["aws"]["key"]). Check whether spherex.obscore has cloud_access; if not, use the SIA2
     route from spx_s3.py. Add an s3_key field to SpherexImage.
5. flags.py: keep both header styles (MP_* and MSKN*/MSKM*). If neither is in the FLAGS header,
   raise an error; never treat all pixels as good.
6. Remove any import of eclipses, methane or ask.
7. Copy <OLD>/backend/tests/test_flags.py, test_coverage.py, test_motion_archive.py, test_coords.py
   into backend/tests/ and make them pass. Add one test for the SPHEREX_COLLECTIONS override and
   one for discover_collections filtering (_cal removed), using a fake query result.
8. Run once, live, and write the numbers in docs/VALIDATION.md under "B1":
   - a QR2 search for Barnard's Star at the "ra"/"dec" of <OLD>/frontend/frames/barnard/d2/manifest.json
     (the position already moved for proper motion): expected 0 rows;
   - Barnard's Star coverage per collection and per detector with the new COLLECTIONS;
   - releases() output;
   - whether every image has an s3_key.
Do not touch main.py, resolve.py, targets.py or frontend/.
```
**Study questions (answer in the pull request):** Why MJD-AVG and not DATE? Why is SOURCE not a bad flag? What is a "visit" in `group_epochs` (gap and span rules)? Why does each SPHEREx exposure see a different wavelength?

**Done when:** `pytest backend/tests` passes; VALIDATION.md "B1" is filled in; pull request `friend/b1-data` is open.

## B2, 14:00 to 16:00: clean images and make per-detector frames
**Study (20 min):** `<OLD>/backend/app/clean.py`, `align.py`, `coadd.py`, `render.py`; `<OLD>/docs/plan/FRAMES_FORMAT.md` sections 2, 3, 8, 9; `<OLD>/research/discovery_2026/scripts/spx_s3.py` (functions `get_range`, `read_header`, `read_rows`, `stamp`); DATA_RELEASE_AND_ACCESS_AUDIT.md sections 2 and 5.

**Needs from Kripas's B1 (already merged by 14:00):** `backend/app/resolve.py` and `targets.py`, because `render.py` imports them. If they are not merged yet, pull Kripas's branch.

**Order that keeps Kripas unblocked:** first make frames with the cutout route (steps 1–4), push a draft pull request, then add the AWS reader (steps 5–8).

**Prompt:**
```text
Block B2 (frames). Branch: friend/b2-frames.

Part A, working frames first (cutout route):
1. Copy <OLD>/backend/app/clean.py, align.py, coadd.py, render.py, frame_notes.py into backend/app/.
2. frame_notes.py: keep the structure, but replace every note with
   "Not yet re-measured on DR1/QR3 data." (the old notes were measured on QR2 frames).
3. render.py: each frame in manifest.json also gets
   - "release" (e.g. "QR3" or "DR1", from the images used),
   - "flag_counts": {flag name: number of flagged pixels} using the official BAD_FLAG_NAMES,
   - "pixel_source": "aws-s3" or "irsa-cutout".
   The manifest gets "collections_checked" and "newest_obs_date". Update docs/FRAMES_FORMAT.md
   section 3 with these fields.
4. Copy <OLD>/backend/tests/test_pipeline.py and make it pass. Then run
   python -m backend.app.render barnard 2 --out frontend/frames
   and tell me the frames, dates and n_images. Stop and tell me so I can push a draft PR.

Part B, pixels from AWS:
5. Create backend/app/s3_reader.py based on <OLD>/research/discovery_2026/scripts/spx_s3.py
   (get_range, read_header, hdu_end, read_rows incl. the row-tiled RICE_1 decode).
   read_box(s3_key, ra, dec, size_deg) -> astropy HDUList with IMAGE, FLAGS, VARIANCE, ZODI
   (only the rows covering the box, columns cropped, CRPIX1/CRPIX2 shifted so the WCS stays right)
   plus the WCS-WAVE table HDU unchanged, so clean.clean_cutout() and clean.wavelength_at() work
   without changes. Cache each box on disk under cache/s3/<release>/<obs_id>_<ra>_<dec>_<size>.fits.
   Retry 4 times; on failure raise, so the caller can fall back.
6. archive.download_cutout(): when config.SPHEREX_PIXELS == "s3" and the image has an s3_key, use
   s3_reader.read_box(); on any exception fall back to the IRSA cutout service and record
   pixel_source = "irsa-cutout". Keep at most 3 parallel cutout downloads; S3 may use 8 threads.
7. Test: tests/test_s3_reader.py with a tiny fake FITS file served from memory (no network) that
   checks CRPIX shift and row cropping.
8. Live validation, write to docs/VALIDATION.md under "B2":
   - for 3 Barnard D2 exposures, compare IMAGE, FLAGS, VARIANCE from S3 vs the IRSA cutout of the
     same box: max absolute difference (expected 0) and wavelength_at() for both;
   - time `render barnard 2` at --fov 3, 10, 20, 30 for both routes (seconds, MB downloaded).
Do not touch main.py, resolve.py, targets.py or frontend/ code (frontend/frames output is fine).
```
**Study questions:** Why must every frame be reprojected onto one north-up grid? What does 1/variance weighting do? Why read only some rows from S3 instead of the whole file?

**Done when:** the tests pass; Barnard D2 frames exist; the S3 and cutout pixels are identical for 3 exposures; the timings are in VALIDATION.md.
**If S3 is not ready by 16:00:** push Part A, keep the cutout route for B3, and finish Part B in B4 (it must be done before B5).

## B3, 16:00 to 18:00: all 5 targets in all 6 detectors, Gaia and WISE
**Study (20 min):** `<OLD>/backend/app/gaia.py`, `motion.py`; FRAMES_FORMAT.md section 6; `<OLD>/research/wanderers/common.py` (functions `catwise`, `gaia_xy_at`); the CatWISE note: proper motions are in arcsec/yr, positions at MJD 57170.

**Prompt:**
```text
Block B3 (all targets, overlays). Branch: friend/b3-targets.

1. Copy <OLD>/backend/app/gaia.py into backend/app/ (write_gaia makes gaia.json).
2. New backend/app/wise.py with write_wise(folder): CatWISE2020 sources (IRSA TAP table catwise_2020)
   inside the frame, moved with their proper motion (pmra/pmdec in arcsec/yr, reference epoch
   MJD 57170 = 2015.4) to every visit date of the manifest. Write wise.json in the same shape as
   gaia.json (format "spherex-blink-wise/1"). Use research/wanderers/common.py catwise() as reference.
3. Alignment check in render.py (or a small align_check.py): for each frame, the median offset in
   pixels between Gaia DR3 stars (G < 17, pm < 100 mas/yr) predicted at that date and their measured
   centroids. Store "align_offset_px"; if > 0.5 add a note "possible misalignment".
4. Make the cache key include release and obs_id.
5. Render ALL 5 official targets in ALL 6 detectors into frontend/frames (30 folders):
   for t in barnard eps_ind_b wise0855 rw_aur r_dra; for d in 1..6:
     python -m backend.app.render $t $d --out frontend/frames
   then write_gaia and write_wise for each folder, then write_index.
6. Validation in docs/VALIDATION.md under "B3":
   - table: target x detector -> visits, n_images per visit, pixel_source, align_offset_px;
   - old vs new: compare <OLD>/frontend/frames/*/d*/manifest.json (QR2) with the new ones
     (visit dates, n_images, pct_flagged);
   - QR2 vs DR1 on AWS: take 5 exposures listed in <OLD>/frontend/frames/barnard/d2/originals.json,
     read them from qr2/level2/ on S3, find the same exposure in DR1 (same obs_id), and compare
     MJD-AVG, WCS centre, flagged-pixel fraction and the median pixel difference. Describe any
     difference; do not hide it.
7. Add tests for wise.py (fake catalogue rows -> positions moved correctly).
```
**Study questions:** Why do Gaia positions need moving to each visit date? Why does CatWISE use a different reference epoch than Gaia (2016.0)? What would a bad alignment look like in the flipbook?

**Done when:** 30 frame folders exist; gaia.json and wise.json are in each; VALIDATION.md "B3" is filled in; every frame has `pixel_source = aws-s3` (unless S3 moved to B4).

## B4, 18:30 to 20:30: add and subtract visits
**Study (20 min):** `<OLD>/backend/app/diff.py`, `measure.py`, `proof.py`; FRAMES_FORMAT.md sections 7, 8, 11.

**Prompt:**
```text
Block B4 (add and subtract visits). Branch: friend/b4-diff.

1. Copy <OLD>/backend/app/diff.py, measure.py, proof.py. Copy <OLD>/backend/tests/test_day3.py and
   the proof tests from test_day5.py (skip parts that need spots/spectrum; those come later).
2. Minus-median frames (WiseView-style difference): in diff.py add write_minus_median(folder):
   median.fits/png = per-pixel median of all visit frames (only pixels good in at least 2 visits);
   minus_median<i>.png = (visit_i - median) / sigma_i, same colour scale as the diff maps.
   Add the list to diff.json.
3. New backend/app/stack.py, write_stack(folder, visits=None): add the chosen visits
   (all if None) with 1/variance weights using coadd.coadd on epoch<i>.fits.
   Outputs stack.fits, stack.png, stack.json {visits, n_images, noise_per_pixel,
   noise_ratio_vs_single_visit}. Test: noise drops close to 1/sqrt(N) on fake data.
4. Run write_diff, write_minus_median, write_proof and write_stack for all 30 folders.
5. Validation "B4": Barnard D2 measured shift between first and last visit vs Gaia prediction
   (expected about 1.7 px, must agree within 0.5 px); same for WISE 0855 D6 and Eps Ind B; the
   stack noise ratio for Barnard D2.
```
**Study question:** Why do we pick the visit pair with the closest wavelengths for the difference?
**Done when:** the tests pass; diff, proof, stack and minus-median files exist in all 30 folders; the shifts are in VALIDATION.md.

## B5, 20:30 to 22:30: Phase 1 sign-off (with Kripas)
**Prompt:**
```text
Block B5 (sign-off). Branch: friend/b5-signoff.
1. Write scripts/check_frames.py: for every frontend/frames/<target>/d<det>/ folder print visits,
   n_images, pixel_source, release, align_offset_px, pct_flagged, and fail if any file required by
   docs/FRAMES_FORMAT.md is missing or pixel_source != "aws-s3".
2. Run it and paste the table into docs/VALIDATION.md "B5".
3. Re-measure frame_notes.py: for each target and detector write one honest sentence from the new
   frames (what is visible, is the target saturated, flagged share). Only measured statements.
4. Tell Kripas which detector is best for each target (for frontend/js/targets.js ratings),
   with the measurement behind each choice.
```
**Done when:** `check_frames.py` passes for all 30 folders, VALIDATION.md is complete, and Kripas has tagged `phase1`.

---

# PHASE 2 (Sat night and Sun): learn from WiseView, then the 102 bands

## P2-1, Sat 22:45 to 00:45: WiseView study (no coding)
Use `docs/tasks/WISEVIEW_STUDY_TEMPLATE.md`. You do the **hands-on** part: every control, what it does, which settings make each mover easiest to see, and how long spotting takes for WISE 0855, Epsilon Indi B and Barnard's Star. Record only what you see or read. Then decide with Kripas the adopt / adapt / skip table.

## P2-2, Sun 07:00 to 09:00: signal-to-noise per detector (NASA's suggestion)
**Study:** NASA's sentence: "separately add together all the data taken by each of the six detector arrays to improve the signal-to-noise". Read `render.py` (`max_per_visit`) and the B2 timings.

**Prompt:**
```text
Block P2-2 (signal-to-noise). Branch: friend/p2-snr.
1. render.py: default max_per_visit = all exposures of the visit (safety cap 200 per detector),
   for prepared targets and for API jobs (Kripas will change JOB_EXPOSURES_PER_VISIT in main.py).
2. Each frame records "noise_per_pixel" (median sigma of good pixels) and
   "noise_ratio_vs_single" = median single-exposure sigma / frame sigma (expected about sqrt(n)).
3. New backend/app/bands.py, write_bands(target_dir):
   - per visit: a 6-detector strip (D1..D6 add-ups on the same grid, each its own stretch) -> bands<i>.png;
   - per visit: a false-colour picture, blue = D1+D2, green = D3+D4, red = D5+D6 -> colour<i>.png;
   - deep per detector: all visits added (stack.write_stack on every visit) -> deep_d<det>.png,
     with n_images and noise ratio;
   - bands.json ("spherex-blink-bands/1") listing all of it.
4. Re-render all 30 folders and run write_bands for the 5 targets.
5. Validation "P2-2": n_images per visit before (8) and after (all); measured noise ratio vs sqrt(n);
   WISE 0855 is red in colour<i>.png (give its RGB values).
```
**Done when:** the measured gain is in VALIDATION.md and the bands files exist for the 5 targets.

## P2-3, Sun 09:00 to 11:00: spectra on the fly and the 102 bands
**Study:** `<OLD>/backend/app/lightcurve.py`, `spectrum.py`, `pixels.py`; FRAMES_FORMAT.md sections 10 and 13; the AWS file `qr3/spectral_channels/cal-sch-v2-2026-229/spectral_channels_spx_cal-sch-v2-2026-229.fits` (also in `dr1/spectral_channels/`).

**Prompt:**
```text
Block P2-3 (live spectra, 102 bands). Branch: friend/p2-spectra.
1. Copy <OLD>/backend/app/lightcurve.py, spectrum.py, pixels.py and tests test_day4.py,
   test_pixels.py; make them pass.
2. New backend/app/channels.py: download (once, cached under cache/calib/) the spectral_channels
   file from S3 for the release of each image; print its HDUs and columns first and show me.
   band_number(detector, wavelength_um) -> 1..102 (17 per detector, numbered D1 first).
   Test the band edges against the file.
3. spectrum.py: spectrum_at(ra, dec, folders) computed live for any position or clicked pixel,
   from the cached exposures of every rendered detector: per-exposure points
   {mjd, visit, detector, band_number, wavelength, flux, flux_err, flagged}
   and a binned spectrum per visit (102 bins, empty bins omitted). Must take < 10 s when cached.
4. Validation "P2-3": R Dra and RW Aur light-curve trend vs visits; time of spectrum_at for
   Barnard (cached); number of the 102 bands present per target.
```

## P2-4, Sun 11:00 to 13:00: creative band views (in this order; stop at 13:00)
Pick the next item, paste its prompt, and push each one as soon as it works.
1. **102-band contact sheet:** `lens.py` `write_contact_sheet(target_dir)`: one image per official band (6 rows × 17), built from the exposures whose band number matches, 1/variance weighted; empty bands marked. Output `contact.json` and `contact_b<n>.png`.
2. **Spectral Lens + methane:** `lens.py` `lens_image(target_dir, wavelength, width)` and molecule maps `(band − k × continuum) / noise`, with k calibrated on field stars exactly as `<OLD>/backend/app/methane.py` does. Preset CH4: 3.15–3.50 µm vs 3.90–4.20 µm. Validation: WISE 0855 and Epsilon Indi B glow, Barnard does not, and field stars average about 0.
3. Other presets: H2O ice 3.05, CO2 4.27, CO 4.67, PAH 3.29, Paschen-α 1.87, Brackett-α 4.05 µm (state the band and continuum used for each).
4. Wavelength movie: one visit, about 16 wavelengths from 0.75 to 5 µm.
5. PSF-fit spectrum: port the forced ePSF photometry from `<OLD>/research/discovery_2026/scripts/phot.py` (ePSF files from AWS `{dr1,qr3}/epsf/`); keep the 2 px circle as a cross-check.
6. `movers.json` for the 5 fields from `<OLD>/research/wanderers/` results (`results/ctrl_*`).
7. `scripts/build_showcase.py`: about 50 famous objects, positions from SIMBAD, SPHEREx coverage counts, best detector, saturation note.
8. Evidence: port `spots.py`, `known_objects.py`, `field_objects.py`, `recovery.py`, `visit_frames.py`, `gif.py`, `originals.py` and their tests (`test_day5`, `test_day6`, `test_day7`).

---

# PHASE 3 (Sun afternoon): help finish
- `scripts/refresh_release.py <target|--all>`: run coverage again, list new `obs_id`s, and re-render only if new ones exist.
- An IRSA status probe function for Kripas's indicator (one small TAP query, cached 5 min).
- Pre-warm the cache on the deployed server for the 5 targets.
- Act as a normal user: 5 timed tasks on the live site, and write the problems found in VALIDATION.md.
