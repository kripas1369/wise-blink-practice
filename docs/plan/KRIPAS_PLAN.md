# Kripas's personal plan (data and science lead)

Role: everything that touches the data. Finding images, downloading cutouts, cleaning, aligning, adding up, Gaia positions, light curves, spectra, and the science text. I hand the frontend clean JSON and PNGs that follow the API format in [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

Partner: [Friend's name] (frontend and presentation). See [FRIEND_PLAN.md](FRIEND_PLAN.md).

**Rule:** before 14 Nov I write code only for WISE/NEOWISE data. No SPHEREx code until the hackathon starts.

---

## Phase 1: 4-day learn-and-build sprint (Thu 29 Oct – Sun 1 Nov), practice repo `wise-blink-practice`

**About 7 hours a day, in 3 blocks.** For each block: read the short lesson part → the AI explains the step → **I type the code myself** → the AI reviews it ("review Day N") → commit. End of day: learning log, pull request into `main`, a 15-minute call with [Friend's name].

### Day 1, Thu 29 Oct: coordinates, names, archive search
- **Block 1 (2.5 h):** lessons 1–2 → `backend/app/coords.py`. Done when the 12 tests in `backend/tests/test_coords.py` pass.
- **Block 2 (2 h):** lessons 3–4 → `resolve.py`: SIMBAD name → (ra, dec), with a clear error when not found, never a guess. Done when "Teegarden's Star" gives about 43.25°, +16.88°, and "notastar123" gives an error.
- **Block 3 (2.5 h):** `archive.py`: find the IRSA collection for NEOWISE single exposures; list images covering Teegarden's Star (count, dates, band). Done when the count matches IRSA's web search.

### Day 2, Fri 30 Oct: images, WCS, mask, frames
- **Block 1 (2 h):** lesson 5 → download one small cutout (image + mask); print the header; pixel ↔ sky.
- **Block 2 (2.5 h):** lesson 7 → apply the mask; % masked; read `MJD_OBS`; group exposures into visits (about every 6 months).
- **Block 3 (2.5 h):** `images.py`: one PNG per visit, with **the same stretch for every frame**. Send 5 PNGs + JSON to [Friend's name].
- **Done when:** about 20 real Teegarden PNGs exist, each with date and % masked, and the star moves between first and last.

### Day 3, Sat 31 Oct: Gaia, alignment, the API (integration day)
- **Morning call:** fix the API format in `docs/plan/FACTS.md` section 7 with [Friend's name].
- **Block 1 (2 h):** proper motion → `gaia.py`: Gaia DR3 stars near the target, moved from 2016.0 to each visit's MJD.
- **Block 2 (2.5 h):** `align.py`: put every visit on one grid (`reproject`); 1/variance-weighted add-up per visit.
- **Block 3 (2.5 h):** FastAPI `main.py`: `/api/resolve`, `/api/coverage`, `/api/frames`, `/api/gaia`, plus a disk cache.
- **Done when:** **Teegarden's Star walks across the browser flipbook, sitting on its Gaia markers.**

### Day 4, Sun 1 Nov: difference, light curve, deploy, test
- **Block 1 (2 h):** variable stars; pick the Mira (W1 fainter than about 8 mag) → `/api/diff` (B − A in sigma).
- **Block 2 (2 h):** `/api/lightcurve`; compare the Mira with AAVSO.
- **Block 3 (3 h):** deploy with [Friend's name]; run the test list (HACKATHON_PLAN Part D 2.4); write the lessons note.
- **Done when:** a public link works, Teegarden's Star and Luhman 16 move with Gaia, and the Mira curve roughly matches AAVSO.

### Mon 2 – Fri 6 Nov
- Mon 2: fix leftovers.
- Tue 3: Level 3 practice (W1 − W2 colour on click, measured motion vs Gaia).
- Wed 4: Supplement 2.2, 3.2.5, 3.2.9, 3.4.3; finish `FACTS.md`.
- Thu 5: 3-hour from-memory drill.
- Fri 6: rest; rehearsal checklist.

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
