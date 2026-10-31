"""Read which bit of the FLAGS layer means which pixel problem, from the file's own header.

The two releases write this differently (checked 31 Oct 2026):
  QR2: MP_<NAME> = <bit>                              e.g. MP_HOT = 10
  QR3: MSKN<nnnn> = '<NAME>', MSKM<nnnn> = 1 << nnnn  e.g. MSKN0010 = 'HOT', MSKM0010 = 1024
QR3 also defines flags QR2 does not have (CROSSTALK, GHOST*, STREAK, BLOOM, HALO).
"""
from astropy.io.fits import Header

from backend.app.config import BAD_FLAG_NAMES


class NoFlagDefinitions(ValueError):
    """The header defines no flag bits, so we cannot tell good pixels from bad ones."""


def flag_bits(header: Header) -> dict[str, int]:
    """{flag name: bit number} from a FLAGS header, in either release's format."""
    bits: dict[str, int] = {}
    for key, value in header.items():
        if key.startswith("MP_"):
            bits[key[3:]] = int(value)
        elif key.startswith("MSKN") and key[4:].isdigit():
            mask = header.get(f"MSKM{key[4:]}")
            bit = int(mask).bit_length() - 1 if mask else int(key[4:])
            bits[str(value).strip()] = bit
    if not bits:
        raise NoFlagDefinitions("No MP_* or MSKN* keywords in this FLAGS header")
    return bits


def bad_pixel_bitmask(header: Header, bad_names: tuple[str, ...] = BAD_FLAG_NAMES) -> int:
    """One integer with every 'bad' bit set; a pixel is bad if `flags & bitmask != 0`.

    Names from the official bad list that this release does not define are skipped.
    SOURCE is not in the bad list: it marks a known object, not a defect.
    """
    bits = flag_bits(header)
    mask = 0
    for name in bad_names:
        if name in bits:
            mask |= 1 << bits[name]
    return mask
