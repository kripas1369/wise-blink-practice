# SPHEREx Blink (practice)

Practice build of our NASA Space Apps 2026 project, challenge **"Planet X and SPHEREx"**.
**Team Not42:** Kripas Khatiwada and [Friend's name] (`lazylog00`).

A public web tool: type RA/Dec or a star name, and see **real SPHEREx images of that patch of sky from different dates as a flipbook**, so moving and changing objects are easy to spot, with Gaia markers, a difference view and light curves as proof.

**Practice only.** Same data (SPHEREx), same 5 official targets and same features as the hackathon. On 14 Nov we write it again from memory in a new repo; nothing here is copied or submitted.

## Roles (from 31 Oct)
- **Kripas builds everything** (`frontend/` and `backend/`, branch `kripas-frontend`): website, data pipeline, API, deploy, the 30-second video and the pitch.
- **[Friend's name] validates and researches** (branch `friend-backend`): checks every number and picture against NASA's tools and documents, answers the open science questions, finds problems, suggests features. Start: [docs/plan/FRIEND_REVIEW_GUIDE.md](docs/plan/FRIEND_REVIEW_GUIDE.md); findings go to [notes/REVIEW_NOTES.md](notes/REVIEW_NOTES.md).

## The 4 days (Sat 31 Oct – Tue 3 Nov)
1. **Day 1:** find and get the data (query SPHEREx, cutouts, the 5 targets). Backend done: [notes/DAY1_REPORT.md](notes/DAY1_REPORT.md). Website done: [frontend/README.md](frontend/README.md).
2. **Day 2:** clean and line up the epochs; flipbook. Done: flipbook in `frontend/`, pipeline `python -m backend.app.render <target> <detector>`, findings in [notes/DAY2_FINDINGS.md](notes/DAY2_FINDINGS.md).
3. **Day 3:** compare epochs with proof (add-up, Gaia, difference); connect website and API.
4. **Day 4:** light curve, online, test the 5 targets.

## Read first
- **[Friend's name], start here: [docs/plan/FRIEND_REVIEW_GUIDE.md](docs/plan/FRIEND_REVIEW_GUIDE.md)** (what we built, how to check it, what to research). The old build guides (`FRIEND_DAY1_STEPS.md`, `FRIEND_DAY2_STEPS.md`) are reference only.
- Frames format (data side ↔ website): [docs/plan/FRAMES_FORMAT.md](docs/plan/FRAMES_FORMAT.md)
- **What we built and why, from the basics: [learning/README.md](learning/README.md)**
- Team plan: [docs/plan/HACKATHON_PLAN.md](docs/plan/HACKATHON_PLAN.md)
- Kripas's plan: [docs/plan/KRIPAS_PLAN.md](docs/plan/KRIPAS_PLAN.md)
- Friend's plan: [docs/plan/FRIEND_PLAN.md](docs/plan/FRIEND_PLAN.md)
- Facts sheet: [docs/plan/FACTS.md](docs/plan/FACTS.md)
- Lessons: [docs/learn/LEARN.md](docs/learn/LEARN.md)
- Branches: [CONTRIBUTING.md](CONTRIBUTING.md)
- Today's task: `notes/DAY<N>_GUIDE.md`; daily notes: [notes/LEARNING_LOG.md](notes/LEARNING_LOG.md)

## Layout
- `backend/app/`: Python code (archive search, cutouts, flags, star motion, clean, align, add-up, render; FastAPI later).
- `backend/tests/`: pytest tests (`RUN_NETWORK=1` for the ones that call real servers).
- `scripts/day1_report.py`: coverage report for the 5 targets (`python -m scripts.day1_report`).
- `learning/`: explanations of everything we built, what comes next, NASA tools review, how to win.
- `frontend/`: plain HTML/JS page with Aladin Lite and the flipbook.
- `docs/`: plans, facts sheet, lessons. `notes/`: daily guides and the learning log.

## Setup (backend)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest backend/tests -v
```

## Setup (website)
```bash
cd frontend
python3 -m http.server 8000   # open http://localhost:8000
npm test                      # needs Node 20+
```

## Data credits
NASA/IPAC Infrared Science Archive (SPHEREx), ESA Gaia DR3, CDS SIMBAD and Aladin, ESA ESASky (background map tiles), AAVSO.
