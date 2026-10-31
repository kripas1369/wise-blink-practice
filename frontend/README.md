# Frontend (Kripas)

Plain HTML, CSS and JavaScript modules. No build step.

## Run

With the API (any typed position works; from the repo root, venv active):

```bash
uvicorn backend.app.main:app --port 8000
# open http://localhost:8000
```

Without the API (the 5 prepared targets only):

```bash
cd frontend
python3 -m http.server 8000
```

The page asks `/api/health` once: if the API answers it uses `/api/frames`, `/api/gaia` and `/api/diff`, otherwise it reads the same files from `frames/`.
Opening `index.html` directly from the file system does not work (browsers block JavaScript modules there).

## Test

```bash
cd frontend
npm test        # node --test, needs Node 20+; no packages to install
```

## Files

| File | What it does |
|---|---|
| `index.html` | Page layout: search panel, target buttons, sky map, SPHEREx flipbook, Before / After / Difference |
| `css/style.css` | Dark theme, phone layout under 900 px, focus outlines |
| `js/app.js` | Wires everything: search, targets, URL, Aladin sky map |
| `js/coords.js` | Reads `17h57m48s +04d41m36s`, `17:57:48 +04:41:36` or degrees |
| `js/motion.js` | Moves a star from 2000 to 2026 with its proper motion |
| `js/targets.js` | The 5 official targets (SIMBAD positions and motions) |
| `js/resolve.js` | Star name → position through SIMBAD (Harvard mirror first, CDS second) |
| `js/urlstate.js` | `?ra=&dec=&fov=&det=` share links |
| `js/flipbook.js` | The flipbook panel: play, step, blink, flags overlay, Gaia markers, labels, honest messages; asks again every 10 s while the API prepares a new position |
| `js/frames.js` | Loads and checks the manifest from the API or from `frames/` (format: [`docs/plan/FRAMES_FORMAT.md`](../docs/plan/FRAMES_FORMAT.md)); also `gaia.json`, `diff.json` and `lightcurve.json` |
| `js/diffview.js` | Before / After / Difference: visit pickers, same-pixel cursor in all three panels, read-out, warnings |
| `js/lightcurve.js` | Light curve: brightness over time (coloured by wavelength) and against wavelength (one colour per visit) as SVG, same-wavelength comparisons, warnings; a clicked flipbook pixel via `/api/lightcurve?…&x=&y=` (API only) |
| `js/sky.js` | Pixel ↔ sky maths, which Gaia stars to show, the target's expected shift and its compass direction |
| `js/player.js` | Stepping, looping and speed rules (tested) |
| `frames/` | Real SPHEREx frames per target and detector, made by `backend/app/render.py`, plus `gaia.json`, `diff.json` and `epoch<i>.fits` (format: `docs/plan/FRAMES_FORMAT.md`) |

## Outside services (all free, no login)

- Aladin Lite 3.8.2 from jsDelivr (unpkg as backup). The npm build is an ES module, so it is loaded with `import()`.
- Background maps from ESA ESASky (`skies.esac.esa.int`). The IRSA copies have no CORS header, so the WebGL map cannot use them.
- SIMBAD TAP: `simbad.harvard.edu` first, `simbad.cds.unistra.fr` second.

If the map cannot load, search, targets and share links still work and the page says so.
