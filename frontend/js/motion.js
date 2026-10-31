// Move a star from its catalogue date to another date with its proper motion.
// Same formula as backend/app/motion.py (straight line; pmra already includes cos(dec)).

const MAS_PER_DEG = 3.6e6;

// SPHEREx data so far runs from Apr 2025 to Oct 2026; the backend searches at 2026.0 too.
export const VIEW_EPOCH = 2026.0;

export function positionAt(ra, dec, pmraMas, pmdecMas, fromYear, toYear) {
  const years = toYear - fromYear;
  const cosDec = Math.cos((dec * Math.PI) / 180);
  if (cosDec < 1e-6) throw new Error("Too close to a celestial pole for a straight-line move");
  const newRa = (((ra + (pmraMas * years) / MAS_PER_DEG / cosDec) % 360) + 360) % 360;
  const newDec = dec + (pmdecMas * years) / MAS_PER_DEG;
  return { ra: newRa, dec: newDec };
}

export function separationArcsec(ra1, dec1, ra2, dec2) {
  const r = Math.PI / 180;
  const h =
    Math.sin(((dec2 - dec1) * r) / 2) ** 2 +
    Math.cos(dec1 * r) * Math.cos(dec2 * r) * Math.sin(((ra2 - ra1) * r) / 2) ** 2;
  return (2 * Math.asin(Math.sqrt(h)) * 180) / Math.PI * 3600;
}
