# Lesson 2 — When was it? Time in astronomy

> Goal of this lesson: you understand how astronomers write time, why they use
> "MJD", and which time inside a FITS file is the correct one.

---

## 2.1 Why time matters so much for us

We want to find objects that **move**. Speed is:

```
speed = distance moved / time taken
```

If the time is wrong, the speed is wrong, and a real asteroid can look like nonsense.

Real example from our own project:
our first report used the wrong date. It said file `2025W18_1B_0074_1` was from **2025-09-18**,
but the photo was actually taken on **2025-04-29**. That is almost **5 months wrong**!
(Step 1 of our work fixes this.)

---

## 2.2 Different clocks

You don't need all the details, only the idea: there are several "clocks" used in astronomy.

| Name | What it is | When you meet it |
|------|------------|------------------|
| **UTC** | Normal world clock (Nepal time = UTC + 5:45) | FITS headers, everyday |
| **TAI** | Atomic clock, no leap seconds | Rarely, inside software |
| **TDB** | Clock used for planet orbit calculations | JPL Horizons, orbits |

The differences are about a minute. For our work, Astropy converts between them automatically.
Our SPHEREx files say `TIMESYS = UTC`.

---

## 2.3 The problem with calendar dates

Try to calculate the number of days between **29 April 2025, 00:23** and **10 June 2026, 08:12**.

You must remember: days in each month, leap years, hours, minutes... Easy to make mistakes.

Astronomers solved this by **counting days** from one fixed starting moment.

---

## 2.4 Julian Date (JD) and Modified Julian Date (MJD)

- **Julian Date (JD)**: number of days since a moment in 4713 BC. Today's JD is about 2,461,000. Very big number.
- **Modified Julian Date (MJD)**: a shorter version.

```
MJD = JD − 2,400,000.5
```

MJD = 0 is **17 November 1858 at midnight (UTC)**. MJD counts days from then, with decimals for part of a day.

| Decimal part | Time of day |
|--------------|-------------|
| .00 | midnight 00:00 |
| .25 | 06:00 |
| .50 | 12:00 noon |
| .75 | 18:00 |

1 hour = 1/24 = **0.0417 day**. 1 minute = **0.000694 day**.

### Worked example with our real files

| File | MJD (middle of exposure) | Calendar date (UTC) |
|------|---------------------------|---------------------|
| 2025W18_1B_0074_1 | 60794.01616 | 2025-04-29 00:23 |
| 2026W24_1A_0511_2 | 61201.34208 | 2026-06-10 08:12 |

Days between them:

```
61201.34208 − 60794.01616 = 407.33 days
```

One subtraction. No calendar needed. That is why astronomers love MJD.

```python
from astropy.time import Time
t1 = Time(60794.01616, format="mjd")
t2 = Time(61201.34208, format="mjd")
print(t1.iso, t2.iso)        # 2025-04-29 00:23:16  2026-06-10 08:12:35
print((t2 - t1).jd)          # 407.33 days
```

---

## 2.5 Time inside a FITS file — which one is correct?

Our SPHEREx files contain many time keywords. Real values from `2025W18_1B_0074_1.fits`:

| Keyword | Value | Meaning | Use it? |
|---------|-------|---------|---------|
| `DATE` | 2025-09-18T04:30:02 | When the **file was created** (processing) | **NO** |
| `DATE-OBS` / `MJD-OBS` | 2025-04-29T00:22:19 / 60794.01550 | Start of the exposure | OK |
| `DATE-BEG` / `MJD-BEG` | same as above | Start of exposure | OK |
| `DATE-AVG` / `MJD-AVG` | 2025-04-29T00:23:17 / 60794.01616 | **Middle** of exposure | **BEST** |
| `DATE-END` / `MJD-END` | 2025-04-29T00:24:14 / 60794.01683 | End of exposure | OK |

The exposure lasted from 00:22:19 to 00:24:14, about **115 seconds**.

### Why the middle (`MJD-AVG`)?

A moving object keeps moving during the exposure. Its measured position is an average over the exposure,
so it matches the **middle time** best.

---

## 2.6 How big is the error if time is wrong?

A typical main-belt asteroid moves about **30″ per hour** on the sky.

- 1 minute time error → 30″ / 60 = **0.5″** position error (small, OK).
- 5 months time error → completely wrong object location (our old bug!).

For Planet X at 500 AU (moves ~7″ per **day**), small time errors hardly matter —
but wrong dates still destroy everything.

---

## 2.7 Summary

- Astronomy uses **UTC** for observations and other clocks for orbits; Astropy converts.
- **MJD** = days counted since 1858-11-17. Differences of MJD = days between events.
- In FITS files, `DATE` = file creation. Use **`MJD-AVG`** (middle of exposure) for science.
- Our SPHEREx exposures last about **115 s**.

## 2.8 Self-check

1. Why do astronomers use MJD instead of calendar dates?
2. What time of day is MJD 60830.75? (18:00 UTC)
3. Why is `DATE` the wrong keyword for observation time?
4. Why use the middle of the exposure for a moving object?
5. An asteroid moves 30″/hour. If time is wrong by 10 minutes, what is the position error? (5″ ≈ 0.8 pixel)

## 2.9 Try it yourself

```python
from astropy.io import fits
h = fits.open("data/raw/2025W18_1B_0074_1.fits")
hdr = h["IMAGE"].header
print(hdr["DATE"], hdr["DATE-OBS"], hdr["MJD-AVG"])
```
