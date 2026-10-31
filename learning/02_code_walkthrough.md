# 02. Code walkthrough (Day 1 backend)

Open each file next to this page. The order follows the data: settings, then typed input, then
star motion, then names, then the archive, then the report that runs everything.

```
backend/app/
  config.py    fixed settings (addresses, detector wavelengths, flags, limits)
  coords.py    text -> (RA, Dec); dates <-> MJD
  motion.py    move a star with its proper motion; angle between two positions
  resolve.py   star name -> position + proper motion (SIMBAD, with a backup server)
  targets.py   the 5 official targets
  flags.py     which FLAGS bit means which problem (reads both QR2 and QR3 headers)
  archive.py   ask IRSA which images cover a point; download and inspect cutouts
scripts/day1_report.py   runs everything on the 5 targets, writes notes/DAY1_REPORT.md
backend/tests/           automatic checks (pytest)
```

---

## 1. `config.py`: one place for fixed values
Why: if a number is written in 5 files and it changes, you will forget one. Here every fixed value
lives once, with a comment saying where it comes from.

- `TAP_URL`: IRSA's query service. We send it questions in ADQL (a SQL dialect for the sky).
- `CUTOUT_URL`: IRSA's cutout service. It cuts a small square out of a big image on their side,
  so we download ~5 MB instead of ~70 MB.
- `SIMBAD_SERVERS`: the main CDS server first, the Harvard mirror second (the main one was down on
  29 and 31 Oct).
- `COLLECTIONS`: which parts of the archive are real sky images. The archive table also has
  calibration entries (`_cal`), which we must not treat as observations. QR2 and QR3 are two
  data releases (QR2: observations up to ~April 2026, QR3: from ~August 2026). `_deep` means
  extra visits to the two deep fields near the ecliptic poles.
- `DETECTORS`: wavelength range of each of the 6 detectors, in micrometres.
- `BAD_FLAG_NAMES`: names of pixel problems that make a pixel unusable (official list). Note:
  only **names** are here; the **bit numbers** are read from each file's header, because they can
  differ between releases. `SOURCE` is not in the list on purpose: it only says "a known star is
  here", which is not a defect.
- `MAX_PARALLEL_DOWNLOADS = 3`, `RETRIES = 4`: IRSA answers "503 busy" if we ask for too much
  at once, and sometimes drops the connection. We go slowly and retry.

## 2. `coords.py`: turn what the user types into numbers
```python
_SEXAGESIMAL = re.compile(r"[hmsd:]", re.IGNORECASE)
```
A regular expression that finds the letters h, m, s, d or a colon. If the text has any of them,
it is "sexagesimal" (hours-minutes-seconds), like `08h55m10.8s -07d14m42s`.

`parse_coordinates(text)`:
1. Replace commas with spaces and split. We need exactly 2 parts (RA and Dec), otherwise error.
2. Sexagesimal: astropy's `SkyCoord(..., unit=(u.hourangle, u.deg))` reads RA as **hours** and
   Dec as **degrees**. (1 hour of RA = 15 degrees.)
3. Otherwise both numbers are decimal degrees. We check RA is 0–360 and Dec is −90 to +90.
4. On any problem it raises `ValueError` with a clear message. It **never guesses**: a wrong
   guess would show the wrong part of the sky and the user would not know.

`date_to_mjd`, `mjd_to_date`, `mjd_to_year`: convert between calendar dates, MJD (a day counter
astronomers use; SPHEREx times are in MJD) and decimal years (for proper motion). astropy's `Time`
does the hard part (leap years, time scales). Lesson: [`docs/learn/02_time.md`](../docs/learn/02_time.md).

## 3. `motion.py`: stars move
Catalogues give a star's position **at one date** (SIMBAD: year 2000.0; Gaia: 2016.0) plus its
**proper motion** (how fast it moves across the sky, in milliarcseconds per year, "mas/yr").
Barnard's Star moves 10.4″ per year, so since 2000 it moved about 270″ (4.5′). A 3′ cutout made
at the year-2000 position would **miss the star completely**. So we move it first.

```python
new_ra = (ra + pmra_mas * years / MAS_PER_DEG / cos_dec) % 360.0
new_dec = dec + pmdec_mas * years / MAS_PER_DEG
```
- `years` = target year − catalogue year.
- `MAS_PER_DEG = 3.6e6` (1 degree = 3600″ = 3,600,000 mas).
- Divide by `cos_dec`: catalogues give the RA motion already multiplied by cos(Dec) (lines of RA
  get closer together near the poles). To turn it back into "degrees of RA" we divide.
- `% 360`: RA wraps around (359.9° + 0.2° = 0.1°).
- Near the poles cos(Dec) is ~0 and the division blows up, so we raise an error there.

This straight-line method is accurate to far less than one SPHEREx pixel (6.15″) for our time
spans. The test compares our 2000 → 2016 move of Barnard's Star with Gaia's own 2016 position and
requires less than 0.5″ difference.

`separation_arcsec`: the angle between two sky points (haversine formula, safe for small angles).
We use it to report "moved N arcsec since 2000" and in tests.

## 4. `resolve.py`: name → position
```python
for server in list(_servers):
    try:
        with conf.set_temp("server", server), conf.set_temp("timeout", TIMEOUT_SECONDS):
            simbad = Simbad()
            simbad.add_votable_fields("pmra", "pmdec")
            table = simbad.query_object(name)
    except Exception as exc:
        errors.append(...)
        continue
    _servers.remove(server); _servers.insert(0, server)
```
- Try each SIMBAD server with a 15-second timeout. `conf.set_temp` changes astroquery's
  settings only inside the `with` block.
- `add_votable_fields("pmra", "pmdec")`: ask for proper motion too (not returned by default).
- If a server fails, remember why and try the next one.
- The server that worked moves to the front of the list, so the next name does not wait 15 s for
  the dead server again. (Before this fix, the Day 1 report took ~10 minutes.)
- Empty answer → `LookupError` ("not found"). All servers dead → `ResolverUnavailable`.
  The website must show these as honest messages, not invent a position.
- `_value()`: SIMBAD has no proper motion for some objects; the value is then "masked" and we
  return `None` (unknown), never 0 by mistake.
- Column names: newer astroquery returns lowercase (`main_id`, `ra`, `dec`). `cols` maps them so
  the code works with either.

## 5. `targets.py`: the 5 official targets
A plain list of dictionaries: a key, a label, the name SIMBAD understands (for example
`"eps Ind B"`), the kind (`mover`, `cold`, `variable`) and a one-line "what to look for" that the
website can show. WISE 0855 also carries the position written in the challenge text as a backup if
SIMBAD is down.

## 6. `archive.py`: talk to NASA's archive
### `SpherexImage` (a dataclass)
One record per image: `obs_id` (one exposure), `did` (unique id of the image = exposure +
detector), `detector`, start/end time (MJD), wavelength range, release date, `collection`
(which release) and `path` (where the file lives, for the cutout service). `mjd` is the middle of
the exposure. Lesson on why each exposure gives 2 images (paired detectors D1+D4, D2+D5, D3+D6):
[`docs/learn/06_spherex.md`](../docs/learn/06_spherex.md).

### `_run(adql)`: ask with retries
Runs an ADQL query through pyvo. If IRSA drops the connection or sends a broken answer, wait
1 s, 2 s, 4 s, 8 s ("exponential backoff") and try again; after 4 tries raise `ArchiveError`.

### `find_images(ra, dec)`: which images contain this point?
```sql
SELECT obs_id, obs_publisher_did, obs_collection, energy_bandpassname, t_min, t_max, ...
FROM spherex.obscore
WHERE CONTAINS(POINT('ICRS', ra, dec), s_region) = 1
  AND obs_collection IN ('spherex_qr2', 'spherex_qr2_deep', 'spherex_qr3', 'spherex_qr3_deep')
```
- `spherex.obscore`: one row per SPHEREx image (standard "ObsCore" columns).
- `s_region`: the outline of the image on the sky. `CONTAINS(POINT, s_region) = 1` means "the
  point is inside the image". (Checking only the image centre, as an old prototype did, misses
  images where the star is near an edge.)
- `energy_bandpassname` is like `"SPHEREx-D3"`; `_detector_number` takes the number after the
  last "D".
- `em_min`/`em_max` are in **metres**; ×1e6 gives micrometres.
- Results are sorted by time, then detector.

### `attach_paths(images)`: where is each file?
The cutout service needs the file path, which is in a different table (`spherex.artifact`).
The archive gives an error ("st_covers does not exist") if we join that table inside a
`CONTAINS` search, so we do a **second query**: give it up to 200 image ids at a time
(`IN (...)`) and read back the paths. We remove the leading `ibe/data/` because the cutout service
expects the path without it (we learned this from a 404 error).

### `group_epochs(images, gap_days=30, max_span_days=60)`: visits
SPHEREx sees most of the sky in a visit of 2–7 weeks, then again ~6 months later. An **epoch** is
one visit. We walk through the images in time order and start a new epoch when:
- the gap since the previous image is more than 30 days, **or**
- the current epoch already lasts more than 60 days.

The second rule is for fields near the ecliptic poles (R Draconis), which SPHEREx sees almost
all the time; without it, a whole year becomes one "epoch". Each epoch gets an id, mean MJD,
date, image count and count per detector.

### `summarize(images)`: the numbers for the coverage table
Counts (images, exposures), first and last date, time span, per-detector and per-collection
counts, epochs, and the newest release date.

### `download_cutout(image, ra, dec, size_deg=0.05)`: one cutout
1. Cache: the file name is built from the image id + position + size (`cutout_file`). If the file
   is already on disk, return it: no download.
2. Ask `CUTOUT_URL?ra=..&dec=..&size=..&path=..`.
3. Accept only HTTP 200 **and** content starting with `SIMPLE` (every FITS file starts with that
   word). This catches error pages that come back with status 200.
4. HTTP 404 means "this position is not in this image" → `NotInImage` (no retry; retrying cannot
   help).
5. Write to `name.part`, then rename. If the program crashes mid-download, we never leave a
   half file that looks complete.
6. Other errors: wait and retry, up to 4 times.

`download_cutouts(...)`: many cutouts with a pool of 3 threads (IRSA's limit in practice).
Failures are returned per image instead of stopping everything.

### `describe_cutout(path)`: what is inside
Opens the FITS file with astropy and lists the extensions and their sizes, the observation time
`MJD-AVG` (the one to use), `DATE` (the **processing** date: never use it as observation time),
the detector, the units, the flag bit numbers, the % of bad pixels and the % of SOURCE-labelled
pixels.

## 6b. `flags.py`: which bit means which problem
The FLAGS layer stores one integer per pixel; bit n set = problem n. **The two releases write the
bit list differently** (we found this when the QR3 list came back empty):
- QR2: `MP_HOT = 10` (name in the keyword, bit number as the value).
- QR3: `MSKN0010 = 'HOT'` and `MSKM0010 = 1024` (= 1 << 10).

`flag_bits(header)` reads both and returns `{"HOT": 10, ...}`. If it finds neither, it raises
`NoFlagDefinitions`. That matters: an old prototype silently "kept everything" when it could not
read flags, so bad pixels looked like real stars.

`bad_pixel_bitmask(header)` builds one integer with all bad bits set (from `BAD_FLAG_NAMES`), so a
whole image is checked in one line: `bad = (flags & mask) != 0`. Names a release does not define
are skipped (QR2 has no GHOST flag, for example).

## 7. `scripts/day1_report.py`: run it all
For each target: resolve the name (fall back to the challenge position for WISE 0855 if SIMBAD
fails) → move to 2026.0 → `find_images` → `summarize` → download one sample cutout **per release**
(D6 for the cold brown dwarf, D2 otherwise) → `describe_cutout`. Writes
`cache/day1_report.json` (all details) and `notes/DAY1_REPORT.md` (tables).

Run it: `python -m scripts.day1_report` (from the repo root, venv active).

## 8. Tests
- `test_coords.py` (12): parsing in all formats, bad input raises, MJD conversions.
- `test_motion_archive.py`: Barnard's Star 2000 → 2016 matches Gaia within 0.5″; no motion
  = no move; RA wraps at 360; epoch splitting by gaps and by maximum length; detector names;
  cache file names stay the same.
- `test_flags.py` (4): reads the QR2 and QR3 header formats; the bad mask skips SOURCE and names
  a release does not define; a header without flag definitions raises an error.
- `test_network.py` (only with `RUN_NETWORK=1`, because it calls real servers): SIMBAD finds
  Barnard's Star; an unknown name raises `LookupError`; Barnard's Star has images in all 6
  detectors.

Run: `python -m pytest backend/tests -q` and `RUN_NETWORK=1 python -m pytest backend/tests/test_network.py -q`.
Last result (31 Oct): 24 passed offline, 3 passed online.

## Exercises (do these to really learn it)
1. Run `find_images` for your own favourite star. How many epochs? Which detectors?
2. Change `max_span_days` to 400 and rerun the R Dra part. What happens to the epochs? Why is
   that wrong for a flipbook?
3. Download one cutout and open it in `astropy.io.fits`. Print `hdul.info()` and find `MJD-AVG`.
4. Turn off the proper-motion move for Barnard's Star and make a 0.05° cutout at the J2000
   position. Is the star in the middle? (Tip: 270″ = 0.075°.)
