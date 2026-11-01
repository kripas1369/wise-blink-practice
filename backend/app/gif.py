"""The flipbook as an animated GIF (flipbook.gif), to share or put in slides.

    python -m backend.app.gif frontend/frames/*/d*

Each frame is the visit's PNG exactly as the website shows it (same scale for every visit), enlarged with
whole pixels (no smoothing, so no detail is invented), with a caption: target, detector, visit, date, and
the data credit.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE_TO_PX = 360
CAPTION_PX = 44
FRAME_MS = 900
CREDIT = "SPHEREx · NASA/IPAC IRSA"


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:   # Pillow < 10.1
        return ImageFont.load_default()


def build_gif(folder: Path) -> bytes:
    import io

    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    frames = manifest["frames"]
    size = manifest["size_px"]
    scale = max(1, SCALE_TO_PX // size)
    side = size * scale
    big, small = _font(15), _font(12)
    images = []
    for i, f in enumerate(frames):
        sky = Image.open(folder / f["png"]).convert("L").resize((side, side), Image.NEAREST)
        canvas = Image.new("L", (side, side + CAPTION_PX), 0)
        canvas.paste(sky, (0, 0))
        draw = ImageDraw.Draw(canvas)
        c = side / 2
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):   # open crosshair at the frame centre
            draw.line([(c + dx * scale * 1.2, c + dy * scale * 1.2), (c + dx * scale * 2.4, c + dy * scale * 2.4)],
                      fill=255, width=1)
        draw.text((6, side + 4), f"{manifest['label']} · D{manifest['band']} · visit {i + 1} of {len(frames)} · "
                  f"{f['date_iso'][:10]}", fill=255, font=big)
        draw.text((6, side + 24), f"N up, E left · {manifest['fov_arcmin']:g} arcmin · {CREDIT}", fill=170, font=small)
        images.append(canvas.convert("P"))
    out = io.BytesIO()
    images[0].save(out, "GIF", save_all=True, append_images=images[1:], duration=FRAME_MS, loop=0, optimize=False)
    return out.getvalue()


def write_gif(folder: Path) -> Path:
    path = Path(folder) / "flipbook.gif"
    path.write_bytes(build_gif(folder))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folders", nargs="+", type=Path)
    for folder in parser.parse_args().folders:
        path = write_gif(folder)
        print(f"{path}: {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
