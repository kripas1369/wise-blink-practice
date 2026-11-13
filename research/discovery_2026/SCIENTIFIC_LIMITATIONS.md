# Scientific limitations

Limitations are grouped by what they affect. Each states how it was handled and what remains.

## 1. Measurement model

* **Analytic band profiles, not laboratory spectra.** H2O is a Gaussian core in wavenumber plus a fixed red wing;
  CO2 is one Gaussian. The shape is shared by all epochs of a source and fitted, so a profile error is common to all
  epochs and cancels in the epoch comparison, but absolute column densities are not derived and τ values are model
  depths, not N(H2O)/A. Comparison with laboratory-template optical depths (Serna et al., Kim et al.) is qualitative.
* **Continuum.** The H2O continuum is a per-epoch power law anchored by 2.42–2.72 µm and 3.75–4.15 µm windows. The
  2.42–2.72 µm window contains photospheric/disk H2O vapour in FUor-like objects and the 3.75–4.15 µm window
  contains Br α (4.05 µm) and the 3.47 µm/"3.3–3.5 µm" carriers. Four alternative continua are run for every target
  (wider range with D3, no blue window, curved continuum, narrow red window); a change is called robust only if it
  survives all of them. In V1647 Ori the baseline change (Δτ ≈ −0.28) reversed sign without the blue window, which
  is why the rule exists.
* **Scattered light.** The injection test (VALIDATION/) shows that an unabsorbed scattered-light component equal to
  30 % of the continuum at 3 µm with a λ⁻⁴ colour lowers the fitted τ_H2O of EC 53 by 0.55 (5.8σ) without any change
  in the ice. Embedded protostars are often seen partly in scattered light from outflow cavities, and the fraction of
  scattered light can change when the inner disk illumination changes. **An apparent depth change can therefore not be
  attributed to ice sublimation/recondensation from SPHEREx data alone**; this is a physical degeneracy, not a
  processing artefact.
* **CO2 saturation.** For deep-ice sources the CO2 band is saturated at SPHEREx resolution; the equivalent width is
  reported, but its sensitivity to depth changes is low (EC 53: an injected Δτ_CO2 = 4 changes EW by 6.6 nm against
  an uncertainty of 8.5 nm). CO2 constrains changes only for moderate depths.
* **CO 4.67 µm** was not measured: R ≈ 130 does not separate CO ice from CO gas rovibrational absorption/emission,
  which is known to vary in EC 53 (EPISODE II).
* **Zodiacal light** (ZODI extension) is not subtracted explicitly; the local background plane in the PSF fit absorbs
  it, since zodiacal light is smooth on 15 × 21 pixel scales.

## 2. Photometry

* **Nebulosity and crowding.** The point-source + plane model fails in bright H II regions and reflection nebulae
  (per-exposure PSF-fit χ²_red of tens to hundreds). A target-band enters the primary analysis only if the joint ice
  fit has χ²_red ≤ 15; the result without this cut is reported alongside.
* **Controls are not perfectly matched in environment.** CTRL protostars are matched in W2 and embedded class, not in
  nebulosity. Verified on the full catalogue: the median over targets of the per-exposure PSF-fit χ²_red is 107
  (IQR 49–292) for CTRL and 11 (IQR 4–28) for VAR, at the same median per-exposure S/N (91 vs 95) and with more
  fitted neighbours (median 19 vs 16.5 sources in the fit box). The controls therefore sit in more nebulous or
  crowded fields, fewer of them pass the joint-fit χ² rule (9 CTRL vs 28 VAR H2O target-bands tested), and the
  empirical systematic floor rests on few control pairs (5 H2O, 19 CO2).
* **Background stars.** The SPLICES background-star pool with A_V > 25 and 6 < W2 < 9 is dominated by Galactic-plane
  sightlines toward M16/M17/M20 and Norma, where much of the extinction is diffuse (ice-free) and the fields are
  crowded and nebulous. Most of the 12 background stars have τ_H2O ≈ 0 and fail the χ² rule; they are a weak control
  for H2O and a usable one only for some CO2 measurements.
* **Saturation.** Sources with W1 ≲ 6 have no usable core pixels (Elias 29, Elias 16); the sample excludes them, so
  the brightest outbursts are not represented.

## 3. Temporal sampling

* Three visits (Sep–Oct 2025, Mar–May 2026, Sep–Oct 2026 for most fields) give two independent intervals of ~6
  months. Within a visit the H2O window is swept over 8–49 days, so changes faster than that are averaged and a
  brightness drift within the sweep is modelled by a linear drift term (H2O) or by per-day normalisation (CO2).
* NEOWISE ended in 2024, so there is **no independent contemporaneous luminosity measurement**; the SPHEREx continuum
  itself is the luminosity proxy (criterion 1 of the mission's strong test is only partly met: NEOWISE establishes past
  variability, not the state during the SPHEREx visits).
* Freeze-out at envelope densities takes decades to centuries, and the sublimation front moves only with the
  luminosity; changes on 6-month intervals are therefore expected only in the inner, warm part of the column.

## 4. Sample and statistics

* 36 VAR + 36 CTRL protostars is a small random subset of the 171 eligible variables. Results are statements about
  this sample; selection effects (W1 > 6.5, IRAC isolation, embedded class) limit generalisation to the brightest and
  the most crowded protostars.
* **Sample purity.** SPLICES classes are not clean: SIMBAD (checked after the analysis) identifies 2 of 36 VAR and
  9 of 36 CTRL as non-protostars (a nova, planetary nebulae, Miras/LPVs, AGB candidates, a high-proper-motion star, a
  B-type binary). They inflate the apparent contrast in ice-detection rate but are absent from the ice-detected
  quality controls; the key statistics recomputed without them are unchanged
  (`EXPERIMENTAL_RESULTS/population/purity_check.json`). The 8 VAR and 12 CTRL with no SIMBAD object within 15″,
  and those with only catalogue entries, are not individually verified.
* Pairs of epochs of one target share an epoch and are not independent: only consecutive pairs are used in
  population statistics, and bootstrap resampling is over targets.
* Formal uncertainties are scaled by √χ²_red of each fit; residual correlated errors (same-day groups, detector
  position) are absorbed by the empirical floor from the controls rather than modelled.

## 5. Interpretation

* **Column change vs covering fraction.** For SJ06135925p1743210 a fixed ice column in front of a varying fraction
  of the 3 µm emitting region (unabsorbed fraction 20 % at epoch 1) fits as well as a per-epoch τ (χ² 166.8 vs 169.0,
  `VALIDATION/scatter_model.csv`). SPHEREx measures an area-weighted effective depth; at R ≈ 35 (band 4, which holds
  the 3 µm feature) and τ ≲ 1 the two cannot be separated. The same degeneracy holds for every apparent H2O change in the sample.
* **CO2 as a column tracer.** The CO2-based limit on column changes assumes that CO2 and H2O ice sit in the same
  column in front of the same continuum. CO2 ice is largely mixed with H2O in protostellar envelopes, but a CO2-rich
  outer layer or a different 4.3 µm emitting area would weaken the comparison. The CO2 saturation correction
  (g = d ln EW / d ln τ, median 0.64) uses the fitted Gaussian shape and the mean depth of each target.
* **Colour diagnostic.** Only 7 quality, ice-detected pairs have |Δ ln F(3.95 µm)| ≥ 0.3; the statement that none is
  extinction-like rests on these and on the fitted fraction of the icy-extinction prediction over 33 pairs.
* **Merged-visit comparison.** The merged single-epoch fit uses this pipeline, not the Serna et al. template fit;
  the size of the bias in their measurements is not known, only its sign and dependence on variability here.

## 6. Literature and novelty

* CDS SIMBAD was unavailable on 13 Nov 2026; the identifier cross-match was completed later the same day through the
  Harvard SIMBAD mirror (59 of 86 targets matched within 15″). Reference lists were read only for the candidate
  SJ06135925p1743210 (IRAS 06110+1744, 4 references) and SJ22280291p6901168 (5 references); for other targets
  the number of references is recorded but the papers were not reviewed. VizieR was not used.
* Web search is not exhaustive (no ADS full-text access was used); see `LITERATURE_REVIEW.md` §11.
