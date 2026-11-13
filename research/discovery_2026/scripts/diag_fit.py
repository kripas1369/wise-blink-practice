"""Data / model / residual panels of the forced ePSF fit for a few exposures of one target.

    PYTHONPATH=.:research .venv/bin/python research/discovery_2026/scripts/diag_fit.py NAME [N]
"""
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import phot as P
import spx_s3 as S


def model_image(d, i, nb):
    det = int(d["det"][i])
    w = WCS(fits.Header.fromstring(str(d["wcs"][i])))
    x0, y0 = int(d["x0"][i]), int(d["y0"][i])
    img, var, flg = d["image"][i], d["variance"][i], d["flags"][i]
    ny, nx = img.shape
    Y, X = np.mgrid[y0:y0 + ny, x0:x0 + nx].astype(float)
    tgt = nb["target"]
    xt, yt = (float(v) for v in w.all_world2pix(tgt["ra"], tgt["dec"], 0))
    src = [(xt, yt)]
    for s in nb["neighbours"]:
        sx, sy = (float(v) for v in w.all_world2pix(s["ra"], s["dec"], 0))
        if abs(sx - xt) <= P.FIT_HALF + P.NEIGH_KEEP_PX and abs(sy - yt) <= P.FIT_HALF + P.NEIGH_KEEP_PX and \
                all(math.hypot(sx - a, sy - b) >= P.MERGE_PX for a, b in src):
            src.append((sx, sy))
    bad = (flg < 0) | ((flg & int(d["bad_mask"][i])) != 0)
    reg = (np.abs(X - xt) <= P.FIT_HALF) & (np.abs(Y - yt) <= P.FIT_HALF)
    zone = P.zone_of(det, xt, yt)
    r = P.fit_one(det, img[reg], var[reg], bad[reg], X[reg], Y[reg], xt, yt, src, zone)
    cols = [P.psf_on(det, zone, X, Y, sx + r["dx"], sy + r["dy"]) for sx, sy in src]
    amps = [r["amp"]] + r["neigh_amp"]
    model = sum(a * c for a, c in zip(amps, cols)) + r["bg"]
    return img, model, var, bad, reg, (xt - x0, yt - y0), [(a - x0, b - y0) for a, b in src], r


def main():
    name = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    d = S.load(S.STAMPS / f"{name}.npz")
    nb = json.loads((P.NEIGH / f"{name}.json").read_text())
    idx = np.linspace(0, len(d["mjd_avg"]) - 1, n).round().astype(int)
    fig, ax = plt.subplots(n, 3, figsize=(9, 2.6 * n))
    for row, i in enumerate(idx):
        img, model, var, bad, reg, (xt, yt), src, r = model_image(d, i, nb)
        lo, hi = np.nanpercentile(img[reg], [5, 99.5])
        for k, (a, t) in enumerate([(img, "data"), (model, "model"), ((img - model) / np.sqrt(var), "resid / sigma")]):
            im = ax[row, k].imshow(a, origin="lower", vmin=(lo if k < 2 else -10), vmax=(hi if k < 2 else 10),
                                   cmap="gray" if k < 2 else "RdBu_r")
            ax[row, k].plot([p[0] for p in src], [p[1] for p in src], "c+", ms=5)
            ax[row, k].plot(xt, yt, "r+", ms=9)
            ax[row, k].contour(reg, [0.5], colors="y", linewidths=0.5)
            ax[row, k].contour(bad, [0.5], colors="m", linewidths=0.5)
            ax[row, k].set_xticks([]); ax[row, k].set_yticks([])
            if k == 2:
                plt.colorbar(im, ax=ax[row, k], shrink=0.8)
        ax[row, 0].set_ylabel(f"D{int(d['det'][i])} {d['mjd_avg'][i]:.2f}\nchi2r {r['chi2r']:.0f}", fontsize=8)
    ax[0, 0].set_title("data (MJy/sr)"); ax[0, 1].set_title("model"); ax[0, 2].set_title("(data-model)/sigma")
    fig.tight_layout()
    out = P.ROOT / "EXPERIMENTAL_RESULTS" / "figures" / f"fit_diag_{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == "__main__":
    main()
