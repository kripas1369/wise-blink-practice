"""Prepare more detectors for official targets: frames (render.py), then Gaia, diff, light curve, proof,
spots and the target's spectrum, the same steps the API runs after a download.

    python scripts/prepare_detectors.py rw_aur 1 3 4 5 6
    python scripts/prepare_detectors.py wise0855 5 --stretch asinh

Detectors that already have a manifest are skipped. A failed detector is reported and the next one runs.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.main import _pipeline_after_render  # noqa: E402
from backend.app.render import DEFAULT_OUT, make_frames  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("target")
    parser.add_argument("detectors", type=int, nargs="+")
    parser.add_argument("--max-per-visit", type=int, default=8)
    parser.add_argument("--stretch", choices=["linear", "asinh"], default="linear")
    args = parser.parse_args()
    target_dir = DEFAULT_OUT / args.target
    for det in args.detectors:
        folder = target_dir / f"d{det}"
        if (folder / "manifest.json").exists():
            print(f"{folder}: already prepared, skipped", flush=True)
            continue
        start = time.time()
        try:
            make_frames(args.target, det, "coadd", args.max_per_visit, 3.0, DEFAULT_OUT, args.stretch)
            warnings = _pipeline_after_render(folder, target_dir)
        except Exception as exc:
            print(f"{folder}: FAILED {exc.__class__.__name__}: {exc}", flush=True)
            continue
        print(f"{folder}: done in {time.time() - start:.0f} s; warnings: {warnings or 'none'}", flush=True)


if __name__ == "__main__":
    main()
