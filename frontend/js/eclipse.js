// Eclipse mode: SPHEREx exposures of a TESS eclipsing binary, sorted by orbital phase (backend/app/eclipse_build.py).
// Every number shown comes from frames/eclipse/<key>/eclipse.json; only the re-folding with a period typed or
// dragged here, and the scatter score θ, are computed in the browser.
import { ticks, wavelengthColour } from "./lightcurve.js";

const $ = (id) => document.getElementById(id);
const ROOT = "frames/eclipse/";
const LN_WL = [Math.log(0.75), Math.log(5.0)];
const W = 640;
const PAD = { left: 56, right: 14, top: 12, bottom: 38 };
const COLOURS = { primary: "#f5f5f7", secondary: "#ffc04d", null: "#86868b", tess: "#8fd3ff" };
const PDM_BINS = 20;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const fmt = (v, d = 3) => (v === null || v === undefined || !Number.isFinite(v) ? "–" : v.toFixed(d));
const pct = (v, d = 1) => (v === null || v === undefined ? "–" : `${(100 * v).toFixed(d)}%`);
const wlColour = (wl) => wavelengthColour(wl === null ? null : Math.log(wl), LN_WL);

async function getJSON(url) {
  const resp = await fetch(url, { cache: "no-cache" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json();
}

/** Phase in [-0.5, 0.5) with the primary eclipse at 0 (same rule as backend/app/eclipses.py). */
export function phaseOf(btjd, period, t0, primPos = 0) {
  const raw = (btjd - t0) / period - primPos + 0.5;
  return raw - Math.floor(raw) - 0.5;
}

/** Stellingwerf θ: pooled variance inside phase bins / total variance (low = the points line up). */
export function pdmTheta(t, y, period, nBins = PDM_BINS) {
  const n = new Float64Array(nBins);
  const s = new Float64Array(nBins);
  const s2 = new Float64Array(nBins);
  let sum = 0;
  let sum2 = 0;
  for (let i = 0; i < t.length; i++) {
    const f = t[i] / period;
    const b = Math.min(nBins - 1, Math.floor((f - Math.floor(f)) * nBins));
    n[b] += 1; s[b] += y[i]; s2[b] += y[i] * y[i];
    sum += y[i]; sum2 += y[i] * y[i];
  }
  const total = (sum2 - (sum * sum) / t.length) / (t.length - 1);
  let within = 0;
  let dof = 0;
  for (let b = 0; b < nBins; b++) {
    if (n[b] > 1) { within += s2[b] - (s[b] * s[b]) / n[b]; dof += n[b] - 1; }
  }
  return within / Math.max(1, dof) / total;
}

/** Which part of the orbit: 1 primary eclipse, 2 secondary, 0 outside (TESS widths). */
export function eclipsePart(phi, eph) {
  if (Math.abs(phi) < eph.prim_width / 2) return 1;
  if (eph.sec_phase !== null && eph.sec_width) {
    const d = Math.abs(phaseOf(phi, 1, eph.sec_phase));
    if (d < eph.sec_width / 2) return 2;
  }
  return 0;
}

// ---------- SVG charts ----------

function frame({ h = 240, x, y, xTicks, yTicks, xLabel, yLabel, logX = false }) {
  const tx = logX ? Math.log : (v) => v;
  const [x0, x1] = [tx(x[0]), tx(x[1])];
  const sx = (v) => PAD.left + ((tx(v) - x0) / (x1 - x0)) * (W - PAD.left - PAD.right);
  const sy = (v) => h - PAD.bottom - ((v - y[0]) / (y[1] - y[0])) * (h - PAD.top - PAD.bottom);
  const parts = [`<rect x="${PAD.left}" y="${PAD.top}" width="${W - PAD.left - PAD.right}" height="${h - PAD.top - PAD.bottom}" class="lc-frame"/>`];
  for (const v of yTicks) {
    parts.push(`<line x1="${PAD.left}" x2="${W - PAD.right}" y1="${sy(v.value)}" y2="${sy(v.value)}" class="lc-grid"/>`,
      `<text x="${PAD.left - 6}" y="${sy(v.value) + 4}" class="lc-tick" text-anchor="end">${esc(v.label)}</text>`);
  }
  for (const v of xTicks) {
    parts.push(`<text x="${sx(v.value)}" y="${h - PAD.bottom + 16}" class="lc-tick" text-anchor="middle">${esc(v.label)}</text>`);
  }
  parts.push(`<text x="${(PAD.left + W - PAD.right) / 2}" y="${h - 4}" class="lc-axis" text-anchor="middle">${esc(xLabel)}</text>`,
    `<text x="12" y="${(h - PAD.bottom + PAD.top) / 2}" class="lc-axis" text-anchor="middle" transform="rotate(-90 12 ${(h - PAD.bottom + PAD.top) / 2})">${esc(yLabel)}</text>`);
  const clipY = (v) => Math.min(y[1], Math.max(y[0], v));
  return { parts, sx, sy, clipY, h, done: (cls = "") => `<svg viewBox="0 0 ${W} ${h}" class="lc-svg ${cls}" role="img">${parts.join("")}</svg>` };
}

const numTicks = (lo, hi, n, digits) => ticks(lo, hi, n).map((v) => ({ value: v, label: v.toFixed(digits) }));
const WL_TICKS = [0.75, 1, 1.5, 2, 3, 4, 5].map((v) => ({ value: v, label: String(v) }));
const DET_EDGES = [1.095, 1.625, 2.415, 3.825, 4.415];

// ---------- page ----------

let el = null;
const elements = () => ({
  showcase: $("ec-showcase"), status: $("ec-status"), period: $("ec-period"), t0: $("ec-t0"), clock: $("ec-clock"),
  reset: $("ec-reset"), share: $("ec-share"), forecast: $("ec-forecast"), catalog: $("ec-catalog"),
  catalogNote: $("ec-catalog-note"), summary: $("ec-summary"), img: $("ec-img"), message: $("ec-message"),
  badge: $("ec-badge"), orbit: $("ec-orbit"), label: $("ec-label"), det: $("ec-det"), viewNorm: $("ec-view-norm"),
  viewRaw: $("ec-view-raw"), viewHelp: $("ec-view-help"), prev: $("ec-prev"), play: $("ec-play"), next: $("ec-next"),
  slider: $("ec-slider"), pos: $("ec-pos"), fold: $("fold-chart"), foldSummary: $("fold-summary"), map: $("map-chart"),
  depth: $("depth-chart"), depthSummary: $("depth-summary"), ratio: $("ratio-chart"), ratioFigure: $("ratio-figure"),
  checks: $("ec-checks"), periodSlider: $("period-slider"), periodValue: $("period-value"), periodSpan: $("period-span"),
  periodBest: $("period-best"), periodSummary: $("period-summary"), pdm: $("pdm-chart"), diffimg: $("diffimg"),
  diffMin: $("diffimg-min"), diffFacts: $("diffimg-facts"), diffSummary: $("diffimg-summary"), method: $("ec-method"),
});

const state = { index: null, catalog: null, e: null, base: "", det: null, order: [], k: 0, view: "norm",
  period: null, t0: null, timer: null, pdm: null, api: false, prepareVersion: 0 };

const setStatus = (text, kind = "info") => { el.status.textContent = text; el.status.className = `status ${kind}`; };

function eph() { return state.e.ephemeris; }
function phi(p) { return phaseOf(p.btjd, state.period, state.t0, eph().prim_pos); }
function baseline(f) {
  const b = state.e.baseline;
  return b.used ? b.c0 + b.a1 * Math.cos(2 * Math.PI * f) + b.a2 * Math.cos(4 * Math.PI * f) : 1;
}
const usable = (p) => p.used && p.g !== null;

function setUrl() {
  const q = new URLSearchParams();
  q.set("tic", state.e.ephemeris.tess_id);
  if (state.period !== eph().period) q.set("P", String(state.period));
  if (state.t0 !== eph().bjd0) q.set("t0", String(state.t0));
  if (state.det) q.set("det", String(state.det));
  history.replaceState(null, "", `?${q}`);
}

// ---------- left panel ----------

function renderShowcase() {
  const items = state.index.binaries;
  if (!items.length) {
    el.showcase.innerHTML = `<li class="muted">No binary is prepared yet (python -m backend.app.eclipse_build &lt;TIC&gt;).</li>`;
    return;
  }
  el.showcase.replaceChildren(...items.map((b) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "target";
    btn.dataset.key = b.key;
    btn.setAttribute("aria-pressed", "false");
    const depth = b.primary && b.primary.combined !== undefined ? ` · primary eclipse ${pct(b.primary.combined, 0)} deep in SPHEREx` : "";
    btn.innerHTML = `<span class="target-kind">Eclipsing binary · ${b.distance_from_nep_deg}° from the pole</span>
      <span class="target-name">${esc(b.label)}</span>
      <span class="target-hint">P = ${b.period.toFixed(4)} d · T = ${fmt(b.tmag, 1)} mag · ${b.n_points} exposures used${depth}</span>`;
    btn.addEventListener("click", () => load(b.key));
    li.append(btn);
    return li;
  }));
}

function renderForecast() {
  const e = state.e;
  const fc = e.forecast;
  const ep = e.ephemeris;
  const rows = Object.entries(fc.per_detector).map(([d, v]) =>
    `<tr><td>D${d}</td><td>${v.n_images}</td><td>${v.n_primary}</td><td>${v.n_secondary}</td><td>${e.selection.n_chosen[d] ?? 0}</td></tr>`).join("");
  const used = e.points.filter(usable).length;
  el.forecast.innerHTML = `
    <dl>
      <dt>Binary</dt><dd>${esc(e.label)}${e.gaia_match ? ` = Gaia DR3 ${esc(e.gaia_match.source_id)}` : ""}</dd>
      <dt>Position</dt><dd>${e.ra.toFixed(5)} ${e.dec >= 0 ? "+" : ""}${e.dec.toFixed(5)}</dd>
      <dt>TESS</dt><dd>P ${ep.period.toFixed(6)} d · primary ${pct(ep.prim_depth, 0)} deep, ${(ep.prim_width * ep.period * 24).toFixed(1)} h long${ep.sec_depth ? ` · secondary ${pct(ep.sec_depth, 0)}` : ""}</dd>
      <dt>Clock error</dt><dd>±${fmt(fc.phase_error, 4)} of an orbit (${(fc.phase_error * ep.period * 24 * 60).toFixed(1)} min) by the last exposure</dd>
    </dl>
    <p class="note">The SPHEREx archive lists <strong>${Object.values(fc.per_detector).reduce((a, v) => a + v.n_images, 0).toLocaleString()}</strong>
      images of this star (asked ${esc(fc.asked_at.slice(0, 10))}); <strong>${fc.n_primary.toLocaleString()}</strong> were taken during a primary
      eclipse and ${fc.n_secondary.toLocaleString()} during a secondary, worked out from their times alone, before downloading anything.</p>
    <div class="sci-table-wrap"><table class="sci-table ec-fc-table">
      <thead><tr><th>Det.</th><th>Images</th><th>In primary</th><th>In secondary</th><th>Downloaded</th></tr></thead>
      <tbody>${rows}</tbody></table></div>
    <p class="note">${used} exposures measured and used; the rest were flagged in the measuring circle, off the frame or failed.</p>`;
}

function renderCatalog() {
  const c = state.catalog;
  el.catalogNote.textContent = `${c.binaries.length} binaries from ${c.source}. ${c.rule}. Image counts are filled in for binaries whose SPHEREx archive list was fetched.`;
  el.catalog.querySelector("tbody").replaceChildren(...c.binaries.map((b) => {
    const tr = document.createElement("tr");
    const name = b.built ? `<button type="button" class="linklike" data-key="tic${b.tess_id}">${b.tess_id}</button>`
      : state.api ? `${b.tess_id} <button type="button" class="btn btn-small" data-tic="${b.tess_id}">Prepare</button>` : b.tess_id;
    tr.innerHTML = `<td>${name}</td><td>${b.distance_deg}°</td><td>${fmt(b.tmag, 1)}</td><td>${b.period.toFixed(4)}</td>
      <td>${pct(b.prim_depth, 0)}</td><td>${b.n_images ?? "–"}</td><td>${b.n_primary ?? "–"}</td>`;
    const btn = tr.querySelector("button");
    btn?.addEventListener("click", () => (btn.dataset.key ? load(btn.dataset.key) : prepare(btn.dataset.tic)));
    return tr;
  }));
}

/** Ask the data API to build a binary that is not prepared; polls while it works (minutes). */
async function prepare(tic) {
  const v = ++state.prepareVersion;
  for (;;) {
    let resp;
    let body;
    try {
      resp = await fetch(`/api/eclipse?tic=${encodeURIComponent(tic)}`, { cache: "no-cache" });
      body = await resp.json();
    } catch {
      setStatus("Could not reach the data API.", "error");
      return;
    }
    if (v !== state.prepareVersion) return;
    if (resp.status === 202) {
      setStatus(`${body.message} The page checks again every 10 s.`);
      await new Promise((r) => setTimeout(r, 10000));
      continue;
    }
    if (!resp.ok) { setStatus(body.error || `HTTP ${resp.status}`, "error"); return; }
    await load(body.key, { base: body.url });
    return;
  }
}

async function apiAvailable() {
  try {
    const resp = await fetch("/api/health", { cache: "no-cache" });
    return resp.ok && (await resp.json()).ok === true;
  } catch {
    return false;
  }
}

// ---------- flipbook ----------

function framesFor(det) {
  const fr = state.e.frames[det];
  if (!fr) return [];
  return [...fr.frames].sort((a, b) => phi(state.e.points[a.point]) - phi(state.e.points[b.point]));
}

function renderOrbit(f) {
  // Cartoon seen from the side: the companion passes in front of the primary star at phase 0.
  const x = Math.sin(2 * Math.PI * f);
  const front = Math.cos(2 * Math.PI * f) > 0;
  const big = `<circle cx="${100 - 18 * x}" cy="30" r="15" fill="#f5f5f7"/>`;
  const small = `<circle cx="${100 + 40 * x}" cy="30" r="10" fill="#ffc04d"/>`;
  el.orbit.innerHTML = `<svg viewBox="0 0 200 60" role="img" aria-label="Orbit cartoon">${front ? big + small : small + big}
    <text x="4" y="56" class="lc-tick">cartoon, not to scale · you are below</text></svg>`;
}

function showFrame(k) {
  if (!state.order.length) return;
  state.k = (k + state.order.length) % state.order.length;
  const f = state.order[state.k];
  const p = state.e.points[f.point];
  const ph = phi(p);
  const src = state.view === "norm" && f.png_n ? f.png_n : f.png;
  el.img.src = state.base + src;
  el.img.alt = `SPHEREx D${p.det} exposure at orbital phase ${ph.toFixed(3)}`;
  el.slider.value = state.k;
  el.pos.textContent = `${ph >= 0 ? "+" : ""}${ph.toFixed(3)} (${state.k + 1} of ${state.order.length})`;
  const part = eclipsePart(ph, eph());
  el.badge.hidden = part === 0;
  el.badge.textContent = part === 1 ? "Primary eclipse" : "Secondary eclipse";
  const rel = p.g !== null ? ` · ${(p.g).toFixed(2)} × normal at this wavelength` : "";
  const flux = p.flux !== null ? `${p.flux.toFixed(1)} ± ${p.err.toFixed(1)} mJy` : "no measurement";
  const why = !p.used ? (p.n_flagged ? ` · ${p.n_flagged} flagged pixel${p.n_flagged === 1 ? "" : "s"} in the circle, not used` : " · not used") : "";
  el.label.innerHTML = `<strong>${p.wl === null ? "wavelength unknown" : `${p.wl.toFixed(3)} µm`}</strong> · ${esc(p.date)}<br>
    ${flux}${rel}${why}`;
  renderOrbit(ph);
  drawFold();
}

function setView(view) {
  state.view = view;
  el.viewNorm.setAttribute("aria-pressed", String(view === "norm"));
  el.viewRaw.setAttribute("aria-pressed", String(view === "raw"));
  el.viewHelp.textContent = view === "norm"
    ? "Each picture is multiplied so that the binary's normal brightness at that picture's own wavelength is the same in every frame. Then only the eclipse changes it. Other stars have other colours, so they still flicker a little."
    : "Straight from SPHEREx (IMAGE − ZODI), one brightness scale per detector. The binary also changes because every picture sees a different wavelength.";
  showFrame(state.k);
}

function setDet(det) {
  state.det = Number(det);
  el.det.value = String(state.det);
  state.order = framesFor(state.det);
  el.slider.max = Math.max(0, state.order.length - 1);
  const start = state.order.findIndex((f) => phi(state.e.points[f.point]) >= -eph().prim_width);
  showFrame(Math.max(0, start));
  drawDiff();
  setUrl();
}

function togglePlay(on = !state.timer) {
  clearInterval(state.timer);
  state.timer = on ? setInterval(() => showFrame(state.k + 1), 280) : null;
  el.play.textContent = on ? "Pause" : "Play";
}

// ---------- charts ----------

function drawFold() {
  const e = state.e;
  if (!e) return;
  const pts = e.points.filter((p) => p.g !== null);
  const used = pts.filter(usable).map((p) => p.g).sort((a, b) => a - b);
  const lo = Math.min(0.9, used[Math.floor(used.length * 0.005)] ?? 0.5) - 0.05;
  const hi = Math.max(1.05, used[Math.ceil(used.length * 0.995) - 1] ?? 1.1) + 0.04;
  const c = frame({ x: [-0.5, 0.5], y: [lo, hi], xTicks: numTicks(-0.5, 0.5, 8, 2), yTicks: numTicks(lo, hi, 5, 2),
    xLabel: "orbital phase (0 = primary eclipse)", yLabel: "÷ normal brightness" });
  const ep = eph();
  const band = (centre, width, cls) => {
    for (const shift of [-1, 0, 1]) {
      const a = Math.max(-0.5, centre + shift - width / 2);
      const b = Math.min(0.5, centre + shift + width / 2);
      if (b > a) c.parts.push(`<rect x="${c.sx(a)}" y="${PAD.top}" width="${c.sx(b) - c.sx(a)}" height="${c.h - PAD.top - PAD.bottom}" class="${cls}"/>`);
    }
  };
  band(0, ep.prim_width, "ec-band");
  if (ep.sec_phase !== null && ep.sec_width) band(ep.sec_phase, ep.sec_width, "ec-band");
  c.parts.push(`<line x1="${PAD.left}" x2="${W - PAD.right}" y1="${c.sy(1)}" y2="${c.sy(1)}" class="lc-band"/>`);
  if (e.baseline.used) {
    const d = Array.from({ length: 101 }, (_, i) => -0.5 + i / 100)
      .map((f, i) => `${i ? "L" : "M"}${c.sx(f).toFixed(1)},${c.sy(baseline(f)).toFixed(1)}`).join("");
    c.parts.push(`<path d="${d}" class="lc-line" stroke="#86868b"/>`);
  }
  const current = state.order[state.k] && e.points[state.order[state.k].point];
  for (const p of pts) {
    const f = phi(p);
    const y = c.sy(c.clipY(p.g));
    const col = wlColour(p.wl);
    const title = `φ ${f.toFixed(3)} · ${fmt(p.wl)} µm · D${p.det} · ${p.g.toFixed(3)} × normal · ${p.date}${p.used ? "" : " · not used"}`;
    c.parts.push(`<circle cx="${c.sx(f).toFixed(1)}" cy="${y.toFixed(1)}" r="${p.used ? 3 : 2.5}" stroke="${col}" fill="${p.used ? col : "none"}"
      class="ec-pt" data-i="${e.points.indexOf(p)}"><title>${esc(title)}</title></circle>`);
  }
  if (current && current.g !== null) {
    c.parts.push(`<circle cx="${c.sx(phi(current))}" cy="${c.sy(c.clipY(current.g))}" r="8" class="ec-ring"/>`);
  }
  el.fold.innerHTML = c.done("ec-clickable");
  const n1 = pts.filter((p) => usable(p) && eclipsePart(phi(p), ep) === 1).length;
  el.foldSummary.textContent = `${pts.filter(usable).length} exposures · ${n1} in the primary eclipse · P = ${state.period.toFixed(6)} d`;
}

function drawMap() {
  const e = state.e;
  const pts = e.points.filter(usable);
  const c = frame({ h: 280, x: [-0.5, 0.5], y: [Math.log(0.72), Math.log(5.1)], xTicks: numTicks(-0.5, 0.5, 8, 2),
    yTicks: WL_TICKS.map((t) => ({ value: Math.log(t.value), label: t.label })), xLabel: "orbital phase",
    yLabel: "wavelength (µm)" });
  for (const p of pts) {
    const v = (e.baseline.used ? p.g / baseline(phi(p)) : p.g) - 1;
    const t = Math.max(-1, Math.min(1, v / 0.3));
    const col = t < 0 ? `hsl(220, 90%, ${Math.round(88 - 58 * -t)}%)` : `hsl(30, 95%, ${Math.round(88 - 30 * t)}%)`;
    c.parts.push(`<rect x="${(c.sx(phi(p)) - 2).toFixed(1)}" y="${(c.sy(Math.log(p.wl)) - 3).toFixed(1)}" width="4" height="6" fill="${col}">
      <title>φ ${phi(p).toFixed(3)} · ${p.wl.toFixed(3)} µm · ${(100 * v).toFixed(1)}%</title></rect>`);
  }
  el.map.innerHTML = c.done();
}

function drawDepth() {
  const d = state.e.depth;
  const rows = ["primary", "secondary", "null"].flatMap((k) => d[k].filter((r) => r.depth !== null).map((r) => ({ ...r, kind: k })));
  const tess = eph().prim_depth;
  const top = Math.max(tess, ...rows.map((r) => r.depth + r.err)) * 1.12;
  const bottom = Math.min(0, ...rows.map((r) => r.depth - r.err)) - 0.01;
  const c = frame({ h: 260, x: [0.6, 5.2], y: [bottom, top], logX: true, xTicks: [{ value: 0.6, label: "0.6" }, ...WL_TICKS],
    yTicks: ticks(bottom, top, 5).map((v) => ({ value: v, label: `${Math.round(v * 100)}%` })),
    xLabel: "wavelength (µm)", yLabel: "light lost in eclipse" });
  for (const x of DET_EDGES) c.parts.push(`<line x1="${c.sx(x)}" x2="${c.sx(x)}" y1="${PAD.top}" y2="${c.h - PAD.bottom}" class="lc-grid"/>`);
  c.parts.push(`<line x1="${c.sx(0.6)}" x2="${c.sx(1.0)}" y1="${c.sy(tess)}" y2="${c.sy(tess)}" stroke="${COLOURS.tess}" stroke-width="3" stroke-dasharray="6 3"><title>TESS primary depth ${pct(tess)} (0.6–1.0 µm)</title></line>`,
    `<line x1="${PAD.left}" x2="${W - PAD.right}" y1="${c.sy(0)}" y2="${c.sy(0)}" class="lc-band"/>`);
  const offset = { primary: 0, secondary: 0.012, null: -0.012 };
  for (const r of rows) {
    const x = c.sx(r.wl_mid * Math.exp(offset[r.kind]));
    const col = COLOURS[r.kind];
    c.parts.push(`<g class="lc-point"><title>${r.kind} · D${r.detector} ${r.wl_lo}–${r.wl_hi} µm · ${pct(r.depth)} ± ${pct(r.err)} · ${r.n} exposures</title>
      <line x1="${x}" x2="${x}" y1="${c.sy(c.clipY(r.depth - r.err))}" y2="${c.sy(c.clipY(r.depth + r.err))}" stroke="${col}"/>
      <circle cx="${x}" cy="${c.sy(r.depth)}" r="4.5" stroke="${col}" fill="${r.kind === "null" ? "none" : col}"/></g>`);
  }
  el.depth.innerHTML = c.done();
  const pc = state.e.checks.primary_combined;
  el.depthSummary.textContent = pc.n_bins ? `${pc.n_bins} wavelength bins · primary ${pct(pc.combined)} ± ${pct(pc.combined_err, 2)} (all bins)` : "";

  const ratio = d.secondary_over_primary.filter((r) => Number.isFinite(r.ratio));
  el.ratioFigure.hidden = ratio.length < 2;
  if (ratio.length < 2) return;
  const rTop = Math.max(1.1, ...ratio.map((r) => r.ratio + r.err)) * 1.05;
  const rBot = Math.min(0, ...ratio.map((r) => r.ratio - r.err));
  const rc = frame({ h: 200, x: [0.6, 5.2], y: [rBot, rTop], logX: true, xTicks: [{ value: 0.6, label: "0.6" }, ...WL_TICKS],
    yTicks: numTicks(rBot, rTop, 4, 1), xLabel: "wavelength (µm)", yLabel: "secondary ÷ primary" });
  rc.parts.push(`<line x1="${PAD.left}" x2="${W - PAD.right}" y1="${rc.sy(1)}" y2="${rc.sy(1)}" class="lc-band"/>`);
  for (const r of ratio) {
    const x = rc.sx(r.wl_mid);
    rc.parts.push(`<g class="lc-point"><title>D${r.detector} ${r.wl_mid} µm · ${r.ratio.toFixed(2)} ± ${r.err.toFixed(2)}</title>
      <line x1="${x}" x2="${x}" y1="${rc.sy(rc.clipY(r.ratio - r.err))}" y2="${rc.sy(rc.clipY(r.ratio + r.err))}" stroke="${COLOURS.secondary}"/>
      <circle cx="${x}" cy="${rc.sy(rc.clipY(r.ratio))}" r="4" stroke="${COLOURS.secondary}" fill="${COLOURS.secondary}"/></g>`);
  }
  el.ratio.innerHTML = rc.done();
}

function drawDiff() {
  const d = state.e.checks.difference_images[state.det];
  el.diffMin.hidden = true;
  if (!d) {
    el.diffimg.removeAttribute("src");
    el.diffSummary.textContent = `D${state.det}`;
    el.diffFacts.textContent = "Not enough exposures in the middle of the eclipse with an out-of-eclipse exposure at the same wavelength (needs 3 pairs).";
    return;
  }
  el.diffimg.src = state.base + d.png;
  el.diffSummary.textContent = `D${state.det} · ${d.n_pairs} pairs`;
  const size = state.e.size_px;
  el.diffMin.hidden = false;
  el.diffMin.style.left = `${((d.min_xy[0] + 0.5) / size) * 100}%`;
  el.diffMin.style.top = `${((d.min_xy[1] + 0.5) / size) * 100}%`;
  el.diffFacts.textContent = `Co-add of ${d.n_pairs} exposures in the middle of the primary eclipse minus ${d.n_pairs} outside it, ` +
    `paired by wavelength (largest gap ${d.max_wl_gap_um} µm). At the binary: ${fmt(d.z_at_binary, 1)}σ. The faintest pixel ` +
    `(${fmt(d.z_min, 1)}σ, small square) is ${d.min_distance_px} px from the binary. Typical pixel: ${d.scatter}σ.`;
}

// ---------- checks ----------

function card(title, verdict, lines) {
  const div = document.createElement("div");
  div.className = "proof-card";
  div.innerHTML = `<h4>${esc(title)}</h4><p class="proof-verdict" data-verdict="${verdict.toLowerCase().replace(/ /g, "-")}">${esc(verdict)}</p>
    <ul>${lines.map((l) => `<li>${l}</li>`).join("")}</ul>`;
  return div;
}

const within = (v, err, k = 3) => Math.abs(v) <= k * err;

function renderChecks() {
  const ch = state.e.checks;
  const cards = [];
  const nul = ch.null;
  cards.push(card("Between the eclipses", !nul.n_bins ? "Not available" : within(nul.combined, nul.combined_err) ? "Nothing, as expected" : "Not zero",
    [nul.n_bins ? `Depth at quarter phase, all wavelengths: ${pct(nul.combined, 2)} ± ${pct(nul.combined_err, 2)} (χ² ${nul.chi2} for ${nul.n_bins} bins).` : "Too few exposures at quarter phase.",
      "These exposures were kept out of the normal-brightness fit, so this is an independent test. Pass = within 3σ of 0."]));
  const fs = ch.field_stars;
  cards.push(card("Comparison stars", !fs.n_bins ? "Not available" : within(fs.combined, fs.combined_err) ? "No eclipse, as expected" : "Not zero",
    [fs.n_bins ? `${fs.n_bins} isolated Gaia stars in the same pictures, folded on the binary's clock: ${pct(fs.combined, 2)} ± ${pct(fs.combined_err, 2)}.` : "No isolated Gaia star bright enough in this frame.",
      ...fs.stars.filter((s) => s.depth !== null).slice(0, 4).map((s) => `Gaia DR3 …${esc(s.source_id.slice(-6))} (G ${s.g_mag}): ${pct(s.depth, 1)} ± ${pct(s.err, 1)}`)]));
  const diffs = Object.entries(ch.difference_images).filter(([, d]) => d);
  const centred = diffs.filter(([, d]) => d.min_distance_px <= 1.5);
  cards.push(card("The dimming is on the binary", !diffs.length ? "Not available" : centred.length === diffs.length ? "Yes" : `${centred.length} of ${diffs.length} detectors`,
    [`In-eclipse minus out-of-eclipse pictures: the faintest spot is within 1.5 px (9″) of the binary in ${centred.length} of ${diffs.length} detectors.`,
      ...diffs.map(([d, v]) => `D${d}: ${fmt(v.z_min, 0)}σ at ${v.min_distance_px} px`)]));
  const tb = ch.tess_band;
  cards.push(card("Same eclipse as TESS", !tb ? "Not available" : Math.abs(tb.spherex_d1_depth - tb.tess_depth) < 0.1 ? "Close" : "Different",
    tb ? [`TESS (0.6–1.0 µm): ${pct(tb.tess_depth)}. SPHEREx D1 (0.75–1.09 µm): ${pct(tb.spherex_d1_depth)} ± ${pct(tb.spherex_d1_err)}.`, esc(tb.note), "\"Close\" = within 10 percentage points."]
      : ["No D1 depth."]));
  const ps = ch.period_search;
  cards.push(card("SPHEREx finds the period alone", !ps || !ps.best ? "Not available" : ps.best_is ? "Yes" : "No",
    ps && ps.best ? [`Best period from SPHEREx alone: ${ps.best[0].period} d (θ ${ps.best[0].theta}); TESS: ${eph().period.toFixed(6)} d.`,
      ps.best_is ? `That is the ${esc(ps.best_is)} (within 0.2%).`
        : `Neither TESS's period nor half or twice it. θ is ${ps.best[0].theta} at best and ${ps.theta_median} for a typical trial: no period lines the exposures up clearly.`,
      `${ps.n_trials.toLocaleString()} trial periods from ${ps.p_min} to ${ps.p_max} d, no TESS information used.`] : [ps?.reason || ""]));
  const tm = ch.timing;
  const onTime = tm && !tm.at_search_edge && Math.abs(tm.delta_min) <= 3 * Math.hypot(tm.err_min, tm.tess_clock_err_min);
  cards.push(card("TESS's clock is still right", !tm ? "Not available" : onTime ? "Yes" : "Shifted",
    tm ? [`Middle of the primary eclipse in SPHEREx data: ${tm.delta_min >= 0 ? "+" : ""}${tm.delta_min} ± ${tm.err_min} min from TESS's prediction (${tm.n} exposures).`,
      `TESS's own clock error by then: ±${tm.tess_clock_err_min} min. "Yes" = within 3σ of both together.`,
      "A real shift would mean the period is changing, for example a third star pulling the pair."]
      : ["Too few exposures near the eclipse."]));
  el.checks.replaceChildren(...cards);
}

// ---------- period explorer ----------

function pdmData() {
  const pts = state.e.points.filter(usable);
  return { t: pts.map((p) => p.btjd), y: pts.map((p) => p.g) };
}

function periodRange() {
  const span = Number(el.periodSpan.value);
  const P = eph().period;
  return [P * (1 - span), P * (1 + span)];
}

function drawPdm() {
  const [a, b] = periodRange();
  const { t, y } = state.pdm;
  const n = 400;
  const curve = Array.from({ length: n }, (_, i) => {
    const P = a + ((b - a) * i) / (n - 1);
    return { P, theta: pdmTheta(t, y, P) };
  });
  state.pdmCurve = curve;
  const c = frame({ h: 200, x: [a, b], y: [0, 1.1], xTicks: numTicks(a, b, 5, b - a < 0.01 ? 5 : 3),
    yTicks: numTicks(0, 1, 4, 1), xLabel: "trial period (days)", yLabel: "θ (lower = cleaner)" });
  const d = curve.map((p, i) => `${i ? "L" : "M"}${c.sx(p.P).toFixed(1)},${c.sy(Math.min(1.1, p.theta)).toFixed(1)}`).join("");
  c.parts.push(`<path d="${d}" class="lc-line ec-pdm" stroke="#f5f5f7"/>`,
    `<line x1="${c.sx(eph().period)}" x2="${c.sx(eph().period)}" y1="${PAD.top}" y2="${c.h - PAD.bottom}" stroke="${COLOURS.tess}" stroke-dasharray="5 4"><title>TESS period</title></line>`,
    `<line x1="${c.sx(state.period)}" x2="${c.sx(state.period)}" y1="${PAD.top}" y2="${c.h - PAD.bottom}" stroke="#ffc04d"/>`);
  el.pdm.innerHTML = c.done();
}

function onPeriodSlider() {
  const [a, b] = periodRange();
  state.period = a + ((b - a) * Number(el.periodSlider.value)) / 1000;
  el.period.value = state.period.toFixed(7);
  const theta = pdmTheta(state.pdm.t, state.pdm.y, state.period);
  el.periodValue.textContent = `${state.period.toFixed(6)} d · θ = ${theta.toFixed(3)}`;
  refold();
}

function syncSlider() {
  const [a, b] = periodRange();
  el.periodSlider.value = String(Math.round(Math.max(0, Math.min(1, (state.period - a) / (b - a))) * 1000));
  const theta = pdmTheta(state.pdm.t, state.pdm.y, state.period);
  el.periodValue.textContent = `${state.period.toFixed(6)} d · θ = ${theta.toFixed(3)}`;
  const ps = state.e.checks.period_search;
  el.periodSummary.textContent = ps && ps.best ? `SPHEREx alone, 0.2–20 d: best ${ps.best[0].period} d · TESS ${eph().period.toFixed(6)} d` : "";
}

let refoldQueued = false;
function refold() {
  if (refoldQueued) return;
  refoldQueued = true;
  requestAnimationFrame(() => {
    refoldQueued = false;
    const current = state.order[state.k];
    state.order = framesFor(state.det);
    state.k = Math.max(0, state.order.indexOf(current));
    showFrame(state.k);
    drawMap();
    drawPdm();
    setUrl();
  });
}

// ---------- loading ----------

async function load(key, { period, t0, det, base } = {}) {
  togglePlay(false);
  setStatus(`Loading ${key}…`);
  const folder = base ?? `${ROOT}${key}/`;
  let e;
  try {
    e = await getJSON(`${folder}eclipse.json`);
  } catch (err) {
    setStatus(`Could not load ${key}: ${err.message}`, "error");
    return;
  }
  state.e = e;
  state.base = folder;
  state.period = period ?? e.ephemeris.period;
  state.t0 = t0 ?? e.ephemeris.bjd0;
  el.period.value = String(state.period);
  el.t0.value = String(state.t0);
  for (const b of el.showcase.querySelectorAll(".target")) b.setAttribute("aria-pressed", String(b.dataset.key === key));
  el.message.hidden = true;
  el.summary.textContent = `${e.label} · ${e.points.length} SPHEREx exposures · ${Object.keys(e.frames).length} detectors`;
  const dets = Object.keys(e.frames).map(Number);
  el.det.replaceChildren(...dets.map((d) => {
    const o = document.createElement("option");
    const ap = e.apertures[d];
    o.value = String(d);
    o.textContent = `D${d} (${e.frames[d].frames.length} exposures${ap.method === "wings" ? ", ring around saturated core" : ""})`;
    return o;
  }));
  renderForecast();
  renderChecks();
  drawDepth();
  state.pdm = pdmData();
  syncSlider();
  setDet(det && dets.includes(det) ? det : dets[0]);
  drawMap();
  drawPdm();
  el.method.innerHTML = Object.entries(e.method).map(([k, v]) => `<strong>${esc(k.replace(/_/g, " "))}:</strong> ${esc(v)}`).join(" ") +
    ` <strong>phase:</strong> ${esc(e.phase_rule)}. <strong>Position:</strong> ${esc(e.position_rule)}. Made by ${esc(e.made_by)} on ${esc(e.made_at)}. Data: ${esc(e.data_credit)}.`;
  setStatus(`${e.label}: ${e.points.filter(usable).length} exposures used.`, "ok");
  setUrl();
}

function wire() {
  el.det.addEventListener("change", () => setDet(el.det.value));
  el.viewNorm.addEventListener("click", () => setView("norm"));
  el.viewRaw.addEventListener("click", () => setView("raw"));
  el.prev.addEventListener("click", () => { togglePlay(false); showFrame(state.k - 1); });
  el.next.addEventListener("click", () => { togglePlay(false); showFrame(state.k + 1); });
  el.play.addEventListener("click", () => togglePlay());
  el.slider.addEventListener("input", () => { togglePlay(false); showFrame(Number(el.slider.value)); });
  el.fold.addEventListener("click", (ev) => {
    const i = ev.target.closest(".ec-pt")?.dataset.i;
    if (i === undefined) return;
    const p = state.e.points[Number(i)];
    if (p.det !== state.det) setDet(p.det);
    const k = state.order.findIndex((f) => f.point === Number(i));
    if (k >= 0) { togglePlay(false); showFrame(k); }
  });
  el.clock.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const P = Number(el.period.value);
    const t0 = Number(el.t0.value);
    if (!(P > 0) || !Number.isFinite(t0)) { setStatus("Period must be a positive number of days and t₀ a BTJD number.", "warn"); return; }
    state.period = P;
    state.t0 = t0;
    syncSlider();
    refold();
  });
  el.reset.addEventListener("click", () => {
    state.period = eph().period;
    state.t0 = eph().bjd0;
    el.period.value = String(state.period);
    el.t0.value = String(state.t0);
    syncSlider();
    refold();
  });
  el.share.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(location.href); setStatus("Link copied.", "ok"); } catch { setStatus(location.href); }
  });
  el.periodSlider.addEventListener("input", onPeriodSlider);
  el.periodSpan.addEventListener("change", () => { syncSlider(); drawPdm(); });
  el.periodBest.addEventListener("click", () => {
    const best = state.pdmCurve.reduce((a, b) => (b.theta < a.theta ? b : a));
    state.period = best.P;
    el.period.value = best.P.toFixed(7);
    syncSlider();
    refold();
  });
  document.addEventListener("keydown", (ev) => {
    if (!state.e || ev.target.closest("input, select, textarea")) return;
    if (ev.key === "ArrowRight") showFrame(state.k + 1);
    if (ev.key === "ArrowLeft") showFrame(state.k - 1);
  });
}

async function main() {
  el = elements();
  wire();
  setView("norm");
  try {
    [state.index, state.catalog] = await Promise.all([getJSON(`${ROOT}index.json`), getJSON(`${ROOT}catalog.json`)]);
  } catch (err) {
    setStatus(`Could not load the prepared binaries: ${err.message}`, "error");
    return;
  }
  state.api = await apiAvailable();
  renderShowcase();
  renderCatalog();
  const q = new URLSearchParams(location.search);
  const tic = q.get("tic")?.replace(/^tic/i, "");
  const key = tic ? `tic${tic}` : state.index.binaries[0]?.key;
  if (tic && !state.index.binaries.some((b) => b.key === key)) {
    if (state.api) prepare(tic);
    else setStatus(`TIC ${tic} is not prepared on this server, and preparing it needs the data API.`, "warn");
    return;
  }
  if (key) {
    await load(key, { period: q.has("P") ? Number(q.get("P")) : undefined, t0: q.has("t0") ? Number(q.get("t0")) : undefined,
      det: q.has("det") ? Number(q.get("det")) : undefined });
  }
}

if (typeof document !== "undefined" && document.getElementById("ec-showcase")) main();
