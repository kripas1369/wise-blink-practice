# Primary research decision (Stages D–E)

## Decision

**Primary question (H1 + H2 of `RESEARCH_GAP_MATRIX.md`).** Do the 3.05 µm H2O and 4.27 µm CO2 ice absorption bands
of mid-infrared-variable embedded protostars change between independent SPHEREx visits by more than those of
brightness-matched non-variable protostars, and does any change follow the continuum change as envelope
sublimation/recondensation would predict?

**Secondary (H10).** How large is the bias and the loss of precision when the visits of a variable source are merged
into one spectrum (the approach of Serna et al. 2026 and the default of the Ices pipeline), measured on the same data?

**Backup (H3).** Prestellar-core central ice deficit in cores other than L1544, CrA 151, L260 and L1512.

## Answers to mission §10

1. *Strongest evidence of being unanswered:* H1. The official Ices overview (Melnick et al., arXiv:2603.22135, §5.2)
   states that ~22% of SPLICES targets are variable and will be excluded or specially processed; the only SPHEREx YSO
   population paper (Serna et al., arXiv:2610.38043) merges all visits; the only multi-epoch ice test of an outbursting
   protostar is a single JWST pair for EC 53 (Kim et al., arXiv:2604.08769), which found no change.
2. *Data:* verified, not assumed. Every sky position has three DR1+QR3 visits (Sep–Oct 2025, Mar–May 2026,
   Sep–Oct 2026 for the fields tested), and the stamp reader extracts all D3–D6 exposures in ~40 s per target
   (`DATA_RELEASE_AND_ACCESS_AUDIT.md`).
3. *Feasibility:* demonstrated end-to-end on EC 53 and V1647 Ori before the sample was run.
4. *Possibility of a new result:* a population measurement with controls does not exist; either a detection or an
   upper limit is new information. A positive individual detection is less likely: EC 53's null and the 0.1–0.3
   systematic in H2O found for V1647 Ori set a high bar.
5. *Validation:* EC 53 (published JWST null) is reproduced (τ_H2O 2.00 ± 0.04 / 2.07 ± 0.03 / 2.10 ± 0.05 while the
   continuum changed by a factor 4; p = 0.25). Controls are part of the design.

## Why not the alternatives

* **H3 (prestellar cores)** needs diffuse-light spectral mapping with zodiacal-light and star removal and a scattering
  model — a new analysis system rather than an extension of existing code (feasibility 6/15). Kept as backup.
* **H4 (transients)** overlaps directly with Karambelkar et al. 2026, whose objects must be excluded.
* **H5 (edge-on disks)** fails the data gate: HV Tau C and HK Tau B are a few arcsec from bright primaries, inside one
  6.2″ SPHEREx pixel.
* **H12 (H I lines)** fails the data gate: line equivalent widths are far below a channel width at R ≈ 40–130.

## Pre-registered analysis plan (fixed before the sample results were inspected)

* Sample: 36 VAR + 36 W2-matched CTRL protostars from SPLICES (random draw, seed 20261113), 12 background stars,
  2 validation objects (`TARGET_SELECTION.md`).
* Epochs: visits separated by > 60 d; a pass (> 20 d gap) is its own epoch only if every pass of the visit has complete
  band coverage. Coverage rule: H2O ≥ 2 exposures in each of core 2.95–3.20, blue 2.42–2.72, red 3.75–4.15 µm;
  CO2 ≥ 1 in each of core 4.235–4.295, blue 4.05–4.215, red 4.31–4.42 µm.
* Measurement: joint fit across epochs, shared band shape, per-epoch depth and continuum (`scripts/ice_fit.py`).
* Per-target test: F-test of one depth vs one depth per epoch; Benjamini–Hochberg at FDR 5% over all target–band tests.
* Robust change: |z| ≥ 3 in the baseline and same sign with |z| ≥ 2 in every alternative analysis (aperture photometry;
  for H2O also no drift, D3 range extension, no blue window, curved continuum, narrow red window).
* Systematic floor: extra scatter that makes the control z distribution unit-variance; all z re-evaluated with it.
* Population test: |z| of VAR vs CTRL consecutive-epoch pairs (Mann–Whitney, one-sided).
* Physical test: slope of Δ ln(depth) on Δ ln(continuum) for ice-detected targets (bootstrap over targets), compared
  with the envelope expectation of −0.25 to −0.5 for the sublimating fraction of the column (`LITERATURE_REVIEW.md` §10).
* Epoch-boundary sensitivity: repeat with the pass split disabled and with alternative gap thresholds.

Changes made after the plan was fixed are listed, with the reason, in `TARGET_SELECTION.md` §5 and
`SCIENTIFIC_LIMITATIONS.md`.
