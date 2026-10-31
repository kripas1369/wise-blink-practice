# Kripas's personal plan (website and presentation lead)

Branch: `kripas-frontend`. Folder: `frontend/`.

**My job:** everything the user and the judges see. The website (search, Aladin sky view, flipbook, buttons, Gaia markers, difference view, charts, URL), the design, the deploy, the 30-second video, the project page and the pitch. Data comes from [Friend's name]'s API in the format of [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

**Partner:** [Friend's name] (GitHub `lazylog00`, data and science). See [FRIEND_PLAN.md](FRIEND_PLAN.md).

**Roles swapped on 31 Oct:** I now do the website; [Friend's name] does the data side. The Day 1 data code (made on 31 Oct before the swap) is handed to [Friend's name]; I still understand it well enough to explain it in the pitch ([`learning/01`](../../learning/01_day1_what_we_built.md) – [`03`](../../learning/03_archive_facts_and_mistakes.md)).

**We practise the real hackathon project:** SPHEREx data, the 5 official targets, the same features. On 14 Nov I write it again from memory in a new repo (no copying). I ask the Nepal local lead in writing whether this practice is allowed.

---

## Phase 1: 4-day practice build (Sat 31 Oct – Tue 3 Nov)
About 7 hours a day, in 3 blocks. For each block: the AI explains → **I type the code** → "review Day N block M" → commit. End of day: learning log, pull request `kripas-frontend` → `main`, 15-minute call with [Friend's name]. Read first: [`learning/00_big_picture.md`](../../learning/00_big_picture.md), [`05_nasa_tools_review.md`](../../learning/05_nasa_tools_review.md), [`06_how_to_win.md`](../../learning/06_how_to_win.md).

### Day 1, Sat 31 Oct: Step 1, find the data (website side)
- **Block 1 (2 h, with [Friend's name]):** walk [Friend's name] through the Day 1 data code and results (`learning/01`–`03`, `notes/DAY1_REPORT.md`). I need this to explain it in the pitch and to design the screens.
- **Block 2 (2.5 h):** `frontend/index.html` (plain HTML + JS):
  - search box (RA/Dec or a name), field of view (arcmin, default 3), Go button;
  - `?ra=..&dec=..&fov=..&det=..` in the URL fills the boxes; Go updates the URL without reloading (`URLSearchParams`, `history.replaceState`).
- **Block 3 (2.5 h):**
  - Aladin Lite v3: moves to the position with the field of view; clicking the sky fills the box.
  - 5 official target buttons (Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis), each with one line on what to look for (texts in `backend/app/targets.py`).
  - Write the 5 story beats (Part F) in `notes/STORY.md`.
- **Done when:** clicking "Barnard's Star" centres Aladin on it and the URL can be shared.
- **Status (31 Oct): done**, checked in the browser (laptop and phone width). Code in `frontend/` ([README](../../frontend/README.md)), 10 tests (`npm test`), story in [`notes/STORY.md`](../../notes/STORY.md), screenshots in `notes/screenshots/`. Block 1 (walking [Friend's name] through the data code) happens on our call.

### Day 2, Sun 1 Nov: Step 2a, the flipbook
- **Block 1 (2.5 h):** canvas flipbook: play, pause, step back/forward, speed, loop.
- **Block 2 (2 h):** blink mode (two chosen epochs swap quickly).
- **Block 3 (2.5 h):**
  - frame label: date, detector, wavelength range, number of images, % flagged;
  - detector buttons D1 – D6; flags overlay toggle (bad pixels in red);
  - load [Friend's name]'s real Barnard's Star PNGs + JSON.
- **Done when:** Barnard's Star frames play with correct labels.

### Day 3, Mon 2 Nov: Step 2b, compare with proof (integration day)
- **Morning call:** fix the API format with [Friend's name] (`docs/plan/FACTS.md` section 7).
- **Block 1 (2 h):** `fetch` from `/api/resolve`, `/api/coverage`, `/api/frames`; honest error messages (no fake values, no defaults, "no SPHEREx data here yet" when empty).
- **Block 2 (2.5 h):** Gaia markers on the flipbook from `/api/gaia` (each marker moves to its position for that epoch).
- **Block 3 (2.5 h):** difference mode (`/api/diff`) with a sigma colour scale and legend.
- **Done when:** **Barnard's Star walks across the browser flipbook onto its Gaia markers.**

### Day 4, Tue 3 Nov: connect, online, test
- **Block 1 (2 h):** click a star → light-curve chart (Chart.js) from `/api/lightcurve`, points coloured by wavelength.
- **Block 2 (3 h):** **deploy** (Render, Railway or a VPS) with [Friend's name]; check on a phone.
- **Block 3 (2 h):** run the C4 tests together on the 5 targets; lessons note.
- **Done when:** the public link works on laptop and phone, and all 5 target buttons load.

### Wed 4 – Fri 6 Nov
- **Wed 4 morning:** fix anything that failed on Day 4.
- **Wed 4 afternoon:** Level 3: spectrum panel (per epoch); **epoch picker (+/−)**; **proof panel** (expected vs measured motion, % flagged, images/epochs, "data as of"); About page (how we clean data, limitations, credits).
- **Thu 5:** draft 30-second video from the practice tool (Part F storyboard); pitch draft; find a public-domain Pluto discovery plate image. Evening: speed drill: empty folder → search → Aladin → flipbook on sample PNGs → deploy in 3 hours, from memory. Delete afterwards.
- **Fri 6:** rest; rehearsal checklist.

---

## Phase 2: Timed rehearsal of the real hackathon (Sat 7 – Sun 8 Nov, 48 hours), my column
Empty private repo `spherex-rehearsal`; build from memory and notes.

| Hours | My task | I give to [Friend's name] | I need from [Friend's name] |
|---|---|---|---|
| 0–2 | Read the challenge together; sketch the screens | Screen sketch | API format |
| 2–10 | Layout, search, URL, Aladin, flipbook on sample PNGs | — | Sample PNGs + JSON by hour 4 |
| 10 | **Checkpoint:** Barnard's Star plays end to end | Flipbook calling the API | Working `/api/frames` |
| 10–14 | **First deploy** | Deploy link | Cache |
| 14–22 | Detector buttons, frame labels, flags toggle, 5 target buttons, deploy again | Live link | Gaia JSON |
| 22–26 | C4 tests together; sleep shift | — | Results |
| 26–34 | Difference mode, Gaia markers, light-curve panel, Aladin Gaia and WISE overlays | — | Diff PNGs, light-curve JSON |
| 34–40 | Spectrum panel, epoch picker, proof panel, About page, polish (only if Level 2 passes) | — | Spectrum JSON |
| 40–46 | **30-second video**, project page, mock submission | Video draft | Science text, references |
| 46–48 | Pitch practice (I do the opening, demo and impact) | — | — |

**My checks:** works on a phone; a copied URL opens the same view; every number comes from the API; failures show an honest message.

## Phase 2.3 – 2.4: Mock judging and review (Sun 8 evening – Tue 10 Nov)
- Organise mock judging: 1 – 2 people, scores 1 – 5 on the 5 criteria, 3 questions each.
- My half of the lessons note (planned vs actual per frontend task, deploy problems).
- **1-page frontend cheat sheet:** Aladin calls, flipbook steps, URL handling, deploy steps. Notes only.

---

## Phase 3: Final prep (Wed 11 – Fri 13 Nov)
- **Wed 11:** final pitch script (3 – 5 minutes) and video storyboard.
- **Thu 12:** speed drill (3 hours) from an empty folder. Delete afterwards.
- **Fri 13:** read the Resources tab and Submission Guide with [Friend's name]; video tools ready (screen recorder, editor); sleep early.

---

## Phase 4: Hackathon (Sat 14 – Sun 15 Nov), my tasks
New empty repo; write it again (no copying). Follow HACKATHON_PLAN Part E, frontend column:
- **0–2:** read the statement and resources; screen sketch; API format.
- **2–10:** layout, search, URL, Aladin, flipbook on sample frames.
- **10–14:** Barnard's Star end to end together.
- **14–22:** detector buttons D1 – D6, frame labels, flags toggle, 5 target buttons, **deploy**.
- **22–26:** acceptance tests together.
- **26–34:** difference mode, Gaia markers, light-curve panel, Aladin Gaia and WISE overlays.
- **34–40:** spectrum panel, epoch picker, proof panel, About page, polish.
- **40–46:** **30-second video**, project page, submission form. **Submit by hour 46.**
- **46–48:** pitch practice; page pre-loaded; backup video ready.

## What I must never do
- Show a value that did not come from the data. Default to a constellation or date. Build a new feature after hour 40. Claim a discovery. Copy practice code into the hackathon repo.
