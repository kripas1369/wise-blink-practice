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

### Day 1, Sat 31 Oct, [Friend's name]
- **Learned:**
- **Broke / confused me:**
- **Time:** planned 2.5 h, actual __ h

### Day 2, Sun 1 Nov, [Friend's name]
- **Learned:**
- **Numbers:** MJD-AVG vs archive time (Step 3): __ s; Barnard Aug 2025 % flagged (Step 4): __; background star position per visit (Step 5): __; compare_frames result (Step 7): __
- **Broke / confused me:**
- **Open question answered (Step 10):**
- **Time:** planned 7 h, actual __ h
