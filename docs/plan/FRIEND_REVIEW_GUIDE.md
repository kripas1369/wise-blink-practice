# [Friend's name]: review guide (what we built, how to check it, what to research)

**Your role from 31 Oct:** you do not have to write code. Kripas builds everything (website and data code, now and on all future days). You are our **checker and researcher**:

1. **Check** that every number and picture is true (Part C).
2. **Research** the open questions (Part D).
3. **Find problems**: wrong, unclear, overclaimed, slow or fragile things (Part E).
4. **Suggest new things** that would help users or judges (Part F).

Write what you find in [`notes/REVIEW_NOTES.md`](../../notes/REVIEW_NOTES.md) (Part G). Your own rule guides everything: **no fake, no hype, only ground truth.**

Time: as much as you like. Part B + C1–C4 take about 1 hour and are the most useful start.

---

## Part A. What we built, in simple words

### The idea
SPHEREx is a NASA space telescope that photographs the whole sky again and again (each spot about every 6 months), in 102 colours of infrared light. Our tool lets anyone type a sky position (or pick one of the challenge's 5 targets) and **see SPHEREx's pictures of that spot from different dates as a flipbook**, so things that move or change stand out. That is how Pluto was found in 1930 ("blinking" two photos).

### Day 1 (done, 31 Oct)
| What | In simple words | Where |
|---|---|---|
| Archive search | Asks NASA's archive (IRSA) which SPHEREx pictures cover a position, using the picture outlines (`s_region`), only the 4 science collections | `backend/app/archive.py` |
| Star motion | Stars move a little each year; we move the catalogue position (year 2000) to 2026 before searching | `backend/app/motion.py` |
| Name lookup | "Barnard's Star" → position, from SIMBAD (with a backup server) | `backend/app/resolve.py` |
| Bad pixels | Reads which pixels are bad from each file's own header (two release formats) | `backend/app/flags.py` |
| Coverage report | How many pictures and visits exist for the 5 targets | [`notes/DAY1_REPORT.md`](../../notes/DAY1_REPORT.md) |
| Website | Search box, sky map (Aladin) with a ring on the target, 5 target buttons, shareable link | `frontend/` |

![Barnard's Star at its 2026 position](../../notes/screenshots/day1_barnard_2026_position.png)

### Day 2 (done, 31 Oct)
| What | In simple words | Where |
|---|---|---|
| Flipbook | Plays the visits in time order; ◀ ▶, slider, speed, loop, arrow keys | `frontend/js/flipbook.js` |
| Blink | Swaps two chosen visits quickly (the Pluto method) | same |
| Honest label | Under each picture: date, detector, the **wavelength at the star**, how many exposures, % bad pixels, % with no value | `frontend/js/frames.js` |
| Overlays | Ring on the target, N/E arrows, 1′ scale bar, bad pixels in red (toggle), stripes where the file has no value | `frontend/` |
| Orange warnings | "Before you trust your eyes": measured cautions per target | `backend/app/frame_notes.py` |
| Data pipeline | Raw pictures → clean (subtract the zodiacal glow, mark bad pixels) → line up on one north-up grid → **add up** the exposures of each visit (less noise) → PNG + `manifest.json` | `backend/app/clean.py`, `align.py`, `coadd.py`, `render.py` |
| Tests | 9 pipeline tests on fake files, plus the Day 1 tests and the website tests | `backend/tests/`, `frontend/tests/` |

![Barnard's Star add-up in the flipbook](../../notes/screenshots/day2_barnard_d2_coadd.png)

![WISE 0855 in D6, add-up of 21 exposures](../../notes/screenshots/day2_wise0855_d6_coadd.png)

**Findings so far** (numbers and method in [`notes/DAY2_FINDINGS.md`](../../notes/DAY2_FINDINGS.md)):
- The bright dot inside the WISE 0855 ring in D2 (1–1.6 µm) is **not** WISE 0855: it does not move in a year. What it is: unknown.
- WISE 0855 in D6 (4.4–5.0 µm): **not seen in single exposures** (2–5σ); in the **add-ups** a source appears at the ring in the two big visits (11 and 13σ by the file's own noise, still 6–9σ in each half of the exposures), but only 2.4σ in the first visit (3 exposures). Its brightest pixel moved 1 pixel west between Nov 2025 and Apr 2026, the direction WISE 0855 moves. Whether that source really is WISE 0855 is **not proven yet** (Part D, question 1).
- The add-ups mix exposures at different wavelengths (each label shows the range), so they show *where* things are, not *how bright* they got.
- R Draconis still shows single exposures: IRSA's search for its 2,483 images kept timing out on 31 Oct.
- Saturated star centres (Barnard, R Dra) have no value; shown striped, never as dark sky.
- Each exposure sees a slightly different wavelength (SPHEREx's filter changes across the detector), so **brightness changes between frames are not claimed**.

### Day 3 (done, 31 Oct)
| What | In simple words | Where |
|---|---|---|
| Gaia markers | Circles where ESA's Gaia catalogue says each star should be on each visit's date (moved from 2016 with its proper motion). The target is yellow, with dots for its other visits. | `backend/app/gaia.py`, `frontend/js/flipbook.js` |
| Before / After / Difference | Two visits side by side and their difference in σ (orange = brighter, blue = fainter). The pair with the closest wavelength is chosen first. Hovering shows the same sky pixel in all three panels, with its value, noise and σ. | `backend/app/diff.py`, `frontend/js/diffview.js` |
| Data files | The real values behind each picture (`epoch<i>.fits`), so the difference is not computed from 8-bit PNGs | `backend/app/rebuild.py` |
| API | One server for the website and the data: name lookup, coverage, frames, Gaia, difference. Any typed position starts a job that downloads and adds up the pictures (a few minutes). | `backend/app/main.py`, [`FACTS.md`](FACTS.md) §7 |
| Motion check | Measures where the target is in each visit and prints it next to Gaia | `scripts/measure_motion.py` |

![Barnard's Star, last visit: on its Gaia marker](../../notes/screenshots/day3_barnard_gaia_visit3.png)

![Barnard's Star: Before / After / Difference](../../notes/screenshots/day3_barnard_before_after_difference.png)

**Findings** (all numbers and method in [`notes/DAY3_FINDINGS.md`](../../notes/DAY3_FINDINGS.md)):
- Barnard's Star: its saturated (striped) centre moved **1.59 px north**; Gaia says 1.67 px. Epsilon Indi B moved **0.99 px south-east**; Gaia says 1.09. RW Aurigae (does not move) moved 0.07 px: our alignment is good to under 0.1 px.
- A bright star leaves a bright/dark pair in the difference **even when it does not move** (RW Aur). So we call a pair "motion" only when it matches Gaia in direction and size.
- Barnard's difference scatters 7.9× more than the file noise predicts; the website warns about it.
- WISE 0855 is not in Gaia (too faint in visible light), so it has no Gaia marker.
- The R Dra add-up is made but not shown: its bright core makes the one linear brightness scale useless (Day 4: non-linear scale). *Day 4: now shown with an asinh scale.*

### Day 4 (done 31 Oct, not online yet)
| What | In simple words | Where |
|---|---|---|
| Light curve | The target's brightness in **every single exposure** (not the add-ups), each with its own wavelength: a 2-pixel circle that follows the star, minus the sky. Visits are compared only at the same wavelength. | `backend/app/lightcurve.py`, `frontend/js/lightcurve.js` |
| Field-star floor | Stars that should not change, measured the same way: how big a change must be before we believe it | same |
| Click a pixel | With the API running, click any flipbook pixel to get its light curve | `/api/lightcurve?…&x=&y=` |
| asinh scale | R Dra's add-up shown so that both the faint halo and the bright core are visible; grey is then not proportional to brightness (the page says so) | `render.py --stretch asinh` |
| C4 tests | The plan's acceptance tests run on all 5 targets | `scripts/acceptance.py`, `notes/acceptance_c4.json` |

![RW Aur: brightness against wavelength, one colour per visit](../../notes/screenshots/day4_rw_aur_wavelength.png)

**Findings** (all numbers and method in [`notes/DAY4_FINDINGS.md`](../../notes/DAY4_FINDINGS.md)):
- **WISE 0855:** the D6 source moved 0.58 ± 0.12 px between Nov 2025 and Apr 2026; WISE 0855 should move 0.72 px (proper motion + parallax), a fixed star 0. In D2 nothing is at WISE 0855's position. So the D6 source moves like WISE 0855 (research question 1, see below).
- **The D2 dot** next to WISE 0855 is Gaia DR3 5756956644387831296 (G 16.31) (research question 2, answered).
- **Epsilon Indi B** is about 7× fainter at 1.36–1.40 µm than at 1.27 µm (its spectrum); at the same wavelength its visits agree within about 15%.
- **RW Aur** was 24% fainter in Sep 2025 than Sep 2026 at the same wavelength (one clean pair; 24–83% including pairs with flagged pixels).
- **Floor:** a steady star in the Barnard frame changes by 4.5% measured this way. Other frames have no such star.
- **Barnard's Star and R Dra:** no light curve (saturated core), with the reason on the page.
- **Not done:** AAVSO comparison (AAVSO and VizieR unreachable on 31 Oct); putting it online.

### Day 5 (done 31 Oct)
| What | In simple words | Where |
|---|---|---|
| Proof panel | The target's measured shift against Gaia's prediction, with a verdict, and what the data rests on (visits, exposures used of those taken, % flagged, which NASA data release) | `backend/app/proof.py`, `frontend/js/proof.js` |
| Spots above 5σ | Places in the difference that changed by more than 5σ, numbered on the picture, each with possible-artifact flags, the Gaia star behind it, and "what else could explain it / what would confirm it" | `backend/app/spots.py`, `frontend/js/spots.js` |
| Known-object check | A button that asks NASA JPL which known asteroids and comets were near a spot at that time, seen from SPHEREx: "matches X", "no match" (never "new object") or "check unavailable" | `backend/app/known_objects.py`, `/api/known-objects` |
| +/− buttons | Step the Before and After visits one at a time | `frontend/js/diffview.js` |
| About page | How we clean the data, what it cannot tell you, credits | `frontend/about.html` |

**Findings** (all numbers in [`notes/DAY5_FINDINGS.md`](../../notes/DAY5_FINDINGS.md)):
- Barnard's Star and Epsilon Indi B **agree** with Gaia (0.18 px apart in both). R Dra and RW Aur move less than 0.3 px according to Gaia, so the panel says **too small to test** instead of passing them. WISE 0855 is not in Gaia.
- The JPL check found **Ceres** at a test spot 7.2″ from Ceres's position (JPL: 10.1″, its error 13.2″). JPL's accurate "second pass" failed for every request on 31 Oct, so the site uses the rougher first pass and says so.
- **Not verified:** the sign of JPL's offsets (we assume east and north positive), and that SPHEREx's position in the file headers uses ICRF axes.

![Spot detail card](../../notes/screenshots/day5_spot_detail.png)

---

## Part B. Run it yourself (15 min)

```bash
git clone https://github.com/kripas1369/wise-blink-practice.git   # or: git pull
cd wise-blink-practice/frontend
python3 -m http.server 8000          # then open http://localhost:8000
```
Click **Barnard's Star**, scroll to **SPHEREx flipbook**, press Play, try Blink, "Show flagged pixels" and the Gaia markers, then scroll to **Before / After / Difference** and hover over the panels.

Optional (to run the data code, the API and the tests; Python 3.11+):
```bash
cd wise-blink-practice
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q                  # expect: 79 passed, 4 skipped
cd frontend && npm test              # expect: 41 pass (Node 20+)
cd .. && uvicorn backend.app.main:app --port 8000      # website + API; API docs at http://localhost:8000/api/docs
```
With the API running you can type any position (e.g. `133.8 -7.2`); the first time, it takes a few minutes to download the pictures.

---

## Part C. Check our claims (tick each, write what you see)

### C1. The number of pictures is NASA's, not ours
Open this link. It asks IRSA directly (without our code) how many science images cover Barnard's Star:

https://irsa.ipac.caltech.edu/TAP/sync?LANG=ADQL&FORMAT=csv&QUERY=SELECT%20COUNT%28%2A%29%20AS%20n%20FROM%20spherex.obscore%20WHERE%20CONTAINS%28POINT%28%27ICRS%27%2C269.446269%2C4.768204%29%2Cs_region%29%3D1%20AND%20obs_collection%20IN%20%28%27spherex_qr2%27%2C%27spherex_qr2_deep%27%2C%27spherex_qr3%27%2C%27spherex_qr3_deep%27%29

- [ ] It said **359** on 31 Oct (`notes/DAY1_REPORT.md`). A bigger number later is fine (new data each week); a smaller one is a problem.
- [ ] Also try IRSA's own [SPHEREx Data Explorer](https://irsa.ipac.caltech.edu/applications/spherex/) at `269.446269 4.768204`. If its count differs, find out why.

### C2. The ring is in the right place
- [ ] On the website, Barnard's Star: the ring should sit on the star in the sky map. Compare with SIMBAD's position and proper motion ([SIMBAD page](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=Barnard%27s+star)). The website says how far it moved since 2000 (about 270″).

### C3. The pictures are real SPHEREx data, lined up correctly
- [ ] Each `frontend/frames/<target>/d<detector>/manifest.json` says how it was made (`method`, `made_by`, `made_at`) and lists each visit's time, wavelength and exposure count.
- [ ] **North up, east left:** compare the flipbook frame with the Aladin map above it (same 3′ size): bright neighbour stars should be on the same side in both.
- [ ] **Same pixel = same sky:** blink the first and last visit of WISE 0855 D2. The background dot should not jump. Barnard's Star should move about 1.7 pixels north over a year (hard to see: its centre is saturated).

### C4. The labels are true
Pick one visit, e.g. Barnard D2 visit 1:
- [ ] The **date** comes from `MJD-AVG` (the time the picture was taken), never `DATE` (processing time). Download one exposure from the Data Explorer, open the header (e.g. with [astropy](https://docs.astropy.org/en/stable/io/fits/) or any FITS viewer), and check `MJD-AVG` is inside the visit.
- [ ] The **wavelength at the star** changes from visit to visit (e.g. Barnard 1.23 → 1.54 µm). Check this is expected: SPHEREx Explanatory Supplement, the "LVF" (linear variable filter) section.
- [ ] **% flagged:** our bad-pixel list is in `backend/app/config.py` (`BAD_FLAG_NAMES`). Compare with the Supplement's recommended flags. SOURCE must **not** be in the list (it marks a known object, not a defect).

### C5. The add-up is done right
- [ ] Read `backend/app/coadd.py` (30 lines) and its tests in `backend/tests/test_pipeline.py`. The rule: weight = 1 / variance, bad pixels get weight 0, noise of the result = 1 / √(sum of weights). Is this the standard method? (Any astronomy data-reduction text; the Supplement may recommend something.)
- [ ] `python -m scripts.compare_frames <folder A> <folder B>` compares two runs. Single-exposure mode gives exactly the old sample pictures (checked 31 Oct: grey difference 0, correlation 1.000).
- [ ] `python -m scripts.measure_ring frontend/frames/wise0855/d6` re-measures the WISE 0855 numbers in [`DAY2_FINDINGS.md`](../../notes/DAY2_FINDINGS.md) (offline, but only after the cutouts are in `cache/`, i.e. after running `python -m backend.app.render wise0855 6 --max-per-visit 21` once; that needs the internet and about 5 minutes).

### C6. Gaia markers and the difference (Day 3)
- [ ] **Gaia positions:** for Barnard's Star, open its [Gaia DR3 entry](https://gea.esac.esa.int/archive/) (source_id `4472832130942575872`) and compare `pmra`, `pmdec` with `frontend/frames/barnard/d2/gaia.json` (−801.55 and 10362.39 mas/yr). Do the same for Epsilon Indi B (`6412596012146801152`). Is Gaia's motion for Eps Ind B the brown-dwarf pair's motion, or only one of them?
- [ ] **Does the motion match?** Run `python -m scripts.measure_motion frontend/frames/eps_ind_b/d2` (offline) and compare with the table in `notes/DAY3_FINDINGS.md`. On the website, step through Barnard's visits with the Gaia markers on: does the striped centre sit on the yellow circle in each visit?
- [ ] **Difference maths:** read `difference()` in `backend/app/diff.py` (about 25 lines). z = (B − A − sky change) / √(σA² + σB²). Is subtracting the median sky change fair? Is 1.4826 × MAD the right "robust σ"?
- [ ] **Default pair:** the website picks the two visits with the closest wavelength. Check one by hand from the `wl_target_um` values in a manifest.
- [ ] **Errors:** with the API running, try `/api/frames?band=2` (no position), `/api/frames?target=pluto&band=2`, `/api/frames?ra=400&dec=0&band=2`. Each should give a plain `{"error": ...}` message, never made-up data.

### C7. The light curve and the C4 tests (Day 4)
- [ ] **Photometry maths:** read `measure()` in `backend/app/lightcurve.py` (about 18 lines). Is "sum inside a 2-pixel circle minus the median sky 10–14 px away" a fair method? Is 1 MJy/sr over one 6.15″ pixel = 0.889 mJy right? (Pixel solid angle in steradians × 10⁹.)
- [ ] **Same-wavelength rule:** pick two RW Aur exposures from `frontend/frames/rw_aur/d2/lightcurve.json` with nearly the same `wl_um` in different visits; divide their `flux_mjy` by hand and find the ratio in `same_wavelength.pairs`.
- [ ] **Eps Ind B spectrum:** on the website's brightness-against-wavelength chart, is it faintest near 1.36–1.40 µm? Is that where a T dwarf should be faint (water/methane bands; any brown-dwarf spectrum paper)?
- [ ] **WISE 0855 fit:** run `python -m scripts.acceptance` (offline) and compare the `wise0855` part with the table in `notes/DAY4_FINDINGS.md`. Check the proper motion (−8123.7, +673.2 mas/yr) and parallax (439.0 mas) against SIMBAD and Kirkpatrick et al. 2021 (ApJS 253, 7).
- [ ] **Coverage counts:** open the C1 link with two other positions (e.g. `200.0, -30.0` and `10.0, 60.0`); on 31 Oct IRSA said 378 and 410, the same as our search.
- [ ] **Honest "no light curve":** Barnard's Star and R Dra say why there is none. Does the reason make sense to you?

### C8. Proof panel, spots and the JPL check (Day 5)
- [ ] **Proof numbers:** the Barnard's Star proof panel says expected 1.67 px, measured 1.59 px. Compare with the C4 table in `notes/DAY4_FINDINGS.md` §3; they must be the same.
- [ ] **Data releases:** the panel says Barnard's 24 exposures come from `spherex_qr2` (16, released 2026-04-21) and `spherex_qr3` (8, released 2026-09-30). Check one exposure id from `frontend/frames/barnard/d2/exposures.fits` (or the flipbook label) at IRSA.
- [ ] **"Too small to test" is fair:** R Dra and RW Aur do not get a pass. Read `motion()` in `backend/app/proof.py`. Is 0.3 px a sensible floor? (Our alignment error is about 0.11 px; pixel phase adds more.)
- [ ] **Spot texts:** open three spots on different targets. Does any text say more than the data shows? Does any spot near a bright star blame a faint one?
- [ ] **JPL by hand (one case):** take Barnard's spot 1 (RA 17h57m47.10s, Dec +04°45′53.2″, 2025-08-26 11:57 UTC) and ask JPL yourself ([sb_ident docs](https://ssd-api.jpl.nasa.gov/doc/sb_ident.html)). Do you also get no known object within 12.3″?
- [ ] **JPL offset sign:** in JPL's documentation, is "Dist. from center RA" positive to the east? (Open item; we assumed yes.)
- [ ] **Spacecraft axes:** in the Explanatory Supplement, what frame are `X_SC`, `Y_SC`, `Z_SC` in when `XYZ_SC_SYSTEM = 'GEOCENTER'`? (We assumed ICRF.)

---

## Part D. Research questions (most important first)

1. **Is the D6 source at the WISE 0855 ring really WISE 0855?** In the add-ups it is 11 and 13σ in Nov 2025 and Apr 2026 (file noise; 15σ by the scatter method), and its brightest pixel moved 1 pixel **west** between those visits; WISE 0855 should move about 0.6 pixel west (8.1″ a year). That fits, but a brightest pixel is only a ±0.5 pixel position, and the D2 background object (question 2) is just 1 pixel away. Please find: WISE 0855's exact proper motion and parallax (SIMBAD and papers, e.g. Luhman 2014), what brightness SPHEREx should see at 4.4–5.0 µm (its Spitzer [4.5] / WISE W2 brightness), and whether the D2 background object is also bright at 4–5 µm (AllWISE W2 in Aladin). *Day 4: a Gaussian position fit shows the D6 source moves like WISE 0855 (0.58 ± 0.12 px against 0.72 px predicted with SIMBAD's motion and parallax; a fixed star would show 0). Still open: the expected [4.5] / W2 brightness, and whether the Gaia star adds light in D6 (a two-source fit gives it about a quarter of the flux at only 2.7–2.8σ).*
2. **The fixed dot inside the WISE 0855 ring in D2:** about **RA 133.7580°, Dec −7.2405°** (1 pixel west and 1 pixel north of the ring centre 133.759765°, −7.242186°). What is it? Try Gaia DR3 (IRSA table `gaia_dr3_source`, or the [ESA Gaia archive](https://gea.esac.esa.int/archive/)), 2MASS, WISE (in Aladin: add the catalogues). Note: our earlier note gave the ring centre as the dot's position; this is the corrected one. *Answered on Day 4: Gaia DR3 5756956644387831296, G 16.31, proper motion 6 mas/yr, 7″ west-north-west of the ring centre. Please confirm it in the ESA Gaia archive and say what kind of star it is if you can (colour, 2MASS/WISE brightness).*
3. **Epsilon Indi B, Apr 2026 visit (`2026W17_2A_0403_1`, D2): 30% of pixels flagged** in that exposure. Which flags (bits)? Is something wrong with that exposure, or is it normal (e.g. a nearby bright star, Epsilon Indi A)? (The add-up fills those pixels from the other 6 exposures, so the website frame is fine; the question is why it happened.)
4. **R Draconis:** the Day 1 report found 9 visits (all detectors together), the flipbook shows 3 in D2. Is that right? (Hint: the `_deep` collections near the ecliptic pole.) Also: IRSA's position search for R Dra (2,483 images) kept timing out on 31 Oct while smaller targets worked. Is there a faster way to ask (e.g. one detector at a time)?
5. **D2 wavelength range:** the files say 1.103–1.650 µm, our `config.DETECTORS` says 1.10–1.62. Which is right? (Explanatory Supplement, detector table.)
6. **Noise:** the file's own noise (from VARIANCE) gives smaller σ values than the pixel scatter (e.g. 11.1 vs 14.7). Lining up the pictures smooths neighbouring pixels, which lowers the scatter. Which should we quote? Is VARIANCE known to be over- or under-estimated?
7. **Is our "wavelength at the star" allowed?** Kripas's older prototype notes say the Explanatory Supplement calls the WCS-WAVE table "display-only". We use it for the wavelength in every label and will use it to pick visit pairs for the Difference view. Find the exact sentence (Supplement section and page) and what SPHEREx recommends instead, if anything.
8. **Known asteroids in the Difference view:** NASA JPL's Small-Body Identification API (`ssd-api.jpl.nasa.gov/sb_ident.api`) lists known asteroids and comets near a position at a time. Check whether it works for SPHEREx (Earth-orbiting telescope: which observer location code to use?) and how big a search box we need for 6.15″ pixels. *Day 5: built. SPHEREx's own position from the file headers is sent as the observer (JPL refuses the geocentre); tested on Ceres. Still open: the offset sign and the header axes (C8), and why JPL's second pass failed on 31 Oct.*
9. **Why does a star that does not move leave a pair in the difference?** RW Aurigae D2: −52σ / +71σ around the star, although Gaia says it moved 0.004 px and we measured 0.07 px. Candidates: a tiny alignment shift on a very bright star, the PSF changing across the detector, the wavelength changing between visits. Is there a SPHEREx document on PSF variation (Explanatory Supplement)? This decides how strongly we may say "this pair is motion".
10. **Display scale for very bright stars (R Draconis):** a linear scale makes everything but the core black. What do astronomers use for web previews (asinh, log, square root)? Is asinh "honest" if the scale is written next to the picture? *Day 4: we now use asinh (softening 0.002) for R Dra, with the formula in the manifest and a warning on the page. Is 0.002 a sensible choice?*
12. **AAVSO light curves for RW Aur and R Dra** (C4): AAVSO VSX and VizieR were unreachable from our machine on 31 Oct. Can you download AAVSO's light curves (J or H band if any, otherwise V) for Jun 2025 – Oct 2026 by hand? Did RW Aur brighten from Sep 2025 to Sep 2026? Where was R Dra in its 245-day cycle on our visit dates (Jun 2025, Dec 2025, Jun 2026)?
11. **NASA's own tools:** what can IRSA's SPHEREx tools already do that we also do? What can they **not** do that we do? (Start: [`learning/05_nasa_tools_review.md`](../../learning/05_nasa_tools_review.md).) This becomes a judge slide.

## Part E. Find problems (where to look)
- **Overclaiming:** any sentence on the website or in the docs that says more than the data shows. The orange notes on the website and `DAY2_FINDINGS.md` are the first place to look.
- **Numbers without a source:** any value you cannot trace to IRSA, SIMBAD, Gaia or a document.
- **Website:** try odd inputs (`0 0`, `400 100`, a made-up star name, a phone), slow internet, a different browser.
- **Docs:** anything a beginner would not understand.

## Part F. New ideas we want
Features, checks or explanations that would help a student, a citizen scientist or a judge. For example: what should the light curve (Day 4) show? Which other objects are good demos? Is there a better way to show the wavelength problem?

## Part G. How to report
1. Add an entry to [`notes/REVIEW_NOTES.md`](../../notes/REVIEW_NOTES.md) using its template (CHECK / PROBLEM / RESEARCH / IDEA; what, how, found, how sure).
2. Commit on your branch and open a pull request to `main`:
   ```bash
   git checkout friend-backend && git pull && git merge origin/main
   # edit notes/REVIEW_NOTES.md
   git add notes/REVIEW_NOTES.md && git commit -m "Review: <short title>" && git push
   ```
   Or just send it to Kripas; he will add it.
3. Kripas answers each entry (fixed, explained, or open). Please re-check the fixes.

## Part H. What comes next (Kripas builds, you check)
| Day | Kripas builds | You check |
|---|---|---|
| Day 3 (done 31 Oct) | Gaia markers, synced Before / After / Difference view, the API, motion measurements (Part A, Day 3) | Part C6; research questions 9 and 10 |
| Day 4 (done 31 Oct, except deploy) | Light curve per exposure, click a pixel, R Dra asinh scale, WISE 0855 position fit, C4 tests on the 5 targets (Part A, Day 4) | Part C7; research questions 1, 2, 10 and 12 |
| Day 4 leftovers | Deploy and phone check; PSF-fit positions; field-star floor outside the Barnard frame | Compare brightness with IRSA's Spectrophotometry Tool; test the public link on your phone |
| Day 5 (done 31 Oct) | Proof panel, spots above 5σ with known-object check (JPL), +/− visit buttons, About page (Part A, Day 5) | Part C8; research question 8 |
| Later | Spectrum panel (needs frames for the other detectors), video, pitch | Science text, references, limitations |
