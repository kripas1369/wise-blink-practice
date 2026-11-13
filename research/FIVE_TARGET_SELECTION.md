# Five new sky regions

All numbers come from files in `research/out/` and `research/five_target_catalog.csv` (machine-readable version of
the table below, written by `research/five_targets.py`).

## What links the five regions

Each region is centred on a TESS eclipsing-binary catalogue entry (TESS-EBs, Prša et al. 2022) for which our
cross-match against the Gaia DR3 eclipsing-binary table (Mowlavi et al. 2023) found a **same-period Gaia eclipsing
binary on a different star**, and that other star is **not itself in TESS-EBs** (`research/tessebs_gaia_xmatch.py`,
265 such entries out of 4,582). The hypothesis being tested in each region is:

> The eclipses TESS-EBs assigns to the TIC star are really the eclipses of the neighbouring Gaia binary, diluted by
> the TIC star's light in the 21″ TESS pixels.

SPHEREx (6.2″ pixels, 0.75–5 µm, many visits near the ecliptic poles) can test this star by star: if the hypothesis
is right the Gaia binary must dim at the TESS eclipse times and the TIC star must not.

## Selection procedure

1. Start from the 265 entries with the real source missing from TESS-EBs.
2. Remove every star already used by the project: the website eclipse catalogue (`on_website_catalog = false` for all
   five) and the 68 duplicate pairs of the overnight survey (`notes/SPHEREX_BLEND_SURVEY.md`). A text search of the
   whole repository outside this investigation's own files finds none of the five TIC numbers.
3. Rank by separation (≥ 7″, so SPHEREx can separate the stars), SPHEREx coverage near the ecliptic poles, and the
   brightness of the Gaia binary.
4. Query the SPHEREx archive (DR1 + QR3) for 12 candidates (`research/coverage_candidates.py`) and keep only those
   whose eclipse times are still known in 2026 (TESS-EBs clock error < 0.01 in phase) or that have an independent
   precise clock.
5. Choose five that differ in environment and in the kind of question they test.

Candidates queried but not used, with the reason:

| TIC | reason |
|---|---|
| 453095485 | TESS clock error 0.030 in phase by 2026 (eclipse times unknown) |
| 320323992 | clock error 0.099 |
| 364965655 | clock error 0.060 |
| 405764176 | clock error 0.175 |
| 29983149 | only 4 SPHEREx images inside primary eclipse |
| 177175199 | usable (clock 0.002, 960 images) — kept as a spare |
| 220420534 | Gaia binary only 5.1″ away (< 1 SPHEREx pixel) |

## The five regions

| | TIC (TESS-EBs) | RA, Dec (deg) | Galactic l, b | Environment | Gaia DR3 eclipsing binary | sep. | SPHEREx images (in primary) | dates (UTC) |
|---|---|---|---|---|---|---|---|---|
| R1 | 179637488 | 80.51578, −67.92467 | 278.3, −33.3 | LMC, LH 47 OB association (crowded, nebular) | 4658741684445417856 = OGLE-LMC-ECL-13800, G 14.30 | 12.6″ | 8,381 (775) | 2025-04-24 – 2026-10-04 |
| R2 | 349156098 | 108.18345, −64.70905 | 275.6, −22.1 | sparse field near the south ecliptic pole | 5282506656766565376 = ASASSN-V J071248.16-644303.5, G 15.53 | 40.6″ | 783 (102) | 2025-04-27 – 2026-08-07 |
| R3 | 309659126 | 79.50676, −60.68995 | 269.8, −34.8 | SPHEREx deep coverage, south | 4761080447161537664 = UCAC4 147-005376, G 11.38 | 7.4″ | 27,783 (2,678) | 2025-04-25 – 2026-10-04 |
| R4 | 160195393 | 258.85064, +85.21150 | 117.9, +29.0 | north celestial polar cap (Milky Way field) | 1724476407826709504 = ASASSN-V J171505.23+851208.0, G 12.21 | 41.0″ | 410 (69) | 2025-08-31 – 2026-09-30 |
| R5 | 31511621 | 89.15761, −67.60690 | 277.6, −30.1 | SPHEREx south ecliptic pole deep field, LMC edge | 4659556972307750528 = OGLE-LMC-ECL-39123, G 16.19 | 18.3″ | 6,944 (1,034) | 2025-04-24 – 2026-10-04 |

All five are observed in all six SPHEREx detectors (0.75–5.0 µm: D1 0.75–1.09, D2 1.10–1.62, D3 1.63–2.41,
D4 2.42–3.82, D5 3.83–4.41, D6 4.42–5.00 µm), from the DR1 and QR3 collections
(`spherex_dr1`, `spherex_qr3`). Images per detector are in the CSV.

TESS-EBs values (period, epoch, depth, Tmag) for the five TIC stars:

| | Tmag | period (d) | primary depth | secondary listed? | TESS sectors (2-min) | TESS clock error 2026 (phase) |
|---|---|---|---|---|---|---|
| R1 | 12.88 | 3.2969808 | 3.9% | yes | 21 sectors (1–13, 27–37) | 0.0017 |
| R2 | 9.78 | 1.2014857 | 0.22% | no | 25 sectors (1–13, 27–39) | 0.0050 |
| R3 | 10.11 | 0.2482701 | 5.7% | yes | 22 sectors (2–13, 27–37) | 0.0095 |
| R4 | 10.47 | 0.5728941 | 1.9% | yes | 14, 19, 20, 25, 26 | 0.0022 |
| R5 | 11.59 | 2.6294860 ± 0.00048 | 0.33% | yes | 11, 12 only | 0.19 → OGLE clock used |

Image quality (fitted PSF core σ, pixels, D1–D6) is similar in all five fields: 0.53–0.57 px in D1–D3,
0.59–0.71 px in D4–D5, 0.61–0.87 px in D6 (largest in the nebular R1 field); per-detector values and co-add χ² are
in the CSV.

## Why each region (scientific diversity)

- **R1 — crowded, young LMC field.** The TIC star is LH 47-237, a blue supergiant (G 12.7; Gaia variability class
  BE|GCAS|SDOR|WR). The Gaia binary is OGLE-LMC-ECL-13800 (OGLE: P = 3.2969676 d, I-band depths 0.48 and 0.32 mag)
  only 12.6″ (2 SPHEREx pixels) away, among 134 Gaia stars brighter than G = 16.5 in a 4′ box, with a classical
  Cepheid (ASASSN-V J052158.53-675534.9) 21″ away and diffuse nebular light. This is the hardest test of the method.
- **R2 — clean, isolated.** Only 10 Gaia stars in the box; the Gaia binary is 5.3 mag fainter than the TIC star and
  6.5 pixels away. The TESS depth (0.22%) is exactly what a 25–50% eclipse diluted ~120 times would look like.
- **R3 — catalogue conflict at the resolution limit.** VSX places the ASAS contact binary ASAS J051801-6041.4
  (P = 0.248268 d) on the TIC star TYC 8878-311-1; Gaia DR3 places the eclipsing binary on UCAC4 147-005376, 7.4″
  away (1.2 SPHEREx pixels). ASAS (15″ pixels) and TESS (21″) cannot tell them apart. Deepest SPHEREx coverage of
  the five (27,783 images).
- **R4 — the northern sky.** A high-proper-motion Tycho star near the north celestial pole, with the ASAS-SN
  binary ASASSN-V J171505.23+851208.0 (EA|EB, P = 0.572889 d) 41″ away. Independent of the LMC/south pole fields.
- **R5 — conflicting identifications and a lost TESS clock.** SIMBAD lists the TIC star itself as the MACHO
  eclipsing binary 71.12422.12, while OGLE places the 2.629-d binary OGLE-LMC-ECL-39123 (P = 2.6288690 d,
  T0 = HJD 2457001.2388, I depths 0.48 / 0.23 mag) 18.3″ away and a second binary OGLE-LMC-ECL-39130
  (P = 2.5643685 d) 25″ away. The TESS-EBs period (2.6294860 d) differs from OGLE's by 6.2 × 10⁻⁴ d, so by 2026 the
  TESS clock is off by 0.19 in phase; the analysis is folded on the OGLE ephemeris
  (`research/data/eph_ogle_lmc_ecl_39123.json`).

## Known literature for each region

| | Known before this work |
|---|---|
| R1 | OGLE-IV LMC eclipsing binaries (Pawlak et al. 2016, AcA 66, 421): OGLE-LMC-ECL-13800; LH 47 association (Lucke & Hodge 1970; Oey & Massey 1995: LH 47-237); Gaia DR3 variability classification (Eyer et al. 2023) |
| R2 | ASAS-SN variable stars (Jayasinghe et al. 2018–2021): ASASSN-V J071248.16-644303.5 |
| R3 | ASAS (Pojmański 2002) / VSX: ASAS J051801-6041.4; Gaia DR3 EB (Mowlavi et al. 2023); ROSAT source 1RXS J051803.3-604059 20″ away |
| R4 | ASAS-SN: ASASSN-V J171505.23+851208.0; Gaia DR3 EB |
| R5 | OGLE-IV LMC (Pawlak et al. 2016): OGLE-LMC-ECL-39123, -39130; MACHO (Alcock et al.) 71.12422.12 |

None of these papers attributes the TESS-EBs signal of the TIC star to the neighbour; that attribution, and its
SPHEREx test, are what is new here (see `FINAL_SCIENTIFIC_DISCOVERY_REPORT.md` for the classification of each
result).
