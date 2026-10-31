// Load and check prepared SPHEREx frames (format: docs/plan/FRAMES_FORMAT.md).
// Day 2 reads files from frontend/frames/; Day 3 swaps this for the /api/frames call.

export const FRAMES_ROOT = "frames";
export const FORMAT = "spherex-blink-frames/1";

export class FramesUnavailable extends Error {}

export function manifestUrl(target, band, root = FRAMES_ROOT) {
  return `${root}/${target}/d${band}/manifest.json`;
}

const isNumber = (v) => typeof v === "number" && Number.isFinite(v);

/** Throws an Error naming the first problem; frames we cannot label honestly are not shown. */
export function checkManifest(m) {
  if (!m || m.format !== FORMAT) throw new Error(`Unknown frames format: ${m && m.format}`);
  for (const key of ["ra", "dec", "fov_arcmin", "pixel_arcsec", "size_px", "band"]) {
    if (!isNumber(m[key])) throw new Error(`Manifest field "${key}" is missing or not a number`);
  }
  if (!m.scale || !isNumber(m.scale.vmin) || !isNumber(m.scale.vmax) || m.scale.vmin >= m.scale.vmax) {
    throw new Error("Manifest brightness scale is missing or invalid");
  }
  if (m.notes !== undefined && !(Array.isArray(m.notes) && m.notes.every((n) => typeof n === "string"))) {
    throw new Error("Manifest notes must be a list of sentences");
  }
  if (!Array.isArray(m.frames) || m.frames.length === 0) throw new Error("Manifest has no frames");
  m.frames.forEach((f, i) => {
    if (typeof f.png !== "string" || !f.png) throw new Error(`Frame ${i}: no image file`);
    if (!isNumber(f.mjd) || typeof f.date_iso !== "string") throw new Error(`Frame ${i}: no observation time`);
    if (f.band !== m.band) throw new Error(`Frame ${i}: detector D${f.band} in a D${m.band} manifest`);
    if (!isNumber(f.pct_flagged) || !isNumber(f.n_images)) throw new Error(`Frame ${i}: missing counts`);
  });
  const times = m.frames.map((f) => f.mjd);
  if (times.some((t, i) => i > 0 && t <= times[i - 1])) throw new Error("Frames are not in time order");
  return m;
}

export function wavelengthText(frame) {
  const band = `band ${frame.wl_min_um.toFixed(2)}–${frame.wl_max_um.toFixed(2)} µm`;
  if (!isNumber(frame.wl_target_um)) return `wavelength at the star unknown (${band})`;
  const range = frame.wl_target_range_um;
  if (Array.isArray(range) && range.length === 2 && range.every(isNumber) && range[0] !== range[1]) {
    return `${range[0].toFixed(3)}–${range[1].toFixed(3)} µm at the star (${band})`;
  }
  return `${frame.wl_target_um.toFixed(3)} µm at the star (${band})`;
}

/** One line under the frame. Every value comes from the manifest. */
export function frameLabel(frame, index, count) {
  const exposures = frame.n_images === 1 ? "1 exposure" : `${frame.n_images} exposures added`;
  const ofEpoch = isNumber(frame.n_images_in_epoch) ? ` of ${frame.n_images_in_epoch} in this visit` : "";
  return [
    `Visit ${index + 1} of ${count}`,
    frame.date_iso,
    `D${frame.band}, ${wavelengthText(frame)}`,
    `${exposures}${ofEpoch}`,
    `${frame.pct_flagged.toFixed(1)}% pixels flagged`,
    ...(isNumber(frame.pct_no_value) && frame.pct_no_value > 0
      ? [`${frame.pct_no_value.toFixed(1)}% with no value (striped)`] : []),
  ].join(" · ");
}

/** Days between the first and last frame, e.g. for "3 visits over 359 days". */
export function spanDays(frames) {
  return Math.round(frames[frames.length - 1].mjd - frames[0].mjd);
}

async function getJson(url, fetchFn) {
  let resp;
  try {
    resp = await fetchFn(url, { cache: "no-cache" });
  } catch {
    throw new FramesUnavailable(`Could not reach ${url}`);
  }
  if (resp.status === 404) return null;
  if (!resp.ok) throw new FramesUnavailable(`${url} answered HTTP ${resp.status}`);
  return resp.json();
}

/** { target: [bands...] } for the frames that exist, from frames/index.json. */
export async function loadIndex(fetchFn = fetch, root = FRAMES_ROOT) {
  const index = await getJson(`${root}/index.json`, fetchFn);
  return index ? index.available : {};
}

/** The checked manifest, or null when no frames were prepared for this target and detector. */
export async function loadManifest(target, band, fetchFn = fetch, root = FRAMES_ROOT) {
  const manifest = await getJson(manifestUrl(target, band, root), fetchFn);
  return manifest === null ? null : checkManifest(manifest);
}
