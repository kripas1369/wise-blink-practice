# 10. Day 2 data pipeline: from raw SPHEREx files to flipbook frames

Code: `backend/app/clean.py`, `align.py`, `coadd.py`, `render.py`, `frame_notes.py`; tests `backend/tests/test_pipeline.py`.
Built by Kripas on 31 Oct (after [Friend's name] moved to validation and research).

```
python -m backend.app.render barnard 2                      # add up to 8 exposures per visit
python -m backend.app.render wise0855 6 --max-per-visit 21  # every exposure
python -m backend.app.render barnard 2 --mode single --out scratch/frames
```

## The 4 steps
```
1. find      SIMBAD position moved to 2026.0 → IRSA: every image in detector N → visits (group_epochs)
2. clean     each cutout: IMAGE − ZODI, sigma = √VARIANCE, bad = FLAGS & official mask, time = MJD-AVG,
             wavelength at the star from the file's spectral WCS (key "W")
3. align     reproject image, variance and bad mask onto ONE north-up 29 × 29 grid of 6.15″ pixels
4. add up    per pixel: weight = 1/σ² (0 if bad or no value); value = Σ(w·x)/Σw; σ = 1/√Σw
then         one brightness scale for all visits → PNG + flags PNG + manifest.json (FRAMES_FORMAT.md)
```

## Why each choice
| Choice | Reason |
|---|---|
| Exposures closest to the visit's middle first | A visit can last weeks; the middle is the fairest single time for the frame. |
| Skip an exposure if < 90% of the grid is inside it | A half-empty frame would look like a change in the sky. |
| Skip only "not in image"; any other download error stops the run | A network error once made an add-up use 17 instead of 21 exposures without saying so. Now it fails loudly and is retried. |
| 1/σ² weights | Noisier exposures count less; this gives the smallest possible noise for the add-up. |
| Bad pixels get weight 0 | A hot pixel in one exposure is filled by the other exposures (Eps Ind B Apr 2026: 30% flagged in one exposure, 0% after adding 7). |
| `inside` vs `covered` | reproject marks both "outside the picture" and "NaN" as footprint 0; reprojecting an array of ones tells them apart, so a saturated core is "no value" (striped), not "outside". |
| The wavelength range in the label | SPHEREx's filter (LVF) gives each exposure its own wavelength; an add-up mixes them, so the label shows the range (e.g. Barnard D2 visit 1: several values between 1.1 and 1.6 µm). |
| `--mode single` kept | It reproduces the first sample frames pixel for pixel, so the website's history can be checked. |

## How we know it works
- **9 offline tests** on fake files: ZODI subtracted, HOT bad but SOURCE not, NaN kept, `MJD-AVG` not `DATE`, unknown wavelength stays unknown, grid size and centre, a bright pixel in a rotated exposure lands north-up/east-left (0°, 90°, 180°), the 1/σ² arithmetic (10 at σ 1 and 20 at σ 2 give 12), bad pixels left out, PNG north at the top and transparent where there is no value.
- **Against the old frames:** `render --mode single` vs the sample frames: same grid, grey difference 0, correlation 1.000.
- **Against the findings:** `scripts/measure_ring.py` gives the same single-exposure numbers as `notes/DAY2_FINDINGS.md` (WISE 0855 D6: 2.1, 5.5, 2.4σ).

## What the add-ups showed
See [`notes/DAY2_FINDINGS.md`](../notes/DAY2_FINDINGS.md), section "Add-ups".

## Re-type exercise (Kripas)
Re-type `coadd.py` (about 30 lines) from the 4 steps above; run `python -m pytest backend/tests/test_pipeline.py`.
