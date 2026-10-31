# Frames format: what the flipbook reads (`spherex-blink-frames/1`)

The contract between the data pipeline (`backend/app/render.py`) and the website (`frontend/`).
Whoever makes the frames (`render.py` for the prepared targets, the `/api/frames` background job for any other position) writes **exactly this**, and the website shows it without changing any value.
Day 3 added three files next to each manifest: the per-visit data (`epoch<i>.fits`, section 8), the Gaia markers (`gaia.json`, section 6) and the difference maps (`diff.json`, section 7).

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
| `scale` | object | `{vmin, vmax, unit: "MJy/sr", method}`: **one** linear scale for every frame; `vmin < vmax` | yes |
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
- Grey = `clip((value − vmin) / (vmax − vmin), 0, 1) × 255`, with the manifest's one scale.
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

After installing new frames, make the Day 3 files again: `python -m backend.app.gaia <folder>` (internet) and `python -m backend.app.diff <folder>` (offline), then `python -m backend.app.frame_notes frontend/frames`.

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
