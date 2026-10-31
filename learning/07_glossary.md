# 07. Glossary

| Word | Meaning |
|---|---|
| **ADQL** | Astronomical Data Query Language: SQL with sky functions such as `CONTAINS` and `POINT`. |
| **Aladin Lite** | A sky viewer that runs in a web page (made by CDS Strasbourg). |
| **arcsec (″)** | 1/3600 of a degree. The full Moon is about 1800″ wide. |
| **arcmin (′)** | 1/60 of a degree = 60″. |
| **astropy** | The main Python library for astronomy (coordinates, time, FITS files, units). |
| **astroquery** | Python library to ask online archives (SIMBAD, IRSA, Gaia). |
| **blink / flipbook** | Showing images of the same sky taken at different times one after another, so changes stand out. |
| **cache** | Saving a downloaded file on disk so we never download it again. |
| **coadd / add-up** | Combining several images of the same spot (weighted mean) to reduce noise. |
| **cutout** | A small square cut from a big image, made on IRSA's side. |
| **DEC (declination)** | Sky "latitude", −90° to +90°. |
| **detector (D1–D6)** | SPHEREx has 6 detectors, each covering a range of wavelengths (D1 0.75–1.09 µm ... D6 4.42–5.00 µm). |
| **epoch** | One visit of SPHEREx to a spot (a few weeks), about every 6 months. |
| **exposure** | One snapshot; it gives 2 images (paired detectors D1+D4, D2+D5, D3+D6). |
| **FastAPI** | Python library that turns functions into web addresses (the API). |
| **FITS** | The standard astronomy file format: header (text keywords) + data (numbers). |
| **flags** | A number per pixel; each bit marks one problem (hot pixel, cosmic ray, ...). |
| **Gaia** | ESA mission that measured positions and motions of ~1.8 billion stars (catalogue date 2016.0). |
| **HiPS / MOC** | Ways to show large sky images (HiPS) and sky coverage maps (MOC). |
| **IRSA** | NASA/IPAC Infrared Science Archive, the official home of SPHEREx data. |
| **LVF** | Linear variable filter: SPHEREx's filter; wavelength changes across the detector. |
| **mas/yr** | Milliarcseconds per year, the unit of proper motion. 1000 mas = 1″. |
| **MJD** | Modified Julian Date: a day counter. MJD 61000 = 21 Nov 2025. |
| **`MJD-AVG`** | Header keyword: the middle time of the exposure. **The** observation time. |
| **`DATE`** | Header keyword: when the file was **processed**. Never use it as observation time. |
| **ObsCore** | A standard table layout for "list of observations" (`spherex.obscore`). |
| **pixel scale** | Sky size of one pixel. SPHEREx: 6.15″. |
| **proper motion** | How fast a star moves across the sky (mas/yr), in RA and Dec. |
| **PSF** | Point spread function: how a point of light is smeared in the image. |
| **pyvo** | Python library for Virtual Observatory services (TAP, SIA). |
| **QR2 / QR3** | SPHEREx Quick Releases 2 and 3 (data releases). Both are live on 31 Oct 2026. |
| **RA (right ascension)** | Sky "longitude", 0–360° (or 0–24 hours). |
| **reproject** | Moving an image onto another pixel grid (for example north-up), so images line up. |
| **`s_region`** | The outline of an image on the sky, used in `CONTAINS(POINT, s_region)`. |
| **sexagesimal** | Base-60 notation like `17h57m48s +04d41m36s`. |
| **sigma (σ)** | Noise level. "5 sigma" = 5 times the noise: very unlikely to be random. |
| **SIA2** | Simple Image Access v2: another IVOA way to search images (lags TAP by ~1 day for SPHEREx). |
| **SIMBAD** | Star name database (CDS). Mirror: `simbad.harvard.edu`. |
| **SPHEREx** | NASA infrared all-sky survey telescope, launched March 2025, 102 colours, 0.75–5 µm. |
| **TAP** | Table Access Protocol: send an ADQL query, get a table back. |
| **variance** | Noise squared. `sigma = sqrt(variance)`. |
| **WCS** | World Coordinate System: header keywords that convert pixel ↔ sky position. |
| **ZODI** | Zodiacal light: glow from dust in our solar system; SPHEREx gives a model to subtract. |
