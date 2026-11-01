"""Which way do JPL's "Dist. from center RA/Dec" point? One real check against a bright asteroid.

    python scripts/check_jpl_offsets.py

1. JPL Horizons: where 1 Ceres is, seen from Maunakea (MPC 568), at a fixed time.
2. JPL Small-Body Identification, with the box centre moved on purpose 60″ east and 40″ north of Ceres.
3. Compare JPL's offsets with the offsets we compute from the RA/Dec JPL gives for Ceres in the same answer.
If JPL's offsets are object minus centre, east and north positive, Ceres must come out near (−60″, −40″).
"""
import json
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.known_objects import dec_text, ra_text  # noqa: E402

JD = "2461000.5"          # 2025-11-21 00:00 TT, inside SPHEREx's survey
SHIFT = (60.0, 40.0)      # ″ east, north: the box centre minus Ceres


def get(url: str, params: dict) -> dict:
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=150) as resp:
        return json.load(resp)


def sexagesimal(text: str, hours: bool) -> float:
    sign = -1 if text.strip().startswith("-") else 1
    parts = [float(p) for p in text.replace(":", " ").replace("-", " ").split()]
    value = parts[0] + parts[1] / 60 + parts[2] / 3600
    return sign * value * (15 if hours else 1)


def main() -> None:
    eph = get("https://ssd.jpl.nasa.gov/api/horizons.api", {
        "format": "json", "COMMAND": "'1;'", "CENTER": "'568'", "MAKE_EPHEM": "YES", "EPHEM_TYPE": "OBSERVER",
        "TLIST": f"'{JD}'", "QUANTITIES": "'1'", "ANG_FORMAT": "'DEG'"})["result"]
    row = eph.split("$$SOE")[1].split("$$EOE")[0].split()
    ra, dec = float(row[-2]), float(row[-1])
    print(f"Horizons, Ceres from 568 at JD {JD}: RA {ra:.6f}  Dec {dec:+.6f}")

    c_ra = ra + SHIFT[0] / 3600 / math.cos(math.radians(dec))
    c_dec = dec + SHIFT[1] / 3600
    (ra_sent, ra_c), (dec_sent, dec_c) = ra_text(c_ra), dec_text(c_dec)
    body = get("https://ssd-api.jpl.nasa.gov/sb_ident.api", {
        "mpc-code": "568", "obs-time": JD, "fov-ra-center": ra_sent, "fov-dec-center": dec_sent,
        "fov-ra-hwidth": "0.1", "fov-dec-hwidth": "0.1", "mag-required": "false"})
    fields = body["fields_first"]
    ceres = next(r for r in body["data_first_pass"] if r[0].startswith("1 Ceres"))
    col = {f: ceres[i] for i, f in enumerate(fields)}
    jpl = (float(col['Dist. from center RA (")']), float(col['Dist. from center Dec (")']))
    o_ra = sexagesimal(col["Astrometric RA (hh:mm:ss)"], True)
    o_dec = sexagesimal(col["Astrometric Dec (dd mm'ss\")"].replace("'", " ").replace('"', " "), False)
    ours = (((o_ra - ra_c + 180) % 360 - 180) * math.cos(math.radians(dec_c)) * 3600, (o_dec - dec_c) * 3600)
    print(f"Box centre sent: {ra_sent} {dec_sent} (Ceres moved {SHIFT[0]:g}″ west, {SHIFT[1]:g}″ south of it)")
    print(f"JPL offsets of Ceres:        RA {jpl[0]:+8.1f}″  Dec {jpl[1]:+8.1f}″")
    print(f"From JPL's own RA/Dec:       RA {ours[0]:+8.1f}″  Dec {ours[1]:+8.1f}″")
    same = all(math.copysign(1, a) == math.copysign(1, b) and abs(a - b) < 5 for a, b in zip(jpl, ours))
    print("Result: JPL's offsets are object minus centre, east and north positive." if same
          else "Result: the signs or sizes DIFFER; known_objects.rows() must be changed.")


if __name__ == "__main__":
    main()
