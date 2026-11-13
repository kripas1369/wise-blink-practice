"""Offline tests for Eclipse mode: time and phase, the depth recipe on fake binaries with a known answer,
the null checks, the period search, and the cutout slimming. Real eclipse folders are checked for format."""
import io
import json
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from backend.app import archive, eclipse_depth as M, eclipses as E
from backend.app.config import DETECTORS
from backend.app.eclipse_build import FORMAT, analyse

ECLIPSE_DIR = Path("frontend/frames/eclipse")


def ephemeris(**kw) -> E.Ephemeris:
    base = dict(tess_id="0", ra=270.0, dec=66.56, pmra=0.0, pmdec=0.0, tmag=11.0, bjd0=2000.0, bjd0_err=1e-4,
                period=1.3, period_err=1e-6, morph=0.3, prim_pos=0.0, prim_width=0.1, prim_depth=0.3,
                sec_pos=0.5, sec_width=0.1, sec_depth=0.1, model="pf")
    return E.Ephemeris(**{**base, **kw})


# ---------- time and phase ----------

def test_btjd_at_the_ecliptic_pole_is_utc_plus_tdb_offset():
    """Earth moves in the ecliptic plane, so towards the pole the light-travel time is about 0 and only
    UTC -> TDB is left: 37 leap seconds + 32.184 s = 69.184 s (TDB - TT is below 2 ms)."""
    mjd = np.array([61000.0, 61100.0, 61200.0])
    naive = mjd + 2400000.5 - E.BTJD_OFFSET
    offset_s = (E.to_btjd(mjd, *E.NEP) - naive) * 86400
    assert np.allclose(offset_s, 69.184, atol=0.5)


def test_btjd_in_the_ecliptic_swings_by_the_light_travel_time():
    """In the ecliptic, the correction swings by about ±499 s (1 au / c) over a year."""
    mjd = np.linspace(61000, 61365, 50)
    naive = mjd + 2400000.5 - E.BTJD_OFFSET
    ltt = (E.to_btjd(mjd, 90.0, 23.44) - naive) * 86400 - 69.184
    assert 480 < ltt.max() < 510 and -510 < ltt.min() < -480


def test_phase_puts_primary_at_zero_and_wraps():
    e = ephemeris(prim_pos=0.02)
    t = e.bjd0 + e.period * (np.array([0, 1, 5, 7.5]) + 0.02)
    assert np.allclose(E.phase(t, e), [0, 0, 0, -0.5], atol=1e-9)
    assert E.secondary_phase(e) == pytest.approx(0.48)


def test_eclipse_parts():
    e = ephemeris()
    phi = np.array([0.0, 0.04, 0.06, 0.49, -0.47, 0.25])
    assert E.eclipse_part(phi, e).tolist() == [1, 1, 0, 2, 2, 0]
    assert E.eclipse_part(phi, e, 0.5).tolist() == [1, 0, 0, 2, 0, 0]
    assert E.out_of_eclipse(phi, e).tolist() == [False, False, False, False, False, True]


def test_phase_error_grows_with_cycles():
    e = ephemeris(period=2.0, period_err=1e-5, bjd0_err=0.001)
    assert e.phase_error(e.bjd0) == pytest.approx(0.0005)
    assert e.phase_error(e.bjd0 + 2000) == pytest.approx((1000 * 1e-5 + 0.001) / 2)


def test_selection_respects_the_budget_and_takes_eclipses():
    e = ephemeris()
    rng = np.random.default_rng(1)
    mjd = np.sort(rng.uniform(61000, 61500, 3000))
    ims = [archive.SpherexImage(f"o{i}", f"d{i}", 1, m, m + 0.001, 0.75, 1.09, "") for i, m in enumerate(mjd)]
    budget = {"primary": 40, "secondary": 25, "outside": 50}
    chosen = E.select_for_download(ims, e, *E.NEP, budget)
    phi = E.phase(E.to_btjd([im.mjd for im in chosen], *E.NEP), e)
    part = E.eclipse_part(phi, e)
    assert (part == 1).sum() == 40 and (part == 2).sum() == 25 and (part == 0).sum() == 50
    assert np.ptp(phi[part == 1]) > 0.08     # spread over the eclipse, not bunched


# ---------- the depth recipe on fake binaries ----------

def fake(eph, depth_fn, sec_depth=0.1, n=2400, noise=0.01, seed=3, ellipsoidal=0.0):
    rng = np.random.default_rng(seed)
    det = rng.integers(1, 7, n)
    wl = np.array([rng.uniform(*DETECTORS[d]) for d in det])
    btjd = rng.uniform(3600, 4200, n)
    phi = E.phase(btjd, eph)

    def shape(dphi, width):
        a = np.abs(dphi) / (width / 2)
        return np.clip((1 - a) / 0.4, 0, 1)      # flat bottom for |dphi| < 0.3 width, then a straight ingress

    sec = (phi - 0.5 + 0.5) % 1.0 - 0.5
    model = (1 - depth_fn(wl) * shape(phi, eph.prim_width) - sec_depth * shape(sec, eph.sec_width)
             + ellipsoidal * np.cos(4 * np.pi * phi))
    steady = 100 * wl ** -1.5
    flux = steady * model * (1 + noise * rng.normal(size=n))
    points = [{"det": int(d), "wl": float(w), "btjd": float(t), "flux": float(f), "err": float(noise * f),
               "n_flagged": 0} for d, w, t, f in zip(det, wl, btjd, flux)]
    return points, steady, det, wl


def test_recovers_a_depth_that_changes_with_wavelength():
    eph = ephemeris()
    depth = lambda wl: 0.30 - 0.06 * np.log(wl)
    points, *_ = fake(eph, depth)
    res = analyse(points, eph, pdm=False)
    rows = [r for r in res["depth"]["primary"] if r["depth"] is not None]
    assert len(rows) >= 10
    for r in rows:
        assert abs(r["depth"] - depth(r["wl_mean"])) < 4 * r["err"] + 0.003, r
    assert abs(res["checks"]["null"]["combined"]) < 4 * res["checks"]["null"]["combined_err"]
    sec = res["checks"]["secondary_combined"]
    assert abs(sec["combined"] - 0.1) < 4 * sec["combined_err"] + 0.003


def test_ellipsoidal_baseline_is_found_and_removed():
    eph = ephemeris()
    points, *_ = fake(eph, lambda wl: 0.2 + 0 * wl, ellipsoidal=0.03)
    res = analyse(points, eph, pdm=False)
    assert res["baseline"]["used"] and res["baseline"]["a2"] == pytest.approx(0.03, abs=0.005)
    comb = res["checks"]["primary_combined"]
    # depth below the baseline at phase 0, where cos 4πφ adds +3%: 1 - (1.03 - 0.2) / 1.03
    assert comb["combined"] == pytest.approx(1 - 0.83 / 1.03, abs=0.005)


def test_a_star_that_does_not_eclipse_has_zero_depth():
    eph = ephemeris()
    points, *_ = fake(eph, lambda wl: 0 * wl, sec_depth=0.0)
    res = analyse(points, eph, pdm=False)
    for key in ("primary_combined", "secondary_combined", "null"):
        c = res["checks"][key]
        assert abs(c["combined"]) < 4 * c["combined_err"], key


def test_field_stars_fold_to_zero():
    eph = ephemeris()
    points, _, det, wl = fake(eph, lambda wl: 0.25 + 0 * wl, n=1200)
    rng = np.random.default_rng(9)
    f = 50 * wl ** -1.0 * (1 + 0.01 * rng.normal(size=len(wl)))
    field = [{"source_id": "1", "g_mag": 15.0, "x": 3, "y": 4, "flux": f.tolist(), "err": (0.01 * f).tolist(),
              "n_flagged": [0] * len(f)}]
    res = analyse(points, eph, field, pdm=False)
    fs = res["checks"]["field_stars"]
    assert fs["n_bins"] == 1 and abs(fs["combined"]) < 4 * fs["combined_err"]


def test_period_search_finds_the_period_without_tess():
    eph = ephemeris(period=0.83)
    points, *_ = fake(eph, lambda wl: 0.3 + 0 * wl, n=900)
    res = analyse(points, eph)
    ps = res["checks"]["period_search"]
    assert ps["best_is"] in ("TESS period", "half the TESS period"), ps["best"]


def test_timing_finds_a_shifted_eclipse():
    """Fake data whose eclipse is 0.006 in phase late against the clock; the fit must find it."""
    eph = ephemeris()
    late = ephemeris(bjd0=eph.bjd0 + 0.006 * eph.period)
    points, *_ = fake(late, lambda wl: 0.3 + 0 * wl, n=3000)
    res = analyse(points, eph, pdm=False)
    t = res["checks"]["timing"]
    assert abs(t["delta_phase"] - 0.006) < 3 * t["err_phase"] + 0.001, t
    assert t["err_phase"] < 0.003
    on_time = analyse(fake(eph, lambda wl: 0.3 + 0 * wl, n=3000)[0], eph, pdm=False)["checks"]["timing"]
    assert abs(on_time["delta_phase"]) < 3 * on_time["err_phase"] + 0.001, on_time


def test_jitter_inflates_errors_to_match_the_scatter():
    rng = np.random.default_rng(2)
    g = 1 + rng.normal(0, 0.03, 4000)
    s = M.jitter(g, np.full(g.size, 0.01))
    assert s == pytest.approx(np.sqrt(0.03 ** 2 - 0.01 ** 2), rel=0.1)
    assert M.jitter(1 + rng.normal(0, 0.01, 4000), np.full(4000, 0.02)) == 0.0


# ---------- cutout slimming ----------

def test_dropping_the_psf_keeps_everything_else():
    hdus = fits.HDUList([fits.PrimaryHDU()] + [fits.ImageHDU(np.arange(12.).reshape(3, 4) + i, name=n)
                                               for i, n in enumerate(("IMAGE", "FLAGS", "VARIANCE", "ZODI", "PSF", "WCS-WAVE"))])
    hdus["IMAGE"].header["MJD-AVG"] = 61000.25
    buf = io.BytesIO()
    hdus.writeto(buf)
    out = Path(__file__).parent / "_slim_test.fits"
    try:
        archive._save_without_psf(buf.getvalue(), out)
        with fits.open(out) as h:
            assert [x.name for x in h] == ["PRIMARY", "IMAGE", "FLAGS", "VARIANCE", "ZODI", "WCS-WAVE"]
            assert h["IMAGE"].header["MJD-AVG"] == 61000.25
            assert np.array_equal(h["ZODI"].data, hdus["ZODI"].data)
    finally:
        out.unlink(missing_ok=True)


# ---------- prepared folders ----------

FOLDERS = sorted(ECLIPSE_DIR.glob("tic*/eclipse.json"))


@pytest.mark.parametrize("path", FOLDERS, ids=lambda p: p.parent.name)
def test_prepared_eclipse_folders(path):
    e = json.loads(path.read_text())
    assert e["format"] == FORMAT
    assert e["points"] and all(-0.5 <= p["phase"] < 0.5 for p in e["points"])
    for d, fr in e["frames"].items():
        for f in fr["frames"]:
            assert (path.parent / f["png"]).exists()
            assert f["png_n"] is None or (path.parent / f["png_n"]).exists()
    for d, diff in e["checks"]["difference_images"].items():
        assert diff is None or (path.parent / diff["png"]).exists()
