"""Move a star's position from one date to another using its proper motion."""
import math

MAS_PER_DEG = 3.6e6


def position_at(
    ra: float, dec: float, pmra_mas: float, pmdec_mas: float, from_year: float, to_year: float
) -> tuple[float, float]:
    """Return (ra, dec) in degrees at `to_year`, given the position at `from_year`.

    `pmra_mas` is the motion along RA already multiplied by cos(dec) (the Gaia and SIMBAD convention),
    in milliarcseconds per year. A straight-line move is accurate to well under one SPHEREx pixel
    for the decades we need, except very close to the celestial poles.
    """
    years = to_year - from_year
    cos_dec = math.cos(math.radians(dec))
    if cos_dec < 1e-6:
        raise ValueError("Position is too close to a celestial pole for a straight-line move")
    new_ra = (ra + pmra_mas * years / MAS_PER_DEG / cos_dec) % 360.0
    new_dec = dec + pmdec_mas * years / MAS_PER_DEG
    return new_ra, new_dec


def separation_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Angle between two sky positions, in arcseconds (haversine formula)."""
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(h))) * 3600.0
