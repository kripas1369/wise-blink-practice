# WISE Blink (practice)

Learn-and-build practice for NASA Space Apps 2026, challenge "Planet X and SPHEREx".
**Team Not42:** Kripas Khatiwada and [Friend's name] (`lazylog00`).

A small web tool: type RA/Dec or a star name, and see WISE/NEOWISE images of that patch of sky from 2010 to 2024 as a flipbook, so moving and changing objects are easy to spot.

**Practice only.** This repo uses WISE/NEOWISE data, not SPHEREx. Nothing here is copied into the hackathon build on 14 Nov.

## Roles
- **Kripas (data side, `backend/`):** archive search, cleaning images, star motion from Gaia, the API.
- **[Friend's name] (website side, `frontend/`):** search box, Aladin sky view, flipbook, buttons, charts, deploy, the 30-second video and the pitch.

## Read first
- Team plan: [docs/plan/HACKATHON_PLAN.md](docs/plan/HACKATHON_PLAN.md)
- Kripas's plan: [docs/plan/KRIPAS_PLAN.md](docs/plan/KRIPAS_PLAN.md)
- Friend's plan: [docs/plan/FRIEND_PLAN.md](docs/plan/FRIEND_PLAN.md)
- Facts sheet: [docs/plan/FACTS.md](docs/plan/FACTS.md)
- Lessons: [docs/learn/LEARN.md](docs/learn/LEARN.md)
- How we work with branches: [CONTRIBUTING.md](CONTRIBUTING.md)
- Today's task: `notes/DAY<N>_GUIDE.md`; daily notes in [notes/LEARNING_LOG.md](notes/LEARNING_LOG.md)

## Layout
- `backend/app/`: Python (FastAPI) code for coordinates, archive queries, images, Gaia and the API.
- `backend/tests/`: pytest tests.
- `frontend/`: plain HTML/JS page with Aladin Lite and the flipbook.
- `docs/`: plans, facts sheet, lessons.
- `notes/`: daily guides and the learning log.

## Setup (backend)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest backend/tests -v
```

## Frontend
Open `frontend/index.html` in a browser (later it will be served by the backend).

## Data credits
NASA/IPAC Infrared Science Archive (WISE/NEOWISE), ESA Gaia DR3, CDS SIMBAD and Aladin, AAVSO.
