# Research gap matrix (Stage D)

Each hypothesis has the 14 required fields. References R1–R17 are listed in `LITERATURE_REVIEW.md`.
"Reusable" names refer to code in this repository (`backend/app/…`, `research/…`) or to the scripts written for this
mission (`research/discovery_2026/scripts/…`).

Scoring weights: novelty 25, data availability 20, feasibility 15, scientific importance 15, validation potential 15,
reproducibility 10 (total 100). **Data gate:** a hypothesis whose data score is below 10/20 is ineligible for
primary/secondary regardless of its total, so novelty cannot compensate for missing data.

---

## H1 — Ice-band variability of mid-IR-variable embedded protostars (population, with controls)

1. **Question:** Do H2O (3.05 µm) and CO2 (4.27 µm) ice absorption depths of NEOWISE-variable Class I/flat protostars change between SPHEREx visits more than those of W2-matched non-variable protostars?
2. **Why it matters:** Tests whether accretion variability processes ices on year timescales; determines whether the 22% variable SPLICES targets (R2) can be measured with merged visits.
3. **Established:** Ice bands exist and are measured statically (R2, R4, R6); EC 53 shows no change across a burst (R8); single edge-on disks show changes (R10, R11).
4. **Unanswered:** How common ice changes are in variable protostars; the size of any change relative to continuum change.
5. **Data products:** DR1 + QR3 L2 images (D3–D6), calibration (CWAVE, CBAND, SAPM, ePSF), SPLICES (`w2var_class`, `w2varamp`), AllWISE positions.
6. **Reusable:** flag decoding (`backend.app.flags`), SIA2 query patterns from the backend, `research/` timing helpers.
7. **New algorithms:** S3 range-read stamp extractor with RICE tile decompression (`spx_s3.py`); forced ePSF photometry with neighbours (`phot.py`); joint multi-epoch ice fit with shared band shape and per-group normalisation (`ice_fit.py`).
8. **Observations:** ≥ 2 (preferably 3) complete visits per band per target.
9. **Measurements:** per-epoch τ, EW, continuum; Δτ, ΔEW, Δln F_cont; no-change F-test p-value.
10. **Validation:** EC 53 known null (R8); V1647 Ori (R12); matched controls; background stars; analysis variants (aperture vs PSF, continuum windows, drift on/off, curvature).
11. **Alternatives:** continuum-shape change (scattered light, water vapour, veiling), blending with neighbours, nebulosity, within-visit variability, saturation.
12. **Positive meaning:** first population evidence of year-scale ice processing (or line-of-sight change) in variable protostars.
13. **Null meaning:** an upper limit on |Δτ| per unit continuum change for a population; supports R8's interpretation and tells the Ices pipeline that merged-visit ice depths are stable within the limit.
14. **Biggest risk:** H2O continuum systematics (~0.1–0.3 in τ, found in V1647 Ori) larger than real changes.

Scores: novelty 21, data 18, feasibility 12, importance 12, validation 13, reproducibility 9 → **85**.

## H2 — Ice response coefficient d ln N_ice / d ln L versus envelope models

1. **Question:** Is the population slope of Δ ln τ versus Δ ln F_cont consistent with the −0.25 (ρ ∝ r^−1.5) or −0.5 (ρ ∝ r^−2) envelope-sublimation expectation, or with zero?
2. **Why:** Converts a detection or non-detection into a physical constraint on where the ice lies relative to the sublimation radius.
3. **Established:** Snow-line motion in disks (R16); envelope chemistry models (R15).
4. **Unanswered:** Any observational coefficient for envelopes.
5. **Data:** As H1.
6. **Reusable:** H1 outputs.
7. **New:** Errors-in-variables regression with control-derived systematic floor.
8. **Observations:** H1 targets with |Δ ln F_cont| ≳ 0.3.
9. **Measurements:** slope ± error.
10. **Validation:** Control slope (should be 0); bootstrap over targets.
11. **Alternatives:** Continuum-dependent fitting bias would produce a spurious slope (V1647 Ori shows this risk).
12. **Positive:** Measured coefficient → ice location.
13. **Null:** Upper limit on the coefficient; ice dominated by cold outer envelope.
14. **Risk:** Few targets with large continuum change; coupled to H1 systematics.

Scores: 20, 18, 11, 12, 11, 9 → **81** (analysed as part of H1).

## H3 — Central ice deficit in further prestellar cores (coreshine)

1. **Question:** Do dense cores other than L1544, CrA 151, L260, L1512 (R5) show a central drop in coreshine-derived τ(H2O)?
2. **Why:** R5 calls the deficit unexplained; more cores test whether it is general.
3. **Established:** Method and four cores (R5).
4. **Unanswered:** Generality; dependence on central density.
5. **Data:** DR1 L2 images (diffuse surface brightness), ZODI extension, cores with coreshine (Pagani et al. lists), Herschel column density maps.
6. **Reusable:** stamp reader (larger cutouts), calibration.
7. **New:** diffuse-light spectral mapping with zodi and stellar removal; Bonnor–Ebert scattering model (R5 used radiative transfer).
8. **Observations:** One epoch is enough (static).
9. **Measurements:** τ(H2O) radial profile.
10. **Validation:** Reproduce R5's L1544 profile.
11. **Alternatives:** Saturation of scattered light, background variation, geometry.
12. **Positive:** Generality of the deficit.
13. **Null:** Deficit specific to the R5 cores.
14. **Risk:** Diffuse-light systematics; new modelling substantially beyond existing code; R5 authors likely extending it.

Scores: 18, 15, 6, 12, 10, 7 → **68**.

## H4 — Spectral evolution of new infrared transients (FU Ori candidates) across visits

1. **Question:** Do newly brightening embedded YSOs show FUor-like spectral evolution (CO 2.3 µm, H2O vapour) between visits?
2. **Why:** Classification of outbursts.
3. **Established:** R7 classified WTP16aakapb/WTP15aaavof etc.
4. **Unanswered:** New events after R7.
5. **Data:** DR1/QR3, NEOWISE/WISE (NEOWISE ended 2024), Gaia alerts.
6. **Reusable:** stamp extractor, photometry.
7. **New:** transient search across visits (difference spectra).
8. **Observations:** ≥ 2 visits.
9. **Measurements:** Δ spectrum, band ratios.
10. **Validation:** recover R7 objects.
11. **Alternatives:** artefacts (ghosts, persistence), asteroids.
12. **Positive:** new outburst identified.
13. **Null:** no new events in searched area.
14. **Risk:** Direct overlap with R7 group; blind search scope large.

Scores: 12, 16, 8, 10, 10, 8 → **64**.

## H5 — Ice variability in known edge-on disks (HV Tau C analogues)

1. **Question:** Do edge-on disks (HV Tau C, HK Tau B, PDS 453, Flying Saucer) show SPHEREx visit-to-visit τ changes?
2. **Why:** Tests R10/R11 claims with a new instrument.
3. **Established:** R10 (τ 1.65 → 1.09), R11 (possible profile change).
4. **Unanswered:** Confirmation.
5. **Data:** DR1/QR3; targets are faint (K ~ 12–15), partially blended with primaries (HV Tau AB 4″ away ≪ 6.2″ pixel).
6. **Reusable:** all H1 scripts.
7. **New:** none beyond H1, but blending model needed.
8. **Observations:** 3 visits.
9. **Measurements:** τ per visit.
10. **Validation:** R10 values.
11. **Alternatives:** blending with bright companions dominates.
12. **Positive:** confirmation.
13. **Null:** limit.
14. **Risk:** HV Tau C and HK Tau B are unresolved from their bright primaries at 6″ pixels → infeasible.

Scores: 15, 8 (blending makes the needed data unusable), 6, 9, 9, 8 → 55, **fails data gate**.

## H6 — Temporal stability of interstellar ice toward background stars

1. **Question:** Are τ(H2O), τ(CO2) toward non-variable reddened background stars constant between visits?
2. **Why:** Systematic floor for H1; calibration check for the Ices pipeline.
3. **Established:** Interstellar ice should not change on months (cloud crossing time ≫ yr).
4. **Unanswered:** SPHEREx empirical floor.
5. **Data:** SPLICES MAIN background stars with high A_V, NEOWISE non-variable.
6. **Reusable:** H1 pipeline.
7. **New:** none.
8. **Observations:** 3 visits.
9. **Measurements:** Δτ distribution.
10. **Validation:** Must be consistent with zero.
11. **Alternatives:** none needed (control).
12. **Positive (non-zero):** pipeline systematic.
13. **Null:** validated floor.
14. **Risk:** low science value on its own.

Scores: 6, 16, 13, 6, 14, 9 → **64** (used as control inside H1).

## H7 — CO ice (4.67 µm) loss in outbursts

1. **Question:** Does the volatile CO ice band weaken after continuum brightening?
2. **Why:** CO sublimates at ~20 K — most sensitive to heating (R15).
3. **Established:** CO ice in protostars; burst CO desorption models.
4. **Unanswered:** Observed CO-ice response.
5. **Data:** D6 channels around 4.67 µm (R ≈ 130); S/N low; gas-phase CO rovibrational lines blend at this resolution.
6. **Reusable:** H1.
7. **New:** CO band model with gas-phase contamination.
8. **Observations:** ≥ 2 visits.
9. **Measurements:** τ(CO) per visit.
10. **Validation:** EC 53 (R8 no change).
11. **Alternatives:** gas-phase CO emission/absorption variability (R9 shows CO line variability in EC 53).
12. **Positive:** CO desorption caught.
13. **Null:** limit.
14. **Risk:** R9 shows CO gas lines vary — degenerate with ice at R ≈ 130.

Scores: 18, 12, 7, 11, 7, 8 → **63**.

## H8 — 3.3 µm PAH emission variability in nebulae around variable YSOs (light echo)

1. **Question:** Does PAH 3.3 µm emission in reflection nebulae respond to central-source outbursts?
2. **Why:** PAH excitation echo maps geometry.
3. **Established:** PAH maps (R6).
4. **Unanswered:** time variation.
5. **Data:** DR1/QR3 diffuse emission.
6. **Reusable:** stamp extractor (larger stamps).
7. **New:** diffuse difference imaging across visits with different detector positions/channels.
8. **Observations:** ≥ 2 visits.
9. **Measurements:** PAH band intensity per visit.
10. **Validation:** non-variable nebulae.
11. **Alternatives:** zodi change, detector position systematics.
12. **Positive:** first SPHEREx PAH echo.
13. **Null:** limit.
14. **Risk:** channel-shift between releases plus zodi model differences.

Scores: 19, 12, 5, 9, 7, 7 → **59**.

## H9 — Water-vapour vs ice degeneracy in FUors across epochs

1. **Question:** Does photospheric H2O vapour absorption in FUors change between visits, contaminating "ice" depths?
2. **Why:** V1647 Ori showed apparent Δτ not robust to continuum choice; vapour (R12) is a candidate cause.
3. **Established:** FUor H2O vapour bands.
4. **Unanswered:** amplitude at SPHEREx resolution per visit.
5. **Data:** DR1/QR3 for known FUors (most excluded as R7 or as known outbursters).
6. **Reusable:** H1.
7. **New:** vapour template.
8. **Observations:** 3 visits.
9. **Measurements:** 1.9/2.7 µm vapour depths.
10. **Validation:** FU Ori (excluded target list), V1057 Cyg.
11. **Alternatives:** ice.
12. **Positive:** explains spurious Δτ.
13. **Null:** —
14. **Risk:** small sample, overlap with known-object literature.

Scores: 10, 14, 9, 8, 8, 8 → **57**.

## H10 — Merged-visit bias in SPHEREx ice depths of variable sources

1. **Question:** How much does merging all visits (as in R4 and the Ices pipeline default) bias τ and inflate χ² for variable protostars, compared with per-visit fitting?
2. **Why:** R2 states variability "can introduce artificial features or mask true absorption"; nobody has quantified it on real data.
3. **Established:** qualitative warning (R2).
4. **Unanswered:** magnitude of the effect versus variability amplitude.
5. **Data:** same as H1 (no new data).
6. **Reusable:** H1 pipeline.
7. **New:** merged-spectrum fit option in the same model.
8. **Observations:** H1 targets.
9. **Measurements:** τ_merged − mean(τ_epoch), χ²_merged/χ²_epoch, versus Δ ln F_cont.
10. **Validation:** controls should show no bias.
11. **Alternatives:** none (methodological).
12. **Positive:** quantified bias → recommendation for the Ices pipeline.
13. **Null:** merging is safe within stated limits.
14. **Risk:** method-oriented rather than astrophysical.

Scores: 16, 18, 13, 10, 12, 9 → **78**.

## H11 — Ice column change during YSO dimming events (dippers / extinction events)

1. **Question:** When an embedded YSO dims by extinction, does τ_ice increase in proportion to A_V (icy outer material) or not (warm inner-disk dust)?
2. **Why:** Locates the occulting material.
3. **Established:** extinction-driven dippers; HV Tau C-like changes (R10).
4. **Unanswered:** ice/A_V ratio of occulting material.
5. **Data:** H1 VAR objects with NEOWISE "D" (dipper/decline) or "B"/"L" classes; need colour change consistent with extinction.
6. **Reusable:** H1.
7. **New:** colour-based A_V change from 1–2 µm SPHEREx continuum.
8. **Observations:** 2–3 visits spanning a dimming.
9. **Measurements:** ΔA_V vs Δτ.
10. **Validation:** ISM τ/A_V relation for background stars.
11. **Alternatives:** accretion change.
12. **Positive:** icy occulter.
13. **Null:** occulter is warm.
14. **Risk:** few dimming events inside the 1-yr SPHEREx window.

Scores: 18, 12, 9, 10, 9, 8 → **66**.

## H12 — Br α / Pf β accretion-line variability vs ice

1. **Question:** Do H I line strengths (4.05, 4.65 µm) track continuum changes?
2. **Why:** accretion diagnostic.
3. **Established:** lines visible in JWST spectra.
4. **Unanswered:** SPHEREx detectability.
5. **Data:** DR1/QR3; line EW ≪ channel width at R ≈ 130.
6. **Reusable:** H1 stamp extractor and photometry.
7. **New:** unresolved-line model convolved with each channel bandpass.
8. **Observations:** ≥ 2 visits with channels covering 4.05 and 4.65 µm.
9. **Measurements:** line EW per visit.
10. **Validation:** EC 53 (R8 line fluxes).
11. **Alternatives:** CO2 ice wing at 4.05 µm, CO at 4.65 µm.
12. **Positive:** accretion-line variability measured with SPHEREx.
13. **Null:** lines below detectability.
14. **Risk:** lines undetectable at SPHEREx resolution in most protostars.

Scores: 12, 7, 5, 9, 6, 7 → 46, **fails data gate**.

## H13 — Periodic protostars: ice vs phase (EC 53-like, other periodic NEOWISE sources)

1. **Question:** Do periodic (NEOWISE class P) protostars show phase-dependent ice depths?
2. **Why:** Repeated bursts offer repeated tests.
3. **Established:** EC 53 null (R8).
4. **Unanswered:** other periodic protostars.
5. **Data:** SPLICES `w2var_class` = P; three SPHEREx visits sample arbitrary phases.
6. **Reusable:** H1 pipeline.
7. **New:** phase assignment from NEOWISE periods.
8. **Observations:** 3 visits at different phases.
9. **Measurements:** τ versus phase.
10. **Validation:** EC 53.
11. **Alternatives:** as H1.
12. **Positive:** ice responds in some.
13. **Null:** confirms R8 generally.
14. **Risk:** small number of P-class sources in the magnitude window; three visits poorly sample phase.

Scores: 15, 11, 10, 9, 10, 8 → **63**.

---

## Summary table

| ID | Hypothesis | Nov 25 | Data 20 | Feas 15 | Imp 15 | Valid 15 | Repro 10 | Total | Data gate |
|---|---|---|---|---|---|---|---|---|---|
| H1 | Ice variability, variable protostars vs controls | 21 | 18 | 12 | 12 | 13 | 9 | **85** | pass |
| H2 | Ice response coefficient | 20 | 18 | 11 | 12 | 11 | 9 | 81 | pass |
| H10 | Merged-visit bias | 16 | 18 | 13 | 10 | 12 | 9 | **78** | pass |
| H3 | Prestellar central ice deficit, new cores | 18 | 15 | 6 | 12 | 10 | 7 | **68** | pass |
| H11 | Ice in dimming events | 18 | 12 | 9 | 10 | 9 | 8 | 66 | pass |
| H4 | IR transient spectral evolution | 12 | 16 | 8 | 10 | 10 | 8 | 64 | pass |
| H6 | Background-star ice stability | 6 | 16 | 13 | 6 | 14 | 9 | 64 | pass (control) |
| H7 | CO ice loss | 18 | 12 | 7 | 11 | 7 | 8 | 63 | pass |
| H13 | Periodic protostars | 15 | 11 | 10 | 9 | 10 | 8 | 63 | pass |
| H8 | PAH echo | 19 | 12 | 5 | 9 | 7 | 7 | 59 | pass |
| H9 | Vapour vs ice in FUors | 10 | 14 | 9 | 8 | 8 | 8 | 57 | pass |
| H5 | Edge-on disk ice variability | 15 | 8 | 6 | 9 | 9 | 8 | 55 | **fail** |
| H12 | H I line variability | 12 | 7 | 5 | 9 | 6 | 7 | 46 | **fail** |

## Decision

* **Primary:** H1, with H2 as its physical-interpretation analysis and H6 as its control arm.
* **Secondary:** H10 (merged-visit bias) — it uses the same data, needs one extra model option, and answers a
  question raised by the official Ices overview (R2). It ranks above the mission's suggested secondary (H3) because
  H3 needs a substantial new diffuse-light modelling effort (feasibility 6/15).
* **Backup:** H3 (prestellar cores), excluding L1544, CrA 151, L260, L1512.
* The mission's third suggestion (H4, transients) ranks lower because of direct overlap with R7.
Details and the justification are in `PRIMARY_RESEARCH_DECISION.md`.
