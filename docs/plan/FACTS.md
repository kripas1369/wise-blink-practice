# FACTS: the one-page truth sheet (Team Not42)

Every number on our website must come from the data or from this sheet, and every line here has a source. If a fact is marked **(verify)**, check it again on 14 Nov (SIMBAD, IRSA or the Resources tab) before using it.

Notes only. No code from this file goes into the hackathon repo.

---

## 1. SPHEREx basics
- **What:** NASA all-sky infrared survey telescope; maps the whole sky every 6 months; 102 colours (6 detectors × 17 channels).
- **Pixel size:** 6.15″ (arcseconds).
- **Data we can use:** from about Apr 2025 to Oct 2026 **(verify the latest release on 13 Nov)**.
- **Archive:** NASA/IPAC IRSA.

### Detectors (wavelength in micrometres, µm)
| Detector | Range (µm) | Notes |
|---|---|---|
| D1 | 0.75 – 1.09 | shortest (near visible red) |
| D2 | 1.10 – 1.62 | |
| D3 | 1.63 – 2.41 | |
| D4 | 2.42 – 3.82 | |
| D5 | 3.83 – 4.41 | cold brown dwarfs show up here |
| D6 | 4.42 – 5.00 | longest; WISE 0855 brightest here |

### File extensions (Level 2 image)
- `IMAGE`: the picture (surface brightness, MJy/sr).
- `FLAGS`: one number per pixel; each bit is a yes/no warning.
- `VARIANCE`: noise squared. sigma = sqrt(VARIANCE).
- `ZODI`: model of the zodiacal light background. Clean image = IMAGE − ZODI.
- `PSF`: the shape of a star image. **QR2:** `PSF` cube 121×101×101. **QR3:** replaced by an `EPSF` table (441 rows) (checked 31 Oct).
- `WCS-WAVE`: wavelength of each pixel. **Display only, not for science** (Supplement v2.0).

### Data releases (checked 31 Oct 2026, `spherex.obscore`)
- **QR2** (observations ~Apr 2025 – Apr 2026) and **QR3** (from ~Aug 2026) are both live. An exposure is in only one release (no double counting).
- Collections: `spherex_qr2`, `spherex_qr2_deep`, `spherex_qr3`, `spherex_qr3_deep` (science) and `spherex_qr2_cal`, `spherex_qr3_cal` (**skip**).
- New data arrives weekly (newest seen: released 28–29 Oct 2026). SIA2 lags TAP by ~1 day.

### Time
- **Use `MJD-AVG`** (middle of the exposure, Modified Julian Date).
- **Never use `DATE`**: that is when the file was *processed*, not when the sky was observed.

---

## 2. SPHEREx flags (Explanatory Supplement v2.0)
- **Bit positions:** read them from the FLAGS header. Do not hard-code them. The format differs by release (checked 31 Oct):
  - **QR2:** `MP_<NAME> = <bit>`, e.g. `MP_HOT = 10`. Defines TRANSIENT 0, OVERFLOW 1, SUR_ERROR 2, PHANTOM 4, REFERENCE 5, NONFUNC 6, DICHROIC 7, MISSING_DATA 9, HOT 10, COLD 11, FULLSAMPLE 12, PHANMISS 14, NONLINEAR 15, PERSIST 17, OUTLIER 19, SOURCE 21. (No CROSSTALK/GHOST/STREAK/BLOOM/HALO.)
  - **QR3:** `MSKN<nnnn> = '<NAME>'`, `MSKM<nnnn> = 1<<nnnn`. Adds CROSSTALK 20, GHOST 22, GHOST_FPA 23, GHOST_EXT 24, STREAK 25, BLOOM 26, HALO 28; drops PHANTOM and REFERENCE.
  - Code: `backend/app/flags.py` reads both, and **raises an error if a header defines no flags** (never "keep everything").
- **SOURCE = bit 21:** "a known object is here" (from the reference catalogue and known Solar System objects). **It is a label, not a problem.** Sources fainter than 19 AB are not marked. The mask circle can be too big or too small (Supplement §3.2.9).
- **Bad-pixel list we mask (Mosaic Tool list, §3.4.3):**
  TRANSIENT, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD, PHANMISS, NONLINEAR, PERSIST, CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO.
- **Shown but not masked:** OVERFLOW, SOURCE, OUTLIER.
- **Rule:** a pixel is bad if **any** bad bit is set. SOURCE never cancels a bad bit.

### What we measured in Kripas's 4 files (D1, near the Galactic plane)
- SOURCE was set on **86 – 95%** of pixels; only 4 – 13% of pixels had no flag at all.
- With the old `preserve_sources` logic, **55 – 86% of truly bad pixels survived**. That is why SOURCE is a label only.

### What we measured in 0.05° cutouts centred on the 5 targets (31 Oct)
- SOURCE covers **98 – 100%** of pixels around the bright targets (22% around faint WISE 0855 in D6). Masking SOURCE would erase the target itself.
- Bad pixels (official list): **0.4 – 7.3%** per cutout.

---

## 3. Finding and getting images
- **Coverage question:** "which images contain this point?" Use the image *footprint*, not the image centre:
  `CONTAINS(POINT('ICRS', <ra>, <dec>), s_region) = 1` on the IRSA table `spherex.obscore`.
- **Check:** our count must equal IRSA's own web search count for the same point.
- **Get:** IRSA cutouts only (small squares around the target), never the full ~70 MB file.
- **Checked 29 Oct 2026** at IRSA TAP `https://irsa.ipac.caltech.edu/TAP`:
  - SPHEREx tables: `spherex.obscore` (one row per image), plus `spherex.observation`, `spherex.plane`, `spherex.artifact`.
  - Useful `spherex.obscore` columns: `obs_id`, `s_region`, `s_ra`, `s_dec`, `t_min`, `t_max` (MJD), `energy_bandpassname`, `em_min`, `em_max` (metres), `access_url`, `access_estsize`, `obs_release_date`.
  - Gaia DR3 is also at IRSA: table `gaia_dr3_source` (not `gaia.gaiadr3_source`).
- **Fast stars:** move the position to today with proper motion **before** searching. Barnard's Star has moved about 4.5′ since 2000.
- **SIMBAD:** the main CDS server (`simbad.cds.unistra.fr`) did not respond on 29 Oct; the mirror `simbad.harvard.edu` worked. Always have the mirror as backup (astroquery: `astroquery.simbad.conf.server`).
- **Cutout method (tested 31 Oct):**
  1. Find images: the `CONTAINS ... s_region` query above, filtered to the 4 science collections.
  2. File path: a second query, `spherex.plane p JOIN spherex.artifact a ON a.planeid = p.planeid WHERE a.producttype = 'science' AND p.obs_publisher_did IN (...)` (a JOIN inside the `CONTAINS` query fails with "st_covers does not exist"). Remove the leading `ibe/data/` from `a.uri`.
  3. Cutout: `https://irsa.ipac.caltech.edu/ibe/cutout?ra=<deg>&dec=<deg>&size=<deg>&path=<path>`. (The docs also show appending `?center=ra,dec&size=0.1` to the file URL.)
  4. A 0.05° cutout = 29×29 pixels but **~5 MB (QR2) / ~4 MB (QR3)**, because the PSF/EPSF comes along. Keep all extensions; cutout axes follow the detector (**not north-up**).
  5. HTTP 404 = position not in that image. HTTP 503 = too many requests: **max 3 at a time**, retry with backoff. Check the reply starts with `SIMPLE`.

---

## 4. Motion maths
- Gaia DR3 positions are for the date **2016.0**. To know where a star "should be" on an image date, move it with its proper motion (`pmra`, `pmdec`, in mas/yr) from 2016.0 to that image's MJD (astropy `SkyCoord.apply_space_motion`).
- **Shift in pixels** = proper motion (″/yr) × years between images ÷ pixel size (″).
  - SPHEREx: 6.15″ per pixel.
- A shift smaller than about 1 pixel is **not** a reliable detection by eye.

---

## 5. Official hackathon targets (SPHEREx)
Coordinates are J2000 positions. **Re-check all of them with SIMBAD on 14 Nov.**

| Target | RA, Dec | What it is | Expected shift, first → last epoch released by 31 Oct |
|---|---|---|---|
| Barnard's Star | 17h57m48.5s, +04°41′36″ **(verify)** | nearest single red dwarf, fastest-moving star (10.39″/yr, SIMBAD) | 0.99 yr → 10.3″ ≈ **1.7 px**; clearest mover |
| Epsilon Indi B | near 22h04m, −56°47′ **(verify)** | brown-dwarf pair, 4.68″/yr; companion of Epsilon Indi A | 1.36 yr → 6.4″ ≈ **1.0 px**; subtle |
| WISE 0855 | 08h55m10.831s, −07°14′42.53″ (from the challenge text) | coldest known brown dwarf, 8.15″/yr | 0.99 yr → 8.1″ ≈ **1.3 px**; invisible in D1–D3, visible in D5–D6 |

Shifts are small (1–2 px), so alignment quality decides whether motion is visible. Re-check on 13 Nov: a new visit (for example WISE 0855, ~Nov 2026) may be released and make the shifts larger.
| RW Aurigae | 05h07m49.5s, +30°24′05″ **(verify)** | young star with dimming events | brightness changes |
| R Draconis | 16h32m40.2s, +66°45′18″ **(verify)** | Mira variable, period about 245 days | strong brightening and fading |

Comparison data: Gaia DR3 (motion), AAVSO (variable-star light curves).

---

## 6. SPHEREx coverage of the 5 targets (measured 31 Oct 2026, `notes/DAY1_REPORT.md`)
Position moved with proper motion to 2026.0, then `CONTAINS ... s_region`, 4 science collections.

| Target | Images | First date | Last date | Epochs (dates) | Images per detector D1 – D6 | Releases |
|---|---|---|---|---|---|---|
| Barnard's Star | 359 | 2025-08-15 | 2026-09-22 | 3 (2025-08-29, 2026-03-20, 2026-08-22) | 60 / 61 / 59 / 59 / 61 / 59 | qr2 240, qr3 119 |
| Epsilon Indi B | 445 | 2025-04-24 | 2026-10-02 | 4 (2025-05-09, 2025-10-11, 2026-04-25, 2026-09-27) | 43 / 92 / 95 / 43 / 80 / 92 | qr2 325, qr3 120 |
| WISE 0855 | 256 | 2025-05-05 | 2026-05-14 | 3 (2025-05-06, 2025-11-12, 2026-05-01) | 36 / 48 / 45 / 36 / 48 / 43 | qr2 256 |
| RW Aurigae | 333 | 2025-09-01 | 2026-09-16 | 3 (2025-09-10, 2026-03-03, 2026-09-11) | 56 / 55 / 56 / 56 / 56 / 54 | qr2 224, qr3 109 |
| R Draconis | 2483 | 2025-04-24 | 2026-09-27 | 9 (split at 60 days; near the north ecliptic pole, seen almost all year) | 584 / 89 / 575 / 581 / 89 / 565 | qr2 536, qr2_deep 1224, qr3_deep 723 |

- Each exposure gives 2 images (paired detectors), so exposures = images ÷ 2 (Barnard 181, Eps Ind B 235, WISE 0855 129, RW Aur 168, R Dra 1257).
- R Dra is in the deep-field area: most of its images are `_deep`. D2 and D5 have far fewer images there (89).
- **To do:** compare one count with IRSA's own SPHEREx Data Explorer search for the same position.

---

## 7. API format (built 31 Oct, `backend/app/main.py`; run `uvicorn backend.app.main:app --port 8000`)
Built (tested in `backend/tests/test_day3.py`):
- `GET /api/health` → `{ "ok": true }` (the website uses it to decide between the API and the static files).
- `GET /api/resolve?name=` → SIMBAD's answer (`name`, `simbad_id`, `ra`, `dec`, `pmra`, `pmdec`, `epoch`, `server`) plus `"source": "SIMBAD (<server>)"` and `position_now` (`{ra, dec, year: 2026.0, moved_arcsec}`, or `null` without a proper motion). Not found → 404; SIMBAD down → 503.
- `GET /api/coverage?ra=&dec=[&band=]` → `{ ra, dec, band, asked_at, summary, images: [ { "obs_id", "band", "mjd", "wl_min_um", "wl_max_um", "release", "release_date" } ] }`, cached 1 hour. IRSA down → 502.
- `GET /api/frames?target=&band=` or `?ra=&dec=&band=[&fov_arcmin=3]` → the frames manifest ([`FRAMES_FORMAT.md`](FRAMES_FORMAT.md)) with `png_url`, `flags_png_url`, `base_url`, `source`, `warnings`. A typed position (not within 5″ of a prepared target) starts a background job: **HTTP 202** `{ "status": "working", "message" }` until ready; no SPHEREx images → 404.
- `GET /api/gaia` (same location parameters) → `gaia.json` (FRAMES_FORMAT §6): per star `source_id` (text), `g_mag`, `xy` per frame.
- `GET /api/diff` (same location parameters) → `diff.json` (FRAMES_FORMAT §7): every visit pair with `png_url`, `days`, `wl_gap_um`, `scatter_sigma`, `max_sigma`, `min_sigma`, `z`; plus `default_pair`.
- `GET /api/lightcurve` (same location parameters) → `lightcurve.json` (FRAMES_FORMAT §10): the target's brightness in every single exposure, each with its own wavelength, plus same-wavelength visit comparisons, the field-star floor and Gaia neighbours inside the circle. Add `&x=&y=` (PNG pixels, 0 to size − 1, both or neither) to measure a clicked pixel instead. Built on Day 4 (tested in `backend/tests/test_day4.py`).
- Unknown `/api/...` path → 404. Interactive docs: `/api/docs`.

Changed from the draft, and why: `/api/frames` returns the whole manifest (labels need every field); `/api/diff` returns all pairs at once (the view switches pairs without waiting); `/api/gaia` gives pixel positions per frame (the website does not need its own WCS code).

`/api/lightcurve` returns an object, not the draft's bare list, because a point means nothing without its wavelength, the comparison rule and the warnings.

Still to build (later):
- `GET /api/spectrum?ra=&dec=&epoch=` → `[ { "wl_um", "flux", "flux_err" } ]`.
- **Units:** degrees for RA/Dec, arcminutes for field of view, micrometres for wavelength, MJD for time.
- **Errors:** always `{ "error": "<plain message>" }` with a non-200 status (400 bad input, 404 nothing there, 502/503 IRSA or SIMBAD down). The frontend shows the message; it never invents a value.

---

## 8. Honesty rules
- No "discovered" or "Planet X found" claims.
- No default or made-up values when something fails (no fake dates, no default constellation).
- Every number on screen comes from the API, and every claim in the pitch has a source.

## Sources
- SPHEREx Explanatory Supplement v2.0 (`SPHEREx_Expsupp_QR.pdf`): §2.2, §3.2.5, §3.2.9, §3.4.3.
- NASA Space Apps 2026 challenge page "Planet X and SPHEREx".
- IRSA SPHEREx documentation; Gaia DR3; AAVSO; SIMBAD.
