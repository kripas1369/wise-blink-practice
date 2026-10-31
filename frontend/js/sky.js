// Frame pixels <-> sky, and Gaia markers on a frame. Grid rules: docs/plan/FRAMES_FORMAT.md, section 2.
const RAD = Math.PI / 180;

/**
 * RA/Dec (degrees) of a PNG pixel (x to the right = west, y down = south, 0 = centre of the first pixel)
 * on the north-up TAN grid of a manifest: { ra, dec, size_px, pixel_arcsec }.
 */
export function pixelToSky(x, y, { ra, dec, size_px: size, pixel_arcsec: scale }) {
  const c = (size - 1) / 2;
  const xi = -(x - c) * (scale / 3600) * RAD; // east is to the left
  const eta = (c - y) * (scale / 3600) * RAD;
  const rho = Math.hypot(xi, eta);
  if (rho === 0) return { ra, dec };
  const cc = Math.atan(rho);
  const d0 = dec * RAD;
  const newDec = Math.asin(Math.cos(cc) * Math.sin(d0) + (eta * Math.sin(cc) * Math.cos(d0)) / rho);
  const newRa = ra * RAD + Math.atan2(xi * Math.sin(cc), rho * Math.cos(d0) * Math.cos(cc) - eta * Math.sin(d0) * Math.sin(cc));
  return { ra: ((newRa / RAD) % 360 + 360) % 360, dec: newDec / RAD };
}

/** CSS position (percent of the frame) of a pixel position. */
export function percentAt([x, y], size) {
  return { left: ((x + 0.5) / size) * 100, top: ((y + 0.5) / size) * 100 };
}

/** The PNG pixel under a pointer, or null outside the frame. */
export function pixelUnder(clientX, clientY, rect, size) {
  const x = Math.floor(((clientX - rect.left) / rect.width) * size);
  const y = Math.floor(((clientY - rect.top) / rect.height) * size);
  return x >= 0 && y >= 0 && x < size && y < size ? { x, y } : null;
}

/** Gaia stars to draw: brighter than gMax (null = all), and always the target. */
export function visibleStars(gaia, gMax) {
  return gaia.stars.filter((s) => s.target || gMax === null || (s.g_mag !== null && s.g_mag <= gMax));
}

export function gaiaTarget(gaia) {
  return gaia ? gaia.stars.find((s) => s.target) || null : null;
}

/** How far Gaia says the target moves between two frames (indexes into the frames list). */
export function expectedShift(gaia, i, j, pixelArcsec) {
  const t = gaiaTarget(gaia);
  if (!t) return null;
  const [x0, y0] = t.xy[i];
  const [x1, y1] = t.xy[j];
  const px = Math.hypot(x1 - x0, y1 - y0);
  return { px, arcsec: px * pixelArcsec, dx: x1 - x0, dy: y1 - y0 };
}

/** Compass words for a shift in PNG pixels (+x = west, +y = south). */
export function directionText(dx, dy) {
  if (Math.hypot(dx, dy) < 0.05) return "no measurable direction";
  const angle = (Math.atan2(-dy, -dx) * 180) / Math.PI; // 0 = east, 90 = north
  const names = ["east", "north-east", "north", "north-west", "west", "south-west", "south", "south-east"];
  return names[((Math.round(angle / 45) % 8) + 8) % 8];
}
