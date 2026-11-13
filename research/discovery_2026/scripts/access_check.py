"""DR1 + QR3 data-access validation (Stage C of the 2026 discovery mission).

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/access_check.py [RA DEC]

For one coordinate (default: the IRSA documentation example, 127.69444 -39.17760) this script

1. queries the IRSA SIA2 service for every current SPHEREx collection (spherex_dr1, spherex_dr1_deep,
   spherex_dr1_cube, spherex_qr3, spherex_qr3_deep) and, as a negative control, spherex_qr2;
2. queries the same position through TAP (spherex.obscore), the route the TimeLens backend uses;
3. downloads one cutout MEF from DR1 and one from QR3 (all extensions, nothing dropped) and one full DR1 MEF;
4. checks extensions, image size, celestial WCS, the spectral WCS (WCS-WAVE "W" keys) against the
   science-grade CWAVE/CBAND calibration product, the EPSF table, MJD-AVG and BUNIT, and that the cutout
   pixels equal the parent image pixels.

Everything it finds is written to EXPERIMENTAL_RESULTS/access_check.json.
"""
import hashlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits, votable
from astropy.wcs import WCS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "EXPERIMENTAL_RESULTS"
DL = ROOT / "data" / "access_check"
SIA = "https://irsa.ipac.caltech.edu/SIA"
TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
COLLECTIONS = ("spherex_dr1", "spherex_dr1_deep", "spherex_dr1_cube", "spherex_qr3", "spherex_qr3_deep",
               "spherex_qr2")
# Calibration products (spectral_wcs, epsf, ...) are listed on IRSA's public S3 mirror; the browsable
# directory https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/ answered 404 on 13 Nov 2026.
S3 = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"


def get(url, params=None, timeout=300, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code} {r.text[:200]!r}"
        except requests.RequestException as exc:
            last = exc
        time.sleep(2 ** i)
    raise RuntimeError(f"{url} failed: {last}")


def sia(collection, ra, dec, radius=0.001):
    r = get(SIA, {"COLLECTION": collection, "POS": f"CIRCLE {ra} {dec} {radius}", "RESPONSEFORMAT": "VOTABLE"})
    return votable.parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True)


def tap(adql):
    from astropy.table import Table
    r = get(TAP, {"QUERY": adql, "FORMAT": "csv", "LANG": "ADQL"})
    return Table.read(r.text, format="ascii.csv")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_mef(path, ra, dec):
    info = {"file": str(path), "sha256": sha256(path), "bytes": Path(path).stat().st_size}
    with fits.open(path) as h:
        info["extensions"] = [{"name": x.name, "type": type(x).__name__,
                               "shape": list(x.data.shape) if getattr(x, "data", None) is not None
                               and hasattr(x.data, "shape") else None} for x in h]
        ph, ih = h[0].header, h["IMAGE"].header
        keys = ("VERSION", "PROCVER", "RELEASE", "OBSID", "DETECTOR", "MJD-AVG", "MJD-BEG", "MJD-END", "DATE-AVG",
                "TIMESYS", "EXPTIME", "BUNIT", "PSF_FWHM", "CRPIX1A", "CRPIX2A", "CTYPE1", "CTYPE2", "CTYPE3W",
                "PS3_0W", "PS3_1W", "PS3_2W")
        info["primary_header"] = {k: str(ph[k]) for k in keys if k in ph}
        info["image_header"] = {k: str(ih[k]) for k in keys if k in ih}
        w = WCS(ih)
        x, y = (float(v) for v in w.world_to_pixel_values(ra, dec))
        info["target_pixel_xy"] = [x, y]
        info["pixel_scale_arcsec"] = [float(v) * 3600 for v in np.sqrt((w.pixel_scale_matrix ** 2).sum(0))]
        spec = WCS(ih, fobj=h, key="W")
        spec.sip = None
        wl, bw = (float(v) for v in spec.pixel_to_world_values(x, y))
        info["wcs_wave_at_target_um"] = [wl, bw]
        # parent-image pixel of the target (IRSA user guide, cutout section)
        if "CRPIX1A" in ih:
            info["parent_pixel_xy"] = [1 + x - ih["CRPIX1A"], 1 + y - ih["CRPIX2A"]]
        img = h["IMAGE"].data
        info["image_stats_MJy_sr"] = {"median": float(np.nanmedian(img)), "nan_frac": float(np.isnan(img).mean())}
        if "EPSF" in h:
            e = h["EPSF"]
            info["epsf"] = {"columns": e.columns.names, "n_rows": len(e.data),
                            "header": {k: str(e.header[k]) for k in ("OVSMPX", "OVSMPY", "TDIM11", "NAXIS2") if k in e.header},
                            "psf_shape": list(np.asarray(e.data["EPSF"][0]).shape)}
            if "parent_pixel_xy" in info:
                px, py = info["parent_pixel_xy"]
                d = np.hypot(e.data["XCENTER"] - px, e.data["YCENTER"] - py)
                k = int(np.argmin(d))
                info["epsf"]["zone_at_target"] = {"row": k, "BINX": int(e.data["BINX"][k]), "BINY": int(e.data["BINY"][k]),
                                                  "CWAVE": float(e.data["CWAVE"][k]),
                                                  "NEFF_MEAN": float(e.data["NEFF_MEAN"][k]),
                                                  "dist_px": float(d[k]),
                                                  "sum": float(np.sum(e.data["EPSF"][k]))}
        elif "PSF" in h:
            info["psf_cube_shape"] = list(h["PSF"].data.shape)
    return info


def main():
    ra, dec = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) == 3 else (127.69444, -39.17760)
    OUT.mkdir(parents=True, exist_ok=True)
    DL.mkdir(parents=True, exist_ok=True)
    report = {"ra": ra, "dec": dec, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "sia2": {}, "tap": {}}

    tables = {}
    for c in COLLECTIONS:
        try:
            t = sia(c, ra, dec)
            tables[c] = t
            cols = t.colnames
            row = {"n": len(t), "columns": cols[:60]}
            if len(t) and "t_min" in cols:
                row["t_min_range"] = [float(np.nanmin(t["t_min"])), float(np.nanmax(t["t_min"]))]
            if len(t) and "energy_bandpassname" in cols:
                row["bands"] = sorted({str(b) for b in t["energy_bandpassname"]})
            report["sia2"][c] = row
            print(f"SIA2 {c}: {len(t)} rows", flush=True)
        except Exception as exc:
            report["sia2"][c] = {"error": str(exc)}
            print(f"SIA2 {c}: ERROR {exc}", flush=True)

    t = tap(f"""SELECT obs_collection, COUNT(*) AS n, MIN(t_min) AS t0, MAX(t_max) AS t1
                FROM spherex.obscore WHERE CONTAINS(POINT('ICRS', {ra}, {dec}), s_region) = 1
                GROUP BY obs_collection""")
    report["tap"]["per_collection"] = {str(r["obs_collection"]): {"n": int(r["n"]), "mjd": [float(r["t0"]), float(r["t1"])]}
                                       for r in t}
    print("TAP:", report["tap"]["per_collection"], flush=True)

    report["files"] = {}
    chosen = {}
    for rel in ("spherex_dr1", "spherex_qr3"):
        tt = tables.get(rel)
        if tt is None or not len(tt):
            report["files"][rel] = "no images at this position"
            continue
        rejected = []
        for i, row in enumerate(tt):
            url = str(row["access_url"])
            cut = DL / f"{rel}_cutout_{i}.fits"
            if not cut.exists():
                cut.write_bytes(get(url, {"center": f"{ra},{dec}", "size": 0.05}).content)
            info = inspect_mef(cut, ra, dec)
            px, py = info["parent_pixel_xy"]
            if 0 <= px <= 2039 and 0 <= py <= 2039:
                break
            # SIA2 matches footprints that touch the search circle; the cutout service still returns pixels
            rejected.append({"obs_publisher_did": str(row["obs_publisher_did"]), "parent_pixel_xy": [px, py]})
            cut.unlink()
        info["access_url"] = url
        info["rejected_target_off_detector"] = rejected
        info["sia_row"] = {k: str(row[k]) for k in ("obs_id", "obs_publisher_did", "t_min", "t_max", "em_min", "em_max",
                                                   "energy_bandpassname", "obs_release_date") if k in tt.colnames}
        det = int(str(row["energy_bandpassname"])[-1])
        info["wcs_wave_vs_cwave"] = compare_cwave(rel.split("_")[1], det, *info["parent_pixel_xy"],
                                                  info["wcs_wave_at_target_um"])
        report["files"][rel] = info
        chosen[rel] = (url, cut)
        print(f"{rel}: {info['extensions']} rejected {len(rejected)}; {info['wcs_wave_vs_cwave']}", flush=True)

    # one full DR1 MEF: check the cutout pixels equal the parent pixels
    if "spherex_dr1" in chosen:
        url, cut = chosen["spherex_dr1"]
        full = DL / "spherex_dr1_full.fits"
        if full.exists():
            full.unlink()
        full.write_bytes(get(url, timeout=900).content)
        finfo = inspect_mef(full, ra, dec)
        with fits.open(full) as hf, fits.open(cut) as hc:
            ch = hc["IMAGE"].header
            x0, y0 = int(round(1 - ch["CRPIX1A"])), int(round(1 - ch["CRPIX2A"]))
            ny, nx = hc["IMAGE"].data.shape
            parent = hf["IMAGE"].data[y0:y0 + ny, x0:x0 + nx]
            same = np.array_equal(np.nan_to_num(parent), np.nan_to_num(hc["IMAGE"].data))
            finfo["cutout_equals_parent_pixels"] = bool(same)
            finfo["cutout_offset_in_parent"] = [x0, y0]
            # science-grade wavelength: compare WCS-WAVE (visualisation) with the CWAVE calibration product
            det = int(hf["IMAGE"].header["DETECTOR"])
            finfo["detector"] = det
            px, py = finfo["target_pixel_xy"]
            finfo["wcs_wave_vs_cwave"] = compare_cwave("dr1", det, px, py, finfo["wcs_wave_at_target_um"])
        report["files"]["spherex_dr1_full"] = finfo
        print("full DR1:", finfo.get("cutout_equals_parent_pixels"), finfo.get("wcs_wave_vs_cwave"), flush=True)

    (OUT / "access_check.json").write_text(json.dumps(report, indent=1, default=str))
    print("wrote", OUT / "access_check.json")


def compare_cwave(release, det, px, py, wcs_wave):
    """Find the spectral_wcs calibration file for this detector and compare CWAVE at the pixel."""
    import re
    try:
        listing = get(f"{S3}/?list-type=2&prefix={release}/spectral_wcs/").text
        keys = sorted(k for k in re.findall(r"<Key>([^<]+)</Key>", listing) if f"/{det}/" in k)
        if not keys:
            return {"error": f"no spectral_wcs for D{det} in {release}"}
        url = f"{S3}/{keys[-1]}"
        path = DL / keys[-1].rsplit("/", 1)[-1]
        if not path.exists():
            path.write_bytes(get(url, timeout=900).content)
        with fits.open(path) as h:
            iy, ix = int(round(py)), int(round(px))
            cw, cb = float(h["CWAVE"].data[iy, ix]), float(h["CBAND"].data[iy, ix])
        return {"url": url, "cwave_um": cw, "cband_um": cb, "wcs_wave_um": wcs_wave[0],
                "difference_nm": 1000 * (wcs_wave[0] - cw)}
    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    main()
