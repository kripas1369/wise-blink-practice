// The SPHEREx flipbook panel: play through visits, or blink two of them.
import { FRAMES_ROOT, frameLabel, loadIndex, loadManifest, spanDays } from "./frames.js";
import {
  BLINK_SPEEDS, DEFAULT_BLINK_SPEED, DEFAULT_SPEED, SPEEDS, defaultBlinkPair, intervalMs, nextIndex, prevIndex,
} from "./player.js";

const $ = (id) => document.getElementById(id);

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

/** `onDetector(n)` is called when the user picks a detector that has prepared frames. */
export function createFlipbook({ onDetector }) {
  const el = {
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

  let manifest = null;
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
  }

  function showMessage(text, detectorChoices = []) {
    stop();
    manifest = null;
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
      ? ` These prepared frames are ${m.fov_arcmin}′ wide; other sizes come with the data API (Day 3).` : "";
    const howMade = m.mode === "single"
      ? "Each frame is one SPHEREx exposure (not an add-up of the whole visit). "
      : "Each frame adds up several exposures of one visit, weighted by their noise, so faint things show " +
        "better; flagged pixels are left out of the add-up. ";
    el.note.textContent = `Real SPHEREx data from NASA IRSA, lined up north-up on ${m.size_px} × ${m.size_px} ` +
      `pixels of ${m.pixel_arcsec}″. ${howMade}Every frame uses the same brightness scale, but each exposure ` +
      `sees a slightly different wavelength (shown in the label), so brightness can differ for that reason too. ` +
      (m.mode === "single"
        ? "Striped pixels have no value in the SPHEREx file (for example a saturated star core). "
        : "Striped pixels have no usable value: the files have none there (for example a saturated star " +
          "core), or every exposure flagged that pixel (turn on the flagged-pixel overlay to see which). ") +
      `The ring marks the target's ${m.position_source.includes("2026") ? "2026" : "catalogue"} position. ` +
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

  /** Show the frames for an official target and detector; anything else gets an honest message. */
  async function show({ targetKey, label, det, fov }) {
    const version = ++loadVersion;
    stop();
    if (!targetKey) {
      showMessage("SPHEREx frames for any position arrive with the data API (Day 3). For now, pick one of the 5 official targets.");
      return;
    }
    try {
      if (available === null) available = await loadIndex();
      if (version !== loadVersion) return;
      const bands = available[targetKey] || [];
      if (!bands.includes(det)) {
        showMessage(
          bands.length
            ? `No prepared SPHEREx frames for ${label} in D${det} yet. Prepared:`
            : `No SPHEREx frames prepared for ${label} yet (they come with the data pipeline).`,
          bands,
        );
        return;
      }
      showMessage(`Loading SPHEREx frames for ${label}, D${det}…`);
      const m = await loadManifest(targetKey, det);
      if (version !== loadVersion) return;
      if (m === null) {
        showMessage(`No prepared SPHEREx frames for ${label} in D${det}.`);
        return;
      }
      const dir = `${FRAMES_ROOT}/${targetKey}/d${det}`;
      await Promise.all(m.frames.flatMap((f) => [f.png, f.flags_png].filter(Boolean).map((p) => loadImage(`${dir}/${p}`))));
      if (version !== loadVersion) return;
      manifest = m;
      folder = dir;
      el.message.hidden = true;
      el.img.hidden = false;
      el.overlays.forEach((o) => { o.hidden = false; });
      el.slider.max = String(count() - 1);
      setControlsEnabled(true);
      el.blinkA.disabled = el.blinkB.disabled = el.blinkToggle.disabled = count() < 2;
      fillBlinkChoices();
      describe(m, fov);
      render(mode === "blink" ? blinkPair()[0] : 0);
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
  el.stage.tabIndex = 0;
  el.stage.addEventListener("keydown", (e) => {
    if (!manifest) return;
    if (e.key === "ArrowRight") { stop(); step(1); e.preventDefault(); }
    if (e.key === "ArrowLeft") { stop(); step(-1); e.preventDefault(); }
    if (e.key === " ") { (mode === "play" ? togglePlay : toggleBlink)(); e.preventDefault(); }
  });

  showMessage("Pick one of the 5 official targets to see its SPHEREx visits.");
  return { show };
}
