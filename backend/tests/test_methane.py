import numpy as np
import pytest

from backend.app import methane as M

SIZE = 29


def gaussian(x, y, peak, fwhm=1.0):
    yy, xx = np.indices((SIZE, SIZE))
    s = fwhm / 2.355
    return peak * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s ** 2))


def exposures(wls, sources, mjd0=60000.0, noise=0.01, seed=0):
    """Synthetic exposures; sources = [(x, y, flux_at(wl))] with F_nu in MJy/sr at the peak."""
    rng = np.random.default_rng(seed)
    n = len(wls)
    image = np.zeros((n, SIZE, SIZE))
    for k, wl in enumerate(wls):
        for x, y, f in sources:
            image[k] += gaussian(x, y, f(wl))
        image[k] += rng.normal(0, noise, (SIZE, SIZE))
    return {"image": image, "sigma": np.full((n, SIZE, SIZE), noise), "bad": np.zeros((n, SIZE, SIZE), bool),
            "has_value": np.ones((n, SIZE, SIZE), bool), "mjd": mjd0 + np.arange(n) * 0.1,
            "wl_um": np.array(wls, float), "obs_id": [f"e{k}" for k in range(n)]}


def normal_star(peak_at_4um):
    return lambda wl: peak_at_4um * (wl / 4.0) ** -2


def methane_dwarf(peak_at_4um, depth=0.15):
    return lambda wl: peak_at_4um * (depth if wl < 3.6 else 1.0)


def test_star_scale_makes_a_rayleigh_jeans_star_flat():
    f = normal_star(1.0)
    assert f(3.3) * M.star_scale(3.3) == pytest.approx(f(4.05) * M.star_scale(4.05))


def test_a_normal_star_fades_and_a_methane_dwarf_glows():
    sources = [(8, 8, normal_star(2.0)), (20, 20, methane_dwarf(1.0))]
    a = M.stack(exposures([3.2, 3.3, 3.4], sources), [0, 1, 2])
    b = M.stack(exposures([3.95, 4.05, 4.15], sources, seed=1), [0, 1, 2])
    z = M.vision(a, b, 1.0)
    assert abs(z[8, 8]) < M.NORMAL_SIGMA
    assert z[20, 20] > M.GLOW_SIGMA
    c = M.colour(M.flux(a, 20, 20), M.flux(b, 20, 20), 1.0)
    assert M.methane_verdict(c)["status"] == "glows"
    assert c["excess"] > M.METHANE_EXCESS
    assert M.methane_verdict(M.colour(M.flux(a, 8, 8), M.flux(b, 8, 8), 1.0))["status"] == "normal"


def test_systematic_share_keeps_a_bright_star_with_a_small_mismatch_from_glowing():
    sources = [(14, 14, normal_star(50.0))]
    a = M.stack(exposures([3.3], sources), [0])
    b = M.stack(exposures([4.05], [(14, 14, lambda wl: 1.03 * normal_star(50.0)(wl))], seed=1), [0])
    assert M.vision(a, b, 1.0, systematic=0.0)[14, 14] > M.GLOW_SIGMA
    assert M.vision(a, b, 1.0, systematic=0.05)[14, 14] < M.GLOW_SIGMA


def test_flagged_pixels_are_left_out_of_the_stack():
    ex = exposures([3.3, 3.3], [(14, 14, normal_star(1.0))])
    ex["image"][1, 14, 14] = 1e6
    ex["bad"][1, 14, 14] = True
    s = M.stack(ex, [0, 1])
    assert s["image"][14, 14] < 10


def test_calibration_needs_enough_field_stars():
    few = [(14, 14, methane_dwarf(1.0)), (6, 6, normal_star(3.0))]
    a = M.stack(exposures([3.3], few), [0])
    b = M.stack(exposures([4.05], few, seed=1), [0])
    cal = M.calibrate(a, b, avoid=[(14, 14)])
    assert cal["k"] == 1.0 and cal["n_sources"] == 1 and "Rayleigh-Jeans" in cal["rule"]
    many = few + [(22, 6, normal_star(2.0)), (6, 22, normal_star(4.0)), (22, 22, normal_star(2.5))]
    a = M.stack(exposures([3.3], many), [0])
    b = M.stack(exposures([4.05], [(x, y, lambda wl, f=f: 1.2 * f(wl)) for x, y, f in many], seed=1), [0])
    cal = M.calibrate(a, b, avoid=[(14, 14)])
    assert cal["n_sources"] == 4
    assert cal["k"] == pytest.approx(1.2, rel=0.05)


def test_verdict_rules():
    base = {"testable": True, "excess_is_lower_limit": False, "window_snr": 50}
    assert M.methane_verdict({**base, "excess": 3.0, "glow_sigma": 20})["status"] == "glows"
    assert M.methane_verdict({**base, "excess": 1.4, "glow_sigma": 8})["status"] == "unclear"
    assert M.methane_verdict({**base, "excess": 3.0, "glow_sigma": 4})["status"] == "unclear"
    assert M.methane_verdict({**base, "excess": 1.0, "glow_sigma": 0.5})["status"] == "normal"
    assert M.methane_verdict({**base, "excess": 0.5, "glow_sigma": -6})["status"] == "bluer"
    assert M.methane_verdict({**base, "window_snr": 3, "excess": 9, "glow_sigma": 3})["status"] == "too_faint"
    out = M.methane_verdict({"testable": False}, "The target is too bright.")
    assert out == {"status": "not_testable", "text": "The target is too bright."}


def test_an_undetected_methane_band_gives_a_lower_limit():
    c = M.colour({"flux_mjy": 0.01, "err_mjy": 0.05}, {"flux_mjy": 2.0, "err_mjy": 0.1}, 1.0)
    assert c["excess_is_lower_limit"] and c["excess_err"] is None
    assert c["excess"] == pytest.approx(2.0 / (0.01 + 0.15), rel=1e-3)
    assert "at least" in M.methane_verdict(c)["text"]


def test_a_circle_with_no_value_is_not_testable():
    hole = {"flux_mjy": None, "err_mjy": None, "no_value": True}
    assert M.colour(hole, {"flux_mjy": 2.0, "err_mjy": 0.1}, 1.0) == {"testable": False}
    assert M.colour({"flux_mjy": 2.0, "err_mjy": 0.1}, hole, 1.0) == {"testable": False}


def test_excess_error_includes_the_normal_star_colour_uncertainty():
    c = M.colour({"flux_mjy": 1.0, "err_mjy": 0.001}, {"flux_mjy": 5.0, "err_mjy": 0.001}, 1.0, systematic=0.1)
    assert c["excess"] == 5.0 and c["excess_err"] == pytest.approx(0.5, abs=0.01)


def test_visits_follow_the_archive_rule():
    a = {"mjd": np.array([100.0, 101.0, 300.0])}
    b = {"mjd": np.array([102.0, 299.0, 600.0])}
    groups = M.group_visits(a, b)
    assert [(g["a"], g["b"]) for g in groups] == [([0, 1], [0]), ([2], [1]), ([], [2])]


def test_saturated_share_counts_core_holes_at_the_target():
    ex = exposures([3.3] * 4, [])
    ex["has_value"][:3, 14, 14] = False
    assert M.saturated_share(ex, lambda t: (14.0, 14.0)) == 0.75
    assert M.saturated_share(ex, lambda t: (4.0, 4.0)) == 0.0
    ex["bad"][:2, 14, 15] = True
    assert M.saturated_share(ex, lambda t: (14.0, 14.0), "bad") == 0.5


def test_combined_text_never_claims_a_discovery():
    text = M.combined_text("glows", {"status": "agrees"})
    assert "brown dwarf" in text and "no discovery" in text
    assert "not a methane brown dwarf" in M.combined_text("normal", {"status": "agrees"})
    assert "could not be checked" in M.combined_text("glows", {"status": "no_gaia_target", "reason": "No Gaia star."})


def test_null_test_widens_the_noise_when_neighbouring_pixels_share_it():
    white_a = M.stack(exposures([3.3], [], seed=3), [0])
    white_b = M.stack(exposures([4.05], [], seed=4), [0])
    assert M.null_test(white_a, white_b, 1.0, 0.05, [(14, 14)])["factor"] < 1.4

    def blocky(seed):
        ex = exposures([3.3], [], seed=seed)
        small = np.random.default_rng(seed).normal(0, 0.01, (SIZE // 3 + 1, SIZE // 3 + 1))
        ex["image"][0] = np.kron(small, np.ones((3, 3)))[:SIZE, :SIZE]
        return M.stack(ex, [0])

    null = M.null_test(blocky(5), blocky(6), 1.0, 0.05, [(14, 14)])
    assert null["factor"] > 1.5 and null["n_places"] >= M.MIN_NULL_PLACES
    c = M.colour({"flux_mjy": 1.0, "err_mjy": 0.1}, {"flux_mjy": 3.0, "err_mjy": 0.1}, 1.0, 0.0, noise_factor=2.0)
    assert c["glow_sigma"] == pytest.approx(2.0 / (2.0 * np.hypot(0.1, 0.1)), abs=0.05)


def test_spread_keeps_first_and_last():
    picked = M.spread(list(range(1000)), 150)
    assert picked[0] == 0 and picked[-1] == 999 and len(picked) == 150
