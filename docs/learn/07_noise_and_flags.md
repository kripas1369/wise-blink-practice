# Lesson 7 — Is it real? Noise, variance, flags and artifacts

> Goal of this lesson: you understand why most "changes" in images are fake,
> how noise is measured (VARIANCE), and how to read the warning bits (FLAGS).

---

## 7.1 Why this matters

When you subtract two images, you will see thousands of little spots.
**Almost all of them are not real astronomical changes.** They are:

- random **noise**,
- **bad pixels** on the detector,
- **cosmic rays** (particles from space hitting the detector),
- **ghosts** and reflections from bright stars,
- leftover signal from a previous exposure (**persistence**).

A good scientist's job is to **remove all these** before saying "something changed". This lesson gives you the tools.

---

## 7.2 How a detector pixel works (simple)

Each pixel is like a small **bucket collecting rain**. Light particles (photons) hit the pixel and create electric charge.
After the exposure (~115 s for SPHEREx), the electronics **read** how much charge is in each bucket.

More light → more charge → higher number in the IMAGE.

---

## 7.3 Where does noise come from?

1. **Photon noise (shot noise)** — light arrives randomly, like raindrops. If you expect N photons, you actually get N ± √N.
   Example: expect 100 → you get about 100 ± 10.
2. **Read noise** — the electronics add a small random error when reading.
3. **Dark current** — heat creates a little charge even with no light (SPHEREx is cooled very cold to reduce this).
4. **Background** — zodiacal light and other sky glow add photons (and their noise).

---

## 7.4 Variance and standard deviation

- **Standard deviation (σ, sigma)** = typical size of the random error.
- **Variance = σ²** (sigma squared).

Why use variance? Because **variances add** when you combine measurements:

```
if C = A − B  (or A + B), and A and B are independent:
variance(C) = variance(A) + variance(B)
σ_C = √(σ_A² + σ_B²)
```

### Worked example

Pixel in image A: σ_A = 2. Same place in image B: σ_B = 3.

```
σ(A − B) = √(4 + 9) = √13 ≈ 3.6
```

So the difference is **noisier than either image**. A difference of 5 is only 5 / 3.6 = 1.4σ — not significant!

### SPHEREx gives us the variance for every pixel

The `VARIANCE` HDU (unit (MJy/sr)²). Real numbers from our file:

- typical √VARIANCE (noise) per pixel ≈ **0.025 MJy/sr**
- typical sky brightness ≈ **0.458 MJy/sr**

So for each difference we can compute a proper **significance**:

```
significance = (B − A) / √(var_A + var_B)
```

Our old prototype did **not** use VARIANCE (it estimated noise from the whole difference image). Step 4 of our plan fixes this.

---

## 7.5 Bits and bit flags (how one number stores many yes/no answers)

Computers store whole numbers in **binary** (base 2): only 0s and 1s.
Each position (bit) is a power of 2:

```
bit:     ...  11    10   ...   2    1    0
value:  ... 2048  1024  ...   4    2    1
```

A **flag number** uses each bit as a **yes/no switch**.
Example: flag value **1025** = 1024 + 1 → bit 10 is ON and bit 0 is ON, all others OFF.

### How to test a bit in Python

```python
flag = 1025
bit = 10
is_set = (flag >> bit) & 1    # 1 = yes, 0 = no
# or:
is_set = (flag & (1 << bit)) != 0
```

`>>` shifts the bits right; `& 1` keeps only the last bit.

---

## 7.6 SPHEREx FLAGS — real list from our file

Each pixel of the `FLAGS` image is such a number. The header tells which bit means what.
Real list from `2025W23_1C_0543_1.fits`, with the **percentage of pixels** that have each bit set:

| Bit | Name | Meaning (from header) | % pixels |
|-----|------|------------------------|----------|
| 0 | `MP_TRANSIENT` | Transient (e.g. cosmic ray) detected during readout | 3.23% |
| 1 | `MP_OVERFLOW` | Pixel overflowed (too much light) | 0.05% |
| 2 | `MP_SUR_ERROR` | Error in onboard processing | 2.47% |
| 4 | `MP_PHANTOM` | Phantom pixel | 0.00% |
| 5 | `MP_REFERENCE` | Reference pixel | 0.00% |
| 6 | `MP_NONFUNC` | Permanently unusable | 0.05% |
| 7 | `MP_DICHROIC` | Low efficiency due to dichroic | 0.00% |
| 9 | `MP_MISSING_DATA` | Onboard data lost | 0.00% |
| 10 | `MP_HOT` | Hot pixel (always too bright) | 0.00% |
| 11 | `MP_COLD` | Anomalously low signal | 0.04% |
| 12 | `MP_FULLSAMPLE` | Full sample history available (information) | 0.01% |
| 14 | `MP_PHANMISS` | Phantom correction not applied | 0.00% |
| 15 | `MP_NONLINEAR` | Nonlinearity correction unreliable | 0.00% |
| 17 | `MP_PERSIST` | Leftover charge from earlier bright light | 0.10% |
| 19 | `MP_OUTLIER` | Flagged as outlier | 0.33% |
| 21 | `MP_SOURCE` | **Pixel belongs to a known source (star/galaxy)** | **93.49%** |

Another file (`2026W24`) also has: `MP_GHOST`, `MP_GHOST_FPA`, `MP_GHOST_EXT`, `MP_BLOOM`, `MP_SNOWBALL`, `MP_HALO`. Flag lists can differ between files → **always read names from the header**, never hard-code them.

### Big lesson: not all flags mean "bad"

Only **6%** of pixels have flag value 0 (no bits set). Why? Because **93.5%** have `MP_SOURCE` —
this only means "a known star/galaxy covers this pixel" (in a crowded Milky Way field, almost everything). That is **information**, not a problem.

So we need **named rules**, for example:

| Group | Bits | What to do |
|-------|------|------------|
| Unusable | NONFUNC, MISSING_DATA, OVERFLOW, HOT, COLD | Always reject |
| Suspicious | TRANSIENT, OUTLIER, PERSIST, GHOST*, SNOWBALL, BLOOM, HALO, SUR_ERROR, NONLINEAR | Reject detections here, or mark "artifact risk" |
| Information | SOURCE, FULLSAMPLE | Keep — use for understanding |

(Our old code rejected every non-zero flag, noticed that left only 6% of pixels, and then ignored flags completely. Neither is right.)

### Decoding a real value

Our file contains the value **2053**:
2053 = 2048 + 4 + 1 → bits **11, 2, 0** → `MP_COLD` + `MP_SUR_ERROR` + `MP_TRANSIENT`. Suspicious pixel!

---

## 7.7 Common artifacts that look like real objects

| Artifact | What it is | How it can fool us | Defence |
|----------|-----------|--------------------|---------|
| **Cosmic ray** | Particle hits the detector | Bright dot in only **one** image → looks like something appeared | `MP_TRANSIENT`; require detection in several images |
| **Hot pixel** | Pixel always too bright | A "star" that stays at the same **detector** position | `MP_HOT`; check detector position |
| **Persistence** | Leftover charge after a bright star | Faint "ghost star" in the next exposure | `MP_PERSIST` |
| **Ghost / halo** | Reflections inside the optics | Faint copies near bright stars | `MP_GHOST*`, `MP_HALO` |
| **Snowball** | Big energy hit making a round blob | Round "object" in one image | `MP_SNOWBALL` |
| **Noise peak** | Random fluctuation | Many 3–4σ spots anywhere | Use proper σ from VARIANCE; statistics (Lesson 14) |
| **Edge effects** | Detector edges behave worse | Fake detections at borders | Avoid edges |
| **Bad alignment** | WCS slightly wrong | "+/−" pairs around every star | Check residuals of stars |
| **Colour effect (SPHEREx!)** | Different wavelength per row | Fake brightness changes | Compare at similar wavelength (Lesson 6) |

**Golden rule:** a real moving object must appear in **several** exposures, at positions that fall on a **straight, sensible path**, with a **sensible brightness**. Artifacts almost never do that.

---

## 7.8 Summary

- Most changes in difference images are **fake**; removing them is the real work.
- Noise sources: photon noise (√N), read noise, dark current, background.
- **Variances add**: σ(A − B) = √(σ_A² + σ_B²). SPHEREx gives variance for every pixel.
- **Flags** store many yes/no warnings as bits; test with `(flag >> bit) & 1`.
- Not all flags are bad: `MP_SOURCE` (93.5% of pixels) is information.
- Real objects repeat and move sensibly; artifacts usually do not.

## 7.9 Self-check

1. If pixel A has variance 4 and pixel B variance 9, what is the noise of A − B? (√13 ≈ 3.6)
2. How do you test whether bit 10 (`MP_HOT`) is set in a flag value?
3. Decode the flag value 131077. (131072 + 4 + 1 → bits 17, 2, 0 → PERSIST, SUR_ERROR, TRANSIENT)
4. Why is rejecting every pixel with a non-zero flag a mistake for SPHEREx?
5. Name three artifacts that can look like a moving object, and one defence for each.

## 7.10 Try it yourself

```python
from astropy.io import fits
import numpy as np
with fits.open("data/raw/2025W23_1C_0543_1.fits") as h:
    flags = h["FLAGS"].data.astype(np.int64)
    hdr = h["FLAGS"].header
    for key in hdr:
        if key.startswith("MP_"):
            bit = hdr[key]
            pct = 100 * ((flags >> bit) & 1).mean()
            print(f"{key:16s} bit {bit:2d}  {pct:6.2f}%")
```

Then run it on `2026W24_1A_0511_2.fits` and compare: which new flags appear?
