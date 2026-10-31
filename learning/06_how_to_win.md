# 06. How to win: what judges score and what we should add

## How judging works
- **Local judges (Nepal)** score every project and pick up to 3 local winners. One or two
  projects become **Global Nominees**.
- **Global judges (NASA and partner experts)** review the nominees from the project page:
  the **30-second video (or ≤7 slides)**, the summary, the public repo and the live link. They
  usually do not watch your live pitch, so **the video and project page must stand alone**.
- **Criteria** (the same at both levels), from the official judging guide:

| Criterion | The judge's question | Our answer (what to show) |
|---|---|---|
| **Impact** | Big problem? Helps many people? | SPHEREx has >1 billion objects; there is no public time-view. Anyone with a phone can now look. Two students from Nepal learned it in a month. |
| **Creativity** | New, or a small improvement? | The first blink tool for SPHEREx; time **and** 102 colours (spectrum per epoch); proof layers (Gaia, sigma differences). |
| **Validity** | Scientifically right? Does it work? | The 5 official targets pass, with numbers: Barnard's Star motion matches Gaia; WISE 0855 only in D5–D6; R Dra matches AAVSO; official flags; MJD-AVG; limits stated. |
| **Relevance** | Answers the challenge? Complete? Easy to use? | Every required item, plus most of the 8 optional items (table below). Works on a phone. |
| **Presentation** | Clear story? | Tombaugh's blink (1930) → SPHEREx today → live demo in the first 30 seconds → proof → honest limits. |

Global award categories worth aiming at: **Best Use of Data** ("makes space data accessible"),
**Best Use of Science**, and **Local Impact**.

## The challenge's optional items (each earns extra points)

| # | Optional item | Plan | Level |
|---|---|---|---|
| 1 | Easy to update with new releases | Live TAP queries across QR2 + QR3 (+ future); "data as of" date shown; collections in one config line | 1 |
| 2 | Creative use of the 102 bands; extra kudos for spectra on the fly | Detector buttons D1–D6; spectrum on click; **spectrum per epoch** comparison | 2–3 |
| 3 | Add or subtract images from different times | Epoch picker: choose epochs to add (+) or subtract (−), like WiseView's epoch legend | 2 |
| 4 | User-chosen field of view | FOV slider 1–15′ | 1 |
| 5 | Gaia and WISE overlays | Gaia markers moved per epoch; Aladin with WISE/2MASS backgrounds | 2 |
| 6 | Coordinates in the URL (embeddable) | `?ra=&dec=&fov=&det=`; share button | 1 |
| 7 | Show contamination flags | Flag overlay in red + "% flagged" + plain-English names | 1 |
| 8 | Use Astropy and Aladin | Backend astropy; frontend Aladin Lite v3 | 1 |

## What to add so judges score us high (recommendations)
These come from the gaps in [05](05_nasa_tools_review.md). Ordered by value for effort.

**Must have (they make the project credible):**
1. **Proof panel per target:** a small table on the page: "expected motion (Gaia) vs measured
   motion (SPHEREx)", "% flagged pixels", "number of images and epochs", "data release and date".
   Judges trust numbers they can see.
2. **North-up aligned frames, with an alignment check** (background stars stay put). Without it
   the flipbook is useless; with it, we fix a real problem in the official tools.
3. **Honest empty and error states:** "No SPHEREx images here yet", "SIMBAD is down, type
   RA/Dec", "IRSA is slow, showing cached data from <date>". Never a fake value.
4. **"Data as of" line** showing the newest release date found (we saw 28 Oct 2026). Proves
   "easy to update".
5. **Limitations box:** 6.15″ pixels, about 1.5 years of data, moving objects under ~1 pixel are
   not detectable, wavelength changes across each detector, not a Planet X detector.

**Strong extras (win points other teams will not have):**
6. **Epoch picker (+/−):** add or subtract any epochs; directly answers optional item 3.
7. **Spectrum per epoch:** for R Dra, two spectra on one chart (two dates). Time + colour
   together is unique to SPHEREx, and it is the "spectra on the fly" kudos.
8. **Coverage timeline:** a small bar chart of when SPHEREx looked at this spot, per detector.
   Instantly shows users why there are N frames and where the gaps are.
9. **Download for teachers:** the flipbook as a GIF, and links to the original files at IRSA
   (scientists can continue in the official tools: we complement them, we do not replace them).
10. **Cross-check with IRSA's Spectrophotometry Tool** for one target, written in the About
    page: "our brightness agrees with IRSA's official tool within X%".

**Local and human touch (cheap, memorable):**
11. **Nepali language toggle** for the main screen text (Local Impact; Global Connection).
12. **Phone-friendly** layout (the official Data Explorer says it does not work on iPhone).
13. **Keyboard controls** (space = play, arrows = step) and colour-blind-safe colours.
14. **"What am I looking at?"** one-line explanation for each target (already in `targets.py`).

**Do not do:** claim discoveries, say "we found Planet X", show any number without a source,
add features after hour 40.

## The 30-second video (most important single item for global judging)
1. 0–5 s: Pluto discovery plates blinking (1930).
2. 5–10 s: the SPHEREx all-sky map.
3. 10–20 s: type "Barnard's Star" → it walks onto its Gaia markers; the proof numbers appear.
4. 20–26 s: WISE 0855 invisible in D1, appears in D6 → its spectrum.
5. 26–30 s: tool name + URL.

## Hard questions to practise
- **"How do you know the motion is real?"** Frames aligned on background stars; the shift
  matches Gaia's proper motion (numbers); difference image shows ±N sigma; flagged pixels removed.
- **"Why not use IRSA's Data Explorer?"** It is for experts and has no time view; frames are not
  north-up; jobs queue. We are the public front door and link back to IRSA.
- **"Why does WISE 0855 only show at 4–5 µm?"** It is so cold that it gives off almost all its
  light at long infrared wavelengths.
- **"Brightness changes, or wavelength changes?"** SPHEREx's filter changes wavelength across
  the detector, so we record the wavelength of each measurement and compare like with like.
- **"Can it find Planet X?"** It shows how such an object would move between visits. A real
  search needs fainter limits and more data; our tool makes it easy to inspect candidates.
- **"What happens with new data?"** Live queries; the new release appears automatically.
- **"What would you do next?"** Many more epochs as SPHEREx continues; candidate voting like
  Backyard Worlds; automatic motion detection.

## Submission must-haves (Part G in the plan)
Title, summary, 30-second video at a public link (no login), public repo (the **new** repo made
during the event), live link, NASA data used (SPHEREx at IRSA), other data (ESA Gaia, CDS
SIMBAD/Aladin, AAVSO), references, honest AI-tools note, all team members on the page.
Check whether the Nepal event has an earlier deadline than 15 Nov 23:59.
