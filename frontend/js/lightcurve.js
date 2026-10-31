// Light curve panel: the brightness of one position in every exposure (backend/app/lightcurve.py).
// Rule: every point keeps its own wavelength (SPHEREx's filter gives each exposure a different one), so
// visits are compared only at the same wavelength, and a change is claimed only above the measured floor.
import { framesQuery, hasApi, loadExtra } from "./frames.js";

const $ = (id) => document.getElementById(id);
const SVG_W = 640;
const SVG_H = 240;
const PAD = { left: 56, right: 14, top: 12, bottom: 38 };
export const VISIT_COLOURS = ["#8fd3ff", "#ffc04d", "#5ee0a0", "#ff7b7b", "#c99bff", "#ff9ed2", "#e8edf7"];

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const measured = (lc) => lc.points.filter((p) => p.flux_mjy !== null);

/** Short wavelengths blue, long red, across the detector's range. */
export function wavelengthColour(wl, [lo, hi]) {
  if (wl === null) return "#9aa7c2";
  const t = Math.min(1, Math.max(0, (wl - lo) / (hi - lo)));
  return `hsl(${Math.round(260 - 260 * t)}, 85%, 62%)`;
}

/** "Nice" tick values covering [lo, hi]. */
export function ticks(lo, hi, count = 5) {
  const raw = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Number(v.toPrecision(12)));
  return out;
}

const OFF_CHART_FACTOR = 3;

/**
 * The y range: from 0 (or below, if a point is negative) to above the highest error bar. An exposure with
 * flagged pixels in the circle that measures more than 3× the highest clean one is left out of the range
 * (one cosmic-ray hit measured 520 mJy where WISE 0855 gives about 0.6).
 */
export function yRange(points) {
  const clean = points.filter((p) => !p.n_flagged);
  const limit = clean.length ? OFF_CHART_FACTOR * Math.max(...clean.map((p) => Math.abs(p.flux_mjy) + p.err_mjy)) : Infinity;
  const use = points.filter((p) => !p.n_flagged || Math.abs(p.flux_mjy) <= limit);
  const lo = Math.min(0, ...use.map((p) => p.flux_mjy - p.err_mjy));
  const hi = Math.max(...use.map((p) => p.flux_mjy + p.err_mjy));
  return [lo, hi > lo ? hi + (hi - lo) * 0.08 : lo + 1];
}

/** Measured points outside the chart's y range (drawn as ▲ at the edge). */
export function offChart(points) {
  if (!points.length) return [];
  const [lo, hi] = yRange(points);
  return points.filter((p) => p.flux_mjy > hi || p.flux_mjy < lo);
}

function chart({ points, xRange, xTicks, xLabel, lines = [] }) {
  const [x0, x1] = xRange;
  const [y0, y1] = yRange(points);
  const sx = (v) => PAD.left + ((v - x0) / (x1 - x0 || 1)) * (SVG_W - PAD.left - PAD.right);
  const sy = (v) => SVG_H - PAD.bottom - ((v - y0) / (y1 - y0)) * (SVG_H - PAD.top - PAD.bottom);
  const parts = [`<rect x="${PAD.left}" y="${PAD.top}" width="${SVG_W - PAD.left - PAD.right}" ` +
    `height="${SVG_H - PAD.top - PAD.bottom}" class="lc-frame"/>`];
  for (const v of ticks(y0, y1)) {
    parts.push(`<line x1="${PAD.left}" x2="${SVG_W - PAD.right}" y1="${sy(v)}" y2="${sy(v)}" class="lc-grid"/>`,
      `<text x="${PAD.left - 6}" y="${sy(v) + 4}" class="lc-tick" text-anchor="end">${v}</text>`);
  }
  for (const { value, label } of xTicks) {
    parts.push(`<text x="${sx(value)}" y="${SVG_H - PAD.bottom + 16}" class="lc-tick" text-anchor="middle">${esc(label)}</text>`);
  }
  parts.push(`<text x="${(PAD.left + SVG_W - PAD.right) / 2}" y="${SVG_H - 4}" class="lc-axis" text-anchor="middle">${esc(xLabel)}</text>`,
    `<text x="12" y="${SVG_H / 2}" class="lc-axis" text-anchor="middle" transform="rotate(-90 12 ${SVG_H / 2})">mJy</text>`);
  for (const line of lines) {
    const d = line.points.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("");
    parts.push(`<path d="${d}" class="lc-line" stroke="${line.colour}"/>`);
  }
  for (const p of points) {
    const cx = sx(p.x);
    if (p.flux_mjy > y1 || p.flux_mjy < y0) {
      const above = p.flux_mjy > y1;
      const tip = above ? PAD.top + 2 : SVG_H - PAD.bottom - 2;
      const base = above ? tip + 9 : tip - 9;
      parts.push(`<g class="lc-point lc-off"><title>Off the chart: ${esc(p.title)}</title>` +
        `<path d="M${cx},${tip}L${cx - 5},${base}L${cx + 5},${base}Z" stroke="${p.colour}" fill="none"/></g>`);
      continue;
    }
    const cy = sy(p.flux_mjy);
    parts.push(`<g class="lc-point"><title>${esc(p.title)}</title>` +
      `<line x1="${cx}" x2="${cx}" y1="${sy(Math.max(y0, p.flux_mjy - p.err_mjy))}" ` +
      `y2="${sy(Math.min(y1, p.flux_mjy + p.err_mjy))}" stroke="${p.colour}"/>` +
      `<circle cx="${cx}" cy="${cy}" r="4.5" stroke="${p.colour}" fill="${p.hollow ? "none" : p.colour}"/></g>`);
  }
  return `<svg viewBox="0 0 ${SVG_W} ${SVG_H}" class="lc-svg" role="img">${parts.join("")}</svg>`;
}

export function pointTitle(p, visitNumber) {
  const wl = p.wl_um === null ? "wavelength unknown" : `${p.wl_um.toFixed(3)} µm`;
  const flags = p.n_flagged ? ` · ${p.n_flagged} flagged pixel${p.n_flagged === 1 ? "" : "s"} in the circle` : "";
  return `Visit ${visitNumber} · ${p.date_iso} · ${wl} · ${p.flux_mjy.toFixed(2)} ± ${p.err_mjy.toFixed(2)} mJy${flags} · ${p.obs_id}`;
}

const isHollow = (p) => p.n_flagged > 0 || p.flux_mjy < 5 * p.err_mjy;

/** Brightness against time, each point coloured by its wavelength. */
export function timeChart(lc, manifest) {
  const pts = measured(lc);
  const mjds = pts.map((p) => p.mjd);
  const span = Math.max(...mjds) - Math.min(...mjds) || 1;
  return chart({
    points: pts.map((p) => ({ ...p, x: p.mjd, colour: wavelengthColour(p.wl_um, manifest.band_range_um),
      hollow: isHollow(p), title: pointTitle(p, p.frame + 1) })),
    xRange: [Math.min(...mjds) - span * 0.04, Math.max(...mjds) + span * 0.04],
    xTicks: manifest.frames.map((f) => ({ value: f.mjd, label: f.date_iso.slice(0, 7) })),
    xLabel: "date of the exposure",
  });
}

/** Brightness against wavelength, one colour per visit: where visits overlap, a gap is a change. */
export function wavelengthChart(lc, manifest) {
  const pts = measured(lc).filter((p) => p.wl_um !== null);
  const wls = pts.map((p) => p.wl_um);
  const lo = Math.min(manifest.band_range_um[0], ...wls);
  const hi = Math.max(manifest.band_range_um[1], ...wls);
  const off = new Set(offChart(pts));
  const lines = manifest.frames.map((_, i) => ({
    colour: VISIT_COLOURS[i % VISIT_COLOURS.length],
    points: pts.filter((p) => p.frame === i && !off.has(p)).sort((a, b) => a.wl_um - b.wl_um)
      .map((p) => ({ x: p.wl_um, y: p.flux_mjy })),
  })).filter((l) => l.points.length > 1);
  return chart({
    points: pts.map((p) => ({ ...p, x: p.wl_um, colour: VISIT_COLOURS[p.frame % VISIT_COLOURS.length],
      hollow: isHollow(p), title: pointTitle(p, p.frame + 1) })),
    xRange: [lo, hi],
    xTicks: ticks(lo, hi, 6).map((v) => ({ value: v, label: v.toFixed(2) })),
    xLabel: "wavelength at the position (µm)",
    lines,
  });
}

const visitName = (manifest, i) => `visit ${i + 1} (${manifest.frames[i].date_iso.slice(0, 10)})`;

function ratioText(p) {
  const range = p.n > 1 ? `, ${p.min_ratio}–${p.max_ratio}` : "";
  return `${p.n} pair${p.n === 1 ? "" : "s"} at the same wavelength, brightness ratio ${p.median_ratio}${range}`;
}

/** One line per visit pair that could be compared, clean pairs first. */
export function comparisonLines(lc, manifest) {
  const sw = lc.same_wavelength;
  const clean = sw.pairs.map((p) => `${visitName(manifest, p.a)} → ${visitName(manifest, p.b)}: ${ratioText(p)}.`);
  const flaggedOnly = sw.pairs_incl_flagged
    .map((p) => {
      const c = sw.pairs.find((q) => q.a === p.a && q.b === p.b);
      return c && c.n === p.n ? null
        : `${visitName(manifest, p.a)} → ${visitName(manifest, p.b)}, including exposures with flagged pixels (less certain): ${ratioText(p)}.`;
    })
    .filter(Boolean);
  if (!clean.length && !flaggedOnly.length) {
    return ["No two visits have usable exposures at the same wavelength, so no brightness change between visits is measured."];
  }
  return [...clean, ...flaggedOnly];
}

/** How far the measuring circle moves between the first and last exposure (pixels). */
export function circleTravelPx(points) {
  if (points.length < 2) return 0;
  const a = points[0];
  const b = points[points.length - 1];
  return Math.hypot(b.x - a.x, b.y - a.y);
}

/** What a visitor must know before reading the charts. */
export function lightCurveWarnings(lc) {
  const out = [];
  const travel = circleTravelPx(lc.points);
  for (const n of lc.neighbours || []) {
    out.push(`Gaia DR3 ${n.source_id} (G ${n.g_mag}) is ${n.distance_px} px from the position, inside the measuring ` +
      "circle, so its light is included" + (travel >= 0.1
      ? `; the circle follows the target ${travel.toFixed(1)} px, taking in more or less of that star, which alone can look like a brightness change.`
      : "."));
  }
  const off = offChart(measured(lc));
  if (off.length) {
    const biggest = off.reduce((a, b) => (Math.abs(b.flux_mjy) > Math.abs(a.flux_mjy) ? b : a));
    const one = off.length === 1;
    out.push(`${off.length} exposure${one ? "" : "s"} with flagged pixels in the circle measure${one ? "s" : ""} far ` +
      `outside the others (up to ${biggest.flux_mjy.toFixed(1)} mJy, ${biggest.obs_id}) and ` +
      `${one ? "is" : "are"} drawn as ▲ at the edge of the charts; a flagged pixel (for example ` +
      "a cosmic-ray hit) can do this.");
  }
  const sw = lc.same_wavelength;
  if (sw.n_excluded) {
    out.push(`${sw.n_excluded} of ${lc.points.length} exposures are left out of the clean comparisons (a flagged pixel in ` +
      "the circle, fainter than 5σ, or unknown wavelength); they are drawn hollow.");
  }
  const c = lc.comparison;
  if (c && c.n_pairs >= 3) {
    out.push(`Field stars in this frame, measured the same way, change by ${c.scatter_pct}% between visits at the same ` +
      `wavelength (${c.n_pairs} pairs, ${c.n_stars} star${c.n_stars === 1 ? "" : "s"}): smaller changes are not evidence.`);
  } else if (c) {
    out.push("No isolated Gaia star in this frame is bright enough to measure how much a star that should not change " +
      "seems to change, so the smallest real change these numbers can show is not known here.");
  }
  return out;
}

export function createLightCurve() {
  const el = {
    box: $("lc-view"), message: $("lc-message"), body: $("lc-body"), summary: $("lc-summary"),
    method: $("lc-method"), time: $("lc-time"), wl: $("lc-wl"), legend: $("lc-legend"),
    comparisons: $("lc-comparisons"), warnings: $("lc-warnings"), target: $("lc-target"), where: $("lc-where"),
  };
  let loaded = null;
  let version = 0;

  function hide(message = "") {
    el.box.hidden = !message;
    el.body.hidden = true;
    el.message.hidden = !message;
    el.message.textContent = message;
  }

  function list(box, lines) {
    box.querySelector("ul").replaceChildren(...lines.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }));
    box.hidden = lines.length === 0;
  }

  function render(lc, clicked) {
    const m = loaded.manifest;
    el.box.hidden = false;
    el.target.hidden = !clicked;
    el.where.textContent = `Position: ${lc.position_rule}.`;
    if (lc.method === "none") {
      el.body.hidden = true;
      el.message.hidden = false;
      el.message.textContent = `No light curve for ${m.label} in D${m.band}. ${lc.reason}`;
      return;
    }
    el.message.hidden = true;
    el.body.hidden = false;
    const n = measured(lc).length;
    el.summary.textContent = `${clicked ? "Clicked pixel" : m.label} · D${m.band} · ${n} of ${lc.points.length} exposures measured`;
    el.method.textContent = `${lc.method_text} Error bars: ${lc.error_text}.`;
    if (!n) {
      el.time.innerHTML = el.wl.innerHTML = "";
      list(el.comparisons, ["No exposure has a value inside the measuring circle here."]);
      list(el.warnings, lightCurveWarnings(lc));
      return;
    }
    el.time.innerHTML = timeChart(lc, m);
    el.wl.innerHTML = wavelengthChart(lc, m);
    el.legend.replaceChildren(...m.frames.map((f, i) => {
      const item = document.createElement("span");
      item.className = "lc-key";
      item.style.setProperty("--key", VISIT_COLOURS[i % VISIT_COLOURS.length]);
      item.textContent = `visit ${i + 1}: ${f.date_iso.slice(0, 10)}`;
      return item;
    }));
    list(el.comparisons, comparisonLines(lc, m));
    list(el.warnings, lightCurveWarnings(lc));
  }

  /** The target's light curve for frames that were just shown ({ manifest, base, where }), or hide (null). */
  async function show(frames) {
    const v = ++version;
    loaded = frames;
    if (!frames) return hide();
    let lc;
    try {
      lc = await loadExtra(frames.base, "lightcurve.json");
    } catch (err) {
      if (v === version) hide(`Could not load the light curve: ${err.message}`);
      return;
    }
    if (v !== version) return;
    if (!lc) return hide("No light curve was made for these frames yet.");
    render(lc, false);
  }

  /** Light curve of a clicked flipbook pixel (PNG pixels); needs the data API. */
  async function showPixel({ x, y }) {
    if (!loaded) return;
    const v = ++version;
    if (!(await hasApi())) {
      el.box.hidden = false;
      el.where.textContent = "Measuring a clicked pixel needs the data API (uvicorn backend.app.main:app); " +
        "this server only has the target's light curve.";
      return;
    }
    el.where.textContent = `Measuring pixel (${x}, ${y}) in every exposure…`;
    const url = framesQuery(loaded.where).replace("/api/frames?", "/api/lightcurve?") + `&x=${x}&y=${y}`;
    let body;
    let resp;
    try {
      resp = await fetch(url, { cache: "no-cache" });
      body = await resp.json();
    } catch {
      if (v === version) el.where.textContent = "Could not reach the data API.";
      return;
    }
    if (v !== version) return;
    if (!resp.ok) {
      el.where.textContent = body.error || `The data API answered HTTP ${resp.status}`;
      return;
    }
    render(body, true);
  }

  el.target.addEventListener("click", () => show(loaded));
  hide();
  return { show, showPixel };
}
