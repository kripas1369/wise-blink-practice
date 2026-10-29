# NASA Space Apps 2026: "Planet X and SPHEREx" team plan

**Team Not42:** Kripas Khatiwada (data and science lead) and [Friend's name] (web and presentation lead, GitHub `lazylog00`).

**Working name:** "Blink: SPHEREx for Everyone" (or "SPHEREx TimeLens"; decide together).

**Hackathon:** 14–15 Nov 2026. Submission closes Sun 15 Nov, 23:59 local time.

**Personal plans:** [KRIPAS_PLAN.md](KRIPAS_PLAN.md) and [FRIEND_PLAN.md](FRIEND_PLAN.md) (day by day, hour by hour).

---

## PART A: Where we are today (who built what)

### A1. What Kripas built (repo `nasa`, prototype "SPHEREx TimeLens")
- **Data access:** `processing/irsa_client.py` (IRSA SIA search, picks multi-epoch images), `processing/download.py` (cutout or S3/IRSA download with retries and sha256), `scripts/query_region.py`, `scripts/download_region.py`.
- **Image processing:**
  - `processing/io_fits.py` (loads SPHEREx FITS);
  - `processing/register.py` (aligns frames onto one sky grid with `reproject`);
  - `processing/difference.py` (epoch B − A, candidate spots with a 5-sigma threshold);
  - `processing/tracking.py` (follows candidates across 3 epochs);
  - `scripts/register_and_diff.py` and `scripts/build_demo_bundle.py` (PNG and JSON demo bundle).
- **Web demo:** Django + DRF backend (SkyRegion, Observation, Candidate, CandidateDetection, ProcessingJob) and React + TypeScript + Vite + Three.js frontend (demo mode, 3D time-stack view).
- **Data on disk:** 4 SPHEREx Level-2 files (detector D1) at RA 304.69°, Dec +42.44°, epochs MJD 60794 / 60831 / 60986 / 61201.
- **Knowledge and docs:**
  - `PROJECT_PLAN.md` (21-step research plan) and `CONVERSATION_NOTES.md`;
  - `LEARN.md` plus beginner lessons `learn/01`–`07` (sky coordinates, time, light, FITS, WCS, SPHEREx, noise and flags);
  - notes from the official Explanatory Supplement v2.0 (flag lists, PSF fix, WCS-WAVE is display-only, releases).
- **Known problems** (do not repeat at the hackathon):
  - uses `DATE` (the processing date) instead of `MJD-AVG`;
  - flag mask falls back to "keep everything";
  - VARIANCE and ZODI unused;
  - "movement" threshold smaller than one pixel;
  - only detector D1 and 4 epochs.

### A2. What [Friend's name] built (repo `SPHEREXPLANETX`)
- **Feature 1, a 3D sky selector** (`web/`: Three.js globe, point and radius selection 0.10–1.75°, hover RA/Dec readout, equator and ecliptic, 88 constellation borders, sector briefing card).
- **Live NASA query** (`web/serve.py`): IRSA TAP `spherex.obscore` count of images, detectors, first and last dates, exposure time; cross-checked against an independent PyVO query.
- **Science code:** `spherex_pipeline.py` (`SpherexImage`: IMAGE/FLAGS/VARIANCE/ZODI/PSF, IMAGE − ZODI, patch extraction, WCS-WAVE wavelength; `PlanetXDetector`: two-epoch difference with variance-based SNR), `spherex_processor.py` (TAP + DataLink download), 3 notebooks.
- **Rust crate** `crates/spherex_spatial` (sky maths, HEALPix; tested, not connected).
- **Research docs:** `spherex_data_bible.md`, `chain_of_truth.md`, `learning_md.md`, the feature `JOURNEY.md`, official resources (Supplement PDF, IRSA tutorials including cutouts, PSF and Source Discovery Tool, Tractor).
- **Known problems** (do not repeat):
  - `preserve_sources` lets SOURCE cancel bad flags (55–86% of bad pixels survived in our 4 files);
  - coverage query checks image centres, not `s_region`;
  - fake fallback values (made-up dates, "705 Slices", default "Draco");
  - D3/D4 swapped in the band table;
  - constellation lookup needs B1875 coordinates.

### A3. What neither of us has done yet
- Variance-weighted add-up per epoch and detector.
- Gaia "should be here" markers.
- Light curves.
- Spectrum on click.
- A flipbook built from many real epochs.
- The 5 official test targets.

### A4. The rule that shapes everything
The official site says: "Do not begin work on your projects until the hackathon begins." So:
- **both repos stay as learning only and are never submitted**;
- **all coding before 14 Nov uses WISE/NEOWISE data, never SPHEREx**;
- on 14 Nov we start a **new, empty repo** and build everything fresh.

---

## PART B: The challenge (official, restated)
- **Required:** a public-facing web tool. The user enters **RA and Dec**, and the tool shows a **series of SPHEREx images of that patch like a little video**, making it easy to spot moving objects.
- **Test targets:**
  - Barnard's Star;
  - Epsilon Indi B (a brown-dwarf pair);
  - WISE 0855 (RA 08h55m10.831s, Dec −7d14m42.53s);
  - RW Aurigae and R Draconis (variable stars).
- **Optional, each worth extra points:**
  1. easy to update with new data releases;
  2. creative use of the 102 bands (add up per detector; **extra kudos for spectra on the fly**);
  3. add or subtract images from different times;
  4. user-chosen field of view;
  5. Gaia and WISE overlays;
  6. coordinates in the URL (embeddable);
  7. show contamination flags;
  8. use Astropy and Aladin.
- **The Resources tab opens Fri 13 Nov;** read it that evening.
- **Judging criteria:** Impact, Creativity, Validity, Relevance, Presentation.
- **Nepal:** 3 local winners, and 1 team goes to global nomination. We aim for #1.

---

## PART C: What we will build (full specification)

### C1. Screens
1. **Home**
   - Search bar: RA/Dec (degrees or `08h55m10.8s -07d14m42s`) or a name (SIMBAD lookup), plus a field-of-view slider (default 3′, range 1–15′).
   - Aladin Lite sky view (2MASS/WISE background). Clicking it fills RA/Dec.
   - 5 test-target buttons with short explanations.
   - The URL updates live: `?ra=269.45&dec=4.69&fov=3&det=1`.
2. **Viewer** (the main screen)
   - **Flipbook** in the centre: play, pause, step back and forward, speed, blink (two chosen epochs), loop.
   - **Frame label:** date (from MJD-AVG), detector, wavelength range, number of images added, % pixels flagged.
   - **Detector buttons D1–D6** (short to long wavelength), plus "all bands" mode.
   - **Toggles:** flags overlay (bad pixels in red), Gaia markers, SOURCE label layer.
   - **Modes:** single frames / add-up per epoch / difference (B − A in sigma).
   - **Side panel:** target info, image count, date range, data release, links to IRSA.
   - **Click a pixel** to see its light curve (brightness over time) and its spectrum (brightness versus wavelength).
3. **About the data:** how we clean the data (each step plus the official sources), limitations (6.15″ pixels, about 1.5 years of data, subtle motions), credits (NASA/IPAC IRSA, ESA Gaia, AAVSO, CDS Aladin).

### C2. Backend API (Python FastAPI)
- `GET /api/resolve?name=` → `{ra, dec, source:"SIMBAD"}`, or an error. Never a guess.
- `GET /api/coverage?ra&dec` → a list of `{obs_id, detector, mjd_avg, em_min, em_max, release, cutout_url}` using `CONTAINS(POINT('ICRS',ra,dec), s_region)=1`.
- `GET /api/frames?ra&dec&fov&det&mode=single|coadd` → a list of `{png_url, mjd, epoch_id, detector, wl_min, wl_max, n_images, pct_flagged}`.
- `GET /api/diff?ra&dec&fov&det&epochA&epochB` → a PNG of (B − A)/sigma, plus statistics.
- `GET /api/gaia?ra&dec&fov&mjds=` → Gaia DR3 stars propagated to each date, `{source_id, ra, dec, pm_ra, pm_dec, G}`.
- `GET /api/lightcurve?ra&dec&det` → `{mjd, flux, flux_err, flagged}` per frame.
- `GET /api/spectrum?ra&dec&epoch` → `{wavelength, flux, flux_err}` across all detectors.
- Cache: a cutout folder on disk keyed by `obs_id + ra + dec + size`. The 5 targets are pre-cached early in the hackathon.

### C3. Data pipeline (agreed, ground truth at every step)
1. **Find:** TAP `s_region` query. The count must match an independent IRSA query.
2. **Get:** IRSA cutouts only (never 70 MB full files).
3. **Time:** `MJD-AVG`. Never `DATE`.
4. **Flags, the official Mosaic Tool list** (Supplement v2.0, Section 3.4.3): TRANSIENT, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD, PHANMISS, NONLINEAR, PERSIST, CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO.
   - Read bit positions from the `MP_*` header keywords.
   - **SOURCE (bit 21) = a known star, galaxy or asteroid. It's a label only:** never mask on it, and never let it cancel a bad flag.
5. **Background:** IMAGE − ZODI.
6. **Noise:** sigma = sqrt(VARIANCE). Differences are shown in sigma.
7. **Align:** `reproject` onto one TAN grid per target. Check that Gaia stars land on the same pixel.
8. **Group:** epochs are clusters of MJD (survey visits about 6 months apart). Detectors:
   - D1: 0.75–1.09 µm
   - D2: 1.10–1.62 µm
   - D3: 1.63–2.41 µm
   - D4: 2.42–3.82 µm
   - D5: 3.83–4.41 µm
   - D6: 4.42–5.00 µm
9. **Add up:** a 1/variance-weighted mean per epoch and detector.
10. **Display:** the same stretch (percentile limits) for every frame of one target, so brightness changes are real, not display tricks.
11. **Verify:** Gaia markers for motion; AAVSO for variable stars; anything unmeasurable shows "unknown".

### C4. Acceptance tests (the definition of "done")

| Target | What must be visible | Check |
|---|---|---|
| Barnard's Star | Moves about 2.5 px (about 15″) from first to last epoch | Measured shift within about 1 px of the Gaia prediction |
| WISE 0855 | Faint or invisible in D1–D3, visible in D5–D6, small motion | Position consistent with the published proper motion (about 8″/yr) |
| Epsilon Indi B | About 1 px shift (subtle); visible near Epsilon Indi A | Gaia or catalogue motion direction agrees |
| RW Aur | Brightness changes between epochs | Light curve trend roughly consistent with AAVSO |
| R Dra | Clear brightening and fading (Mira variable, period about 245 days) | Light curve shape consistent with AAVSO |
| Any RA/Dec | No crash; "no SPHEREx data here yet" shown honestly if empty | Coverage count = IRSA count |

### C5. Feature levels
- **Level 1, a complete entry (by hour ~22):** search, name lookup, field of view, URL; cutouts and cleaning; flipbook with frame labels; detector buttons; 5 target buttons; flags toggle; deployed link.
- **Level 2, a strong contender (by hour ~34):** add-up per epoch and detector; difference in sigma; Gaia markers; light curve; Aladin with Gaia and WISE overlays.
- **Level 3, winner level (only if Level 2 is solid):** spectrum on click; measured motion compared with Gaia; latest-release querying; a "mark interesting" share link; a small Planet X explainer.
- **Not building:** a custom Three.js globe, Rust, freehand lasso, Django, a database, accounts, Planet X detection claims.

### C6. Stack
- **Backend:** Python 3.11, FastAPI, astropy, astroquery (IRSA, SIMBAD, Gaia), pyvo, reproject, numpy, Pillow.
- **Frontend:** Vite with plain JS or React, Aladin Lite v3, Chart.js or Plotly for graphs.
- **Deploy:** one small server (for example Render, Railway or a VPS) with the frontend served as static files. Test the deploy early in the hackathon.

---

## PART D: Phases from now to the hackathon

### Phase 1: 4-day learn-and-build sprint (Thu 29 Oct – Sun 1 Nov, practice repo `wise-blink-practice`)
The whole practice tool is built in **4 days**, on **WISE/NEOWISE data** (never SPHEREx). That means **about 7 hours a day each**, in three blocks: morning, afternoon, evening. Kripas types his own code; the AI explains each step and reviews it. Each day ends with the learning log, a pull request into `main`, and a 15-minute call.

| Day | Kripas (learn → build) | [Friend's name] (learn → build) | End-of-day check |
|---|---|---|---|
| **1, Thu 29 Oct** | Lessons 1–4 → `coords.py` (tests pass), `resolve.py` (SIMBAD), `archive.py` (NEOWISE images covering Teegarden's Star: count and dates) | Lessons 1, 6 + story → `index.html` search box + URL; Aladin Lite moves to RA/Dec, click fills the box | Image count matches IRSA's web search; link opens Aladin at the right place |
| **2, Fri 30 Oct** | Lessons 5, 7 → cutouts (image + mask), WCS, `MJD_OBS`, mask, % masked, `images.py` PNG frames for every visit with **one stretch for all** | Flipbook (play, pause, step, speed, blink), frame label, W1/W2 buttons, mask toggle, on dummy PNGs | About 20 real Teegarden PNGs; flipbook plays dummy frames |
| **3, Sat 31 Oct** | Proper motion → `gaia.py` (Gaia DR3 moved to each MJD); `align.py` (`reproject`) + 1/variance add-up per visit; FastAPI `main.py` (`/api/resolve`, `/api/coverage`, `/api/frames`, `/api/gaia`) + disk cache | Gaia markers; `fetch` from the real API; honest error messages; agree API format with Kripas in the morning | **Teegarden's Star walks in the browser, on its Gaia markers** |
| **4, Sun 1 Nov** | Variable stars, pick the Mira → `/api/diff` (sigma), `/api/lightcurve`; test list | Difference mode, Chart.js light curve; **deploy**; test list | **Public link works**; all tests in Part D 2.4 run once; lessons note written |

**Mon 2 – Fri 6 Nov (buffer and extra practice):**
- Mon 2: fix anything not finished in the 4 days.
- Tue 3: Level 3 practice (W1 − W2 colour on click, measured motion vs Gaia, About page).
- Wed 4: Kripas reads Supplement sections 2.2, 3.2.5, 3.2.9 and 3.4.3 and finishes `FACTS.md`. [Friend's name] makes a practice 30-second video from the practice tool.
- Thu 5: a 3-hour from-memory drill (empty folder → search → one cutout → flipbook → deploy). Delete afterwards.
- Fri 6: rest; rehearsal checklist (2.5).

The practice repo is **not** copied into the rehearsal or the hackathon; it is archived on 9–10 Nov.

### Phase 2: Full rehearsal "WISE Blink" (Sat 7 – Sun 8 Nov, timed 48 hours)
**Goal:** one complete fake hackathon with the same tool type, schedule, roles and submission, so that on 14 Nov nothing is new except the data.

#### 2.1 Why WISE is the right practice data
- Also NASA data, also at IRSA, same file type (FITS + WCS + mask), same tools (pyvo, astroquery, cutouts).
- Same sky rhythm: WISE/NEOWISE visits each patch about every 6 months (2010 – 2024), like SPHEREx.
- Similar pixels (WISE 2.75″, SPHEREx 6.15″), so motions look similar.
- It's what Backyard Worlds uses, so we can compare our flipbook with a known working tool.

#### 2.2 Feature mapping (rehearsal → hackathon)
- WISE bands W1 (3.4 µm) and W2 (4.6 µm) → SPHEREx detectors D1 – D6.
- WISE mask image (`-msk`) bits → SPHEREx FLAGS bits (official list).
- `MJD_OBS` per exposure → `MJD-AVG`.
- Per-visit add-up of about 12 exposures → add-up per epoch and detector.
- W1 − W2 colour (two-point "spectrum") → spectrum on click.
- Teegarden's Star / Luhman 16 motion vs Gaia → Barnard's Star / Epsilon Indi B vs Gaia.
- Luhman 16 bright in W2, fainter in W1 (cold) → WISE 0855 only in D5 – D6.
- A Mira variable light curve vs AAVSO → R Dra / RW Aur vs AAVSO.

#### 2.3 Mock challenge statement (print it, treat it as the official text)
"Build a public web tool. The user enters RA/Dec or a name and sees WISE/NEOWISE images of that patch from 2010 – 2024 as a flipbook, making moving and changing objects easy to spot. Bonus: choose band, add or subtract epochs, field of view, Gaia overlay, coordinates in the URL, show bad pixels, light curve, colour on click, use Astropy and Aladin."

#### 2.4 Rehearsal test targets and pass/fail
- **Teegarden's Star** (RA 02h53m00.9s, Dec +16°52′53″, about 5.1″/yr): about 70″ (about 25 px) over 14 years. Pass: track within about 1 px of Gaia.
- **Luhman 16** (RA 10h49m15.6s, Dec −53°19′06″, about 2.8″/yr): about 40″ (about 14 px). Pass: motion matches Gaia; W1 − W2 colour is red (cold brown dwarf).
- **Proxima Centauri** (about 3.9″/yr): may saturate. Pass: the tool shows saturation or mask honestly instead of crashing.
- **One Mira variable** (Kripas picks it from AAVSO; W1 fainter than about 8 mag). Pass: light-curve shape roughly matches AAVSO.
- **Edge cases:** an invalid name gives a clear error (no guess); a far-off RA/Dec still loads; a slow archive call shows a timeout message.

#### 2.5 Before the clock starts (Fri 6 Nov evening)
- Mock statement printed; this plan and `FACTS.md` open.
- Both laptops: Python 3.11 venv, Node, Git, hosting account logged in.
- Empty private GitHub repo `wise-blink-rehearsal`.
- **Time log sheet:** planned hours vs actual hours vs blocker, for each task.
- Phone hotspot tested; food and sleep shifts agreed.

#### 2.6 Hour-by-hour (identical to Part E, so the timings transfer)
- **0 – 2 (both):** read the mock statement; write the API format; split the work.
- **2 – 10:** Kripas: resolve, coverage, cutouts, mask and clean, PNG frames, `/api/frames`. [Friend's name]: layout, search, URL, Aladin, flipbook on sample PNGs.
- **Checkpoint hour 10:** Teegarden's Star plays end to end. If not, stop and fix together.
- **10 – 14:** pre-cache all rehearsal targets; first deploy.
- **14 – 22:** Kripas: alignment, per-visit add-up, `/api/gaia`. [Friend's name]: band buttons, frame labels, mask toggle, target buttons, deploy again.
- **Checkpoint hour 22 (Level 1):** run the 2.4 test list; write down results. Sleep in shifts.
- **22 – 34:** Kripas: `/api/diff` in sigma, `/api/lightcurve`. [Friend's name]: difference mode, Gaia markers, light-curve panel, Aladin overlays.
- **Checkpoint hour 34 (Level 2).**
- **34 – 40:** Level 3 only if Level 2 passes: W1 − W2 colour on click, measured motion vs Gaia, About page.
- **40 – 46:** Kripas: limitations, references, credits. [Friend's name]: 30-second video, project page. **Mock submission by hour 46.**
- **46 – 48:** pitch twice, timed; record a backup demo video.

#### 2.7 Mock judging (Sun 8 Nov evening, 1 hour)
- 1 – 2 people watch the video and a 3-minute live demo, score 1 – 5 on the 5 criteria, and ask 3 questions each.
- Write down every question we could not answer well.

#### 2.8 Lessons learned and archive (Mon 9 – Tue 10 Nov)
- Lessons-learned note: planned vs actual hours, top 5 blockers and fixes, slow libraries or archive calls, deploy problems, what to cut or move earlier.
- Update Part E timings with the real numbers.
- A **1-page command cheat sheet** (library names, IRSA endpoints, deploy steps). Notes, not code.
- **Archive the rehearsal repo; do not open or copy it again.**

#### 2.9 Rehearsal "done" means
- Public link works; Teegarden's Star and Luhman 16 visibly move and match Gaia; 30-second video exists; mock form filled; lessons-learned note written.
- If Level 1 is not reached by hour 22 in the rehearsal, the real plan cuts Level 3 and moves the deploy earlier.

### Phase 3: Final preparation (11 – 13 Nov)
- Part E adjusted with the rehearsal timings.
- **From-memory drill (12 Nov, 3 hours, WISE again):** in a new empty folder, rebuild the Level 1 skeleton (search, one cutout, flipbook, deploy) without looking at the rehearsal code. Then delete the folder.
- Pitch script (3–5 minutes) and the 30-second video storyboard.
- Laptops ready; accounts ready; IRSA reachable from the venue network or a phone hotspot.
- Team and local event registered on spaceappschallenge.org.
- **13 Nov evening:** read the challenge Resources tab and the Project Submission Guide together; adjust the plan.

### Phase 4: The hackathon (14 – 15 Nov), a fresh build
- New empty repo at the start. Commit often (the history shows the code was written during the event).
- Follow Part E.

### Phase 5: After the hackathon
- Resume the research track (`PROJECT_PLAN.md`: moving objects, the Planet Nine sensitivity map, a possible RNAAS paper).

---

## PART E: 48-hour build schedule

| Hours | Kripas (backend and science) | [Friend's name] (frontend and presentation) |
|---|---|---|
| 0–2 | Read the statement and resources together; create the repo; agree on the API format | Same |
| 2–10 | `/api/resolve`, `/api/coverage`, cutouts, cleaning, PNG frames, `/api/frames` | Layout, search, URL, Aladin, flipbook using sample frames |
| 10–14 | **Integration: Barnard's Star plays end to end.** Pre-cache the 5 targets | Same |
| 14–22 | Alignment, add-up per epoch and detector, `/api/gaia` | Detector buttons, frame labels, flags toggle, target buttons, **deploy** |
| 22–26 | Run the C4 acceptance tests on all 5 targets; fix problems; sleep in shifts | Same |
| 26–34 | `/api/diff` (sigma), `/api/lightcurve` | Difference mode UI, Gaia markers, light-curve panel, Aladin Gaia and WISE overlays |
| 34–40 | Level 3: `/api/spectrum`, measured motion vs Gaia (only if Level 2 passes) | Spectrum panel, About page, polish |
| 40–46 | Limitations text, references, NASA data section | **30-second video** from the real tool, project page; **submit by hour 46** |
| 46–48 | Rehearse the live pitch twice; prepare the backup demo video | Same |

**Hard rules during the event:** no new features after hour 40; if a feature isn't working by its deadline, cut it.

---

## PART F: Story, pitch and video
- **One line:** "In 1930 one person found Pluto by blinking two photos. Today SPHEREx photographs a billion objects in 102 colours, and our tool lets anyone, anywhere, do what Tombaugh did."
- **Five beats:**
  1. Tombaugh's blink.
  2. Too much SPHEREx data for one person.
  3. Our tool.
  4. Proof: Barnard's Star walks and matches Gaia; WISE 0855 appears only at 4–5 µm, so it's cold; R Dra brightens and fades, matching AAVSO.
  5. Impact: anyone can discover. Two students from Nepal learned SPHEREx in a month.
- **30-second video:**
  1. 0–5 s: Pluto plates blinking.
  2. 5–10 s: the SPHEREx sky.
  3. 10–20 s: type "Barnard's Star"; it walks over the Gaia markers.
  4. 20–26 s: WISE 0855 appearing from D1 to D6, plus a spectrum.
  5. 26–30 s: name and URL.
- **Live pitch (3–5 minutes):** live demo in the first 30 seconds, then the 5 beats, then limitations, then questions.
- **Practise these questions:** how we know motion is real (Gaia, sigma differences, official flags); why WISE 0855 shows only in some bands (it's cold); what happens with new data (live IRSA queries); whether it can find Planet X (it shows how such an object would move; a real search needs more data); who uses it (volunteers, students, scientists).
- **Honesty:** no "discovered" or "Planet X found" claims; every number has a source.

## PART G: Submission checklist (English)
- Title, high-level summary, **30-second demo video** (or 7 slides max) at a public link with no login.
- Public GitHub repo and the live link; project details and tools.
- NASA data used (SPHEREx/IRSA); partner and other data (ESA Gaia, AAVSO, CDS).
- References; AI tools disclosure (honest; it does not affect judging).
- All team members on the project page. Deadline: Sun 15 Nov, 23:59 local time (check whether the local event has an earlier deadline).

## PART H: Risks and what we do about them
- **IRSA down or slow:** pre-cached targets, small cutouts, a timeout with an honest message.
- **Faint targets:** D5–D6 presets and add-ups.
- **Venue internet:** phone hotspot; cached demo.
- **Scope creep:** Level 1 first; nothing new after hour 40.
- **Demo failure during judging:** a backup video, and the page pre-loaded before the pitch.
- **Rule risk:** fresh repo, all pre-hackathon coding on WISE data (never SPHEREx), no reuse of rehearsal or prototype code.
- **WISE practice surprises** (unknown collection names, saturated stars): solved in Phase 1, before the rehearsal clock starts.
