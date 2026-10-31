# [Friend's name]: Day 2 step by step (data side)

**Your role:** data and science. **Your branch:** `friend-backend`. **Your folder:** `backend/`.
**Today's goal:** turn raw SPHEREx cutouts into clean, lined-up pictures, one per visit, that the website's flipbook can play. You write the real pipeline: `clean.py`, `align.py`, `render.py`.

**What Kripas already did (so you are not starting blind):**
- The website now has a working flipbook (play, step, blink two visits, flagged pixels in red, honest labels).
- To build it before your pipeline exists, he made **sample frames** from real data with the simplest honest method: one exposure per visit (`scripts/sample_frames.py`). They are in `frontend/frames/` for all 5 targets (Barnard D2, WISE 0855 D2 and D6, RW Aur D2, Eps Ind B D2, R Dra D2).
- The file format the website reads is fixed in [`FRAMES_FORMAT.md`](FRAMES_FORMAT.md). Your pipeline writes exactly that, so the website needs no change when your frames replace the samples.
- [`notes/DAY2_FINDINGS.md`](../../notes/DAY2_FINDINGS.md) lists what the samples showed, including 3 open questions for you.
- `scripts/compare_frames.py` compares your frames with the samples, so you can prove yours are right.

**Rule for today (same as Day 1):** write your own code from [`learning/04_whats_next.md`](../../learning/04_whats_next.md) and `FRAMES_FORMAT.md`. **Do not open `scripts/sample_frames.py`** until Step 7; it is the answer key for checking. Stuck for more than 20 minutes? Peek, close it, type the rest yourself, and write in the log where you got stuck.

Time: about 7 hours. Tick each box as you go.

---

## Step 0. Get today's code (10 min)

```bash
cd wise-blink-practice
git checkout friend-backend
git pull
git fetch origin
git merge origin/main          # brings in Kripas's Day 2 work (frames, compare script, these docs)
source .venv/bin/activate      # Win: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
```

- If `git merge` opens an editor, save and close it (the default message is fine).
- You should see the same test result as Day 1 (**`24 passed, 3 skipped`**). Your re-typed files from Day 1 stay.
- If `main` does not have the Day 2 work yet, use `git merge origin/kripas-frontend` instead and tell Kripas.

---

## Step 1. See the goal in the browser (15 min)

```bash
cd frontend
python3 -m http.server 8000        # Win: py -m http.server 8000
```

Open http://localhost:8000, click **Barnard's Star**, scroll down to **SPHEREx flipbook**.

- [ ] Press **Play**: 3 real SPHEREx visits (Aug 2025, Mar 2026, Aug 2026) of a 3′ square.
- [ ] Read the label under the picture: date, detector, the **wavelength at the star** (it changes between visits because of SPHEREx's LVF filter: 1.235, 1.314, 1.539 µm), exposures, % flagged.
- [ ] Tick **Show flagged pixels in red**.
- [ ] The striped pixels at the star's centre: the file has **no value** there (the star saturates the detector). Never paint those as black sky.
- [ ] Click **WISE 0855**, then switch the detector to D2. Read the orange box "Before you trust your eyes".

Stop the server with Ctrl+C and go back to the repo root (`cd ..`).

---

## Step 2. Read first (45 min)

1. [`learning/04_whats_next.md`](../../learning/04_whats_next.md), the Step 2a section, Problems 1–4 (clean, align, add up, honest brightness).
2. [`FRAMES_FORMAT.md`](FRAMES_FORMAT.md): every field you must write, the exact sky grid, and the PNG rules.
3. [`notes/DAY2_FINDINGS.md`](../../notes/DAY2_FINDINGS.md): real numbers from the samples and the open questions.
4. Words: [`learning/07_glossary.md`](../../learning/07_glossary.md) (reproject, WCS, coadd, sigma, LVF).

Answer out loud before coding:
- [ ] Why IMAGE − ZODI? (ZODI is the glow of dust in our solar system; it changes with the date, so without removing it the same sky looks brighter or darker in different visits.)
- [ ] Why reproject onto **one** grid? (Every exposure is turned a different way; only on one grid does "the same pixel" mean "the same place in the sky".)
- [ ] Why **one** brightness scale for all frames? (Otherwise a star looks brighter just because the scale changed.)
- [ ] Why is the sky grid centred on the **2026.0** position? (The website draws its ring there; both must agree.)

---

## Step 3. Epochs per detector (Block 1, about 1.5 h)

`archive.group_epochs(images)` already groups images into visits (30-day gap, 60-day maximum).

Write in `backend/app/archive.py` (or a new `backend/app/epochs.py`):

```python
def detector_epochs(ra: float, dec: float, detector: int) -> list[dict]:
    """Visits that have images in this detector, each with only this detector's images."""
```

Decide one thing and **write the reason in your log**: group *all* detectors first and then keep this detector's images, or keep this detector's images first and then group? They can give different visits. Kripas's sample does the second; for R Draconis it found only 3 D2 visits, while the Day 1 report found 9 epochs with all detectors. Which is right for the flipbook? (Open question 1 in `DAY2_FINDINGS.md`.)

Then check the observation time for 5 Barnard D2 images:
- [ ] `image.mjd` from the archive table vs `MJD-AVG` in the downloaded cutout's IMAGE header. Write the largest difference (in seconds) in the log. We use `MJD-AVG` in the frames.

Test (`backend/tests/test_epochs.py`, mark it network like `test_network.py`): Barnard D2 gives **3 visits**, in time order, every image has `detector == 2`.

---

## Step 4. `clean.py` (Block 2, about 2 h)

```python
def clean_cutout(path) -> dict:
    """image (IMAGE − ZODI), sigma (sqrt VARIANCE), bad (official mask), mjd (MJD-AVG), wcs,
    wl_um and bw_um at a given position (spectral WCS key "W"; None if missing)."""
```

Rules:
- `bad = (FLAGS & flags.bad_pixel_bitmask(header)) != 0`. SOURCE is a label, never a defect.
- Keep NaN as NaN. Do not replace it with 0 (that is how the black hole appeared in the first sample).
- Wavelength at the target: `WCS(header, fobj=hdul, key="W").pixel_to_world_values(x, y)` gives (wavelength, bandwidth) in µm at pixel (x, y). Get (x, y) from the sky WCS: `WCS(header).world_to_pixel_values(ra, dec)`.
- `pct_flagged` = flagged pixels / pixels inside the image × 100.

Tests (`backend/tests/test_clean.py`, **offline**): build a tiny fake cutout in the test with `astropy.io.fits` (IMAGE, FLAGS with `MP_*` keywords, VARIANCE, ZODI, each 5 × 5) and check:
- [ ] image equals IMAGE − ZODI exactly; sigma equals sqrt(VARIANCE);
- [ ] a pixel with a bad bit is `bad`; a pixel with only the SOURCE bit is **not** bad;
- [ ] a NaN pixel stays NaN.

Then one real check: clean a cached Barnard cutout and print `pct_flagged`. The sample has 4.0% for the Aug 2025 visit (exposure `2025W35_1A_0444_1`, detector 2). Write your number in the log.

---

## Step 5. `align.py` (Block 3a, about 1.5 h)

```python
def target_grid(ra, dec, fov_arcmin=3.0):   # -> (WCS, size); rules in FRAMES_FORMAT.md section 2
def align(cleaned: dict, grid, size) -> dict:   # image, sigma, bad, inside on the grid
```

Rules:
- `reproject_interp` for the image. For the bad mask use `order="nearest-neighbor"` (a mask is yes/no; do not blur it).
- The footprint from reproject is 0 **both** outside the exposure and at NaN pixels. To tell them apart, also reproject an array of ones: where that footprint is 1 but the image footprint is 0, the file has no value (`pct_no_value`).
- Download cutouts big enough: the grid's diagonal plus 5%, at least 0.08° (`download_cutout(image, ra, dec, size_deg)`). The default 0.05° is too small once the exposure is rotated, and corners come out empty.

Test (offline): make a fake image with one bright pixel and a WCS rotated 90°; after `align`, the bright pixel is where the sky position says (north up, east left).

**The alignment check that matters** (write the numbers in the log): in the Barnard D2 frames, the bright dot in the upper right is a background star. Its position (brightness-weighted centre of the 3 × 3 pixels around its peak) must be the **same pixel in every visit, within about 0.5 px**. If it moves, the alignment is wrong, and any "motion" we show is fake.

---

## Step 6. `render.py` (Block 3b, about 1 h)

```bash
python -m backend.app.render barnard 2 --out scratch/frames
```

It writes `scratch/frames/barnard/d2/manifest.json` plus `epoch<i>.png` and `epoch<i>_flags.png`, exactly as in `FRAMES_FORMAT.md`:
- `mode: "single"` first, choosing the **same exposure** as the sample (the one closest to the visit's mean time, skipping exposures where less than 90% of the grid is covered). Then Step 7 can compare pixel by pixel.
- One scale for all frames: the 1st and 99.5th percentile of the good pixels of **all** frames together.
- PNG: north at the top (`np.flipud`), alpha 0 where there is no value.
- `made_by: "backend/app/render.py"`. Every field from your data; if you do not know a value, write `null` and say so; never guess.

`scratch/` is ignored by git, so you can run it as often as you like.

---

## Step 7. Prove your frames are right (30 min)

```bash
python -m scripts.compare_frames frontend/frames/barnard/d2 scratch/frames/barnard/d2
```

You want: `grid centre differs by 0.000″`, one line per visit with **grey difference median 0.0** (at most 1) and **correlation above 0.99**, then `OK`.

If not, the usual causes:

| What you see | Likely cause |
|---|---|
| "grid centres differ" | a different position: use the SIMBAD position moved to 2026.0 (`motion.position_at`) |
| correlation low (near 0 or negative) | missing `np.flipud`, or `CDELT1` positive (the picture is mirrored) |
| correlation high, but median difference large | a different scale (per frame instead of all frames), or ZODI not subtracted |
| "no B frame within 2 days" | different visits: see Step 3 |

Now you may open `scripts/sample_frames.py` and compare the ideas. Different code is fine if the numbers agree and you can explain it.

---

## Step 8. Add up all exposures of a visit (stretch, about 1 h; this is Day 3 Block 1 started early)

Why it matters, with real numbers: in single D6 exposures, **WISE 0855 is not clearly seen** (2 to 5 sigma at the ring, not at the same spot each time; `DAY2_FINDINGS.md`). The challenge says it should be visible at 4–5 µm. An add-up of the visit's exposures is how we find out honestly.

```
weight = 1 / sigma²   (per pixel; 0 where bad or no value)
coadd  = sum(weight × image) / sum(weight)
sigma_coadd = 1 / sqrt(sum(weight))
```

- Write `mode: "coadd"`, `n_images` = exposures used, `mjd` = mean `MJD-AVG` of those exposures.
- Watch out: within one visit the **wavelength changes** between exposures (LVF). Write the range of `wl_target_um` you added up in the `method` text.
- Measure WISE 0855 D6 again: the peak at the ring in sigma (`(value − sky median) / noise`, noise = 1.4826 × median absolute deviation). Write the numbers in `DAY2_FINDINGS.md`. Only if it is clearly above 5 sigma, at the same spot in every visit, can we change the website note to "seen".

---

## Step 9. Replace the samples (20 min)

When Step 7 says OK for Barnard D2:

```bash
python -m backend.app.render barnard 2 --out frontend/frames
```

- Then rebuild `frontend/frames/index.json` (call `write_index()` from `scripts/sample_frames.py`, or your own version).
- Start the website again (Step 1) and check that the flipbook shows **your** frames: the "made by" in the note under the picture says `backend/app/render.py`.
- Then do the other targets: `wise0855 6`, `wise0855 2`, `rw_aur 2`, `eps_ind_b 2`, `r_dra 2`. Run them one at a time (IRSA says 503 if you download too much at once).
- If you have Node.js: `cd frontend && npm test` checks every manifest. If not, Kripas runs it on your pull request.

---

## Step 10. One open question (30 min, pick at least one)

From `DAY2_FINDINGS.md`:
1. **R Draconis visits:** 3 D2 visits in the sample, 9 epochs in the Day 1 report. Why? Which should the flipbook show?
2. **Epsilon Indi B, Apr 2026:** 30% of pixels flagged, against 1–9% in other visits. Which flag bits? (Count each bit in that cutout's FLAGS.) Is the exposure usable?
3. **The dot inside the WISE 0855 ring in D2:** about 9″ north-west of WISE 0855's 2026 position, fixed in all 4 visits, not in SIMBAD. What is it? Try Gaia DR3 around RA 133.7598°, Dec −7.2422°, radius 30″: IRSA TAP, table `gaia_dr3_source` (found on Day 0), same `CONTAINS(POINT(...), CIRCLE(...))` style as our image search. On 31 Oct, ESA's Gaia server timed out and IRSA answered 502 for Kripas, so retry later if that happens. SIMBAD had nothing within 29″.

Write what you found **with the query or numbers**, even if the answer is "still unknown".

---

## Step 11. Finish the day (20 min)

1. Learning log (`notes/LEARNING_LOG.md`, a new "Day 2, Sun 1 Nov, [Friend's name]" section): what you built, the numbers from Steps 3, 4, 5 and 7, what broke, planned vs actual hours.
2. Save to GitHub:
   ```bash
   git status                 # no .venv, cache, scratch or .fits files listed
   git add backend scripts frontend/frames notes docs
   git commit -m "Day 2 (friend): clean, align, render; frames match the sample; open question N answered"
   git push
   ```
3. Open a pull request `friend-backend` → `main`. Kripas reviews it and checks the flipbook.
4. 15-minute call with Kripas: show the comparer output and the background-star check. Agree on Day 3 (the API format, FACTS §7).

---

## Done when (Day 2 checklist)

- [ ] `clean.py`, `align.py`, `render.py` written by you, with offline tests that pass.
- [ ] Barnard D2: `compare_frames` says OK against the sample.
- [ ] Background star on the same pixel in every visit (within about 0.5 px); numbers in the log.
- [ ] Your frames are in `frontend/frames/` for at least Barnard D2 and play in the browser.
- [ ] At least one open question answered with evidence.
- [ ] Log written, pushed, pull request opened.
- Stretch: an add-up mode, and a WISE 0855 D6 measurement written down.

---

## If something goes wrong

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: reproject` or `PIL` | `pip install -r requirements.txt` with the venv active. |
| `NotInImage` from `download_cutout` | The position is outside that exposure (near its edge). Skip it and take the next exposure of the visit. |
| All-NaN or empty corners in the aligned image | The cutout is too small: use the diagonal + 5%, at least 0.08°. |
| The PNG looks upside down or mirrored | `np.flipud` before saving; `CDELT1` must be negative. |
| Everything is white or black | The scale: percentiles of the **good** pixels only (not flagged, not NaN). |
| IRSA `503` | Too many downloads at once. Wait a minute; never run two scripts at the same time. |
| The website shows "Could not load the SPHEREx frames: …" | Read the message: it names the field that breaks `FRAMES_FORMAT.md` (e.g. frames not in time order). |
| The website still shows the old frames | Hard reload: Cmd+Shift+R (Win: Ctrl+F5). |

Questions: ask Kripas, or ask the AI "explain this error" and paste the full error.
