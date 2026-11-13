# Literature review (Stage B)

Cut-off: 13 Nov 2026. Sources were read in full text where marked "(read)"; otherwise the abstract or the quoted
passage was used. Full-text copies were fetched with the agent's web tools on 13 Nov 2026; quotations below are verbatim.
A search returning nothing is **not** taken as proof that a result is unpublished (see §11 for the search log and its
limits).

## 0. Core references

| # | Reference | What it establishes for this project |
|---|---|---|
| R1 | Bock et al., SPHEREx mission paper; SPHEREx Explanatory Supplement v1.6 (read) | L2 product definition, survey cadence (each sky position re-observed ~every 6 months), LVF channel structure |
| R2 | Melnick, Hora, Ashby, Tolls, Kim et al., "The SPHEREx Ices Investigation: An Overview", arXiv:2603.22135, ApJ (doi 10.3847/1538-4357/ae53e0) (read) | official Ices pipeline; **variability treated as a contaminant** (quoted in Q3) |
| R3 | Ashby et al., "The SPHEREx Target List of Ice Sources (SPLICES)", arXiv:2501.17797; SPLICES v8.6 release notes (read) | 9.9 M target catalogue; NEOWISE variability classes `w2var_class` (Park et al. 2021 scheme) used here for sample selection |
| R4 | Serna, Matt, McClure, Kounkel, Román-Zúñiga, "Evolutionary Demographics of Molecular Ice Mantles in Young Stars with SPHEREx", arXiv:2610.38043, ApJ 27 Oct 2026 (read) | first population SPHEREx YSO ice paper: 20,292 YSOs, QR1, **"we use all valid measurements of each source"** (visits merged) |
| R5 | Roychowdhury, Bergner, Kauffmann, Pillai, Spezzano, "Using Scattered NIR Light to Map Water Ice in Prestellar Cores with SPHEREx", arXiv:2607.24934, ApJL (doi 10.3847/2041-8213/aeb94a) (read) | coreshine ice maps of L1544, CrA 151, L260, L1512; central ice deficit in the two densest cores, unexplained |
| R6 | Hora, Noh, Melnick et al., "SPHEREx Wide-Field Infrared Spectral Mapping of Interstellar Ices and PAHs", arXiv:2603.12390, ApJ (doi 10.3847/1538-4357/ae5180) | static H2O/CO2/CO ice maps of Cygnus X / North America Nebula; mentions the IRSA spectrophotometry tool and the future High Reliability Source Catalog |
| R7 | Karambelkar, De, Hillenbrand, Sokoloski, Frostig, Dalcanton, "SPHEREx as a frontier for infrared transients", ApJL 1000, L8 (2026), doi 10.3847/2041-8213/ae4aa9 (read) | SPHEREx spectra classify new Galactic FU Ori outbursts and novae; excluded targets |
| R8 | Kim, J., Lee, J.-E., et al., "EPISODE IV: Ice Inventory in the Envelope of EC 53", arXiv:2604.08769 (read) | JWST NIRSpec+MIRI at quiescence (5 Oct 2023) and burst (10 May 2024): **"no measurable change in any ice absorption band"** while flux rose by ≥ 3× |
| R9 | Lee, S., Lee, J.-E., et al., "EPISODE II: Variability in the CO and H2O rovibrational absorption lines in EC 53", ApJ 2026-07-01 | gas-phase (not ice) line variability in EC 53 |
| R10 | Terada et al. 2007, ApJ 667, 303, doi 10.1086/520951 (read) | HV Tau C (edge-on disk): τ(H2O) **1.65 → 1.09 over 2.32 yr** with no photometric change at K and L′; earlier ice variability reported for Haro 6-10 and T Tau S (Leinert et al. 2001; Beck et al. 2004) |
| R11 | Terada & Tokunaga 2017, ApJ 834, 115, doi 10.3847/1538-4357/834/2/115 (read) | PDS 453: "possible variation" of the 3 µm profile at 3.20–3.25 µm among six epochs |
| R12 | Gibb et al. 2006; Aspin, Beck & Reipurth 2008, AJ 135, 423; Aspin et al. 2009, ApJ 692, L67 (read) | V1647 Ori: ice band similar between outburst and quiescence; water vapour absorption present |
| R13 | Graham, "3 Micron Ice-Band Absorption in Young Stellar Objects", ApJ (1998), doi 10.1086/305021 (read) | HH 100 IR / V346 Nor 3 µm profiles; earlier "2.97 µm feature" retracted — profile details at low S/N are fragile |
| R14 | Kim, J., Lee, J.-E., Jeong, W.-S., et al. 2022, ApJ 935, 137 (AKARI low-luminosity protostars, arXiv:2207.05178) | CO2 ice profile as a fossil record of past bursts; burst/quiescent durations ~100 / 10⁴ yr (Vorobyov et al. 2013) |
| R15 | Kim, H. J., Evans, Dunham, Lee & Pontoppidan 2012, ApJ 758, 38 (doi 10.1088/0004-637x/758/1/38); Visser & Bergin 2012; Vorobyov et al. 2013 (A&A) | episodic-accretion chemistry: CO desorbs during bursts and refreezes on ~10³–10⁴ yr at envelope densities |
| R16 | Cieza et al. 2016, Nature 535, 258 (V883 Ori water snow line); Houge & Krijt 2023, MNRAS; Houge et al. 2024 (MNRAS stad3758) | outbursts move the water snow line outward (disk scale, tens of au) |
| R17 | Kulkarni et al., arXiv:2601.21013 (27 yr ISO–NEOWISE YSO variability) | large-amplitude mid-IR YSO variability catalogue, independent of SPHEREx |
| R18 | "The role of absorption and scattering in shaping ice bands — Spatially resolved spectroscopy of protoplanetary disks", A&A 2025 (https://www.aanda.org/articles/aa/full_html/2025/04/aa54360-25/aa54360-25.html) (abstract read) | the observed water-ice band (depth, minimum wavelength shifted by up to 0.17 µm) depends on the balance of absorption and scattering, i.e. on geometry, even for a fixed ice mixture |
| R19 | Stecklum, "Disentangling Variability in YSOs: Light Echoes, Diamond Stars, Ice and Accretion Diagnostics", MPIA (https://www.mpia.de/6435187/stecklum.pdf) (search excerpt read) | proposes comparing pre-burst 3 µm depths with post-burst SPHEREx measurements; notes envelope absorption may dilute burst-induced changes and that scattered-light variability is ubiquitous; no measurement |
| R20 | Graham 1998 (R13), result on HH 100 IR (read) | 3 µm ice optical-depth spectrum unchanged over 7 yr while the IR source changed from faint to bright: "the variability of HH 100 IR is evidently not caused by changes in the obscuration by ice-covered dust grains" — a single-object precedent for the population result here |
| R21 | Bolocam Galactic Plane Survey III, arXiv:1005.4969; Carpenter et al. 1995, ApJ 450, 201 (bibcode 1995ApJ...450..201C) | Gem OB1 molecular cloud, distances 1.4–2.1 kpc quoted; region of the candidate SJ06135925p1743210 |

## 1. (Q1) What new SPHEREx data products appeared in 2026?

* **DR1** (`spherex_dr1`, `spherex_dr1_deep`, `spherex_dr1_cube`): reprocessed L2 spectral images for survey visits
  May 2025 – May 2026, pipeline VERSION 7.0.5, product tag `l2b-v27-2026-23x/24x`; calibration products
  `cal-swcs-v5`, `cal-sapm-v3`, `cal-epsf-v1/v2` (all `2026-191`). Verified directly (DATA_RELEASE_AND_ACCESS_AUDIT §1–3).
* **QR3** (`spherex_qr3`, `spherex_qr3_deep`): quick-release L2 images from May 2026 (survey 3) onward, same file format
  and identical calibration files (identical S3 ETags).
* QR2 collections are superseded; querying them returns zero rows (negative control in our audit).
* L3 forced photometry is available only through the IRSA Spectrophotometry Tool at user positions; the SSDC High
  Reliability Source Catalog has **not** been released as of the cut-off (R6 points to the data-products schedule).
  We could not verify a release date from the saved documentation and therefore do not quote one.
* Public anonymous S3 mirror of all L2 files (used here with HTTP range requests).

## 2. (Q2) Which investigations already use DR1/QR3?

* R4 (Serna et al.) uses **QR1** via the Spectrophotometry Tool — not DR1/QR3 — and merges all visits.
* R5 (Roychowdhury et al.) uses SPHEREx spectra of four prestellar cores (coreshine); time is not a variable.
* R6 (Hora et al.) static maps of Cygnus X.
* R7 (Karambelkar et al.) uses SPHEREx spectra of transients (FU Ori outbursts, novae); targets excluded here.
* R2 describes the Ices pipeline that will run on the release data.
We found no paper (to 13 Nov 2026) that measures ice bands **separately per SPHEREx visit**.

## 3. (Q3) What time-domain limitations are documented?

* R2, §5.2 (verbatim): "SPHEREx spectra are assembled from exposures spanning several days to weeks. Significant
  variability on these timescales can introduce artificial features or mask true absorption signals ... Approximately
  22% of SPLICES targets are flagged as variable and will either be excluded from the Ices analysis or subjected to
  additional processing".
* R4 merges every valid measurement (May–Dec 2025) into one spectrum per source.
* Our own audit (DATA_RELEASE_AND_ACCESS_AUDIT §6): within one visit a 3 µm band is sampled over 8–45 days in same-day
  groups of 3–5 channels; QR3 channels are offset by about half a channel from DR1.
Consequences: (a) the official ice catalogue is blind, by design, to the variable fifth of the targets; (b) a single
"spectrum" from merged visits can carry spurious structure when the continuum varies.

## 4. (Q4) Which phenomena can be tested with repeated SPHEREx observations?

With 2–3 visits ~6 months apart (and a ~45-day two-pass structure in some visits): continuum variability of
embedded YSOs at 2.4–5 µm; ice band changes on ≥ months timescale (sublimation/recondensation in the inner envelope,
changes of line of sight through disks — HV Tau C-like); variable reflection nebulae; transients. Sub-day
variability cannot be measured spectrally because one band is sampled over days.

## 5. (Q5) Which phenomena would optical surveys miss?

Deeply embedded (Class 0/I) protostars are often invisible to Gaia/ZTF; their variability is known mainly from
NEOWISE (W1/W2 photometry, R3/R17). NEOWISE ended in 2024 and has no spectral resolution: it cannot separate a change
of the continuum from a change of the 3 µm or 4.27 µm absorption (W1 contains the 3.05 µm H2O band, W2 contains CO2
4.27 µm and CO 4.67 µm). SPHEREx is the first all-sky instrument that resolves those bands at multiple epochs.

## 6. (Q6) Which environments have enough coverage?

Every position has ≥ 2 complete visits by the end of DR1 + QR3; ecliptic-pole regions have far more (deep fields).
For the sample, the per-target number of complete epochs is measured, not assumed (OBSERVATION_TIMELINES/). Typical
galactic star-forming regions: 3 complete visits (Sep–Oct 2025, Mar–May 2026, Sep–Oct 2026) for D4 (H2O) and D6 (CO2).

## 7. (Q7) Papers identifying unresolved problems

* R5: central ice deficit in the two densest cores, "pointing to an unexplained physical or chemical effect".
* R8: why do ≥ 3× luminosity bursts of EC 53 leave the ice unchanged? (the authors attribute it to short, moderate
  bursts; sublimation is confined to regions too small to matter in absorption).
* R10/R11: ice-band changes in edge-on disks are attributed to material moving through the line of sight; whether such
  changes are common is unknown (single objects).
* R2: how to recover ice measurements for the 22% variable targets.
* R14/R15: whether burst-driven ice processing can be caught "in the act" rather than as a fossil CO2 signature.

## 8. (Q8) Published results testable with TimeLens

* **EC 53 (R8)**: no ice change between quiescence and burst — a known-answer test. Our SPHEREx result: H2O τ
  2.00 ± 0.04, 2.07 ± 0.03, 2.10 ± 0.05 while the 3 µm continuum fell 78.5 → 19.5 mJy (p_change = 0.25); CO2 EW constant
  (p = 0.53). Consistent with R8 (VALIDATION/).
* **V1647 Ori (R12)**: ice reported unchanged between outburst states. Our baseline fit shows an apparent τ decrease
  that does **not** survive the continuum variants — consistent with R12 once systematics are included
  (REJECTED_CANDIDATES.md).
* R4's static ice detections could be re-tested for epoch-to-epoch stability, but the R4 candidate list is not public
  in machine-readable form in the material we saved; not attempted.

## 9. (Q9) Measurements not in existing catalogues

Per-visit H2O and CO2 optical depths and equivalent widths, and their between-visit differences, for variable embedded
protostars with matched non-variable controls. Neither SPLICES (R3), R4 nor the Ices pipeline (R2) provides them;
NEOWISE amplitudes are broad-band only.

## 10. (Q10) A realistic research question for this project

"Do the 3.05 µm H2O and 4.27 µm CO2 ice absorption bands of mid-IR-variable embedded protostars change between SPHEREx
visits by more than those of matched non-variable protostars, and does any change scale with the change in continuum
brightness as envelope sublimation would predict?" A null result with a quantified upper limit is itself useful:
it tells the Ices pipeline whether variable protostars can be measured with merged visits, and it extends the single
JWST null of R8 to a population.

Physical expectation (order of magnitude, our derivation, not from a paper): for an envelope with ρ ∝ r^−p the ice
column outside the sublimation radius scales as N ∝ r_sub^(1−p), and r_sub ∝ L^0.5, so d ln N / d ln L ≈ −0.25 for
p = 1.5 and −0.5 for p = 2 — but only for the fraction of the column that lies near r_sub. Most of the 3 µm absorption
arises at r ≫ r_sub (T < 90 K), so the expected Δτ for a factor-2 burst is small (few per cent of τ) unless the
envelope is compact. Re-freeze-out at n ~ 10⁷–10⁸ cm⁻³ takes ~10–100 yr (R14/R15), so a sublimated layer would not
recover between 6-month visits.

## 11. Search log (novelty)

| Date (2026) | Tool | Query / source | Result relevant to novelty |
|---|---|---|---|
| 13 Nov | web search | "SPHEREx multi-epoch ice absorption variability young stellar objects 2026" | R2, R4, R5, R6 only; none per-visit |
| 13 Nov | web search | "time variable water ice optical depth protostar outburst sublimation observed change 3 micron" | Graham 1998, AKARI 2022, V883 Ori (disk snow line) — no SPHEREx |
| 13 Nov | web search | "arXiv 2026 SPHEREx variable protostars spectrophotometry NEOWISE ice CO2 4.27 micron epoch" | R4, R6, R17; none per-visit |
| 13 Nov (earlier session) | web search + full text | EC 53 ice (R8, R9), V1647 Ori (R12), HV Tau C (R10), PDS 453 (R11), Karambelkar (R7), episodic accretion chemistry (R14, R15) | precedents listed above |
| 13 Nov (after the experiment) | web search | "SPHEREx ice absorption variability protostars multi-epoch H2O CO2 2026" | R2, R4, R5, R6 again; search synthesis: 2026 SPHEREx ice studies are single-cycle and treat variability as a data-quality issue; no multi-epoch ice result |
| 13 Nov (after the experiment) | web search | "time variable 3 micron water ice absorption young stellar object scattered light geometry variability" | R18, R19, R20, L1527 scattered-light variability (A&A 2019); no population measurement |
| 13 Nov (after the experiment) | web search | "J061359.25+174321.0" / "061359.25+174321" young stellar object Gemini OB1 | only general Gem OB1 papers (R21); nothing on this object |
| 13 Nov | SIMBAD (Harvard mirror; CDS down) | cone 15″ around all 86 targets; reference lists of IRAS 06110+1744 and 2MASS J22280298+6901166 | IRAS 06110+1744: 4 references (IRAS PSC; 1989ApJS...69..651C lunar-occultation list; 1995ApJ...450..201C; 2007PASJ...59.1185S H2O maser survey) — no spectroscopy, no variability study |

Limits: web search is not an exhaustive ADS/arXiv full-text query; papers submitted shortly before the cut-off, AAS
abstracts, and non-indexed theses may be missed. Novelty statements in this project are therefore phrased as "not found
in the literature searched", never "unpublished".
