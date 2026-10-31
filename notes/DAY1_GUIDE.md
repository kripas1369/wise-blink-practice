# Day 1 guide (Sat 31 Oct): Step 1, find and get the SPHEREx data

Day 1 of 4. About 7 hours each, in 3 blocks. After each block say "review Day 1 block N" to the AI, then commit.

---

## Block 1 (both together, about 2 h): revise how to query and get cutouts

Sit together (or call) and go through this. Both of you must be able to explain each line.

1. **Where the data is.** NASA's IRSA archive. We ask it questions in ADQL (like SQL) through TAP: `https://irsa.ipac.caltech.edu/TAP` (Python: `pyvo.dal.TAPService`).
2. **The SPHEREx image table:** `spherex.obscore`, one row per image. Look at the columns: `obs_id`, `s_region` (the image outline on the sky), `t_min`/`t_max` (MJD), `energy_bandpassname` (detector), `em_min`/`em_max` (wavelength in metres), `access_url` (download link), `access_estsize`.
3. **The question "which images cover this point?":**
   `CONTAINS(POINT('ICRS', ra, dec), s_region) = 1`
   This checks the outline, not the centre. (The old prototype checked the centre and missed images.)
4. **Cutouts.** A full SPHEREx file is about 70 MB. Read IRSA's SPHEREx cutout tutorial (in [Friend's name]'s resources folder or on the IRSA website) and find how to ask for a small square around a position. Write the method in `docs/plan/FACTS.md` section 3.
5. **What is inside a cutout:** IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE, and the header keyword `MJD-AVG` (the real observation time; never use `DATE`). See `docs/plan/FACTS.md` sections 1 – 2.
6. **Gaia** (for proof later): also at IRSA, table `gaia_dr3_source`.
7. **SIMBAD** (names → positions): main server `simbad.cds.unistra.fr`; it was down on 29 Oct, the mirror `simbad.harvard.edu` worked.
8. **Moving stars:** SIMBAD gives positions for the year 2000. Barnard's Star has moved about 4.5′ since then, so move the position to today with its proper motion **before** asking for images.

---

## Kripas (branch `kripas-backend`)

### Block 2 (about 2.5 h): `coords.py` and `resolve.py`

**`backend/app/coords.py`**: read `docs/learn/01_sky_coordinates.md` and `02_time.md` first.
1. `parse_coordinates(text) -> (ra_deg, dec_deg)`: accepts `"08h55m10.831s -07d14m42.53s"`, `"08:55:10.831 -07:14:42.53"` and `"133.795 -7.245"`; raises `ValueError` for empty text, words, one number, RA outside 0 – 360 or Dec outside −90 to +90. Hint: `SkyCoord(..., unit=(u.hourangle, u.deg))` for sexagesimal; decimal numbers are degrees.
2. `date_to_mjd(date) -> float` and `mjd_to_date(mjd) -> str`. Hint: `astropy.time.Time`.
3. Check: `python -m pytest backend/tests/test_coords.py -v`, all 12 pass. **Do not edit the tests.**

**`backend/app/resolve.py`**:
- `resolve_name(name) -> {"ra", "dec", "pmra", "pmdec", "source", "name"}`.
- Try the main SIMBAD server; if it fails, try the Harvard mirror. If the name is unknown, raise `LookupError`. **Never guess.**
- Hint: `from astroquery.simbad import Simbad, conf`; `conf.server = "simbad.harvard.edu"`; ask for proper motion fields. Print the result table first to see the column names.
- Check: "Barnard's Star" → about 269.45°, +4.69° (J2000), pmdec about +10 300 mas/yr; "notastar123" → `LookupError`.

### Block 3 (about 2.5 h): `archive.py`

1. `position_now(ra, dec, pmra, pmdec, year)`: move a J2000 position to a given year with proper motion. Check: Barnard's Star moves about 4.5′ from 2000 to 2026.
2. `find_images(ra, dec) -> list[dict]`: SPHEREx images covering the point, each with `obs_id`, `mjd` (`t_min`), `detector`, `wl_min_um`, `wl_max_um`, `access_url`.
3. **Run it for all 5 targets** and fill the table in `docs/plan/FACTS.md` section 6: number of images, first and last date, number of epochs (groups of dates weeks or months apart), images per detector D1 – D6.
4. **Check one count against IRSA's own SPHEREx search website** for the same position. Write both numbers in the learning log.
5. Download **one** Barnard's Star cutout, open it with `astropy.io.fits`, and print every extension name, its shape, and the header keywords `MJD-AVG`, `DATE`, and the `MP_*` flag keywords.

**Done when:** the table of 5 targets is filled in, one count matches IRSA's website, and one cutout opens with all its parts.

---

## [Friend's name] (branch `friend-frontend`)

### Block 2 (about 2.5 h): `frontend/index.html` (plain HTML + JS)
- Search box (RA/Dec or a name), field of view (arcmin, default 3), Go button.
- On load, read `?ra=..&dec=..&fov=..&det=..` from the URL and fill the boxes.
- Go updates the URL without reloading so the link can be shared. Hint: `URLSearchParams`, `history.replaceState`.

### Block 3 (about 2.5 h): Aladin and the 5 targets
- Embed Aladin Lite v3; Go moves it to the position and field of view; clicking the sky fills the box and the URL.
- 5 target buttons, each with one line:
  - **Barnard's Star:** the fastest-moving star; watch it walk.
  - **Epsilon Indi B:** a pair of brown dwarfs; a small shift.
  - **WISE 0855:** the coldest brown dwarf; only visible at the longest wavelengths.
  - **RW Aurigae:** a young star that dims and brightens.
  - **R Draconis:** a pulsating giant; brightness rises and falls over about 8 months.
- Write the 5 story beats (HACKATHON_PLAN Part F) in your own words in `notes/STORY.md`.

**Done when:** clicking "Barnard's Star" centres Aladin on it, and the URL can be copied and opens the same view.

---

## End of day (both)
- `notes/LEARNING_LOG.md`: Day 1 entry.
- Commit and push your branch; open a pull request into `main`.
- 15-minute call: show each other what works; agree what Kripas sends tomorrow (PNG frames + JSON).
