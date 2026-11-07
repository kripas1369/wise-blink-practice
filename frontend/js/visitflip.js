// Inside one visit: flip through the single exposures behind the flipbook frame (hours to days apart), with the
// known asteroids and comets NASA JPL puts in the frame at each exposure time. Data: visits.json
// (backend/app/visit_frames.py). A moving spot without a JPL object is never called a new object.
import { loadExtra } from "./frames.js";
import { percentAt } from "./sky.js";

const $ = (id) => document.getElementById(id);
const PLAY_MS = 700;

/** "+3.2 h" / "+2.4 d" since the visit's first exposure. */
export function sinceFirst(hours) {
  if (hours === 0) return "first exposure";
  return hours < 48 ? `+${hours.toFixed(1)} h` : `+${(hours / 24).toFixed(1)} d`;
}

/** Caption under the picture. */
export function exposureCaption(visit, k) {
  const e = visit.exposures[k];
  const wl = e.wl_um === null ? "wavelength unknown" : `${e.wl_um.toFixed(3)} µm` + (e.bw_um === null ? "" : ` (±${(e.bw_um / 2).toFixed(3)})`);
  return `Exposure ${k + 1} of ${visit.n_exposures} · ${e.obs_id} · ${e.date_iso.replace("T", " ")} UTC · ` +
    `${sinceFirst(e.hours_from_first)} · ${wl} · ${e.pct_flagged}% flagged` +
    (e.pct_no_value ? ` · ${e.pct_no_value}% no value` : "");
}

/** One line per known object in an exposure. */
export function objectLine(o) {
  const mag = o.mag === null ? "" : `V ${o.mag.toFixed(1)}, `;
  return `${o.name}: ${mag}moving ${o.rate_arcsec_per_h}″/h, ${o.distance_au} AU away (JPL prediction)`;
}

/** { headline, lines } for an exposure's known-object answer. */
export function knownSummary(answer, vMax = null) {
  const limit = vMax === null ? "the search limit" : `V ${vMax}`;
  switch (answer.outcome) {
    case "objects":
      return { headline: `${answer.objects.length} known object${answer.objects.length === 1 ? "" : "s"} in the frame`,
        lines: answer.objects.map(objectLine) };
    case "none":
      return { headline: `No known asteroid or comet brighter than ${limit} in the frame`, lines: [
        `A moving spot here would still not be a new object: it can be a cosmic ray, an artifact or a known object fainter than ${limit}.`,
      ] };
    case "unavailable":
      return { headline: "Known-object check unavailable", lines: [`${answer.reason}.`] };
    default:
      return { headline: "Known objects not looked up for these frames", lines: [] };
  }
}

/** Visit span in words. */
export function spanText(visit) {
  return `${visit.n_exposures} exposure${visit.n_exposures === 1 ? "" : "s"} over ${sinceFirst(visit.span_hours).replace("+", "")}`;
}

/** `onExposure(visit, k)`: single exposure `k` of `visit` is now on screen. */
export function createVisitFlip({ onExposure = () => {} } = {}) {
  const el = {
    toggle: $("iv-toggle"), view: $("iv-view"), summary: $("iv-summary"), message: $("iv-message"), body: $("iv-body"),
    exposure: $("iv-exposure"), play: $("iv-play"), modePic: $("iv-mode-picture"), modeRes: $("iv-mode-residual"),
    flags: $("iv-flags"), known: $("iv-known"), img: $("iv-img"), flagsImg: $("iv-flags-img"), marks: $("iv-marks"),
    caption: $("iv-caption"), jplTitle: $("iv-jpl-title"), jplList: $("iv-jpl-list"), cautions: $("iv-cautions"),
    method: $("iv-method"), steps: document.querySelectorAll("#iv-view [data-iv-step]"),
  };
  let loaded = null;
  let visitIndex = 0;
  let data = null;
  let dataBase = null;
  let k = 0;
  let mode = "picture";
  let timer = null;
  let version = 0;

  const isOpen = () => el.toggle.getAttribute("aria-expanded") === "true";
  const visit = () => data.visits[visitIndex];

  function message(text) {
    el.message.textContent = text;
    el.message.hidden = !text;
    el.body.hidden = Boolean(text);
  }

  function li(text) {
    const n = document.createElement("li");
    n.textContent = text;
    return n;
  }

  function drawMarks(e) {
    el.marks.replaceChildren();
    if (!el.known.checked || !e.known.objects) return;
    for (const o of e.known.objects) {
      const box = document.createElement("span");
      box.className = "spot-mark iv-mark";
      const { left, top } = percentAt([o.x, o.y], data.size_px);
      Object.assign(box.style, { left: `${left}%`, top: `${top}%`, width: `${(100 / data.size_px) * 3}%` });
      box.dataset.label = o.name.split(" (")[0];
      el.marks.append(box);
    }
  }

  function render() {
    const v = visit();
    const e = v.exposures[k];
    const showRes = mode === "residual" && e.residual_png;
    el.img.src = `${loaded.base}/${showRes ? e.residual_png : e.png}`;
    el.img.alt = `${showRes ? "Minus the visit median" : "Single exposure"}: ${exposureCaption(v, k)}`;
    el.flagsImg.src = `${loaded.base}/${e.flags_png}`;
    el.flagsImg.hidden = !el.flags.checked;
    el.modeRes.disabled = !e.residual_png;
    el.exposure.value = String(k);
    el.steps.forEach((b) => {
      const next = k + Number(b.dataset.ivStep);
      b.disabled = next < 0 || next >= v.n_exposures;
    });
    el.caption.textContent = exposureCaption(v, k) +
      (showRes ? ` · grey = minus the median of the other exposures, black −${data.residual.sigma_range}σ to white +${data.residual.sigma_range}σ` : "");
    const { headline, lines } = knownSummary(e.known, data.known_v_max ?? null);
    el.jplTitle.textContent = headline;
    el.jplList.replaceChildren(...lines.map(li));
    drawMarks(e);
    onExposure(visitIndex, k);
  }

  function renderVisit() {
    const v = visit();
    if (k >= v.n_exposures) k = 0;
    el.summary.textContent = `visit ${visitIndex + 1} (${v.date_iso.slice(0, 10)}) · ${spanText(v)}`;
    el.exposure.replaceChildren(...v.exposures.map((e, i) =>
      new Option(`${i + 1}: ${sinceFirst(e.hours_from_first)} · ${e.wl_um === null ? "?" : e.wl_um.toFixed(3)} µm`, String(i))));
    el.cautions.querySelector("ul").replaceChildren(...data.notes.map(li));
    el.cautions.hidden = false;
    el.method.textContent = `Made by ${data.made_by}, ${data.made_at}, from exposures.fits (each exposure lined up on ` +
      `the flipbook grid, same brightness scale). Minus-median picture: ${data.residual.rule}. Known objects: ${data.known_objects}.`;
    render();
  }

  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
    el.play.textContent = "Play";
    el.play.setAttribute("aria-label", "Play the exposures");
  }

  function play() {
    if (timer) { stop(); return; }
    el.play.textContent = "Stop";
    el.play.setAttribute("aria-label", "Stop");
    timer = setInterval(() => {
      if (!data) return stop();
      k = (k + 1) % visit().n_exposures;
      render();
    }, PLAY_MS);
  }

  async function load() {
    const v = ++version;
    if (!loaded) return;
    if (dataBase !== loaded.base) {
      message("Loading the single exposures…");
      let file = null;
      try {
        file = await loadExtra(loaded.base, "visits.json");
      } catch (err) {
        if (v === version) message(`Could not load the single exposures: ${err.message}`);
        return;
      }
      if (v !== version) return;
      data = file;
      dataBase = loaded.base;
      k = 0;
    }
    if (!data) {
      message("No single-exposure frames for these frames yet. Make them with python -m backend.app.visit_frames <frames folder>.");
      return;
    }
    if (visitIndex >= data.visits.length) { message("This visit has no single exposures listed."); return; }
    message("");
    renderVisit();
  }

  function setOpen(open) {
    el.toggle.setAttribute("aria-expanded", String(open));
    el.view.hidden = !open;
    if (!open) { stop(); return; }
    load();
    el.view.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function choose(next) {
    if (!data) return;
    k = Math.min(visit().n_exposures - 1, Math.max(0, next));
    render();
  }

  el.toggle.addEventListener("click", () => setOpen(!isOpen()));
  el.exposure.addEventListener("change", () => { stop(); choose(Number(el.exposure.value)); });
  el.steps.forEach((b) => b.addEventListener("click", () => { stop(); choose(k + Number(b.dataset.ivStep)); }));
  el.play.addEventListener("click", play);
  for (const [button, next] of [[el.modePic, "picture"], [el.modeRes, "residual"]]) {
    button.addEventListener("click", () => {
      mode = next;
      el.modePic.setAttribute("aria-pressed", String(mode === "picture"));
      el.modeRes.setAttribute("aria-pressed", String(mode === "residual"));
      if (data) render();
    });
  }
  el.flags.addEventListener("change", () => { if (data) render(); });
  el.known.addEventListener("change", () => { if (data) render(); });
  el.view.addEventListener("keydown", (event) => {
    if (!data || event.target.tagName === "SELECT") return;
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      stop();
      choose(k + (event.key === "ArrowRight" ? 1 : -1));
    }
  });

  return {
    /** New frames ({ manifest, base } or null). */
    show(next) {
      loaded = next;
      version += 1;
      stop();
      el.toggle.disabled = !next;
      if (!next) { data = null; dataBase = null; el.view.hidden = true; el.toggle.setAttribute("aria-expanded", "false"); return; }
      if (isOpen()) load();
    },
    /** The flipbook now shows visit `i`. */
    visit(i) {
      if (i === visitIndex) return;
      visitIndex = i;
      k = 0;
      if (isOpen()) load();
    },
  };
}
