# Executive summary

**In one sentence:** SPHEREx images show that, in five TESS eclipsing-binary catalogue entries tested in five new
sky regions, the eclipses belong to a neighbouring Gaia DR3 eclipsing binary and not to the star the catalogue
names, and a catalogue-wide cross-match identifies 265 more TESS-EBs entries where the same is likely. These are
corrections to existing catalogues, found with an established idea applied in a new place, not the discovery of new
stars. Details: `FINAL_SCIENTIFIC_DISCOVERY_REPORT.md`.

## 1. What was the original research question?

Can the existing SPHEREx TimeLens methods (Blink Flipbook, Eclipse Mode) reveal something scientifically important?
After the literature review and 22 scored hypotheses, it became: *for TESS-EBs entries whose period-matched Gaia DR3
eclipsing binary is a different star, does SPHEREx show the eclipse on the Gaia binary, and how common are such
misattributions?*

## 2. What research gaps were investigated?

Five, ranked (report §5): (1) which star produces each TESS-EBs signal; (2) infrared eclipse depths of these
binaries; (3) eclipse-time drift since TESS; (4) primary/secondary labels in TESS-EBs; (5) uncatalogued variables
in the SPHEREx deep fields.

## 3. What was the strongest research opportunity?

Gap 1 (hypotheses H1 and H2, scores 83 and 85 of 100; H1 was 88 before Zasche's related work was found). TESS's 21″ pixels mix stars; TESS-EBs names one star per signal and has no
true-source column; Gaia DR3 lists 2.2 million eclipsing binaries with periods; SPHEREx resolves 3.4× finer than TESS
and observes the ecliptic poles hundreds of times, where TESS-EBs is densest.

## 4. What did the five sky regions reveal?

In every region the Gaia binary eclipses and the TIC star does not:

| Region | Gaia binary depth (primary / secondary) | TIC star | Independent checks |
|---|---|---|---|
| R1 LMC, crowded (OGLE-LMC-ECL-13800) | 11 ± 2% / 9 ± 2% | −2 ± 2% / 0 ± 2% | own period found blind; z 2.6 / 2.1 |
| R2 sparse (ASASSN-V J071248.16-644303.5) | 21 ± 3% / 42–56% | −2 ± 1% | difference-image position 0.02 px from the binary, TIC star excluded at 3.9σ |
| R3 close pair, 7.4″ (UCAC4 147-005376) | 21 ± 1% / 16 ± 1% | 0 ± 1% / 0 ± 1% | position 0.17 px from the binary, TIC star excluded at 15σ |
| R4 north polar (ASASSN-V J171505.23+851208.0) | 30 ± 1% / 28 ± 1% | −1 ± 1% / 0 ± 1% | position 0.03 px from the binary, 4.0σ; empirical z 18 / 17 |
| R5 south ecliptic pole (OGLE-LMC-ECL-39123) | 32 ± 3% / 15 ± 4% | 0 ± 1% / 1 ± 1% | empirical z 11.5 / 5.2; own period found blind |

In all five, the binary's own periodogram — computed without any TESS information — finds half its catalogue
period, and in R2–R5 it is the most significant periodic star in the whole field.

## 5. Did any target exhibit unusual behaviour?

- **R2:** the eclipse TESS-EBs calls "primary" is the shallower one (21% vs 42–56%); the ASAS-SN epoch confirms
  the deeper eclipse is half a period from the TESS primary → a primary/secondary label swap in TESS-EBs.
- **R5:** the TESS-EBs clock is 0.24 in phase off by 2026 (only two TESS sectors), and both SPHEREx eclipses arrive
  ~1 hour later than the OGLE-IV ephemeris predicts (+61 ± 24, +74 ± 40 min); TESS 2019 is also late (+139 min).
  Possible eclipse-timing variation — a candidate, not claimed.
- Not unusual after checking: an apparent infrared "depth reversal" (R2, label swap), a 4% dip in an R4 control star
  (systematic), two uncatalogued periodicities from the blind search (rejected: one appears only in half the data,
  one only in one detector).

## 6. Did we obtain any new measurements?

Yes (class B): the first SPHEREx 0.75–5 µm eclipse depths of these five binaries, eclipse times in 2025–26 that test
the TESS and OGLE clocks (R3 and R4 on time to ±2 min), the R2 label swap, and the finding that the TESS-EBs period
of TIC 31511621 is too imprecise for 2026.

## 7. Did we identify any potentially novel candidate?

Yes, as **corrections of catalogue attributions**, not new objects:

- **D (potentially novel, strong evidence):** the TESS-EBs signals of TIC 349156098, 309659126, 160195393 and
  31511621 belong to neighbouring Gaia DR3 eclipsing binaries; the VSX position of ASAS J051801-6041.4 is on the
  wrong star (R3); SIMBAD's "eclipsing binary" type for TIC 31511621 most likely copies the TESS-EBs error (R5).
- **C (candidate):** TIC 179637488 (R1, weaker evidence in a crowded nebular field); the list of 265 TESS-EBs entries
  whose eclipse matches a specific neighbouring Gaia DR3 binary absent from TESS-EBs, with the misattribution rate
  rising from 8–9% at high galactic latitude to 30% in the plane (p = 2 × 10⁻¹⁵); the R5 eclipse-timing offset.
- **No new variable star** was found.

## 8. What evidence supports it?

Catalogue level: 278 of 1,543 entries with a period-matched Gaia binary within 63″ point to a different star, against
~2 expected by chance; 242 of 245 are physically possible by dilution, and the implied undiluted depths match those of
correctly attributed entries (median 15.7% vs 16.5%). Region level: forced PSF photometry of every Gaia star; an
empirical false-alarm test against 1,000 random phases (FAP < 0.001 for every binary, TIC stars |z| < 1); the
binary's own periodogram; the position of the light that disappears in eclipse (R2, R3, R4); control stars; OGLE,
ASAS-SN, VSX and SIMBAD checks. All numbers are in `experimental_results/results_summary.json`, with figures per
region.

## 9. What did previous researchers already establish?

That TESS signals often come from neighbouring stars (Higgins & Bell 2023; Pedersen & Bell 2023; Mistry et al. 2024;
Panahi et al. 2022); that catalogue cross-matching finds the true source of blended eclipses (Coughlin et al. 2014 for
Kepler; Zasche 2024 for OGLE; Zasche 2025 — a third of the Rowan et al. doubly-eclipsing candidates are blends); that
TESS-EBs used a centroid test (Prša et al. 2022); and the identities and periods of all five binaries (OGLE, ASAS-SN,
Gaia). None of our 278 entries is in Zasche's list, and no published catalogue-wide TESS-EBs × Gaia DR3 reassignment
or SPHEREx eclipse measurement was found (`LITERATURE_REVIEW.md`).

## 10. What remains uncertain?

- How many of the 265 are truly wrong: only 5 were checked directly, chosen for SPHEREx coverage, not at random.
  A TIC star could host its own eclipse at the same period.
- Selection biases in the trends (Gaia detects deep eclipses more easily); the 3,039 entries without a Gaia match
  are untested.
- R1 (z 2.1–2.6, no usable position test) and the R5 timing offset (2–3σ, OGLE errors assumed).
- The infrared depths are not yet a physical result (too few exposures per wavelength bin, no third-light model).
- Literature completeness: unpublished or recent work could overlap.

## 11. What algorithmic improvements were necessary?

All in `research/`; the application is untouched (`CODE_CHANGES.md`):

1. Forced PSF photometry of every Gaia star at once (Eclipse Mode measures one aperture on the named star).
2. A pixel-integrated PSF with a wide wing (co-add χ² halved; detection 11.4σ → 14.1σ on the validation pair).
3. An external-ephemeris option (needed for R5).
4. A fix to the ensemble reference stars (an eclipsing binary had been used as a reference, making other stars seem
   to brighten by 8.7%).
5. Jitter-weighted empirical significance against random phases.
6. A difference-image centroid (Bryson et al. 2013) to show where the missing light is.
7. Rejected: a wavelength-dependent PSF within a detector (no measurable gain).

## 12. How could the result become a scientific publication?

A short paper (e.g. RNAAS or an MNRAS Letter, in the style of Zasche 2025): "Misattributed sources in the TESS
eclipsing binary catalogue identified with Gaia DR3 and confirmed with SPHEREx". Needed first:

1. Share the list with the TESS EB Working Group (Prša et al.) before publishing.
2. Verify a random subsample of the 265 (e.g. 30 entries) with Gaia epoch photometry and TESS pixel data
   (TESS_localize), not only SPHEREx, to measure the true confirmation rate.
3. Extend the cross-match to later TESS-EBs releases and to the TESS Ten Thousand catalogue.
4. Model selection effects for the latitude and depth trends.
5. Report the VSX (R3) and SIMBAD (R5) corrections to those services.
6. For the R5 timing candidate, obtain the OGLE-IV photometry and fit an O−C diagram before any claim.

The investigation does not support the word "discovery": the stars were known, and the attributions are corrections
that still need independent review.
