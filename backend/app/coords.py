"""Turn what a user types into sky positions and times."""
import re

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

_SEXAGESIMAL = re.compile(r"[hmsd:]", re.IGNORECASE)


def parse_coordinates(text: str) -> tuple[float, float]:
    """Return (ra_deg, dec_deg) from "08h55m10.8s -07d14m42s", "08:55:10.8 -07:14:42" or "133.795 -7.245".

    Sexagesimal RA is read as hours, decimal numbers as degrees. Raises ValueError, never guesses.
    """
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError(f"Expected two values (RA and Dec), got: {text!r}")

    if _SEXAGESIMAL.search(text):
        try:
            coord = SkyCoord(parts[0], parts[1], unit=(u.hourangle, u.deg), frame="icrs")
        except (ValueError, u.UnitsError) as exc:
            raise ValueError(f"Could not read coordinates {text!r}: {exc}") from exc
        return float(coord.ra.deg), float(coord.dec.deg)

    try:
        ra, dec = float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise ValueError(f"Could not read coordinates {text!r}") from exc
    if not 0 <= ra < 360:
        raise ValueError(f"RA must be between 0 and 360 degrees, got {ra}")
    if not -90 <= dec <= 90:
        raise ValueError(f"Dec must be between -90 and +90 degrees, got {dec}")
    return ra, dec


def date_to_mjd(date: str) -> float:
    """"2026-10-29" or "2026-10-29T12:00:00" (UTC) -> Modified Julian Date."""
    return float(Time(date, scale="utc").mjd)


def mjd_to_date(mjd: float) -> str:
    """Modified Julian Date -> ISO text in UTC, e.g. "2023-02-25T00:00:00.000"."""
    return Time(mjd, format="mjd", scale="utc").isot


def mjd_to_year(mjd: float) -> float:
    """Modified Julian Date -> decimal year (e.g. 2025.62), used for proper motion."""
    return float(Time(mjd, format="mjd", scale="utc").jyear)
