# Hackathon readiness (Team Not42) — practice vs global nomination

**Updated:** 6 Nov 2026. **Event:** 14–15 Nov 2026. **Goal:** #1 in Nepal → **global nomination**.

## Is `wise-blink-practice` the final project?

**No.** This repo is **practice only** (team rule):

- Do **not** submit it on spaceappschallenge.org.
- On **14 Nov** start a **new empty repo** and rebuild during the event (**no copying** from this code).
- Keep this repo **private**; notes (`FACTS.md`, cheat sheets, findings) are allowed at the hackathon.

What you have here is a **rehearsal of the real tool** — most of Level 1–3 from the plan — so the 48-hour build is faster and more honest.

---

## What practice already covers (good for judges’ *Validity* and *Relevance*)

| Required / optional (challenge) | Practice status |
|--------------------------------|-----------------|
| Public web tool, RA/Dec + names | Done (search, SIMBAD, 5 targets) |
| Flipbook / time series | Done (play, blink, visits) |
| 5 official targets | Done (prepared frames; IRSA job for other positions) |
| FOV slider, URL share | Done |
| Aladin + Astropy | Done |
| Flag overlay + % flagged | Done |
| Gaia overlays (moved per visit) | Done |
| Before / After / Difference (σ) | Done |
| Light curve (per exposure, same-λ rule) | Done |
| Proof panel (motion vs Gaia, data releases) | Done |
| Spot list + honest JPL check | Done |
| About page (cleaning, limits, credits) | Done |
| Spectrum across detectors (Eps Ind B D1–D6) | Done |
| Live IRSA when band missing (API) | Done (commit b74225e) |
| Coverage timeline (when SPHEREx looked, per detector) | Done 1 Nov (Day 6) |
| GIF download + links to the original IRSA files | Done 1 Nov (Day 6) |
| Nepali toggle (fixed page text; data notes stay English) | Done 1 Nov (Day 6); removed 7 Nov (not needed: English only) |
| Planet X explainer (About, geometry only) | Done 1 Nov (Day 6) |
| JPL offset sign | Verified 1 Nov (Ceres, `scripts/check_jpl_offsets.py`) |
| Spectra: Eps Ind B D1–D6, RW Aur D1–D6, WISE 0855 D2/D5/D6 | Done 1 Nov |
| Revisit cache (switching back to a target downloads nothing again) | Done (checked in the browser: 0 requests on revisit) |
| C4-style tests (scripts + pytest) | 128 backend + 59 frontend pass; AAVSO not checked |
| 10 research papers (PDFs in `researchpdf/`) | Done 6 Nov |
| Research gaps mapped to the tool (`RESEARCH_GAPS.md`) | Done 6 Nov: main gap, G1 and G2 covered; G3–G5 supporting |
| Automatic "is it real?" check per spot (single-exposure count, moving-star pair) | Not built; manual "To confirm" text only (`RESEARCH_GAPS.md` §5, H1) |
| "Why this tool exists" block citing the papers (About) | Not built; no paper is cited on the site yet (H2) |

---

## What global nomination still needs (not the same as “more code”)

Global judges score **Impact, Creativity, Validity, Relevance, Presentation** from the **project page, repo, live link, and 30-second video** — not from this private practice repo.

| Item | Status | Who / when |
|------|--------|------------|
| **30-second video** (Pluto → Barnard → WISE → URL) | Not made | Kripas, before or during event |
| **Public live URL** on submission form | Skipped in practice | Deploy hour 14–22 of Part E (real repo) |
| **Phone layout check** | Checked at 390 px in an emulated phone 1 Nov: no sideways overflow, charts scroll, links tappable | Test on a real phone after deploy |
| **Project summary + NASA data section** on submission form | Draft from pitch in plan | Hour 40–46, real event |
| **Friend cross-checks** (review guide Part C) | Pending | [Friend's name] |
| **Friend checks the 3 main gaps against the PDFs** (review guide Part D, questions 13–15) | Pending | [Friend's name], before Fri 13 Nov |
| **Research line in the pitch** (main gap + G1 + G2, `HACKATHON_PLAN` Part F) | Written 6 Nov | Kripas practises it |
| **User test** (5–10 people, Barnard's Star, real counts, time, one quote) | Not done | Both, hours 34–46 of the event (try once at the rehearsal) |
| **AAVSO** for RW Aur / R Dra (Validity beat) | Blocked 31 Oct | Friend retry or hand download |
| **IRSA Spectrophotometry Tool** cross-check (About) | Not done | Friend, Thu 5 plan |
| **48 h rehearsal** from **empty repo** (Sat 7–8 Nov) | Not done | Both — critical for speed |
| **Mock judging** (Sun 8 evening) | Not done | Both |
| **Speed drill** empty folder (12 Nov) | Not done | Kripas |
| **Read Resources tab** (13 Nov evening) | Not yet | Both |
| **Nepal lead: written OK to practise?** | Unknown | Kripas |
| **Register team** on spaceappschallenge.org | Check | Both |
| **Repo private + add lazylog00** | User todo | Kripas |

Optional extras that **help Creativity** but are not in practice yet: epoch add/subtract legend (WiseView-style). (Coverage timeline, GIF download: done Day 6; the Nepali toggle was removed 7 Nov. R Dra is saturated in D2, so the multi-detector spectrum uses RW Aur instead.)

---

## Remaining *practice* work (before 14 Nov — improves rehearsal, not submission)

1. ~~**Eps Ind B D6**~~ — done 1 Nov (frames + spectrum D1–D6).
2. **Docs** — `DAY5_FINDINGS.md` §6–7 updated; review guide **84 / 43**, C9; learning note 13 spectrum step; README + HACKATHON_PLAN status.
3. **Screenshot** — `notes/screenshots/day5_spectrum_eps.png` (done 1 Nov; use a current `uvicorn` so `/api/spectrum` exists).
4. **Optional:** deploy practice once to get a **demo URL** for the video storyboard (still not the submission repo).
5. **Research-based additions (Mon 9 – Wed 11 Nov, after the rehearsal):** H1 automatic spot checks and H2 "Why this tool exists" block first, then H3 blend badge, H4 change-colour panel, H5 report download. Details, data and "done when" for each: `RESEARCH_GAPS.md` §5–6.

---

## What to do on 14–15 Nov (real submission path)

Follow **HACKATHON_PLAN Part E** (48 h): empty repo → Level 1 by hour 22 (C4 tests) → Level 2 → Level 3 only if Level 2 passes → **no new features after hour 40** → video + submit by hour 46.

Level 3 order (`HACKATHON_PLAN` C5): spectrum + "Why this tool exists" block → single-exposure count per spot → moving-star pair → the rest only if time is left.

**Global nomination** comes from: a **working public link**, a **clear honest story**, **proof numbers on screen**, and a **strong 30-second video** — plus local judges picking you as Nepal’s nominee.

---

## One honest sentence for the pitch

“We built a blink tool for SPHEREx that shows real IRSA data, checks motion against Gaia, and never claims a discovery — practice proved the pipeline; the hackathon submission will be a fresh build with the same honesty.”

With the research (from `HACKATHON_PLAN` Part F): “NASA's SPHEREx paper calls the survey a reference every six months for time-domain science, but none of IRSA's SPHEREx tools compares visits. Ours does, and it checks each spot for the artifacts that the Backyard Worlds team called the main challenge.” (Say the second half only once the automatic check works.)
