# Kripas's personal plan (data and science lead)

Role: everything that touches the data. Finding images, downloading cutouts, cleaning, aligning, adding up, Gaia positions, light curves, spectra, and the science text. I hand the frontend clean JSON and PNGs that follow the API format in [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

Partner: [Friend's name] (frontend and presentation). See [FRIEND_PLAN.md](FRIEND_PLAN.md).

**Rule:** before 14 Nov I write code only for WISE/NEOWISE data. No SPHEREx code until the hackathon starts.

---

## Phases 0 + 1: Learn and build (29 Oct – 6 Nov), practice repo `wise-blink-practice`

**Each session (about 2.5 hours):** read the lesson (45 min) → the AI explains the step (15 min) → **I type the code myself** (60–90 min) → the AI reviews it (15 min) → 3 lines in `notes/LEARNING_LOG.md` → commit and push.

| Day | Learn | Build (I type it) | Done when |
|---|---|---|---|
| 1, Thu 29 Oct | Lessons 1–2 (sky coordinates, time) | Repo, venv, `requirements.txt`; `backend/app/coords.py`: parse `08h55m10.831s -7d14m42.53s` or degrees → (ra, dec); date → MJD | WISE 0855 gives RA ≈ 133.795°, Dec ≈ −7.245°; tests pass |
| 2, Fri 30 Oct | Lessons 3–4 (light, FITS) | `resolve.py` (SIMBAD name → RA/Dec, clear error); `archive.py` lists NEOWISE images covering Teegarden's Star (find the collection name) | Count matches IRSA's web search |
| 3, Sat 31 Oct | Lesson 5 (WCS) | One small cutout; print header; pixel ↔ sky; `images.py` saves a PNG with percentile stretch | The star sits where the WCS says |
| 4, Sun 1 Nov | Lessons 6–7 (SPHEREx, noise and flags) | Apply WISE `-msk` mask; % masked; `MJD_OBS`; frames for every visit; one stretch for all frames | About 20 visit PNGs, each with date and % masked |
| 5, Mon 2 Nov | Proper motion (Gaia `pmra`/`pmdec`, epoch 2016.0, `apply_space_motion`) | `gaia.py`: Gaia DR3 stars moved to each frame's MJD | Gaia marker on Teegarden's Star in first and last frames |
| 6, Tue 3 Nov | Variable stars, Miras, AAVSO (pick the Mira) | FastAPI `main.py`: `/api/resolve`, `/api/coverage`, `/api/frames`, `/api/gaia`; disk cache | JSON for Teegarden's Star in the browser |
| 7, Wed 4 Nov | Alignment and weighted means | `align.py` (`reproject`), 1/variance add-up per visit; API format call with [Friend's name] | **Teegarden's Star walks in the browser** |
| 8, Thu 5 Nov | Noise and sigma | `/api/diff` (B − A in sigma), `/api/lightcurve` | Mira curve roughly matches AAVSO |
| 9, Fri 6 Nov | — | Deploy; run the test list; lessons note; rehearsal checklist (Part D 2.5) | Public link works; note written |

The practice repo is never copied into the rehearsal or the hackathon.

---

## Phase 2: Rehearsal "WISE Blink" (Sat 7 – Sun 8 Nov, 48 hours), my tasks

| Hours | My task | I give to [Friend's name] | I need from [Friend's name] |
|---|---|---|---|
| 0–2 | Read the mock statement together; write the API format | API format document | Screen sketch |
| 2–10 | `/api/resolve`, `/api/coverage`, cutouts, mask and clean, PNG frames, `/api/frames` | 5 sample PNGs + sample JSON by hour 4 | — |
| 10 | **Checkpoint:** Teegarden's Star plays end to end | Working `/api/frames` | Flipbook calling it |
| 10–14 | Pre-cache all rehearsal targets; help with the first deploy | Cached data folder | Deploy link |
| 14–22 | Align frames to one grid; per-visit add-up (1/variance weighted); `/api/gaia` (positions per date) | Gaia JSON | Frame labels showing my numbers |
| 22 | **Checkpoint Level 1:** run the test list; write results; sleep shift | Test results | — |
| 22–34 | `/api/diff` in sigma; `/api/lightcurve` | Diff PNGs, light-curve JSON | Diff mode + chart |
| 34 | **Checkpoint Level 2** | — | — |
| 34–40 | Level 3 (only if Level 2 passes): W1 − W2 colour on click; measured motion vs Gaia | Colour JSON, motion numbers | Click handler |
| 40–46 | Limitations, references, data credits; fill the mock submission form | Text for the project page | Video draft to check the science |
| 46–48 | Pitch practice twice (I explain the science part) | — | — |

**My science checks in the rehearsal:**
- Teegarden's Star: measured shift within about 1 px of Gaia.
- Luhman 16: moves with Gaia; W1 − W2 is red.
- Proxima: saturation shown honestly.
- Mira: light-curve shape like AAVSO.
- Bad name gives an error, never a guess.

---

## Phase 2.8: Review (Mon 9 – Tue 10 Nov)
- Fill in my half of the lessons-learned note (planned vs actual hours for each backend task).
- Write the **1-page backend cheat sheet**: library names, IRSA endpoints, the query shape, cutout steps, the deploy command. Notes only, no code.
- Update Part E backend timings.
- Archive the rehearsal repo. Do not open it again.

---

## Phase 3: Final prep (Wed 11 – Fri 13 Nov)
- **Wed 11:** finish `FACTS.md`: SPHEREx band table, official flag list, `MJD-AVG`, `s_region` query, the 5 targets with coordinates and expected motion (from published papers, not code).
- **Thu 12:** **from-memory drill** (3 hours, WISE): empty folder → search → one cutout → PNG → API → deploy. Delete afterwards.
- **Fri 13:** read the Resources tab and Submission Guide with [Friend's name]; check IRSA is reachable from the venue or a hotspot; sleep early.

---

## Phase 4: Hackathon (Sat 14 – Sun 15 Nov), my tasks
Fresh empty repo. Follow HACKATHON_PLAN Part E, backend column:
- **0–2:** read the statement and resources; create the repo; API format.
- **2–10:** resolve, coverage (`s_region`), cutouts, official flag mask (SOURCE is a label only), IMAGE − ZODI, PNG frames with `MJD-AVG`, `/api/frames`. Sample frames to [Friend's name] by hour 4.
- **10–14:** Barnard's Star end to end; pre-cache the 5 targets.
- **14–22:** alignment, add-up per epoch and detector, `/api/gaia`.
- **22–26:** C4 acceptance tests on all 5 targets.
- **26–34:** `/api/diff` (sigma), `/api/lightcurve`.
- **34–40:** `/api/spectrum`, measured motion vs Gaia (only if Level 2 passes).
- **40–46:** limitations, references, NASA data section. **Submit by hour 46.**
- **46–48:** pitch practice.

## What I must never do
- Use `DATE` for time. Mask on SOURCE. Let SOURCE cancel a bad flag. Show a made-up value when something fails. Claim a discovery.
