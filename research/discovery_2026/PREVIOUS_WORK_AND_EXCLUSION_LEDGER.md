# Previous work and exclusion ledger (Stage A)

Audit date: 13 Nov 2026. Repository `wise-blink-practice`, branch `kripas-frontend` (owner's uncommitted changes
present; nothing in this mission is committed). Purpose: list what TimeLens and earlier research already did, so that
nothing below is presented as a new result of this mission.

## 1. Existing TimeLens capabilities reused (not new)

| Capability | Where | Used in this mission for |
|---|---|---|
| SPHEREx image search through IRSA TAP `spherex.obscore`, epoch grouping (gap 30 d, max span 60 d) | `backend/app/archive.py` | Concept of visits/epochs; not called directly (S3 range reader is faster, see `DATA_RELEASE_AND_ACCESS_AUDIT.md`) |
| FLAGS bit decoding for QR2 (`MP_*`) and QR3/DR1 (`MSKN*`/`MSKM*`) headers, official bad-flag list | `backend/app/flags.py`, `config.BAD_FLAG_NAMES` | Imported unchanged by `scripts/spx_s3.py` |
| Spectral WCS (`WCS-WAVE`, key `W`) per-pixel wavelength | `backend/app/clean.py` | Replaced by the calibration CWAVE map (agrees to ≤ 3.4 nm, `access_check.json`) |
| Forced multi-star PSF photometry (pixel-integrated Gaussian + wing) | `research/field_psf.py` | Design reference; this mission fits the official ePSF instead |
| DR1 + QR3 collections list | `research/dr1.py` | Same collections queried |
| Methane-dip spectra, Eclipse Mode, Blink Flipbook, difference views | `backend/app/methane.py`, `eclipses.py`, frontend | Not used |

The production backend still lists QR2 collections (`backend/app/config.py: COLLECTIONS`); this mission does **not**
change production code (no demonstrated requirement; research scripts live in `research/discovery_2026/scripts/`).

## 2. Earlier research results — excluded from novelty claims

| Item | Status before this mission | Treatment here |
|---|---|---|
| TESS-EBs misattribution (5 regions R1–R5, 265-entry catalogue list) | Reported in `research/FINAL_SCIENTIFIC_DISCOVERY_REPORT.md` | Excluded; not reused |
| R2 primary/secondary label swap, R5 eclipse-timing offset candidate | Same report | Excluded |
| Two blind periodicities (rejected: half-data only; one detector only) | Same report §5 | Excluded |
| VSX (R3) and SIMBAD (R5) attribution corrections | Same report | Excluded |
| Ice dips (H2O 3.0 µm, CO2 4.27 µm) in three reddened stars behind Barnard 68, single co-added spectra (τ_H2O 0.48, 0.84, 1.33) | Commit `83060d7`, `experiments/ice_check.py` | Excluded as prior static TimeLens result; shows that SPHEREx detects the bands, which this mission builds on |
| H16 "ice absorption toward YSOs in LH 47" | Scored, **not tested** (`research/experimental_results/hypotheses.md`) | Not pursued (LMC sources are too faint for per-exposure ice photometry) |
| RW Aur D5/D6 brightness drop Mar→Sep 2026 (ratios 0.633, 0.770) | Preliminary, not validated (`notes/DAY6_FINDINGS.md`) | Not claimed; RW Aur is a Class II source without deep ices |
| Methane (3.3 µm) dips in brown dwarfs and R Dra/WISE 0855 demos | Frontend demonstrations | Excluded |
| Generic variable-star searches | VarWISE (Paz 2024) and earlier TimeLens blinking | Excluded as a research aim |

## 3. External work excluded from novelty (details in `LITERATURE_REVIEW.md`)

- Karambelkar et al. 2026 (SPHEREx spectra of eruptive young stars): their targets and findings are not presented as new.
- Published static SPHEREx ice studies (QR1/QR2 merged-visit spectra, arXiv:2610.38043 and the SPHEREx ices team
  papers) and published ice maps of prestellar cores (L1544, CrA 151, L260, L1512).
- JWST two-epoch EC 53 ice result (EPISODE IV): no measurable ice change between quiescence and burst.
  EC 53 is used here only as a **known-answer validation target**.
- V1647 Ori ground-based ice spectra 2004–2007 (Gibb et al. 2006; Aspin et al. 2008): ice depth unchanged through
  the outburst. Used as a second known-answer case.
- 3I/ATLAS SPHEREx results.

## 4. What this mission adds that did not exist in the repository

1. A byte-range reader for SPHEREx L2 files on IRSA's public S3 mirror, including row-tiled RICE_1 FLAGS, verified
   pixel-for-pixel against astropy on a full DR1 file (`scripts/spx_s3.py`).
2. Forced photometry with the official SPHEREx ePSF (calibration table verified byte-identical to the image EPSF).
3. Per-epoch ice-band fitting with a band shape shared across epochs, drift-immune CO2 normalisation per exposure
   group, a formal no-change test and systematics variants (`scripts/ice_fit.py`).
4. A population multi-epoch test of ice-band variability in variable protostars with matched controls
   (results in `SCIENTIFIC_RESULTS.md`).
