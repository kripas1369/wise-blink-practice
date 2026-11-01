# Hackathon readiness (Team Not42) — practice vs global nomination

**Today:** 1 Nov 2026. **Event:** 14–15 Nov 2026. **Goal:** #1 in Nepal → **global nomination**.

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
| C4-style tests (scripts + pytest) | Mostly pass; AAVSO not checked |

---

## What global nomination still needs (not the same as “more code”)

Global judges score **Impact, Creativity, Validity, Relevance, Presentation** from the **project page, repo, live link, and 30-second video** — not from this private practice repo.

| Item | Status | Who / when |
|------|--------|------------|
| **30-second video** (Pluto → Barnard → WISE → URL) | Not made | Kripas, before or during event |
| **Public live URL** on submission form | Skipped in practice | Deploy hour 14–22 of Part E (real repo) |
| **Phone layout check** | Partial CSS only | Test on real phone after deploy |
| **Project summary + NASA data section** on submission form | Draft from pitch in plan | Hour 40–46, real event |
| **Friend cross-checks** (review guide Part C) | Pending | [Friend's name] |
| **AAVSO** for RW Aur / R Dra (Validity beat) | Blocked 31 Oct | Friend retry or hand download |
| **IRSA Spectrophotometry Tool** cross-check (About) | Not done | Friend, Thu 5 plan |
| **48 h rehearsal** from **empty repo** (Sat 7–8 Nov) | Not done | Both — critical for speed |
| **Mock judging** (Sun 8 evening) | Not done | Both |
| **Speed drill** empty folder (12 Nov) | Not done | Kripas |
| **Read Resources tab** (13 Nov evening) | Not yet | Both |
| **Nepal lead: written OK to practise?** | Unknown | Kripas |
| **Register team** on spaceappschallenge.org | Check | Both |
| **Repo private + add lazylog00** | User todo | Kripas |

Optional extras that **help Creativity** but are not in practice yet: coverage timeline chart, Nepali toggle, GIF download, epoch add/subtract legend (WiseView-style), spectrum **per epoch** side-by-side for R Dra.

---

## Remaining *practice* work (before 14 Nov — improves rehearsal, not submission)

1. ~~**Eps Ind B D6**~~ — done 1 Nov (frames + spectrum D1–D6).
2. **Docs** — `DAY5_FINDINGS.md` §6–7 updated; review guide **84 / 43**, C9; learning note 13 spectrum step; README + HACKATHON_PLAN status.
3. **Screenshot** — `notes/screenshots/day5_spectrum_eps.png` (done 1 Nov; use a current `uvicorn` so `/api/spectrum` exists).
4. **Optional:** deploy practice once to get a **demo URL** for the video storyboard (still not the submission repo).

---

## What to do on 14–15 Nov (real submission path)

Follow **HACKATHON_PLAN Part E** (48 h): empty repo → Level 1 by hour 22 (C4 tests) → Level 2 → Level 3 only if Level 2 passes → **no new features after hour 40** → video + submit by hour 46.

**Global nomination** comes from: a **working public link**, a **clear honest story**, **proof numbers on screen**, and a **strong 30-second video** — plus local judges picking you as Nepal’s nominee.

---

## One honest sentence for the pitch

“We built a blink tool for SPHEREx that shows real IRSA data, checks motion against Gaia, and never claims a discovery — practice proved the pipeline; the hackathon submission will be a fresh build with the same honesty.”
