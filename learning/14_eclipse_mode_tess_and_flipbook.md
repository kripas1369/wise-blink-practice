# 14. Eclipse mode: how TESS's clock lines up SPHEREx photos into a flipbook (2-hour study)

Code: `backend/app/eclipses.py` (TESS catalogue, time, phase, which photos to download),
`backend/app/eclipse_depth.py` (normal brightness and dip depth), `backend/app/eclipse_build.py` (download,
measure, pictures, checks), `frontend/eclipse.html` + `frontend/js/eclipse.js` (the page).
Data: `frontend/frames/eclipse/tic219900027/eclipse.json`. Every number below comes from that file or from the code.

Run the site and open `http://localhost:8011/eclipse.html?tic=219900027` next to this file.

| Part | Topic | Time |
|---|---|---|
| 1 | The torch picture: what an eclipse is | 10 min |
| 2 | What TESS gives us: the clock | 15 min |
| 3 | Time: turning a SPHEREx time stamp into TESS's clock | 20 min |
| 4 | Phase: where the stars are in their circle (two real photos, worked by hand) | 20 min |
| 5 | Which photos we download, and why | 10 min |
| 6 | From photo to number: brightness, colour correction, baseline | 15 min |
| 7 | The flipbook, line by line | 15 min |
| 8 | Why the clock must be exact (try it on the page) | 10 min |
| 9 | Self-test | 5 min |

---

## Part 1. The torch picture (10 min)

- Two stars circle each other. From Earth they look like **one dot**.
- Seen edge-on, once per circle one star passes in front of the other: the dot gets dimmer. That is an **eclipse**; the drop is the **dip**.
- Two dips per circle:
  - **Primary (big) dip:** the hotter, brighter star is hidden.
  - **Secondary (small) dip:** the cooler, dimmer star is hidden.
- **How much light disappears tells you how bright the hidden star is.**
- A cooler star catches up in redder colours, so its dip grows towards the infrared. That is what SPHEREx can measure.

Our example, **TIC 219900027**:

| Quantity | Value |
|---|---|
| One circle (period P) | 0.5152647 days = 12.37 hours = 742.0 minutes |
| Big dip lasts | 0.157 of a circle = 1.95 hours |
| Small dip lasts | 0.109 of a circle = 1.35 hours |

---

## Part 2. What TESS gives us: the clock (15 min)

**TESS** is a NASA telescope that stared at the sky around the north ecliptic pole for most of a year (2018–19). It saw thousands of stars dip.

The **TESS-EBs catalogue** (Prša et al. 2022, ApJS 258, 16) lists each eclipsing pair with:

| Column (our name) | Meaning | TIC 219900027 |
|---|---|---|
| `period` | time for one circle | 0.5152647090536 d |
| `period_err` | how unsure that is | 0.00000079 d (0.07 seconds) |
| `bjd0` | one moment near a big dip, in BTJD (Part 3) | 1683.750362539 |
| `bjd0_err` | how unsure that is | 0.0000145 d (1.3 seconds) |
| `prim_pos` | exact place of the big dip relative to `bjd0`, as a fraction of a circle | 1.000134 |
| `prim_width`, `sec_width` | how long each dip lasts, as a fraction of a circle | 0.157, 0.109 |
| `prim_depth`, `sec_depth` | how deep each dip is in TESS's colour (0.6–1.0 µm) | 24.5%, 5.1% |

Together these numbers are called the **ephemeris**: a timetable of the dips. Think of it as a train timetable: "first train at 08:00, then one every 12 h 22 min".

**Where it lives in our code:** `eclipses.py`, `load_catalog()` downloads the CSV from MAST once and keeps it in `cache/catalogs/`. `by_tess_id("219900027")` returns one row as an `Ephemeris` object.

**Why near the north ecliptic pole?**
- TESS watched that region the longest, so its timings there are the most precise.
- SPHEREx's North deep field is centred on the same spot, so SPHEREx photographed it thousands of times.
- The catalogue has **112** usable pairs within 10° of the pole. TIC 219900027 is 3.13° from it.

**Is TESS's clock still good in 2026?** Small errors add up over many circles. The code checks:

```
drift (in circles) = (number of circles × period_err + bjd0_err) / period
```

For TIC 219900027 at the last SPHEREx photo this is **0.0079 of a circle, about 5.9 minutes**. The dip lasts 117 minutes, so the timetable is still good. Pairs whose drift is over 0.01 of a circle are not used (`MAX_PHASE_ERROR`).

---

## Part 3. Time: turning a SPHEREx time stamp into TESS's clock (20 min)

SPHEREx and TESS write time differently. Before comparing, everything must be on **one clock**.

**SPHEREx:** every photo has `MJD-AVG`, the middle of the exposure, in **UTC** (ordinary clock time). MJD = days since 17 Nov 1858.

**TESS:** uses **BTJD** = BJD_TDB − 2457000:
- **TDB** is a smooth, steady time scale used for astronomy. It is UTC plus leap seconds plus 32.184 s, so today **69.2 seconds** ahead of UTC.
- **B (barycentric)** means "as if measured at the centre of mass of the solar system". Earth moves around the Sun, so light from a star reaches Earth a bit earlier or later depending on where Earth is in its orbit (up to ±8.3 minutes for a star in the plane of Earth's orbit). The barycentric time removes that wobble.

**The code** (`eclipses.py`, `to_btjd()`):
1. UTC → TDB with astropy (adds the 69.2 s).
2. Light-travel correction = (Earth's position from the solar-system centre · direction to the star) / speed of light.
3. Subtract 2457000.

**Real numbers, one SPHEREx photo of TIC 219900027** (D1, taken 2025-10-01 09:11 UTC):

| Step | Value |
|---|---|
| SPHEREx time, MJD (UTC) | 60949.383225 |
| Same moment as JD − 2457000 (UTC) | 3949.883225 |
| + 69.2 s (UTC → TDB) | 3949.884026 |
| + light-travel correction (−0.28 minutes) | **3949.883834 = BTJD** |

**Why only −0.28 minutes here, not up to 8 minutes?** This star is almost at the ecliptic pole, nearly at right angles to the plane of Earth's orbit, so Earth's yearly motion barely changes its distance to the star. For a star in the plane of Earth's orbit the correction would reach about ±8.3 minutes.

**Why bother if it is so small?**
- **The 69.2 s:** without it every phase would be off by 69 seconds.
- **Other targets:** the code works for any position, and further from the pole the light-travel correction grows.
- **The timing check (Part 8)** looks for shifts of a few minutes, so the clock must be right to seconds.

---

## Part 4. Phase: where the stars are in their circle (20 min)

**The rule** (`eclipses.py`, `phase()`; the same formula in the browser in `eclipse.js`, `phaseOf()`):

```
circles since the TESS moment = (BTJD − bjd0) / period
phase = that number − prim_pos, keep only the fraction, written from −0.5 to +0.5
```

**Why "keep only the fraction":** after every full circle the stars are back where they started, so full circles don't matter. Only the leftover tells you where they are.

| Phase | Where the stars are |
|---|---|
| 0.00 | middle of the **big dip** |
| ±0.25 | side by side, no dip |
| ±0.50 | middle of the **small dip** |

### Worked example 1 (the photo from Part 3)

```
(3949.883834 − 1683.750363) / 0.5152647 = 4397.9986 circles
4397.9986 − prim_pos (1.000134)          = 4396.9985
keep the fraction                         = 0.9985  → written as −0.0015
```

**Phase −0.0015**: 0.0015 × 742 minutes = **1.1 minutes before the middle of the big dip**. In the data this photo measured **0.67 × normal brightness** at 1.1085 µm. It was taken in the dip, and the brightness shows it.

### Worked example 2 (another D1 photo, 2026-05-24 23:44 UTC, almost 8 months later)

```
BTJD 4185.489601 → 4855.2505 circles → minus 1.000134 → fraction 0.2504
```

**Phase +0.2504**: a quarter of the way round, stars side by side, no dip. It measured **1.07 × normal** at 0.9112 µm. Why above 1? See "baseline" in Part 6.

### The key insight

The first photo was taken on circle number ~4398, the second on ~4855, almost 8 months apart. Their **dates** say nothing about the dip. Their **phases** say exactly where the stars were. **Sorting by phase instead of date** puts every in-dip photo together, wherever it is in the calendar.

---

## Part 5. Which photos we download, and why (10 min)

**Step 1, forecast, with no download** (`eclipses.py`, `forecast()`). The archive lists every image's time. With the ephemeris, each time becomes a phase. For TIC 219900027:

| Count | Value |
|---|---|
| SPHEREx images of this star, all 6 detectors | **16,676** |
| Of those, taken during the big dip | **2,615** |
| Of those, taken during the small dip | **1,709** |

The page shows this under **"3. What SPHEREx has"**.

**Step 2, choose a fixed number per detector** (`select_for_download()`, budget `BUDGET`):

| Group | Photos per detector |
|---|---|
| in the big dip | 40 |
| in the small dip | 25 |
| clearly outside both dips (each dip widened by 25% for safety) | 50 |

Inside each group, the photos are **spread evenly in phase** (`_spread()`), so the start, middle and end of each dip are all covered.

**Why choose by time, not by brightness?** The choice is made **before** anyone sees a single brightness. We cannot pick photos that happen to show a nice dip, so the result cannot be cherry-picked.

**What happened to them:**

| Stage | Photos |
|---|---|
| chosen (115 × 6 detectors) | 690 |
| measured (16 fell off the 3′ frame) | 674 |
| **used** (the rest had a flagged pixel on the star, or no measurement) | **557** |

Flagged photos are not thrown away silently: on the page they appear as **hollow** dots.

---

## Part 6. From photo to number (15 min)

**1. Brightness** (`eclipse_build.py`, `photometry()`):
- Each photo is cut out, IMAGE − ZODI, and lined up on a 29 × 29 north-up grid of 6.15″ pixels.
- Brightness = light inside a **2-pixel circle** on the star minus the median sky **10–14 pixels** away.
- Unit: mJy. The first photo above: 56.3 ± 0.3 mJy.

**2. Colour correction** (`eclipse_depth.py`, `fit_steady()`):
- Every photo sees a different colour, and the star is naturally brighter in some colours, so raw numbers jump around.
- Using **only photos taken outside the dips**, the code fits a smooth curve **S(λ)** = "normal brightness at each colour", per detector.
- Each photo is divided by S at its own colour: **g = brightness / S(λ)**. 1.00 = normal; 0.67 = 33% dimmer than normal.
- **Blind test:** photos near phase ±0.25 are kept out of this fit, to check later that they really come out as no dip.

**3. Baseline** (`fit_baseline()`):
- These two stars are so close that gravity stretches them into egg shapes. Side-on (phase ±0.25) we see more surface; end-on (0 and ±0.5) less. So even outside dips the brightness rises and falls smoothly.
- The code fits B(φ) = c0 + a1·cos(2πφ) + a2·cos(4πφ), used only when significant. For TIC 219900027 it is used: about **1.08 at phase ±0.25** and **0.87 at phase 0**.
- That explains worked example 2: 1.07 measured / 1.08 baseline ≈ **0.99**, so no dip, as it should be.
- And example 1: 0.67 / 0.87 ≈ **0.77**, so about 23% of the light is missing in that one photo.

**4. Depth per colour** (`depth_spectrum()`):
- The middle half of each dip, in 12 colour groups (2 per detector).
- **Depth = 1 − weighted average of g / B.**
- Results for TIC 219900027 (selected bins):

| Colour | Big dip | Small dip |
|---|---|---|
| ~1.0 µm | 19% | 6% |
| ~3.4 µm | 18% | 13% |
| ~4.9 µm | 20% | 14% |

The small dip roughly doubles towards the infrared: the cooler star catching up.

---

## Part 7. The flipbook, line by line (15 min)

**Back end, making the pictures** (`eclipse_build.py`, `write_frames()`):
- **Order:** for each detector, the photos are sorted by **phase** and saved as `d1/p000.png`, `p001.png`, … in that order.
- **One brightness scale for the whole detector,** so the star cannot look brighter just because the scale changed.
- **A second, colour-corrected copy `_n.png`** is multiplied by `factor = median S / S(λ of this photo)`. For example `d1/p000_n.png` has factor 1.0036. In this copy the star's normal brightness is the same in every frame, so **only the dip changes it**.

**Front end, playing them** (`frontend/js/eclipse.js`):

| Function | What it does |
|---|---|
| `phi(p)` | phase of a photo from its BTJD and the **current** period and t₀ (TESS's values, or what you typed) |
| `framesFor(det)` | the frames of one detector, **sorted by `phi`**. If you change the period, the order changes. |
| `setDet(det)` | picks a detector and starts the flipbook just before the big dip (phase ≥ −prim_width) |
| `showFrame(k)` | shows frame k: picture, phase, **"Primary eclipse" / "Secondary eclipse"** badge (from TESS's dip widths, `eclipsePart()`), label (colour, date, mJy, "× normal at this wavelength", why a photo is not used), the little orbit cartoon (`renderOrbit()`), and a ring on that photo's dot in the folded light curve |
| `togglePlay()` | Play / Pause: next frame every **280 ms** |
| `setView()` | **"Colour-corrected"** (`_n.png`, the default) or **"As measured"** (`.png`) |

**What you see when you press Play on D1** (112 photos): normal brightness → fades into the big dip (badge on, cartoon shows the small star in front) → recovers → fades a little into the small dip near ±0.5 → back.

**Under the flipbook:**
- **Folded light curve:** every photo as a dot, g against phase, coloured by wavelength; hollow = not used; grey line = baseline.
- **Phase × wavelength:** every photo placed by its phase and its colour, showing that each dip is covered across all colours.
- **Eclipse depth spectrum:** the depths per colour from Part 6.
- **During eclipse minus outside eclipse** (the "blink" picture):
  - 16 photos from the middle of the big dip, added up, minus 16 photos outside the dip **paired by colour**. In D1 the largest colour gap within a pair is 0.0122 µm.
  - Everything that did not change cancels to grey. The binary shows as a dark spot: **−193.7σ, 0 pixels from our star**.
  - So the dip belongs to this star, not a neighbour.

**Links:** `?tic=219900027&det=1&P=…&t0=…` opens a binary, a detector and your own period and t₀ (`setUrl()`).

---

## Part 8. Why the clock must be exact (10 min, do this on the page)

Our photos are about **4,400 circles** after TESS's `bjd0`. Any error in the period is multiplied by 4,400:

| Period used | Error × 4,400 circles | What happens to the flipbook |
|---|---|---|
| TESS's 0.5152647 d (error 0.00000079 d) | about 5 minutes | dip photos line up; clean dip |
| off by 0.00001 d (under 1 second) | 0.044 d = **63 minutes** | dip smeared, about half its 117-minute width |
| off by 0.0007 d (e.g. 0.5160) | 3.1 days = **6 whole circles** | photos completely scrambled; **the dip disappears** |

**Try it:**
1. Type `0.5160` in **Period P** and press **Fold**. The folded light curve becomes a flat cloud.
2. Press **TESS values** and the dip comes back.
3. In **"Find the period yourself"**, drag the slider. θ (the scatter score) drops when the photos line up into a clean curve.

**The two clock checks on the page, for TIC 219900027:**
- **"TESS's clock is still right" → Yes:** the dip's middle in SPHEREx data is 11.1 ± 3.0 minutes early. TESS's own clock is uncertain by ±5.3 minutes by then. Combined, that is within 3σ, so no real shift. A real shift would mean the period is changing, for example a third star pulling on the pair.
- **"SPHEREx finds the period alone" → No:** with no TESS input, the best θ is 0.92, against about 1.00 for a random period. The dip is too shallow for the scatter of single photos (about 4% per photo), so SPHEREx alone cannot find the clock. **That is exactly why TESS's clock is needed.** The other pair, TIC 233208885, has a deeper dip (40%), and there SPHEREx alone does find it (at half the TESS period, a common mix-up when the two dips look alike).

---

## Part 9. Self-test (5 min)

Answer without looking, then check.

1. Why can't one SPHEREx photo show the dip in many colours?
2. What two numbers from TESS do you need to give a photo its phase?
3. A photo has phase +0.48. Where are the stars, and which dip is it?
4. Why do we convert UTC to BTJD before computing phase?
5. Why does a 1-second error in the period matter, when a dip lasts 2 hours?
6. Why are photos chosen for download before looking at their brightness?
7. What does the "Colour-corrected" view change, and why?
8. In "During eclipse minus outside eclipse", what does a dark spot on a neighbouring star mean?

<details><summary>Answers</summary>

1. Each photo sees only one colour at the star (SPHEREx's linear variable filter). The colours come from many photos on many days.
2. The period and the time of one big dip (`period`, `bjd0`, plus `prim_pos` for the exact offset).
3. Almost halfway round, near the middle of the **small** dip (secondary eclipse): the brighter star is in front of the cooler one.
4. TESS's timetable is written in BTJD. Mixing clocks would shift every phase (by 69 s from UTC → TDB alone, and up to ±8 minutes of light-travel time for stars far from the pole).
5. It is multiplied by about 4,400 circles: 1 second × 4,400 ≈ 73 minutes, more than half the dip's length.
6. So the result cannot be cherry-picked: the choice uses only times (phases), never brightness.
7. Each frame is multiplied so the star's normal brightness at that frame's colour is the same everywhere. The colour-to-colour flicker is removed and only the dip changes the star.
8. That TESS's dip belongs to the neighbour, not our star. TESS's 21″ pixels can mix stars that SPHEREx's 6.15″ pixels separate.

</details>

## Exercises (if you have more time)

- **Recompute the phase in Python:**
  ```
  PYTHONPATH=. .venv/bin/python -c "from backend.app import eclipses as E; e=E.by_tess_id('219900027'); print(E.phase(E.to_btjd([60949.383225], e.ra, e.dec), e))"
  ```
  You should get −0.0015 (tiny differences in the 4th decimal come from using the J2000 position).
- **Find the sort:** find the one line in `framesFor()` that turns a date-ordered list into a phase-ordered flipbook.
- **Compare views:** open D5 and switch between **Colour-corrected** and **As measured**. Explain the flicker you see in "As measured".
