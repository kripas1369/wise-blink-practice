# [Friend's name]'s personal plan (validator and researcher)

GitHub: `lazylog00`. Branch: `friend-backend` (for review notes only).

**Your job (from 31 Oct): check, research, suggest.** Kripas builds everything (website and data code, Day 1 to Day 4 and later). You:
1. **Validate:** check that every number and picture we show is true, using NASA's own tools and the files themselves.
2. **Research:** answer the open science questions and read the official SPHEREx documents for things we may have wrong.
3. **Find problems:** anything wrong, unclear, overclaimed or fragile in the website, the data code or the docs.
4. **Suggest new things:** features or checks that would make the tool more useful or more convincing to the judges.

**Your first stop: [FRIEND_REVIEW_GUIDE.md](FRIEND_REVIEW_GUIDE.md)**: what we built in simple words, how to check each claim, and the research list.

**Partner:** Kripas Khatiwada (builds everything). See [KRIPAS_PLAN.md](KRIPAS_PLAN.md).

**Your rule (you set it):** no fake, no hype, only ground truth. If something cannot be proven from the data or an official source, it must be marked "not checked yet" or removed.

**History:** on 31 Oct morning you were planned as the data lead, with step-by-step build guides ([FRIEND_DAY1_STEPS.md](FRIEND_DAY1_STEPS.md), [FRIEND_DAY2_STEPS.md](FRIEND_DAY2_STEPS.md)). Those are now **reference only**: their commands are still a good way to check the Day 1 and Day 2 numbers yourself.

---

## How you report
- **Problems and research answers:** add them to [`notes/REVIEW_NOTES.md`](../../notes/REVIEW_NOTES.md) (template inside) on your branch `friend-backend`, then open a pull request to `main`, or simply send them to Kripas.
- Each entry: what you checked, how (link, command, page of a document), what you found, and how sure you are.
- Kripas fixes the code and the website; you re-check the fix.

## Phase 1: practice week (Sat 31 Oct – Fri 6 Nov)
| Day | Kripas builds | You check and research |
|---|---|---|
| Sat 31 Oct – Sun 1 Nov (Day 1 + 2, built early) | Search, Aladin sky view, flipbook, data pipeline (clean, align, add-up) | The review guide: Parts A–C; the research questions (Part D) |
| Mon 2 Nov (Day 3) | Gaia markers, synced Before / After / Difference view, the API | Gaia positions and motions of the 5 targets; is the Difference view honest (residuals explained by motion, wavelength or alignment first)? |
| Tue 3 Nov (Day 4) | Light curve, deploy, tests on the 5 targets | Brightness numbers vs IRSA's Spectrophotometry Tool; test the public link on your phone |
| Wed 4 – Thu 5 Nov | Level 3 features (proof panel, spot evidence panel with known-object check, About page) | Read the Explanatory Supplement (2.2, 3.2.5, 3.2.9, 3.4.3); finish `FACTS.md` checks |
| Fri 6 Nov | Rest | Rest |

## Phase 2: timed rehearsal (Sat 7 – Sun 8 Nov)
Kripas builds from memory in an empty repo. You act as the **judge and tester**: every 6 hours, check the newest build against the C4 acceptance tests in [HACKATHON_PLAN.md](HACKATHON_PLAN.md), look for wrong numbers, and write the science text (limitations, references, NASA data section) for the project page.

## Phase 3 – 4: final prep and hackathon (Wed 11 – Sun 15 Nov)
- Before: re-check `FACTS.md` against the Supplement and IRSA; check IRSA and the SIMBAD mirror work from the venue.
- During: test every new build; check each number on the project page; science text; explain the science part of the pitch.

## What you watch for (the mistakes that would be "fake")
- Time from `DATE` instead of `MJD-AVG`. Masking on SOURCE, or SOURCE cancelling a bad flag.
- A brightness change claimed when the wavelength changed (SPHEREx's filter gives each exposure its own wavelength).
- A dot called "the target" when it is a background object (see WISE 0855 D2).
- A made-up value shown when something failed. A "discovery" claim.
