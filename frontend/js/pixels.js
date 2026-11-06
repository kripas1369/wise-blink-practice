// Scientist view data (pixels<i>.json.gz, made by backend/app/pixels.py): decode FLAGS integers, find a pixel's
// numbers and sky position. The good / bad rule is applied once, in Python; this file only shows its result.
import { remember } from "./frames.js";

export const PIXELS_FORMAT = "spherex-blink-pixels/1";

// Colours carry data (the page is otherwise black and white): kept pixels cool, rejected pixels warm.
export const CATEGORIES = {
  good: {
    label: "Good", color: "#aeaeb2", kept: true,
    meaning: "No flag from the official bad list and no SOURCE label. Used in the add-up.",
  },
  source: {
    label: "Good, SOURCE label", color: "#4f8ff7", kept: true,
    meaning: "SOURCE only says a known star or galaxy covers this pixel. It is a label, not a defect: used in the add-up.",
  },
  bad: {
    label: "Bad", color: "#ff453a", kept: false,
    meaning: "At least one flag from the official bad list. Left out of the add-up.",
  },
  transient: {
    label: "Transient", color: "#ffd60a", kept: false,
    meaning: "TRANSIENT: the signal jumped during the readout (for example a cosmic-ray hit). It is on the bad list, so left out of the add-up.",
  },
  no_value: {
    label: "No value", color: null, kept: false,
    meaning: "The file has no number here (NaN), for example a saturated star core.",
  },
};

const isNumber = (v) => typeof v === "number" && Number.isFinite(v);

/** Throws an Error naming the first problem; a file we cannot read honestly is not shown. */
export function checkPixels(p) {
  if (!p || p.format !== PIXELS_FORMAT) throw new Error(`Unknown pixel-file format: ${p && p.format}`);
  if (!Array.isArray(p.categories) || p.categories.some((k) => !(k in CATEGORIES))) {
    throw new Error("Pixel file has unknown categories");
  }
  if (!Array.isArray(p.exposures) || p.exposures.length === 0) throw new Error("Pixel file has no exposures");
  p.exposures.forEach((e, i) => {
    const [ny, nx] = e.shape || [];
    if (!(ny > 0 && nx > 0)) throw new Error(`Exposure ${i}: no shape`);
    for (const key of ["flag_index", "category", "value", "sigma"]) {
      if (!Array.isArray(e[key]) || e[key].length !== nx * ny) throw new Error(`Exposure ${i}: "${key}" does not match its shape`);
    }
    if (e.flag_index.some((k) => !(k >= 0 && k < e.flag_values.length))) throw new Error(`Exposure ${i}: bad flag index`);
    if (e.category.some((c) => !(c >= 0 && c < p.categories.length))) throw new Error(`Exposure ${i}: bad category`);
  });
  return p;
}

/** Bit numbers set in a FLAGS integer, lowest first (FLAGS is a 32-bit integer). */
export function bitsSet(value) {
  const out = [];
  for (let bit = 0; bit < 32; bit += 1) if (((value >>> bit) & 1) === 1) out.push(bit);
  return out;
}

/** "0000 0000 0010 0000 0000 0000 0000 0001": bit 31 first, in groups of 4. */
export function binary32(value) {
  return (value >>> 0).toString(2).padStart(32, "0").match(/.{4}/g).join(" ");
}

export function hex32(value) {
  return `0x${(value >>> 0).toString(16).toUpperCase().padStart(8, "0")}`;
}

/** One line per set bit, named by this file's own FLAGS header. */
export function describeFlags(value, bits) {
  const byBit = new Map(bits.map((b) => [b.bit, b]));
  return bitsSet(value).map((bit) => {
    const b = byBit.get(bit);
    if (!b) return { bit, name: `bit ${bit}`, meaning: "not defined in this file's FLAGS header", rejected: false, known: false };
    return { bit, name: b.name, meaning: b.meaning, rejected: b.rejected, known: true };
  });
}

/** What a bit does in our add-up, in words. */
export function bitUse(b) {
  if (b.rejected) return "Rejected (official bad list)";
  if (b.name === "SOURCE") return "Kept (label only)";
  return "Kept (not on the bad list)";
}

/** Arrays are FITS row order: row 0 at the bottom. */
export const pixelIndex = (e, x, y) => y * e.shape[1] + x;

export function skyAt(sky, x, y) {
  const [x0, y0] = sky.ref_px;
  const [[ex, nx], [ey, ny]] = sky.arcsec_per_px;
  const east = ex * (x - x0) + ey * (y - y0);
  const north = nx * (x - x0) + ny * (y - y0);
  const dec = sky.ref_radec[1] + north / 3600;
  const ra = (sky.ref_radec[0] + east / 3600 / Math.cos((sky.ref_radec[1] * Math.PI) / 180) + 360) % 360;
  return { ra, dec };
}

export function wavelengthAt(wl, sky, x, y) {
  if (!wl) return null;
  const [x0, y0] = sky.ref_px;
  return wl.at_ref_px + wl.per_px[0] * (x - x0) + wl.per_px[1] * (y - y0);
}

/** Every number the inspector shows for pixel (x, y) of one exposure. */
export function pixelInfo(p, e, x, y) {
  const i = pixelIndex(e, x, y);
  const flag = e.flag_values[e.flag_index[i]];
  const value = e.value[i];
  const sigma = e.sigma[i];
  return {
    x, y,
    detector: e.detector_origin ? [e.detector_origin[0] + x, e.detector_origin[1] + y] : null,
    ...skyAt(e.sky, x, y),
    wavelength: wavelengthAt(e.wavelength, e.sky, x, y),
    flag,
    flags: describeFlags(flag, e.bits),
    category: p.categories[e.category[i]],
    value, sigma,
    snr: isNumber(value) && isNumber(sigma) && sigma > 0 ? value / sigma : null,
  };
}

/** Grey limits for the brightness view: 1st and 99.5th percentile of the pixels that have a value. */
export function greyLimits(values) {
  const v = values.filter(isNumber).sort((a, b) => a - b);
  if (!v.length) return null;
  const at = (q) => v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
  const lo = at(0.01);
  const hi = at(0.995);
  return { lo, hi: hi > lo ? hi : lo + 1e-9 };
}

/** "down and slightly left" style words for a direction in the view (x right, y up). */
export function directionWords([vx, vy]) {
  const names = ["right", "up-right", "up", "up-left", "left", "down-left", "down", "down-right"];
  const k = Math.round(Math.atan2(vy, vx) / (Math.PI / 4));
  return names[(k + 8) % 8];
}

/** The pixel nearest the target ring, or the middle of the box. */
export function startPixel(e) {
  const [ny, nx] = e.shape;
  const [x, y] = e.target_px ? e.target_px.map(Math.round) : [Math.floor(nx / 2), Math.floor(ny / 2)];
  return { x: Math.min(nx - 1, Math.max(0, x)), y: Math.min(ny - 1, Math.max(0, y)) };
}

async function gunzipJson(buffer) {
  const bytes = new Uint8Array(buffer);
  // Some servers unpack .gz themselves (Content-Encoding); then the body is already JSON text.
  if (!(bytes[0] === 0x1f && bytes[1] === 0x8b)) return JSON.parse(new TextDecoder().decode(bytes));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}

/** The checked pixel file of visit `i`, or null when this folder has none. Kept for the page visit. */
export function loadPixels(base, i, fetchFn = fetch) {
  const url = `${base}/pixels${i}.json.gz`;
  return remember(fetchFn, `pixels:${url}`, async () => {
    let resp;
    try {
      resp = await fetchFn(url, { cache: "no-cache" });
    } catch {
      throw new Error(`Could not reach ${url}`);
    }
    if (resp.status === 404) return null;
    if (!resp.ok) throw new Error(`${url} answered HTTP ${resp.status}`);
    return checkPixels(await gunzipJson(await resp.arrayBuffer()));
  });
}
