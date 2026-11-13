"""Per-exposure SPHEREx stamps for one sky position, read by HTTP range from IRSA's public S3 mirror.

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/spx_s3.py NAME RA DEC [--dets 3,4,5,6]

Why not the cutout service: it delivers ~0.4 cutouts/s; one YSO has ~300 D3-D6 exposures. The L2 MEF on S3
(level2/.../*.fits, uncompressed, 2040x2040 float32 per extension) lets us read only the rows around the target:
IMAGE header (WCS, MJD-AVG), then the rows y0..y1 of IMAGE, FLAGS and VARIANCE. ZODI is not read: the photometry fits
a local background plane, which absorbs the smooth zodiacal light.

Wavelength, bandwidth and pixel solid angle come from the calibration products (spectral_wcs CWAVE/CBAND,
solid_angle_pixel_map), identical for DR1 and QR3 (same S3 ETag, checked 13 Nov 2026). The ePSF is the
calibration table; it was checked to be byte-identical to the EPSF extension of DR1 and QR3 D4 images.

Output: data/stamps/NAME.npz (one row per accepted exposure) and data/stamps/NAME.json (query, rejections, timing).
"""
import argparse
import io
import json
import math
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits, votable
from astropy.io.fits.hdu.compressed._codecs import Rice1
from astropy.wcs import WCS, FITSFixedWarning

from backend.app.flags import bad_pixel_bitmask, flag_bits

ROOT = Path(__file__).resolve().parents[1]
CALIB = ROOT / "data" / "calib"
STAMPS = ROOT / "data" / "stamps"
S3 = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
SIA = "https://irsa.ipac.caltech.edu/SIA"
COLLECTIONS = ("spherex_dr1", "spherex_dr1_deep", "spherex_qr3", "spherex_qr3_deep")
NPIX = 2040
HALF_Y = 7                            # stamp rows: y0-7 .. y0+7
HALF_X = 10                           # stamp columns kept: x0-10 .. x0+10
EDGE = 4                              # the target must be at least this far from the detector edge (px)
EPSF_FILES = {3: "epsf_D3_spx_cal-epsf-v2-2026-191.fits", 4: "epsf_D4_spx_cal-epsf-v1-2026-191.fits",
              5: "epsf_D5_spx_cal-epsf-v1-2026-191.fits", 6: "epsf_D6_spx_cal-epsf-v1-2026-191.fits"}

warnings.simplefilter("ignore", FITSFixedWarning)
_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.mount("https://", requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=4))
    return _local.s


def get_range(key, start, length, tries=5):
    url = f"{S3}/{key}"
    last = None
    for i in range(tries):
        try:
            r = session().get(url, headers={"Range": f"bytes={start}-{start + length - 1}"}, timeout=60)
            if r.status_code == 206 and len(r.content) == length:
                return r.content
            last = f"HTTP {r.status_code}, {len(r.content)} bytes"
        except requests.RequestException as exc:
            last = exc
        time.sleep(0.5 * 2 ** i)
    raise RuntimeError(f"range {key} {start}+{length}: {last}")


def parse_header(buf, pos):
    """(Header, offset just after it) if the END card is inside buf[pos:], else None."""
    i = pos
    while i + 2880 <= len(buf):
        for k in range(i, i + 2880, 80):
            if buf[k:k + 8] == b"END     ":
                return fits.Header.fromstring(buf[pos:i + 2880].decode("ascii")), i + 2880
        i += 2880
    return None


def read_header(key, start, first=57600):
    """(Header, data offset, bytes read after the header). The extra bytes hold a compressed HDU's tile table."""
    buf = get_range(key, start, first)
    got = parse_header(buf, 0)
    if got is None:
        buf = get_range(key, start, first * 4)
        got = parse_header(buf, 0)
    if got is None:
        raise RuntimeError(f"no END card within {first * 4} bytes at {key}:{start}")
    hdr, n = got
    return hdr, start + n, buf[n:]


def hdu_end(hdr, data0):
    """Offset of the next HDU: data size from NAXIS/BITPIX (+PCOUNT heap), padded to 2880-byte blocks."""
    n = abs(hdr["BITPIX"]) // 8 * hdr["NAXIS1"] * hdr["NAXIS2"] + hdr.get("PCOUNT", 0)
    return data0 + -(-n // 2880) * 2880


def read_rows(key, hdr, data0, after, y0, nrow):
    """Rows y0..y0+nrow-1 (full width) of an uncompressed image HDU or of a row-tiled RICE_1 compressed HDU."""
    if not hdr.get("ZIMAGE"):
        dt = {-32: ">f4", 32: ">i4", 16: ">i2"}[hdr["BITPIX"]]
        n = NPIX * abs(hdr["BITPIX"]) // 8
        return np.frombuffer(get_range(key, data0 + y0 * n, nrow * n), dtype=dt).reshape(nrow, NPIX)
    if (hdr["ZCMPTYPE"] != "RICE_1" or hdr["ZTILE1"] != NPIX or hdr["ZTILE2"] != 1 or hdr["TFIELDS"] != 1
            or hdr["ZBITPIX"] not in (16, 32) or not str(hdr["TFORM1"]).startswith("1P")):
        raise RuntimeError(f"unsupported compression {hdr['ZCMPTYPE']} tile {hdr['ZTILE1']}x{hdr['ZTILE2']}")
    width = hdr["NAXIS1"]
    table = after if len(after) >= width * hdr["NAXIS2"] else get_range(key, data0, width * hdr["NAXIS2"])
    desc = np.frombuffer(table[:width * hdr["NAXIS2"]], dtype=">i4").reshape(hdr["NAXIS2"], 2)
    count, offset = desc[y0:y0 + nrow, 0], desc[y0:y0 + nrow, 1]
    heap0 = data0 + hdr.get("THEAP", width * hdr["NAXIS2"])
    lo, hi = int(offset.min()), int((offset + count).max())
    heap = get_range(key, heap0 + lo, hi - lo)
    params = {hdr[f"ZNAME{i}"]: hdr[f"ZVAL{i}"] for i in range(1, 5) if f"ZNAME{i}" in hdr}
    codec = Rice1(blocksize=int(params.get("BLOCKSIZE", 32)), bytepix=int(params.get("BYTEPIX", hdr["ZBITPIX"] // 8)),
                  tilesize=NPIX)
    heap = np.frombuffer(heap, dtype=np.uint8)
    return np.stack([codec.decode(heap[o - lo:o - lo + c]) for o, c in zip(offset, count)])


def sia(collection, ra, dec, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(SIA, params={"COLLECTION": collection, "POS": f"CIRCLE {ra} {dec} 0.0005",
                                          "RESPONSEFORMAT": "VOTABLE"}, timeout=300)
            if r.status_code == 200:
                return votable.parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True)
            last = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001 - network or VOTable parse failure, retried
            last = exc
        time.sleep(2 ** i)
    raise RuntimeError(f"SIA {collection} failed: {last}")


def find_images(ra, dec, dets):
    """Every L2 exposure whose footprint contains (ra, dec), from SIA2 (QR2 is not queried: it is superseded)."""
    out, seen, counts = [], set(), {}
    for col in COLLECTIONS:
        t = sia(col, ra, dec)
        counts[col] = len(t)
        for row in t:
            if str(row["dataproduct_subtype"]) != "science":
                continue
            det = int(str(row["energy_bandpassname"]).split("D")[-1])
            if det not in dets:
                continue
            key = json.loads(str(row["cloud_access"]))["aws"]["key"]
            if key in seen:
                continue
            seen.add(key)
            out.append({"key": key, "collection": col, "obs_id": str(row["obs_id"]), "det": det,
                        "t_min": float(row["t_min"]), "t_max": float(row["t_max"])})
    return out, counts


_calib = {}
_calib_lock = threading.Lock()


def calib(det):
    with _calib_lock:
        if det not in _calib:
            sw = CALIB / f"spectral_wcs_D{det}_spx_cal-swcs-v5-2026-191.fits"
            sa = CALIB / f"solid_angle_pixel_map_D{det}_spx_cal-sapm-v3-2026-191.fits"
            _calib[det] = {"cwave": fits.getdata(sw, "CWAVE").astype(np.float32),
                           "cband": fits.getdata(sw, "CBAND").astype(np.float32),
                           "sapm": fits.getdata(sa, "IMAGE").astype(np.float32)}
        return _calib[det]


def stamp(img, ra, dec):
    """Read the target's stamp from one exposure. Returns (record, None) or (None, rejection reason)."""
    key = img["key"]
    ph, p_end, _ = read_header(key, 0, 2880)
    ih, data0, i_after = read_header(key, p_end)
    if ih.get("EXTNAME") != "IMAGE" or ih.get("ZIMAGE") or ih["NAXIS1"] != NPIX or ih["NAXIS2"] != NPIX:
        return None, f"unexpected IMAGE HDU {ih.get('EXTNAME')} {ih.get('NAXIS1')}x{ih.get('NAXIS2')}"
    w = WCS(ih)
    x, y = (float(v) for v in w.all_world2pix(ra, dec, 0))
    if not (EDGE <= x <= NPIX - 1 - EDGE and EDGE <= y <= NPIX - 1 - EDGE):
        return None, f"target off detector or within {EDGE} px of edge (x={x:.1f}, y={y:.1f})"
    xc, yc = int(round(x)), int(round(y))
    y0, y1 = max(yc - HALF_Y, 0), min(yc + HALF_Y, NPIX - 1)
    x0, x1 = max(xc - HALF_X, 0), min(xc + HALF_X, NPIX - 1)
    nrow = y1 - y0 + 1
    cols = slice(x0, x1 + 1)

    sci = read_rows(key, ih, data0, i_after, y0, nrow)[:, cols].astype(np.float32)
    fh, fdata0, f_after = read_header(key, hdu_end(ih, data0))
    if fh.get("EXTNAME") != "FLAGS":
        return None, f"expected FLAGS, found {fh.get('EXTNAME')}"
    flg = read_rows(key, fh, fdata0, f_after, y0, nrow)[:, cols].astype(np.int32)
    vh, vdata0, v_after = read_header(key, hdu_end(fh, fdata0))
    if vh.get("EXTNAME") != "VARIANCE":
        return None, f"expected VARIANCE, found {vh.get('EXTNAME')}"
    var = read_rows(key, vh, vdata0, v_after, y0, nrow)[:, cols].astype(np.float32)
    c = calib(img["det"])
    sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
    rec = dict(img)
    rec.update({
        "version": str(ph.get("VERSION")), "mjd_avg": float(ih["MJD-AVG"]), "mjd_beg": float(ih["MJD-BEG"]),
        "mjd_end": float(ih["MJD-END"]), "xposure": float(ih.get("XPOSURE", np.nan)),
        "psf_fwhm": float(ih.get("PSF_FWHM", np.nan)), "l2dqa": str(ih.get("L2DQAFLG")),
        "bunit": str(ih.get("BUNIT")), "x": x, "y": y, "x0": x0, "y0": y0,
        "wcs": w.to_header_string(relax=True),
        "flag_bits": flag_bits(fh), "bad_mask": bad_pixel_bitmask(fh),
        "image": sci, "variance": var, "flags": flg,
        "cwave": c["cwave"][sl].copy(), "cband": c["cband"][sl].copy(), "sapm": c["sapm"][sl].copy(),
    })
    return rec, None


def extract(name, ra, dec, dets=(3, 4, 5, 6), workers=24, out=STAMPS):
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    imgs, counts = find_images(ra, dec, set(dets))
    t_query = time.time() - t0
    recs, rejected = [], []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(stamp, im, ra, dec): im for im in imgs}
        for f in as_completed(futs):
            im = futs[f]
            try:
                rec, why = f.result()
            except Exception as exc:  # noqa: BLE001 - recorded, not hidden
                rec, why = None, f"read error: {exc}"
            if rec is None:
                rejected.append({"key": im["key"], "collection": im["collection"], "det": im["det"],
                                 "t_min": im["t_min"], "reason": why})
            else:
                recs.append(rec)
    recs.sort(key=lambda r: (r["det"], r["mjd_avg"]))
    save(out / f"{name}.npz", recs)
    meta = {"name": name, "ra": ra, "dec": dec, "detectors": list(dets), "collections": list(COLLECTIONS),
            "sia_rows_per_collection": counts, "n_images_found": len(imgs), "n_accepted": len(recs),
            "n_rejected": len(rejected), "rejected": rejected, "sia_seconds": round(t_query, 1),
            "read_seconds": round(time.time() - t0 - t_query, 1), "half_y": HALF_Y, "half_x": HALF_X, "edge": EDGE,
            "versions": sorted({r["version"] for r in recs}),
            "flag_bits_by_version": {r["version"]: r["flag_bits"] for r in recs},
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / f"{name}.json").write_text(json.dumps(meta, indent=1))
    return recs, meta


SCALARS = ("key", "collection", "obs_id", "det", "t_min", "t_max", "version", "mjd_avg", "mjd_beg", "mjd_end",
           "xposure", "psf_fwhm", "l2dqa", "bunit", "x", "y", "x0", "y0", "wcs", "bad_mask")
ARRAYS = ("image", "variance", "flags", "cwave", "cband", "sapm")


def save(path, recs):
    """Stamps at the detector edge are smaller; arrays are padded to full size with NaN / flag -1."""
    ny, nx = 2 * HALF_Y + 1, 2 * HALF_X + 1
    d = {k: np.array([r[k] for r in recs]) for k in SCALARS}
    for k in ARRAYS:
        fill = -1 if k == "flags" else np.nan
        a = np.full((len(recs), ny, nx), fill, dtype=np.int32 if k == "flags" else np.float32)
        for i, r in enumerate(recs):
            s = r[k]
            a[i, :s.shape[0], :s.shape[1]] = s
        d[k] = a
    np.savez_compressed(path, **d)


def load(path):
    z = np.load(path, allow_pickle=False)
    return {k: z[k] for k in z.files}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("ra", type=float)
    p.add_argument("dec", type=float)
    p.add_argument("--dets", default="3,4,5,6")
    p.add_argument("--workers", type=int, default=24)
    a = p.parse_args()
    recs, meta = extract(a.name, a.ra, a.dec, tuple(int(d) for d in a.dets.split(",")), a.workers)
    print(json.dumps({k: v for k, v in meta.items() if k not in ("rejected", "flag_bits_by_version")}, indent=1))
    reasons = {}
    for r in meta["rejected"]:
        reasons[r["reason"].split("(")[0].strip()] = reasons.get(r["reason"].split("(")[0].strip(), 0) + 1
    print("rejections:", reasons)


if __name__ == "__main__":
    main()
