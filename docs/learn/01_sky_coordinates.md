# Lesson 1 — Where is it? Sky coordinates and angles

> Goal of this lesson: you can describe any point on the sky with two numbers,
> and you can measure how far apart two points are.

---

## 1.1 The big idea: the sky as a giant ball

When you look up at night, all stars seem stuck on the inside of a huge ball around the Earth.
They are really at very different distances, but **for describing directions**, we pretend they are all painted on one ball.

Astronomers call this imaginary ball the **celestial sphere**.

```
            North Celestial Pole (above Earth's North Pole)
                        *
                    .-"   "-.
                  /           \
                 |   (Earth)   |  <- celestial equator (Earth's equator projected on the sky)
                  \           /
                    "-.___.-"
                        *
            South Celestial Pole
```

We do not care (yet) how far away an object is. We only care **in which direction** it is.
A direction on a ball needs **two numbers** — exactly like a place on Earth needs latitude and longitude.

---

## 1.2 Latitude and longitude on Earth (you already know this)

- **Latitude**: how far north or south of the equator. Kathmandu ≈ 27.7° North.
- **Longitude**: how far east or west around the Earth. Kathmandu ≈ 85.3° East.

The sky uses the same idea, with different names.

---

## 1.3 Right Ascension (RA) and Declination (Dec)

| Earth | Sky | Range |
|-------|-----|-------|
| Latitude | **Declination (Dec)** | −90° (south pole) to +90° (north pole) |
| Longitude | **Right Ascension (RA)** | 0° to 360° around the sky |

- **Dec = 0°** is the celestial equator (directly above Earth's equator).
- **Dec = +90°** is the north celestial pole (almost where the Pole Star is).
- **RA** goes around the sky like longitude goes around the Earth.

### RA in hours (old style)

Older books write RA in **hours**, because the sky seems to turn once every 24 hours.

- 24 hours = 360°
- so **1 hour = 15°**

Example: RA = 20h 18m ≈ 20.31 h × 15 = 304.6°.
In our project we always use **degrees**, so write `ra_deg`.

### Our project's sky position

Our current SPHEREx field is at:

- **RA = 304.69°**
- **Dec = +42.44°**

That is in the constellation **Cygnus (the Swan)**, in the northern sky.

---

## 1.4 Measuring angles: degrees, arcminutes, arcseconds

Objects on the sky are measured by **angle**, not by km, because we usually do not know the distance.

- 1 full circle = **360°**
- 1 degree = **60 arcminutes** (written 60′)
- 1 arcminute = **60 arcseconds** (written 60″)
- so **1° = 3600″**

How big are these?

| Thing | Angle |
|-------|-------|
| Full Moon | ~0.5° = 30′ = 1800″ |
| Your little finger at arm's length | ~1° |
| One SPHEREx pixel | **6.15″** (we measured this from our file) |
| One SPHEREx detector image (2040 pixels wide) | 2040 × 6.15″ ≈ 12,550″ ≈ **3.5°** (7 full Moons!) |
| Best ground telescopes can separate | ~0.5–1″ |

**Useful conversion to remember:**

> 1 radian = 206,265 arcseconds

You will use this for the small-angle formula below and later for parallax.

---

## 1.5 A trap: why you cannot just subtract RA

On Earth, the lines of longitude **come together at the poles**.
At the equator, 1° of longitude ≈ 111 km. Near the North Pole, 1° of longitude is almost 0 km.

The sky is the same. A difference in RA gives a **smaller real angle** when you are far from the equator.

The correction factor is **cos(Dec)**:

```
real east–west angle = ΔRA × cos(Dec)
```

At our field, Dec = 42.44°, so cos(42.44°) = 0.738.
A difference of 1° in RA is only **0.738°** of real angle on the sky.

---

## 1.6 How far apart are two points? (angular separation)

For two nearby points (less than a few degrees apart), use this simple formula:

```
Δx = ΔRA × cos(Dec)        (east–west)
Δy = ΔDec                   (north–south)
separation ≈ √(Δx² + Δy²)
```

### Worked example (real numbers)

Point A: RA = 304.6935°, Dec = 42.4437° (our field centre)
Point B: RA = 304.7000°, Dec = 42.4500°

1. ΔRA = 304.7000 − 304.6935 = 0.0065°
2. Δx = 0.0065° × 0.738 = 0.0048° → × 3600 = **17.3″**
3. ΔDec = 42.4500 − 42.4437 = 0.0063° → × 3600 = **22.7″**
4. separation = √(17.3² + 22.7²) = √(299 + 515) = √814 ≈ **28.5″**

Astropy gives exactly **28.53″**. So the two points are about **4.6 SPHEREx pixels** apart (28.5 / 6.15).

For large separations the simple formula becomes wrong, so in code we always let Astropy do it:

```python
from astropy.coordinates import SkyCoord
import astropy.units as u

a = SkyCoord(304.6935 * u.deg, 42.4437 * u.deg)
b = SkyCoord(304.7000 * u.deg, 42.4500 * u.deg)
print(a.separation(b).arcsec)   # 28.53
```

---

## 1.7 The small-angle formula (connects angle and real size)

If an object of real size **D** is at distance **d**, and the angle is small:

```
angle (radians) = D / d
angle (arcsec)  = 206265 × D / d
```

Example: the Moon, D = 3474 km, d = 384,400 km
angle = 206265 × 3474 / 384400 ≈ 1864″ ≈ 0.52°. Correct — about half a degree.

We will use the same formula later to understand how fast Planet X appears to move.

---

## 1.8 Three important "planes" on the sky

1. **Celestial equator** — Earth's equator projected on the sky (Dec = 0°).
2. **Ecliptic** — the path of the Sun across the sky during the year. It is also the **plane of the Solar System**, so the planets and most **asteroids** are found near it.
3. **Galactic plane** — the disc of our Milky Way galaxy. **Very crowded with stars** and dust.

Astropy can convert our field into these other systems. Real result for our field:

| System | Latitude of our field |
|--------|------------------------|
| Ecliptic latitude | **+59.4°** (far from the ecliptic) |
| Galactic latitude | **+3.6°** (almost inside the Milky Way plane) |

**What this means for our project:**

- Far from the ecliptic → **few asteroids** pass through this field.
- Near the galactic plane → **very many stars** (crowded).

That is why the plan adds a **second field near the ecliptic** for asteroid hunting.

```python
c = SkyCoord(304.6935 * u.deg, 42.4437 * u.deg)
print(c.barycentrictrueecliptic.lat.deg)   # ~ 59.4
print(c.galactic.b.deg)                    # ~ 3.6
```

---

## 1.9 Summary

- A sky direction = **two angles**: RA (0–360°) and Dec (−90° to +90°).
- **1° = 60′ = 3600″**; one SPHEREx pixel = **6.15″**.
- East–west angle = **ΔRA × cos(Dec)** — never subtract RA directly.
- Small angles: **angle(″) = 206265 × size / distance**.
- Asteroids live near the **ecliptic**; stars crowd the **galactic plane**.

## 1.10 Self-check (write answers in your own words)

1. Why is 1° of RA smaller on the sky near the pole than at the equator?
2. How many SPHEREx pixels is 1 arcminute? (Answer: 60 / 6.15 ≈ 9.8)
3. Why do we expect few asteroids in our current field?
4. Two stars are 0.01° apart in Dec only. How many arcseconds is that? (36″)
5. An object moves 60″ on the sky. How many SPHEREx pixels did it move? (~9.8)

## 1.11 Try it yourself

In the project folder:

```bash
source .venv/bin/activate
python
```

Then type the `SkyCoord` examples above and check you get the same numbers.
