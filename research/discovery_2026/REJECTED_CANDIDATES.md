# Rejected candidates

Every target that showed, or could have been mistaken for, an ice-depth change, and why it is not reported as one.
Numbers: `EXPERIMENTAL_RESULTS/population/pairs.csv` (consecutive pairs), `VALIDATION/scatter_model.csv`,
`EXPERIMENTAL_RESULTS/colour/colour_pairs.csv`. z values are Δ/σ for one consecutive pair; the seven columns are the
baseline and the six alternative analyses (aperture, no drift, with D3, no blue window, curved continuum, narrow red).

## 1. Statistically significant (BH 5 %) but not robust — H2O, variable protostars

| Target (SIMBAD) | Pair | Δτ ± σ | z: base / ap / nodrift / D3 / noblue / curved / narrow | Why rejected |
|---|---|---|---|---|
| SJ20573116p4402374 (2MASS J20573117+4402374, Cygnus) | 0→1 | +0.139 ± 0.037 | 3.7 / 3.8 / 4.4 / 3.1 / **0.7** / 1.7 / 3.0 | vanishes without the blue continuum window; p < 0.01 lost when visits are merged at a 120 d gap; τ only 0.10–0.31 |
| SJ00381870p6306053 (IRAS 00353+6249) | 1→2 | −0.169 ± 0.056 | −3.0 / −3.0 / −2.3 / **−1.4** / −2.4 / −3.2 / −2.8 | fails the D3-continuum variant; 0→1 pair only 2.7σ |
| SJ18570951p0210407 (CXOU J185709.3+021039) | 0→1 | −0.377 ± 0.072 | −5.3 / −4.0 / **+2.0** / +1.4 / −1.6 / −1.2 / −1.6 | sign reverses with no drift term and with D3; coincides with an ×8 fade (Δln F₃.₉₅ = −2.14) of grey colour (R = 0.86); CO2 χ² 640 |
| SJ06123374p1749238 (2MASS J06123374+1749240, Gem OB1) | 1→2 | −0.234 ± 0.072 | −3.3 / −3.3 / −3.3 / −2.5 / **−0.8** / −1.2 / −2.5 | vanishes without the blue window and with a curved continuum |
| SJ07051097m1105081 (2MASS J07051096-1105081, CMa OB1) | 0→1 | −0.138 ± 0.055 | −2.5 / −2.5 / −2.1 / −2.1 / **+0.8** / +0.3 / −2.6 | vanishes without the blue window; τ → 0 at epoch 1; additive grey unabsorbed light fits better than an ice change (ΔBIC −14); only 2 epochs |

SJ06135925p1743210 is the sixth BH-significant target and the only one that passes; see `SCIENTIFIC_RESULTS.md` §4.

## 2. Large changes in fits that fail the quality rule (χ²_red > 15)

| Target | Change | Why rejected |
|---|---|---|
| SJ22280291p6901168 (2MASS J22280298+6901166, L1221 region, A_V 53) | τ_H2O 2.28 → 3.16 → 2.38 (z +5.3, −4.6), anti-correlated with the continuum (97 → 23 → 60 mJy); CO2 BH-significant (p = 0.002) but per-pair z only 1.3 | joint-fit χ²_red 27; vanishes without the blue window (z 1.0); continuum change dims 3.95 µm **four times more** than 2.2 µm (R = 0.26), the opposite of extinction — a change in the warm-dust emission, not in the absorbing column; deep, partly saturated band makes τ sensitive to the continuum model |
| SJ07142692m1203589 (IRAS 07121-1158) | Δτ_H2O +0.29 ± 0.10 (z 2.9) | χ²_red 16.4; z 1.7 with a curved continuum; only 2 epochs |

## 3. Validation and pilot targets

| Target | Why not a result |
|---|---|
| V1647 Ori | Baseline Δτ −0.16 and −0.12 per interval; sign flips without the 2.42–2.72 µm window (H2O vapour in FUor-like spectra); not robust. Partial-covering model fits much worse (ΔBIC +28) — the apparent change is a continuum-window artefact rather than geometry. |
| EC 53 | No change (known answer reproduced). |
| Elias 29, Elias 16 | Saturated cores (W1 ≲ 6): no usable photometry. Excluded from the sample. |

## 4. Controls and background stars

| Group | Observation | Why not a result |
|---|---|---|
| CTRL, H2O | 0 of 9 quality targets with p < 0.05 | control behaviour as expected |
| CTRL, CO2 | 0 of 20 with BH significance | idem |
| BGSTAR, CO2 | 3 of 9 with p < 0.05, none after BH; most background stars have τ_H2O ≈ 0 (diffuse, ice-free extinction) and fail the χ² rule | consistent with the multiple-testing expectation and with crowded, nebulous fields |

## 5. Sample members that are not protostars (found with SIMBAD after the analysis)

| Target | Role | SIMBAD identification | Effect |
|---|---|---|---|
| SJ07375689m2556589 | VAR | V445 Pup — helium nova (2000), dusty | its H2O "ice" (τ 0.23) is in the VAR population statistics; removed in the purity check |
| SJ07142692m1203589 | VAR | IRAS 07121-1158 — planetary-nebula candidate | already rejected (§2); its CO2 pair removed in the purity check |
| SJ20313267p3752317, SJ19534386p3146371 | CTRL | Mira variables | no ice detection (or no complete epoch) |
| SJ19224465p1959065, SJ18561192p0753394 | CTRL | long-period variable (candidate) | idem |
| SJ18522549p0054061 | CTRL | IRAS 18498+0050, AGB candidate | idem |
| SJ18090746m1923037 | CTRL | 2MASS J18090735-1922547, AGB candidate | H2O "detected" (depth 1.8) but fails the quality rule, so not in the statistics; a 3 µm band in an AGB star is probably stellar/circumstellar water, not interstellar ice |
| SJ15051679m5511105 | CTRL | WRAY 16-162, planetary nebula | idem |
| SJ17555845m1624393 | CTRL | G 154-34, high-proper-motion star | idem |
| SJ05352186m0429389 | CTRL | HD 37017, B-type spectroscopic binary (Orion) | idem |

None of these is an ice-detected quality control. Statistics without them: `SCIENTIFIC_RESULTS.md` §3.

## 6. Ideas rejected before the experiment

See `RESEARCH_GAP_MATRIX.md` (H5 and H12 fail the data gate) and `PREVIOUS_WORK_AND_EXCLUSION_LEDGER.md` (TESS-EB
targets, blind periodicities, Karambelkar et al. 2026 transients, static ice maps, 3I/ATLAS — not repeated). No
sample target lies within 60″ of a Karambelkar et al. object (`data/selection/karambelkar_check.json`).
