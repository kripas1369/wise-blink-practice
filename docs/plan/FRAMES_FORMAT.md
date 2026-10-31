# Frames format: what the flipbook reads (`spherex-blink-frames/1`)

The contract between the data pipeline (`backend/app/render.py`) and the website (`frontend/`).
Whoever makes the frames (`render.py` for the prepared targets, the `/api/frames` background job for any other position) writes **exactly this**, and the website shows it without changing any value.
Day 3 added three files next to each manifest: the per-visit data (`epoch<i>.fits`, section 8), the Gaia markers (`gaia.json`, section 6) and the difference maps (`diff.json`, section 7).
Day 4 added the asinh brightness scale (section 3), every single exposure on the grid (`exposures.fits`, section 9) and the light curve (`lightcurve.json`, section 10).
Day 5 added the proof panel (`proof.json`, section 11) and the spots above 5σ (`spots.json`, section 12).

The website refuses a manifest that breaks these rules (`frontend/js/frames.js`, `checkManifest`) and says why, instead of showing frames it cannot label honestly.

---

## 1. Where the files go

```
frontend/frames/
  index.json                     which targets and detectors exist
  <target>/d<detector>/
    manifest.json                one per target and detector
    epoch<i>.png                 the picture of visit i
    epoch<i>_flags.png           red where the pixel is flagged bad (optional)
    epoch<i>.fits                the values behind the picture (section 8)
    gaia.json                    Gaia DR3 stars moved to each visit (section 6; backend/app/gaia.py)
    diff.json, diff_<a>_<b>.png  difference of every visit pair (section 7; backend/app/diff.py)
    exposures.fits               every single exposure behind the frames (section 9; backend/app/lightcurve.py)
    lightcurve.json              the target's brightness in every exposure (section 10)
    proof.json                   measured motion vs Gaia, and the data it rests on (section 11; backend/app/proof.py)
    spots.json                   spots above 5σ in every difference, SPHEREx's position per visit (section 12; backend/app/spots.py)
```

- `<target>` is the key from `backend/app/targets.py`: `barnard`, `eps_ind_b`, `wise0855`, `rw_aur`, `r_dra`.
- `<detector>` is 1–6, e.g. `frontend/frames/barnard/d2/`.
- Do not use a folder called `data/`: it is in `.gitignore`.

`index.json`:

```json
{ "format": "spherex-blink-frames-index/1", "available": { "barnard": [2], "wise0855": [2, 6] } }
```

`backend/app/render.py` rebuilds it from the folders (`write_index()`) every time it writes frames.

---

## 2. The sky grid (must be identical, or frames cannot be compared)

| Rule | Value |
|---|---|
| Centre | the target's position at **2026.0**: SIMBAD J2000 position moved with its proper motion (`backend/app/motion.position_at`). The website uses the same rule, so the ring lands on the same spot. |
| Projection | `RA---TAN`, `DEC--TAN` |
| Pixel size | 6.15″ (`config.PIXEL_SCALE_ARCSEC`), `CDELT1 = -6.15/3600` (east to the left), `CDELT2 = +6.15/3600` |
| Size | `round(fov_arcmin × 60 / 6.15)`, forced odd: 3′ gives **29 × 29** |
| Reference pixel | `CRPIX = (size + 1) / 2` on both axes, so the target is the centre of the middle pixel |
| PNG rows | **north at the top**: FITS row 0 is south, so flip (`np.flipud`) before saving |

Code for this grid: `target_grid()` in `backend/app/align.py`.

---

## 3. `manifest.json`

Real example: `frontend/frames/barnard/d2/manifest.json`.

### Top level

| Field | Type | Meaning | Required |
|---|---|---|---|
| `format` | text | always `"spherex-blink-frames/1"` | yes |
| `target`, `label` | text | key and display name, e.g. `"barnard"`, `"Barnard's Star"` | yes |
| `ra`, `dec` | number (deg) | grid centre (section 2), **full precision, never rounded**: rounding to 6 decimals moved the grid enough to flip a pixel when the frames were rebuilt (`notes/DAY3_FINDINGS.md` §3) | yes |
| `position_source` | text | where the centre came from, e.g. `"SIMBAD (simbad.harvard.edu) NAME Barnard's star, moved to 2026.0"` | yes |
| `fov_arcmin`, `pixel_arcsec`, `size_px` | number | grid size; the website draws the 1′ scale bar from these | yes |
| `orientation` | text | `"north up, east left"` | yes |
| `band` | number | detector 1–6 | yes |
| `band_range_um` | [min, max] | detector range from `config.DETECTORS` | yes |
| `mode` | text | `"single"` (one exposure per visit) or `"coadd"` (several exposures of the visit added with 1/variance weights; how many is in each frame's `n_images`) | yes |
| `scale` | object | `{vmin, vmax, unit: "MJy/sr", method, stretch, asinh_softening}`: **one** scale for every frame; `vmin < vmax`; `stretch` is `"linear"` (or missing: linear) or `"asinh"`, which needs `asinh_softening > 0` | yes |
| `method` | text | one sentence: how the pictures were made | yes |
| `made_by`, `made_at` | text | which script, and when (UTC) | yes |
| `data_credit` | text | `"NASA/IPAC Infrared Science Archive (IRSA), SPHEREx"` | yes |
| `notes` | list of text | things a visitor must know before trusting their eyes; each one measured (see `notes/DAY2_FINDINGS.md`). Shown in an orange box. | no |
| `frames` | list | one per visit, **in time order** | yes, at least 1 |

### Each frame

| Field | Type | Meaning | Required |
|---|---|---|---|
| `png` | text | file name in the same folder | yes |
| `flags_png` | text | red flagged-pixel overlay, same size | no |
| `fits` | text | the visit's data file (section 8); the website does not read it | no |
| `epoch_id` | number | visit number from `archive.group_epochs` | yes |
| `mjd` | number | observation time: `MJD-AVG` from the header (never `DATE`). For an add-up: the mean of the exposures' `MJD-AVG`. | yes |
| `date_iso` | text | the same time as `"YYYY-MM-DD HH:MM UTC"` | yes |
| `band` | number | must equal the manifest's `band` | yes |
| `wl_min_um`, `wl_max_um` | number | wavelength range of the exposure(s) (obscore `em_min`/`em_max`; for an add-up the lowest min and highest max) | yes |
| `wl_target_um`, `bw_target_um` | number or null | wavelength and bandwidth **at the target pixel** from the file's spectral WCS (`key="W"`); for an add-up the mean over its exposures. `null` if unknown for any exposure; never guess. | yes |
| `wl_target_range_um` | [min, max] | add-ups only: lowest and highest wavelength at the target among the exposures (the LVF gives each exposure its own). The label shows this range. | no |
| `n_images` | number | exposures in this picture (1 for `single`) | yes |
| `n_images_in_epoch` | number | exposures of this detector in the visit | no |
| `pct_flagged` | number | % of grid pixels flagged bad (official mask, `flags.bad_pixel_bitmask`). For an add-up: pixels where every exposure that had a value was flagged. | yes |
| `pct_no_value` | number | % of pixels inside the image with no value (NaN, e.g. a saturated star core; for an add-up: NaN in every exposure); shown striped | no |
| `pct_covered` | number | % of the grid inside the exposure | no |
| `obs_id`, `collection` | text | which exposure (single mode) | no |

### PNG rules

- Grey RGBA, size `size_px × size_px`, north up.
- Grey = `t × 255` with `t = clip((value − vmin) / (vmax − vmin), 0, 1)` and the manifest's one scale.
- `stretch: "asinh"` (R Dra, Day 4): grey = `asinh(t / a) / asinh(1 / a) × 255`, `a = asinh_softening` (0.002), so faint light shows next to a very bright core. Grey levels are then **not proportional** to brightness; `method` and the website say so. Make it with `render.py --stretch asinh` or `rebuild.py --stretch asinh`.
- **Alpha 0** where there is no value (outside the exposure or NaN). The website shows those pixels striped, never as dark sky.
- Flags PNG: `(255, 40, 40, 200)` on flagged pixels, alpha 0 elsewhere.

---

## 4. How it becomes `/api/frames` (built on Day 3, `backend/app/main.py`)

`GET /api/frames?target=barnard&band=2` or `GET /api/frames?ra=&dec=&band=[&fov_arcmin=3]` returns **this manifest** plus:
- `png_url` and `flags_png_url` in each frame (the file names stay too);
- `base_url` (folder of the files; `gaia.json` and `diff.json` URLs are built from it), `source` (`"prepared"` or `"job"`), `warnings` (e.g. "Gaia DR3 markers failed: …").

A position within 5″ of an official target at a 3′ field of view gets the prepared frames. Any other position starts a background job (add-ups of up to 4 exposures per visit, then Gaia, then differences), answered with HTTP 202 `{"status": "working", "message"}` until ready; the website asks again every 10 s. Full list: [`FACTS.md`](FACTS.md) §7.

Without the API (plain `python3 -m http.server`), the website reads the same files directly from `frontend/frames/` (prepared targets only) and runs every check the same way.

---

## 5. Check frames before replacing the website's

```bash
python -m backend.app.render barnard 2 --out scratch/frames      # write to scratch first
python -m scripts.compare_frames frontend/frames/barnard/d2 scratch/frames/barnard/d2
cd frontend && npm test        # every manifest in frontend/frames must pass checkManifest
```

After installing new frames, make the Day 3 and Day 4 files again: `python -m backend.app.gaia <folder>` (internet), `python -m backend.app.diff <folder>` (offline), `python -m backend.app.lightcurve <folder> --rebuild-exposures` (offline, from the cached cutouts), then `python -m backend.app.frame_notes frontend/frames`.

---

## 6. `gaia.json` (`spherex-blink-gaia/1`, made by `backend/app/gaia.py`)

| Field | Meaning |
|---|---|
| `catalogue`, `catalogue_epoch` | `"Gaia DR3 (gaia_dr3_source at NASA/IPAC IRSA)"`, `2016.0` |
| `query` | `{ra, dec, radius_deg, n_returned}`: the cone asked for (covers the whole field plus the largest motion) |
| `method`, `pixel_convention`, `target_match_rule` | one sentence each, shown or linked on the website |
| `target_match` | `{source_id, sep_arcsec}` of the Gaia star nearest the grid centre at 2026.0 within 3″, or `null` (e.g. WISE 0855 is not in Gaia DR3) |
| `stars` | one per Gaia star whose position falls on the grid (plus a small margin, `MARGIN_PX`) in any visit |

Each star: `source_id` (**text**: 19-digit ids do not fit in a JavaScript number), `g_mag`, `pmra`, `pmdec` (mas/yr), `parallax` (mas), `has_motion`, `target` (only on the matched star), and `xy`: one `[x, y]` per frame, in the frames' order.
`xy` is in PNG pixels: x to the right (west), y down (south), 0 = centre of the first pixel, so the grid centre is `(size − 1) / 2`.
Positions: straight-line proper motion from 2016.0 to the frame's `mjd`; parallax not applied; stars without a Gaia proper motion stay at their 2016.0 position (`has_motion: false`).

---

## 7. `diff.json` (`spherex-blink-diff/1`, made by `backend/app/diff.py`)

Top level: `target`, `band`, `size_px`, `unit`, `limit_sigma` (5: the colour scale is clipped at ±5σ), `colours` (`brighter` `#ff6e28`, `fainter` `#468cff`, `zero` `#12141a`), `method`, `row_order` (north first, like the PNGs), `state_codes`, `default_pair`, `made_by`, `made_at`.

- `frames`: one per visit, for the hover read-out: `epoch_id`, `value` and `sigma` (2-D lists, MJy/sr, north first, `null` where there is no usable value), `state` (one text row per pixel row: `o` usable, `f` flagged bad, `n` no value).
- `pairs`: every visit pair with `a < b` (indices into `frames`): `png`, `days`, `wl_a_um`, `wl_b_um`, `wl_gap_um` (mean wavelength at the target of each add-up; `null` if unknown), `sky_change`, `scatter_sigma` (1.4826 × MAD of z; ≈ 1 when VARIANCE describes the real noise), `max_sigma`/`max_xy`, `min_sigma`/`min_xy`, `pct_valid`, `pct_flagged`, `pct_no_value`, and `z` (2-D, `null` where either visit is flagged or has no value).
- `default_pair`: `{a, b, reason}`: the closest mean wavelength at the target, then the longest time apart.

z = (B − A − sky change) / √(σA² + σB²); sky change = median of B − A over pixels usable in both visits.
Difference PNG: the colours above, linear from 0 to ±5σ; **alpha 0** where z is `null`, so the website shows it striped.

---

## 8. `epoch<i>.fits` (the values behind each picture)

Primary HDU empty, then 4 image extensions on the grid of section 2 (FITS rows: **south first**, as FITS always is; the PNGs are flipped):

| Extension | Type | Meaning |
|---|---|---|
| `IMAGE` | float32, MJy/sr | IMAGE − ZODI (added up for `coadd`), NaN where there is no usable value |
| `SIGMA` | float32, MJy/sr | 1σ noise from VARIANCE |
| `FLAGGED` | uint8 | 1 = flagged bad (official mask) |
| `HAS_VALUE` | uint8 | 1 = has a usable value |

Each header has the grid WCS plus `BUNIT`, `MJD-AVG`, `NIMAGES`, `DETECTOR`, `MODE`.
Written by `render.py`; `python -m backend.app.rebuild <folders>` writes them for existing frames from the cached cutouts and stops if a rebuilt PNG differs from the installed one by more than 1 grey level.

---

## 9. `exposures.fits` (every exposure behind the frames, Day 4)

Same grid and row order as section 8, but one plane per **single exposure** (all exposures the frames used, in time order), so each keeps its own wavelength:

| Extension | Type | Meaning |
|---|---|---|
| `IMAGE` | float32 cube, MJy/sr | IMAGE − ZODI of each exposure, reprojected onto the grid |
| `SIGMA` | float32 cube | 1σ from VARIANCE |
| `FLAGGED` | uint8 cube | 1 = flagged bad (official mask) |
| `HAS_VALUE` | uint8 cube | 1 = has a value |
| `EXPOSURES` | table | `OBS_ID`, `MJD`, `WL_UM` and `BW_UM` (wavelength and bandwidth at the grid centre; NaN if unknown), `FRAME` (which visit, index into `frames`) |

Written by `python -m backend.app.lightcurve <folder> --rebuild-exposures` from the cached cutouts (no download).

---

## 10. `lightcurve.json` (`spherex-blink-lightcurve/1`, made by `backend/app/lightcurve.py`)

Top level: `format`, `target`, `label`, `band`, `unit` (`"mJy"`), `position_rule` (how the measuring circle follows the target: Gaia, SIMBAD proper motion, or fixed), `made_by`, `made_at`, `data_credit`, `method`.

- **`method: "core"`**: a circle of `r_out_px` (2 px) around the target, minus the median sky in `sky_annulus_px` (10–14 px). `method_text` and `error_text` say this in words. No aperture correction: compare points with each other, not with catalogues.
- **`method: "none"`**: no light curve; `reason` says why (e.g. Barnard's Star and R Dra: the saturated core reaches 5–6 px, and only rings starting at most 3 px out were checked). `points` is `[]`.
- `points`: one per exposure: `obs_id`, `mjd`, `date_iso`, `frame`, `epoch_id`, `wl_um`, `bw_um`, `x`, `y` (PNG pixels of the circle's centre), `flux_mjy`, `err_mjy` (`null` when the circle has no value), `n_flagged` (flagged pixels inside the circle), `no_value`, `sky`.
- `same_wavelength`: `rule` (two exposures of different visits are compared only when their wavelengths differ by less than half the bandwidth and both are ≥ 5σ), `n_excluded`, and `pairs` / `pairs_incl_flagged`: per visit pair `a`, `b`, `n`, `median_ratio`, `min_ratio`, `max_ratio` (b / a), `max_wl_gap_um`. `pairs` needs no flagged pixel in either circle.
- `comparison`: field stars measured the same way (Gaia G ≤ 17, isolated within 4 px, sky 5–8 px): `n_stars`, `n_pairs`, `scatter_pct` (the change a steady star seems to show), `median_ratio`, the same `_incl_flagged`, and `stars`. `n_pairs: 0` means the floor is unknown in this frame.
- `neighbours`: Gaia stars inside the circle (up to 3 mag fainter than the target): `source_id`, `g_mag`, `distance_px`. Their light is in every point.

`GET /api/lightcurve` (same location parameters as `/api/frames`) returns this file; with `&x=&y=` (PNG pixels, both or neither) it measures that fixed position the same way instead.

---

## 11. `proof.json` (`spherex-blink-proof/1`, made by `backend/app/proof.py`)

Top level: `format`, `target`, `band`, `pixel_arcsec`, `motion`, `data`, `method` (in words), `made_by`, `made_at`.

- `motion.status`: `agrees`, `disagrees`, `too_small` (Gaia's motion below `limits.min_testable_px`), `not_measurable`, `no_gaia_target` (no Gaia star within 3″), `one_visit`. With `reason` in words whenever it is not `agrees` / `disagrees`.
- When Gaia has the target: `gaia_source_id` (text), `visits` (first and last date), `expected_px` (PNG x, y) and `expected_size_px`. When measured: `method` (`centroid` or `saturated-core centre`), `measured_px`, `measured_size_px`, `difference_px`, `direction_difference_deg` (`null` when the expected shift is too small for a direction).
- `motion.limits`: `max_error_px` 0.5 with `max_error_source` `"HACKATHON_PLAN C4"`; `max_direction_deg` 30 and `min_testable_px` 0.3 with `direction_and_min_source` `"ours"`.
- `data`: `n_visits`, `span_days`, `n_exposures_used`, `n_exposures_taken`, `pct_flagged_range` ([min, max] per visit), `visits` (per visit `date`, `n_images`, `n_images_in_epoch`, `pct_flagged`, `pct_no_value`), `frames_made_at`, `newest_exposure`.
- `data.releases` (made with `--online`): per collection `n_exposures` and `release_date` (the latest IRSA `release_date` of those exposures), plus `asked_irsa_at`. When missing or incomplete: `releases_reason` in words.

`GET /api/proof` returns this file.

---

## 12. `spots.json` (`spherex-blink-spots/1`, made by `backend/app/spots.py`)

Top level: `format`, `target`, `band`, `limit_sigma` (5), `rules` (`max_spots_per_pair`, `near_gaia_px`, `long_thin_ratio`, `large_px`, with `source: "ours"`), `observers`, `pairs`, `made_by`, `made_at`.

- `observers`: one per visit: `epoch_id`, `obs_id` (the exposure nearest the visit's mean time), `exposures_mjd_range`, `exposures_span_hours`, `available`, `mjd`, `xyz_km`, `vxyz_kms` (SPHEREx's geocentric position and velocity from the exposure header `X_SC` … `VZ_SC`), `system` (`"GEOCENTER (axes assumed ICRF)"`). `available: false` comes with a `reason`.
- `pairs`: one per visit pair `a` < `b`: `n_spots` (all found) and `spots` (up to 10, strongest |z| first).
- Each spot: `sign` (+1 brighter in B, −1 fainter), `peak_sigma`, `peak_xy`, `xy` (|z|-weighted centre, PNG pixels), `ra`, `dec`, `n_pixels`, `axis_ratio` (`null` below 3 pixels), `frame` (the visit it belongs to: B for +, A for −), `artifact_flags` (texts: long and thin, very large, next to flagged or no-value pixels, touches the frame edge), `gaia_star` (`source_id`, `g_mag`, `distance_px`, `target`, `chosen`: the brightest Gaia star within 1.5 px, else the nearest; `null` without Gaia), and the texts `why`, `what_else` (list), `confirm` (list).

The website reads this file directly (no endpoint); `GET /api/known-objects?…&a=&b=&spot=` uses it to check one spot against NASA JPL (FACTS §7).
