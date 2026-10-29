# [Friend's name]'s personal plan (web and presentation lead)

GitHub: `lazylog00`.

Role: everything the user sees and everything the judges see. The website (search, Aladin, flipbook, buttons, charts, URL), the deploy, the 30-second video, the project page and the pitch. Data comes from Kripas's API in the format in [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

Partner: Kripas Khatiwada (data and science). See [KRIPAS_PLAN.md](KRIPAS_PLAN.md).

**Rule:** before 14 Nov, practise only with WISE/NEOWISE data or dummy images. No SPHEREx code until the hackathon starts. The 3D globe stays in the old repo; we use Aladin Lite instead.

---

## Phase 1: 4-day learn-and-build sprint (Thu 29 Oct – Sun 1 Nov), practice repo `wise-blink-practice` (`frontend/`, branch `friend-frontend`)

**About 7 hours a day, in 3 blocks.** You build the frontend while Kripas builds the backend; both halves meet on **Day 3**. End of day: learning log, pull request into `main`, a 15-minute call with Kripas.

### Day 1, Thu 29 Oct: search page and sky view
- **Block 1 (2 h):** read `docs/plan/HACKATHON_PLAN.md`, lessons 1 and 6; write the 5 story beats (Part F) in your own words.
- **Block 2 (2.5 h):** `frontend/index.html`: search box (RA/Dec or name), field of view (arcmin, default 3), Go button; `?ra&dec&fov` fills the boxes; Go updates the URL (`URLSearchParams`, `history.replaceState`).
- **Block 3 (2.5 h):** embed Aladin Lite v3; it moves to the typed RA/Dec with the chosen field of view; clicking the sky fills the box.
- **Done when:** opening `index.html?ra=43.2537&dec=16.8814&fov=5` shows Aladin centred on Teegarden's Star.

### Day 2, Fri 30 Oct: the flipbook
- **Block 1 (2.5 h):** canvas flipbook on 5 dummy PNGs: play, pause, step back/forward, speed slider, loop.
- **Block 2 (2 h):** blink mode (two chosen frames swap quickly).
- **Block 3 (2.5 h):** frame label (date, band, number of images, % masked), W1/W2 buttons, mask toggle. Use Kripas's 5 real PNGs + JSON when he sends them.
- **Done when:** the flipbook plays Kripas's real Teegarden frames from files.

### Day 3, Sat 31 Oct: connect to the real API (integration day)
- **Morning call:** fix the API format in `docs/plan/FACTS.md` section 7 with Kripas.
- **Block 1 (2 h):** `fetch` from `/api/resolve`, `/api/coverage`, `/api/frames`; show honest error messages (no fake values, no defaults).
- **Block 2 (2.5 h):** Gaia markers on top of the flipbook from `/api/gaia` (each marker moves to its position for that frame's date).
- **Block 3 (2.5 h):** target buttons (Teegarden's Star, Luhman 16, Proxima, the Mira); pick the host (Render, Railway or a VPS) and test a deploy.
- **Done when:** **Teegarden's Star walks across the browser flipbook, sitting on its Gaia markers.**

### Day 4, Sun 1 Nov: difference, light curve, deploy, test
- **Block 1 (2 h):** difference mode (show `/api/diff` images, colour scale in sigma).
- **Block 2 (2 h):** Chart.js light curve when a star is clicked (`/api/lightcurve`).
- **Block 3 (3 h):** **deploy** with Kripas; run the test list (HACKATHON_PLAN Part D 2.4); check on a phone; lessons note.
- **Done when:** the public link works on laptop and phone.

### Mon 2 – Fri 6 Nov
- Mon 2: fix leftovers.
- Tue 3: About page, polish, Level 3 practice (colour-on-click panel).
- Wed 4: a practice 30-second video from the practice tool; pitch draft.
- Thu 5: 3-hour from-memory drill.
- Fri 6: rest; rehearsal checklist.

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
