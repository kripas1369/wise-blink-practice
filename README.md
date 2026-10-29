# WISE Blink (practice)

Learn-and-build practice for NASA Space Apps 2026 (Team Not42: Kripas Khatiwada and [Friend's name]).

A small web tool: type RA/Dec or a star name, and see WISE/NEOWISE images of that patch of sky from 2010 to 2024 as a flipbook, so moving and changing objects are easy to spot.

**Practice only.** This repo uses WISE/NEOWISE data, not SPHEREx. Nothing here is copied into the hackathon build.

## Layout
- `backend/app/`: Python (FastAPI) code for coordinates, archive queries, images, Gaia and the API.
- `backend/tests/`: pytest tests.
- `frontend/`: plain HTML/JS page with Aladin Lite and the flipbook.
- `notes/`: daily guides and `LEARNING_LOG.md`.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the tests
```bash
python -m pytest backend/tests -v
```

## Data credits
NASA/IPAC Infrared Science Archive (WISE/NEOWISE), ESA Gaia DR3, CDS SIMBAD and Aladin, AAVSO.
