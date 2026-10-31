"""Star name -> position and proper motion, from SIMBAD (main server first, then the mirror)."""
import numpy as np
from astroquery.simbad import Simbad, conf

from backend.app.config import SIMBAD_SERVERS


TIMEOUT_SECONDS = 15

# The server that answered last time is tried first, so a dead server costs one timeout, not one per name.
_servers = list(SIMBAD_SERVERS)


class ResolverUnavailable(RuntimeError):
    """No SIMBAD server answered."""


def _value(row, name):
    value = row[name]
    if value is np.ma.masked or (isinstance(value, float) and np.isnan(value)):
        return None
    return float(value)


def resolve_name(name: str) -> dict:
    """Return {"name", "simbad_id", "ra", "dec", "pmra", "pmdec", "epoch", "server"}.

    ra/dec are SIMBAD's ICRS position for epoch J2000. pmra (already times cos dec) and pmdec are
    in mas/yr, or None when SIMBAD has no proper motion. Raises LookupError if the name is unknown
    and ResolverUnavailable if no server answers. Never guesses.
    """
    name = name.strip()
    if not name:
        raise LookupError("Empty name")

    errors = []
    for server in list(_servers):
        try:
            with conf.set_temp("server", server), conf.set_temp("timeout", TIMEOUT_SECONDS):
                simbad = Simbad()
                simbad.add_votable_fields("pmra", "pmdec")
                table = simbad.query_object(name)
        except Exception as exc:  # network errors differ between astroquery versions
            errors.append(f"{server}: {exc.__class__.__name__}")
            continue
        _servers.remove(server)
        _servers.insert(0, server)

        if table is None or len(table) == 0:
            raise LookupError(f"{name!r} was not found in SIMBAD")
        row = table[0]
        cols = {c.lower(): c for c in table.colnames}
        return {
            "name": name,
            "simbad_id": str(row[cols["main_id"]]),
            "ra": float(row[cols["ra"]]),
            "dec": float(row[cols["dec"]]),
            "pmra": _value(row, cols["pmra"]),
            "pmdec": _value(row, cols["pmdec"]),
            "epoch": 2000.0,
            "server": server,
        }

    raise ResolverUnavailable("No SIMBAD server answered: " + "; ".join(errors))
