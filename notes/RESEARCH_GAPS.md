# Research gaps and what SPHEREx Blink should add

**Written:** 6 Nov 2026. **Sources:** the 10 papers in `researchpdf/` (limitations, discussion and future-work sections read in full).
**Rules that still apply:** no fake values; a spot is never called a new object; this practice repo is not the submission (rebuild from an empty repo on 14 Nov).

---

## 1. The main gap

**SPHEREx is promoted for time-domain science, but nothing official lets you compare its visits.**

- `01_Bock2026` §2.4: "SPHEREx also provides a valuable dataset for the upcoming generation of time-domain studies. In the all-sky survey, SPHEREx measurements can serve as a reference every 6 months." §3.4.6: the four surveys exist partly to "identify time-variable sources".
- `01_Bock2026` Table 5 (IRSA's SPHEREx tools): Spectrophotometry (Aug 2025), Spectral Image Cutout (Oct 2025), Source Discovery (Oct 2025), Custom Mosaic (Feb 2026), Spectral Cube Cutout (Nov 2026). None compares visits.
- `01_Bock2026` Table 4: the legacy catalogs of brown dwarfs and solar-system objects arrive in **May 2028**.

**What we already do about it:** flipbook, blink, before/after/difference in σ, coverage timeline, per-visit light curves and spectra, for any position.

Before the pitch, check IRSA's current tool list once more (the paper's table is from Dec 2025).

---

## 2. Supporting gaps from the papers

| # | Gap (what the paper says) | Paper | What we have today | Fit |
|---|---|---|---|---|
| G1 | Telling movers from artifacts is "the primary challenge for users" (partly subtracted stars, cosmic rays, ghosts, latents); help was a tutorial and a "Field Guide". SPHEREx flags 1.1% of pixels as transients; faint satellite streaks "near the noise level" are still being worked on. | `02_Kuchner2017` §2; `01_Bock2026` §5 | Red flagged pixels, "possible artifact" labels, JPL known-object check. The "confirm" list only tells the user what to check by hand. | Strong |
| G2 | Motion and confirmation came from different telescopes: IRTF spectrum (Backyard Worlds); Gemini + Spitzer (WISE 0855); visual check of all epochs per candidate (Luhman). Luhman searched "based on parallactic motion instead of colors" so odd colours would not be missed. | `02_Kuchner2017` §4; `08_Luhman2014` §2; `07_Luhman2014` §3 | Flipbook and spectrum of the same target from the same SPHEREx data. | Strong |
| G3 | ~6″ beams blend sources: WISE 0855 is "dominated by a moving object in W2 and two stationary objects in W1"; RW Aur's WISE beam holds both A and B. | `08_Luhman2014` §2.3; `10_Koutoulaki2019` §3.4 | Gaia overlay; light-curve warning for Gaia stars inside the aperture (up to 3 mag fainter). WISE 0855: Gaia DR3 has no match (`target_match: null`); motion from SIMBAD / Kirkpatrick 2021 (measured 0.58 ± 0.12 px vs 0.72 px predicted); nearby Gaia star G 16.31 "may add some light". | Medium |
| G4 | RW Aur: "two epochs" only; "the WISE and X-Shooter observations are not simultaneous"; the cause of the dimming "is not clear" (dusty wind, puffed-up inner rim, or tidal disturbance by RW Aur B). | `10_Koutoulaki2019` §2, §3.4, §5 | RW Aur D1–D6 per visit (SPHEREx takes 1–2 weeks for a full spectrum, `01_Bock2026` §2.4). Our result: 4–5 µm dropped Mar → Sep 2026 (D5 median 0.633 from 3 clean pairs, D6 0.770 from 5). In the 2014–16 dimming RW Aur got *brighter* at 4.6 µm (Bozhinova 2016, cited in Koutoulaki §3.4). | Medium; possible science result |
| G5 | Planet Nine: the Galactic plane "remains scarcely explored by solar system surveys" and the aphelion is near it; Rubin's plan "does not extend as far north as the full predicted path"; 3–5 µm limits are "extremely model-dependent"; a methane-poor Planet Nine could have "order of magnitude more emission in the 3-4 µm range". The WISE method "should be readily applicable to the WISE W2 channel". | `05_Batygin2019` §6.1–6.2; `06_Brown_Batygin2021` §5, §7; `03_Meisner2018` Conclusion | Planet X explainer (geometry, Neptune-twin brightness); any position can be opened. | Teaching only: SPHEREx is too shallow for the predicted Planet Nine |

Papers `04_Batygin_Brown2016` and `09_GaiaCollab2023` are good references but add no separate gap.

---

## 3. What to add (things that do not exist in our system yet)

Each item says which gap it answers, what it shows, where the data comes from, and what "done" means. Ordered by value for effort.

### F1. Change-colour panel ("how did the spectrum change?") — gap G4 · **highest value**
- **Shows:** for a target with two visits, the ratio visit B / visit A against wavelength, one point per same-wavelength clean pair (the light curve's rule: within half a bandwidth, both ≥ 5σ, no flagged pixel), one colour per detector.
- **How to read it (text on the panel, with sources):** flat ratio below 1 = grey dimming by large grains (RW Aur 2014–16, `10_Koutoulaki2019` §3.3); ratio falling toward short wavelengths = ordinary dust reddening; ratio above 1 at 3–5 µm while short wavelengths dim = extra hot dust (Koutoulaki §3.4, Bozhinova 2016). Our Mar → Sep 2026 RW Aur result fits none of these yet, because everything dropped and 4–5 µm dropped most, so the panel says "not explained here".
- **Data:** already in `lightcurve.json` / `spectrum.json` (pairs and wavelengths). No new download.
- **Done when:** RW Aur shows the D5 0.633 and D6 0.770 medians from the notes; a target with no clean pairs says so; tests check the ratios against `DAY6_FINDINGS.md`.

### F2. Automatic "is it real?" checks per spot — gap G1
Replace the hand-check list with results:
- **Seen in single exposures:** for each spot, in how many single exposures of that visit the pixel is above 3σ ("6 of 8 exposures"). One exposure only → likely cosmic ray or streak.
- **Seen in another detector:** same visit, same sky position, other detector's difference image (when frames exist).
- **Moving-star pair:** a fainter spot and a brighter spot within 3 px whose offset matches the Gaia motion → "a moving star (Gaia DR3 …)"; a pair with no Gaia star → "a pair worth checking: could be a star too faint or red for Gaia, or an artifact".
- **Data:** the single-exposure cutouts the light curve already reads; existing diffs; Gaia file.
- **Done when:** Barnard's Star's spots show the pair matched to Gaia; RW Aur's 1-px spots near flagged pixels show their exposure counts; no spot is ever labelled a discovery.

### F3. Field guide page from our own data — gap G1
- **Shows:** real SPHEREx examples only, each with its link: a moving star (Barnard dipole), a variable star (RW Aur), a saturated core with no value, a bright-star halo, a 1-pixel hit, a satellite streak if we find one in our frames (if not, say we have none yet).
- **Done when:** each example has a working "open this in the flipbook" link; no drawn or simulated examples.

### F4. Target blend and "not in Gaia" badge on the proof panel — gap G3
- **Shows:** Gaia stars within 2 SPHEREx pixels (12.4″) of the target with their G magnitudes; known close companions from SIMBAD (e.g. RW Aur B); a "Not in Gaia DR3" badge with the reason (too faint or too red in visible light) and the motion source used instead.
- **Data:** existing Gaia file; one SIMBAD query.
- **Done when:** WISE 0855 shows "Not in Gaia DR3" and the G 16.31 neighbour; RW Aur names RW Aur B and says SPHEREx cannot separate them.

### F5. Report this spot (export) — gaps G1, G2, main gap
- **Shows:** a button that downloads a plain report (JSON + readable text): position, visits, detectors, σ, the F2 checks, Gaia and JPL results, IRSA original-file links, and the line "This is a place to look, not a discovery."
- **No server storage.** Like Backyard Worlds' web form, but the checks are filled in.
- **Done when:** the file opens, every number matches the page, and the disclaimer is in it.

### F6. Optical state at SPHEREx dates (AAVSO, with ZTF at IRSA as fallback) — gap G4
- **Shows:** visible-light brightness near each SPHEREx visit on the RW Aur / R Dra light curve, or "no optical data in this period".
- **Risk:** AAVSO was unreachable on 31 Oct; ZTF public releases lag months behind, so they may not reach Sep 2026. Check coverage first; if neither covers 2026, show the honest message and skip.
- **Done when:** the RW Aur 4–5 µm drop can be called "during a dim state", "after a dim state" or "optical state unknown".

### F7. Planet Nine sky overlay on the sky map — gap G5 (teaching)
- **Shows:** the Galactic plane (±20°, as drawn in `06_Brown_Batygin2021` Fig. 9) and the swath where Planet Nine most likely is: "±12° in declination from an orbit with an inclination of 16° and an ascending node of 97°" (§5). Clicking inside opens SPHEREx frames there.
- **Text:** "SPHEREx is too shallow to see Planet Nine as predicted; this shows where searches are thin, not where we found anything." Check the reference frame of the elements in §4–5 before drawing.
- **Done when:** the swath matches Fig. 9 by eye; no brightness or detection claim.

### F8. Within-visit motion check (stretch) — gaps G2, G5
- Between visits a solar-system object leaves our 3′ square (the Planet X explainer: at 500 AU about 1 px a day). So the only useful test is inside one visit: fit the spot's position in each single exposure and report the shift per day, and what distance that shift would mean using the explainer's geometry.
- **Done when:** a known asteroid in one of our fields gives a distance that matches JPL. Build only if F1–F5 are done.

---

## 4. Gaps we cannot fill (say so if asked)
- Detecting Planet Nine: SPHEREx's 5σ depth is 19.5–19.9 AB below 3.8 µm after all four surveys (`01_Bock2026` abstract), and a single visit is shallower.
- Separating RW Aur A from B: 6.2″ pixels.
- Detailed atmosphere of WISE 0855: JWST spectra exist now; SPHEREx adds repeated low-resolution 4–5 µm points, not a better spectrum.

---

## 5. Plan

### Practice repo (after the rehearsal; nothing on Sat 7 – Sun 8 Nov, which is the empty-repo rehearsal)
| Day | Work | Owner |
|---|---|---|
| Mon 9 Nov | F1 change-colour panel (backend ratios + panel + tests). F6 coverage check only (does AAVSO or ZTF reach 2026?) | Kripas (F1), friend (F6 check) |
| Tue 10 Nov | F2 single-exposure count + moving-star pair; F4 blend / "not in Gaia" badge | Kripas |
| Wed 11 Nov | F5 report export; F3 field guide from our frames; F6 only if the data exists | Kripas, friend reviews every number |
| Thu 12 Nov | Speed drill as planned. F7 overlay only if time is left | Kripas |
| Fri 13 Nov | Read the Resources tab; update the pitch with the main gap and G1–G4 | Both |

### Hackathon build (14–15 Nov, fresh repo)
- Follow `HACKATHON_PLAN` Part E unchanged: Level 1 by hour 22, Level 2 by hour 34.
- Hours 34–40, in this order, only if Level 2 passes: **F1**, then **F4**, then **F5**, then the F2 exposure count. Nothing new after hour 40.
- F3, F6, F7 and F8 stay out of the hackathon unless everything above is done and tested.

### Pitch line
"SPHEREx's own mission paper calls its maps a reference every 6 months for time-domain science, yet none of IRSA's SPHEREx tools compares visits, and the official catalogs of moving objects come in 2028. SPHEREx Blink lets anyone compare visits today, checks every change against flags, Gaia and JPL, and shows the spectrum from the same data, so people see what really moved or changed instead of mistaking artifacts for discoveries."

### Do not claim
- That SPHEREx can find Planet Nine.
- That the RW Aur drop is new or explained, until F6 (or the literature) says what RW Aur was doing in visible light in 2026.
- That any spot is a new object.
