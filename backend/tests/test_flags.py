import pytest
from astropy.io.fits import Header

from backend.app.flags import NoFlagDefinitions, bad_pixel_bitmask, flag_bits


def qr2_header():
    h = Header()
    for name, bit in {"TRANSIENT": 0, "OVERFLOW": 1, "HOT": 10, "SOURCE": 21}.items():
        h[f"HIERARCH MP_{name}"] = bit
    return h


def qr3_header():
    h = Header()
    for name, bit in {"TRANSIENT": 0, "HOT": 10, "SOURCE": 21, "GHOST": 22, "HALO": 28}.items():
        h[f"MSKN{bit:04d}"] = name
        h[f"MSKM{bit:04d}"] = 1 << bit
    return h


def test_reads_qr2_format():
    assert flag_bits(qr2_header()) == {"TRANSIENT": 0, "OVERFLOW": 1, "HOT": 10, "SOURCE": 21}


def test_reads_qr3_format():
    assert flag_bits(qr3_header()) == {"TRANSIENT": 0, "HOT": 10, "SOURCE": 21, "GHOST": 22, "HALO": 28}


def test_bad_mask_skips_source_and_unknown_names():
    # QR2: TRANSIENT and HOT are bad; OVERFLOW is not in the official list; SOURCE is a label.
    assert bad_pixel_bitmask(qr2_header()) == (1 << 0) | (1 << 10)
    # QR3 adds GHOST and HALO, which are bad.
    assert bad_pixel_bitmask(qr3_header()) == (1 << 0) | (1 << 10) | (1 << 22) | (1 << 28)


def test_missing_definitions_raise_instead_of_keeping_everything():
    with pytest.raises(NoFlagDefinitions):
        flag_bits(Header())
