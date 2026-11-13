# What changed from the night of 12 Nov to 13 Nov 2026

A guide for anyone reading the repo for the first time. It lists, in time order, what was added from the evening of
12 November to the afternoon of 13 November 2026, what each part found, how sure we are, and which file to open.

**Nothing below is committed to git yet.** The last commit is still `b03567e` ("Remove the Nepali language toggle").
All the new work sits in the working folder as uncommitted or untracked files.

**One word about wording.** None of this is a "discovery" of a new star. The results are *identifications* (which star
really produces a known signal) and *measurements* (how much something changes, with error bars). Each section says
how strong the evidence is.

---

## Quick reading order (about 30 minutes)

| Order | File | What you get | Time |
|---|---|---|---|
| 1 | this file | the overview | 5 min |
| 2 | [`notes/SPHEREX_BLEND_SURVEY.md`](notes/SPHEREX_BLEND_SURVEY.md) | the clearest result: which star really eclipses in six blended TESS pairs | 10 min |
| 3 | [`research/FINAL_EXECUTIVE_SUMMARY.md`](research/FINAL_EXECUTIVE_SUMMARY.md) | the TESS eclipsing-binary catalogue study (5 sky regions, 265 suspect entries) | 7 min |
| 4 | [`research/discovery_2026/FINAL_DISCOVERY_REPORT.md`](research/discovery_2026/FINAL_DISCOVERY_REPORT.md) — executive summary only | the ice study of young stars | 8 min |

If you want to learn how the Eclipse Mode page works first, read
[`learning/14_eclipse_mode_tess_and_flipbook.md`](learning/14_eclipse_mode_tess_and_flipbook.md) (a 2-hour lesson).

---

## Timeline

| When (Nepal time) | What | Where |
|---|---|---|
| 12 Nov, before 18:00 | Eclipse Mode and Methane Mode were built in the app (backend + frontend + tests). Not part of the night's work, but also uncommitted | `backend/app/eclipse*.py`, `backend/app/methane.py`, `frontend/eclipse.html`, `frontend/js/eclipse.js`, `frontend/js/methane.js` |
| 12 Nov, 18:00 | Methane pictures generated for five targets (Barnard's Star, WISE 0855, R Dra, RW Aur, eps Ind B) | `frontend/frames/*/methane/` |
| 12 Nov, 18:57 | Last edit to the eclipse page script | `frontend/js/eclipse.js` |
| 12 Nov, 19:09 | Two 2026 papers added (stable accretion from substellar objects; UPK 13 eclipsing binary seen by SPHEREx) | `researchpdf/11_…pdf`, `researchpdf/12_…pdf` |
| 12 Nov, 21:18 | Lesson 14 written: how Eclipse Mode lines SPHEREx photos up on TESS's eclipse clock; added to the lesson index | `learning/14_eclipse_mode_tess_and_flipbook.md`, `learning/README.md` |
| 12 Nov, 21:50 – 00:30 | Eclipse search in the SPHEREx deep field: which star really dims (TIC 233058262) | `scratch/` (git-ignored), write-up in `notes/ECLIPSE_FINDINGS.md` |
| 13 Nov, 00:40 – 09:00 | Overnight blend survey: all 11 unanswered TESS duplicate pairs tested with SPHEREx DR1 | `research/*.py`, `research/out/`, write-up in `notes/SPHEREX_BLEND_SURVEY.md` |
| 13 Nov, 09:00 – 11:25 | TESS eclipsing-binary catalogue study: Gaia cross-match + five sky regions | `research/` (reports `research/FINAL_*.md`) |
| 13 Nov, 11:40 – 17:25 | New research mission: does the ice around young stars change over time? | `research/discovery_2026/` |

---

## 1. Eclipse search: which star really dims? (night of 12 Nov)

**Write-up:** [`notes/ECLIPSE_FINDINGS.md`](notes/ECLIPSE_FINDINGS.md)

**The question.** The TESS eclipsing-binary catalogue (TESS-EBs) lists the same 26.28-day eclipse under two stars
29″ apart. TESS's pixels (21″) blur them; SPHEREx's pixels (6.2″) separate them.

**What we found.**

- Only the faint red star **TIC 233058262** dims (31 ± 4% during the main eclipse). The bright neighbour does not
  (−0.1 ± 0.8%).
- SPHEREx also sees the second, shallower eclipse (18 ± 2%) at phase 0.70, which means the orbit is eccentric
  (rough estimate e ≈ 0.4).
- The period is pinned to 26.27818 ± 0.0002 days, about 10 times more precise than the catalogue's value.
- From its Gaia colour and brightness, it is probably a pair of M dwarfs (small red stars) 282 parsecs (about 920
  light-years) away. No published study of it was found.

**Limits.** TESS observed this field again later, and the TESS team may already know the answer without having
published it. The "two M dwarfs" reading comes from colour, not a spectrum. SPHEREx dips are shallower than TESS's,
and we have not explained why.

---

## 2. Blend survey: six blended TESS pairs resolved (night of 12–13 Nov)

**Write-up:** [`notes/SPHEREX_BLEND_SURVEY.md`](notes/SPHEREX_BLEND_SURVEY.md) · **figures:**
`notes/screenshots/blend_survey/` · **code:** `research/classify_pairs.py`, `research/run_pairs.py`,
`research/plot_phase.py`, `research/summarise.py`

**The question.** TESS-EBs has **68 pairs of different stars that share one eclipse** (same period, less than 150″
apart). Only one star of each pair can be the real binary. Other catalogues (VSX, Gaia DR3, TESS Ten Thousand)
answer 31 pairs; 26 are too close for SPHEREx; **11 pairs had no answer anywhere**.

**What we found.** All 11 were tested with SPHEREx DR1 data:

| Real eclipsing star | Not eclipsing | Strength |
|---|---|---|
| TIC 233058262 | TIC 233058265 | very strong (section 1) |
| TIC 140659978 | TIC 140659980 | strong |
| TIC 150101476 | TIC 150101472 | good |
| TIC 258918831 | TIC 258918835 | good |
| TIC 269696430 | TIC 269696438 | good (few exposures) |
| TIC 420114772 | TIC 420114776 | probable — and here the catalogue's *deeper* eclipse is on the star that does **not** eclipse |

The other 5 pairs could not be settled (SPHEREx missed the eclipse, or the stars are too close).

**Checked how?** The method was first tested on three pairs where the answer is already known, and got all three
right. Each pair was measured three independent ways (circle photometry, a two-star fit, and a blind search for the
deepest dip at any phase).

**Side findings.**

- The app's SPHEREx data collections (`spherex_qr2`) are **obsolete**: IRSA now serves `spherex_dr1` and
  `spherex_qr3`, with 5–10 times more exposures in the deep fields. The app itself was **not** changed; the fix is
  described in the write-up.
- One TESS-EBs "binary" pair is actually WASP-140, a planet transiting a star.

**Limits.** Three of the five new answers are only about 3–4σ. Nothing has been checked with TESS's own pixels yet
(the tool TESS-Localize would do that). Nobody else has reviewed it.

---

## 3. TESS catalogue study: 265 entries probably on the wrong star (morning of 13 Nov)

**Write-ups:** [`research/FINAL_EXECUTIVE_SUMMARY.md`](research/FINAL_EXECUTIVE_SUMMARY.md) (short) and
[`research/FINAL_SCIENTIFIC_DISCOVERY_REPORT.md`](research/FINAL_SCIENTIFIC_DISCOVERY_REPORT.md) (full) · **numbers:**
`research/experimental_results/` · **how to rerun:** [`research/REPRODUCIBILITY.md`](research/REPRODUCIBILITY.md)

**The question.** Instead of duplicate pairs, look at every TESS-EBs entry: is there a Gaia DR3 eclipsing binary
with the same period nearby that is a *different* star?

**What we found.**

- 278 of 1,543 entries with a period-matched Gaia binary point to a different star (about 2 expected by chance).
  After removing impossible cases, **265 entries are probably attributed to the wrong star**.
- The error rate rises from 8–9% far from the Milky Way's plane to 30% inside it (crowded fields), as you would
  expect if blending causes it.
- Five of them, in five different sky regions (R1–R5), were checked directly with SPHEREx. In all five the Gaia
  binary eclipses and the catalogue star does not.
- Extra findings: in region R2 the catalogue has the primary and secondary eclipses swapped; in R5 the eclipses
  arrive about an hour late (a possible timing variation — a candidate only, 2–3σ).
- A wrong position in VSX (R3) and a SIMBAD label copied from the catalogue error (R5).

**Code improvements (research scripts only; the app was not touched):** forced photometry of every Gaia star at
once, a better model of the star image, a fix to the reference stars (an eclipsing binary had been used as a
reference), and a test of *where* the missing light is during eclipse. See
[`research/CODE_CHANGES.md`](research/CODE_CHANGES.md).

**Limits.** Only 5 of the 265 were checked directly, and they were not chosen at random, so the true error rate is
not yet known.

---

## 4. Ice study of young stars (afternoon of 13 Nov)

**Main report:** [`research/discovery_2026/FINAL_DISCOVERY_REPORT.md`](research/discovery_2026/FINAL_DISCOVERY_REPORT.md)
· **details:** `SCIENTIFIC_RESULTS.md`, `SCIENTIFIC_LIMITATIONS.md`, `VALIDATION/README.md` · **catalogue:**
`CANDIDATE_CATALOG.csv` (86 targets) · **code:** `research/discovery_2026/scripts/` · **how to rerun:**
`REPRODUCIBILITY.md` (all in `research/discovery_2026/`)

**The question.** Very young stars (protostars) are wrapped in dust coated with ice: water ice (absorbs light at
3 µm) and CO2 ice (at 4.27 µm). Many protostars change brightness. SPHEREx took spectra of the same stars in three
visits (Sep–Oct 2025, Mar–May 2026, Sep–Oct 2026). Does the ice change when the star changes? Previous work on this
repo (TESS eclipses, generic variable searches) was deliberately excluded so that the result would be new.

**What was measured.** 86 targets: 36 variable protostars, 36 steady protostars (controls), 12 background stars and
2 known validation stars. For each visit separately (not merged into one spectrum), the depth of the water and CO2
ice bands was measured with error bars.

**What we found.**

1. **The amount of ice is stable.** The CO2 band limits the change in ice amount between visits to **less than 8%**
   (95% confidence) in 25 variable protostars.
2. **The water band looks less stable than that.** Its depth wobbles by about 16% between visits — more than in the
   steady controls, and more than the CO2 limit allows. Since the ice itself cannot change that much, the most likely
   reason is a change in *how the light reaches us* (for example, some light escaping around the ice), not ice
   being destroyed or formed. This is an interpretation, not a measurement.
3. **Brightness changes are not caused by dust clouds passing in front.** The colour of the changes does not match
   dimming by dust.
4. **A warning for other researchers.** Merging all visits into one spectrum biases the measured ice depth by up to
   18% for variable stars.
5. **One candidate star: IRAS 06110+1744.** Its water-ice band went 0.70 → 0.52 → 0.68 over the three visits. This
   passed every check (7 analysis variants, removing any single exposure, neighbouring stars, control stars,
   injected fake signals). But a model where part of the light escapes unabsorbed fits just as well as a real ice
   change, and SPHEREx's spectral resolution cannot tell them apart. **It needs follow-up** (e.g. JWST or a
   ground-based spectrum).

**The original idea did not work.** The starting hypothesis was "ice changes when the star's brightness changes".
The data do not support it; result 1 replaces it.

**Found at the very end.** A check with the SIMBAD database showed that 2 of the 36 "variable protostars" are not
protostars at all (a nova, V445 Pup, and a possible planetary nebula) and neither are 9 of the 36 controls (old stars
such as Miras). Removing them barely changes the numbers, but it shows the input catalogue (SPLICES) is not clean.

**How sure are we?** On the mission's 1-to-5 scale: results 1–4 are **Level 3** (measured and checked, not
independently confirmed); the candidate star is **Level 4** (candidate needing follow-up); the original hypothesis is
**Level 5** (not supported).

**Limits.** Only 5 control pairs with detected ice pass the quality rule, so the comparison with controls rests on few
stars. The literature check used web search, SIMBAD and journal pages, not a full-text search of the astronomy
databases.

---

## What was *not* changed

- The website code (backend and frontend) was **not** changed after 19:00 on 12 Nov; the last edits were the methane
  pictures (18:00) and `frontend/js/eclipse.js` (18:57). All later code is research code in `research/`,
  `research/discovery_2026/scripts/` or `scratch/`.
- No earlier research or report was deleted or overwritten.
- Nothing was committed or pushed.

## Folder map of the new material

```
WHAT_CHANGED_NOV_12-13.md            ← this file
learning/14_eclipse_mode_…md         lesson on Eclipse Mode
notes/ECLIPSE_FINDINGS.md            section 1
notes/SPHEREX_BLEND_SURVEY.md        section 2
notes/screenshots/blend_survey/      figures for section 2
research/                            section 3 (+ the code for section 2)
  FINAL_EXECUTIVE_SUMMARY.md
  FINAL_SCIENTIFIC_DISCOVERY_REPORT.md
  experimental_results/  out/  papers/
research/discovery_2026/             section 4
  FINAL_DISCOVERY_REPORT.md
  SCIENTIFIC_RESULTS.md  SCIENTIFIC_LIMITATIONS.md  REJECTED_CANDIDATES.md
  CANDIDATE_CATALOG.csv  scripts/  EXPERIMENTAL_RESULTS/  VALIDATION/
scratch/                             git-ignored working scripts for section 1
```
