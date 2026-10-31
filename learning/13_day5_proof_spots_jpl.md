# 13. Day 5: the proof panel, spots above 5σ, the known-object check, and the About page

Code: `backend/app/proof.py`, `backend/app/spots.py`, `backend/app/known_objects.py`, `backend/app/measure.py`, `/api/proof` and `/api/known-objects` in `main.py`; `frontend/js/proof.js`, `frontend/js/spots.js`, `stepPair()` in `diffview.js`, `frontend/about.html`.
Tests: `backend/tests/test_day5.py`, `frontend/tests/day5.test.js`, the Ceres test in `backend/tests/test_network.py`. Built by Kripas on 31 Oct. Numbers: [`notes/DAY5_FINDINGS.md`](../notes/DAY5_FINDINGS.md).

```
python -m backend.app.proof frontend/frames/*/d* --online    # proof.json (online: IRSA release dates)
python -m backend.app.spots frontend/frames/*/d*             # spots.json (offline)
uvicorn backend.app.main:app --port 8010                     # website + API, then open a spot and press the JPL button
```

## The question Day 5 answers
Days 1–4 show pictures, differences and light curves. Day 5 asks: **why should anyone believe them?** A judge (or the friend) should be able to see, on the page, what each claim rests on and what it does not prove.

## Step 1: the proof panel (`proof.py`)
One file per frame folder, `proof.json`, with two parts.

| Part | What it holds | Why |
|---|---|---|
| Motion | Gaia's predicted shift from the first to the last visit, our measured shift, and a verdict | A claim of motion needs a reference that is not us. Gaia DR3 is that reference. |
| Data | visits, exposures used / taken, % flagged, newest exposure, data releases, when the frames were made | "How much data, how old, from which release" is what a scientist asks first. |

The verdict has six possible values, not two. "Agrees" needs both a size difference of at most 0.5 px (the plan's C4 test) and a direction difference of at most 30° (ours). If Gaia's motion is under 0.3 px, the panel says **too small to test**. Our own measurement error is about that size, so a "pass" there would mean nothing. R Dra and RW Aur get this verdict. WISE 0855 gets **nothing to compare with**: it is not in Gaia.

The centroid code is shared with `scripts/acceptance.py` in `measure.py`, so the website and the C4 tests cannot drift apart.

## Step 2: spots above 5σ (`spots.py`)
`ndimage.label` groups touching pixels (8 neighbours) above +5σ or below −5σ in the difference. Each group becomes a **spot** with:
- size, peak σ, position (pixels and RA/Dec);
- **artifact flags**: long and thin, very large, next to flagged or no-value pixels, touches the frame edge;
- **the Gaia star behind it**: the brightest Gaia star within 1.5 px, else the nearest;
- three texts: *why it is listed*, *what else could explain it*, *what would confirm it*.

**Mistake I made and fixed.** The first version picked the *nearest* Gaia star. Barnard's −173.7σ spot got a G 20.59 star at 0.58 px, while Barnard's Star itself (G 8.19) was at 1.41 px. A star 12.4 magnitudes (about 90,000 times) fainter in Gaia's band cannot make that spot. Lesson: "closest" is not "cause"; brightness matters.

## Step 3: the known-object check (`known_objects.py`)
Could a spot be a known asteroid? NASA JPL's Small-Body Identification API answers "which known objects were near this position at this time, seen from here".

| Choice | Reason |
|---|---|
| Observer = SPHEREx, not Earth's centre | SPHEREx is about 7,000 km from Earth's centre; a nearby asteroid's position changes with the viewpoint. JPL also refuses the geocentre. The position comes from each exposure's header (`X_SC` … `VZ_SC`). |
| Three outcomes: match / no match / unavailable | Never guess. "No match" never means "new object"; "unavailable" is not cached, so it is asked again. |
| Whole seconds in RA/Dec, time as a Julian date | Other forms failed on 31 Oct (decimal seconds; `_hh:mm:ss`). The rounding is corrected back to the spot. |
| Second pass first, first pass as a labelled fallback | The accurate second pass failed for every request on 31 Oct, even JPL's own example. |
| Tested on Ceres | A spot 7.2″ from Ceres's position (from JPL Horizons) gave "match, 1 Ceres, 10.1″", with JPL's error 13.2″. A check that never says "match" could be broken; this shows it is not. |

The card also gives the add-up's time span. WISE 0855 D6 visits span 478–786 hours, so an asteroid would smear across many pixels there. A match on that visit would mean little, and the card says so.

## Step 4: the +/− picker and the About page
- `stepPair(ids, a, b, which, delta)` returns the new pair, or `null` if it would leave the list or put A at or after B. The buttons use this to disable themselves. It's a pure function, so it is easy to test.
- `about.html`: the cleaning steps, the limits, the credits. **Rule: every sentence must point to code or a source.** Checking it found two of my errors: WISE 0855 D6 adds up all exposures of a visit (up to 21, not 8), and `scipy` was missing from `requirements.txt`.

## What could still be wrong
- JPL's offset sign (east and north positive) is assumed, not tested.
- `XYZ_SC_SYSTEM = 'GEOCENTER'`: we assume ICRF axes.
- For huge spots (hundreds of pixels), the "Gaia star" is chosen from the patch's centre, which is not where its cause is.
- The spectrum panel is not built: it needs frames for the other detectors.
