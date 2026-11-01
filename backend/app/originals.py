"""Links to the original SPHEREx files behind every frame (originals.json), so anyone can check our numbers.

    python -m backend.app.originals frontend/frames/*/d*

Each frame adds up a few exposures (exposures.fits, made by render.py). For each one, IRSA's catalogue
(spherex.obscore, then the file table spherex.artifact) gives the data release, the DataLink address
(IRSA's official list of every product of that image) and the full Level 2 FITS file.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from astropy.io import fits

from backend.app.archive import ArchiveError, run_query

FORMAT = "spherex-blink-originals/1"
IBE_DATA_URL = "https://irsa.ipac.caltech.edu/ibe/data/"
CHUNK = 200


def _quoted(values) -> str:
    return ",".join("'" + v.replace("'", "''") + "'" for v in values)


def lookup(obs_ids: list[str], band: int) -> dict[str, dict]:
    """{obs_id: {release, did, datalink_url, file_url}} for one detector; raises ArchiveError."""
    out: dict[str, dict] = {}
    for i in range(0, len(obs_ids), CHUNK):
        table = run_query(f"""
            SELECT obs_id, obs_collection, obs_publisher_did, access_url FROM spherex.obscore
            WHERE obs_id IN ({_quoted(obs_ids[i:i + CHUNK])}) AND energy_bandpassname = 'SPHEREx-D{int(band)}'
        """)
        for row in table:
            out[str(row["obs_id"])] = {"release": str(row["obs_collection"]), "did": str(row["obs_publisher_did"]),
                                       "datalink_url": str(row["access_url"]), "file_url": None}
    dids = {v["did"]: k for k, v in out.items()}
    for i in range(0, len(dids), CHUNK):
        table = run_query(f"""
            SELECT p.obs_publisher_did, a.uri FROM spherex.plane p JOIN spherex.artifact a ON a.planeid = p.planeid
            WHERE a.producttype = 'science' AND p.obs_publisher_did IN ({_quoted(list(dids)[i:i + CHUNK])})
        """)
        for row in table:
            out[dids[str(row["obs_publisher_did"])]]["file_url"] = IBE_DATA_URL + str(row["uri"]).removeprefix("ibe/data/")
    return out


def build_originals(folder: Path) -> dict:
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    table = fits.getdata(folder / "exposures.fits", "EXPOSURES")
    rows = [(str(r["OBS_ID"]).strip(), float(r["MJD"]), int(r["FRAME"])) for r in table]
    found = lookup(sorted({o for o, _, _ in rows}), manifest["band"])
    frames = []
    for i, f in enumerate(manifest["frames"]):
        exposures = [{"obs_id": o, "mjd": round(m, 5), **{k: v for k, v in found.get(o, {}).items() if k != "did"}}
                     for o, m, k in sorted(rows, key=lambda r: r[1]) if k == i]
        frames.append({"epoch_id": f["epoch_id"], "date_iso": f["date_iso"], "exposures": exposures})
    missing = sorted(o for o, _, _ in rows if o not in found)
    return {
        "format": FORMAT, "target": manifest["target"], "band": manifest["band"], "frames": frames,
        "missing": missing,
        "note": "datalink_url: IRSA's list of every product of the image (VOTable); file_url: the full Level 2 "
                "file (several tens of MB; IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE).",
        "made_by": "backend/app/originals.py",
        "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_credit": "NASA/IPAC Infrared Science Archive (IRSA), SPHEREx",
    }


def write_originals(folder: Path) -> dict:
    originals = build_originals(folder)
    (Path(folder) / "originals.json").write_text(json.dumps(originals, indent=1) + "\n")
    return originals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path)
    for folder in parser.parse_args().folders:
        try:
            o = write_originals(folder)
        except (ArchiveError, FileNotFoundError) as exc:
            print(f"{folder}: FAILED {exc}")
            continue
        n = sum(len(f["exposures"]) for f in o["frames"])
        print(f"{folder}: {n} exposures linked, {len(o['missing'])} not found at IRSA")


if __name__ == "__main__":
    main()
