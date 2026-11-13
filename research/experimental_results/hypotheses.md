# Hypotheses, scored

Each criterion is scored 1–5 and weighted: novelty 25%, scientific significance 20%, data availability 15%,
feasibility 15%, ability to validate 15%, compatibility with the existing pipeline 10%. Total = weighted mean × 20
(maximum 100). "Status" says what was done in this investigation.

| # | Hypothesis | Nov | Sig | Data | Feas | Val | Pipe | Score | Status |
|---|---|---|---|---|---|---|---|---|---|
| H1 | A measurable fraction of TESS-EBs entries put the eclipse on the wrong star: the period-matched Gaia DR3 eclipsing binary is a different, neighbouring star | 4 | 4 | 5 | 5 | 4 | 5 | 88 | **tested** — 278 of 1,543 Gaia-matched entries (265 with the real source absent from TESS-EBs) |
| H2 | SPHEREx (6.2″ pixels) can show directly, star by star, which star eclipses | 4 | 4 | 4 | 4 | 5 | 5 | 85 | **tested** in five regions |
| H3 | The TESS depths of those entries are what dilution of the Gaia binary's eclipse predicts | 3 | 3 | 5 | 5 | 4 | 4 | 77 | **tested** — 242/245 physically possible; implied depths match correctly attributed binaries |
| H4 | The misattribution rate rises in crowded fields (low galactic latitude) and for shallow TESS depths | 3 | 3 | 5 | 5 | 4 | 4 | 77 | **tested** — 30% at \|b\| < 5° vs 8–9% at \|b\| > 30° |
| H5 | Catalogue conflicts (VSX/ASAS vs Gaia, MACHO/SIMBAD vs OGLE) can be settled by SPHEREx | 4 | 3 | 4 | 4 | 4 | 5 | 78 | **tested** in R3 and R5 |
| H6 | All-star forced PSF photometry with a pixel-integrated core + wing beats one/two-star circles | 2 | 3 | 5 | 5 | 5 | 5 | 77 | **tested** — χ² halved, 11.4σ → 14.1σ (kept) |
| H7 | TESS-EBs' "primary" is sometimes the shallower eclipse (prim_pos ≈ 0.5 in 222 entries) | 3 | 2 | 5 | 5 | 4 | 4 | 73 | **tested** for R2 (labels swapped, confirmed by ASAS-SN epoch); not tested catalogue-wide |
| H8 | Eclipse depth ratio across 0.75–5 µm measures the temperature ratio of the two stars | 3 | 3 | 4 | 4 | 3 | 4 | 68 | **partly tested** (R2, R4 depth spectra; too few points per bin for a temperature fit) |
| H9 | Eclipse timing has drifted since TESS (period change, apsidal motion, third body) | 3 | 3 | 4 | 4 | 3 | 4 | 68 | **tested** — R1 not significant, R2 18–24 min early (2.6σ, consistent with a small period error), R4 0 ± 2 min |
| H10 | Reference stars for ensemble photometry must be constant at all phases, not only out of eclipse | 2 | 2 | 5 | 5 | 5 | 5 | 73 | **tested** — bug found and fixed |
| H11 | A PSF shape that varies with wavelength inside a detector improves photometry | 2 | 2 | 5 | 5 | 5 | 5 | 73 | **tested — rejected** (σ varies < 4% within a detector) |
| H12 | A blind variability search of every Gaia star in the five fields finds variables not in VSX/Gaia | 4 | 3 | 4 | 3 | 3 | 4 | 70 | **tested** (see report) |
| H13 | SPHEREx can detect eclipses of G ≈ 16 binaries in the deep fields | 2 | 2 | 4 | 4 | 4 | 5 | 64 | **tested** in R2 (G 15.5) and R5 (G 16.2) |
| H14 | Third light from the TIC star can be measured in SPHEREx and fed back to TESS models | 3 | 3 | 3 | 3 | 2 | 3 | 57 | not tested (needs TESS pixel data) |
| H15 | Circumbinary dust: infrared excess at 3–5 µm in eclipsing binaries | 3 | 4 | 3 | 2 | 2 | 2 | 56 | not tested (needs absolute calibration and SED models) |
| H16 | Ice absorption (3.0 µm H2O, 4.27 µm CO2) toward the young stellar objects in LH 47 | 3 | 3 | 3 | 2 | 2 | 2 | 52 | not tested (outside the eclipse/flipbook scope) |
| H17 | Ellipsoidal/reflection amplitude depends on wavelength | 2 | 2 | 3 | 3 | 2 | 3 | 48 | not tested (needs more exposures outside eclipse) |
| H18 | Eccentric orbits: SPHEREx secondary eclipse phase differs from TESS | 2 | 2 | 4 | 4 | 3 | 4 | 59 | **tested** for R4 (secondary on time: −0.1 ± 2.4 min) |
| H19 | The 3,039 entries with no Gaia DR3 EB are mostly shallow or long-period (Gaia sensitivity) | 2 | 2 | 5 | 5 | 3 | 3 | 63 | partly (depth table in `misattribution_trends.txt`) |
| H20 | Duplicate TESS-EBs pairs are mostly one binary seen twice | 1 | 2 | 5 | 5 | 4 | 5 | 65 | done before this investigation (overnight survey) — **not counted as new** |
| H21 | The TESS-EBs period of some misattributed entries is wrong enough to lose the eclipse times (R5: 6 × 10⁻⁴ d) | 3 | 2 | 4 | 4 | 4 | 4 | 67 | **tested** in R5 |
| H22 | Spurious brightening of all field stars during the target's eclipse indicates an ensemble-photometry bias | 2 | 2 | 5 | 5 | 5 | 5 | 73 | **tested** — same as H10 |

Rejected or not supported: H11 (wavelength PSF), the R1 timing offset (85 ± 47 min, later 33 ± 49 min), the
"infrared depth reversal" reading of R2 (H7 explains it), the 4% "dip" of a bright R4 control star (systematic).

Post-hoc correction (11:20): the H1 novelty score (4) was given before Zasche 2024/2025 and Coughlin et al. 2014
were found; they establish the method (catalogue cross-checks to find the true source of blended eclipses) for OGLE,
ASAS-SN/TESS doubly-eclipsing candidates and Kepler, though not for TESS-EBs. With novelty 3, H1 scores 83 instead
of 88 and ranks second after H2 (85, the SPHEREx test of H1). The selected research question combines H1 and H2,
so it does not change.
New candidate from the R5 re-run (not one of the 22 pre-registered hypotheses): OGLE-LMC-ECL-39123 eclipses later
than the OGLE-IV ephemeris (+61 ± 24 min SPHEREx, +139 min TESS 2019) — class C.
