# Progress log: SPHEREx TimeLens discovery investigation

Times are local (UTC+5:45), 13 November 2026.

## Before this investigation (already done, not counted as new)

- Overnight 12–13 Nov: 11 open TESS-EBs duplicate pairs tested with SPHEREx DR1 (`notes/SPHEREX_BLEND_SURVEY.md`).
  Six pairs resolved in total: 233058262, 140659978, 150101476, 258918831, 269696430, 420114772 (probable).
  Validated on 276935987 (VSX + Gaia), 233058262 and WW Dra (198242678).

## 13 Nov

- **09:05** Started. Two background helpers: code audit (`EXISTING_PIPELINE_AUDIT.md`) and literature review
  (`LITERATURE_REVIEW.md`).
- **09:06** Idea from the earlier data: in two "too close" duplicate pairs (155884454/449 and 92938279/280), VSX and
  Gaia put the same-period eclipsing binary on a *third* star 21–38″ away. Question: how often does this happen
  across the whole TESS-EBs catalogue?
- **09:07** `tessebs_gaia_xmatch.py`: all 4,582 TESS-EBs entries against the Gaia DR3 eclipsing-binary table
  (2.18 M sources) within 63″. The single uploaded query was aborted by the ESA archive; it works in chunks of 400 rows
  (12 chunks, ~10 min, finished 09:17).
- **09:10** `field_psf.py` (all-star forced PSF photometry) and `field_analysis.py` (normalisation, ensemble
  correction, eclipse tests, variability statistics) written. Validated on TIC 140659978: secondary depth
  16.4 ± 1.3% on the source, −1.4 ± 3.5% on its neighbour (earlier two-star method: 18.8 ± 1.8% vs −0.4 ± 1.2%).
- **09:17** PSF experiments on the same 320 exposures:
  - single Gaussian: co-add χ² ≈ 600–1000 in D1–D4, source detected at 11.4σ, neighbour scatter 3.62%;
  - core + wing (pixel-integrated): co-add χ² halved, source 14.1σ, neighbour scatter 2.97% → **kept**;
  - shape interpolated in wavelength within each detector: no change (σ varies < 4% within a detector) → **negative
    result, switched off**.
- **09:17** Cross-match result: 1,265 entries "same star", **278 "other star"**, 3,039 no Gaia EB. Of the 278, 13 are
  known duplicates (the Gaia EB is another TESS-EBs entry) and **265 have their real source missing from TESS-EBs**.
  Expected chance period coincidences: ~2.
- **09:23** `dilution_check.py`: 242 of 245 (98.8%) are physically possible; implied undiluted depths (median 15.7%)
  match the depths of correctly attributed entries (median 16.5%; KS D = 0.095); measured depths are much smaller
  (median 1.0% vs 16.5%, Mann–Whitney p = 1.6 × 10⁻⁸¹). In 88% the listed TIC star is the brighter one.
- **09:25** SPHEREx coverage queries started for 12 candidates (`coverage_candidates.py`), preferring stars not on the
  website's eclipse catalogue.
- **09:45** Five regions chosen (R1–R5, `FIVE_TARGET_SELECTION.md` to follow): TESS-EBs entries whose Gaia DR3
  same-period eclipsing binary is a different star, none on the website's eclipse catalogue, with SPHEREx phase
  error < 0.01 (R5 uses the OGLE clock instead because the TESS one has drifted).
- **10:01** R1 (TIC 179637488, LMC, LH 47): 558 exposures, 134 Gaia stars fitted together. The Gaia binary
  (= OGLE-LMC-ECL-13800) dims 11.5 ± 2.2% (primary) and 9.0 ± 1.6% (secondary); the TIC star LH 47-237 shows
  −2.2 ± 2.3% and −0.3 ± 1.9%. Eclipse timing offset 85 ± 47 min (1.8σ) → **not significant, rejected**.
  Limitation: the PSF wing hits its bound (absorbs the LMC diffuse light).
- **10:09** Ephemeris override (`--eph-json`) added to `field_psf.py`, `field_analysis.py`, `eclipse_timing.py`;
  OGLE-LMC-ECL-39123 clock in `research/data/eph_ogle_lmc_ecl_39123.json` for R5.
- **10:11** R2 (TIC 349156098): 335 exposures, 10 Gaia stars. The Gaia binary (ASASSN-V J071248.16-644303.5,
  G 15.5, 40.6″ away) shows a 21 ± 3% dip at the TESS-EBs primary and a 50–56% dip half a period later; the TIC
  star (G 10.2) shows −2.0 ± 1.4%. So the TESS-EBs signal belongs to the Gaia binary.
  First reading — "secondary deeper than primary in the infrared" — **checked and rejected**: TESS-EBs' polyfit
  places the primary at prim_pos = 0.499; the ASAS-SN (VSX) epoch of the deepest V-band minimum falls at TESS phase
  −0.486, i.e. on the deep SPHEREx eclipse. The catalogue's "primary" is the shallower eclipse; the deeper one is at
  the catalogue epoch bjd0. 222 of 4,413 catalogue entries (5%) have prim_pos ≈ 0.5 (same fraction, 5%, among the
  misattributed entries), so the website's "primary at phase 0" rule picks the shallower eclipse for some of them.
  Timing: both eclipses arrive early by 24 ± 8 and 18 ± 4 min (TESS clock error 8 min), consistent with a period
  ~7 × 10⁻⁶ d shorter than TESS-EBs' 1.2014857 d (2.6σ) — noted, not claimed.
- **10:20** `field_psf.py` now saves every aligned exposure in `frames.npz` (was 24) so difference images and
  flipbooks can be made; R1 and R2 re-run from cached cutouts — R1 numbers reproduced exactly.
  New `make_figures.py` (fold, wavelength-matched difference image, Eclipse-Mode flipbook GIF) and
  `significance.py` (empirical false-alarm probability from 1,000 random eclipse-free phase centres).
  - R2 difference image, deep eclipse: box z = −9.5 (D2), −11.3 (D3) at the Gaia binary, +1.5 / −0.6 at the TIC
    star. Empirical test: Gaia binary z = 6.7 (phase 0) and 11.7 (phase 0.48), FAP < 0.001 (limit of 1,000 trials);
    TIC star −0.6 / 1.2; two controls within ±1.6 (one at −3.3, i.e. brighter, not an eclipse).
  - R1 difference image: not decisive in the crowded LMC field (|z| < 2 everywhere; the supergiant 2 px away
    dominates the residuals). Empirical test on the PSF photometry: Gaia binary z = 4.1 / 3.2, FAP < 0.001;
    TIC star 0.1 / 0.8; controls within ±0.7.
- **10:22** `five_target_catalog.csv` written by `five_targets.py`.
- **10:28** Test baseline after all research changes: backend 286 passed / 5 skipped / 1 failed
  (`test_day5.py::test_spectrum_points_are_exactly_the_light_curve_points` — expects detectors [2,5,6] in
  `frontend/frames/wise0855/spectrum.json`, which the owner's uncommitted work of 7 Nov extended to [1…6]; not caused
  by this investigation); frontend 83/83.
- **10:33** R4 (TIC 160195393, Dec +85°): 347 exposures, 8 Gaia stars. Gaia binary (ASASSN-V J171505.23+851208.0)
  primary 30.5 ± 0.8%, secondary 27.6 ± 1.0%, blind scan 30σ; TIC star (TYC 4651-1759-1) −1.4 ± 1.0% / −0.4 ± 1.3%.
  Eclipse times: −0.9 ± 2.2 min and −0.1 ± 2.4 min from the TESS prediction (clock confirmed).
  **Bug found and fixed in `field_analysis.py`:** reference stars for the ensemble correction were chosen by their
  scatter *outside the TESS eclipse windows only*, so in a sparse field the eclipsing binary itself became a
  reference star and its eclipses appeared as spurious *brightenings* (−4% to −9%) of every other star (the TIC star
  read −8.7 ± 2.5%). Now reference scatter uses all exposures, and a second pass drops any reference star with a
  phase-scan dip (SNR > 6, jitter included). After the fix the other stars are consistent with zero; R1 and R2 change
  by < 0.002 in depth; the validation neighbour goes from −4.3 ± 3.4% to −1.1 ± 3.5%.
  **Bug found and fixed in `significance.py`:** weights now include each star's jitter. Before, a bright control star
  (Gaia DR3 1724464661091513600, χ²_red 486) showed a 4.6% / 5.1% "dip" at both eclipse phases (z 5.3 / 5.9); after,
  1.2% (z 1.2) at phase 0 and 4.4% (z 3.2) at phase 0.5, driven by visit-correlated scatter (single points from 0.60
  to 1.16) and one 0.60 point; median in-eclipse flux 0.96–1.00; no Gaia variability flag → **treated as a
  systematic**, and taken as the realistic false-signal level (~4%, ~3σ) for bright stars near the field edge.
- **10:44** Literature check on novelty (web): wrong-star (nearby eclipsing binary) identification is standard for
  TESS *planet candidates* (Panahi et al. 2022, A&A, Gaia photometry; Mistry et al. 2024, MNRAS 527, 4018,
  centroid-based probabilities). TESS-EBs (Prša et al. 2022) uses a centroid-motion test in its validation score and
  notes "the large number of signals that are off target", but the catalogue (v1.0 CSV) lists only the TIC target and
  has no column for the true source or the validation score. No catalogue-wide reassignment of TESS-EBs entries to
  specific Gaia DR3 eclipsing binaries was found in the papers checked.
- **10:47** Trends of the misattribution (`research/out/misattribution_trends.txt`), among the 1,543 entries with a
  period-matched Gaia DR3 EB within 63″ (278 on another star):
  - galactic latitude: 30% at |b| < 5° → 8–9% at |b| > 30° (χ² p = 2 × 10⁻¹⁵) — crowding, as expected for blends;
  - TESS depth: 96% (123/128) of the < 1% entries are on another star, 56% of 1–3%, 4% of > 30% (p = 3 × 10⁻¹⁶²).
    Caveat: Gaia rarely detects < 1% eclipses on the TIC star itself, so the conditional fraction is biased upward;
    the unconditional lower limit is 123 of all 801 TESS-EBs entries shallower than 1% (15%).
  - TIC brightness: 72% for T > 13 (mostly LMC fields), 11% for T < 8.
- **10:50** R3 (TIC 309659126; Gaia binary UCAC4 147-005376 only 7.4″ = 1.26 px from the TIC star): 651
  exposures, 5 stars. Gaia binary primary 21.4 ± 0.9%, secondary 16.1 ± 1.1%, its own periodogram peaks at 0.12414 d
  = P/2 (contact binary; FAP 10⁻⁶⁹); TIC star TYC 8878-311-1 −0.4 ± 0.8% / +0.3 ± 1.0%. Eclipses on time
  (−0.4 ± 1.2, −0.8 ± 1.9 min). **Difference-image centroid** (new in `make_figures.py`: one PSF with free position
  fitted to the stacked wavelength-matched in−out difference, grid search + bootstrap): 0.17 ± 0.09 px from the
  Gaia binary, 1.42 px = 15σ from the TIC star → VSX/ASAS place ASAS J051801-6041.4 on the wrong star; Gaia is right.
  Centroid on R2: 0.02 px from the Gaia binary, TIC star excluded at 3.9σ; R4: 0.03 px, TIC star at 4.0σ;
  R1: not usable (strongest residual 11.6 px away, on noisy faint stars in the nebular LMC field).
- **10:52** R5 (TIC 31511621, OGLE clock): Gaia binary OGLE-LMC-ECL-39123 primary 32.3 ± 2.9% at the OGLE time,
  own periodogram 1.31457 d = P/2 (FAP 3 × 10⁻⁸); TIC star −0.6 ± 0.5%. On the TESS-EBs clock the same eclipses
  fall at TESS phase −0.24 (expected drift 0.215 after 914 cycles); the TESS-EBs period 2.62949 ± 0.00048 d is 1.3σ
  from OGLE's 2.6288690 d → imprecise, not wrong. Timing vs OGLE: +53 ± 22 min (2.4σ; would need P longer by
  2.4 × 10⁻⁵ d over ~1,500 cycles; OGLE gives no period error) → noted, not claimed.
  SIMBAD's type "EclBin" for TIC 31511621 (= MACHO 71.12422.12): the only eclipsing-binary paper in its SIMBAD
  bibliography is TESS-EBs (2022ApJS..258...16P); MACHO (Fraser et al. 2008, AJ 136, 1242) lists it only as a
  long-period-variable candidate → the label most likely propagates the TESS-EBs misattribution.
  Bugs fixed: the OGLE override kept TESS-EBs' secondary position (0.03 instead of 0.5) → `sec_pos = 0.5` added to
  the JSON; `eclipse_timing.py` start value could exceed its bound for faint stars with negative fluxes.
  R5 re-run started with the corrected secondary window (460 new cutouts).
- **10:55** Blind variability search (`experimental_results/blind_variability.txt`): in R2–R5 the top-ranked star
  by Lomb–Scargle FAP is the Gaia binary, at P/2, with no TESS input. In R1, 7 of 8 other significant stars are
  known variables (Gaia/VSX EBs at P/2, LPVs, a Be/S Dor star). Two uncatalogued periodicities **rejected**: R4
  1724476686999945344 (only in the second half of the data) and R1 4658741753164873472 (an LMC B star, but the
  signal is confined to detector D4 — instrumental or 3.3 µm nebular light). No new variable star claimed.
  Correction (11:20): 6 of the 8 are catalogued variables themselves; one is 8.5″ from catalogued variables (a
  slow trend), one is the rejected B star.
- **11:00** `five_target_catalog.csv` now also lists TESS sectors and PSF width per detector. R5 has only TESS
  sectors 11–12, which explains its imprecise TESS-EBs period.
- **11:05** `FINAL_SCIENTIFIC_DISCOVERY_REPORT.md` drafted; every number checked against `results_summary.json`
  and the catalogue outputs (two unsupported phrases removed).
- **11:08** Both background agents (pipeline audit, literature review) had stopped at ~09:15 without writing their
  files. Literature: the 58 PDFs they downloaded are in `research/papers/`; metadata re-fetched from the arXiv API.
  **New, important for novelty:** Zasche 2025 (MNRAS 544, L174) found by VSX + Gaia cross-checks that ⅓ of the
  Rowan et al. 2023 doubly-eclipsing candidates are blends of two binaries tens of arcsec apart; Zasche 2024 did the
  same for OGLE; Coughlin et al. 2014 for Kepler. So the catalogue method is established; our contribution is its
  application to TESS-EBs + SPHEREx confirmation. None of our 278 entries is in Zasche's list (checked by TIC).
  Web searches found no TESS-EBs × Gaia DR3 reassignment and no SPHEREx eclipse light curve. Wrote
  `LITERATURE_REVIEW.md` and `EXISTING_PIPELINE_AUDIT.md` myself.
- **11:11** R5 re-run finished (705 exposures). Gaia binary 32.2 ± 2.7% / 14.8 ± 3.7% (secondary now on 50
  exposures instead of 12), empirical z 11.5 / 5.2; TIC star +0.2 ± 0.5% / +0.6 ± 0.6% (z 0.0 / 0.7); LS 1.3144 d
  (FAP 4 × 10⁻¹²). Difference-image centroid not usable (binary 4 mag fainter than the TIC star).
  Timing vs OGLE: +61 ± 24 and +74 ± 40 min; the TESS-EBs 2019 epoch is also late on the OGLE clock (+139 min,
  cycle 609). Not a clean linear drift → recorded as a timing **candidate (C)**, not claimed.
- **11:15** Tests re-run: backend 286 passed / 5 skipped / 1 pre-existing failure; frontend 83/83 — unchanged.
- **11:18** `misattribution_trends.py` and `blind_search.py` saved as scripts (they had been run inline);
  the trends script reproduces `out/misattribution_trends.txt` identically, the blind search reproduces the
  per-detector numbers and all conclusions.
- **11:23** `FINAL_EXECUTIVE_SUMMARY.md` written; `CODE_CHANGES.md` (changes 8–11), `REPRODUCIBILITY.md`
  (expected results, new scripts) updated. All deliverables present.
- **11:24** The audit agent finished after all and replaced my short `EXISTING_PIPELINE_AUDIT.md` with its 885-line
  audit (kept). Added the source-attribution section and the full test baseline (its own run stopped at the first
  failure). Two of its findings added to the report's limitations: depths are means over the central half of the
  eclipse (lower than depth at minimum), and flagged pixels leak through bilinear resampling (verified in
  `align.align`). Neither affects the attribution result.
