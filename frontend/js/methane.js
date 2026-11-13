// Methane vision panel: 3.3 µm (methane band), 4 µm (window) and their difference for every visit
// (methane/methane.json, made by backend/app/methane.py). Every number comes from that file.
import { framesQuery, hasApi, loadExtra } from "./frames.js";
import { targetBase } from "./spectrum.js";

const $ = (id) => document.getElementById(id);
const PLAY_MS = 900;
const BLINK_MS = 650;
const POLL_MS = 5000;

const VERDICTS = {
  glows: "Glows in methane vision",
  normal: "Normal star colour",
  bluer: "Bluer than a normal star",
  unclear: "Redder, but not clearly methane",
  too_faint: "Too faint to test",
  not_testable: "Cannot be tested here",
};

export const verdictTitle = (status) => VERDICTS[status] || status;

const um = (r) => `${r[0].toFixed(2)}–${r[1].toFixed(2)} µm`;

/** Lines under the verdict: the measured numbers and where k comes from. */
export function numberLines(data) {
  const c = data.target.colour;
  const s = data.settings;
  const lines = [];
  if (c.testable) {
    const more = c.excess_is_lower_limit ? "at least " : "";
    const err = c.excess_err === null ? "" : ` ± ${c.excess_err}`;
    lines.push(`At ${um(s.window.range_um)} it has ${more}${c.excess}${err}× the light a normal star with its ` +
      `${um(s.absorbed.range_um)} light would have (${c.glow_sigma >= 0 ? "+" : ""}${c.glow_sigma}σ).`);
    lines.push(`Measured: ${c.absorbed_mjy} ± ${c.absorbed_err_mjy} mJy (methane band) and ` +
      `${c.window_mjy} ± ${c.window_err_mjy} mJy (window), both scaled to ${s.ref_um} µm for a normal star.`);
  }
  lines.push(`Normal-star colour k = ${data.calibration.k}: ${data.calibration.rule}.`);
  lines.push(`Glow rule: at least ${s.methane_excess}× and ${s.glow_sigma}σ; normal within ±${s.normal_sigma}σ.`);
  const n = data.null_test;
  if (n && n.scatter !== null) {
    lines.push(`Null test: the same measurement at ${n.n_places} places away from the target scatters ±${n.scatter}σ ` +
      `(largest ${n.largest}σ), so every σ here is divided by ${n.factor}.`);
  }
  return lines;
}

/** The line under the pictures for one visit, or for all visits added (visit = null). */
export function visitCaption(data, visit) {
  if (visit === null) {
    return `All visits added: ${data.all.n_absorbed} exposures at ${um(data.settings.absorbed.range_um)} (D${data.settings.absorbed.band}) ` +
      `and ${data.all.n_window} at ${um(data.settings.window.range_um)} (D${data.settings.window.band}). A moving source is smeared here.`;
  }
  const v = data.visits[visit];
  const wl = (list) => (list.length ? `${Math.min(...list).toFixed(2)}–${Math.max(...list).toFixed(2)} µm` : "none");
  const glow = v.colour.testable ? ` · target ${v.colour.glow_sigma >= 0 ? "+" : ""}${v.colour.glow_sigma}σ` : "";
  return `Visit ${visit + 1} of ${data.visits.length} · ${v.date} · ${v.absorbed.n} exposure${v.absorbed.n === 1 ? "" : "s"} ` +
    `at ${wl(v.absorbed.wl_um)} and ${v.window.n} at ${wl(v.window.wl_um)}${glow}`;
}

/** CSS position of a PNG pixel (x right, y down) on a square stage. */
export function markerStyle([x, y], size) {
  return { left: `${((x + 0.5) / size) * 100}%`, top: `${((y + 0.5) / size) * 100}%` };
}

export function downloadLines(data) {
  if (!data.downloads) return [];
  return Object.entries(data.downloads).map(([det, d]) => {
    const archive = d.n_in_archive === null ? "" : `${d.n_in_archive} images in the archive, `;
    return `${det}: ${archive}${d.n_considered} looked at, ${d.n_in_window} at the right wavelength` +
      (d.n_off_grid ? `, ${d.n_off_grid} left out (target near the image edge)` : "") +
      (d.n_failed ? `, ${d.n_failed} failed to download` : "") + ".";
  });
}

async function askApi(loaded, prepare, fetchFn) {
  const url = framesQuery(loaded.where).replace("/api/frames?", "/api/methane?") + (prepare ? "&prepare=1" : "");
  let resp;
  try {
    resp = await fetchFn(url, { cache: "no-cache" });
  } catch {
    throw new Error("Could not reach the data API");
  }
  const body = await resp.json().catch(() => ({}));
  if (resp.status === 202) return { status: "working", message: body.message || "Preparing methane vision…" };
  if (resp.status === 404) return { status: "none", message: body.error || "No methane vision here", canPrepare: !!body.can_prepare };
  if (!resp.ok) throw new Error(body.error || `The data API answered HTTP ${resp.status}`);
  return { status: "ready", data: body, base: body.base_url.replace(/\/$/, "") };
}

export async function loadMethane(loaded, { prepare = false, fetchFn = fetch } = {}) {
  if (await hasApi(fetchFn)) return askApi(loaded, prepare, fetchFn);
  const base = `${targetBase(loaded.base)}/methane`;
  const data = await loadExtra(base, "methane.json", fetchFn);
  if (!data) return { status: "none", message: "Methane vision was not prepared for this target.", canPrepare: false };
  return { status: "ready", data, base };
}

export function createMethane() {
  const el = {
    box: $("ch4-view"), message: $("ch4-message"), prepare: $("ch4-prepare"), body: $("ch4-body"),
    summary: $("ch4-summary"), verdict: $("ch4-verdict"), combined: $("ch4-combined"), numbers: $("ch4-numbers"),
    visit: $("ch4-visit"), play: $("ch4-play"), blink: $("ch4-blink"), caption: $("ch4-caption"),
    imgA: $("ch4-img-a"), imgB: $("ch4-img-b"), imgM: $("ch4-img-m"), capA: $("ch4-cap-a"), capB: $("ch4-cap-b"),
    marksA: $("ch4-marks-a"), marksB: $("ch4-marks-b"), marksM: $("ch4-marks-m"),
    others: $("ch4-others"), warnings: $("ch4-warnings"), downloads: $("ch4-downloads"), method: $("ch4-method"),
  };
  let version = 0;
  let current = null;   // { data, base, loaded }
  let visit = null;     // index, or null = all visits added
  let playTimer = null;
  let blinkTimer = null;
  let pollTimer = null;
  let showingWindow = false;

  function fill(ul, lines) {
    ul.replaceChildren(...lines.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }));
  }

  function stopTimers() {
    clearInterval(playTimer);
    clearInterval(blinkTimer);
    clearTimeout(pollTimer);
    playTimer = blinkTimer = pollTimer = null;
    el.play.textContent = "Play visits";
    el.blink.textContent = "Blink 3.3 ↔ 4 µm";
    showingWindow = false;
  }

  function hide(message = "", canPrepare = false) {
    el.box.hidden = !message;
    el.body.hidden = true;
    el.message.hidden = !message;
    el.message.textContent = message;
    el.prepare.hidden = !canPrepare;
  }

  function ring(layer, xy, size, className, label = "") {
    const mark = document.createElement("span");
    mark.className = className;
    Object.assign(mark.style, markerStyle(xy, size));
    if (label) mark.dataset.label = label;
    layer.appendChild(mark);
  }

  function drawMarks() {
    const { data } = current;
    const size = data.size_px;
    const v = visit === null ? null : data.visits[visit];
    const xy = v ? v.target_xy : (data.visits[Math.floor(data.visits.length / 2)] || {}).target_xy;
    for (const layer of [el.marksA, el.marksB, el.marksM]) {
      layer.replaceChildren();
      if (xy) ring(layer, xy, size, "ch4-ring");
    }
    if (visit === null) data.other_glows.forEach((o, i) => ring(el.marksM, [o.x, o.y], size, "ch4-ring ch4-other", String(i + 1)));
  }

  function drawVisit() {
    const { data, base } = current;
    const pics = visit === null ? data.all : data.visits[visit];
    el.imgA.src = `${base}/${showingWindow ? pics.window_png : pics.absorbed_png}`;
    el.capA.textContent = showingWindow
      ? `${um(data.settings.window.range_um)} (D${data.settings.window.band}) · blinking`
      : `${um(data.settings.absorbed.range_um)} (D${data.settings.absorbed.band}) · methane band`;
    el.imgB.src = `${base}/${pics.window_png}`;
    el.imgM.src = `${base}/${pics.methane_png}`;
    el.caption.textContent = visitCaption(data, visit);
    el.visit.value = visit === null ? "all" : String(visit);
    drawMarks();
  }

  function render() {
    const { data } = current;
    const s = data.settings;
    el.box.hidden = false;
    el.message.hidden = true;
    el.prepare.hidden = true;
    el.body.hidden = false;
    el.summary.textContent = `${data.label} · D${s.absorbed.band} ÷ D${s.window.band} · ${data.visits.length} visit${data.visits.length === 1 ? "" : "s"}`;
    el.verdict.textContent = verdictTitle(data.target.verdict.status);
    el.verdict.dataset.status = data.target.verdict.status;
    el.combined.textContent = `${data.target.verdict.text} ${data.summary}`;
    fill(el.numbers, numberLines(data));
    el.capB.textContent = `${um(s.window.range_um)} (D${s.window.band}) · window`;
    el.visit.replaceChildren(
      new Option("All visits added", "all"),
      ...data.visits.map((v, i) => new Option(`Visit ${i + 1}: ${v.date}`, String(i))),
    );
    el.play.disabled = data.visits.length < 2;
    const others = data.other_glows.map((o, i) => `${i + 1}: ${o.excess_is_lower_limit ? "at least " : ""}${o.excess}×, ` +
      `${o.sigma}σ at RA ${o.ra.toFixed(5)}° Dec ${o.dec.toFixed(5)}°` +
      (o.gaia.length ? ` · Gaia DR3 ${o.gaia.map((g) => `${g.source_id} (G ${g.g_mag})`).join(", ")}` : " · no Gaia DR3 star there"));
    fill(el.others.querySelector("ul"), others.length ? others : ["None above the glow rule in this field."]);
    fill(el.warnings.querySelector("ul"), data.notes);
    fill(el.downloads, downloadLines(data));
    el.method.textContent = `How: ${data.method}. Made ${data.made_at} by ${data.made_by}.`;
    visit = null;
    drawVisit();
  }

  async function show(loaded, { prepare = false } = {}) {
    const v = ++version;
    stopTimers();
    if (!loaded) return hide();
    let answer;
    try {
      answer = await loadMethane(loaded, { prepare });
    } catch (err) {
      if (v === version) hide(String(err.message));
      return;
    }
    if (v !== version) return;
    if (answer.status === "working") {
      hide(answer.message);
      pollTimer = setTimeout(() => { if (v === version) show(loaded); }, POLL_MS);
      return;
    }
    if (answer.status === "none") {
      current = { loaded };
      return hide(answer.canPrepare
        ? `${answer.message} It downloads the SPHEREx images at 3.15–3.50 µm and 3.90–4.20 µm from NASA IRSA (a few minutes).`
        : answer.message, answer.canPrepare);
    }
    current = { data: answer.data, base: answer.base, loaded };
    render();
  }

  el.prepare.addEventListener("click", () => current && current.loaded && show(current.loaded, { prepare: true }));
  el.visit.addEventListener("change", () => {
    visit = el.visit.value === "all" ? null : Number(el.visit.value);
    drawVisit();
  });
  el.play.addEventListener("click", () => {
    if (playTimer) {
      clearInterval(playTimer);
      playTimer = null;
      el.play.textContent = "Play visits";
      return;
    }
    el.play.textContent = "Pause";
    playTimer = setInterval(() => {
      visit = visit === null ? 0 : (visit + 1) % current.data.visits.length;
      drawVisit();
    }, PLAY_MS);
  });
  el.blink.addEventListener("click", () => {
    if (blinkTimer) {
      clearInterval(blinkTimer);
      blinkTimer = null;
      showingWindow = false;
      el.blink.textContent = "Blink 3.3 ↔ 4 µm";
      drawVisit();
      return;
    }
    el.blink.textContent = "Stop blinking";
    blinkTimer = setInterval(() => {
      showingWindow = !showingWindow;
      drawVisit();
    }, BLINK_MS);
  });

  hide();
  return { show };
}
