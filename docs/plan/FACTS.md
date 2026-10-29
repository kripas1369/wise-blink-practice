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
- `PSF`: the shape of a star image.
- `WCS-WAVE`: wavelength of each pixel. **Display only, not for science** (Supplement v2.0).

### Time
- **Use `MJD-AVG`** (middle of the exposure, Modified Julian Date).
- **Never use `DATE`**: that is when the file was *processed*, not when the sky was observed.

---

## 2. SPHEREx flags (Explanatory Supplement v2.0)
- **Bit positions:** read them from the `MP_*` keywords in the FLAGS header. Do not hard-code them.
- **SOURCE = bit 21:** "a known object is here" (from the reference catalogue and known Solar System objects). **It is a label, not a problem.** Sources fainter than 19 AB are not marked. The mask circle can be too big or too small (Supplement §3.2.9).
- **Bad-pixel list we mask (Mosaic Tool list, §3.4.3):**
  TRANSIENT, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD, PHANMISS, NONLINEAR, PERSIST, CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO.
- **Shown but not masked:** OVERFLOW, SOURCE, OUTLIER.
- **Rule:** a pixel is bad if **any** bad bit is set. SOURCE never cancels a bad bit.

### What we measured in Kripas's 4 files (D1, near the Galactic plane)
- SOURCE was set on **86 – 95%** of pixels; only 4 – 13% of pixels had no flag at all.
- With the old `preserve_sources` logic, **55 – 86% of truly bad pixels survived**. That is why SOURCE is a label only.

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
- **Cutout method:** from the IRSA SPHEREx cutout tutorial **(Kripas fills in on Day 1)**.

---

## 4. Motion maths
- Gaia DR3 positions are for the date **2016.0**. To know where a star "should be" on an image date, move it with its proper motion (`pmra`, `pmdec`, in mas/yr) from 2016.0 to that image's MJD (astropy `SkyCoord.apply_space_motion`).
- **Shift in pixels** = proper motion (″/yr) × years between images ÷ pixel size (″).
  - SPHEREx: 6.15″ per pixel.
- A shift smaller than about 1 pixel is **not** a reliable detection by eye.

---

## 5. Official hackathon targets (SPHEREx)
Coordinates are J2000 positions. **Re-check all of them with SIMBAD on 14 Nov.**

| Target | RA, Dec | What it is | Expected in SPHEREx (about 1.5 years) |
|---|---|---|---|
| Barnard's Star | 17h57m48.5s, +04°41′36″ **(verify)** | nearest single red dwarf, fastest-moving star (about 10.4″/yr) | about 15″ ≈ 2.5 px shift; clearest mover |
| Epsilon Indi B | near 22h04m, −56°47′ **(verify)** | brown-dwarf pair, about 4.7″/yr; companion of Epsilon Indi A | about 1 px; subtle |
| WISE 0855 | 08h55m10.831s, −07°14′42.53″ (from the challenge text) | coldest known brown dwarf, about 8″/yr | about 2 px; invisible in D1–D3, visible in D5–D6 |
| RW Aurigae | 05h07m49.5s, +30°24′05″ **(verify)** | young star with dimming events | brightness changes |
| R Draconis | 16h32m40.2s, +66°45′18″ **(verify)** | Mira variable, period about 245 days | strong brightening and fading |

Comparison data: Gaia DR3 (motion), AAVSO (variable-star light curves).

---

## 6. SPHEREx coverage of the 5 targets (Kripas fills in on Day 1)

| Target | Images | First date | Last date | Epochs | Images per detector D1 – D6 |
|---|---|---|---|---|---|
| Barnard's Star | | | | | |
| Epsilon Indi B | | | | | |
| WISE 0855 | | | | | |
| RW Aurigae | | | | | |
| R Draconis | | | | | |

Our count must match IRSA's own SPHEREx search for the same position.

---

## 7. API format (draft, finalise together on the Day 3 morning call, Sat 31 Oct)
- `GET /api/resolve?name=` → `{ "ra": deg, "dec": deg, "source": "SIMBAD" }` or `{ "error": "not found" }`.
- `GET /api/coverage?ra=&dec=` → `[ { "obs_id", "band", "mjd", "wl_min_um", "wl_max_um", "release" } ]`.
- `GET /api/frames?ra=&dec=&fov_arcmin=&band=&mode=single|coadd` → `[ { "png_url", "mjd", "date_iso", "epoch_id", "band", "n_images", "pct_flagged" } ]`.
- `GET /api/diff?...&epochA=&epochB=` → `{ "png_url", "max_sigma", "min_sigma" }`.
- `GET /api/gaia?ra=&dec=&fov_arcmin=&mjds=` → `[ { "source_id", "g_mag", "positions": [ { "mjd", "ra", "dec" } ] } ]`.
- `GET /api/lightcurve?ra=&dec=&band=` → `[ { "mjd", "flux", "flux_err", "flagged" } ]`.
- `GET /api/spectrum?ra=&dec=&epoch=` → `[ { "wl_um", "flux", "flux_err" } ]`.
- **Units:** degrees for RA/Dec, arcminutes for field of view, micrometres for wavelength, MJD for time.
- **Errors:** always `{ "error": "<plain message>" }` with a non-200 status. The frontend shows the message; it never invents a value.

---

## 8. Honesty rules
- No "discovered" or "Planet X found" claims.
- No default or made-up values when something fails (no fake dates, no default constellation).
- Every number on screen comes from the API, and every claim in the pitch has a source.

## Sources
- SPHEREx Explanatory Supplement v2.0 (`SPHEREx_Expsupp_QR.pdf`): §2.2, §3.2.5, §3.2.9, §3.4.3.
- NASA Space Apps 2026 challenge page "Planet X and SPHEREx".
- IRSA SPHEREx documentation; Gaia DR3; AAVSO; SIMBAD.
