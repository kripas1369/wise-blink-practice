# 11. Day 3: Gaia markers, the difference in σ, and the API

Code: `backend/app/rebuild.py`, `gaia.py`, `diff.py`, `main.py`; `frontend/js/sky.js`, `diffview.js`, Gaia layer in `flipbook.js`; `scripts/measure_motion.py`.
Tests: `backend/tests/test_day3.py`, `frontend/tests/day3.test.js`. Built by Kripas on 31 Oct.

```
python -m backend.app.gaia frontend/frames/barnard/d2     # Gaia DR3 stars → gaia.json (internet)
python -m backend.app.diff frontend/frames/barnard/d2     # every visit pair → diff.json + PNGs (offline)
python -m scripts.measure_motion frontend/frames/eps_ind_b/d2
uvicorn backend.app.main:app --port 8000                  # website + API
```

## The question Day 3 answers
Day 2 gave a flipbook. But "I see it move" is not proof: the eye is easy to fool on a 29 × 29 picture.
Day 3 adds two independent checks:
1. **Gaia says where each star should be.** If the target lands on its Gaia marker in every visit, the motion is real and our alignment is right.
2. **The difference says how sure we are.** B − A divided by the noise tells us whether a change is 1σ (noise) or 50σ (real, or a problem we must explain).

## Step 0: keep the real values (`rebuild.py`)
The PNGs are 8-bit grey (256 levels) and clipped at the scale. A difference must use the real MJy/sr values and their σ, so each visit now also gets `epoch<i>.fits` (IMAGE, SIGMA, FLAGGED, HAS_VALUE).
For the frames already on the website, `rebuild.py` remade them from the cached cutouts and **refused to write anything unless the rebuilt picture gave the same PNG** (1 grey level allowed).
That check found a real bug: the manifest stored the position rounded to 6 decimals, which moved the grid by a tiny fraction of a pixel and flipped one flagged pixel. Lesson: never round a number that something else will be computed from; round only for display.

## Step 1: Gaia markers (`gaia.py`)
```
IRSA Gaia DR3 (gaia_dr3_source): every star in a circle covering the field
→ for each frame: position = 2016.0 position + proper motion × (frame year − 2016.0)
→ grid WCS: sky position → PNG pixel (x to the right = west, y down = south)
→ target = the Gaia star nearest the grid centre at 2026.0, if within 3″
```
| Choice | Reason |
|---|---|
| Straight line, no parallax | Parallax is a yearly wobble; Barnard's is 0.55″ = 0.09 px, the biggest of our targets. Too small to see; written in the method text. |
| `source_id` as text | Gaia ids have 19 digits; JavaScript numbers are exact only to about 16, so `4472832130942575872` would silently become another star. |
| Pixel positions computed in Python | The website then needs no WCS code: it just draws circles at `xy[frame]`. |
| Match within 3″ or nothing | WISE 0855 is not in Gaia (too faint in visible light). Rather than circling a random neighbour, the website says "no star within 3″ of the frame centre". |

## Step 2: the difference (`diff.py`)
```
z = (B − A − sky change) / √(σA² + σB²)
sky change = median of (B − A) over pixels usable in both visits
```
- **Why divide by σ?** A change of 0.5 MJy/sr is huge on dark sky and nothing on a bright star. In σ units, "5" means the same everywhere: 5 times bigger than the noise.
- **Why √(σA² + σB²)?** Both pictures have noise; independent noises add in squares.
- **Why subtract the sky change?** The zodiacal glow is removed per exposure, but not perfectly; a small leftover offset would make the whole picture orange or blue.
- **Scatter check:** if σ is right, most pixels have |z| around 1, so 1.4826 × MAD(z) (a robust standard deviation that ignores the star) should be about 1. If it is 7.9 (Barnard), σ is too small for that picture, and big z values mean less. The website warns above 1.5.
- **Default pair:** the two visits with the closest wavelength at the target, because SPHEREx's filter gives each visit a different wavelength, and a different wavelength alone changes brightness.
- **Colours:** orange = brighter in B, blue = fainter, clipped at ±5σ. Flagged or no-value pixels in either visit get no colour (striped). No cross-fade animation: it would invent in-between pictures that were never taken.

**How to read a moving star:** blue where it was, orange where it went. The line from blue to orange is the direction of motion.
**The trap:** a bright star leaves a blue/orange pair even when it does not move (RW Aurigae: −52σ / +71σ). Tiny alignment or PSF differences on a very bright star are enough. So a pair counts as motion only when its direction and size match Gaia, and a non-moving star is smaller.

## Step 3: the API (`main.py`)
One FastAPI server gives both the website files and the data. Endpoints and formats: [`docs/plan/FACTS.md`](../docs/plan/FACTS.md) §7.
| Choice | Reason |
|---|---|
| Official targets use prepared frames | They are already checked; a request within 5″ of one at 3′ gets them instantly. |
| Any other position = background job, HTTP 202 | Downloading and adding up takes minutes; a web request cannot wait that long. The page shows "Preparing…" and asks again every 10 s. |
| One job at a time | IRSA answers "503 busy" to too many parallel downloads. |
| Every error is `{"error": "…"}` | The page shows the message as is; it never fills in a default value. |
| Website works without the API | `/api/health` decides; otherwise it reads `frontend/frames/` (the prepared targets), so a simple static host still works. |

## How we know it works
- **Motion against Gaia** (`scripts/measure_motion.py`): Barnard's saturated hole moved 1.59 px north (Gaia 1.67); Epsilon Indi B's centre moved 0.99 px south-east (Gaia 1.09); RW Aur, which does not move, 0.07 px. Full table: [`notes/DAY3_FINDINGS.md`](../notes/DAY3_FINDINGS.md).
- **In the browser:** Barnard's striped centre sits on its yellow Gaia circle in visits 1 and 3 (screenshots in `notes/screenshots/day3_*`).
- **Tests:** a still star sits on the centre pixel; a star moving north appears higher in the next frame, a star moving east further left; a sky offset between visits is removed and a pixel made 3σ brighter comes out as 3σ; flagged pixels give no z and no colour; the closest-wavelength pair is chosen; the API answers prepared targets, 400/404 errors and 202 "working" correctly.

## What is not done
R Dra add-up (needs a non-linear scale), a WISE 0855 position fit, PSF-fit positions. List: [`notes/DAY3_FINDINGS.md`](../notes/DAY3_FINDINGS.md) §4.

## Re-type exercise (Kripas)
Re-type `difference()` and `robust_scatter()` in `diff.py` (about 30 lines) from Step 2 above; run `python -m pytest backend/tests/test_day3.py`.
