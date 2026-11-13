# Literature review

*13 November 2026. 58 PDFs are stored in `research/papers/` (file name = arXiv identifier). "Read" means the relevant
sections of the PDF were read (methods, limitations, results); "abstract" means only the abstract was read. DOIs and
publication details come from the arXiv API and the publisher pages; where no journal reference was available the
arXiv identifier is given.*

## What this review was for

The investigation asks whether TESS eclipsing-binary signals are attributed to the wrong star, and whether SPHEREx
can show which star really eclipses. The review had to answer three questions: (1) how the TESS-EBs catalogue
handles blending, (2) whether anyone has already reassigned TESS-EBs entries to neighbouring Gaia eclipsing binaries,
and (3) whether anyone has measured eclipses with SPHEREx.

**Answers.**

1. TESS-EBs (Prša et al. 2022) uses a centroid test inside a validation score and acknowledges many off-target
   signals, but the published table names one TIC star per signal and has no true-source column.
2. **Wrong-source eclipsing binaries are a known problem, and catalogue cross-checking to find the true source is an
   established method**: Coughlin et al. 2014 (685 Kepler false positives by ephemeris matching), Zasche 2024 (a quarter
   of OGLE doubly-eclipsing candidates are blends), Zasche 2025 (a third of the Rowan et al. 2023 TESS/ASAS-SN
   doubly-eclipsing candidates are blends of two binaries tens of arcseconds apart), Banerjee & Prša 2025 (one
   TESS-EBs-adjacent false positive), Panahi et al. 2022 and Mistry et al. 2024 (planet candidates). **None of the
   papers found applies it catalogue-wide to TESS-EBs against the Gaia DR3 eclipsing-binary table.** None of our 278
   TESS-EBs entries or five targets appears in Zasche (2025)'s list of 76 corrected blends (checked by TIC number;
   two of Zasche's TIC numbers are in TESS-EBs, neither in our list).
3. SPHEREx time-domain work so far: transients and outbursts (Karambelkar et al. 2026), a fading microquasar (Gandhi
   & Boorman 2026), a dipper (Tzanidakis & Davenport 2026), phase-grouped spectra of pulsating AGB stars with OGLE
   periods (Huang et al. 2026, the closest precedent for folding SPHEREx on an external clock), and a disk-eclipsing
   binary where SPHEREx was used only as an out-of-eclipse spectrum (Lin, Sun & Li 2026). **No published SPHEREx
   eclipse light curve or eclipse-depth measurement of an eclipsing binary was found.** The SPHEREx pipeline paper
   (Akeson et al. 2025) describes a planned Level-3 "Estimate Variability" module, not yet released.

This does not prove that no one has done our analysis (unpublished work, conference talks, and the TESS-EBs website's
later releases were not all checked).

## 1. TESS and the eclipsing-binary catalogues

| Paper | Identifiers | Method | Result | Limitation (for our question) | Status |
|---|---|---|---|---|---|
| Prša, A. et al. 2022, *TESS Eclipsing Binary Stars I* | ApJS 258, 16; doi:10.3847/1538-4365/ac324a; arXiv:2110.13382 | 2-min light curves, Sectors 1–26; ephemerides by polyfit; validation and triage incl. centroid test; morphology by dimensionality reduction | 4,584 EBs; catalogue at tessEBs.villanova.edu and MAST | One TIC star per signal; the v1.0 table has no validation, centroid or true-source column; 222 entries have the primary at phase ≈ 0.5 of the epoch | read |
| Banerjee, A. & Prša, A. 2025, *Crossmatching the TESS EB Catalog with Kepler* | RNAAS 9, 152; doi:10.3847/2515-5172/ade853 | Kepler EB catalogue vs TESS-EBs via SIMBAD/TIC IDs; TCE period, epoch and centroid checks; neighbours inspected | 21 Kepler EBs missing from TESS-EBs; TIC 170740081 shown to be a copy of neighbour TIC 170740143 | Kepler field only; looks for missing EBs, not wrong-star entries | publisher page read |
| Kostov, V. B. et al. 2025, *TESS Ten Thousand (TTT)* | arXiv:2506.05631 | Neural-network search of FFIs, Sectors 1–82; ephemeris and photocentre tests; citizen-scientist vetting | 10,001 validated EBs (7,936 new); ~900,000 unvetted candidates | Photocentre tests on 21″ pixels; blends with known EBs flagged by separation | read (blending sections) |
| Kostov et al. 2022, 2023, 2025, *Eclipsing quadruple candidates in TESS FFIs* | ApJS doi:10.3847/1538-4365/ac5458 (arXiv:2202.05790); arXiv:2309.14200; arXiv:2510.27470 | Two periods in one light curve; photocentre test that both eclipse sets are on target | 97, 101 and 52 quadruple candidates | Shows photocentre tests are needed because blends mimic multiples | abstract |
| Oddo, D. et al. 2025, *M&M eclipsing binaries with TESS* | arXiv:2508.13941 | Selection and vetting of low-mass EBs | 1,292 low-mass EBs; circularisation period ≈ 2 d | Vetting for contamination is a key step | read (vetting) |
| Higgins, M. E. & Bell, K. J. 2023, *TESS_localize* | AJ; doi:10.3847/1538-3881/acb20c; arXiv:2204.06020 | Per-pixel sinusoid amplitudes at known frequencies fitted with the TESS PRF to locate the variable source to < 0.2 px; most likely Gaia star | Stars > 3 px outside an aperture can produce significant contaminating signals | Assumes no other star varies at the same frequency; needs TESS pixel data | read |
| Pedersen, M. G. & Bell, K. J. 2023, *Contamination in TESS light curves: FYPS* | AJ; doi:10.3847/1538-3881/accc31; arXiv:2304.05706 | TESS_localize on 17 fast yellow pulsating supergiants | Localisable signals come from contaminants (e.g. nearby EBs), none intrinsic | Supergiant targets only — directly relevant to R1, where TESS-EBs names a supergiant | abstract |
| Han, T. & Brandt, T. D. 2023, *TESS-Gaia Light Curves (TGLC)* | AJ 165, 71; doi:10.3847/1538-3881/acaaa7; arXiv:2301.03704 | PSF photometry of FFIs with Gaia positions and fluxes as priors | Decontaminated light curves for Gaia stars to G ~ 16 | Still limited by the 21″ PSF; contamination reduced, not removed | read (limitations) |
| Stassun, K. G. et al. 2019, *Revised TESS Input Catalog* | AJ 158, 138; doi:10.3847/1538-3881/ab3467; arXiv:1905.10694 | TIC-8 built on Gaia DR2; contamination ratios | G→T conversion used in our dilution check | Contamination ratio is per target, not a source attribution | abstract |
| Paegert, M. et al. 2021, *TIC 8.1 and 8.2: phantoms* | arXiv:2108.04778 | Removal of duplicated/phantom TIC entries | Some TIC entries are artefacts | Relevant to duplicate TESS-EBs pairs | abstract |

## 2. Identifying the true source of an eclipse

| Paper | Identifiers | Method | Result | Limitation | Status |
|---|---|---|---|---|---|
| Coughlin, J. L. et al. 2014, *Contamination in the Kepler field* | AJ 147, 119; doi:10.1088/0004-6256/147/5/119; arXiv:1401.1240 | Ephemeris matching between Kepler targets and known EBs | 685 KOIs (12%) are false positives from 409 parent sources; four contamination routes (direct PRF, antipodal reflection, column anomaly, crosstalk) | Kepler only; parent must be in a catalogue | read |
| Bryson, S. T. et al. 2013, *Background false positives from Kepler data* | PASP 125, 889; doi:10.1086/671767; arXiv:1303.0052 | Difference-image centroids and flux-weighted centroids | Standard method to locate a transit source | Needs well-modelled PSF; fails in crowded variable backgrounds | read (method) — basis of our difference-image centroid |
| Twicken, J. D. et al. 2018, *Kepler Data Validation I* | PASP 130, 064502; doi:10.1088/1538-3873/aab694; arXiv:1803.04526 | Pipeline diagnostics incl. centroid and ghost tests | Vetting architecture | Planets, not EB catalogues | abstract |
| Panahi, A. et al. 2022, *Gaia–TESS synergy* | A&A (Nov 2022); doi:10.1051/0004-6361/202244207 | Gaia epoch photometry of every source in the TESS PSF, folded on the TOI ephemeris | 124 TOIs excluded as background EBs, 126 confirmed on target; ~5% each | Needs enough Gaia points in transit; planet candidates only | publisher page read |
| Mistry, P. et al. 2024, *Positional probability and true host star identification of TESS exoplanet candidates* | MNRAS 527, 4018 | Observed TESS centroid offsets vs models for target and Gaia neighbours | 293 of 2,365 active planet candidates most likely on a nearby source; 38/40 known hosts recovered | Planet candidates; depends on SPOC centroids | publisher page read |
| Zasche, P. 2024, *Comment on Ádám et al. (2023)* | A&A 688, A41; doi:10.1051/0004-6361/202450463; arXiv:2408.02969 | VSX/OGLE search around OGLE doubly-eclipsing candidates | 53 of 245 (~¼) are blends of known OGLE neighbours | OGLE bulge fields; doubly-eclipsing candidates only | read |
| Zasche, P. 2025, *Large fraction of blends from Rowan et al. (2023)* | MNRAS 544, L174; arXiv:2608.25387 | VSX, Gaia DR3, ASAS-SN, ZTF, ATLAS, ASAS within 200″ of each candidate | 76 of 225 (33.8%) are blends of two separate EBs, typically tens of arcsec apart, up to > 100″ | Doubly-eclipsing candidates from Rowan et al., not TESS-EBs; catalogue evidence only, no imaging | **read — closest precedent** |
| Rowan, D. M. et al. 2023, *ASAS-SN EBs II: extra-physics* | MNRAS; doi:10.1093/mnras/stad021; arXiv:2210.06486 | ASAS-SN + TESS light curves; blend check against Gaia/ATLAS/ZTF/ASAS-SN | 766 EBs with extra signals | Blend check incomplete (see Zasche 2025) | abstract |
| Zasche, P., Henzl, Z. & Mašek, M. 2022, *Multiply eclipsing candidates from TESS* | A&A 664, A96; doi:10.1051/0004-6361/202243723; arXiv:2205.03934 | VSX EBs checked in TESS | 116 doubly eclipsing, 25 triply eclipsing; "several confirmed blends" excluded | — | abstract |
| Tingley 2004; Colón & Ford 2011; Parviainen et al. 2019 | A&A 425, 1125 (astro-ph/0406201); PASP doi:10.1086/663352 (arXiv:1110.4385); A&A 630, A89 (arXiv:1907.09776) | Multicolour transit depths to detect blends | Colour-dependent depth reveals a blended EB (KOI 565) | Needs targeted follow-up | abstract |
| Désert, J.-M. et al. 2015 | ApJ 804, 59; doi:10.1088/0004-637X/804/1/59; arXiv:1503.03173 | Spitzer 4.5 µm vs Kepler depths (a blended EB gives a colour-dependent depth) | Low false-positive rate for Kepler candidates | Infrared depth comparison as a blend test — the same logic as our SPHEREx test | read |

## 3. Gaia variability catalogues

| Paper | Identifiers | Method | Result | Limitation | Status |
|---|---|---|---|---|---|
| Mowlavi, N. et al. 2023, *Gaia DR3 eclipsing-binary candidates* | A&A 674, A16; doi:10.1051/0004-6361/202245330; arXiv:2211.00929 | G light curves, three period searches, two-Gaussian + cosine model, BIC selection | 2,184,477 candidates; 93% of 530,000 known EBs have compatible periods; completeness 25–50% | P > 0.2 d only; incomplete; crowding affects faint sources | read (limitations) |
| Eyer, L. et al. 2023, *Gaia DR3 variability summary* | A&A 674, A13; doi:10.1051/0004-6361/202244242; arXiv:2206.06416 | Classification of 1.8 billion sources | 10.5 million variables | — | abstract |
| Lebzelter, T. et al. 2023, *Gaia DR3 long-period variables* | A&A 674, A15; doi:10.1051/0004-6361/202244241; arXiv:2206.05745 | LPV candidates | Used to identify LPVs in the blind search | — | abstract |

## 4. SPHEREx

| Paper | Identifiers | Content relevant here | Status |
|---|---|---|---|
| Bock, J. J. et al. 2026, *The SPHEREx Satellite Mission* | ApJ; doi:10.3847/1538-4357/ae2be2; arXiv:2511.02985 | 6.15″ pixels, 102 channels 0.75–5 µm, deep fields at the ecliptic poles observed hundreds of times; mentions time-variable sources | read (relevant sections) |
| Akeson, R. et al. 2025, *SPHEREx image and spectrophotometry pipeline* | arXiv:2511.15823 | Calibrated images; forced photometry; planned Level-3 "Estimate Variability" module comparing new and earlier measurements | read (relevant sections) |
| Crill, B. P. et al. 2020, *SPHEREx* (SPIE) | Proc. SPIE 11443, 114430I; doi:10.1117/12.2567224; arXiv:2404.11017 | Instrument design, linear variable filters | abstract |
| Bryan, S. et al. 2025, *SPHEREx survey planning* | arXiv:2508.20332 | Observation sequencing: cadence is irregular and wavelength changes from visit to visit | read (cadence) |
| Bahk, H. & Hwang, H. S. 2026, *TractorJAX* | arXiv:2610.16007 | Forced photometry of undersampled SPHEREx images; fitting catalogues deeper than the image supports increases scatter by 34% | abstract — supports our G ≤ 16.5 cut |
| Karambelkar, V. et al. 2026, *SPHEREx infrared transients* | arXiv:2602.07129 | Spectra of NEOWISE-selected outbursts (FU Ori, novae) | abstract |
| Karambelkar, V., Sharma, Y. & De, K. 2026, *VY CMa shell is an artifact* | arXiv:2609.28612 | Bright-star artefacts in SPHEREx images | read (artefacts) |
| Gandhi, P. & Boorman, P. G. 2026, *GRS 1915+105* | arXiv:2607.06200 | Two-epoch SPHEREx mid-IR fading | read (SPHEREx part) |
| Huang, C. D. et al. 2026, *AGB variability and H₂O with SPHEREx* | arXiv:2609.30551 | Multi-epoch SPHEREx spectra of LMC AGB stars grouped by OGLE pulsation phase — closest precedent for folding SPHEREx on an external ephemeris | read (method) |
| Lin, J., Sun, Y. & Li, C. 2026, *Disk-eclipsing binary in UPK 13* | ApJ; doi:10.3847/1538-4357/ae7a3e; arXiv:2606.18971 | SPHEREx used only as an out-of-eclipse spectrum; eclipse depths from ZTF/NEOWISE | read |
| Tzanidakis, A. & Davenport, J. R. A. 2026, *Gaia-GIC-1* | ApJL; doi:10.3847/2041-8213/ae3ddc; arXiv:2603.10952 | SPHEREx confirms an infrared-bright state | abstract |
| Rustamkulov, Z. et al. 2026, *SPHEREx brown dwarf spectra* | arXiv:2607.00543 | Spectra of brown dwarfs; no eclipse or phase-resolved analysis | abstract |
| Davies, F. B. et al. 2026, *Lensed quasar with SPHEREx* | arXiv:2604.13152 | ~15% epoch-to-epoch change noted | abstract |
| Kim, M. et al. 2021, *Torus reverberation with SPHEREx* | JKAS 54, 37; doi:10.5303/JKAS.2021.54.2.37; arXiv:2107.04219 | Simulated SPHEREx time-domain AGN | abstract |
| Bisht, D. et al. 2026, *Blue stragglers in Berkeley 18* | arXiv:2606.04624 | Uses SPHEREx photometry (single epoch) | abstract |

## 5. Infrared time-domain surveys (context for SPHEREx light curves)

| Paper | Identifiers | Relevance | Status |
|---|---|---|---|
| Kim, M. et al. 2026, *Mid-IR variables at the ecliptic poles* | arXiv:2604.05332 | NEOWISE W1/W2 variables within 5° of the NEP and SEP (2,764 and 27,581): the same deep fields SPHEREx observes | abstract |
| Petrosky, E. et al. 2021, *Variability, periodicity and contact binaries in WISE* | MNRAS; doi:10.1093/mnras/stab592; arXiv:2012.04690 | ~42,000 short-period EBs in WISE light curves | abstract |
| Chen, X. et al. 2018, *WISE catalog of periodic variables* | ApJS; doi:10.3847/1538-4365/aad32b; arXiv:1807.03448 | Infrared EB amplitudes | abstract |
| Paz, M. et al. 2026, *VarWISE* | ApJS 284, 41; doi:10.3847/1538-4365/ae562f; arXiv:2605.19059 | NEOWISE single-exposure variability | abstract |
| Meisner, A. M. et al. 2023, *unTimely* | AJ; doi:10.3847/1538-3881/aca2ab; arXiv:2209.14327 | Time-domain unWISE | abstract |
| Schlafly, E. F., Meisner, A. M. & Green, G. M. 2019, *unWISE catalog* | ApJS; doi:10.3847/1538-4365/aafbea; arXiv:1901.03337 | Simultaneous fitting of thousands of blended sources | abstract |
| Lang, D., Hogg, D. W. & Schlegel, D. J. 2016, *WISE forced photometry* | AJ 151, 36; doi:10.3847/0004-6256/151/2/36; arXiv:1410.7397 | Forced photometry at catalogue positions — basis of `field_psf.py` | abstract |
| Morales-Calderón, M. et al. 2011, 2012 (YSOVAR) | ApJ 733, 50 (arXiv:1103.5238); ApJ 753, 149 (arXiv:1206.6350) | Spitzer 3.6/4.5 µm light curves; infrared eclipse depths of six PMS EBs | read (depths) |
| Cody, A. M. et al. 2014 (CSI 2264) | AJ 147, 82; arXiv:1401.6582 | Simultaneous optical/IR light curves | abstract |
| Minniti, D. et al. 2010 (VVV) | New Astron. 15, 433; arXiv:0912.1056 | Near-IR variability survey of the bulge | abstract |
| Iwanek, P., Soszyński, I. & Kozłowski, S. 2021 | ApJ; doi:10.3847/1538-4357/ac10c5; arXiv:2012.12910 | Mid-IR Mira P–L relations in the LMC | abstract |

## 6. Methods

| Paper | Identifiers | Used for | Status |
|---|---|---|---|
| Alard, C. & Lupton, R. H. 1998 | ApJ 503, 325; arXiv:astro-ph/9712287 | Image subtraction (we use wavelength-matched pairs instead of kernel matching) | abstract |
| Zackay, B., Ofek, E. O. & Gal-Yam, A. 2016 | ApJ 830, 27; arXiv:1601.02655 | Optimal image subtraction | abstract |
| Sokolovsky, K. V. et al. 2017 | MNRAS; doi:10.1093/mnras/stw2262; arXiv:1609.01716 | Variability indices (von Neumann η among the best) | read (conclusions) |
| Miller, C. J. et al. 2001 | AJ 122, 3492; arXiv:astro-ph/0107034 | False-discovery-rate control (we use Bonferroni, more conservative) | abstract |
| Borkovits, T. et al. 2016 | MNRAS; doi:10.1093/mnras/stv2530; arXiv:1510.08272 | Eclipse-timing variations | abstract |
| Conroy, K. E. et al. 2014 | AJ 147, 45; arXiv:1306.0512 | Eclipse timing of Kepler EBs | abstract |

Classic method references cited in the report but not downloaded: Stetson 1987 (PASP 99, 191); Honeycutt 1992 (PASP
104, 435); Anderson & King 2000 (PASP 112, 1360); Lomb 1976 (Ap&SS 39, 447); Scargle 1982 (ApJ 263, 835); VanderPlas
2018 (ApJS 236, 16); Broeg, Fernández & Neuhäuser 2005 (AN 326, 134); Gregory 2005 (ApJ 631, 1198).

## 7. Catalogues used as ground truth (not downloaded)

OGLE-IV LMC eclipsing binaries (Pawlak, M. et al. 2016, AcA 66, 421); ASAS-SN variable stars (Jayasinghe, T. et al.
2018, MNRAS 477, 3145, and later papers); VSX (Watson, C. L., Henden, A. A. & Price, A. 2006, SASS 25, 47); MACHO LMC
variables (Fraser, O. J. et al. 2008, AJ 136, 1242); LH 47 (Lucke & Hodge 1970; Oey, M. S. & Massey, P. 1995, ApJ 452,
210).

## 8. What this means for novelty

- **Previously known (class A):** that TESS signals can come from neighbouring stars; that catalogue cross-matching
  finds the true source; the five binaries themselves (OGLE, ASAS-SN, Gaia).
- **Not found in the literature checked:** a TESS-EBs-wide list of entries whose eclipse matches a specific
  neighbouring Gaia DR3 eclipsing binary, with its latitude and depth dependence; direct imaging confirmation of such
  reassignments at 6″ resolution; SPHEREx eclipse light curves and 0.75–5 µm eclipse depths of any eclipsing binary.
- **Caution:** Zasche's method would find many of our 265 entries if applied to TESS-EBs; our catalogue result is a
  new application of an established idea, not a new idea.
