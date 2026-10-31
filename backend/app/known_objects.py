"""Known-object check: the known asteroids and comets NASA JPL puts near a spot at its observation time.

JPL Small-Body Identification API (https://ssd-api.jpl.nasa.gov/doc/sb_ident.html, version 1.1). The
observer is SPHEREx itself: its geocentric position and velocity from the exposure's header (spots.py),
because JPL refuses the geocentre ("never 500") and SPHEREx is ~7,000 km from it, which moves a
main-belt asteroid by up to about a pixel.

Three answers only: "match" (a known object within 2 px), "no_match" (none within 2 px; this does not
make the spot a new object) and "unavailable" (JPL did not answer, or we lack the observer). On
31 Oct 2026 JPL's accurate second pass failed for every request we sent, even the example in its own
documentation (HTTP 500 "unexpected error" or 400 with no message), while the first pass (two-body
orbits, rougher) answered when the time was given as a Julian date; so the second pass is tried first
and the first pass is the labelled fallback.
"""
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from backend.app.config import CACHE_DIR

API = "https://ssd-api.jpl.nasa.gov/sb_ident.api"
SEARCH_HALF_DEG = 0.05     # ours: a 6′ × 6′ box around the spot
MATCH_PX = 2.0             # ours
TIMEOUT_S = 150
CACHE = CACHE_DIR / "known_objects"


class Unavailable(Exception):
    pass


def ra_text(ra: float) -> tuple[str, float]:
    """JPL's hh-mm-ss, whole seconds (requests with decimal seconds failed on 31 Oct 2026), and its value."""
    seconds = round((ra % 360) / 15 * 3600) % 86400
    hh, rem = divmod(seconds, 3600)
    mm, ss = divmod(rem, 60)
    return f"{hh:02d}-{mm:02d}-{ss:02d}", seconds / 3600 * 15


def dec_text(dec: float) -> tuple[str, float]:
    seconds = round(abs(dec) * 3600)
    dd, rem = divmod(seconds, 3600)
    mm, ss = divmod(rem, 60)
    return f"{'M' if dec < 0 else ''}{dd:02d}-{mm:02d}-{ss:02d}", math.copysign(seconds / 3600, dec)


def ask(params: dict) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as exc:
        try:
            message = json.load(exc).get("message") or "no message"
        except Exception:
            message = "no message"
        raise Unavailable(f"JPL answered HTTP {exc.code} ({message})")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Unavailable(f"could not reach JPL ({exc})")
    if "code" in body and "signature" not in body:
        raise Unavailable(f"JPL answered code {body['code']} ({body.get('message') or 'no message'})")
    return body


def _number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def rows(body: dict, which: str, spot_offset: tuple[float, float]) -> list[dict]:
    """Objects with their distance from the spot. JPL gives offsets (″) from the box centre we sent; the
    spot is `spot_offset` (″, east and north) from that centre. We assume JPL's offsets are object minus
    centre, east and north positive (the documentation does not say)."""
    fields = body.get(f"fields_{which}") or []
    data = body.get(f"data_{which}_pass") or []

    def col(part):
        return next((i for i, f in enumerate(fields) if part in f), None)

    idx = {k: col(p) for k, p in [("name", "Object name"), ("ra", "Astrometric RA"), ("dec", "Astrometric Dec"),
                                  ("d_ra", "center RA"), ("d_dec", "center Dec"),
                                  ("vmag", "Visual magnitude"), ("ra_rate", "RA rate"),
                                  ("dec_rate", "Dec rate"), ("err_ra", "error RA"), ("err_dec", "error Dec")]}
    out = []
    for r in data:
        get = lambda k: r[idx[k]] if idx[k] is not None and idx[k] < len(r) else None
        rate = [_number(get("ra_rate")), _number(get("dec_rate"))]
        d_ra, d_dec = _number(get("d_ra")), _number(get("d_dec"))
        distance = (round(math.hypot(d_ra - spot_offset[0], d_dec - spot_offset[1]), 1)
                    if d_ra is not None and d_dec is not None else None)
        out.append({"name": str(get("name")).strip(), "ra": get("ra"), "dec": get("dec"),
                    "distance_arcsec": distance, "v_mag": _number(get("vmag")),
                    "rate_arcsec_per_h": round(math.hypot(*rate), 2) if None not in rate else None,
                    "est_error_arcsec": [_number(get("err_ra")), _number(get("err_dec"))]
                    if idx["err_ra"] is not None else None})
    return out


def check(spot: dict, observer: dict, pixel_arcsec: float) -> dict:
    match_arcsec = round(MATCH_PX * pixel_arcsec, 1)
    base = {"match_radius_arcsec": match_arcsec, "match_rule": f"within {MATCH_PX:g} px (ours)",
            "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    if not observer.get("available"):
        return {**base, "outcome": "unavailable", "reason": f"no SPHEREx position for this visit: {observer.get('reason')}"}
    (ra_sent, ra_c), (dec_sent, dec_c) = ra_text(spot["ra"]), dec_text(spot["dec"])
    d_ra = ((spot["ra"] - ra_c + 180) % 360 - 180) * math.cos(math.radians(spot["dec"])) * 3600
    spot_offset = (d_ra, (spot["dec"] - dec_c) * 3600)
    params = {"xobs": ",".join(f"{v}" for v in observer["xyz_km"] + observer["vxyz_kms"]),
              "obs-time": f"{observer['mjd'] + 2400000.5:.6f}",
              "fov-ra-center": ra_sent, "fov-dec-center": dec_sent,
              "fov-ra-hwidth": f"{SEARCH_HALF_DEG / max(math.cos(math.radians(spot['dec'])), 0.01):.4f}",
              "fov-dec-hwidth": f"{SEARCH_HALF_DEG}", "mag-required": "false"}
    key = f"{params['obs-time']}_{spot['ra']:.5f}_{spot['dec']:+.5f}"
    cached = CACHE / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    notes = [f"Observer: SPHEREx at the time of exposure {observer['obs_id']} ({observer['system']}).",
             f"Box centre sent to JPL rounded to whole seconds ({ra_sent}, {dec_sent}); distances are corrected "
             "back to the spot, assuming JPL's offsets are east and north positive.",
             f"The add-up of this visit spans {observer['exposures_span_hours']} h; an object moving faster than "
             f"{match_arcsec / max(observer['exposures_span_hours'], 0.01):.2f}″/h moves more than the match radius in that time."]
    try:
        body = ask({**params, "two-pass": "true", "suppress-first-pass": "true"})
        found, used = rows(body, "second", spot_offset), "second pass (numerical orbits)"
    except Unavailable as second:
        try:
            body = ask(params)
        except Unavailable as first:
            return {**base, "outcome": "unavailable", "reason": f"second pass: {second}; first pass: {first}"}
        found, used = rows(body, "first", spot_offset), "first pass (two-body orbits, rougher)"
        notes.append(f"JPL's accurate second pass failed ({second}), so this uses the first pass.")
    box = SEARCH_HALF_DEG * 3600 * math.sqrt(2)
    near = sorted((r for r in found if r["distance_arcsec"] is not None and r["distance_arcsec"] <= box),
                  key=lambda r: r["distance_arcsec"])
    matches = [r for r in near if r["distance_arcsec"] <= match_arcsec]
    result = {**base, "outcome": "match" if matches else "no_match", "pass_used": used,
              "matches": matches, "nearby": near[:5], "n_in_box": len(near), "search_half_deg": SEARCH_HALF_DEG,
              "jpl_version": body.get("signature", {}).get("version"), "notes": notes}
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(result, indent=1) + "\n")
    return result
