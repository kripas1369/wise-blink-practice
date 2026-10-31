# Learning log

One entry per session. Keep it short: 3 lines plus the time. This becomes our lessons-learned note on 9 Nov.

## Template (copy for each session)

### Day N, <date>, <name>
- **Learned:**
- **Broke / confused me:**
- **Time:** planned __ h, actual __ h

---

### Day 0, Thu 29 – Fri 30 Oct, both
- **Learned:** checked the real archive: the `s_region` query works for all 5 targets; Gaia table is `gaia_dr3_source`; SIMBAD main server down, Harvard mirror works.
- **Broke / confused me:** the 4-day plan slipped by 2 days (moved to Sat 31 Oct – Tue 3 Nov).

### Day 1, Sat 31 Oct, Kripas (data code, made before the role swap)
- **Learned:** a `CONTAINS` query cannot JOIN the file table (2-step query); cutout path = `a.uri` minus `ibe/data/`; cutouts are ~4–5 MB because the PSF comes along; IRSA says 503 above ~3 parallel downloads; the archive mixes QR2 + QR3 + calibration rows; QR3 writes flag bits as `MSKN*` instead of `MP_*`; SOURCE covers 98–100% of pixels around bright targets; Barnard's Star moves only ~1.7 px in the data so far.
- **Broke / confused me:** R Dra became one year-long "epoch" (fixed with a 60-day maximum); SIMBAD timeouts made the report take 10 minutes (fixed: remember the server that works).
- **Time:** planned 7 h, actual __ h. Read `learning/` 01–03 and re-type the code.

### Day 1, Sat 31 Oct, Kripas (website, after the role swap)
- **Learned:** npm Aladin Lite 3.8 is an ES module, so `<script src>` gives no `window.A` (use `import()`); the WebGL map needs CORS on the image tiles: IRSA's HiPS copies have none, ESA ESASky's do; on the old 2MASS map Barnard's Star sits ~4.5′ from today's position, so moving it with proper motion is visible by eye; SIMBAD TAP works from the browser (CORS `*`) and returns ids like `M  31` with double spaces.
- **Broke / confused me:** target buttons with `role="listitem"` stopped being buttons for screen readers (now `<li><button>`); a slow SIMBAD answer could overwrite a newer map click (fixed with a version counter); the end of a map drag counted as a click (fixed: ignore presses that moved > 5 px); "M31" was treated as numbers because "m" is a unit letter (now only after a digit).
- **Time:** planned 5 h, actual __ h. Re-type `coords.js` and `urlstate.js` myself.

### Day 2 (done early, Sat 31 Oct), Kripas (website flipbook)
- **Learned:** a 29 × 29 picture needs `image-rendering: pixelated` or it turns to mush; each visit sees a different wavelength inside one detector (Barnard D2: 1.235, 1.314, 1.539 µm, from the file's spectral WCS), so brightness changes between visits are not automatically real; reproject's footprint is 0 both outside the image and at NaN pixels (a saturated star core), so I reproject an array of ones to tell them apart; WISE 0855 is not clearly seen in single D6 exposures (2–5 sigma), and a fixed background dot sits 9″ from it in D2, so the website now says so in an orange box.
- **Broke / confused me:** NaN star cores showed as black "sky" (now striped and counted); `hidden` did nothing on elements whose CSS sets `display` (added `[hidden] { display: none !important }`); a zsh loop passed `"wise0855 6"` as one word; SIMBAD stopped answering midway through a batch (the script stops instead of guessing).
- **Time:** planned 7 h, actual __ h. Re-type `player.js` and `frames.js` myself.

### Day 2 (Sat 31 Oct afternoon), Kripas (data pipeline, after [Friend's name] moved to validation and research)
- **Built:** `clean.py`, `align.py`, `coadd.py`, `render.py`, `frame_notes.py`; 9 offline tests; `scripts/measure_ring.py`. The website now shows add-ups (R Dra still single exposures).
- **Learned:** `render --mode single` gave exactly the morning frames (grey difference 0), a good first check; adding up exposures fills flagged pixels from the other exposures (Eps Ind B Apr 2026: 30% → 0%); an add-up mixes wavelengths across most of the detector, so it shows *where*, not *how bright*; WISE 0855 shows up in the D6 add-ups (11 and 13σ, still 6–9σ in each half), not yet proven to be WISE 0855.
- **Broke / confused me:** a failed download was silently treated as "not in image" and an add-up used 17 instead of 21 exposures (now it stops and retries); pyvo has no timeout, so a dropped IRSA connection hung for 55 minutes (now 300 s, then retry); R Dra's full search kept timing out (now one detector at a time); running a script in parallel with editing it gave me results from the old code twice: once a wrong motion direction for WISE 0855 D6 (east instead of west), once a wrong grouping of close visits. Lesson: edit, then run.
- **Time:** planned (friend's Day 2) 7 h, actual __ h. Re-type `coadd.py` myself.

### Day 3 (done early, Sat 31 Oct), Kripas (Gaia, difference, API, website)
- **Built:** `rebuild.py` (per-visit `epoch<i>.fits`), `gaia.py`, `diff.py`, FastAPI `main.py`, `scripts/measure_motion.py`; Gaia markers and the Before / After / Difference view on the website; 19 backend + 9 website tests. Explained in [`learning/11_day3_gaia_diff_api.md`](../learning/11_day3_gaia_diff_api.md).
- **Learned:** Barnard's Star moves the way Gaia says (1.59 px vs 1.67 px north), Eps Ind B too (0.99 vs 1.09 px south-east); a bright star leaves a blue/orange pair in the difference even when it does not move (RW Aur), so a pair is motion only when it matches Gaia; scatter of z far above 1 (Barnard 7.9) means σ is too small for that picture; Gaia ids do not fit in a JavaScript number (store as text); WISE 0855 is not in Gaia.
- **Broke / confused me:** rebuilt pictures differed from the website's by 9 grey levels on one pixel, because the manifest position was rounded to 6 decimals (now stored exactly); the R Dra add-up keeps core pixels up to 2,870 MJy/sr, so a linear scale makes everything else black (not installed; Day 4); I wrote "west" for Eps Ind B's motion in a note when PNG x −0.93 means east (caught by re-reading the sign rule: +x = west).
- **Time:** planned 7 h, actual __ h. Re-type `difference()` in `diff.py` myself.

### Day 4 (done early, Sat 31 Oct), Kripas (light curve, asinh scale, C4 tests; not online yet)
- **Built:** `lightcurve.py` (`exposures.fits`, `lightcurve.json`), `/api/lightcurve` (+ clicked pixel), `render.py`/`rebuild.py --stretch asinh`, `scripts/acceptance.py`; website light-curve panel (`lightcurve.js`, SVG charts); 15 backend + 10 website tests. Explained in [`learning/12_day4_lightcurve.md`](../learning/12_day4_lightcurve.md).
- **Learned:** a light curve must be made from single exposures, because each one sees a different wavelength (Eps Ind B is 7× fainter at 1.38 than at 1.27 µm); compare visits only at the same wavelength; a steady field star changes by 4.5% measured this way, so smaller changes are not evidence; the WISE 0855 D6 source moves 0.58 ± 0.12 px where WISE 0855 should move 0.72 px (motion + parallax) and a fixed star 0; the D2 dot is a Gaia star (G 16.31).
- **Broke / confused me:** a ring 6–9 px around Barnard's saturated core gave a fake 0.62 ratio (now: no light curve when the hole reaches beyond 3 px); WISE 0855's D2 "brightening" was the moving circle sliding over a fixed Gaia star (now a warning); one flagged D6 exposure measured 520 mJy and squashed the chart (now drawn as ▲ and named); flagged-only scaling would have pushed most RW Aur points off the chart (now only flagged points 3× above the clean ones); AAVSO and VizieR were unreachable, so no AAVSO check.
- **Time:** planned 7 h (without the deploy), actual __ h. Re-type `measure()` in `lightcurve.py` myself.

### [Friend's name] (validation and research, from 31 Oct)
Write findings in [`REVIEW_NOTES.md`](REVIEW_NOTES.md); this log is for what you learned.
- **Learned:**
- **Checked (Part C of the review guide):**
- **Research answered (Part D):**
- **Time:** __ h
