# 08. Day 1 website: what Kripas built and how it works

Code: `frontend/` on branch `kripas-frontend`. Run: `cd frontend && python3 -m http.server 8000`, open http://localhost:8000. Tests: `npm test`.

## What the page does
1. **Search box:** type a name (`Barnard's Star`, `M31`, `R Dra`) or a position (`17h57m48s +04d41m36s`, `17:57:48 +04:41:36`, `269.45 4.69`).
2. **Field of view slider** (1–15′, default 3′) and **detector menu** (D1–D6 with their wavelength ranges). Both only matter from Day 2, when the flipbook arrives.
3. **5 target buttons:** one click moves the map to the star *as it is in 2026* and picks the best detector (D6 for WISE 0855, D2 for the rest).
4. **Sky map (Aladin Lite):** a real sky picture with a yellow square = the area the flipbook will show. Click the sky to pick a position; drag to pan.
5. **Share link:** the address bar always holds `?ra=&dec=&fov=&det=`. Paste it anywhere and the same view opens.

## How one search travels through the code
```
form submit  → search(text)                     app.js
  exact target name?  → chooseTarget()          targets.js + motion.js
  numbers?            → parseCoordinates()      coords.js
  a name?             → resolveName()           resolve.js  (SIMBAD over the internet)
                         + positionAt(…, 2000 → 2026)   motion.js
→ applyPosition()  → writeUrl()  (urlstate.js, history.replaceState)
                   → renderSelection()  (the "Your position" box)
                   → moveMap()  (Aladin gotoRaDec + setFoV + yellow square)
```

## Why each choice
| Choice | Reason |
|---|---|
| Move stars to 2026 with proper motion | Barnard's Star moved 270″ (4.5′) since 2000. With a 3′ square, the year-2000 position would miss it completely. |
| Name lookup from the browser, not our server | SIMBAD allows it (CORS `*`), so Day 1 needs no backend. Harvard mirror first because the main CDS server was down on 29–31 Oct. |
| Aladin loaded with `import()` | The npm build of Aladin 3.8 is an ES module; a plain `<script>` tag gives no `A` object. |
| Background maps from ESA ESASky | The map draws with WebGL, which needs CORS headers on every image. IRSA's copies have none; ESASky's do; CDS was unreachable. |
| Text from SIMBAD inserted with `textContent` | Never paste outside text as HTML (it could contain code). |
| Version counter in `search()` | If SIMBAD answers slowly and you click the map meanwhile, your newer choice wins. |
| Ignore presses that moved more than 5 px | The end of a drag is not a click. |

## What we saw (real, Day 1)
- The target buttons land within 0.1″ of the positions the Python backend searched (`tests/motion_targets_url.test.js`).
- On the 2MASS map (taken 1997–2001) Barnard's Star sits about 4.5′ south of today's position: `notes/screenshots/day1_mobile_barnard_offset.png`. This is the story's first proof.
- Clicking the bright star next to Epsilon Indi B's square gave RA 331.04499, Dec −56.78308: within about 2″ of its year-2000 catalogue position (331.044147, −56.782844).

## Re-type exercise (Kripas)
1. Close `coords.js`. Write `parseCoordinates` again from this description: RA is in hours when written with h/m/s, colons or as 6 numbers; 2 plain numbers are degrees; Dec keeps its sign even when degrees are `-00`; reject minutes/seconds ≥ 60, RA outside 0–360, Dec outside ±90. Run `npm test`.
2. Same for `buildUrlState` / `readUrlState` in `urlstate.js`.
3. Explain out loud: why does the yellow square look empty for Barnard's Star on the 2MASS map?
