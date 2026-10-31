"""Fixed settings: archive addresses, SPHEREx facts, and where downloads are cached.

Every value here is checked against a source (see docs/plan/FACTS.md).
"""
from pathlib import Path

TAP_URL = "https://irsa.ipac.caltech.edu/TAP"
CUTOUT_URL = "https://irsa.ipac.caltech.edu/ibe/cutout"

# The main CDS server did not respond on 29 Oct 2026; the Harvard mirror did.
SIMBAD_SERVERS = ("simbad.cds.unistra.fr", "simbad.harvard.edu")

# Science image collections in spherex.obscore (31 Oct 2026). The table also holds
# spherex_qr2_cal / spherex_qr3_cal, which are not sky images of a target.
# QR2 holds observations up to ~Apr 2026, QR3 from ~Aug 2026 on; an exposure is in only one.
# "_deep" = the extra visits to the two SPHEREx Deep Fields near the ecliptic poles.
COLLECTIONS = ("spherex_qr2", "spherex_qr2_deep", "spherex_qr3", "spherex_qr3_deep")

PIXEL_SCALE_ARCSEC = 6.15

# Wavelength range of each detector in micrometres (SPHEREx Explanatory Supplement).
DETECTORS = {
    1: (0.75, 1.09),
    2: (1.10, 1.62),
    3: (1.63, 2.41),
    4: (2.42, 3.82),
    5: (3.83, 4.41),
    6: (4.42, 5.00),
}

# Pixels with any of these flags are bad (Supplement v2.0, section 3.4.3, Mosaic Tool list).
# Bit positions are NOT fixed here; they are read from the MP_* keywords of each FLAGS header,
# and names missing from a release's header are simply skipped.
# SOURCE (bit 21) is deliberately absent: it labels a known object, it is not a defect.
BAD_FLAG_NAMES = (
    "TRANSIENT", "SUR_ERROR", "NONFUNC", "DICHROIC", "MISSING_DATA", "HOT", "COLD",
    "PHANMISS", "NONLINEAR", "PERSIST", "CROSSTALK", "GHOST", "GHOST_FPA", "GHOST_EXT",
    "STREAK", "BLOOM", "SNOWBALL", "HALO", "SATELLITE_HALO",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "cache"

# IRSA answered "503 busy" when we sent 4+ cutout requests at once (31 Oct 2026).
MAX_PARALLEL_DOWNLOADS = 3
RETRIES = 4
