// The SPHEREx flipbook panel: play through visits, or blink two of them, with Gaia markers.
import { frameLabel, loadExtra, loadFrames, loadIndex, spanDays } from "./frames.js";
import {
  BLINK_SPEEDS, DEFAULT_BLINK_SPEED, DEFAULT_SPEED, SPEEDS, defaultBlinkPair, intervalMs, nextIndex, prevIndex,
} from "./player.js";
import { directionText, expectedShift, gaiaTarget, percentAt, pixelUnder, visibleStars } from "./sky.js";

const $ = (id) => document.getElementById(id);
const POLL_MS = 10000;
export const GAIA_LIMITS = [
  { value: "14", label: "brighter than G = 14" },
  { value: "16", label: "brighter than G = 16" },
  { value: "18", label: "brighter than G = 18" },
  { value: "all", label: "all Gaia stars" },
];
export const DEFAULT_GAIA_LIMIT = "16";

/** Draw Gaia markers for frame `i` into `layer` (a positioned box over the frame). */
export function drawGaia(layer, gaia, i, size, gMax, { trail = true } = {}) {
  layer.replaceChildren();
  if (!gaia) return;
  for (const star of visibleStars(gaia, gMax)) {
    if (star.target && trail) {
      star.xy.forEach((xy, k) => {
        if (k === i) return;
        const dot = document.createElement("span");
        dot.className = "gaia-trail";
        const { left, top } = percentAt(xy, size);
        Object.assign(dot.style, { left: `${left}%`, top: `${top}%` });
        layer.append(dot);
      });
    }
    const mark = document.createElement("span");
    mark.className = star.target ? "gaia-mark gaia-target" : "gaia-mark";
    const { left, top } = percentAt(star.xy[i], size);
    Object.assign(mark.style, { left: `${left}%`, top: `${top}%`, width: `${100 / size}%` });
    mark.title = `Gaia DR3 ${star.source_id}` + (star.g_mag !== null ? `, G ${star.g_mag}` : "") +
      (star.has_motion ? "" : " (no Gaia proper motion)");
    layer.append(mark);
  }
}

export function gaiaNote(gaia, pixelArcsec) {
  if (!gaia) return "No Gaia markers for these frames.";
  const t = gaiaTarget(gaia);
  const base = "Circles: where Gaia DR3 says each star should be on this visit's date (its 2016.0 position moved " +
    "with its proper motion; parallax not applied). ";
  if (!t) return `${base}Gaia DR3 lists no star within 3″ of the frame centre, so there is no target marker.`;
  const shift = expectedShift(gaia, 0, gaia.frames.length - 1, pixelArcsec);
  return `${base}Yellow: the target, Gaia DR3 ${t.source_id}` + (t.g_mag !== null ? ` (G ${t.g_mag})` : "") +
    `; dots are its predicted places on the other visits. Gaia: it moves ${shift.px.toFixed(2)} px ` +
    `(${shift.arcsec.toFixed(1)}″) from the first to the last visit` +
    (shift.px >= 0.05 ? `, toward the ${directionText(shift.dx, shift.dy)}.` : ".");
}

/** How the grey levels relate to brightness (manifest `scale`). */
export function scaleText(scale) {
  return scale.stretch === "asinh"
    ? "Every frame uses the same brightness scale, stretched (asinh) so faint light and bright stars both show; " +
      "grey levels are not proportional to brightness, so do not judge brightness changes by eye."
    : "Every frame uses the same brightness scale.";
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`could not load ${src}`));
    img.src = src;
  });
}

function fillSpeeds(select, speeds, chosen) {
  select.innerHTML = speeds.map((s) => `<option value="${s}">${s} per second</option>`).join("");
  select.value = String(chosen);
}

/**
 * `onDetector(n)`: the user picked a detector that has prepared frames.
 * `onFrames(loaded | null)`: frames were shown ({ manifest, base, gaia, where }) or cleared.
 * `onPixel({ x, y })`: the user clicked a pixel of the frame (PNG pixels, 0 = first).
 */
export function createFlipbook({ onDetector, onFrames = () => {}, onPixel = () => {} }) {
  const el = {
    gaia: $("flip-gaia"), showGaia: $("flip-show-gaia"), gaiaMag: $("flip-gaia-mag"), gaiaNoteBox: $("flip-gaia-note"),
    stage: $("flip-stage"), img: $("flip-img"), flags: $("flip-flags"), message: $("flip-message"),
    summary: $("flip-summary"), label: $("flip-label"), note: $("flip-note"), cautions: $("flip-cautions"),
    prev: $("flip-prev"), play: $("flip-play"), next: $("flip-next"), slider: $("flip-slider"),
    position: $("flip-position"), speed: $("flip-speed"), loop: $("flip-loop"), showFlags: $("flip-show-flags"),
    modePlay: $("mode-play"), modeBlink: $("mode-blink"), playControls: $("play-controls"),
    blinkControls: $("blink-controls"), blinkA: $("blink-a"), blinkB: $("blink-b"),
    blinkToggle: $("blink-toggle"), blinkSpeed: $("blink-speed"),
    overlays: document.querySelectorAll(".flip-target, .flip-compass, .flip-scale"),
    scale: document.querySelector(".flip-scale"),
  };
  fillSpeeds(el.speed, SPEEDS, DEFAULT_SPEED);
  fillSpeeds(el.blinkSpeed, BLINK_SPEEDS, DEFAULT_BLINK_SPEED);
  el.gaiaMag.innerHTML = GAIA_LIMITS.map((o) => `<option value="${o.value}">${o.label}</option>`).join("");
  el.gaiaMag.value = DEFAULT_GAIA_LIMIT;

  let manifest = null;
  let gaia = null;
  let pollTimer = null;
  let folder = "";
  let index = 0;
  let timer = null;
  let mode = "play";
  let blinkShowingA = true;
  let loadVersion = 0;
  let available = null;

  const count = () => (manifest ? manifest.frames.length : 0);

  function stop() {
    clearInterval(timer);
    timer = null;
    el.play.textContent = "Play";
    el.play.setAttribute("aria-label", "Play");
    el.blinkToggle.textContent = "Start blinking";
  }

  function setControlsEnabled(on) {
    for (const c of [el.prev, el.play, el.next, el.slider, el.speed, el.loop, el.blinkA, el.blinkB,
      el.blinkToggle, el.blinkSpeed, el.showFlags]) c.disabled = !on;
    el.showGaia.disabled = el.gaiaMag.disabled = !(on && gaia);
  }

  const gaiaLimit = () => (el.gaiaMag.value === "all" ? null : Number(el.gaiaMag.value));

  function renderGaia() {
    el.gaia.hidden = !(manifest && gaia && el.showGaia.checked);
    if (!el.gaia.hidden) drawGaia(el.gaia, gaia, index, manifest.size_px, gaiaLimit());
  }

  function showMessage(text, detectorChoices = []) {
    stop();
    manifest = null;
    gaia = null;
    el.gaia.hidden = true;
    el.gaiaNoteBox.textContent = "";
    el.img.hidden = true;
    el.flags.hidden = true;
    el.overlays.forEach((o) => { o.hidden = true; });
    el.message.hidden = false;
    el.message.textContent = text;
    for (const d of detectorChoices) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-small";
      button.textContent = `Show D${d}`;
      button.addEventListener("click", () => onDetector(d));
      el.message.append(" ", button);
    }
    el.summary.textContent = "";
    el.label.textContent = "";
    el.note.textContent = "";
    el.cautions.hidden = true;
    el.position.textContent = "–";
    setControlsEnabled(false);
  }

  function render(i) {
    index = i;
    const frame = manifest.frames[i];
    el.img.src = `${folder}/${frame.png}`;
    el.img.alt = `SPHEREx D${frame.band} image of ${manifest.label}, visit ${i + 1}, ${frame.date_iso}`;
    el.flags.hidden = !(el.showFlags.checked && frame.flags_png);
    if (frame.flags_png) el.flags.src = `${folder}/${frame.flags_png}`;
    el.label.textContent = frameLabel(frame, i, count());
    el.slider.value = String(i);
    el.position.textContent = `${i + 1} of ${count()}`;
    renderGaia();
  }

  function step(direction) {
    const n = direction > 0 ? nextIndex(index, count(), el.loop.checked) : prevIndex(index, count(), el.loop.checked);
    if (n === null) {
      stop();
      return;
    }
    render(n);
  }

  function togglePlay() {
    if (timer) return stop();
    if (!el.loop.checked && index === count() - 1) render(0);
    timer = setInterval(() => step(1), intervalMs(Number(el.speed.value)));
    el.play.textContent = "Pause";
    el.play.setAttribute("aria-label", "Pause");
  }

  function blinkPair() {
    return [Number(el.blinkA.value), Number(el.blinkB.value)];
  }

  function toggleBlink() {
    if (timer) return stop();
    const [a, b] = blinkPair();
    blinkShowingA = true;
    render(a);
    timer = setInterval(() => {
      blinkShowingA = !blinkShowingA;
      render(blinkShowingA ? a : b);
    }, intervalMs(Number(el.blinkSpeed.value)));
    el.blinkToggle.textContent = "Stop blinking";
  }

  function setMode(next) {
    stop();
    mode = next;
    el.modePlay.setAttribute("aria-selected", String(mode === "play"));
    el.modeBlink.setAttribute("aria-selected", String(mode === "blink"));
    el.playControls.hidden = mode !== "play";
    el.blinkControls.hidden = mode !== "blink";
    if (manifest) render(mode === "blink" ? blinkPair()[0] : index);
  }

  function restartIfRunning() {
    if (!timer) return;
    stop();
    if (mode === "play") togglePlay(); else toggleBlink();
  }

  function fillBlinkChoices() {
    const options = manifest.frames
      .map((f, i) => `<option value="${i}">${i + 1}: ${f.date_iso.slice(0, 10)}</option>`).join("");
    el.blinkA.innerHTML = options;
    el.blinkB.innerHTML = options;
    const [a, b] = defaultBlinkPair(count());
    el.blinkA.value = String(a);
    el.blinkB.value = String(b);
  }

  function describe(m, fov) {
    const n = m.frames.length;
    el.summary.textContent = `${m.label} · D${m.band} · ${n} visit${n === 1 ? "" : "s"}` +
      (n > 1 ? ` over ${spanDays(m.frames)} days` : "");
    const sizeNote = fov !== m.fov_arcmin
      ? ` These frames are ${m.fov_arcmin}′ wide; other sizes need the data API.` : "";
    const howMade = m.mode === "single"
      ? "Each frame is one SPHEREx exposure (not an add-up of the whole visit). "
      : "Each frame adds up several exposures of one visit, weighted by their noise, so faint things show " +
        "better; flagged pixels are left out of the add-up. ";
    el.note.textContent = `Real SPHEREx data from NASA IRSA, lined up north-up on ${m.size_px} × ${m.size_px} ` +
      `pixels of ${m.pixel_arcsec}″. ${howMade}${scaleText(m.scale)} Each exposure also sees a slightly ` +
      `different wavelength (shown in the label), so brightness can differ for that reason too. ` +
      (m.mode === "single"
        ? "Striped pixels have no value in the SPHEREx file (for example a saturated star core). "
        : "Striped pixels have no usable value: the files have none there (for example a saturated star " +
          "core), or every exposure flagged that pixel (turn on the flagged-pixel overlay to see which). ") +
      (m.position_source.includes("2026") ? "The dashed ring marks the target's 2026 position. "
        : "The dashed ring marks the centre of the frame. ") +
      `Made by ${m.made_by}, ${m.made_at}.${sizeNote}`;
    el.scale.style.width = `${(60 / m.pixel_arcsec / m.size_px) * 100}%`;
    const list = el.cautions.querySelector("ul");
    list.replaceChildren(...(m.notes || []).map((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    }));
    el.cautions.hidden = !(m.notes && m.notes.length);
  }

  async function preparedBands(targetKey) {
    if (!targetKey) return [];
    try {
      if (available === null) available = await loadIndex();
    } catch {
      return [];
    }
    return available[targetKey] || [];
  }

  /**
   * Show the frames for a position and detector ({ targetKey, label, ra, dec, det, fov }).
   * While the data API prepares frames for a new position, it asks again every 10 seconds.
   */
  async function show(where) {
    const version = ++loadVersion;
    clearTimeout(pollTimer);
    stop();
    const { label, det } = where;
    const name = label || "this position";
    try {
      showMessage(`Loading SPHEREx frames for ${name}, D${det}…`);
      onFrames(null);
      const result = await loadFrames(where);
      if (version !== loadVersion) return;
      if (result.status === "working") {
        showMessage(`${result.message} Checking again every ${POLL_MS / 1000} seconds.`);
        pollTimer = setTimeout(() => { if (version === loadVersion) show(where); }, POLL_MS);
        return;
      }
      if (result.status === "none") {
        const bands = (await preparedBands(where.targetKey)).filter((b) => b !== det);
        if (version !== loadVersion) return;
        showMessage(bands.length ? `${result.message} Prepared:` : result.message, bands);
        return;
      }
      const m = result.manifest;
      const dir = result.base;
      const [extraGaia] = await Promise.all([
        loadExtra(dir, "gaia.json").catch(() => null),
        ...m.frames.flatMap((f) => [f.png, f.flags_png].filter(Boolean).map((p) => loadImage(`${dir}/${p}`))),
      ]);
      if (version !== loadVersion) return;
      manifest = m;
      gaia = extraGaia && extraGaia.frames.length === m.frames.length ? extraGaia : null;
      folder = dir;
      el.message.hidden = true;
      el.img.hidden = false;
      el.overlays.forEach((o) => { o.hidden = false; });
      el.slider.max = String(count() - 1);
      setControlsEnabled(true);
      el.blinkA.disabled = el.blinkB.disabled = el.blinkToggle.disabled = count() < 2;
      fillBlinkChoices();
      describe(m, where.fov);
      if (result.warnings.length) el.note.textContent += ` Warnings: ${result.warnings.join("; ")}`;
      el.gaiaNoteBox.textContent = gaiaNote(gaia, m.pixel_arcsec);
      render(mode === "blink" ? blinkPair()[0] : 0);
      onFrames({ manifest: m, base: dir, gaia, where });
    } catch (err) {
      if (version !== loadVersion) return;
      showMessage(`Could not load the SPHEREx frames: ${err.message}`);
    }
  }

  el.prev.addEventListener("click", () => { stop(); step(-1); });
  el.next.addEventListener("click", () => { stop(); step(1); });
  el.play.addEventListener("click", togglePlay);
  el.slider.addEventListener("input", () => { stop(); render(Number(el.slider.value)); });
  el.speed.addEventListener("change", restartIfRunning);
  el.blinkSpeed.addEventListener("change", restartIfRunning);
  el.blinkToggle.addEventListener("click", toggleBlink);
  el.blinkA.addEventListener("change", () => { stop(); render(blinkPair()[0]); });
  el.blinkB.addEventListener("change", () => { stop(); render(blinkPair()[1]); });
  el.modePlay.addEventListener("click", () => setMode("play"));
  el.modeBlink.addEventListener("click", () => setMode("blink"));
  el.showFlags.addEventListener("change", () => { if (manifest) render(index); });
  el.showGaia.addEventListener("change", renderGaia);
  el.gaiaMag.addEventListener("change", renderGaia);
  el.stage.addEventListener("click", (e) => {
    if (!manifest) return;
    const p = pixelUnder(e.clientX, e.clientY, el.img.getBoundingClientRect(), manifest.size_px);
    if (p) onPixel(p);
  });
  el.stage.tabIndex = 0;
  el.stage.addEventListener("keydown", (e) => {
    if (!manifest) return;
    if (e.key === "ArrowRight") { stop(); step(1); e.preventDefault(); }
    if (e.key === "ArrowLeft") { stop(); step(-1); e.preventDefault(); }
    if (e.key === " ") { (mode === "play" ? togglePlay : toggleBlink)(); e.preventDefault(); }
  });

  showMessage("Pick one of the 5 official targets, or type a position, to see its SPHEREx visits.");
  return { show, gaiaLimit: () => el.gaiaMag.value };
}
