# 12. Day 4: the light curve, the asinh scale, and the C4 tests

Code: `backend/app/lightcurve.py`, `/api/lightcurve` in `main.py`, `--stretch` in `render.py` and `rebuild.py`; `frontend/js/lightcurve.js`, the click in `flipbook.js`; `scripts/acceptance.py`.
Tests: `backend/tests/test_day4.py`, `frontend/tests/day4.test.js`. Built by Kripas on 31 Oct. Numbers: [`notes/DAY4_FINDINGS.md`](../notes/DAY4_FINDINGS.md).

```
python -m backend.app.lightcurve frontend/frames/rw_aur/d2     # exposures.fits + lightcurve.json (offline)
python -m scripts.acceptance --json notes/acceptance_c4.json   # the C4 checks (add --online for IRSA counts)
uvicorn backend.app.main:app --port 8010                       # website + API, then click a flipbook pixel
```

## The question Day 4 answers
Day 3 proved *where* things are (Gaia markers, the difference in σ). Day 4 asks *how bright*, and whether a brightness change is real.
The trap is SPHEREx's filter (the LVF): every exposure sees a slightly different wavelength at the target. A star's brightness depends on wavelength, so two exposures can differ without the star changing at all.

## Step 1: every exposure on the grid (`exposures.fits`)
The add-ups (Day 2) mix up to 8 exposures and so mix wavelengths. For a light curve each exposure must stay separate.
`write_exposures()` takes every cached exposure behind the frames (no new download), puts it on the same grid, and stores IMAGE, SIGMA, FLAGGED and HAS_VALUE as cubes (one plane per exposure), plus a table with each exposure's id, time, wavelength, bandwidth and visit.

## Step 2: measure one position (`measure()`)
```
flux = sum over the circle (r = 2 px) of (pixel − sky) × weight × 0.889 mJy
sky  = median of the pixels 10–14 px away
err  = √(sum of σ² × weight²) × 0.889, plus the sky uncertainty
```
| Choice | Reason |
|---|---|
| Circle of 2 px (12.3″) | SPHEREx's PSF is about a pixel wide; 2 px holds most of the light without taking in much sky. |
| Weights from 5 × 5 sub-pixels | A pixel half inside the circle counts half; without this the flux jumps when the circle moves by a fraction of a pixel. |
| Median sky in a ring 10–14 px away | The median ignores other stars in the ring. |
| 0.889 mJy per (MJy/sr × pixel) | One pixel is (6.15″)² = 8.89 × 10⁻¹⁰ sr; 1 MJy = 10⁹ mJy. |
| No aperture correction | A 2 px circle misses some light; the same fraction every time, so points can be compared with each other, not with catalogues. The website says so. |
| The error is a lower limit | Reprojection mixes neighbouring pixels, so their noise is not independent. Written next to the chart. |
| The circle follows the target | Gaia's motion (or SIMBAD's for WISE 0855). Otherwise a moving star walks out of the circle and looks fainter. |

## Step 3: compare only at the same wavelength (`same_wavelength()`)
Two exposures of **different visits** are compared when their wavelengths differ by less than half a bandwidth, and both are at least 5σ. The answer is a ratio, b / a.
"Clean" pairs also need no flagged pixel inside either circle. Pairs that include flagged pixels are listed separately ("less certain"), because persistence or a cosmic ray inside the circle can add light.

**Epsilon Indi B shows why.** In one detector it is about 7 times fainter at 1.36–1.40 µm than at 1.27 µm (water and methane in a cool brown dwarf absorb there). That alone explained the factor-2 changes between the add-ups. At the same wavelength, its visits agree within about 15%.

## Step 4: how big a change is real? (the field-star floor)
Measure stars that should not change, the same way, with the same rule. The spread of their ratios is the smallest change we can believe.
Only the Barnard frame has a suitable Gaia star (G 13.6, isolated): **4.5%**. RW Aur's 24% (one clean pair) is above that, but its own frame has no comparison star, so the website says the floor there is unknown.

## Step 5: when not to make a light curve
Barnard's Star and R Dra are saturated: no value up to 5–6 px from the centre. A ring outside that hole would have to start at 6–7 px.
Checked on RW Aur (not saturated): a 3–6 px ring follows the core within 10%; a 6–9 px ring does not. A first try on Barnard with a 6–9 px ring gave a 0.62 ratio, a **fake change**. So: rings starting beyond 3 px are not used, and these stars get "no light curve", with the reason, instead of a wrong one.

## Step 6: the website panel (`lightcurve.js`)
| Chart | How to read it |
|---|---|
| Brightness over time, coloured by wavelength | Points of one visit spread up and down mostly because of wavelength, not because the star changed. |
| Brightness against wavelength, one colour per visit | Where two visits overlap in wavelength, a gap between their colours is a real change. RW Aur: Sep 2025 (blue) sits below 2026. |

- **Hollow point:** a flagged pixel in the circle, or fainter than 5σ. **▲ at the edge:** an exposure with flagged pixels more than 3× above the clean ones (WISE 0855 D6: one exposure measured 520 mJy where the others give about 0.6). It is named in the warnings, not hidden.
- **Warnings:** Gaia stars inside the circle (and, when the circle moves, that this alone can fake a change: WISE 0855 D2), how many exposures were left out, and the floor (or that it is unknown).
- **Click a pixel:** the API measures that fixed position the same way. Without the API, the panel says that a click needs it.
- Own SVG charts instead of Chart.js: no extra library to load, and every mark (hollow, ▲, error bar) is under our control and tested.

## Step 7: R Dra's asinh scale
The R Dra add-up has core pixels up to 2,870 MJy/sr and a sky near 1. A linear scale makes the sky black.
asinh grows like a straight line for faint values and like a logarithm for bright ones, so both show:
```
grey = asinh(t / 0.002) / asinh(1 / 0.002),   t = (value − vmin) / (vmax − vmin)
```
The price: grey levels are no longer proportional to brightness. The manifest writes `stretch: "asinh"`, the website says it, and brightness is judged by measurement, not by eye.

## Step 8: the C4 acceptance tests (`scripts/acceptance.py`)
| Target | Result |
|---|---|
| Barnard's Star | the saturated hole moved 0.18 px from Gaia's prediction (limit 0.5): pass |
| WISE 0855 | D6 source moved 0.58 ± 0.12 px; WISE 0855 should move 0.72 px (motion + parallax), a fixed star 0: pass. Nothing at its position in D2: pass. D1, D3, D5 not prepared. |
| Epsilon Indi B | direction 8° from Gaia's: pass |
| RW Aur, R Dra | AAVSO not reachable; R Dra has no light curve: not checked / cannot be checked |
| Any position | our image count = IRSA's own count at 3 positions (359, 378, 410): pass |

**How the WISE 0855 fit separates the two candidates.** A 2-D Gaussian is fitted to the D6 source in each visit. WISE 0855 must move about 0.7 px west between Nov 2025 and Apr 2026; the Gaia star next to it (G 16.31) must stay put. The measured shift is 1.4σ from the first and 4.9σ from the second. Parallax (0.44″ = 0.07 px) is included because SPHEREx sees the star from opposite sides of the Sun six months apart.

## What could still be wrong
- The 4.5% floor comes from one star in one frame.
- The Gaia star may add about a quarter of the D6 light (2.7–2.8σ): not proven, would bias the fit slightly.
- The 520 mJy D6 exposure: cause not checked.
- No AAVSO comparison yet.
