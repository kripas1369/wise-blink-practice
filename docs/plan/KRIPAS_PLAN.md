# Kripas's personal plan (data and science lead)

**My job:** everything that touches the data. Finding SPHEREx images, downloading cutouts, cleaning, lining up epochs, adding up, Gaia positions, difference images, light curves, spectra, the API, and the science text. I hand [Friend's name] clean JSON and PNGs in the API format of [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

**Partner:** [Friend's name] (website and presentation). See [FRIEND_PLAN.md](FRIEND_PLAN.md).

**We practise the real hackathon project:** SPHEREx data, the 5 official targets, the same features. On 14 Nov I write it again from memory in a new repo (no copying). I ask the Nepal local lead in writing whether this practice is allowed.

---

## Phase 1: 4-day practice build (Sat 31 Oct – Tue 3 Nov)
About 7 hours a day, in 3 blocks. For each block: the AI explains → **I type the code** → "review Day N block M" → commit. End of day: learning log, pull request `kripas-backend` → `main`, 15-minute call. Explanations of everything built: [`learning/`](../../learning/README.md).

### Day 1, Sat 31 Oct: Step 1, find and get the data
**Status: done (31 Oct).** `backend/app/` config, coords, motion, resolve, targets, flags, archive; `scripts/day1_report.py`; 24 offline + 3 network tests pass; results in `notes/DAY1_REPORT.md` and `FACTS.md` §6. Walkthrough: [`learning/02_code_walkthrough.md`](../../learning/02_code_walkthrough.md). **Re-type it yourself** before Day 2 (the speed drill depends on it).
- **Block 1 (2 h, with [Friend's name]):** revise how to query and get cutouts.
  - IRSA TAP `https://irsa.ipac.caltech.edu/TAP`; table `spherex.obscore`; condition `CONTAINS(POINT('ICRS', ra, dec), s_region) = 1`.
  - Columns: `obs_id`, `t_min`, `energy_bandpassname`, `em_min`, `em_max`, `access_url`, `access_estsize`.
  - The IRSA SPHEREx cutout tutorial: how to ask for a small square instead of the 70 MB file.
  - Inside a cutout: IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE; header `MJD-AVG`.
  - Gaia DR3 at IRSA: `gaia_dr3_source`. SIMBAD: main CDS server, backup `simbad.harvard.edu`.
- **Block 2 (2.5 h):** `coords.py` (12 tests pass) and `resolve.py` (name → position, mirror as backup, clear error, never a guess).
- **Block 3 (2.5 h):** `archive.py`.
  - Move the target to today's position with its proper motion, then query.
  - For each of the 5 targets: number of images, first and last date, images per detector D1 – D6.
  - Download one Barnard's Star cutout; print every extension and the header.
- **Done when:** a table of the 5 targets (count, dates, detectors) is in `FACTS.md`, and one cutout opens with all its parts.

### Day 2, Sun 1 Nov: Step 2a, clean and line up the epochs
- **Block 1 (2 h):** epochs: `archive.group_epochs` already exists (30-day gap, 60-day maximum). Add per-detector frames and use `MJD-AVG` from each cutout header.
- **Block 2 (2.5 h):** `clean.py`:
  - official flag mask with `flags.bad_pixel_bitmask(header)` (reads QR2 `MP_*` and QR3 `MSKN*`; SOURCE is a label only, never cancels a bad bit);
  - IMAGE − ZODI; sigma = sqrt(VARIANCE); % flagged.
- **Block 3 (2.5 h):** `align.py` + `render.py`:
  - every cutout onto one sky grid around the target (`reproject`); check background stars stay on the same pixel;
  - one PNG per epoch and detector, **same brightness scale for all**;
  - send PNGs + JSON to [Friend's name].
- **Done when:** Barnard's Star frames from different epochs are lined up and the star is in a different place in the first and last.

### Day 3, Mon 2 Nov: Step 2b, compare with proof (integration day)
- **Morning call:** fix the API format in `docs/plan/FACTS.md` section 7.
- **Block 1 (2 h):** `coadd.py`: 1/variance-weighted add-up per epoch and detector.
- **Block 2 (2 h):** `gaia.py`: Gaia DR3 stars near the target, moved from 2016.0 to each epoch's date. `diff.py`: epoch B − A in sigma.
- **Block 3 (3 h):** FastAPI `main.py`: `/api/resolve`, `/api/coverage`, `/api/frames`, `/api/gaia`, `/api/diff`; disk cache.
- **Done when:** **Barnard's Star walks across the browser flipbook onto its Gaia markers.**

### Day 4, Tue 3 Nov: connect, online, test
- **Block 1 (2 h):** `/api/lightcurve` (brightness at one position, all epochs, with errors, flagged marks and the **wavelength** of each point, because of the LVF).
- **Block 2 (2 h):** pre-cache the 5 targets; run the C4 acceptance tests; write results.
- **Block 3 (3 h):** deploy with [Friend's name]; lessons note.
- **Done when:**
  - Barnard's Star shift (expected ~1.7 px) within about 0.5 px of Gaia;
  - WISE 0855 visible in D5 – D6, not in D1 – D3;
  - R Dra and RW Aur change brightness;
  - an empty or bad position gives an honest message;
  - the public link works.

### Wed 4 – Fri 6 Nov
- **Wed 4 morning:** fix anything that failed on Day 4.
- **Wed 4 afternoon:** Level 3: `/api/spectrum` (brightness vs wavelength, per epoch); measured motion vs Gaia; proof-panel numbers in the API.
- **Thu 5:** Supplement 2.2, 3.2.5, 3.2.9, 3.4.3; finish `FACTS.md`; one cross-check against IRSA's Spectrophotometry Tool. Evening: speed drill: empty folder → resolve → coverage → one cutout → clean → PNG in 3 hours, from memory. Delete afterwards.
- **Fri 6:** rest; rehearsal checklist.

---

## Phase 2: Timed rehearsal of the real hackathon (Sat 7 – Sun 8 Nov, 48 hours), my column
Empty private repo `spherex-rehearsal`; build from memory and notes.

| Hours | My task | I give to [Friend's name] | I need from [Friend's name] |
|---|---|---|---|
| 0–2 | Read the challenge together; write the API format | API format | Screen sketch |
| 2–10 | resolve, coverage, cutouts, clean, PNG frames, `/api/frames` | Sample PNGs + JSON by hour 4 | — |
| 10 | **Checkpoint:** Barnard's Star plays end to end | Working `/api/frames` | Flipbook calling it |
| 10–14 | Pre-cache the 5 targets; help first deploy | Cache | Deploy link |
| 14–22 | Align, add-up per epoch and detector, `/api/gaia` | Gaia JSON | Labels showing my numbers |
| 22–26 | C4 tests on all 5 targets; sleep shift | Results | — |
| 26–34 | `/api/diff` (sigma), `/api/lightcurve` | Diff PNGs, light-curve JSON | Diff mode, chart |
| 34–40 | `/api/spectrum`, measured motion vs Gaia (only if Level 2 passes) | Spectrum JSON | Spectrum panel |
| 40–46 | Limitations, references, NASA data text; mock submission | Project page text | Video draft to check |
| 46–48 | Pitch practice (I explain the science) | — | — |

## Phase 2.4: Review (Mon 9 – Tue 10 Nov)
- My half of the lessons note (planned vs actual hours per backend task).
- **1-page backend cheat sheet:** table names, columns, query shape, cutout method, cleaning steps, Gaia steps, deploy command. Notes only.
- Update Part E backend timings.

---

## Phase 3: Final prep (Wed 11 – Fri 13 Nov)
- **Wed 11:** check `FACTS.md` once more against the Supplement and IRSA.
- **Thu 12:** speed drill (3 hours) from an empty folder. Delete afterwards.
- **Fri 13:** read the Resources tab and Submission Guide with [Friend's name]; check IRSA and the SIMBAD mirror work from the venue or a hotspot; sleep early.

---

## Phase 4: Hackathon (Sat 14 – Sun 15 Nov), my tasks
New empty repo; write it again (no copying). Follow HACKATHON_PLAN Part E, backend column:
- **0–2:** read the statement and resources; create the repo; API format.
- **2–10:** resolve, coverage (`s_region`), cutouts, official flag mask, IMAGE − ZODI, PNG frames with `MJD-AVG`, `/api/frames`. Sample frames to [Friend's name] by hour 4.
- **10–14:** Barnard's Star end to end; pre-cache the 5 targets.
- **14–22:** alignment, add-up per epoch and detector, `/api/gaia`.
- **22–26:** C4 acceptance tests on all 5 targets.
- **26–34:** `/api/diff` (sigma), `/api/lightcurve`.
- **34–40:** `/api/spectrum`, measured motion vs Gaia (only if Level 2 passes).
- **40–46:** limitations, references, NASA data section. **Submit by hour 46.**
- **46–48:** pitch practice.

## What I must never do
- Use `DATE` for time. Mask on SOURCE. Let SOURCE cancel a bad flag. Show a made-up value when something fails. Claim a discovery. Copy practice code into the hackathon repo.
