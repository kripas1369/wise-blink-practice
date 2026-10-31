// Before / After / Difference: two visits and (B − A) / sigma side by side, moving together.
// Rules (docs/plan/HACKATHON_PLAN.md, C1): the closest-wavelength pair is the default; flagged and
// no-value pixels stay striped; no cross-fade; every number comes from diff.json / gaia.json.
import { loadExtra } from "./frames.js";
import { directionText, expectedShift, gaiaTarget, percentAt, pixelToSky, pixelUnder } from "./sky.js";
import { formatDec, formatRa } from "./coords.js";

const $ = (id) => document.getElementById(id);
const SCATTER_WARN = 1.5;

export function findPair(diff, a, b) {
  return diff.pairs.find((p) => p.a === a && p.b === b) || null;
}

/** Visit A or B one step earlier (−1) or later (+1), keeping A before B; null when it cannot move. */
export function stepPair(ids, a, b, which, delta) {
  const ia = ids.indexOf(a) + (which === "a" ? delta : 0);
  const ib = ids.indexOf(b) + (which === "b" ? delta : 0);
  if (ia < 0 || ib >= ids.length || ia >= ib) return null;
  return [ids[ia], ids[ib]];
}

/** The line above the panels. */
export function pairFacts(pair, fa, fb) {
  const wl = pair.wl_gap_um === null
    ? "wavelength at the star unknown for one visit"
    : `wavelength at the star ${fa.wl_target_um.toFixed(3)} → ${fb.wl_target_um.toFixed(3)} µm ` +
      `(${pair.wl_gap_um.toFixed(3)} µm apart; mean of each add-up)`;
  return `${pair.days} days apart · ${wl} · sky change ${pair.sky_change >= 0 ? "+" : ""}${pair.sky_change.toFixed(3)} ` +
    `MJy/sr removed · ${pair.pct_flagged}% flagged and ${pair.pct_no_value}% without a value in either visit (striped)`;
}

/** Plain warnings a visitor must read before trusting a coloured spot. */
export function pairWarnings(pair, fa, fb) {
  const out = [];
  if (pair.scatter_sigma > SCATTER_WARN) {
    out.push(`The difference scatters ${pair.scatter_sigma}× more than the files' noise predicts, so large σ ` +
      "values here are not a detection by themselves (bright-star halos, wavelength and PSF differences all add to it).");
  }
  const ra = fa.wl_target_range_um;
  const rb = fb.wl_target_range_um;
  if (Array.isArray(ra) && Array.isArray(rb)) {
    out.push(`Each add-up mixes wavelengths (A ${ra[0].toFixed(3)}–${ra[1].toFixed(3)} µm, B ${rb[0].toFixed(3)}–${rb[1].toFixed(3)} µm), ` +
      "so a star whose brightness changes with wavelength can look brighter or fainter without changing.");
  }
  if (fa.n_images === 1 || fb.n_images === 1) {
    out.push("At least one panel is a single exposure, so it is noisier than an add-up.");
  }
  return out;
}

export function shiftText(gaia, iA, iB, pixelArcsec) {
  if (!gaia) return "No Gaia markers for these frames.";
  const t = gaiaTarget(gaia);
  if (!t) return "Gaia DR3 lists no star within 3″ of the frame centre, so there is no expected motion to compare with.";
  const s = expectedShift(gaia, iA, iB, pixelArcsec);
  if (s.px < 0.05) return `Gaia: the target moves ${s.px.toFixed(2)} px between A and B, too little to see.`;
  return `Gaia: the target should move ${s.px.toFixed(2)} px (${s.arcsec.toFixed(1)}″) toward the ${directionText(s.dx, s.dy)} ` +
    "between A and B. A moving star leaves a blue spot where it was (ring A) and an orange spot where it went (ring B); " +
    "a small pair can also come from alignment or PSF differences, so compare with a star that does not move.";
}

function valueText(frame, x, y) {
  const state = frame.state[y][x];
  if (state === "f") return "flagged";
  if (state === "n") return "no value";
  return `${frame.value[y][x].toFixed(3)} ± ${frame.sigma[y][x].toFixed(3)}`;
}

/** The readout line for one pixel. */
export function pixelText(diff, pair, ia, ib, x, y, manifest) {
  const { ra, dec } = pixelToSky(x, y, manifest);
  const z = pair.z[y][x];
  return `Pixel (${x}, ${y}) · RA ${formatRa(ra)} Dec ${formatDec(dec)} · A ${valueText(diff.frames[ia], x, y)} · ` +
    `B ${valueText(diff.frames[ib], x, y)} MJy/sr · (B − A)/σ ${z === null ? "none (striped)" : `${z >= 0 ? "+" : ""}${z.toFixed(1)}`}`;
}

export function createDiffView({ onPair = () => {} } = {}) {
  const el = {
    box: $("diff-view"), summary: $("diff-summary"), a: $("diff-a"), b: $("diff-b"), reset: $("diff-default"),
    reason: $("diff-reason"), facts: $("diff-facts"), warnings: $("diff-warnings"), shift: $("diff-shift"),
    readout: $("diff-readout"), message: $("diff-message"), panels: $("diff-panels"),
    stages: [...document.querySelectorAll(".diff-stage")],
    imgs: { a: $("diff-img-a"), b: $("diff-img-b"), d: $("diff-img-d") },
    caps: { a: $("diff-cap-a"), b: $("diff-cap-b"), d: $("diff-cap-d") },
    marks: { a: $("diff-marks-a"), b: $("diff-marks-b"), d: $("diff-marks-d") },
    steps: [...document.querySelectorAll("[data-step]")],
  };
  let state = null; // { manifest, base, gaia, diff }
  let version = 0;

  const indexOf = (epochId) => state.manifest.frames.findIndex((f) => f.epoch_id === epochId);

  function hide(message = "") {
    state = null;
    onPair(null);
    el.box.hidden = !message;
    el.panels.hidden = true;
    el.message.hidden = !message;
    el.message.textContent = message;
  }

  function ring(layer, xy, cls, text) {
    const size = state.manifest.size_px;
    const mark = document.createElement("span");
    mark.className = `diff-ring ${cls}`;
    const { left, top } = percentAt(xy, size);
    Object.assign(mark.style, { left: `${left}%`, top: `${top}%`, width: `${(100 / size) * 2.2}%` });
    mark.dataset.label = text;
    layer.append(mark);
  }

  function cursor(x, y) {
    const size = state.manifest.size_px;
    for (const stage of el.stages) {
      const box = stage.querySelector(".diff-cursor");
      box.hidden = x === null;
      if (x !== null) {
        Object.assign(box.style, {
          left: `${(x / size) * 100}%`, top: `${(y / size) * 100}%`, width: `${100 / size}%`, height: `${100 / size}%`,
        });
      }
    }
  }

  function render() {
    const a = Number(el.a.value);
    const b = Number(el.b.value);
    const pair = findPair(state.diff, a, b);
    const { manifest, gaia, base } = state;
    const ia = indexOf(a);
    const ib = indexOf(b);
    const fa = manifest.frames[ia];
    const fb = manifest.frames[ib];
    el.imgs.a.src = `${base}/${fa.png}`;
    el.imgs.b.src = `${base}/${fb.png}`;
    el.imgs.d.src = `${base}/${pair.png}`;
    el.imgs.a.alt = `Before: SPHEREx D${fa.band}, ${fa.date_iso}`;
    el.imgs.b.alt = `After: SPHEREx D${fb.band}, ${fb.date_iso}`;
    el.imgs.d.alt = `Difference after minus before, in sigma, ${pair.days} days`;
    const wl = (f) => (f.wl_target_um === null ? "wavelength unknown" : `${f.wl_target_um.toFixed(3)} µm`);
    el.caps.a.textContent = `A · ${fa.date_iso.slice(0, 10)} · D${fa.band} · ${wl(fa)} · ${fa.n_images} exp.`;
    el.caps.b.textContent = `B · ${fb.date_iso.slice(0, 10)} · D${fb.band} · ${wl(fb)} · ${fb.n_images} exp.`;
    el.caps.d.textContent = `(B − A)/σ · strongest +${pair.max_sigma} / ${pair.min_sigma} · scatter ${pair.scatter_sigma}`;
    el.facts.textContent = pairFacts(pair, fa, fb);
    const warnings = pairWarnings(pair, fa, fb);
    el.warnings.querySelector("ul").replaceChildren(...warnings.map((w) => {
      const li = document.createElement("li");
      li.textContent = w;
      return li;
    }));
    el.warnings.hidden = warnings.length === 0;
    el.shift.textContent = shiftText(gaia, ia, ib, manifest.pixel_arcsec);
    const isDefault = a === state.diff.default_pair.a && b === state.diff.default_pair.b;
    el.reason.textContent = isDefault ? `Default pair: ${state.diff.default_pair.reason}.` : "";
    for (const layer of Object.values(el.marks)) layer.replaceChildren();
    const t = gaiaTarget(gaia);
    if (t) {
      ring(el.marks.a, t.xy[ia], "ring-a", "A");
      ring(el.marks.b, t.xy[ib], "ring-b", "B");
      ring(el.marks.d, t.xy[ia], "ring-a", "A");
      ring(el.marks.d, t.xy[ib], "ring-b", "B");
    }
    cursor(null, null);
    el.readout.textContent = "Point at (or tap) a pixel to compare it in all three panels.";
    const ids = manifest.frames.map((f) => f.epoch_id);
    for (const button of el.steps) {
      const [which, delta] = button.dataset.step.split(":");
      button.disabled = stepPair(ids, a, b, which, Number(delta)) === null;
    }
    onPair(state, a, b);
  }

  /** Put the shared cursor on a pixel, as if pointed at. */
  function pointAt([x, y]) {
    if (!state) return;
    cursor(x, y);
    const a = Number(el.a.value);
    const b = Number(el.b.value);
    el.readout.textContent = pixelText(state.diff, findPair(state.diff, a, b), indexOf(a), indexOf(b), x, y, state.manifest);
  }

  function fillChoices() {
    const options = state.manifest.frames
      .map((f, i) => `<option value="${f.epoch_id}">${i + 1}: ${f.date_iso.slice(0, 10)}</option>`).join("");
    el.a.innerHTML = options;
    el.b.innerHTML = options;
  }

  function choose(a, b) {
    el.a.value = String(a);
    el.b.value = String(b);
    render();
  }

  /** Keep A earlier than B: the pairs exist in time order only. */
  function onPick(changed) {
    let a = Number(el.a.value);
    let b = Number(el.b.value);
    if (a === b) {
      const ids = state.manifest.frames.map((f) => f.epoch_id);
      const k = ids.indexOf(a);
      if (changed === "a") b = ids[k + 1] ?? ids[k - 1];
      else a = ids[k - 1] ?? ids[k + 1];
    }
    if (indexOf(a) > indexOf(b)) [a, b] = [b, a];
    choose(a, b);
  }

  function onPointer(event) {
    if (!state) return;
    const p = pixelUnder(event.clientX, event.clientY, event.currentTarget.getBoundingClientRect(), state.manifest.size_px);
    if (!p) return;
    cursor(p.x, p.y);
    const a = Number(el.a.value);
    const b = Number(el.b.value);
    el.readout.textContent = pixelText(state.diff, findPair(state.diff, a, b), indexOf(a), indexOf(b), p.x, p.y, state.manifest);
  }

  /** Show the view for loaded frames ({ manifest, base, gaia }), or hide it (null). */
  async function show(loaded) {
    const v = ++version;
    if (!loaded) return hide();
    if (loaded.manifest.frames.length < 2) return hide("Before / After / Difference needs at least two visits.");
    let diff;
    try {
      diff = await loadExtra(loaded.base, "diff.json");
    } catch (err) {
      if (v === version) hide(`Could not load the difference maps: ${err.message}`);
      return;
    }
    if (v !== version) return;
    if (!diff) return hide("No difference maps were made for these frames yet.");
    state = { ...loaded, diff };
    el.box.hidden = false;
    el.message.hidden = true;
    el.panels.hidden = false;
    el.summary.textContent = `${loaded.manifest.label} · D${loaded.manifest.band}`;
    fillChoices();
    choose(diff.default_pair.a, diff.default_pair.b);
  }

  el.a.addEventListener("change", () => onPick("a"));
  el.b.addEventListener("change", () => onPick("b"));
  el.reset.addEventListener("click", () => { if (state) choose(state.diff.default_pair.a, state.diff.default_pair.b); });
  for (const button of el.steps) {
    button.addEventListener("click", () => {
      if (!state) return;
      const [which, delta] = button.dataset.step.split(":");
      const next = stepPair(state.manifest.frames.map((f) => f.epoch_id), Number(el.a.value), Number(el.b.value),
        which, Number(delta));
      if (next) choose(...next);
    });
  }
  for (const stage of el.stages) {
    stage.addEventListener("pointermove", onPointer);
    stage.addEventListener("pointerdown", onPointer);
  }
  hide();
  return { show, pointAt };
}
