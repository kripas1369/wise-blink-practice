# Validation

Every test that decides whether a measured change is astrophysical, instrumental or a modelling artefact. Files in
this directory unless stated otherwise. Simulated data appear only in the injection test and are labelled as such;
nothing simulated is used as astronomical evidence.

## 1. Data access and photometry

| Test | Result | Evidence |
|---|---|---|
| Stamp reader vs full-file decode (3 positions incl. clipped corners) | IMAGE, FLAGS, VARIANCE identical | `DATA_RELEASE_AND_ACCESS_AUDIT.md` §5 |
| ePSF in calibration product vs EPSF extension of DR1 and QR3 images (D4) | byte-identical | idem §3 |
| Flux scale: SPHEREx 2.00–2.30 µm vs 2MASS Ks (log₁₀ ratio, per visit) | CTRL +0.052 dex (σ_robust 0.088, 87 visits / 31 targets); BGSTAR +0.022 dex (0.058, 34 / 12); VAR +0.099 dex (0.36, 94 / 35) | `flux_check.csv`, `flux_check.json` |

The non-variable roles agree with 2MASS to 5–12 % with ≤ 0.09 dex scatter (2MASS is 1998–2001, so part of that
scatter is real); the variable protostars scatter four times more, as expected for sources selected by NEOWISE
amplitude. The flux scale is therefore valid to ~10 % and the photometry recovers the known variability contrast.

## 2. Known-answer targets

| Target | Published | Measured here | Verdict |
|---|---|---|---|
| EC 53 (V371 Ser) | JWST: ice features unchanged across a ≥ 3× luminosity change (EPISODE IV, arXiv:2604.08769) | τ_H2O 2.00 / 2.07 / 2.10 (p = 0.25) while the continuum changes ×4; CO2 EW constant (p = 0.53) | reproduced |
| V1647 Ori | ice absorption seen during and after the 2004 and 2008 outbursts (Aspin et al.) | H2O detected (τ ≈ 0.7–1.0); baseline Δτ = −0.28 over two intervals, but the sign flips without the 2.42–2.72 µm continuum window (FUor-like H2O vapour there) | change **not robust**; motivated the variant rule |

## 3. Analysis-choice robustness (every target)

Seven analyses per H2O fit: baseline, aperture photometry, no drift term, continuum including D3 to 2.10 µm, no
blue window (start 2.80 µm), curved continuum, narrow red window (to 3.90 µm). A pair is *robust* only if the baseline
|z| ≥ 3 and every alternative gives the same sign with |z| ≥ 2. Of 6 Benjamini–Hochberg-significant variable
protostars (H2O, quality selection), 5 fail this rule, almost always in the "no blue window" or "curved continuum"
analysis (`REJECTED_CANDIDATES.md`). Only SJ06135925p1743210 passes (minimum |z| 2.2 in the curved continuum).

## 4. Epoch-boundary sensitivity

`EXPERIMENTAL_RESULTS/population/epoch_sensitivity.csv`: five settings (baseline 60/20 d visit/pass gap; no pass
split; visit gap 30 d; visit gap 120 d; pass gap 10 d). Across 149 target-band fits the epoch definitions changed in
63 fits at 120 d, 11 at 30 d, 5 without the pass split and 3 at a 10 d pass gap, and the p < 0.01 status changed in
**one** (SJ20573116p4402374, H2O, at 120 d,
where two visits merge: p 4×10⁻⁵ → 0.019). SJ06135925p1743210 is identical in all five settings.

## 5. Injection–recovery (simulated perturbations of real photometry)

`injection_summary.csv`, `injection_NAME.json`. The last epoch of 9 targets (EC 53, V1647 Ori, the candidate,
6 ice-detected quality controls) was perturbed:

* **Depth change**: recovered without bias in all 9 (e.g. injected Δτ_H2O = 0.10 → recovered 0.0995–0.1014). The
  1σ sensitivity is Δτ_H2O ≈ 0.03–0.16 depending on the target; Δτ = 0.2 is detected at 3–7.5σ in well-measured
  targets.
* **Grey (×2, ×0.5) and colour ((λ/λ₀)^±1) continuum changes**: recovered Δτ = 0 to < 10⁻⁶ — the joint fit separates
  continuum from depth exactly when the model is right.
* **Unabsorbed blue light** (0.3 × F_cont(3 µm) × (λ/λ₀)⁻⁴): target-dependent, from −0.55 (EC 53, 5.8σ) and −0.44
  (SJ15315679m5532126) to +0.04…+0.11 (others). The sign and size depend on the continuum shape. For the candidate
  it is +0.04 ± 0.04, the opposite sign to its measured −0.18.
* **CO2**: an injected Δτ_CO2 = 1 changes the EW by 2–30 nm depending on saturation (EC 53: Δτ = 4 → 6.6 ± 8.5 nm).

## 6. Physically distinct models for the apparent H2O changes

`scatter_model.csv` (script `scripts/scatter_model.py`), band shape fixed to the baseline fit:

| Target | χ² ice change (A) | ΔBIC unabsorbed blue light q=4 / 2 / 0 (B) | ΔBIC partial covering (C) |
|---|---|---|---|
| SJ06135925p1743210 | 169.0 | +61 / +63 / +24 | **+2.3** (χ² 166.8, unabsorbed 20 % at epoch 1) |
| SJ18570951p0210407 | 347.6 | +54 / +44 / +108 | +1.0 |
| SJ20573116p4402374 | 516.9 | +133 / +133 / +79 | +5.1 |
| SJ00381870p6306053 | 468.6 | +84 / +84 / +60 | +6.1 |
| SJ06123374p1749238 | 505.0 | +98 / +102 / +55 | +9.4 |
| SJ07051097m1105081 | 260.4 | +8 / −2 / **−14** | +3.2 |
| SJ22280291p6901168 | 2147 | +945 / +823 / +675 | +578 |
| SJ07142692m1203589 | 687.0 | +190 / +190 / +163 | +6.2 |
| V1647 Ori | 351.5 | +147 / +187 / +151 | +28 |
| EC 53 | 346.8 | +13 / +9 / +6 | +2.3 |

ΔBIC > 0 favours the ice-change model A (one parameter fewer). Additive unabsorbed light with a fixed blue, flat or
grey colour is disfavoured everywhere except SJ07051097m1105081. A fixed column in front of a varying fraction of the
continuum (C) fits as well as A (ΔBIC ≤ 6, i.e. Δχ² ≤ 2 apart from the extra parameter) for 7 of 10 targets:
**SPHEREx measures an area-weighted effective depth and cannot separate a column change from a covering change.**

## 7. Crowding (candidate)

`crowding_SJ06135925p1743210.json/.png` (script `scripts/crowding_check.py`). Every stamp fitted the same 20 sources.
The two nearest AllWISE neighbours (20.4″, W1 12.2; 20.9″, W1 11.0 / W2 9.7 — about 3.3 SPHEREx pixels) have
constant fluxes (5.04 / 5.09 / 5.06 mJy and 9.97 / 9.68 / 8.64 mJy at 3 µm) and constant ice depths (τ 0.02 / 0.02 /
0.00 and 0.18 / 0.18 / 0.24, indicative p = 0.49 and 0.65) in the same three epochs. No light was traded between the
target and its neighbours when its depth changed.

## 8. Jackknife (candidate)

`jackknife_SJ06135925p1743210.json` (script `scripts/jackknife.py`). Removing each of the in-window exposures in turn:
z(0→1) between −4.53 and −3.45, z(1→2) between +2.97 and +4.45; τ at epoch 1 between 0.514 and 0.540. Removing each
0.15 µm block of channels: τ at epoch 1 stays 0.508–0.548; only removing the band core (3.02–3.17 µm) lowers the
significance (z −2.2 / +1.7) without changing Δτ. No single exposure or spectral region creates the change.

## 9. Controls and empirical floor

* Ice-detected controls give the systematic floor: H2O n = 5 consecutive pairs, s = 0, MAD(z) = 0.36 (fit errors are
  conservative by ~3×); CO2 n = 19, s = 0.0019 µm, MAD(z) = 1.09 (calibrated).
* No control has a robust or BH-significant change in either band; 3 of 9 background stars have CO2 p < 0.05, none
  after BH (`EXPERIMENTAL_RESULTS/population/summary.json`).
* Controls are matched in W2 and class, not in environment: their median per-exposure PSF χ²_red is 107 vs 11 for the
  variables (`SCIENTIFIC_LIMITATIONS.md` §2).
* Sample purity: 2 VAR and 9 CTRL are non-protostars per SIMBAD (`REJECTED_CANDIDATES.md` §5); none is an
  ice-detected quality control, and the key statistics without them are in
  `EXPERIMENTAL_RESULTS/population/purity_check.json` (script `scripts/purity_check.py`).

## 10. Colour of the continuum change (extinction test)

`EXPERIMENTAL_RESULTS/colour/` (script `scripts/colour_diagnostic.py`). Extinction by the same dust would dim
2.05–2.35 µm 1.92× more than 3.95 µm (ratio R = Δln F_K / Δln F_3.95). The seven quality, ice-detected pairs with
|Δln F(3.95 µm)| ≥ 0.3 have R = 0.19–1.18 (EC 53: 0.19 and 0.96); SJ22280291p6901168 (quality fail) has R = 0.26
in both intervals. Across 33 pairs the measured Δτ_H2O is −0.15 ± 0.07 times the change expected if the K-band change
were icy extinction (Spearman ρ = −0.09, p = 0.60). **No large continuum change in the sample is extinction-like, and
the ice depth does not follow the continuum.**
