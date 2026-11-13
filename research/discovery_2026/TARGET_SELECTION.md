# Target selection (Stage E)

All selections are reproducible from the saved query results with `scripts/select_targets.py` and
`scripts/choose_sample.py` (numpy seed 20261113). The per-target record with identifiers, epochs, S/N, flags and the
selection or rejection reason is `CANDIDATE_CATALOG.csv`.

## 1. Parent catalogue: SPLICES (IRSA TAP table `splices`, v8.6)

SPLICES (Ashby et al., arXiv:2501.17797) is the SPHEREx Ices target list. For each source it carries AllWISE
photometry, the YSO classification (`class_1`, `stype_ml`), an extinction estimate (`av`), the molecular cloud on the
sightline (`mc`, `mc_los`), IRAC neighbour contamination (`fluxratioi2`) and a NEOWISE long-term variability
classification following Park et al. (2021): `w2var_class` = N (not variable), L (linear trend), C (curved, period
> 1400 d), P (periodic, 200–1400 d), B (burst), D (drop), I (irregular), U (unclassified), and the amplitude
`w2varamp` (mag) over the ~2014–2024 NEOWISE baseline.

Query 1 (async job 28122138, 480 s, 12 745 rows; `data/selection/splices_protostars_w2lt10p5_query.json`):
protostars and flat-spectrum sources (`class_1` in YSO_P, YSO_F or `stype_ml` Class I / Flat) with 4 < W2 < 10.5.

Query 2 (async job 28122604, 505 s, 2 650 rows; `data/selection/splices_background_stars_query.json`): background
stars — `sel_type` = MAIN, 6 < W2 < 9, A_V > 25, `w2var_class` = N, `mc_los` = BE (behind a cloud).

## 2. Cuts (fixed before any sample source was analysed)

| Step | Rule | Reason | Remaining |
|---|---|---|---|
| 0 | query 1 | — | 12 745 |
| 1 | embedded: `class_1` = YSO_P or `stype_ml` = Class I YSO | envelope ice is the target | 6 293 |
| 2 | 6.0 < W2 < 9.5 and W1 > 6.5 | S/N for the 3 µm band; W1 ≲ 6 saturates the SPHEREx core (Elias 29, Elias 16 pilots: 0 usable core pixels) | 3 411 |
| 3 | `fluxratioi2` ≤ 20 % or not measured | IRAC 4.5 µm neighbours within 7.6″ would blend in 6.2″ pixels | 3 154 |
| 4 | not within 60″ of excluded objects | Karambelkar et al. 2026 transients and comparison objects; EC 53 and V1647 Ori (validation) | 3 152 |

VAR pool: `w2var_class` in {L, C, B, D, I} and `w2varamp` ≥ 1.0 mag → 171 sources. Periodic (P) sources were not
included: three visits sample arbitrary phases, which is a different experiment (H13).
CTRL pool: `w2var_class` = N → 1 609 sources.

36 VAR sources were drawn at random; each was paired with the unused CTRL source of the same embedded class closest
in W2 (|ΔW2| ≤ 0.3 mag), so variables and controls have the same brightness distribution and therefore the same
photometric noise and saturation behaviour. VAR classes drawn: C 14, I 11, L 8, B 2, D 1.

Background stars: from the 2 650 rows, W1 > 6.5 and excluding sources that the SPLICES classifier labels as YSO or
AGB (they carry their own circumstellar dust) → 1 823; 12 drawn at random. The pool is dominated by sightlines toward
M17 (653), Norma (355), M20 (258) and M16 (184); the drawn stars are in M17, M20, M16, Ara and Norma.

Validation objects: EC 53 (published JWST quiescent/burst ice spectra) and V1647 Ori (published ice spectra in
outburst and quiescence).

## 3. Exclusion checks (`data/selection/karambelkar_check.json`)

Every sample position was compared with all YSO-type objects of Karambelkar et al. 2026 (WTP16aakapb, WTP15aaavof,
WTP24abacpo, PGIR20dci/WTP14aabswi, FUOr-Aur0544+3330/WTP10aaktsc) and the comparison objects FU Ori, V900 Mon,
V1057 Cyg. Closest approach: 937″ (WTP15aaavof); no overlap. The three novae of that paper (PGIR19aetsqr,
PGIR22agyklf, Gaia22alz) were not position-checked on the assumption that a class-selected protostar sample cannot
contain novae; that assumption proved unsafe (the sample contains the unrelated nova V445 Pup, §4), but none of the
SIMBAD identifications of the 86 targets is one of those three objects.

## 4. Identifiers

Gaia DR3 (ESA archive, nearest source within 2″): 40 of 86 targets have a counterpart; the remainder are too
embedded for Gaia. SIMBAD at CDS was unavailable on 13 Nov 2026; the cross-match was run later that day through the
Harvard SIMBAD mirror (nearest object within 15″): 59 of 86 targets have a SIMBAD object
(`data/selection/simbad_xmatch.csv`, identifiers also in `CANDIDATE_CATALOG.csv`).

**Purity (found after the analysis):** SIMBAD identifies 2 VAR and 9 CTRL sources as non-protostars — V445 Pup
(nova), IRAS 07121-1158 (PN candidate), two Miras, two long-period variables, two AGB candidates, WRAY 16-162 (PN),
G 154-34 (high-proper-motion star) and HD 37017 (B-type binary). SPLICES classes alone do not guarantee a protostar.
They were kept in the pre-registered analysis and removed in a sensitivity check (`SCIENTIFIC_RESULTS.md` §3);
a future selection should require a SIMBAD/literature YSO type or exclude these types up front.

## 5. Changes after the plan was fixed

1. Background-star draw: the first draw (before any background star was analysed) contained two SPLICES "O AGB" and
   two YSO-classified sources; the YSO/AGB exclusion was added and the draw repeated. VAR, CTRL and validation lists
   were verified unchanged (`diff` against the earlier file).
2. Photometric quality: per-exposure PSF-fit χ²_red of several hundred in the M17/M20 background-star fields shows
   that bright H II-region nebulosity is not described by the point-source + plane model. A uniform quality rule is
   applied to all roles in the population analysis (see `SCIENTIFIC_RESULTS.md` §2); the rule uses fit quality only,
   never the measured depth change.
