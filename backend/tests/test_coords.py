import pytest

from backend.app.coords import date_to_mjd, mjd_to_date, parse_coordinates

ONE_ARCSEC = 1 / 3600


def test_sexagesimal_with_letters():
    ra, dec = parse_coordinates("08h55m10.831s -07d14m42.53s")
    assert ra == pytest.approx(133.795129, abs=ONE_ARCSEC)
    assert dec == pytest.approx(-7.245147, abs=ONE_ARCSEC)


def test_sexagesimal_with_colons():
    ra, dec = parse_coordinates("08:55:10.831 -07:14:42.53")
    assert ra == pytest.approx(133.795129, abs=ONE_ARCSEC)
    assert dec == pytest.approx(-7.245147, abs=ONE_ARCSEC)


def test_decimal_degrees():
    ra, dec = parse_coordinates("43.2537 16.8814")
    assert ra == pytest.approx(43.2537)
    assert dec == pytest.approx(16.8814)


def test_positive_dec_with_plus_sign():
    ra, dec = parse_coordinates("02h53m00.9s +16d52m53s")
    assert ra == pytest.approx(43.253750, abs=ONE_ARCSEC)
    assert dec == pytest.approx(16.881389, abs=ONE_ARCSEC)


@pytest.mark.parametrize("bad", ["", "hello world", "400 10", "10 95", "12.5"])
def test_bad_input_raises(bad):
    with pytest.raises(ValueError):
        parse_coordinates(bad)


def test_date_to_mjd():
    assert date_to_mjd("2026-10-29") == pytest.approx(61342.0)
    assert date_to_mjd("2000-01-01T12:00:00") == pytest.approx(51544.5)


def test_mjd_to_date():
    assert mjd_to_date(60000.0).startswith("2023-02-25")


def test_round_trip():
    assert date_to_mjd(mjd_to_date(61201.25)) == pytest.approx(61201.25, abs=1e-6)
