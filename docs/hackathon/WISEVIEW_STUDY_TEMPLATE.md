# WiseView study (P2-1, Sat 22:45 to 00:45)

NASA's Resources tab links WiseView as "a similar tool made for viewing data from an earlier NASA mission called WISE. It's been used by the public to make hundreds of discoveries. Feel free to use it as a model or as inspiration."

**Goal:** learn what really helps people spot moving objects, then copy what works into our SPHEREx tool. No coding in this block. Write down only what you see on screen or read in WiseView's own pages or code, never from memory.

**Output:** fill in this file, then save it as `docs/WISEVIEW_STUDY.md` in the new repo.

---

## 1. Basics (Friend)
- WiseView address used:
- Date and time of the study:
- Is the source code public? Where? (link)
- Is there documentation or a paper? (link)
- What data does it show (which WISE products, how many epochs, co-adds or single frames)?
- How does it get the data (from the browser directly, through a server, pre-built tiles)?

## 2. Every control (Friend)
One row per control you can see.

| Control | What it does (observed) | Default | Helps spot movers? (yes / no / sometimes) | Notes |
|---|---|---|---|---|
| | | | | |

Make sure you check: position input (formats accepted), field of view or size, zoom, blink or animation speed, epochs (all, first/last, choosing), bands (W1, W2, colour), contrast and stretch (min/max, linear or other), difference mode, scan direction or parallax option, overlays (catalogues, known objects), links to other services, the URL (which settings go into it), and keyboard shortcuts.

## 3. Timed test on 3 movers (Friend)
For each target, start from an empty WiseView page and time how long it takes until you can point at the moving object.

| Target | Settings that worked best | Time to spot it | What made it obvious | What got in the way |
|---|---|---|---|---|
| WISE 0855 (08h55m10.831s −07d14m42.53s) | | | | |
| Epsilon Indi B | | | | |
| Barnard's Star | | | | |

## 4. User experience (Kripas)
- The screen flow from opening the page to seeing motion (steps and clicks):
- How motion is made obvious (blink, colour, difference, markers):
- What a first-time user would not understand:
- Mouse and keyboard use:
- Speed: time from entering a position to the first moving image:
- Embedding and sharing (URL):

## 5. The same 3 targets in our Phase 1 tool (Kripas)

| Target | Our best detector and mode | Time to spot it | Better than WiseView? | Worse because |
|---|---|---|---|---|
| WISE 0855 | | | | |
| Epsilon Indi B | | | | |
| Barnard's Star | | | | |

## 6. Decisions (both)

| WiseView feature | Adopt / Adapt / Skip | Why | How it maps to SPHEREx | Block that builds it |
|---|---|---|---|---|
| | | | | |

SPHEREx differences to keep in mind when deciding:
- Each SPHEREx exposure sees a different wavelength (the LVF filter): blinking two visits can show colour, not only motion.
- About 2–4 visits per position so far (every 6 months), against WISE's many epochs.
- 6.15″ pixels (WISE is about 2.75″).
- 6 detectors with 102 bands, where WISE has 2 to 4 broad bands.

## 7. Which 102-band idea comes first in Phase 2 (both)
Rank them, giving the reason from the study:
1. All exposures per detector with the measured signal-to-noise gain, Six Eyes flipbook, colour flipbook
2. Spectra on the fly (click any pixel)
3. 102-band contact sheet
4. Spectral Lens with methane and other molecule presets
5. Wavelength movie
6. "What moved?" list
