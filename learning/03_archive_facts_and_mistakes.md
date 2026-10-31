# 03. Archive facts we measured, and every mistake we fixed

Ground truth from real queries on 29–31 Oct 2026. These are the things that cost hours to find.
At the hackathon they cost zero.

## Facts about NASA's SPHEREx archive (IRSA)

| Fact | Why it matters |
|---|---|
| Query service: `https://irsa.ipac.caltech.edu/TAP`, table `spherex.obscore` | where every search starts |
| "Contains this point" = `CONTAINS(POINT('ICRS', ra, dec), s_region) = 1` | checks the image outline, not just its centre |
| The table holds 6 collections: `spherex_qr2`, `spherex_qr2_deep`, `spherex_qr3`, `spherex_qr3_deep`, plus `_cal` rows | filter to the 4 science collections |
| QR2 = observations up to ~Apr 2026; QR3 = from ~Aug 2026. No exposure is in both | combine both, no double counting |
| New data every week (newest seen: released 28–29 Oct 2026) | "easy to update" works if we query live |
| One exposure → 2 images (D1+D4, D2+D5, D3+D6 at the same moment) | exposures = images ÷ 2 |
| Wavelength in `em_min`/`em_max` is in **metres** | × 1e6 for micrometres |
| File path is in `spherex.artifact` (`a.uri`), joined via `spherex.plane` | needed for cutouts |
| Cutout: `/ibe/cutout?ra=&dec=&size=<deg>&path=<uri without "ibe/data/">` | small downloads |
| A 0.05° cutout = 29×29 px but ~5 MB (QR2) or ~4 MB (QR3) | the PSF/EPSF is always included |
| Cutout axes follow the detector, **not north-up** | we must reproject before blinking |
| Observation time = header `MJD-AVG`; `DATE` = processing date | wrong keyword = wrong dates |
| QR2 flag bits in `MP_*` keywords; QR3 in `MSKN*`/`MSKM*` keywords | read both; never hard-code |
| QR3 adds CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, HALO flags | better cleaning in QR3 |
| SOURCE labels 98–100% of pixels around bright targets | masking SOURCE would delete the target |
| Bad pixels (official list) in our cutouts: 0.4–7.3% | show "% flagged" under each frame |
| Gaia DR3 at IRSA: table `gaia_dr3_source` | Gaia markers without another server |
| SIMBAD main server (CDS) down on 29 and 31 Oct; `simbad.harvard.edu` works | always two servers |
| Barnard's Star moved 270″ since 2000; WISE 0855 212″; Eps Ind B 122″ | move positions before searching |

## Mistakes we made and how we fixed them

| What went wrong | Why | Fix |
|---|---|---|
| JOIN + `CONTAINS` in one query → "st_covers does not exist" | the archive's database cannot do both together | 2 queries: positions first, then file paths with `IN (...)` |
| Cutout → 404 | the path still started with `ibe/data/`, or we guessed a path | always use `a.uri` and remove `ibe/data/` |
| Cutout → 503 | we asked for too many at once | max 3 parallel, retry with backoff |
| Query → "Connection reset by peer" | IRSA dropped the connection | retries in `_run` |
| R Dra = one epoch lasting a year | it is observed almost all the time; "gap > 30 days" never happens | also split when an epoch is longer than 60 days |
| Report took ~10 minutes | every name waited 15+ s for the dead SIMBAD server | timeout 15 s, and the working server moves to the front |
| Wrong Gaia table name `gaia.gaiadr3_source` | guessed the name | checked the IRSA table list: `gaia_dr3_source` |
| QR3 flag list came back **empty** | QR3 uses `MSKN*` keywords, not `MP_*` | `flags.py` reads both and raises an error if neither exists |
| Calibration rows counted as images | `spherex.obscore` also holds `_cal` collections | filter `obs_collection IN (4 science collections)` |
| A second report run wrote into the same log | the first run was never stopped (the kill was blocked) | check running processes before starting a long job |
| New test file "not run" | the test run started before the file was saved | rerun after writing; check the test count |

## Lessons for the hackathon (write these on the cheat sheet)
1. Query **all** science collections; show the newest release date.
2. Two-step query: positions, then paths.
3. Cutouts: strip `ibe/data/`, max 3 at a time, cache, check `SIMPLE`.
4. Time = `MJD-AVG`. Flags from the header, both formats. SOURCE is a label.
5. Move the star with proper motion before searching.
6. Reproject to north-up before blinking.
7. SIMBAD: two servers, short timeout.
8. Expected motions are 1–2 px. Alignment quality is everything.
