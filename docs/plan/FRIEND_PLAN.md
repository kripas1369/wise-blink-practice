# [Friend's name]'s personal plan (web and presentation lead)

GitHub: `lazylog00`.

Role: everything the user sees and everything the judges see. The website (search, Aladin, flipbook, buttons, charts, URL), the deploy, the 30-second video, the project page and the pitch. Data comes from Kripas's API in the format in [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

Partner: Kripas Khatiwada (data and science). See [KRIPAS_PLAN.md](KRIPAS_PLAN.md).

**Rule:** before 14 Nov, practise only with WISE/NEOWISE data or dummy images. No SPHEREx code until the hackathon starts. The 3D globe stays in the old repo; we use Aladin Lite instead.

---

## Phases 0 + 1: Learn and build (29 Oct – 6 Nov), practice repo `wise-blink-practice` (`frontend/` folder)

Same repo as Kripas. You build the frontend while he builds the backend, so both halves meet on Day 7. Each session ends with 3 lines in `notes/LEARNING_LOG.md` and a commit.

| Day | Learn | Build (you type it) | Done when |
|---|---|---|---|
| 1, Thu 29 Oct | Read HACKATHON_PLAN; lessons 1 and 6; story beats in your own words | `frontend/index.html`: search box (RA/Dec or name), field of view; `?ra&dec&fov` fills the box | Copy-pasted link fills the box |
| 2, Fri 30 Oct | Aladin Lite v3: embed, `gotoRaDec`, survey, field of view, click event | Aladin moves to the typed RA/Dec; clicking the sky fills the box | Click gives correct coordinates |
| 3, Sat 31 Oct | Canvas drawing and timers | Flipbook on 5 dummy PNGs: play, pause, step, speed, blink two frames | All controls work smoothly |
| 4, Sun 1 Nov | Page state and buttons | Frame label (date, band, image count, % masked), W1/W2 buttons, mask toggle | Label changes with each frame |
| 5, Mon 2 Nov | Drawing markers from sky coordinates | Gaia markers on the flipbook from a JSON list | Markers follow their positions per frame |
| 6, Tue 3 Nov | `fetch`, JSON, error messages | Frontend calls Kripas's real API instead of dummy files; honest error messages | Teegarden's Star frames load from the API |
| 7, Wed 4 Nov | Pick a host (Render, Railway or a VPS) | End-to-end with Kripas; API format call | **Teegarden's Star walks in the browser** |
| 8, Thu 5 Nov | Chart.js | Difference mode; light-curve chart when a star is clicked | Chart shows real data |
| 9, Fri 6 Nov | Deploying | Deploy; test list with Kripas; lessons note; rehearsal checklist (Part D 2.5) | Public link works |

The practice repo is never copied into the rehearsal or the hackathon.

---

## Phase 2: Rehearsal "WISE Blink" (Sat 7 – Sun 8 Nov, 48 hours), your tasks

| Hours | Your task | You give to Kripas | You need from Kripas |
|---|---|---|---|
| 0–2 | Read the mock statement together; sketch the screens | Screen sketch | API format |
| 2–10 | Layout, search bar (RA/Dec or name), URL parameters, Aladin view, flipbook on sample PNGs | — | 5 sample PNGs + JSON by hour 4 |
| 10 | **Checkpoint:** Teegarden's Star plays end to end | Flipbook calling `/api/frames` | Working `/api/frames` |
| 10–14 | **First deploy** | Deploy link | Cached data folder |
| 14–22 | Band buttons, frame labels, mask toggle (bad pixels red), target buttons, deploy again | Live link for testing | Gaia JSON |
| 22 | **Checkpoint Level 1:** run the test list together; sleep shift | — | Test results |
| 22–34 | Difference mode, Gaia markers on the flipbook, light-curve panel, Aladin overlays | — | Diff PNGs, light-curve JSON |
| 34 | **Checkpoint Level 2** | — | — |
| 34–40 | Level 3 (only if Level 2 passes): colour on click panel, About page, polish | Click handler | Colour JSON |
| 40–46 | **30-second video** from the real tool; project page; mock submission | Video draft for Kripas to check | Science text, references |
| 46–48 | Pitch practice twice (you do the opening, demo and impact) | — | — |

**Your checks in the rehearsal:**
- Works on a phone screen.
- Copied URL opens the same view.
- Every number on screen comes from the API.
- When the API fails, an honest message is shown (no fake dates, no default values).

---

## Phase 2.7 – 2.8: Mock judging and review (Sun 8 evening – Tue 10 Nov)
- Organise mock judging: 1–2 people, scores 1–5 on the 5 criteria, 3 questions each.
- Fill in your half of the lessons-learned note (planned vs actual for each frontend task, deploy problems).
- Write the **1-page frontend cheat sheet**: Aladin calls, flipbook logic steps, URL handling, deploy steps. Notes only, no code.
- Archive the rehearsal repo. Do not open it again.

---

## Phase 3: Final prep (Wed 11 – Fri 13 Nov)
- **Wed 11:** pitch script (3–5 minutes) and the 30-second video storyboard (HACKATHON_PLAN Part F). Find a public-domain Pluto discovery plate image for the first 5 seconds.
- **Thu 12:** **from-memory drill** (3 hours): empty folder → search → Aladin → flipbook → deploy. Delete afterwards.
- **Fri 13:** read the Resources tab and Submission Guide with Kripas; prepare video tools (screen recorder, editor); sleep early.

---

## Phase 4: Hackathon (Sat 14 – Sun 15 Nov), your tasks
Fresh empty repo. Follow HACKATHON_PLAN Part E, frontend column:
- **0–2:** read the statement and resources; screen sketch; API format.
- **2–10:** layout, search, URL, Aladin, flipbook on sample frames.
- **10–14:** Barnard's Star end to end together.
- **14–22:** detector buttons D1–D6, frame labels, flags toggle, 5 target buttons, **deploy**.
- **22–26:** acceptance tests together.
- **26–34:** difference mode, Gaia markers, light-curve panel, Aladin Gaia and WISE overlays.
- **34–40:** spectrum panel, About page, polish.
- **40–46:** **30-second video**, project page, submission form. **Submit by hour 46.**
- **46–48:** pitch practice; page pre-loaded; backup video ready.

## What you must never do
- Show a value that did not come from the data. Default to a constellation or date. Build a new feature after hour 40. Claim a discovery.
