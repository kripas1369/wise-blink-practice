# Pipeline alignment: ours vs IRSA's official tools vs SPHEREXPLANETX (1 Nov 2026)

**Short answer.** One real bug found and fixed in our pipeline: the wavelength at the target was read with the image's SIP distortion switched on. Everything else we checked against IRSA's per-pixel calibration maps or the official tools' choices either agrees already or makes no measurable difference on our data, so it stays as it is. Numbers and scripts below; any of them can be re-run from the cache.

Compared:
- **Ours:** `backend/app/` (clean → align → coadd → render → diff → lightcurve → spots → spectrum).
- **IRSA's official tutorials and tools** (copies in SPHEREXPLANETX `resources/official_pipelines/irsa-tutorials/tutorials/spherex/`): `spherex_intro`, `spherex_cutouts`, `spherex_psf`, `spherex_mosaic`, Source Discovery Tool (`spherex_source_discovery_tool/aperture_photometry.py`), and the archive documentation (`spherex_data_products.md`).
- **lazylog00/SPHEREXPLANETX** at commit `1b13479` (29 Oct 2026): `spherex_pipeline.py`, `spherex_processor.py`, `02_fits_conversion.py`, `spherex_data_bible.md`. Read only; nothing was copied from it.

---

## 1. Step by step

| Step | IRSA official | Ours | SPHEREXPLANETX |
|---|---|---|---|
| Bad pixels | 19 flags of the Mosaic Tool (Supplement §3.4.3); SOURCE is a label | same 19, bit positions read from the header (`MP_*` QR2, `MSKN*` QR3) | same 19, bit positions hard-coded |
| Background | `IMAGE − ZODI` | `IMAGE − ZODI` | `IMAGE − ZODI` |
| Noise | √VARIANCE | √VARIANCE | √VARIANCE |
| Time | `MJD-OBS` (SDT) | `MJD-AVG` (middle of the exposure) | `DATE-OBS` (`spherex_pipeline.py:131`) |
| Wavelength | WCS "W", **SIP off**; CWAVE/CBAND for science | WCS "W", SIP off **since today** | WCS "W", SIP off (`spherex_pipeline.py:154`) |
| Same sky in two images | `reproject_exact` (values), `reproject_interp` (masks) | `reproject_interp` (values), nearest neighbour (masks) on a north-up grid | none: `difference()` subtracts the same detector pixels (`spherex_pipeline.py:392`) |
| MJy/sr → mJy | per-pixel solid angle map (SAPM) on detector pixels | one constant, 37.82 arcsec², on our 6.15″ grid | constant 8.887e-10 sr; `02_fits_conversion.py:69` uses 9.04e-10 |
| Aperture / sky | 3, 4, 5 px; sky 7–16 px, 3σ-clipped median | 2 px; sky 10–14 px median | none |
| Detector ranges | Supplement | D1 0.75–1.09 … D6 4.42–5.00 | D3 and D4 swapped, D1/D2 edges off (`spherex_pipeline.py:51-58`) |

---

## 2. Changed: wavelength read with SIP off (`clean.wavelength_at`)

Astropy copies the image's SIP distortion into the spectral WCS "W"; IRSA's tutorials switch it off (`spectral_wcs.sip = None`, spherex_intro §8b), because the filter's wavelength map is not optically distorted. We had not.

**Size of the error (D2, 146 exposures, against the science map CWAVE at the same detector pixel):**

| | median error | largest error |
|---|---|---|
| SIP on (before) | 2.0 nm | 8.1 nm = 0.27 × bandwidth |
| SIP off (now) | 0.3 nm | 0.83 nm = 0.03 × bandwidth |

So with SIP off, the file's lookup table is as good as CWAVE for our purpose (the same-wavelength rule allows 0.5 × bandwidth). CWAVE is therefore not needed.

**What was redone:** every prepared folder was rebuilt from the cache (`python -m backend.app.rebuild frontend/frames/*/d*`, which now also rewrites the wavelengths in `manifest.json`; all PNGs matched within 1 grey level), then `diff`, `lightcurve --rebuild-exposures`, `spots`, `spectrum`.

**What changed downstream:**
- Mean wavelengths per visit moved by 0.0001–0.016 µm (largest: Eps Ind B D4).
- Default difference pairs: the same pairs everywhere; only the quoted gap moved (e.g. Eps Ind B D4 0.026 → 0.019 µm).
- Same-wavelength pairs: a few changed. Eps Ind B D3 visits 1→2: 8 → 6 pairs, median ratio 0.947 → **0.991** (a steady star should give 1). Eps Ind B D5 visits 2→5: 2 → 3 pairs, 0.987 → 1.002.
- WISE 0855 D2 ratios unchanged (1.857, 2.057). As `DAY4_FINDINGS.md` already says, they are the moving circle sliding over a fixed Gaia star, not WISE 0855 (confirmed again in section 3c).

Test: `test_wavelength_ignores_sip_distortion` (`backend/tests/test_pipeline.py`) builds a file with a 1.35 px SIP shift; it fails without the fix (1.320 vs 1.3335 µm) and passes with it.

---

## 3. Checked and kept

### a. Pixel solid angle: our constant is exact on our grid

`scripts/check_calibration.py`, IRSA SAPM `cal-sapm-v2-2025-164`, at the target's detector pixel in every cached exposure:

| Folder | Exposures | SAPM (arcsec²) | SAPM / area from the file's sky WCS |
|---|---|---|---|
| Barnard D2 | 24 | 37.43–37.80 | 0.9997–1.0001 |
| Eps Ind B D2 | 39 | 37.45–38.02 | 0.9996–1.0001 |
| R Dra D2 | 29 | 37.42–37.98 | 0.9998–1.0000 |
| RW Aur D2 | 24 | 37.44–37.99 | 0.9995–1.0001 |
| WISE 0855 D2 | 30 | 37.43–37.92 | 0.9997–1.0001 |
| Eps Ind B D6 | 74 | 37.56–38.40 | 0.9996–1.0001 |
| WISE 0855 D6 | 43 | 37.58–38.41 | 0.9995–1.0003 |

The SAPM equals the pixel area given by each file's sky WCS to 0.05%. `align.py` resamples surface brightness (MJy/sr) with that WCS onto a grid of exactly 6.15″ pixels, so light per grid pixel = value × 37.82 arcsec², with no per-pixel map needed. The SAPM is needed only when measuring on detector pixels, as IRSA's tool does. A detector pixel can be 1.1% smaller or 1.6% larger than ours.

### b. `reproject_exact` vs our `reproject_interp`

`scripts/compare_reproject.py`: same cutouts, light curve measured twice; spread of same-wavelength ratios between visits on Eps Ind A (a steady star):

| | D2 | D3 | D4 | D5 |
|---|---|---|---|---|
| interp (ours) | 7.6% (14 pairs) | 9.4% (15) | 8.6% (3) | 2.9% (18) |
| exact | 6.3% | 9.2% | 10.7% | 2.8% |

Mixed and within the noise of so few pairs. Kept `reproject_interp`.

### c. Aperture and sky ring

`scripts/compare_apertures.py`: same exposures and target track, only the circle changes. Spread on Eps Ind A:

| radius | D2 | D3 | D4 | D5 |
|---|---|---|---|---|
| 2 px (ours) | 6.6% (14) | 10.8% (15) | 3.9% (3) | 6.7% (15) |
| 3 px | 9.0% (12) | 9.3% (11) | 6.8% (3) | 3.3% (10) |
| 4 px | 9.3% (11) | 7.4% (9) | – | 3.5% (7) |
| 5 px | 6.8% (6) | 7.6% (7) | – | 3.7% (5) |

No radius is best everywhere, and bigger circles lose pairs: they more often contain a flagged pixel, which makes a point "not comparable". IRSA's sky ring (7–16 px, 3σ-clipped) changes the spread by at most 1.3 points in either direction. Kept 2 px and 10–14 px.

**WISE 0855 D2, the same test:** median brightness per visit 0.46 / 0.80 / 0.83 / 1.01 mJy with 2 px, but 0.91 / 1.00 / 0.97 / 1.07 with 3 px and flat with 4 px. Seen with a larger circle, the "brightening" disappears. This fits the DAY4 explanation: WISE 0855 is far too faint at 1.3 µm, and the light is the Gaia star (G 16.31) 1.3 px away, which the moving 2 px circle takes in partly.

---

## 4. Found in IRSA's Source Discovery Tool (to report, not to copy)

`aperture_photometry.sa_mjy_scale_map`: when the image is a cutout (not 2040×2040), the solid angle map is evaluated at pixels `arange(nx)`, `arange(ny)` ([lines 160-165](../../SPHEREXPLANETX/resources/official_pipelines/irsa-tutorials/tutorials/spherex/spherex_source_discovery/spherex_source_discovery_tool/aperture_photometry.py)), i.e. at the detector's corner, not where the cutout lies (`CRPIX1A`/`CRPIX2A`). On D2 the corner is 37.45 arcsec² while our targets sit on 37.42–38.03, so fluxes from that tool can be off by up to about 1.5% (D6: up to about 2.3%). This is our reading of the code; worth confirming with IRSA before saying it publicly.

---

## 5. For lazylog00 (SPHEREXPLANETX): what to check

1. **Detector ranges:** `SPHEREX_BANDS` lists D3 as 2.41–3.82 µm and D4 as 1.64–2.41 µm; they are swapped (D3 1.63–2.41, D4 2.42–3.82, Supplement). D1/D2 edges 1.11/1.64 vs 1.09–1.10/1.62. Their own `spherex_data_bible.md` has the right values.
2. **Differencing:** `PlanetXDetector.difference()` subtracts the same detector pixel box from two exposures. Two exposures point differently and see different wavelengths at the same pixel, so stars will not cancel. The images need putting on one sky grid first (as in IRSA's mosaic tutorial, or our `align.py`), and then comparing at the same wavelength.
3. **Time:** `DATE-OBS` is the start of the exposure; `MJD-AVG` is the middle (`MJD-OBS` in IRSA's tool). This matters for fast movers.
4. **Pixel solid angle:** `02_fits_conversion.py` uses 9.04e-10 sr; (6.15″)² is 8.887e-10 sr (`spherex_pipeline.py` itself has the right value). Real pixels are 37.4–38.4 arcsec² (SAPM), i.e. 8.80–9.03e-10 sr.
5. **Flag bits:** hard-coded positions; QR3 headers use `MSKN*` instead of `MP_*`. Reading positions from the header (as IRSA's tool does with `MP_*`) keeps working across releases.
6. **Good, and ahead of us:** they already had `spectral_wcs.sip = None`.

---

## 6. Re-run

```
python scripts/check_calibration.py frontend/frames/*/d2 frontend/frames/*/d6   # needs cache/calibration/*.fits (URLs in the script)
python scripts/compare_reproject.py frontend/frames/eps_ind_b/d2 frontend/frames/eps_ind_b/d5
python scripts/compare_apertures.py frontend/frames/eps_ind_b/d2 frontend/frames/wise0855/d2
```

For the hackathon repo (14 Nov, from empty): read the wavelength with SIP off from the start; the solid-angle and aperture choices above can be kept, with these numbers as the reason.
