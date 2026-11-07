"""Known asteroids and comets inside a frame at each exposure's time, for the "inside one visit" view.

Two NASA JPL services:
1. Small-Body Identification API, first pass (https://ssd-api.jpl.nasa.gov/doc/sb_ident.html): every known
   object around the field, with rough two-body positions and rates. One request per group of exposures
   within CLUSTER_HOURS. Its accurate second pass took 94 s per request with a 0.1° box on 7 Nov 2026 and
   timed out with larger boxes, so it is not used here; the first pass put (32455) 74″ from Horizons'
   position, so it only picks candidates (with FIELD_MARGIN_DEG of room).
2. Horizons API (https://ssd-api.jpl.nasa.gov/doc/horizons.html, served at ssd.jpl.nasa.gov): precise geocentric positions of each
   candidate at every exposure time, moved to SPHEREx's place (X_SC.. in the exposure header, km, "GEOCENTER";
   axes assumed ICRF, as in spots.py). Its distance (delta) makes that parallax correction exact.

Only objects brighter than FIELD_VMAX are asked for: a single SPHEREx exposure does not reach fainter ones.
"""
import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from astropy.coordinates import Angle

from backend.app.known_objects import CACHE, Unavailable, ask, dec_text, ra_text

HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
FIELD_VMAX = 20.5          # ours: a single exposure reaches about AB 18-19 (recovery.json), V 20.5 leaves room
FIELD_MARGIN_DEG = 0.15    # ours: room for the first pass's rough positions and the motion within a group
CLUSTER_HOURS = 12.0
REUSE_HOURS = 6.0          # ours: a cached first pass this close in time still covers the frame (rates applied)
AU_KM = 149_597_870.7
TIMEOUT_S = 150
MAX_FAILURES = 2


def parse_radec(ra: str, dec: str) -> tuple[float, float]:
    """JPL's '05:07:34.57' and '+30 27\\'38.4"' in degrees."""
    d = dec.strip().replace("'", "m").replace('"', "s")
    d = re.sub(r"^([+-]?\d+)\s+", r"\1d", d)
    return float(Angle(ra, unit="hourangle").deg), float(Angle(d, unit="deg").deg)


def _number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def cached_first_pass(jd: float, ra: float, dec: float) -> tuple[list[dict], float] | None:
    """A cached first pass of the same field within REUSE_HOURS of jd (another band's exposures), with its time."""
    best = None
    for path in CACHE.glob(f"field1_*_{ra:.4f}_{dec:+.4f}.json"):
        t = float(path.name.split("_")[1])
        if abs(t - jd) * 24 <= REUSE_HOURS and (best is None or abs(t - jd) < abs(best[1] - jd)):
            best = (path, t)
    return (json.loads(best[0].read_text()), best[1]) if best else None


def first_pass(observer: dict, ra: float, dec: float) -> tuple[list[dict], float]:
    """Objects brighter than FIELD_VMAX around (ra, dec) from sb_ident's first pass, and the JD they are for."""
    jd = observer["mjd"] + 2400000.5
    if reused := cached_first_pass(jd, ra, dec):
        return reused
    (ra_sent, _), (dec_sent, _) = ra_text(ra), dec_text(dec)
    params = {"xobs": ",".join(f"{v}" for v in observer["xyz_km"] + observer["vxyz_kms"]),
              "obs-time": f"{jd:.6f}",
              "fov-ra-center": ra_sent, "fov-dec-center": dec_sent,
              "fov-ra-hwidth": f"{FIELD_MARGIN_DEG / max(math.cos(math.radians(dec)), 0.01):.4f}",
              "fov-dec-hwidth": f"{FIELD_MARGIN_DEG}", "mag-required": "true"}
    cached = CACHE / f"field1_{params['obs-time']}_{ra:.4f}_{dec:+.4f}.json"
    body = ask(params)
    fields = body.get("fields_first") or []
    col = lambda part: next(i for i, f in enumerate(fields) if part in f)
    i_name, i_ra, i_dec = col("Object name"), col("Astrometric RA"), col("Astrometric Dec")
    i_v, i_rra, i_rdec = col("Visual magnitude"), col("RA rate"), col("Dec rate")
    out = []
    for r in body.get("data_first_pass") or []:
        v = _number(r[i_v])
        if v is None or v > FIELD_VMAX:
            continue
        o_ra, o_dec = parse_radec(r[i_ra], r[i_dec])
        out.append({"name": str(r[i_name]).strip(), "ra": o_ra, "dec": o_dec, "v_mag": v,
                    "ra_rate": _number(r[i_rra]) or 0.0, "dec_rate": _number(r[i_rdec]) or 0.0})
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(out) + "\n")
    return out, float(params["obs-time"])


def offset_arcsec(ra: float, dec: float, ra0: float, dec0: float) -> tuple[float, float]:
    """(east, north) of (ra, dec) from (ra0, dec0), small-angle."""
    return (((ra - ra0 + 180) % 360 - 180) * math.cos(math.radians(dec0)) * 3600, (dec - dec0) * 3600)


def horizons_command(name: str) -> str:
    """Horizons COMMAND for an sb_ident name: '32455 (2000 SW60)', '(2020 RL59)', '29P/Schwassmann-Wachmann',
    'C/2023 A3 (Tsuchinshan)'."""
    if m := re.match(r"^(\d+)\s*(\(|$)", name):
        return f"{m.group(1)};"
    if m := re.match(r"^(\d+[PI])/", name):
        return f"DES={m.group(1)};CAP;NOFRAG;"
    if m := re.match(r"^\((.+)\)$", name):
        return f"DES={m.group(1)};"
    designation = name.split(" (")[0].strip()
    return f"DES={designation};CAP;NOFRAG;"


def horizons(name: str, jds: list[float]) -> list[dict]:
    """Geocentric astrometric RA/Dec (ICRF), distance and magnitude of one object at each Julian date (UT)."""
    command = horizons_command(name)
    key = hashlib.sha1(f"{command}|{','.join(f'{j:.6f}' for j in jds)}".encode()).hexdigest()[:16]
    cached = CACHE / "horizons" / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    params = {"format": "json", "COMMAND": f"'{command}'", "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
              "EPHEM_TYPE": "OBSERVER", "CENTER": "'500@399'", "TLIST_TYPE": "JD",
              "TLIST": " ".join(f"'{j:.6f}'" for j in jds), "QUANTITIES": "'1,3,9,20'",
              "ANG_FORMAT": "DEG", "CSV_FORMAT": "YES", "EXTRA_PREC": "YES"}
    url = f"{HORIZONS}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as resp:
            body = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Unavailable(f"could not reach JPL Horizons ({exc})")
    text = body.get("result", "")
    start, end = text.find("$$SOE"), text.find("$$EOE")
    if start < 0 or end < 0:
        raise Unavailable(f"JPL Horizons gave no ephemeris for {name!r}")
    header_line = text[:start].strip().splitlines()[-2]
    names = [h.strip() for h in header_line.split(",")]
    idx = lambda *parts: next(i for i, h in enumerate(names) if any(h.startswith(p) for p in parts))
    i_ra, i_dec, i_delta = idx("R.A."), idx("DEC"), idx("delta")
    i_rra, i_rdec, i_mag = idx("dRA*cosD"), idx("d(DEC)/dt"), idx("APmag", "T-mag")
    rows = []
    for line in text[start + 5:end].strip().splitlines():
        c = [x.strip() for x in line.split(",")]
        rows.append({"ra": float(c[i_ra]), "dec": float(c[i_dec]), "delta_au": float(c[i_delta]),
                     "mag": _number(c[i_mag]), "ra_rate": float(c[i_rra]), "dec_rate": float(c[i_rdec])})
    if len(rows) != len(jds):
        raise Unavailable(f"JPL Horizons gave {len(rows)} positions for {len(jds)} times ({name!r})")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(rows) + "\n")
    return rows


def from_spherex(ra: float, dec: float, delta_au: float, xyz_km: list[float]) -> tuple[float, float]:
    """A geocentric direction and distance seen from SPHEREx's geocentric position instead (parallax)."""
    r, d = math.radians(ra), math.radians(dec)
    v = np.array([math.cos(d) * math.cos(r), math.cos(d) * math.sin(r), math.sin(d)]) * delta_au * AU_KM
    t = v - np.array(xyz_km)
    return math.degrees(math.atan2(t[1], t[0])) % 360, math.degrees(math.asin(t[2] / np.linalg.norm(t)))


def clusters(exposures: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    for e in sorted(exposures, key=lambda e: e["mjd"]):
        if not out or (e["mjd"] - out[-1][0]["mjd"]) * 24 > CLUSTER_HOURS:
            out.append([])
        out[-1].append(e)
    return out


def objects_in_exposures(exposures: list[dict], ra: float, dec: float, grid, size: int) -> dict[int, dict]:
    """{k: answer} for exposures [{"k", "mjd", "observer"}]; answer outcome is objects / none / unavailable."""
    answers: dict[int, dict] = {}
    half = size / 2 * abs(grid.wcs.cdelt[1]) * 3600 * math.sqrt(2)
    room = half + FIELD_MARGIN_DEG * 3600
    failures = 0
    for group in clusters(exposures):
        with_observer = [e for e in group if e["observer"].get("available")]
        for e in group:
            if not e["observer"].get("available"):
                answers[e["k"]] = {"outcome": "unavailable", "reason": e["observer"].get("reason", "no SPHEREx position")}
        if not with_observer:
            continue
        if failures >= MAX_FAILURES:
            for e in with_observer:
                answers[e["k"]] = {"outcome": "unavailable", "reason": "JPL did not answer earlier requests, so it was not asked again"}
            continue
        mid = sum(e["mjd"] for e in with_observer) / len(with_observer)
        ref = min(with_observer, key=lambda e: abs(e["mjd"] - mid))
        try:
            found, found_jd = first_pass(ref["observer"], ra, dec)
            failures = 0
        except Unavailable as exc:
            failures += 1
            for e in with_observer:
                answers[e["k"]] = {"outcome": "unavailable", "reason": f"JPL small-body search: {exc}"}
            continue
        wanted: dict[str, list[dict]] = {}
        for o in found:
            east0, north0 = offset_arcsec(o["ra"], o["dec"], ra, dec)
            for e in with_observer:
                hours = (e["observer"]["mjd"] + 2400000.5 - found_jd) * 24
                east, north = east0 + o["ra_rate"] * hours, north0 + o["dec_rate"] * hours
                if abs(east) <= room and abs(north) <= room:
                    wanted.setdefault(o["name"], []).append(e)
        per_exposure: dict[int, list[dict]] = {e["k"]: [] for e in with_observer}
        problems = []
        for name, exps in wanted.items():
            try:
                rows = horizons(name, [e["observer"]["mjd"] + 2400000.5 for e in exps])
            except Unavailable as exc:
                problems.append(str(exc))
                continue
            for e, row in zip(exps, rows):
                o_ra, o_dec = from_spherex(row["ra"], row["dec"], row["delta_au"], e["observer"]["xyz_km"])
                x, y = (float(v) for v in grid.world_to_pixel_values(o_ra, o_dec))
                if -1.5 <= x <= size + 0.5 and -1.5 <= y <= size + 0.5:
                    per_exposure[e["k"]].append({
                        "name": name, "x": round(x, 2), "y": round(size - 1 - y, 2),
                        "ra": round(o_ra, 6), "dec": round(o_dec, 6), "mag": row["mag"],
                        "rate_arcsec_per_h": round(math.hypot(row["ra_rate"], row["dec_rate"]), 2),
                        "rate_east_north": [round(row["ra_rate"], 2), round(row["dec_rate"], 2)],
                        "distance_au": round(row["delta_au"], 4)})
        for e in with_observer:
            objs = sorted(per_exposure[e["k"]], key=lambda o: (o["mag"] is None, o["mag"] or 0))
            answers[e["k"]] = {"outcome": "objects" if objs else "none", "objects": objs,
                               "n_candidates": len(wanted), "problems": problems[:3]}
    return answers
