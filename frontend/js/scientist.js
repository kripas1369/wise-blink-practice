// Scientist view: the raw detector pixels of each exposure behind the flipbook frame, coloured by what their
// FLAGS say, with every number of the pixel under the pointer. Data: pixels<i>.json.gz (backend/app/pixels.py).
import { formatDec, formatRa } from "./coords.js";
import {
  CATEGORIES, binary32, bitUse, bitsSet, directionWords, greyLimits, hex32, loadPixels, pixelIndex, pixelInfo,
  startPixel,
} from "./pixels.js";

const $ = (id) => document.getElementById(id);
const CELL = 18;   // canvas pixels per detector pixel; CSS scales the canvas to the panel
const DIM = "rgba(0, 0, 0, 0.74)";

function node(tag, { className, text, attrs } = {}, children = []) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
  n.append(...children);
  return n;
}

function swatch(key) {
  const c = CATEGORIES[key].color;
  const s = node("span", { className: c ? "sci-swatch" : "sci-swatch sci-stripes", attrs: { "aria-hidden": "true" } });
  if (c) s.style.setProperty("--sw", c);
  return s;
}

const pct = (n, total) => (total ? `${((100 * n) / total).toFixed(1)}%` : "–");
const num = (v, digits = 4) => (v === null || v === undefined ? "no value" : String(Number(v.toPrecision(digits))));

function stripePattern(ctx) {
  const tile = document.createElement("canvas");
  tile.width = tile.height = 8;
  const t = tile.getContext("2d");
  t.fillStyle = "#0a0a0a";
  t.fillRect(0, 0, 8, 8);
  t.strokeStyle = "#48484a";
  t.lineWidth = 2;
  t.beginPath();
  t.moveTo(-2, 10); t.lineTo(10, -2);
  t.moveTo(-2, 2); t.lineTo(2, -2);
  t.moveTo(6, 10); t.lineTo(10, 6);
  t.stroke();
  return ctx.createPattern(tile, "repeat");
}

export function createScientistView() {
  const el = {
    toggle: $("sci-toggle"), view: $("sci-view"), summary: $("sci-summary"), message: $("sci-message"),
    body: $("sci-body"), exposure: $("sci-exposure"), modeFlags: $("sci-mode-flags"),
    modeBright: $("sci-mode-bright"), grid: $("sci-grid"), canvas: $("sci-canvas"), caption: $("sci-caption"), compass: $("sci-compass"),
    pixel: $("sci-pixel"), legend: $("sci-legend"), bits: $("sci-bits"), method: $("sci-method"),
    steps: document.querySelectorAll("#sci-view [data-sci-step]"),
  };
  const ctx = el.canvas.getContext("2d");
  const stripes = stripePattern(ctx);

  let loaded = null;
  let visitIndex = 0;
  let data = null;
  let expIndex = 0;
  let mode = "flags";
  let highlight = null;   // { kind: "category", key } or { kind: "bit", bit }
  let pinned = null;
  let hover = null;
  let version = 0;

  const isOpen = () => el.toggle.getAttribute("aria-expanded") === "true";
  const exposure = () => data.exposures[expIndex];

  function message(text) {
    el.message.textContent = text;
    el.message.hidden = !text;
    el.body.hidden = Boolean(text);
  }

  function matches(e, i) {
    if (!highlight) return true;
    if (highlight.kind === "category") return data.categories[e.category[i]] === highlight.key;
    return ((e.flag_values[e.flag_index[i]] >>> highlight.bit) & 1) === 1;
  }

  // ---------- picture ----------

  function draw() {
    const e = exposure();
    const [ny, nx] = e.shape;
    el.canvas.width = nx * CELL;
    el.canvas.height = ny * CELL;
    const limits = mode === "brightness" ? greyLimits(e.value) : null;
    for (let y = 0; y < ny; y += 1) {
      for (let x = 0; x < nx; x += 1) {
        const i = pixelIndex(e, x, y);
        const key = data.categories[e.category[i]];
        const px = x * CELL;
        const py = (ny - 1 - y) * CELL;   // FITS row 0 is the bottom row
        const v = e.value[i];
        if (mode === "flags") {
          ctx.fillStyle = CATEGORIES[key].color || stripes;
        } else if (v === null || !limits) {
          ctx.fillStyle = stripes;
        } else {
          const g = Math.round(255 * Math.min(1, Math.max(0, (v - limits.lo) / (limits.hi - limits.lo))));
          ctx.fillStyle = `rgb(${g}, ${g}, ${g})`;
        }
        ctx.fillRect(px, py, CELL, CELL);
        if (mode === "brightness" && (key === "bad" || key === "transient")) {
          ctx.strokeStyle = CATEGORIES[key].color;
          ctx.lineWidth = 3;
          ctx.strokeRect(px + 2.5, py + 2.5, CELL - 5, CELL - 5);
        }
        if (!matches(e, i)) {
          ctx.fillStyle = DIM;
          ctx.fillRect(px, py, CELL, CELL);
        }
      }
    }
    if (el.grid.checked) {
      ctx.strokeStyle = "rgba(0, 0, 0, 0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= nx; x += 1) { ctx.moveTo(x * CELL + 0.5, 0); ctx.lineTo(x * CELL + 0.5, ny * CELL); }
      for (let y = 0; y <= ny; y += 1) { ctx.moveTo(0, y * CELL + 0.5); ctx.lineTo(nx * CELL, y * CELL + 0.5); }
      ctx.stroke();
    }
    if (e.target_px) {
      const [tx, ty] = e.target_px;
      ctx.setLineDash([6, 5]);
      for (const [color, width] of [["#000", 4], ["#fff", 2]]) {
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        ctx.arc((tx + 0.5) * CELL, (ny - 1 - ty + 0.5) * CELL, 2.4 * CELL, 0, 2 * Math.PI);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    for (const [p, outer, inner] of [[hover, 3, 1.5], [pinned, 5, 3]]) {
      if (!p) continue;
      const px = p.x * CELL;
      const py = (ny - 1 - p.y) * CELL;
      ctx.strokeStyle = "#000";
      ctx.lineWidth = outer;
      ctx.strokeRect(px, py, CELL, CELL);
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = inner;
      ctx.strokeRect(px, py, CELL, CELL);
    }
  }

  /** North and east arrows beside the picture (inside it they would hide pixels). */
  function drawCompass(e) {
    const svg = "http://www.w3.org/2000/svg";
    const parts = [];
    for (const [label, [vx, vy]] of [["N", e.sky.north_px], ["E", e.sky.east_px]]) {
      const line = document.createElementNS(svg, "line");
      // view y grows upwards, SVG y downwards
      Object.entries({ x1: 0, y1: 0, x2: vx * 13, y2: -vy * 13 }).forEach(([k, v]) => line.setAttribute(k, v.toFixed(2)));
      const text = document.createElementNS(svg, "text");
      text.setAttribute("x", (vx * 19).toFixed(2));
      text.setAttribute("y", (-vy * 19).toFixed(2));
      text.textContent = label;
      parts.push(line, text);
    }
    el.compass.replaceChildren(...parts);
    el.compass.setAttribute("aria-label",
      `North points ${directionWords(e.sky.north_px)}, east points ${directionWords(e.sky.east_px)}`);
  }

  // ---------- pixel details ----------

  function renderPixel() {
    const p = hover || pinned;
    const e = exposure();
    const info = pixelInfo(data, e, p.x, p.y);
    const cat = CATEGORIES[info.category];
    const rows = [
      ["In this view", `x ${info.x}, y ${info.y}`],
      ["Detector pixel", info.detector ? `x ${info.detector[0]}, y ${info.detector[1]} (0-based)` : "unknown (no WCS \"A\" in the file)"],
      ["Sky", `${formatRa(info.ra)} ${formatDec(info.dec)} · ${info.ra.toFixed(5)}° ${info.dec >= 0 ? "+" : ""}${info.dec.toFixed(5)}°`],
      ["Wavelength", info.wavelength === null ? "unknown (no WCS-WAVE table)" : `${info.wavelength.toFixed(4)} µm`],
      ["Value", info.value === null ? "no value (NaN)"
        : `${num(info.value)} ± ${num(info.sigma, 3)} MJy/sr` + (info.snr === null ? "" : ` · ${info.snr.toFixed(1)}σ`)],
      ["FLAGS", `${info.flag} · ${hex32(info.flag)}`],
    ];
    const set = new Set(bitsSet(info.flag));
    const named = new Map(e.bits.map((b) => [b.bit, b.name]));
    const binary = node("code", { className: "sci-binary", attrs: { "aria-label": `binary ${binary32(info.flag)}` } });
    binary32(info.flag).replace(/ /g, "").split("").forEach((ch, k) => {
      const bit = 31 - k;
      if (k && k % 4 === 0) binary.append(" ");
      const span = node("span", { text: ch });
      if (set.has(bit)) {
        span.className = "on";
        span.title = `bit ${bit}${named.has(bit) ? ` ${named.get(bit)}` : ""}`;
      }
      binary.append(span);
    });
    const list = node("ul", { className: "sci-flaglist" });
    if (!info.flags.length) list.append(node("li", { text: "No bit set." }));
    for (const f of info.flags) {
      list.append(node("li", {}, [
        node("strong", { text: `bit ${f.bit} ${f.name}` }),
        `: ${f.meaning || "no meaning in the header"} · `,
        node("span", { className: f.rejected ? "sci-use sci-rejected" : "sci-use", text: f.known ? bitUse(f) : "not used by our rule" }),
      ]));
    }
    el.pixel.replaceChildren(
      node("h4", { text: hover ? "Pixel under the pointer" : "Chosen pixel" }),
      node("p", { className: "sci-cat" }, [swatch(info.category), node("strong", { text: cat.label }), ` · ${cat.meaning}`]),
      node("dl", { className: "sci-dl" }, rows.flatMap(([k, v]) => [node("dt", { text: k }), node("dd", { text: v })])),
      node("p", { className: "sci-sub", text: "The 32 bits (bit 31 on the left, bit 0 on the right; set bits bright):" }),
      binary,
      node("p", { className: "sci-sub", text: "What the set bits mean (from this file's FLAGS header):" }),
      list,
    );
  }

  // ---------- legend, bit table, words ----------

  function setHighlight(next) {
    const same = highlight && next && highlight.kind === next.kind && highlight.key === next.key && highlight.bit === next.bit;
    highlight = same ? null : next;
    renderLegend();
    renderBits();
    draw();
  }

  function renderLegend() {
    const e = exposure();
    const total = e.shape[0] * e.shape[1];
    el.legend.replaceChildren(...data.categories.map((key) => {
      const n = e.counts[key] || 0;
      const on = highlight && highlight.kind === "category" && highlight.key === key;
      const button = node("button", {
        className: "sci-chip",
        attrs: { type: "button", "aria-pressed": String(Boolean(on)), title: CATEGORIES[key].meaning },
      }, [swatch(key), `${CATEGORIES[key].label} `, node("span", { className: "sci-count", text: `${n} · ${pct(n, total)}` })]);
      button.disabled = n === 0;
      button.addEventListener("click", () => setHighlight({ kind: "category", key }));
      return node("li", {}, [button]);
    }));
  }

  function renderBits() {
    const e = exposure();
    const total = e.shape[0] * e.shape[1];
    const body = el.bits.querySelector("tbody");
    body.replaceChildren(...e.bits.map((b) => {
      const on = highlight && highlight.kind === "bit" && highlight.bit === b.bit;
      const button = node("button", {
        className: "sci-bitbtn", text: b.name,
        attrs: { type: "button", "aria-pressed": String(Boolean(on)), title: `Highlight the pixels with ${b.name} set` },
      });
      button.disabled = b.pixels === 0;
      button.addEventListener("click", () => setHighlight({ kind: "bit", bit: b.bit }));
      return node("tr", { className: b.pixels ? "" : "zero" }, [
        node("td", { className: "num", text: String(b.bit) }),
        node("td", { className: "num", text: String(2 ** b.bit) }),
        node("td", {}, [button]),
        node("td", { text: b.meaning }),
        node("td", {}, [node("span", { className: b.rejected ? "sci-use sci-rejected" : "sci-use", text: bitUse(b) })]),
        node("td", { className: "num", text: `${b.pixels} · ${pct(b.pixels, total)}` }),
      ]);
    }));
  }

  function renderWords() {
    const e = exposure();
    const [ny, nx] = e.shape;
    const where = e.detector_origin
      ? `detector pixels x ${e.detector_origin[0]}–${e.detector_origin[0] + nx - 1}, y ${e.detector_origin[1]}–${e.detector_origin[1] + ny - 1}`
      : `${nx} × ${ny} pixels`;
    drawCompass(e);
    el.caption.textContent = `${e.obs_id}, ${e.date_iso}: ${where}, shown as the detector sees them (not rotated, not ` +
      `lined up, not added up). Here north points ${directionWords(e.sky.north_px)} and east ` +
      `${directionWords(e.sky.east_px)}; x grows to the right and y upwards. Each square is one 6.15″ pixel. ` +
      `${data.target_ring}`;
    const rejected = (e.counts.bad || 0) + (e.counts.transient || 0) + (e.counts.no_value || 0);
    el.summary.textContent = `${data.label} · D${data.band} · visit ${data.frame + 1} (${data.date_iso.slice(0, 10)}) · ` +
      `exposure ${expIndex + 1} of ${data.exposures.length} · ${rejected} of ${nx * ny} pixels left out`;
    el.method.textContent = `Made by ${data.made_by}, ${data.made_at}, from the cached IRSA cutout ${e.cutout_file} ` +
      `(${data.crop}). Value = IMAGE − ZODI, σ = √VARIANCE. Categories use the same rule as the add-up ` +
      `(backend/app/clean.py). Sky positions come from a straight-line model of the file's WCS (largest error ` +
      `${e.sky.max_error_arcsec}″)` + (e.wavelength ? `; wavelengths from its WCS-WAVE table as a plane (largest ` +
      `error ${e.wavelength.max_error_um} µm)` : "") + ".";
  }

  function renderAll() {
    el.exposure.innerHTML = "";
    data.exposures.forEach((e, k) => {
      const out = (e.counts.bad || 0) + (e.counts.transient || 0) + (e.counts.no_value || 0);
      el.exposure.append(new Option(`${k + 1}: ${e.obs_id} · ${e.date_iso.slice(11, 19)} · ${out} left out`, String(k)));
    });
    el.exposure.value = String(expIndex);
    el.steps.forEach((b) => {
      const next = expIndex + Number(b.dataset.sciStep);
      b.disabled = next < 0 || next >= data.exposures.length;
    });
    renderLegend();
    renderBits();
    renderWords();
    draw();
    renderPixel();
  }

  function chooseExposure(k) {
    const keep = pinned;
    expIndex = k;
    const e = exposure();
    pinned = keep && keep.x < e.shape[1] && keep.y < e.shape[0] ? keep : startPixel(e);
    hover = null;
    renderAll();
  }

  // ---------- loading ----------

  async function load() {
    const v = ++version;
    if (!loaded) return;
    message("Loading the raw pixels of this visit…");
    try {
      const file = await loadPixels(loaded.base, visitIndex);
      if (v !== version) return;
      if (!file) {
        message("No raw-pixel file for this visit yet. Make one from the cached cutouts with " +
          "python -m backend.app.pixels <frames folder>.");
        return;
      }
      const first = data === null || data.target !== file.target || data.band !== file.band;
      data = file;
      if (first || expIndex >= data.exposures.length) expIndex = 0;
      const e = exposure();
      if (first || !pinned || pinned.x >= e.shape[1] || pinned.y >= e.shape[0]) pinned = startPixel(e);
      hover = null;
      message("");
      renderAll();
    } catch (err) {
      if (v === version) message(`Could not load the raw pixels: ${err.message}`);
    }
  }

  function setOpen(open) {
    el.toggle.setAttribute("aria-expanded", String(open));
    el.view.hidden = !open;
    if (open) {
      load();
      el.view.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // ---------- pointer and keys ----------

  function pixelAt(event) {
    if (!data) return null;
    const [ny, nx] = exposure().shape;
    const r = el.canvas.getBoundingClientRect();
    const x = Math.floor(((event.clientX - r.left) / r.width) * nx);
    const row = Math.floor(((event.clientY - r.top) / r.height) * ny);
    if (x < 0 || x >= nx || row < 0 || row >= ny) return null;
    return { x, y: ny - 1 - row };
  }

  el.toggle.addEventListener("click", () => setOpen(!isOpen()));
  el.canvas.addEventListener("pointermove", (event) => {
    const p = pixelAt(event);
    if (!p || (hover && hover.x === p.x && hover.y === p.y)) return;
    hover = p;
    draw();
    renderPixel();
  });
  el.canvas.addEventListener("pointerleave", () => {
    if (!hover) return;
    hover = null;
    draw();
    renderPixel();
  });
  el.canvas.addEventListener("click", (event) => {
    const p = pixelAt(event);
    if (!p) return;
    pinned = p;
    hover = null;
    draw();
    renderPixel();
  });
  el.canvas.addEventListener("keydown", (event) => {
    if (!data) return;
    const moves = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
    if (event.key === "Escape" && highlight) { setHighlight(null); return; }
    if (!(event.key in moves)) return;
    event.preventDefault();
    const [ny, nx] = exposure().shape;
    const [dx, dy] = moves[event.key];
    pinned = { x: Math.min(nx - 1, Math.max(0, pinned.x + dx)), y: Math.min(ny - 1, Math.max(0, pinned.y + dy)) };
    hover = null;
    draw();
    renderPixel();
  });
  el.exposure.addEventListener("change", () => chooseExposure(Number(el.exposure.value)));
  el.steps.forEach((b) => b.addEventListener("click", () => chooseExposure(expIndex + Number(b.dataset.sciStep))));
  for (const [button, next] of [[el.modeFlags, "flags"], [el.modeBright, "brightness"]]) {
    button.addEventListener("click", () => {
      mode = next;
      el.modeFlags.setAttribute("aria-pressed", String(mode === "flags"));
      el.modeBright.setAttribute("aria-pressed", String(mode === "brightness"));
      if (data) draw();
    });
  }
  el.grid.addEventListener("change", () => { if (data) draw(); });

  return {
    /** New frames ({ manifest, base } or null). The flipbook has already said which visit it shows. */
    show(next) {
      loaded = next;
      version += 1;
      el.toggle.disabled = !next;
      if (!next) { data = null; el.view.hidden = true; el.toggle.setAttribute("aria-expanded", "false"); return; }
      if (isOpen()) load();
    },
    /** The flipbook now shows visit `i`. */
    visit(i) {
      if (i === visitIndex) return;
      visitIndex = i;
      if (isOpen()) load();
    },
  };
}
