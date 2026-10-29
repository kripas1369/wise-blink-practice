# Lesson 4 — What is inside the file? FITS

> Goal of this lesson: you can open a SPHEREx FITS file, list its parts, read its
> headers, and understand what each part is for.

---

## 4.1 What is FITS?

**FITS** = **F**lexible **I**mage **T**ransport **S**ystem.
It is the standard file format of astronomy since 1981. NASA, ESA, all big telescopes use it.

Think of a normal photo file (JPG/PNG): it stores colours for your screen.
A FITS file stores **scientific measurements** plus a **text description** of how they were measured.

| JPG photo | FITS file |
|-----------|-----------|
| 8-bit colour values (0–255) | Real physical numbers (e.g. 0.458 MJy/sr), can be negative |
| Little information about the camera | Hundreds of lines describing time, position, detector, units |
| One picture | Many pictures and tables in one file |

---

## 4.2 HDU = Header + Data Unit

A FITS file is like a **box with several drawers**. Each drawer is called an **HDU**.

Each HDU has two parts:

1. **Header** — text "labels", like the label on a drawer: what is inside, units, time, etc.
2. **Data** — the actual numbers (an image, a 3D cube, or a table).

```
FITS FILE
├── HDU 0  (Primary)   header + (maybe) data
├── HDU 1              header + data
├── HDU 2              header + data
└── ...
```

A file with many HDUs is called a **Multi-Extension FITS (MEF)**. SPHEREx files are MEF.

---

## 4.3 The three kinds of HDU

| Type | Contains | Example in SPHEREx |
|------|----------|--------------------|
| **PrimaryHDU** | The first HDU; often only a header | `PRIMARY` (header only) |
| **ImageHDU** | A grid of numbers (2D image or 3D cube) | `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `PSF` |
| **BinTableHDU** | A table with rows and columns | `WCS-WAVE` |

---

## 4.4 Our real SPHEREx file

Output of `hdul.info()` for `data/raw/2025W23_1C_0543_1.fits`:

```
No.  Name      Type          Dimensions       Format
 0   PRIMARY   PrimaryHDU    ()
 1   IMAGE     ImageHDU      (2040, 2040)     float32
 2   FLAGS     ImageHDU      (2040, 2040)     int32
 3   VARIANCE  ImageHDU      (2040, 2040)     float32
 4   ZODI      ImageHDU      (2040, 2040)     float32
 5   PSF       ImageHDU      (101, 101, 121)  float32
 6   WCS-WAVE  BinTableHDU   1 row x 3 columns
```

What each one means (simple words; details in Lessons 5–7):

| HDU | Simple meaning | Unit |
|-----|----------------|------|
| `PRIMARY` | Cover page (almost empty) | – |
| `IMAGE` | **The sky picture**: brightness of each pixel | MJy/sr |
| `FLAGS` | For each pixel, a number whose bits say "warnings" (bad pixel, cosmic ray, star here...) | bits |
| `VARIANCE` | For each pixel, how uncertain the brightness is (noise²) | (MJy/sr)² |
| `ZODI` | Model of the glow from Solar System dust (zodiacal light) | MJy/sr |
| `PSF` | 121 small pictures showing how a point of light spreads out on the detector | – |
| `WCS-WAVE` | Table giving the **wavelength** seen by each part of the detector | µm |

---

## 4.5 The header: "cards" of text

A header is made of lines called **cards**. Each card is exactly **80 characters**:

```
KEYWORD = value / comment
```

Real cards from our IMAGE header:

```
NAXIS   =                    2 / number of data axes
NAXIS1  =                 2040 / width  (x)
NAXIS2  =                 2040 / height (y)
BUNIT   = 'MJy / sr'           / unit of the data
DETECTOR=                    1
MJD-AVG =      60830.841087034 / middle of exposure
CTYPE1  = 'RA---TAN-SIP'       / sky projection (Lesson 5)
```

Important keywords:

| Keyword | Meaning |
|---------|---------|
| `NAXIS` | Number of dimensions (2 = image, 3 = cube) |
| `NAXIS1` | Size along x (width) |
| `NAXIS2` | Size along y (height) |
| `BUNIT` | Unit of the numbers |
| `EXTNAME` | Name of the HDU (e.g. `IMAGE`) |
| `BITPIX` | Number type (−32 = 32-bit decimal "float", 32 = 32-bit whole number "int") |

**Always look up HDUs by name** (`hdul["IMAGE"]`), not by number — the order can differ between data releases.

---

## 4.6 A trap: x/y order in Python

FITS says `NAXIS1` = x (width), `NAXIS2` = y (height).
But **NumPy stores arrays as [row, column] = [y, x]**.

```python
data = hdul["IMAGE"].data
data.shape        # (2040, 2040)  = (NAXIS2, NAXIS1) = (y, x)
value = data[y, x]   # NOT data[x, y]
```

Our images are square, so the shape looks the same — but the order still matters!
For the PSF cube, FITS says (101, 101, 121) but NumPy gives shape **(121, 101, 101)** = (which PSF, y, x).

Another trap: FITS counts pixels starting from **1**, Python from **0**. (More in Lesson 5.)

---

## 4.7 How big is the file, and why?

Our file is **71,634,240 bytes** (~72 MB).

- One 2040 × 2040 layer of 4-byte numbers = 2040 × 2040 × 4 = **16.6 MB**
- IMAGE + FLAGS + VARIANCE + ZODI = 4 × 16.6 = **66.6 MB**
- PSF cube = 101 × 101 × 121 × 4 = **4.9 MB**
- Headers + table = small
- Total ≈ **71.6 MB** ✔

Fun fact: FITS files are stored in blocks of exactly **2880 bytes**. 71,634,240 / 2880 = **24,873** blocks exactly.

Because files are big, astronomers use:

- **memory mapping** (`memmap=True`) — read only the part you need,
- **cutouts** — download only a small sky region instead of the full file.

---

## 4.8 Python: opening a FITS file step by step

```python
from astropy.io import fits

path = "data/raw/2025W23_1C_0543_1.fits"

with fits.open(path) as hdul:          # open the "box"
    hdul.info()                         # list all drawers (HDUs)

    img_hdu = hdul["IMAGE"]             # choose a drawer by name
    hdr = img_hdu.header                # the labels
    data = img_hdu.data                 # the numbers (NumPy array)

    print(hdr["BUNIT"])                 # MJy / sr
    print(hdr["MJD-AVG"])               # 60830.84...
    print(data.shape, data.dtype)       # (2040, 2040) >f4
    print(data[1000, 1000])             # brightness of one pixel

    import numpy as np
    print(np.nanmedian(data))           # typical sky brightness, ~0.458
```

`nanmedian` ignores `NaN` values ("Not a Number" = missing pixels). Our files have very few (~0.005%).

---

## 4.9 Summary

- FITS = astronomy's standard file; one file can hold many **HDUs**.
- Each HDU = **header** (text labels, 80-character cards) + **data** (image, cube or table).
- SPHEREx file = 7 HDUs: PRIMARY, **IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE**.
- Use names, not numbers, to pick HDUs.
- NumPy order is **[y, x]**; FITS pixels start at **1**, Python at **0**.

## 4.10 Self-check

1. What is the difference between an ImageHDU and a BinTableHDU?
2. Name the 7 HDUs in our file and say in one sentence what each contains.
3. Why should we never modify files in `data/raw/`?
4. Why is `data[y, x]` correct and `data[x, y]` wrong?
5. Why is each file about 72 MB?

## 4.11 Try it yourself

Run the Python code in 4.8 on each of our 4 files and write down: `DETECTOR`, `MJD-AVG`, image median.
