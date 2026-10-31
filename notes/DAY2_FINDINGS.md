# Day 2 findings: what the real SPHEREx frames show (31 Oct 2026)

Measured by Kripas on real SPHEREx frames (IMAGE − ZODI, official flag mask, 29 × 29 grid of 6.15″ pixels centred on the 2026.0 position).
Every website note in the orange box ("Before you trust your eyes") comes from this file (`backend/app/frame_notes.py`).

Two rounds:
1. **Morning: single exposures** (one per visit), the first website frames. Section "Single exposures" below.
2. **Afternoon: add-ups** (up to 8 exposures per visit, all 21 for WISE 0855 D6, 1/variance weights; `backend/app/render.py`). These are on the website now. Section "Add-ups".

**How "sigma" was measured** (`python -m scripts.measure_ring frontend/frames/<target>/d<n>`, offline from the cached cutouts; it checks it used exactly the manifest's exposures):
- sky = median of the good pixels in the frame; noise = 1.4826 × median absolute deviation (MAD);
- **σ (scatter)** = (brightest ring pixel − sky) / noise; **σ (file)** = the same divided by the pipeline's own sigma from VARIANCE at that pixel;
- "ring" = the 3 × 3 pixels at the target's 2026 position; offset = where the brightest pixel is (+x west, +y north).
The two σ disagree (the scatter is lowered by the smoothing of the line-up step, and very bright stars are not noise-limited), so **both are given and neither is a precise detection significance**.

---

## Add-ups (afternoon, on the website now)

| Target, detector | Exposures added per visit | Wavelength at the star across the add-up (µm) | Flagged / no value | What we measured |
|---|---|---|---|---|
| Barnard's Star, D2 | 8, 8, 8 (of 18, 18, 25) | 1.23–1.63, 1.25–1.63, 1.31–1.54 | 2.6–3.6% / 0.2–0.5% | Centre saturated or flagged in every exposure (striped); ring empty in visits 2–3, so no position check from these pixels. |
| Epsilon Indi B, D2 | 8, 8, 8, 7, 8 | 1.24–1.64, 1.16–1.64, 1.11–1.58, 1.10–1.54, 1.15–1.56 | 0% / 0% | At the ring centre in all 5 visits: σ (file) 160–266. The Apr 2026 exposure with 30% flagged pixels is filled by the other 6. |
| WISE 0855, D2 | 8, 8, 6, 8 | 1.28–1.63, 1.25–1.51, 1.28–1.44, 1.16–1.48 | 0% / 0% | The background dot: offset (+1 W, +1 N) in 3 visits, (+1 W, 0) in Dec 2025; σ (file) 30–42. Does not follow WISE 0855's 1.3 px/yr westward motion. |
| WISE 0855, D6 | 3, 19, 21 (all) | 4.85–5.00, 4.41–4.97, 4.41–4.96 | 0% / 0% | **May 2025:** σ (file) 2.4, scatter 3.6: nothing clear. **Nov 2025:** σ (file) 11.1, scatter 14.7, offset (0, 0). **Apr 2026:** σ (file) 12.6, scatter 15.4, offset (+1 W, 0). |
| RW Aurigae, D2 | 8, 8, 8 | 1.18–1.39, 1.12–1.65, 1.11–1.64 | 0% / 0% | Bright, at the ring centre in all visits. |
| R Draconis, D2 | — | — | — | Add-up not made yet: IRSA's search for its 2,483 images kept timing out on 31 Oct. The website still shows the single exposures. |

**WISE 0855 D6 checks (Nov 2025 and Apr 2026):**
- **Not one odd exposure:** leaving out any single exposure keeps σ (file) at 10.1–11.4 and 12.0–12.6; each half of the exposures alone gives 9.2 / 6.4 and 8.4 / 9.4.
- **Motion:** the brightest pixel moved 1 px west between the visits. WISE 0855's proper motion (about 8.1″/yr west) predicts about 0.6 px west over those 0.44 years. Same direction; a brightest pixel is only a ±0.5 px position, so this is **consistent, not a measurement**.
- **Not proven to be WISE 0855:** the D2 background object is 1 px away (offset +1 W, +1 N). Whether it adds light in D6 is unknown. Needs a proper position fit (Day 3) and its identity (open question 2).
- **May 2025 sky:** 0.14 MJy/sr against 0.09 in the other visits (after ZODI subtraction) and noise 0.029 against 0.011 (only 3 exposures). Cause of the brighter sky not checked.
- One Nov 2025 exposure has a very bright, very noisy pixel at the ring (VARIANCE says σ about 2.6 MJy/sr, so its weight in the add-up is tiny). Cause not checked.

**What the add-ups change:**
1. Less noise: WISE 0855 D2 noise went from about 0.014 to 0.007 MJy/sr (8 exposures; √8 would give 0.005).
2. Flagged pixels are filled from other exposures (Eps Ind B Apr 2026: 30% → 0%), except where every exposure is flagged (Barnard's centre).
3. **Each add-up mixes wavelengths** across most of the detector (e.g. Barnard visit 1: 1.23–1.63 µm), because the LVF filter gives every exposure its own wavelength. Fine for *where* things are; **no brightness comparisons** from these frames. The label shows the range.

Checks: `scripts/compare_frames.py` against the morning frames: same grid and visits; correlation 0.82–0.98 for Barnard, WISE 0855 D2, RW Aur and four of the five Eps Ind B visits. Lower where expected: Eps Ind B Apr 2026 0.75 (the single had 30% flagged), WISE 0855 D6 0.24–0.43 (single exposures were mostly noise). Screenshots: `notes/screenshots/day2_barnard_d2_coadd.png`, `day2_wise0855_d6_coadd.png`.

---

## Single exposures (morning; first website frames, replaced by the add-ups)

| Target, detector | Visits | Wavelength at the star (µm) | Flagged | What we see |
|---|---|---|---|---|
| Barnard's Star, D2 | 3 (Aug 2025, Mar 2026, Aug 2026) | 1.235, 1.314, 1.539 | 4.0, 8.8, 5.4% | Very bright; the centre has **no value** in every visit (saturated; 0.7–1.2% of pixels). |
| Epsilon Indi B, D2 | 5 (Apr 2025 – Oct 2026) | 1.270, 1.638, 1.160, 1.537, 1.336 | 1.9, 1.0, 0.7, **30.1**, 9.2% | Clear dot exactly at the ring in all 5 visits (180–450 sigma). |
| WISE 0855, D2 | 4 (May 2025 – May 2026) | 1.627, 1.375, 1.342, 1.438 | 0.4–2.4% | A dot **inside the ring, 1 px west and 1 px north of its centre** (about 9″), on the same pixel in all 4 visits (25–34 sigma). |
| WISE 0855, D6 | 3 (May 2025, Nov 2025, Apr 2026) | 4.997, 4.972, 4.925 | 0.1–0.7% | At the ring: 2.1, 5.5, 2.4 sigma; the brightest pixel near the ring is in a different place each visit. **Not a clear detection.** |
| RW Aurigae, D2 | 3 (Sep 2025, Mar 2026, Sep 2026) | 1.179, 1.533, 1.225 | 2.0, 1.9, 5.7% | Bright dot at the ring in all visits. |
| R Draconis, D2 | 3 (Jun 2025, Dec 2025, Jun 2026) | 1.104, 1.400, 1.384 | 14.1, 12.1, 4.5% | The centre has **no value** in all 3 visits (saturated; 1.4–3.1% of pixels). |

## What this means (and does not mean)

1. **WISE 0855 in D2:** the dot inside the ring does not move in a year, while WISE 0855 moves about 8″ a year (about 1.3 px). So it is a **background object, not WISE 0855**. It is not in SIMBAD (nothing within 29″). What it is: **unknown** (Gaia check not done: ESA timed out, IRSA answered 502 on 31 Oct).
2. **WISE 0855 in D6:** in single exposures we **cannot yet say it is seen**. The challenge says it appears at 4–5 µm; an add-up of each visit's exposures (3, 19 and 21 D6 exposures in the three visits) is the honest test. Until then the website says "not clearly seen".
3. **Wavelength changes between visits** inside one detector (SPHEREx's LVF filter): Barnard D2 goes from 1.235 to 1.539 µm. Brightness differences between frames can come from that, so **no brightness claim** for RW Aur or R Dra from these frames.
4. **Saturated centres** (Barnard, R Dra) have no value. They are shown striped and counted (`pct_no_value`), never painted black.
5. **Barnard's Star motion:** expected about 1.7 px north from the first to the last visit (10.4″ a year × 0.99 year ÷ 6.15″). A rough centre-of-light check on the earlier sample put the measured shift at about 2.4 px; with a saturated centre and single exposures that is **not** a measurement. The proof is the Gaia comparison (Day 3).
6. **Alignment sanity check** (Barnard D2, earlier sample): the star's measured position differed from the expected one by 0.54, 0.58 and 0.78 px in the three visits. Rough; a background-star check (Day 3, with Gaia) is the real test.
7. **D2 range:** the files say 1.103–1.650 µm (`em_min`/`em_max`), our `config.DETECTORS` says 1.10–1.62. Not yet explained; check the SPHEREx Explanatory Supplement.

Screenshots: `notes/screenshots/day2_barnard_d2_flipbook.png`, `day2_barnard_blink_flags.png`, `day2_wise0855_d2_note.png`, `day2_wise0855_d6.png`, `day2_mobile_eps_ind_b.png`.

## Open questions (for [Friend's name]: [`docs/plan/FRIEND_REVIEW_GUIDE.md`](../docs/plan/FRIEND_REVIEW_GUIDE.md) Part D)

1. **Is the D6 source at the WISE 0855 ring WISE 0855?** (Add-ups section above.)
2. **The dot 9″ from WISE 0855 in D2:** what is it? Its position is about **RA 133.7580°, Dec −7.2405°** (1 px west and 1 px north of the ring centre 133.759765°, −7.242186°). *Correction:* the morning version of this file gave the ring centre (133.7598°, −7.2422°) as the dot's position.
3. **Epsilon Indi B, Apr 2026 (`2026W17_2A_0403_1`, D2):** 30.1% flagged in that exposure. Which flag bits, and why?
4. **R Draconis:** 3 D2 visits here, 9 epochs in the Day 1 report (all detectors grouped together). Which visits should the flipbook show?
