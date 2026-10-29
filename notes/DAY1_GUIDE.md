# Day 1 guide (Thu 29 Oct): coordinates, names, archive search, search page

4-day sprint, day 1 of 4. About 7 hours each, in 3 blocks. After each block, say "review Day 1 block N" to the AI, then commit.

---

## Kripas (branch `kripas-backend`)

### Block 1 (about 2.5 h): coordinates and time → `backend/app/coords.py`

**Read:** `docs/learn/01_sky_coordinates.md`, `docs/learn/02_time.md`. You should be able to answer:
- What are RA and Dec? Why is RA written in hours (1h = 15°)?
- What is the difference between `08h55m10.8s` and `133.795°`?
- What is MJD, and why do astronomers count days instead of using dates?

**Write three functions:**
1. **`parse_coordinates(text: str) -> tuple[float, float]`**, returning `(ra_deg, dec_deg)`.
   - Must accept:
     - letters: `"08h55m10.831s -07d14m42.53s"`
     - colons: `"08:55:10.831 -07:14:42.53"` (RA in hours, Dec in degrees)
     - decimal degrees: `"133.795 -7.245"`
   - Must **raise `ValueError`** for empty text, words, one number only, RA outside 0–360, or Dec outside −90 to +90.
   - Hint: `astropy.coordinates.SkyCoord` parses these if you give the units. Decimal numbers are degrees; sexagesimal RA is hours (`unit=(u.hourangle, u.deg)`). How can you tell which kind of text you got?
   - Hint: catch astropy's errors and raise your own `ValueError` with a clear message.
2. **`date_to_mjd(date: str) -> float`**: `"2026-10-29"` gives `61342.0`, and `"2000-01-01T12:00:00"` gives `51544.5`. Hint: `astropy.time.Time`.
3. **`mjd_to_date(mjd: float) -> str`**: ISO text such as `"2023-02-25T00:00:00.000"`. Hint: `Time(..., format="mjd")` and `.isot`.

**Check:**
```bash
cd ~/wise-blink-practice
source .venv/bin/activate
python -m pytest backend/tests/test_coords.py -v
```
All 12 tests must pass. **Do not edit the tests.** If you think a test is wrong, ask.

### Block 2 (about 2 h): star names → `backend/app/resolve.py`

**Read:** `docs/learn/03_light_and_brightness.md` (magnitudes; you'll need them for Gaia and saturation).

**Write `resolve_name(name: str) -> dict`:**
- Returns `{"ra": float, "dec": float, "source": "SIMBAD", "name": <the name used>}`.
- If SIMBAD does not know the name, raise `LookupError("... not found in SIMBAD")`. **Never guess, never return a default.**
- Hint: `from astroquery.simbad import Simbad`, `Simbad.query_object(name)`. Look at what the result table contains (print it first). Column names can differ between astroquery versions, so check them.
- Hint: SIMBAD gives the J2000 position as stored in its catalogue. For fast stars this is not "where it is today"; that's what Gaia is for on Day 3.

**Check by hand (write `backend/tests/test_resolve.py` yourself, marked as a network test):**
- `"Teegarden's Star"` gives about RA 43.25°, Dec +16.88°.
- `"WISE J085510.83-071442.5"` gives about RA 133.80°, Dec −7.25°.
- `"notastar123"` raises `LookupError`.

### Block 3 (about 2.5 h): which images exist? → `backend/app/archive.py`

**Read:** `docs/learn/04_fits_files.md`.

**Background:** IRSA keeps a big table called `ivoa.obscore` with one row per image: which collection it belongs to, its sky footprint (`s_region`), its time (`t_min`, in MJD), its band (`energy_bandpassname`), and a download link (`access_url`). You ask it questions in ADQL (a kind of SQL) through its TAP service at `https://irsa.ipac.caltech.edu/TAP`, using `pyvo.dal.TAPService`.

**Steps:**
1. **Find the collection name.** Ask the table for the distinct values of `obs_collection`, and find the one for **NEOWISE single exposures** (the reactivation mission, 2013 – 2024). Write it in `docs/plan/FACTS.md` section 6.
2. **Write `find_images(ra, dec, collection) -> list[dict]`:** every image whose footprint contains the point. Use `CONTAINS(POINT('ICRS', ra, dec), s_region) = 1` (the footprint, not the image centre). Return `obs_id`, `mjd` (`t_min`), `band`, `access_url` for each.
3. **Summarise for Teegarden's Star:** total count, count per band (W1, W2), first and last date (convert MJD with your `mjd_to_date`).

**Check against IRSA's own website:** open the IRSA image search for NEOWISE single exposures at the same position, and compare the count. Write both numbers in the learning log. If they differ, find out why before Day 2.

### End of day
- `notes/LEARNING_LOG.md` Day 1 entry.
- `git add -A && git commit -m "Day 1: coords, resolve, archive"` and `git push`.
- Pull request `kripas-backend` → `main` on GitHub.
- 15-minute call with [Friend's name]: show each other what works.

---

## [Friend's name] (branch `friend-frontend`)

### Block 1 (about 2 h): read and the story
- `docs/plan/HACKATHON_PLAN.md` and `docs/plan/FRIEND_PLAN.md`.
- Lessons `docs/learn/01_sky_coordinates.md` and `docs/learn/06_spherex.md`.
- Write the 5 story beats (HACKATHON_PLAN Part F) in your own words in `notes/STORY.md`.

### Block 2 (about 2.5 h): `frontend/index.html` search page (plain HTML + JS, no framework)
- A text box for RA/Dec or a name, a field-of-view number box (arcminutes, default 3), and a "Go" button.
- On page load, read `?ra=..&dec=..&fov=..` from the URL and fill the boxes.
- When Go is pressed, update the URL without reloading, so the link can be shared.
- Hint: `new URLSearchParams(window.location.search)` and `history.replaceState`.

### Block 3 (about 2.5 h): Aladin Lite sky view
- Embed Aladin Lite v3 (from the CDS website: one script tag plus a `div`).
- Go moves Aladin to the typed RA/Dec with the chosen field of view.
- Clicking the sky fills the RA/Dec box (and the URL).
- Try the background surveys: 2MASS, unWISE or AllWISE (the same telescope our data comes from).

### Done when
Opening `frontend/index.html?ra=43.2537&dec=16.8814&fov=5` shows Aladin centred on Teegarden's Star, and clicking somewhere updates the box and the URL.

### End of day
- `notes/LEARNING_LOG.md` Day 1 entry.
- `git add -A && git commit -m "Day 1: search page and Aladin"` and `git push`.
- Pull request `friend-frontend` → `main` on GitHub.
- 15-minute call with Kripas.
