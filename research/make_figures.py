"""Figures for one field_psf.py / field_analysis.py run.

    PYTHONPATH=.:research .venv/bin/python research/make_figures.py NAME --tic TIC --eb SOURCE_ID [--target SOURCE_ID]

  fold.png        phase-folded light curves: the Gaia eclipsing binary, the star TESS-EBs names (TIC), and two
                  control stars of similar brightness that are not flagged as variable.
  difference.png  per detector: mean of (in-eclipse frame - out-of-eclipse frame at the nearest wavelength), and
                  the same divided by its standard error. A real eclipse leaves a negative spot only at the source.
  flipbook.gif    Eclipse Mode as a flipbook: pairs of out-of-eclipse / in-eclipse frames at the same wavelength.
Uses the eclipse (primary or secondary) where the Gaia binary's measured depth is larger.
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from backend.app import eclipses as E  # noqa: E402
from field_psf import ephemeris, psf  # noqa: E402

RESULTS = Path(__file__).parent / "experimental_results"
MAX_DWL_FRAC = 0.02   # out-of-eclipse partner within 2% in wavelength (SPHEREx resolution R ~ 40-130)


def _star(stars, sid):
    return next(i for i, s in enumerate(stars) if s["source_id"] == sid)


def controls(analysis, stars, j_eb, exclude, n=2):
    g_eb = stars[j_eb]["g_mag"]
    ok = [i for i, r in enumerate(analysis["stars"])
          if i not in exclude and not r.get("variable_flag") and (r.get("coverage") or 0) >= 0.8]
    return sorted(ok, key=lambda i: abs(stars[i]["g_mag"] - g_eb))[:n]


def which_eclipse(rec, eph):
    p, s, sc = rec.get("primary"), rec.get("secondary"), rec.get("phase_scan")
    sec_phase = E.secondary_phase(eph)
    best = ("primary", 0.0, p["depth"] if p else -1)
    if s and sec_phase is not None and s["depth"] > best[2]:
        best = ("secondary", sec_phase, s["depth"])
    if sc and sc["snr"] > 5 and sc["depth"] > best[2]:
        best = (f"deepest dip of the blind scan (phase {sc['phase']:.2f})", sc["phase"], sc["depth"])
    return best[0], best[1]


def fold(folder, lc, stars, rows, labels, title):
    phi = (lc["phi"] + 0.25) % 1 - 0.25
    fig, axes = plt.subplots(len(rows), 1, figsize=(9, 2.3 * len(rows)), sharex=True)
    for ax, j, lab in zip(axes, rows, labels):
        g = lc["gc"][:, j]
        sc = ax.scatter(phi, g, c=lc["wl"], s=7, cmap="turbo", vmin=0.75, vmax=5.0)
        ax.axhline(1, color="k", lw=0.5)
        lo, hi = np.nanpercentile(g, [1, 99])
        ax.set_ylim(min(lo, 0.85) - 0.03, max(hi, 1.1) + 0.03)
        ax.set_ylabel("flux / S(λ)")
        ax.set_title(lab, fontsize=9, loc="left")
    axes[-1].set_xlabel("orbital phase (primary eclipse at 0)")
    axes[-1].set_xlim(-0.25, 0.75)
    fig.colorbar(sc, ax=axes, label="wavelength (µm)", shrink=0.6)
    fig.suptitle(title, fontsize=10)
    fig.savefig(folder / "fold.png", dpi=100)
    plt.close(fig)


def pairs(frames_phi, det, wl, centre, half, clear):
    """(in, out) index pairs: each central-eclipse frame with the out-of-eclipse frame of the same detector nearest
    in wavelength."""
    x = np.abs((frames_phi - centre + 0.5) % 1 - 0.5)
    inside = np.where(x < half)[0]
    out = []
    for i in inside:
        cand = np.where(clear & (det == det[i]) & np.isfinite(wl))[0]
        if not len(cand) or not np.isfinite(wl[i]):
            continue
        k = cand[np.argmin(np.abs(wl[cand] - wl[i]))]
        if abs(wl[k] - wl[i]) <= MAX_DWL_FRAC * wl[i]:
            out.append((i, k))
    return out


def box_z(diff, x, y, r=1):
    """Mean over pairs of the (2r+1)^2-pixel box sum of the difference at (x, y), divided by its standard error."""
    i, j = int(round(y)), int(round(x))
    s = np.nansum(diff[:, max(i - r, 0):i + r + 1, max(j - r, 0):j + r + 1], axis=(1, 2))
    return round(float(s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))), 2) if len(s) > 2 else None


def diff_centroid(img, det, prs, shapes, start, n_boot=100, seed=1):
    """Where the missing light is: one PSF with free position fitted to the mean wavelength-matched difference image
    of all pairs (each pair scaled by its out-of-eclipse frame's peak), per detector with a common position.
    Errors by bootstrap over pairs. Model-light: no catalogue positions are used except as a starting point."""
    from scipy.optimize import least_squares
    dets = [d for d in sorted(set(det[i] for i, _ in prs)) if str(d) in shapes and sum(det[i] == d for i, _ in prs) >= 3]
    if not dets:
        return None
    per_det = {d: np.stack([(img[i] - img[k]) / np.nanmax(img[k]) for i, k in prs if det[i] == d]) for d in dets}

    def fit(stacks):
        means = {d: np.nanmean(v, 0) for d, v in stacks.items()}
        sems = {d: np.nanstd(v, 0, ddof=1) / np.sqrt(len(v)) for d, v in stacks.items()}

        def resid(p):
            x, y = p[:2]
            out = []
            for n, d in enumerate(dets):
                sh = shapes[str(d)]
                model = psf(means[d].shape, x + sh["dx"], y + sh["dy"], sh["sigma"], sh["wing_frac"], sh["wing_sigma"])
                r = (means[d] - (p[2 + 2 * n] * model + p[3 + 2 * n])) / sems[d]
                out.append(np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0).ravel())
            return np.concatenate(out)
        def linear_chi2(x, y):
            # amplitude and sky solved exactly per detector; only fits with missing light (amplitude < 0) count
            tot = 0.0
            for d in dets:
                sh = shapes[str(d)]
                w = 1 / sems[d]
                ok = np.isfinite(means[d]) & np.isfinite(w)
                m = psf(means[d].shape, x + sh["dx"], y + sh["dy"], sh["sigma"], sh["wing_frac"], sh["wing_sigma"])
                A = np.stack([m[ok] * w[ok], w[ok]], 1)
                coef, *_ = np.linalg.lstsq(A, means[d][ok] * w[ok], rcond=None)
                if coef[0] >= 0:
                    return np.inf
                tot += float(np.sum((means[d][ok] * w[ok] - A @ coef) ** 2))
            return tot

        if grid_start is None:
            xs = np.arange(start[0] - 8, start[0] + 8.01, 0.2)
            ys = np.arange(start[1] - 8, start[1] + 8.01, 0.2)
            chi = np.array([[linear_chi2(x, y) for x in xs] for y in ys])
            iy, ix = np.unravel_index(np.argmin(chi), chi.shape)
            x0, y0 = xs[ix], ys[iy]
        else:
            x0, y0 = grid_start
        p0 = [x0, y0] + [-0.1, 0.0] * len(dets)
        return least_squares(resid, p0).x

    grid_start = None
    best = fit(per_det)
    grid_start = (best[0], best[1])
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        s = {d: v[rng.integers(0, len(v), len(v))] for d, v in per_det.items()}
        boots.append(fit(s)[:2])
    boots = np.array(boots)
    return {"x": round(float(best[0]), 3), "y": round(float(best[1]), 3),
            "x_err": round(float(boots[:, 0].std()), 3), "y_err": round(float(boots[:, 1].std()), 3),
            "amplitudes": {f"D{d}": round(float(best[2 + 2 * n]), 4) for n, d in enumerate(dets)},
            "n_pairs": len(prs)}


def difference(folder, img, det, prs, marks, title):
    dets = [d for d in sorted(set(det.tolist())) if sum(det[i] == d for i, _ in prs) >= 3]
    if not dets:
        return None
    fig, axes = plt.subplots(2, len(dets), figsize=(2.6 * len(dets), 5.4), squeeze=False)
    summary, all_diffs = {}, []
    for c, d in enumerate(dets):
        sel = [(i, k) for i, k in prs if det[i] == d]
        diff = np.stack([(img[i] - img[k]) / np.nanmax(img[k]) for i, k in sel])
        mean = np.nanmean(diff, 0)
        sem = np.nanstd(diff, 0, ddof=1) / np.sqrt(np.sum(np.isfinite(diff), 0))
        z = mean / sem
        lim = np.nanpercentile(np.abs(mean), 99.5)
        axes[0, c].imshow(mean, origin="lower", cmap="RdBu", vmin=-lim, vmax=lim)
        axes[1, c].imshow(z, origin="lower", cmap="RdBu", vmin=-5, vmax=5)
        axes[0, c].set_title(f"D{d}: {len(sel)} pairs", fontsize=9)
        for ax in axes[:, c]:
            for (x, y, m, col) in marks:
                ax.plot(x, y, m, mfc="none", mec=col, ms=12, mew=1.5)
            ax.set_xticks([])
            ax.set_yticks([])
        summary[f"D{d}"] = {"pairs": len(sel), **{lab: box_z(diff, x, y)
                                                  for (x, y, _, _), lab in zip(marks, ("z_at_eb", "z_at_tic"))}}
        all_diffs.append(diff)
    if all_diffs:
        diff = np.concatenate(all_diffs)
        summary["all"] = {"pairs": len(diff), **{lab: box_z(diff, x, y)
                                                 for (x, y, _, _), lab in zip(marks, ("z_at_eb", "z_at_tic"))}}
    axes[0, 0].set_ylabel("mean in - out\n(fraction of peak)")
    axes[1, 0].set_ylabel("mean / std. error")
    fig.suptitle(title + "\nsquare: Gaia binary, circle: TIC star (red/blue = fainter/brighter in eclipse)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(folder / "difference.png", dpi=100)
    plt.close(fig)
    return summary


def flipbook(folder, img, wl, prs, marks, n=12, scale=8):
    if not prs:
        return
    pick = [prs[i] for i in np.linspace(0, len(prs) - 1, min(n, len(prs))).round().astype(int)]
    frames = []
    for i, k in pick:
        lo, hi = np.nanpercentile(img[k], [5, 99.7])
        for idx, tag in ((k, "OUT"), (i, "IN ECLIPSE")):
            a = np.clip((np.arcsinh((img[idx] - lo) / (hi - lo) * 10) / np.arcsinh(10)), 0, 1)
            a = np.nan_to_num(a[::-1]) * 255
            im = Image.fromarray(a.astype(np.uint8)).resize((a.shape[1] * scale, a.shape[0] * scale),
                                                            Image.NEAREST).convert("RGB")
            dr = ImageDraw.Draw(im)
            h = a.shape[0]
            for (x, y, m, col) in marks:
                cx, cy, r = (x + 0.5) * scale, (h - 0.5 - y) * scale, 2.2 * scale
                box = [cx - r, cy - r, cx + r, cy + r]
                (dr.rectangle if m == "s" else dr.ellipse)(box, outline=col, width=2)
            dr.text((6, 6), f"{tag}  {wl[idx]:.3f} µm", fill="yellow")
            frames.append(im)
    frames[0].save(folder / "flipbook.gif", save_all=True, append_images=frames[1:], duration=700, loop=0)


def main(name, tic, eb, target=None):
    folder = RESULTS / name
    meta = json.loads((folder / "meta.json").read_text())
    stars = json.loads((folder / "stars.json").read_text())
    analysis = json.loads((folder / "analysis.json").read_text())
    lc = np.load(folder / "lightcurves.npz")
    eph = ephemeris(tic, meta.get("eph_json"))
    j_eb = _star(stars, eb)
    c = meta["grid_size_px"] // 2
    j_tic = _star(stars, target) if target else min(range(len(stars)),
                                                    key=lambda i: np.hypot(stars[i]["x"] - c, stars[i]["y"] - c))
    ctrl = controls(analysis, stars, j_eb, {j_eb, j_tic})
    lab = lambda j, what: (f"{what}: Gaia DR3 {stars[j]['source_id']}, G {stars[j]['g_mag']:.2f}, "
                           f"scatter {analysis['stars'][j]['scatter_pct']}%")
    fold(folder, lc, stars, [j_eb, j_tic] + ctrl,
         [lab(j_eb, "Gaia eclipsing binary"), lab(j_tic, f"TIC {tic} (TESS-EBs source)")]
         + [lab(j, "control") for j in ctrl], f"{name}: SPHEREx phase-folded light curves")
    which, centre = which_eclipse(analysis["stars"][j_eb], eph)
    out = {"eclipse_used": which, "centre_phase": centre, "tic_star": stars[j_tic]["source_id"],
           "controls": [stars[j]["source_id"] for j in ctrl]}
    fr = np.load(folder / "frames.npz")
    if len(fr["mjd"]) == len(lc["mjd"]):
        phi = lc["phi"] % 1
        half = eph.prim_width / 3
        clear = E.out_of_eclipse(lc["phi"], eph) & (np.abs((phi - centre + 0.5) % 1 - 0.5) > 0.75 * eph.prim_width)
        prs = pairs(phi, fr["det"], fr["wl"], centre % 1, half, clear)
        marks = [(stars[j_eb]["x"], stars[j_eb]["y"], "s", "lime"), (stars[j_tic]["x"], stars[j_tic]["y"], "o", "magenta")]
        out["difference"] = difference(folder, fr["image"], fr["det"], prs, marks,
                                       f"{name}: SPHEREx {which} eclipse, wavelength-matched difference")
        flipbook(folder, fr["image"], fr["wl"], prs, marks)
        out["n_pairs"] = len(prs)
        cen = diff_centroid(fr["image"], fr["det"], prs, meta["shapes"],
                            ((stars[j_eb]["x"] + stars[j_tic]["x"]) / 2, (stars[j_eb]["y"] + stars[j_tic]["y"]) / 2))
        if cen:
            err = np.hypot(cen["x_err"], cen["y_err"])
            for lab, j in (("gaia_eb", j_eb), ("tic_star", j_tic)):
                d = float(np.hypot(cen["x"] - stars[j]["x"], cen["y"] - stars[j]["y"]))
                cen[f"dist_to_{lab}_px"] = round(d, 3)
                cen[f"dist_to_{lab}_sigma"] = round(d / err, 1) if err > 0 else None
            out["difference_centroid"] = cen
    else:
        out["difference"] = "frames.npz predates the all-frames format; re-run field_psf.py"
    (folder / "figures.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--tic", required=True)
    p.add_argument("--eb", required=True)
    p.add_argument("--target")
    a = p.parse_args()
    main(a.name, a.tic, a.eb, a.target)
