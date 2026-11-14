# Kripas's tasks: Space Apps 2026, "Planet X and SPHEREx"

You own the **repo, the API (`backend/app/main.py`), the website (`frontend/`) and validation**. Govinda owns the pipeline (see `GOVINDA_TASKS.md`). You review and merge every pull request, by hand on GitHub.

The old repo `wise-blink-practice` is the reference. You copy files from it and change only what is listed here.

**Two repos, side by side.** Both of you clone `wise-blink-practice` and `blinkit` into the same parent folder. The prompts live here in `wise-blink-practice/docs/hackathon/` (one copy only; `git pull` at the start of every block). The agent is always opened in `blinkit`, where the old repo is `../wise-blink-practice`. All new code, branches and pull requests go to `blinkit`.

---

## B0, 11:15 to 11:30: create the repo (by hand)
1. **Ask the local lead** (message, keep the answer): "We practised on SPHEREx before the event in our own repo. May we reuse that code in our hackathon repo if we say so in the README?"
2. On GitHub, create the repo `blinkit`. Start it private; make it public before submitting. Add Govinda as a collaborator.
3. Clone it. The first push is code only, no docs or README: other folders appear when their first file is copied in (B1 and later).
4. Copy these from the old repo:
   - `requirements.txt` → `requirements.txt`
   - `frontend/package.json` → `frontend/package.json`
   - empty `backend/__init__.py` and `backend/app/__init__.py`
5. `.gitignore`:
   ```
   .venv/
   cache/
   .env
   __pycache__/
   node_modules/
   frontend/frames/
   ```
   `frontend/frames/` stays out of git until Phase 3 (the deploy decides how frames get to the server).
6. Do not copy the old frames. `blinkit` holds code only; frames are made fresh by Govinda's pipeline (B2 onwards).
7. Docs come later, each when it is first needed: `docs/VALIDATION.md` when the first block writes results (B1), `docs/FRAMES_FORMAT.md` when Govinda changes the manifest (B2, copied from the old `docs/plan/FRAMES_FORMAT.md` without section 16), the README in B5.
8. First commit and push (you, by hand). Tell Govinda to `git pull` in `wise-blink-practice` and in `blinkit`, then open `wise-blink-practice/docs/hackathon/GOVINDA_TASKS.md`.

**Git routine for every block (by hand):**
```
git checkout main && git pull
git checkout -b kripas/b1-api
# ... work, commit small steps in your own words ...
git push -u origin kripas/b1-api
# open the pull request on GitHub, review Govinda's PR, merge both on GitHub
```

---

## Port map (old repo → new repo)
**Yours:**

| Old | New | When | Change |
|---|---|---|---|
| `backend/app/main.py` | same | B1–B4, grows each block | remove the eclipse, methane and ask imports, routes and jobs; `_pipeline_after_render` lists only the steps already ported |
| `backend/app/resolve.py`, `targets.py` | same | B1 | none |
| `backend/tests/test_network.py` | same | B1 | none |
| `frontend/index.html` | same | B1 | remove: the `Eclipse mode` nav link, `#ask-view`, `#ch4-view`; leave `#sci-view`, `#iv-view`, `#lc-view`, `#spec-view` hidden until Phase 2 |
| `frontend/about.html` | same | Phase 3 | remove the Eclipse and Methane sections; add WiseView credit and AWS data source |
| `frontend/css/style.css` | same | B1 | none (do not copy `eclipse.css`, `methane.css`) |
| `frontend/js/coords.js`, `resolve.js`, `urlstate.js`, `targets.js`, `motion.js` | same | B1 | `urlstate.js`: more view keys (below) |
| `frontend/js/app.js` | same | B1–B4, grows | remove the imports of `ask.js`, `methane.js`, `eclipse.js`; add each panel when its block arrives |
| `frontend/js/frames.js`, `player.js`, `flipbook.js`, `sky.js`, `timeline.js` | same | B2 | none at first |
| `frontend/js/diffview.js`, `proof.js` | same | B4 | modes added |
| `frontend/js/lightcurve.js`, `spectrum.js`, `pixels.js`, `scientist.js` | same | P2-3 | live spectrum |
| `frontend/js/spots.js`, `spotEvidence.js`, `recovery.js`, `visitflip.js`, `files.js`, `planetx.js` | same | P2-4 | none |
| `frontend/tests/*.test.js` | same | with each file | skip `ask`, `methane`, `eclipse` tests |

**Not ported:** `eclipse*.py`, `eclipses.py`, `ask.py`, `rebuild.py`, `methane.py` (it becomes Govinda's `lens.py` in Phase 2), `eclipse.html`, `eclipse.js`, `ask.js`, `methane.js`, `eclipse.css`, `methane.css`.

---

# PHASE 1 (Sat): a flipbook for every detector

## B1, 11:30 to 13:30: API base, search, URL
**Build** (paste this into the agent, opened in `blinkit`):
```text
Block B1. Old repo: ../wise-blink-practice (read only, never edit it). New repo: this folder (blinkit).
1. Copy backend/app/resolve.py, targets.py and backend/tests/test_network.py unchanged.
2. Copy backend/app/main.py but keep only: imports that exist now (archive, config, coverage,
   motion, resolve, targets), ApiError/Working and their handlers, /api/health, /api/resolve,
   /api/coverage, and the StaticFiles mount of frontend/. Add GET /api/releases that returns
   archive.releases(). Remove everything about eclipse, methane, ask, frames jobs (added in B2).
3. Copy frontend/index.html and remove: the "Eclipse mode" nav link, the #ask-view section,
   the #ch4-view section. Copy css/style.css, js/coords.js, resolve.js, urlstate.js, targets.js,
   motion.js, and app.js with the imports of ask.js, methane.js, eclipse.js removed and every
   panel whose file is not here yet commented out with a TODO block name.
4. urlstate.js: the URL keeps ra, dec, fov, det plus mode (flip|blink|diff|stack|minus),
   a, b (visit ids), gaia, wise, flags (0/1), speed. Unknown values fall back to defaults with
   a visible message (as it already does for fov). Add tests to tests/motion_targets_url.test.js.
5. Search panel: add a second tab "Enter coordinates" with separate RA and Dec inputs, a unit
   switch (degrees / h:m:s and d:m:s), a live preview line ("= 269.452°, +4.693°") or a plain
   error ("Dec must be between -90 and +90"), using coords.js. Pasted text like
   "RA=133.79 Dec=-7.24" fills both fields.
6. Copy the frontend tests coords.test.js and motion_targets_url.test.js; npm test (in frontend/)
   must pass. Create docs/VALIDATION.md with a "B1" heading for the results.
```
**Review Govinda's `govinda/b1-data`:**
- [ ] `pytest backend/tests` passes on your machine.
- [ ] `config.COLLECTIONS` is QR3 + DR1, and `SPHEREX_COLLECTIONS` overrides it.
- [ ] VALIDATION.md "B1": the QR2 search returned 0 rows; Barnard's coverage per collection and detector; every image has an `s3_key`.
- [ ] No changes to your files (`main.py`, `resolve.py`, `targets.py`, `frontend/`).
- [ ] The study answers are in the pull request text, and they are right.

**Done when:** `/api/health`, `/api/resolve?name=Barnard's Star`, `/api/coverage?ra=..&dec=..` and `/api/releases` answer; the page loads with search, Aladin and the coordinate tab; the URL changes as you type.

Lunch 13:30 to 14:00.

## B2, 14:00 to 16:00: the flipbook
**Build:**
```text
Block B2. Copy from the old repo into main.py: PREPARED_DIR/JOBS_DIR constants, _official_positions,
_job_key, locate, the job pool (_pool, _jobs, _run_job, _run_official_prepare, job_status,
ensure_ready, _read), location() dependency and GET /api/frames. _pipeline_after_render must only
call steps that exist (none yet besides render; add gaia in B3, diff/proof/stack in B4).
Copy frontend/js/frames.js, player.js, flipbook.js, sky.js, timeline.js and their tests
(frames_player.test.js, timeline.test.js, the frames parts of day3.test.js). Wire them in app.js.
Test against the Barnard D2 frames Govinda makes in Part A of his B2 (not in git).
```
**Review `govinda/b2-frames`:**
- [ ] Barnard D2 frames in `frontend/frames/barnard/d2/` open in **your** flipbook.
- [ ] `manifest.json` has `release`, `flag_counts`, `pixel_source`, `collections_checked`, `newest_obs_date`, and FRAMES_FORMAT.md documents them.
- [ ] VALIDATION.md "B2": the S3 vs cutout max difference is 0 for 3 exposures; the timings at 3′, 10′, 20′ and 30′.
- [ ] `s3_reader.py` falls back to cutouts on error (ask him to show it by breaking the URL).

**Done when:** Barnard's Star plays (play, pause, step, speed, blink) and the frame label shows the date, detector and exposures.

## B3, 16:00 to 18:00: every detector, overlays, metadata
**Build:**
- D1–D6 buttons: each opens that detector's flipbook (all 30 folders exist after Govinda's B3).
- Frame label: date, detector, **wavelength range used** (`wl_target_range_um`), `n_images` of `n_images_in_epoch`, % flagged, **release badge**, and an `align_offset_px` warning above 0.5 px.
- Flags toggle and **flag legend** under the frame: name, pixel count (`flag_counts`), one-line meaning (from FACTS.md section 2). SOURCE is shown as "label, not a defect".
- `/api/gaia` and `/api/wise`; marker toggles in two colours.
- Aladin: Gaia DR3 (VizieR `I/355/gaiadr3`) and AllWISE (`II/328/allwise`) catalogue layers with on/off switches, plus the field-of-view square.
- Field of view up to 30′ (`FOV_MAX` in `urlstate.js` and the slider). Above 15′, show "slower: about N MB, about M min" using Govinda's B2 timings, and add a "Fast mover (30′)" preset.
- A "Data" panel from `/api/releases`: "Data as of …, releases: DR1 (…), QR3 (…)".
- Empty state ("SPHEREx has no images here yet") and error states with what to try next.

**Review `govinda/b3-targets`:**
- [ ] 30 folders; open 5 at random in your flipbook.
- [ ] `gaia.json` and `wise.json` load, and the markers sit on stars.
- [ ] VALIDATION.md "B3": the target × detector table, old vs new, QR2 vs DR1 on AWS.
- [ ] `pixel_source` is `aws-s3` everywhere (or S3 is moved to B4, with a note).

**Milestone (stop and check together at 18:00):** Barnard's Star plays in all 6 detectors from the URL `?ra=…&dec=…&fov=3&det=N`.

Break 18:00 to 18:30.

## B4, 18:30 to 20:30: add and subtract visits
**Build:**
- `/api/diff`, `/api/proof`, `/api/stack?visits=`; add `write_diff`, `write_minus_median`, `write_proof` and `write_stack` to `_pipeline_after_render`.
- Copy `diffview.js` and `proof.js` (and the matching tests in `day3.test.js` and `day5.test.js`).
- Flipbook mode switch: **Images / Minus median / Add visits / Difference**. "Add visits" shows checkboxes per visit and the stacked image with its noise ratio.
- The URL keeps the mode and the chosen visits.

**Review `govinda/b4-diff`:**
- [ ] Barnard's measured shift vs Gaia is within 0.5 px (VALIDATION.md "B4").
- [ ] The stack noise ratio is close to sqrt(number of visits).
- [ ] Minus-median frames: fixed stars mostly gone; Barnard's Star leaves a dark and bright pair.

## B5, 20:30 to 22:30: Phase 1 sign-off (your validation job)
For each of the 5 targets, in every detector D1–D6, check and tick in VALIDATION.md:
- [ ] **Barnard's Star:** walks about 1.7 px across the visits; the Gaia marker follows it.
- [ ] **WISE 0855:** faint or absent in D1–D3, visible in D5–D6; moves.
- [ ] **Epsilon Indi B:** small shift in the Gaia direction; separate from Epsilon Indi A.
- [ ] **RW Aur and R Dra:** brightness changes between visits. Check the frame's wavelength range first, because a different range can look like a change.
- [ ] **A random RA/Dec:** a job starts, shows progress, then plays.
- [ ] **An empty position** (for example an RA/Dec with no images yet): an honest "no data" message.
- [ ] `scripts/check_frames.py` (Govinda's) passes.
- [ ] Every frame has `pixel_source = aws-s3`.

Then:
- Put Govinda's measured detector ratings into `frontend/js/targets.js`.
- README draft:
  - what the tool does and how to run it;
  - data: SPHEREx from NASA IRSA, read from IRSA's public AWS copy; Gaia DR3 (ESA); CatWISE2020 and AllWISE; SIMBAD; Aladin Lite (CDS); astropy, astroquery, pyvo, reproject;
  - **AI disclosure:** "Code ported from our own pre-event practice repo; written with help from AI coding assistants."
- Merge, then tag `phase1` on GitHub.

---

# PHASE 2 (Sat night and Sun)

## P2-1, Sat 22:45 to 00:45: WiseView study
Fill in `blinkit/docs/WISEVIEW_STUDY.md` (Govinda copies it from `WISEVIEW_STUDY_TEMPLATE.md` in this folder). Your part is the **user experience**: the screen flow, defaults, how motion is made obvious, keyboard and mouse use, and what confuses a first-time user. Then do the same 3 targets in our tool and compare. Decide the adopt / adapt / skip table together.

## P2-2, Sun 07:00 to 09:00: signal-to-noise and the Six Eyes
- `main.py`: `JOB_EXPOSURES_PER_VISIT` → all exposures (the same cap as Govinda's).
- Each frame label shows "N exposures, noise X× lower than one exposure".
- `/api/bands`; the **Six Eyes flipbook** (6 small flipbooks D1–D6 playing in sync with the main player), the **colour flipbook**, and a Per-visit / Deep switch.
- The top "adopt" items from the WiseView study.

**Review `govinda/p2-snr`:** the measured gain is close to sqrt(n); WISE 0855 is red in colour.

## P2-3, Sun 09:00 to 11:00: live spectra and light curves
- `/api/lightcurve` (with x, y), `/api/spectrum?x=&y=` (live).
- Copy `lightcurve.js`, `spectrum.js`, `pixels.js`, `scientist.js` and their tests.
- Click a pixel: light curve plus spectrum, "computed live from N exposures", the 102-band binned view, a CSV download.
- A "Prepare all 6 detectors" button for typed positions (6 jobs, with progress).

## P2-4, Sun 11:00 to 13:00: creative band views (same order as Govinda's)
1. The 102-band contact sheet (6 × 17 tiles; clicking a tile opens that band).
2. The Spectral Lens: a slider snapping to the 102 bands ("Band 57 of 102: 3.30 µm, D4"), molecule presets with plain one-line explanations, and "a glow is a colour, not an identification".
3. The wavelength movie player.
4. The spectrum flipbook.
5. A "What moved?" list.
6. An "Explore" panel (famous objects), "?" tooltips, keyboard shortcuts (Space, ←/→, B, F, G, W, D).
7. Evidence panels (spots, JPL, planted movers, single exposures, GIF, IRSA links).

---

# PHASE 3 (Sun 13:00 to 22:00): see `PHASE3_SUBMIT.md`
