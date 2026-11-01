"""Check two shortcuts of our pipeline against IRSA's per-pixel calibration maps, at our targets.

1. Pixel solid angle. lightcurve.py turns MJy/sr into mJy with one constant, (6.15")^2 per pixel, because
   it measures on our own north-up grid of 6.15" pixels (align.py). IRSA's Source Discovery Tool measures
   on detector pixels and multiplies by the solid angle pixel map (SAPM) instead. Printed: the SAPM at
   the target's detector pixel, and the pixel area implied by the file's own sky WCS (SIP included).
2. Wavelength. clean.wavelength_at reads the file's WCS-WAVE lookup table, which IRSA calls "intended
   for visualization" (about 1 nm); for science it points to CWAVE/CBAND in the spectral WCS calibration
   product. Printed: our wavelength minus CWAVE at the same pixel, in nm and in units of the bandwidth.

Cutout pixel -> detector pixel: 1 + x - CRPIX1A (IRSA PSF tutorial, section 4.3).

    python scripts/check_calibration.py frontend/frames/*/d2 frontend/frames/*/d6

Needs cache/calibration/sapm_D<n>.fits and spectral_wcs_D<n>.fits (whichever exist are used), from
https://nasa-irsa-spherex.s3.amazonaws.com/qr2/solid_angle_pixel_map/cal-sapm-v2-2025-164/<n>/solid_angle_pixel_map_D<n>_spx_cal-sapm-v2-2025-164.fits
https://nasa-irsa-spherex.s3.amazonaws.com/qr2/spectral_wcs/cal-wcs-v4-2025-254/<n>/spectral_wcs_D<n>_spx_cal-wcs-v4-2025-254.fits
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.align import cutout_size_deg  # noqa: E402
from backend.app.clean import wavelength_at  # noqa: E402
from backend.app.config import CACHE_DIR, PIXEL_SCALE_ARCSEC  # noqa: E402

ASSUMED = PIXEL_SCALE_ARCSEC ** 2


def wcs_pixel_area(sky: WCS, x: float, y: float) -> float:
    """arcsec^2 of the pixel at (x, y), from the sky WCS (SIP included), by finite differences."""
    ra0, dec0 = sky.pixel_to_world_values(x, y)
    ra1, dec1 = sky.pixel_to_world_values(x + 0.5, y)
    ra2, dec2 = sky.pixel_to_world_values(x, y + 0.5)
    cosd = np.cos(np.radians(dec0))
    jx = np.array([(ra1 - ra0) * cosd, dec1 - dec0]) * 2
    jy = np.array([(ra2 - ra0) * cosd, dec2 - dec0]) * 2
    return float(abs(jx[0] * jy[1] - jx[1] * jy[0]) * 3600 ** 2)


def bilinear(a: np.ndarray, x: float, y: float) -> float:
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    fx, fy = x - x0, y - y0
    return float(a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
                 + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def calibration(det: int, name: str, ext: str) -> np.ndarray | None:
    path = CACHE_DIR / "calibration" / f"{name}_D{det}.fits"
    return fits.getdata(path, ext) if path.exists() else None


def main() -> None:
    warnings.simplefilter("ignore")
    for folder in map(Path, sys.argv[1:]):
        m = json.loads((folder / "manifest.json").read_text())
        det = m["band"]
        sapm = calibration(det, "sapm", "IMAGE")
        cwave = calibration(det, "spectral_wcs", "CWAVE")
        cband = calibration(det, "spectral_wcs", "CBAND")
        pattern = f"*_D{det}_{m['ra']:.5f}_{m['dec']:+.5f}_{cutout_size_deg(m['fov_arcmin']):.4f}.fits"
        areas, waves = [], []
        for path in sorted((CACHE_DIR / "cutouts").glob(pattern)):
            with fits.open(path) as hdul:
                h = hdul["IMAGE"].header
                sky = WCS(h)
                x, y = sky.world_to_pixel_values(m["ra"], m["dec"])
                xd, yd = 1 + float(x) - h["CRPIX1A"], 1 + float(y) - h["CRPIX2A"]
                if not (0 <= xd < 2039 and 0 <= yd < 2039):
                    continue
                if sapm is not None:
                    areas.append((bilinear(sapm, xd, yd), wcs_pixel_area(sky, float(x), float(y))))
                if cwave is not None:
                    wl, _ = wavelength_at(hdul, m["ra"], m["dec"])
                    if wl is not None:
                        waves.append((wl - bilinear(cwave, xd, yd), bilinear(cband, xd, yd)))
        if areas:
            s, w = np.array(areas).T
            print(f"{folder} D{det} solid angle ({len(s)} exposures): SAPM {s.min():.2f}-{s.max():.2f} arcsec^2 "
                  f"(median {np.median(s):.2f}, {np.median(s) / ASSUMED - 1:+.1%} vs our {ASSUMED:.2f}); "
                  f"SAPM / sky WCS area {np.min(s / w):.4f}-{np.max(s / w):.4f}")
        if waves:
            d, bw = np.array(waves).T
            print(f"{folder} D{det} wavelength ({len(d)} exposures): ours - CWAVE median {np.median(d) * 1e3:+.2f} nm, "
                  f"largest {np.max(np.abs(d)) * 1e3:.2f} nm = {np.max(np.abs(d) / bw):.3f} x bandwidth")


if __name__ == "__main__":
    main()
