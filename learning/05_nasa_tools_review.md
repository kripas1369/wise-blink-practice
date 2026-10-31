# 05. NASA/IRSA tools for SPHEREx: what exists, the problems, and our gap

Checked on 31 Oct 2026 from the official IRSA pages (links below) and from our own tests.
Judges will ask "Why not just use IRSA's tools?" This page is the answer.

## The tools that exist

| Tool | What it does | Who it is for |
|---|---|---|
| [SPHEREx Data Explorer](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html) | Web GUI (Firefly): Spectral Image Search, cutouts (scissors icon), Job Monitor | scientists |
| [Spectrophotometry Tool](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) | Forced PSF photometry (Tractor) at a known position → a low-resolution spectrum | scientists |
| [Mosaic Tool](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html) | Combines many images into one 102-plane cube | scientists |
| [Cutout service](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html) | Small pieces of the big image files | programmers |
| [Source Discovery Tool](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/) | Python notebook: image subtraction, SExtractor, spectra | Python users |
| Moving Object Search Tool (MOST), listed on the [IRSA SPHEREx page](https://irsa.ipac.caltech.edu/Missions/spherex.html) | Finds SPHEREx images along a **solar-system** object's orbit | scientists |
| [Tutorial notebooks](https://caltech-ipac.github.io/irsa-tutorials/spherex/) | Python examples (search, cutouts, PSF) | Python users |
| [WiseView](http://byw.tools/wiseview) (not NASA SPHEREx; Backyard Worlds) | Blinks **WISE** images by RA/Dec. Hundreds of brown dwarfs found by volunteers with it | volunteers |

## Problems we found (with sources)

### 1. No "watch it change over time" view for SPHEREx
- The Data Explorer shows a **table of images** and one image at a time. There is no flipbook,
  no epochs, and no "play".
- The Mosaic Tool **combines all dates into one picture**, which erases exactly what we want to
  see (motion and variability). Its first version also leaves out the deep-field frames, and the
  docs warn about gaps and stripe artefacts.
- MOST only works for solar-system objects with a known orbit. It cannot show a nearby star or a
  brown dwarf moving, and it cannot find something whose orbit is unknown.
- WiseView, the blink tool volunteers love, only works with WISE, not SPHEREx (no 102 colours).

### 2. Raw images cannot be blinked directly
IRSA's own cutout page: cutout axes follow the parent image, which is **not north-up**, and the
orientation depends on how the spacecraft was pointing; the distortion corrections are "often not
supported by FITS viewers". So two cutouts of the same star are turned differently. Someone has to
reproject them onto one grid before anything can be compared. The official tools leave that to
the user.

### 3. Built for experts
Tabs, panes, HDUs, MOCs, HiPS, Sérsic parameters, job queues. The help pages are long and good,
but a student or an amateur astronomer will not get from "I want to see Barnard's Star move" to an
answer. The notebooks and the Source Discovery Tool need Python, conda and SExtractor installed.

### 4. Slow, queued jobs
- The Spectrophotometry and Mosaic tools run as **jobs**: at most 2 at once, others wait in a
  queue. A typical ~200-frame mosaic takes ~2 minutes; fields near the ecliptic poles take much
  longer.
- The [known-bugs page](https://irsa.ipac.caltech.edu/docs/known_issues/spherexbugslist.html)
  (Sept 2026) lists: **jobs may be lost** (also during the regular Tuesday maintenance every
  other week), email notification sometimes fails, IRSA Workspace does not always work, and
  "not on the iPhone".

### 5. Fragile name lookup
The IRSA cutout tool page showed "10/28/2026: Some object lookup services are unavailable". We saw
the same thing: the main SIMBAD server (CDS) did not answer on 29 and 31 Oct; the Harvard mirror
did. A tool that depends on one name server breaks.

### 6. Fast-moving stars and old catalogue positions
Catalogue positions are for one date (SIMBAD: 2000; Gaia: 2016). Barnard's Star has moved ~270″
since 2000, about 44 SPHEREx pixels. If a tool searches or cuts out at the old position with a
small field, the star is off-centre or outside. (We did not test whether the Data Explorer
corrects for this, so we do not claim it fails. We only say our tool **does** correct for it.)

### 7. Heavy downloads for small pictures
Our test: a 0.05° cutout (29×29 pixels) is still **~5 MB**, because each cutout carries the full
PSF cube (121×101×101). Fine for one image; a flipbook of hundreds of frames needs caching and
server-side processing. Browsers should get small PNGs, not FITS files.

### 8. Two data releases, more coming
QR2 and QR3 are both live, with new data added weekly (the newest image we saw was released on
28 Oct 2026). The SIA2 interface lags TAP by about a day. Tools that hard-code one release go
stale; users do not know how fresh the data is.

## The gap our tool fills

| Problem | What our tool does |
|---|---|
| No time view | Flipbook of epochs per detector: play, step, blink two dates |
| Not north-up | Reprojects every frame onto one north-up grid and checks the alignment on background stars |
| Expert-only | One search box + 5 target buttons + plain-English explanation of what to look for |
| Slow jobs | Pre-cached targets; small PNG frames; answers in seconds for cached spots |
| Name lookup fragile | Two SIMBAD servers with fallback; fixed positions for the 5 targets |
| Old positions | Moves the position with proper motion before searching |
| Is it real? | Gaia "should be here" markers, difference images in sigma, flagged pixels shown |
| Data freshness | Live queries to all releases; "data as of" date shown |

**One-sentence answer for the judges:** "IRSA's tools are excellent for scientists who already
know what they want. We built the missing front door: anyone types a name, sees the sky change
over time, and gets proof it is real, in seconds, on a phone."
