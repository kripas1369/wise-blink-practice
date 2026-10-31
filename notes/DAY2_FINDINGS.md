# Day 2 findings: what the real SPHEREx sample frames show (31 Oct 2026)

Measured by Kripas on the sample frames in `frontend/frames/` (made by `scripts/sample_frames.py`: one exposure per visit, IMAGE − ZODI, official flag mask, 29 × 29 grid of 6.15″ pixels centred on the 2026.0 position).
Every website note in the orange box ("Before you trust your eyes") comes from this file.

**How "sigma" was measured:** sky = median of the good pixels in the frame; noise = 1.4826 × median absolute deviation; signal = (brightest pixel − sky) / noise. "Ring" = the 3 × 3 pixels at the target's 2026 position. Single exposures only, so these are rough; add-ups will be better.

---

## Per target

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
6. **Alignment sanity check** (Barnard D2, earlier sample): the star's measured position differed from the expected one by 0.54, 0.58 and 0.78 px in the three visits. Rough; [Friend's name]'s background-star check (Day 2 Step 5) is the real test.
7. **D2 range:** the files say 1.103–1.650 µm (`em_min`/`em_max`), our `config.DETECTORS` says 1.10–1.62. Not yet explained; check the SPHEREx Explanatory Supplement.

Screenshots: `notes/screenshots/day2_barnard_d2_flipbook.png`, `day2_barnard_blink_flags.png`, `day2_wise0855_d2_note.png`, `day2_wise0855_d6.png`, `day2_mobile_eps_ind_b.png`.

## Open questions (for [Friend's name], `FRIEND_DAY2_STEPS.md` Step 10)

1. **R Draconis:** 3 D2 visits here (the sample keeps D2 images first, then groups), but 9 epochs in the Day 1 report (all detectors grouped together). Which visits should the flipbook show?
2. **Epsilon Indi B, Apr 2026 (`2026W17_2A_0403_1`, D2):** 30.1% flagged. Which flag bits? Is the frame usable?
3. **The dot 9″ from WISE 0855 in D2:** what is it? Gaia DR3 (IRSA table `gaia_dr3_source`) around RA 133.7598°, Dec −7.2422°.
