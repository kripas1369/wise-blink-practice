# Frontend (Kripas)

Plain HTML, CSS and JavaScript modules. No build step.

## Run

```bash
cd frontend
python3 -m http.server 8000
# open http://localhost:8000
```

Opening `index.html` directly from the file system does not work (browsers block JavaScript modules there).

## Test

```bash
cd frontend
npm test        # node --test, needs Node 20+; no packages to install
```

## Files

| File | What it does |
|---|---|
| `index.html` | Page layout: search panel, target buttons, sky map, flipbook placeholder |
| `css/style.css` | Dark theme, phone layout under 900 px, focus outlines |
| `js/app.js` | Wires everything: search, targets, URL, Aladin sky map |
| `js/coords.js` | Reads `17h57m48s +04d41m36s`, `17:57:48 +04:41:36` or degrees |
| `js/motion.js` | Moves a star from 2000 to 2026 with its proper motion |
| `js/targets.js` | The 5 official targets (SIMBAD positions and motions) |
| `js/resolve.js` | Star name → position through SIMBAD (Harvard mirror first, CDS second) |
| `js/urlstate.js` | `?ra=&dec=&fov=&det=` share links |

## Outside services (all free, no login)

- Aladin Lite 3.8.2 from jsDelivr (unpkg as backup). The npm build is an ES module, so it is loaded with `import()`.
- Background maps from ESA ESASky (`skies.esac.esa.int`). The IRSA copies have no CORS header, so the WebGL map cannot use them.
- SIMBAD TAP: `simbad.harvard.edu` first, `simbad.cds.unistra.fr` second.

If the map cannot load, search, targets and share links still work and the page says so.
