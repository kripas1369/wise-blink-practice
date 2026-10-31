"""What a visitor must know before trusting their eyes, per (target, detector).

Each sentence was measured on the frames it is shown with; numbers and method: notes/DAY2_FINDINGS.md,
DAY3_FINDINGS.md and DAY4_FINDINGS.md.
When the frames are remade (other mode, other exposures), re-measure and update these first.

After editing, put the new notes into existing manifests without re-downloading anything:
    python -m backend.app.frame_notes frontend/frames
"""
import json
import sys
from pathlib import Path

NOTES: dict[tuple[str, int], list[str]] = {
    ("barnard", 2): [
        "Gaia DR3 says Barnard's Star moves 1.67 pixels north from the first to the last visit (yellow markers). "
        "Its centre is saturated or flagged in every exposure (striped), so we measured the middle of that "
        "striped hole instead: it moved 1.59 pixels north (and 0.03 east, where Gaia says 0.12 west). The hole "
        "is a rough position, but it walks with the Gaia markers.",
    ],
    ("eps_ind_b", 2): [
        "The two brown dwarfs are far closer together than one SPHEREx pixel (6.15″), so they show as one dot.",
        "Measured centre of the dot: it moved 0.99 pixels from Apr 2025 to Oct 2026, toward the south-east; "
        "Gaia says 1.09 pixels in the same direction. RW Aurigae, which Gaia says does not move, shifts by "
        "only 0.04–0.07 pixels measured the same way.",
        "Its brightness in the add-ups changes by a factor of 2 between visits because each add-up mixes "
        "wavelengths. Measured exposure by exposure (light curve below), it is brightest near 1.27 and 1.58 µm "
        "and about 7 times fainter at 1.36-1.40 µm, where water and methane in a cool brown dwarf absorb. "
        "Exposures of different visits at the same wavelength agree within about 15% (ratios 0.86-1.05), so "
        "there is no clear sign that it varies.",
        "One exposure of the Apr 2026 visit had 30% of its pixels flagged; the add-up leaves those pixels out "
        "and fills them from the other 6 exposures.",
    ],
    ("rw_aur", 2): [
        "Each add-up mixes exposures at different wavelengths (at the star 1.18–1.39, 1.12–1.65 and "
        "1.11–1.64 µm), so the frames alone cannot say how much RW Aurigae changed; the light curve below "
        "compares single exposures at matching wavelengths instead.",
        "At matching wavelengths (1.2-1.27 µm) it was fainter in Sep 2025 than in Sep 2026: 24% in the one "
        "pair with no flagged pixels, 24-83% in the 4 pairs that include flagged pixels. Mar and Sep 2026 agree "
        "(ratios 0.89-1.03 at 1.11 and 1.6 µm). A star in the Barnard field, measured the same way, changes by about 5%.",
        "The Sep 2025 exposures also differ by 10-20% from each other within 2 hours; whether the star or the "
        "measurement causes this is not checked.",
        "Gaia DR3 lists a second star 1.5″ away (G 12.18; RW Aurigae is a known double star). Both are inside "
        "the measuring circle.",
        "Gaia says RW Aurigae moves 0.004 pixels over the year, yet the difference view shows a small "
        "bright-dark pair at the star: that is the size of pair that alignment and PSF differences alone make.",
    ],
    ("r_dra", 2): [
        "R Draconis is so bright that its centre is saturated in every exposure (in single exposures, no value "
        "up to 6 pixels from the centre). The add-up fills part of that hole from the exposures where those "
        "pixels were not saturated, which is why very bright pixels ring the striped centre.",
        "These frames use an asinh brightness scale so that the faint halo shows next to the core: grey "
        "levels are not proportional to brightness, but every visit uses the same scale.",
        "No light curve: the light around the saturated core could only be measured from 7 pixels out, and "
        "only rings up to 3 pixels out were checked to follow a star's brightness. So these frames do not show "
        "how much R Draconis changed; its pulsation was not checked here.",
    ],
    ("wise0855", 2): [
        "The bright dot inside the ring is NOT WISE 0855. It is the Gaia DR3 star 5756956644387831296 "
        "(G 16.31), 1.1 pixels (7″) west-north-west of the ring's centre; its Gaia marker shows with "
        "\"brighter than G = 18\". Gaia gives it a proper motion of 6 mas a year, so it stays on the same "
        "pixel, while WISE 0855 moves about 1.3 pixels a year to the west.",
    ],
    ("wise0855", 6): [
        "In the two visits with many exposures (19 and 21 added), a faint source sits at the ring: about 11 "
        "and 13 times the noise, and still 6 to 9 times in each half of the exposures, so it is not one odd "
        "exposure.",
        "Position fit (scripts/acceptance.py): from Nov 2025 to Apr 2026 the source moved 0.58 ± 0.12 pixels, "
        "mostly west. WISE 0855's published motion and parallax (SIMBAD, Kirkpatrick et al. 2021) predict "
        "0.72 pixels in that direction; a star that does not move would show 0. In both visits the source sits "
        "within 0.22 pixels of where WISE 0855 should be, and 1.11 and 0.57 pixels from the Gaia star seen in "
        "D2 (G 16.31). In D2 nothing is found at WISE 0855's position (below 3 times the noise in all 4 "
        "visits). So the D6 source moves like WISE 0855. The Gaia star may add some light in D6 (a fit with "
        "both gives it about a quarter of the flux, at only 2.7–2.8 times the noise; not proven).",
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
