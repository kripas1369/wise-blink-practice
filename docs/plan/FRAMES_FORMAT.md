# Frames format: what the flipbook reads (`spherex-blink-frames/1`)

The contract between the data pipeline (`backend/app/render.py`) and the website (`frontend/`).
Whoever makes the frames (the pipeline today, the `/api/frames` call on Day 3) writes **exactly this**, and the website shows it without changing any value.

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
| `ra`, `dec` | number (deg) | grid centre (section 2) | yes |
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

## 4. How it becomes `/api/frames` (Day 3)

FACTS §7 drafts `GET /api/frames?ra=&dec=&fov_arcmin=&band=&mode=` returning `[ {png_url, mjd, date_iso, epoch_id, band, n_images, pct_flagged} ]`.
Proposal for the Day 3 call: return **this manifest** instead (the top-level fields plus `frames`), with `png_url` and `flags_png_url` in place of the file names. Then the website changes one line (`loadManifest` fetches the API instead of the file) and keeps every honesty check.

---

## 5. Check frames before replacing the website's

```bash
python -m backend.app.render barnard 2 --out scratch/frames      # write to scratch first
python -m scripts.compare_frames frontend/frames/barnard/d2 scratch/frames/barnard/d2
cd frontend && npm test        # every manifest in frontend/frames must pass checkManifest
```
