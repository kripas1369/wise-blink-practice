"""Does flux-conserving reprojection (reproject_exact, used by IRSA's Source Discovery Tool) measure
steadier light curves than ours (reproject_interp, align.py)?

For each folder, the light curve is measured twice from the same cached cutouts, in a copy under /tmp:
once as align.py does it, once with the image and variance reprojected by reproject_exact (flag and
coverage masks unchanged). Printed: the spread of same-wavelength ratios between visits
(lightcurve.log_scatter_pct). On a steady star, a lower spread means less noise from the method.

    python scripts/compare_reproject.py frontend/frames/eps_ind_b/d2 frontend/frames/eps_ind_b/d5
"""
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

from reproject import reproject_exact, reproject_interp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend.app.align as align_module  # noqa: E402
from backend.app.lightcurve import log_scatter_pct, wavelength_pairs, write_exposures, write_lightcurve  # noqa: E402


def exact_for_values(data_wcs, grid, shape_out, order="bilinear"):
    if order != "bilinear":
        return reproject_interp(data_wcs, grid, shape_out=shape_out, order=order)
    return reproject_exact(data_wcs, grid, shape_out=shape_out)


def measure(folder: Path, method: str) -> dict:
    align_module.reproject_interp = exact_for_values if method == "exact" else reproject_interp
    work = Path(tempfile.mkdtemp()) / folder.name
    work.mkdir()
    for name in ("manifest.json", "gaia.json"):
        if (folder / name).exists():
            shutil.copy(folder / name, work / name)
    write_exposures(work)
    lc = write_lightcurve(work)
    if lc["method"] == "none":
        return {"method": "none"}
    out = {"method": lc["method"]}
    for allow in (False, True):
        ratios = [r for _, _, r, _ in wavelength_pairs(lc["points"], allow)]
        out["incl_flagged" if allow else "clean"] = (len(ratios), log_scatter_pct(ratios))
    return out


def main() -> None:
    warnings.simplefilter("ignore")
    for folder in map(Path, sys.argv[1:]):
        a, b = measure(folder, "interp"), measure(folder, "exact")
        print(f"{folder}: interp {a}  |  exact {b}")


if __name__ == "__main__":
    main()
