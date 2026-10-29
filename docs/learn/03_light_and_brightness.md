# Lesson 3 — How bright is it? Light, wavelength, flux and magnitude

> Goal of this lesson: you understand what SPHEREx measures (light at different
> wavelengths), how brightness is written (Jansky, MJy/sr, magnitudes), and why
> Planet X is so hard to see.

---

## 3.1 Light is a wave, and wavelength = colour

Light travels as waves. The distance from one wave top to the next is the **wavelength**, written **λ** (lambda).

```
  /\    /\    /\
 /  \  /  \  /  \        <- one wavelength = distance between two tops
/    \/    \/    \
```

Different wavelengths = different "colours". Most of them our eyes cannot see.

We measure wavelength in **micrometres (µm)**: 1 µm = one millionth of a metre = 0.001 mm.

| Name | Wavelength | Can eyes see? |
|------|------------|---------------|
| Ultraviolet | < 0.4 µm | No |
| **Visible light** (violet → red) | 0.4 – 0.7 µm | **Yes** |
| **Near-infrared** | 0.7 – 5 µm | No — **SPHEREx works here: 0.75 – 5 µm** |
| Mid-infrared | 5 – 30 µm | No (heat of room-temperature things) |
| Far-infrared | 30 – 300 µm | No (heat of very cold things) |
| Radio | mm to km | No |

---

## 3.2 Why does everything glow? (temperature and colour)

Every object glows because of its temperature. Hotter = shorter wavelength.

**Wien's law** gives the wavelength where an object glows the most:

```
λ_peak (µm) = 2898 / T (Kelvin)
```

| Object | Temperature | Peak wavelength | Region |
|--------|-------------|------------------|--------|
| Sun | 5,800 K | 2898 / 5800 = **0.5 µm** | visible (yellow-green) |
| Human body / Earth | ~300 K | ~**10 µm** | mid-infrared |
| Planet X (if ~40 K) | 40 K | 2898 / 40 = **72 µm** | far-infrared |

**Important for us:**

- A cold distant planet glows by itself only in the **far-infrared** (not SPHEREx).
- In SPHEREx's **near-infrared**, we would only see **sunlight reflected** by it — and that is extremely weak.

That is why an earlier study (Phan et al. 2025) searched for Planet X with **far-infrared** satellites (IRAS, AKARI).

---

## 3.3 Two ways light reaches us from a Solar System object

1. **Reflected sunlight** — like the Moon. Main light from asteroids in SPHEREx's short wavelengths.
2. **Thermal (heat) glow** — the object's own warmth. Near asteroids (warm, ~200 K) glow at the long end of SPHEREx (above ~3.5 µm).

For distant cold objects, only (1) matters in SPHEREx data.

---

## 3.4 Brightness: flux and the Jansky

**Flux** = how much light energy arrives at our telescope, per second, per square metre.

Astronomers use a special unit, the **Jansky (Jy)**:

```
1 Jy = 10⁻²⁶ watts per square metre per hertz
```

That is a tiny amount of energy. Useful sizes:

- 1 **mJy** (milli-Jansky) = 0.001 Jy
- 1 **µJy** (micro-Jansky) = 0.000001 Jy
- 1 **MJy** (mega-Jansky) = 1,000,000 Jy

---

## 3.5 Surface brightness: MJy/sr (the unit in our SPHEREx images)

Our SPHEREx image header says: `BUNIT = MJy / sr`.

- **sr** = **steradian**, a unit of **area on the sky** (like "square degrees", but in radians).
- **MJy/sr** = how much flux falls on each piece of sky area.

Why? SPHEREx also measures smooth, spread-out light (like zodiacal dust glow), not only point stars.
So it measures "brightness per sky area", like measuring rain "per square metre".

### From MJy/sr to flux in one pixel (worked example)

One SPHEREx pixel = 6.15″ × 6.15″. Convert to radians: 6.15 / 206265 = 2.98 × 10⁻⁵ rad.

```
pixel area = (2.98 × 10⁻⁵)² = 8.9 × 10⁻¹⁰ sr
```

So a pixel with brightness **1 MJy/sr** receives:

```
1,000,000 Jy/sr × 8.9 × 10⁻¹⁰ sr = 0.00089 Jy = 0.89 mJy
```

Real numbers from our file `2025W23_1C_0543_1.fits`:

| Quantity | Typical (median) value |
|----------|--------------------------|
| Sky brightness (IMAGE) | 0.458 MJy/sr |
| Noise per pixel (√VARIANCE) | 0.025 MJy/sr → ≈ 22 µJy per pixel |
| Zodiacal light model (ZODI) | 0.101 MJy/sr |

---

## 3.6 Magnitudes: the old, backwards scale

Before electronics, the Greek astronomer Hipparchus ranked stars from "1st magnitude" (brightest)
to "6th magnitude" (faintest visible). We still use this system today.

Rules:

1. **Bigger number = fainter.** Mag 20 is fainter than mag 10.
2. **5 magnitudes = exactly 100× in brightness.**
3. So **1 magnitude = 2.512×** (because 2.512⁵ = 100).

| Magnitude difference | Brightness ratio |
|----------------------|-------------------|
| 1 | 2.5× |
| 2.5 | 10× |
| 5 | 100× |
| 10 | 10,000× |

Examples: Sirius (brightest star) ≈ −1.5; faintest naked-eye star ≈ 6; **Planet Nine prediction ≈ 20.6 – 23.1**.

### AB magnitude (connects magnitudes to Jansky)

```
m_AB = −2.5 × log10( flux / 3631 Jy )
```

Worked example: SPHEREx depth ~ **19.5 AB mag**. What flux is that?

```
flux = 3631 × 10^(−19.5 / 2.5) = 3631 × 10^(−7.8) ≈ 0.0000575 Jy = 57.5 µJy
```

---

## 3.7 Noise and signal-to-noise ratio (SNR)

Every measurement has random "jitter" called **noise**. Like trying to hear a whisper in a noisy room.

- **Signal** = the light from the object.
- **Noise (σ, sigma)** = the typical random error.
- **SNR = signal / noise**.

| SNR | Meaning |
|-----|---------|
| 1 | Cannot tell object from noise |
| 3 | Maybe something |
| **5** | Standard "detected" threshold ("5σ detection") |
| 100 | Very clear, precise measurement |

**"5σ depth of 19.5 mag"** means: an object of magnitude 19.5 is measured with SNR = 5.
Fainter objects are lost in the noise.

---

## 3.8 Why is Planet X so faint? (the 1/distance⁴ rule)

Sunlight must travel **to** the planet and then the reflection travels **back** to us.

1. Light from the Sun spreads out: at distance d, it is weaker by **1/d²** (inverse-square law).
2. The reflected light spreads out again on the way back: another **1/d²**.

For a distant object (Sun and Earth nearly the same distance from it):

```
reflected brightness ∝ 1 / d⁴
```

- 2× farther → 2⁴ = **16× fainter**
- 10× farther → 10,000× fainter
- An object at 500 AU vs the same object at 1 AU → 500⁴ = **62.5 billion times fainter**

### Can SPHEREx see Planet Nine? (rough, simple estimate)

- SPHEREx limit ≈ **19.5 mag**
- Planet Nine prediction ≈ **22** (middle of 20.6 – 23.1)
- Difference = 2.5 mag → Planet Nine is about **10× fainter** than SPHEREx's limit

(This is a rough comparison. The prediction uses visible "V" magnitudes and SPHEREx measures near-infrared AB magnitudes; in week 3 we will do it properly with injection tests.)

Conclusion: **typical Planet Nine predictions are probably too faint for SPHEREx**, but brighter/closer versions might not be. Measuring exactly where that limit is — that is our Planet X result.

---

## 3.9 Summary

- Wavelength = colour; SPHEREx sees **0.75 – 5 µm** (near-infrared).
- Hot things glow at short wavelengths (Wien's law); cold Planet X glows in far-infrared.
- Flux unit: **Jansky**. SPHEREx images: **MJy/sr** (brightness per sky area).
- **Magnitudes**: bigger = fainter; 5 mag = 100×.
- **SNR = signal / noise**; "detected" usually means SNR ≥ 5.
- Reflected light from distant objects falls as **1/d⁴** — the reason Planet X is hidden.

## 3.10 Self-check

1. What does "5σ depth of 19.5 mag" mean in simple words?
2. A star is mag 15, another mag 20. Which is brighter and by how much? (mag 15, 100×)
3. Why does a planet 2× farther look about 16× fainter in reflected light?
4. Why is a 40 K planet bright in far-infrared but dark in near-infrared?
5. What is the unit of our SPHEREx IMAGE, and why is it "per steradian"?

## 3.11 Try it yourself

```python
import numpy as np
# AB magnitude -> flux
for m in [15, 19.5, 22]:
    print(m, 3631 * 10 ** (-m / 2.5) * 1e6, "microJy")
# Wien's law
for T in [5800, 300, 40]:
    print(T, "K ->", 2898 / T, "um")
```
