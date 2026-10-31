# [Friend's name]'s personal plan (data and science lead)

GitHub: `lazylog00`. Branch: `friend-backend`. Folder: `backend/`.

**Your job:** everything that touches the data. Finding SPHEREx images, downloading cutouts, cleaning, lining up epochs, adding up, Gaia positions, difference images, light curves, spectra, the API, and the science text. You hand Kripas clean JSON and PNGs in the API format of [HACKATHON_PLAN.md](HACKATHON_PLAN.md) Part C2.

**Partner:** Kripas Khatiwada (website and presentation). See [KRIPAS_PLAN.md](KRIPAS_PLAN.md).

**Roles swapped on 31 Oct:** you now do the data side; Kripas does the website. The Day 1 data code already exists (made on 31 Oct before the swap); it is yours now. Read it and re-type it so you can rebuild it from memory.

**We practise the real hackathon project:** SPHEREx data, the 5 official targets, the same features. On 14 Nov you write it again from memory in a new repo (no copying).

---

## Phase 1: 4-day practice build (Sat 31 Oct – Tue 3 Nov)
About 7 hours a day, in 3 blocks. For each block: the AI explains → **you type the code** → "review Day N block M" → commit. End of day: learning log, pull request `friend-backend` → `main`, 15-minute call with Kripas. Explanations of everything built: [`learning/`](../../learning/README.md).

### Day 1, Sat 31 Oct: Step 1, find and get the data (take over the existing code)
**Start here: [FRIEND_DAY1_STEPS.md](FRIEND_DAY1_STEPS.md)**, every command with the result you should see (all checked on a fresh copy on 31 Oct).

**Status: the code is done (31 Oct).** `backend/app/` config, coords, motion, resolve, targets, flags, archive; `scripts/day1_report.py`; 24 offline + 3 network tests pass; results in `notes/DAY1_REPORT.md` and `FACTS.md` §6. Your Day 1 is to **own** it:
- **Block 1 (2 h, with Kripas):** Kripas walks you through it.
  - Read [`learning/00`](../../learning/00_big_picture.md), [`01`](../../learning/01_day1_what_we_built.md), [`03`](../../learning/03_archive_facts_and_mistakes.md).
  - IRSA TAP `https://irsa.ipac.caltech.edu/TAP`; table `spherex.obscore`; condition `CONTAINS(POINT('ICRS', ra, dec), s_region) = 1`; the 4 science collections (QR2, QR3, and their `_deep`).
  - Inside a cutout: IMAGE, FLAGS, VARIANCE, ZODI, PSF (QR2) or EPSF (QR3), WCS-WAVE; header `MJD-AVG`.
  - Gaia DR3 at IRSA: `gaia_dr3_source`. SIMBAD: main CDS server, backup `simbad.harvard.edu`.
- **Block 2 (2.5 h):** set up the venv (`pip install -r requirements.txt`), run the tests and `python -m scripts.day1_report`. Read [`learning/02_code_walkthrough.md`](../../learning/02_code_walkthrough.md) next to the code.
- **Block 3 (2.5 h):** re-type `coords.py`, `motion.py`, `resolve.py`, `flags.py` and `archive.find_images` in a scratch folder from the walkthrough, without copying; run the tests against your version. Do the 4 exercises at the end of `learning/02`.
- **Done when:** you can explain each step of the pipeline, all tests pass on your laptop, and one coverage count matches IRSA's own SPHEREx Data Explorer search.

### Day 2, Sun 1 Nov: Step 2a, clean and line up the epochs
**Step-by-step guide: [`FRIEND_DAY2_STEPS.md`](FRIEND_DAY2_STEPS.md)** (Kripas's flipbook and sample frames are ready; your frames replace the samples in the format of [`FRAMES_FORMAT.md`](FRAMES_FORMAT.md)).
- **Block 1 (2 h):** epochs: `archive.group_epochs` already exists (30-day gap, 60-day maximum). Add per-detector frames and use `MJD-AVG` from each cutout header.
- **Block 2 (2.5 h):** `clean.py`:
  - official flag mask with `flags.bad_pixel_bitmask(header)` (reads QR2 `MP_*` and QR3 `MSKN*`; SOURCE is a label only, never cancels a bad bit);
  - IMAGE − ZODI; sigma = sqrt(VARIANCE); % flagged.
- **Block 3 (2.5 h):** `align.py` + `render.py`:
  - every cutout onto one north-up sky grid around the target (`reproject`); check background stars stay on the same pixel;
  - one PNG per epoch and detector, **same brightness scale for all**;
  - send PNGs + JSON to Kripas.
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
- **Block 3 (3 h):** deploy with Kripas; lessons note.
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

## Phase 2: Timed rehearsal of the real hackathon (Sat 7 – Sun 8 Nov, 48 hours), your column
Empty private repo `spherex-rehearsal`; build from memory and notes.

| Hours | Your task | You give to Kripas | You need from Kripas |
|---|---|---|---|
| 0–2 | Read the challenge together; write the API format | API format | Screen sketch |
| 2–10 | resolve, coverage, cutouts, clean, PNG frames, `/api/frames` | Sample PNGs + JSON by hour 4 | — |
| 10 | **Checkpoint:** Barnard's Star plays end to end | Working `/api/frames` | Flipbook calling it |
| 10–14 | Pre-cache the 5 targets; help first deploy | Cache | Deploy link |
| 14–22 | Align, add-up per epoch and detector, `/api/gaia` | Gaia JSON | Labels showing your numbers |
| 22–26 | C4 tests on all 5 targets; sleep shift | Results | — |
| 26–34 | `/api/diff` (sigma), `/api/lightcurve` | Diff PNGs, light-curve JSON | Diff mode, chart |
| 34–40 | `/api/spectrum`, measured motion vs Gaia (only if Level 2 passes) | Spectrum JSON | Spectrum panel |
| 40–46 | Limitations, references, NASA data text; mock submission | Project page text | Video draft to check |
| 46–48 | Pitch practice (you explain the science) | — | — |

## Phase 2.4: Review (Mon 9 – Tue 10 Nov)
- Your half of the lessons note (planned vs actual hours per backend task).
- **1-page backend cheat sheet:** table names, columns, query shape, cutout method, cleaning steps, Gaia steps, deploy command. Notes only.
- Update Part E backend timings.

---

## Phase 3: Final prep (Wed 11 – Fri 13 Nov)
- **Wed 11:** check `FACTS.md` once more against the Supplement and IRSA.
- **Thu 12:** speed drill (3 hours) from an empty folder. Delete afterwards.
- **Fri 13:** read the Resources tab and Submission Guide with Kripas; check IRSA and the SIMBAD mirror work from the venue or a hotspot; sleep early.

---

## Phase 4: Hackathon (Sat 14 – Sun 15 Nov), your tasks
New empty repo; write it again (no copying). Follow HACKATHON_PLAN Part E, backend column:
- **0–2:** read the statement and resources; create the repo; API format.
- **2–10:** resolve, coverage (`s_region`), cutouts, official flag mask, IMAGE − ZODI, PNG frames with `MJD-AVG`, `/api/frames`. Sample frames to Kripas by hour 4.
- **10–14:** Barnard's Star end to end; pre-cache the 5 targets.
- **14–22:** alignment, add-up per epoch and detector, `/api/gaia`.
- **22–26:** C4 acceptance tests on all 5 targets.
- **26–34:** `/api/diff` (sigma), `/api/lightcurve`.
- **34–40:** `/api/spectrum`, measured motion vs Gaia (only if Level 2 passes).
- **40–46:** limitations, references, NASA data section. **Submit by hour 46.**
- **46–48:** pitch practice.

## What you must never do
- Use `DATE` for time. Mask on SOURCE. Let SOURCE cancel a bad flag. Show a made-up value when something fails. Claim a discovery. Copy practice code into the hackathon repo.
