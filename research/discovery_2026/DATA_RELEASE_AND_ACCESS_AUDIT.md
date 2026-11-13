# Data release and access audit (Stage C)

All checks were run on 13 Nov 2026 (UTC) from this machine, without credentials, against public IRSA services.
Raw evidence: `EXPERIMENTAL_RESULTS/access_check.json` (script `scripts/access_check.py`), documentation snapshots in
`docs_snapshot/`, and the stamp-reader validation described in §5.

## 1. Releases and collections

| Collection (IRSA) | Content | Rows at test position 127.69444 −39.17760 | MJD range there |
|---|---|---|---|
| `spherex_dr1` | DR1 L2 spectral images, survey visits May 2025 – May 2026 | 411 (SIA2) / 410 (TAP) | 60790.58 – 61174.29 |
| `spherex_dr1_deep` | DR1 deep-field L2 images | 0 (outside deep fields) | – |
| `spherex_dr1_cube` | DR1 spectral cubes | 1 | 60789.85 |
| `spherex_qr3` | Quick Release 3 L2 images, May 2026 onward | 14 (SIA2 and TAP) | 61181.14 – 61181.22 |
| `spherex_qr3_deep` | QR3 deep fields | 0 | – |
| `spherex_qr2` (negative control) | superseded | **0** | – |

QR2 returns nothing: querying QR2 and concluding "no data" would be wrong (mission rule). Every analysis here queries
`spherex_dr1`, `spherex_dr1_deep`, `spherex_qr3`, `spherex_qr3_deep`; duplicates are removed by S3 key.
The TimeLens production backend still lists QR2 collections (`backend/app/config.py`); not changed (research only).

## 2. File format (verified on a full DR1 L2 file, VERSION 7.0.5, D4)

| HDU | Type | Notes |
|---|---|---|
| PRIMARY | header only | `VERSION = '7.0.5'` |
| IMAGE | 2040×2040 float32, uncompressed | `BUNIT = 'MJy / sr'`, zodiacal light **not** subtracted; celestial WCS `RA---TAN-SIP`; time `MJD-BEG/AVG/END` (UTC, `TIMESYS`); `PSF_FWHM` ≈ 8.67″; pixel ≈ 6.16″ |
| FLAGS | 2040×2040 int32 **tile-compressed** (RICE_1, one tile per row) | bit names in `MSKN*`/`MSKM*` keys; bit 21 = SOURCE (not a defect) |
| VARIANCE | 2040×2040 float32 | (MJy/sr)² |
| ZODI | 2040×2040 float32 | model zodiacal light |
| EPSF | binary table, 441 zones (21×21), 33×33 ePSF oversampled ×5 | identical to the calibration file (below) |
| WCS-WAVE | binary table | approximate per-pixel wavelength (`WCS(key="W")`) |

Byte offsets in that file: IMAGE data at 25 920, FLAGS header at 16 672 320 (FLAGS data 6.38 MB, compressed),
VARIANCE at 23 068 800. A reader that assumes uncompressed FLAGS misplaces every later HDU (this happened in the
first attempt and was caught because the VARIANCE header was not found).

## 3. Wavelength, bandwidth, PSF, solid angle

* Spectral WCS: calibration product `spectral_wcs/cal-swcs-v5-2026-191/{1..6}/spectral_wcs_D{d}_spx_cal-swcs-v5-2026-191.fits`
  (extensions CWAVE, CBAND in µm). At the test pixel, CWAVE 2.40267 µm vs the image's WCS-WAVE 2.40608 µm: 3.4 nm,
  ~8% of the channel width. CWAVE is used.
* Wavelength runs along detector rows (y): CWAVE at (x=1020) spans 2.40 → 3.82 µm (D4) bottom to top; along a row it
  changes by ≤ 1.5%.
* ePSF: `epsf/cal-epsf-v1-2026-191/{d}/` (D3 also `v2`, 451 zones, used for D3). For D4, the calibration table
  (all 11 columns including the 441 ePSFs) is **byte-identical** to the EPSF extension of a DR1 image and of a QR3
  image. Each ePSF sums to 1 on the oversampled grid; photutils `ImagePSF` convention (array [y, x], centre (n−1)/2,
  native value = 25 × spline value).
* Solid angle: `solid_angle_pixel_map/cal-sapm-v3-2026-191/{d}/` (arcsec², median ≈ 37.9 arcsec²); F_ν[Jy] =
  I[MJy/sr] × Ω[sr] × 10⁶.
* DR1 and QR3 calibration files have identical S3 ETags (checked for spectral_wcs, epsf and solid-angle maps, D1–D6).

## 4. Access routes

| Route | Use | Measured throughput |
|---|---|---|
| SIA2 `https://irsa.ipac.caltech.edu/SIA?COLLECTION=…&POS=CIRCLE ra dec r` | image discovery; `cloud_access` column gives the S3 key | 5–15 s per collection query |
| TAP `spherex.obscore` (CSV) | same rows; used by the backend | – |
| IRSA cutout service (`…/ibe/data/spherex/…fits?center=…&size=…`) | cutouts with all HDUs | ≈ 0.43 cutouts/s |
| Public S3 mirror `https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/{dr1,qr3}/level2/…` with HTTP Range | rows around the target only | 26–33 requests/s with 16–32 threads; ≈ 8 exposures/s end-to-end |
| Browsable `https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/` calibration directory | – | HTTP 404 on 13 Nov 2026; S3 listing used instead |

The S3 bucket is public, anonymous, and documented by IRSA (`docs_snapshot/sx_spherex-data-access.txt`).
No credentials, paid services or private accounts were used.

## 5. Stamp reader validation (`scripts/spx_s3.py`)

The reader takes the IMAGE header (WCS, time), computes the target pixel, rejects the exposure if the target is
outside the detector or within 4 px of its edge (the IRSA SIA2 footprint test is approximate: the first DR1 row at the
test position had the target at y = 2041.4, off the detector), then reads rows y±7 of IMAGE, FLAGS (decompressing only
the needed RICE tiles) and VARIANCE.

Test: the reader was pointed at the local full DR1 file instead of S3, at three positions (centre, and two corners
where the stamp is clipped). IMAGE, FLAGS and VARIANCE stamps are **identical** to astropy's full decode at all three.
Live run (EC 53): 280 D3–D6 exposures found, 280 read, 0 failures, 35 s.

## 6. Temporal structure (mandatory test)

Example, EC 53 (277.46325 +1.27789), D3–D6 (details per target in `OBSERVATION_TIMELINES/`):

| Visit | MJD | Release | Exposures D3/D4/D5/D6 | D4 sweep duration | D5 sweep | D6 sweep |
|---|---|---|---|---|---|---|
| 0 | 60914.8 – 60949.7 (Sep–Oct 2025) | DR1 | 21/18/20/21 | 8.9 d | 14.0 d | 34.9 d |
| 1 | 61120.4 – 61171.9 (Apr–May 2026), two passes | DR1 | 30/30/29/30 | 45.6 d | 45.8 d | 44.8 d |
| 2 | 61278.7 – 61317.2 (Sep–Oct 2026) | QR3 | 18/18/27/18 | 10.3 d | 35.9 d | 7.8 d |

Within a visit, exposures arrive in same-day groups of 3–5 adjacent channels (e.g. visit 2, MJD 61290.0:
4.202, 4.238, 4.274, 4.311 µm within hours). A source therefore has to be modelled with possible brightness change
**within** a visit; the full spectrum is never treated as instantaneous. QR3 (survey 3) channels are shifted by about
half a channel relative to DR1, so wavelengths are never compared channel-by-channel across releases; models are
evaluated at each exposure's own CWAVE/CBAND.

Detector pairs D1/D4, D2/D5 and D3/D6 observe the same sky at the same time (dichroic split), e.g. EC 53 D3 at
MJD+17.7 and D6 at MJD+17.7.
