# SPHEREx Blink (practice)

Practice build of our NASA Space Apps 2026 project, challenge **"Planet X and SPHEREx"**.
**Team Not42:** Kripas Khatiwada and [Friend's name] (`lazylog00`).

A public web tool: type RA/Dec or a star name, and see **real SPHEREx images of that patch of sky from different dates as a flipbook**, so moving and changing objects are easy to spot, with Gaia markers, a difference view and light curves as proof.

**Practice only.** Same data (SPHEREx), same 5 official targets and same features as the hackathon. On 14 Nov we write it again from memory in a new repo; nothing here is copied or submitted.

## Roles
- **Kripas (data side, `backend/`, branch `kripas-backend`):** archive search, cutouts, cleaning images, lining up epochs, star motion from Gaia, the API.
- **[Friend's name] (website side, `frontend/`, branch `friend-frontend`):** search box, Aladin sky view, flipbook, buttons, charts, deploy, the 30-second video and the pitch.

## The 4 days (29 Oct – 1 Nov)
1. **Day 1:** find and get the data (query SPHEREx, cutouts, the 5 targets).
2. **Day 2:** clean and line up the epochs; flipbook.
3. **Day 3:** compare epochs with proof (add-up, Gaia, difference); connect website and API.
4. **Day 4:** light curve, online, test the 5 targets.

## Read first
- Team plan: [docs/plan/HACKATHON_PLAN.md](docs/plan/HACKATHON_PLAN.md)
- Kripas's plan: [docs/plan/KRIPAS_PLAN.md](docs/plan/KRIPAS_PLAN.md)
- Friend's plan: [docs/plan/FRIEND_PLAN.md](docs/plan/FRIEND_PLAN.md)
- Facts sheet: [docs/plan/FACTS.md](docs/plan/FACTS.md)
- Lessons: [docs/learn/LEARN.md](docs/learn/LEARN.md)
- Branches: [CONTRIBUTING.md](CONTRIBUTING.md)
- Today's task: `notes/DAY<N>_GUIDE.md`; daily notes: [notes/LEARNING_LOG.md](notes/LEARNING_LOG.md)

## Layout
- `backend/app/`: Python (FastAPI) code.
- `backend/tests/`: pytest tests.
- `frontend/`: plain HTML/JS page with Aladin Lite and the flipbook.
- `docs/`: plans, facts sheet, lessons. `notes/`: daily guides and the learning log.

## Setup (backend)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest backend/tests -v
```

## Data credits
NASA/IPAC Infrared Science Archive (SPHEREx), ESA Gaia DR3, CDS SIMBAD and Aladin, AAVSO.
