// Load and check SPHEREx frames (format: docs/plan/FRAMES_FORMAT.md): from the data API
// (backend/app/main.py) when the site is served by it, otherwise the prepared files in frontend/frames/.

export const FRAMES_ROOT = "frames";
export const FORMAT = "spherex-blink-frames/1";
export const PREPARED_FOV = 3;

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

/** gaia.json / diff.json next to a manifest, or null when that folder has none. */
export async function loadExtra(base, name, fetchFn = fetch) {
  return getJson(`${base}/${name}`, fetchFn);
}

let apiAnswered = null;

/** Is the site served by the data API? Asked once. */
export async function hasApi(fetchFn = fetch) {
  if (apiAnswered === null) {
    try {
      const resp = await fetchFn("/api/health", { cache: "no-cache" });
      apiAnswered = resp.ok && (await resp.json()).ok === true;
    } catch {
      apiAnswered = false;
    }
  }
  return apiAnswered;
}

export function resetApiCheck() {
  apiAnswered = null;
}

export function framesQuery({ targetKey, ra, dec, det, fov }) {
  const params = targetKey && fov === PREPARED_FOV
    ? { target: targetKey, band: det }
    : { ra: ra.toFixed(6), dec: dec.toFixed(6), band: det, fov_arcmin: fov };
  return `/api/frames?${new URLSearchParams(params)}`;
}

/**
 * Frames for a position and detector:
 *   { status: "ready", manifest, base, warnings }  base = folder URL without the trailing slash
 *   { status: "working", message }                 the API is preparing them; ask again later
 *   { status: "none", message }                    there are none (the message says why)
 * Throws FramesUnavailable when a server fails.
 */
export async function loadFrames(where, fetchFn = fetch) {
  const { targetKey, det, fov } = where;
  if (await hasApi(fetchFn)) {
    let resp;
    try {
      resp = await fetchFn(framesQuery(where), { cache: "no-cache" });
    } catch {
      throw new FramesUnavailable("Could not reach the data API");
    }
    const body = await resp.json().catch(() => ({}));
    if (resp.status === 202) return { status: "working", message: body.message || "Preparing the frames…" };
    if (resp.status === 404) return { status: "none", message: body.error || "No SPHEREx frames here" };
    if (!resp.ok) throw new FramesUnavailable(body.error || `The data API answered HTTP ${resp.status}`);
    return {
      status: "ready", manifest: checkManifest(body), base: body.base_url.replace(/\/$/, ""), warnings: body.warnings || [],
    };
  }
  if (!targetKey) {
    return { status: "none", message: "SPHEREx frames for any position need the data API (uvicorn backend.app.main:app). This server only has the 5 prepared targets." };
  }
  const manifest = await loadManifest(targetKey, det, fetchFn);
  if (manifest === null) return { status: "none", message: `No prepared SPHEREx frames for this target in D${det}.` };
  return { status: "ready", manifest, base: `${FRAMES_ROOT}/${targetKey}/d${det}`, warnings: [] };
}
