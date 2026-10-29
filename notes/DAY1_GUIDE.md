# Day 1 guide (Thu 29 Oct): coordinates and time

## Kripas

### 1. Read (about 45 min)
- `docs/learn/01_sky_coordinates.md`
- `docs/learn/02_time.md`

You should be able to answer:
- What are RA and Dec? Why is RA written in hours (1h = 15°)?
- What is the difference between `08h55m10.8s` and `133.795°`?
- What is MJD, and why do astronomers count days instead of using calendar dates?

### 2. The task: write `backend/app/coords.py` yourself
Every later step (search box, archive query, Gaia, flipbook labels) starts here, so it must never guess.

Write three functions:

1. **`parse_coordinates(text: str) -> tuple[float, float]`**
   - Returns `(ra_deg, dec_deg)`.
   - Must accept:
     - letters: `"08h55m10.831s -07d14m42.53s"`
     - colons: `"08:55:10.831 -07:14:42.53"` (RA in hours, Dec in degrees)
     - decimal degrees: `"133.795 -7.245"`
   - Must **raise `ValueError`** for empty text, words, one number only, RA outside 0–360, or Dec outside −90 to +90.
   - Hint: `astropy.coordinates.SkyCoord` can parse these, but you must tell it the units. Decimal numbers are degrees; sexagesimal RA is hours (`unit=(u.hourangle, u.deg)`). How can you tell which kind of text you got?
   - Hint: wrap astropy's errors and raise your own `ValueError` with a clear message.

2. **`date_to_mjd(date: str) -> float`**
   - `"2026-10-29"` gives `61342.0`, and `"2000-01-01T12:00:00"` gives `51544.5`.
   - Hint: `astropy.time.Time`.

3. **`mjd_to_date(mjd: float) -> str`**
   - Returns ISO text such as `"2023-02-25T00:00:00.000"`.
   - Hint: `Time(..., format="mjd")` and `.isot`.

### 3. Check your work
```bash
cd ~/wise-blink-practice
source .venv/bin/activate
python -m pytest backend/tests/test_coords.py -v
```
All 12 tests must pass. **Do not edit the tests to make them pass.** If you think a test is wrong, ask.

### 4. Review
Tell the AI "review Day 1". It will read your `coords.py` and point out bugs, astronomy mistakes and cleaner ways.

### 5. Finish
- Fill in Day 1 in `notes/LEARNING_LOG.md`.
- Commit: `git add -A && git commit -m "Day 1: coords.py"` then `git push`.

---

## [Friend's name]

### 1. Read
- `docs/plan/HACKATHON_PLAN.md` and `docs/plan/FRIEND_PLAN.md`; lessons `docs/learn/01_sky_coordinates.md` and `docs/learn/06_spherex.md`.
- Write the 5 story beats (Part F) in your own words.

### 2. Build `frontend/index.html` (plain HTML + JS, no framework)
- A text box for RA/Dec or a name, a field-of-view number box (arcminutes, default 3), and a "Go" button.
- On page load, read `?ra=..&dec=..&fov=..` from the URL and fill the boxes.
- When "Go" is pressed, update the URL (without reloading) so the link can be copied and shared.
- Hint: `new URLSearchParams(window.location.search)` and `history.replaceState`.

### 3. Done when
Opening `frontend/index.html?ra=133.795&dec=-7.245&fov=5` fills the boxes, and pressing Go after changing them updates the address bar.

### 4. Finish
Learning log entry, commit, push.
