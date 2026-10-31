"""What a visitor must know before trusting their eyes, per (target, detector).

Each sentence was measured on the frames it is shown with; numbers and method: notes/DAY2_FINDINGS.md.
When the frames are remade (other mode, other exposures), re-measure and update these first.

After editing, put the new notes into existing manifests without re-downloading anything:
    python -m backend.app.frame_notes frontend/frames
"""
import json
import sys
from pathlib import Path

NOTES: dict[tuple[str, int], list[str]] = {
    ("barnard", 2): [
        "From its known motion (10.4″ a year, mostly north), Barnard's Star should move about 1.7 pixels "
        "between the first and last visit. Its centre is saturated or flagged in every exposure (striped), so "
        "the shift is hard to judge by eye; measuring it against Gaia comes on Day 3.",
    ],
    ("eps_ind_b", 2): [
        "The two brown dwarfs are far closer together than one SPHEREx pixel (6.15″), so they show as one dot.",
        "One exposure of the Apr 2026 visit had 30% of its pixels flagged; the add-up leaves those pixels out "
        "and fills them from the other 6 exposures.",
    ],
    ("rw_aur", 2): [
        "Each add-up mixes exposures at different wavelengths (at the star 1.18–1.39, 1.12–1.65 and "
        "1.11–1.64 µm), and the star's brightness depends on wavelength, so these frames cannot say how much "
        "RW Aurigae itself changed. That needs brightness measured at matching wavelengths (light curve, Day 4).",
    ],
    ("r_dra", 2): [
        "R Draconis is so bright that its centre is saturated (striped) in all 3 visits, so its brightness "
        "cannot be measured from these D2 frames.",
    ],
    ("wise0855", 2): [
        "The bright dot inside the ring is NOT WISE 0855. It sits about 9″ north-west of the ring's centre "
        "and stays there for a year (same pixel in 3 of 4 visits, one pixel lower in Dec 2025), while WISE 0855 "
        "moves about 1.3 pixels a year to the west. It is not in SIMBAD; what it is has not been checked yet.",
    ],
    ("wise0855", 6): [
        "In the two visits with many exposures (19 and 21 added), a faint source sits at the ring: about 11 "
        "and 13 times the noise, and still 6 to 9 times in each half of the exposures, so it is not one odd "
        "exposure. Its brightest pixel moved 1 pixel west from Nov 2025 to Apr 2026, the way WISE 0855 moves "
        "(about 0.6 pixel expected). That fits WISE 0855 but is not proven yet: the background object seen in "
        "D2 is only 1 pixel away, and a proper position fit comes on Day 3.",
        "The May 2025 visit adds only 3 exposures: nothing clear at the ring (2.4 times the noise), and its "
        "sky is brighter (0.14 against 0.09 MJy/sr after removing the zodiacal glow; cause not checked).",
    ],
}


def apply_notes(out_root: Path) -> None:
    """Replace the `notes` of every manifest under out_root with the ones above."""
    for path in sorted(Path(out_root).glob("*/d*/manifest.json")):
        manifest = json.loads(path.read_text())
        key = (manifest["target"], int(manifest["band"]))
        manifest["notes"] = NOTES.get(key, [])
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        print(f"{path}: {len(manifest['notes'])} notes")


if __name__ == "__main__":
    apply_notes(Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/frames"))
