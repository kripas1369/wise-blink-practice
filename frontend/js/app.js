import { formatDec, formatRa, looksLikeName, parseCoordinates } from "./coords.js";
import { createDiffView } from "./diffview.js";
import { createFlipbook } from "./flipbook.js";
import { createLightCurve } from "./lightcurve.js";
import { positionAt, separationArcsec, VIEW_EPOCH } from "./motion.js";
import { NameNotFound, resolveName } from "./resolve.js";
import { TARGETS } from "./targets.js";
import { buildUrlState, DETECTORS, readUrlState } from "./urlstate.js";

// Aladin Lite from two CDNs: the CDS server was unreachable on 31 Oct 2026, jsDelivr worked.
const ALADIN_SCRIPTS = [
  "https://cdn.jsdelivr.net/npm/aladin-lite@3.8.2/dist/aladin.js",
  "https://unpkg.com/aladin-lite@3.8.2/dist/aladin.js",
];

// Background images: ESA ESASky copies of the CDS surveys. They send CORS headers, which the
// WebGL map needs; the IRSA copies do not, and the CDS servers were unreachable on 31 Oct 2026.
const SURVEYS = [
  { id: "2mass", name: "2MASS near-infrared (J, H, K)", url: "https://skies.esac.esa.int/2MASSColor" },
  { id: "allwise", name: "AllWISE mid-infrared (W1, W2, W4)", url: "https://skies.esac.esa.int/AllWISEColor" },
  { id: "dss2", name: "DSS2 visible light", url: "https://skies.esac.esa.int/DSSColor" },
];

const $ = (id) => document.getElementById(id);
const form = $("search-form");
const query = $("query");
const goButton = $("go");
const fovInput = $("fov");
const fovValue = $("fov-value");
const detSelect = $("det");
const surveySelect = $("survey");
const statusBox = $("status");
const selectionBox = $("selection");
const targetsBox = $("targets");
const mapMessage = $("map-message");

const state = { ra: null, dec: null, fov: 3, det: 2, source: "", note: "", targetKey: null };
let A = null;
let aladin = null;
let fovOverlay = null;
// Bumped on every new position, so a slow SIMBAD answer cannot overwrite a newer choice.
let positionVersion = 0;
let flipbook = null;

function setStatus(message, kind = "info") {
  statusBox.textContent = message;
  statusBox.className = `status ${message ? kind : ""}`;
}

// The background maps are older than SPHEREx (2MASS 1997–2001, AllWISE 2010–2011, DSS2 older
// still), so fast stars sit away from today's position on them.
function oldMapWarning(movedSince2000Arcsec) {
  if (movedSince2000Arcsec < 5) return "";
  return ` The background maps are older than SPHEREx, so on 2MASS the star sits about ` +
    `${(movedSince2000Arcsec / 60).toFixed(1)}′ from the square (less on AllWISE).`;
}

function targetPosition(target) {
  return positionAt(target.ra, target.dec, target.pmra, target.pmdec, 2000.0, VIEW_EPOCH);
}

/** The official target within 5″ of a position, so a typed or shared position still gets its frames. */
function officialTargetAt(ra, dec) {
  return TARGETS.find((t) => {
    const p = targetPosition(t);
    return separationArcsec(p.ra, p.dec, ra, dec) < 5;
  }) || null;
}

function refreshFlipbook() {
  if (!flipbook || state.ra === null) return;
  const target = TARGETS.find((t) => t.key === state.targetKey);
  flipbook.show({
    targetKey: state.targetKey, label: target ? target.label : "", ra: state.ra, dec: state.dec, det: state.det, fov: state.fov,
  });
}

function setDetector(det) {
  state.det = det;
  detSelect.value = String(det);
  writeUrl();
  renderSelection();
  refreshFlipbook();
}

// ---------- rendering ----------

function renderDetectors() {
  detSelect.innerHTML = Object.entries(DETECTORS)
    .map(([n, range]) => `<option value="${n}">D${n} · ${range}</option>`)
    .join("");
}

function renderSurveys() {
  surveySelect.innerHTML = SURVEYS.map((s) => `<option value="${s.id}">${s.name}</option>`).join("");
}

function renderTargets() {
  targetsBox.innerHTML = "";
  for (const target of TARGETS) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "target";
    button.setAttribute("aria-pressed", "false");
    button.dataset.key = target.key;
    button.innerHTML = `
      <span class="target-kind">${target.kind}</span>
      <span class="target-name">${target.label}</span>
      <span class="target-hint">${target.lookFor}</span>`;
    button.addEventListener("click", () => chooseTarget(target));
    item.appendChild(button);
    targetsBox.appendChild(item);
  }
}

function renderSelection() {
  for (const button of targetsBox.querySelectorAll(".target")) {
    button.setAttribute("aria-pressed", String(button.dataset.key === state.targetKey));
  }
  if (state.ra === null) return;
  selectionBox.innerHTML = `
    <dl>
      <dt>RA</dt><dd>${formatRa(state.ra)} · ${state.ra.toFixed(6)}°</dd>
      <dt>Dec</dt><dd>${formatDec(state.dec)} · ${state.dec.toFixed(6)}°</dd>
      <dt>View</dt><dd>${state.fov}′ square · D${state.det} (${DETECTORS[state.det]})</dd>
      <dt>From</dt><dd></dd>
    </dl>
    <p class="note"></p>
    <div class="share-row">
      <button type="button" class="btn btn-small" id="copy-link">Copy share link</button>
      <span class="help" id="copy-result" aria-live="polite"></span>
    </div>`;
  // Text from users or SIMBAD goes in with textContent, never as HTML.
  selectionBox.querySelector("dd:last-of-type").textContent = state.source;
  selectionBox.querySelector(".note").textContent = state.note;
  $("copy-link").addEventListener("click", copyLink);
}

// ---------- state changes ----------

function writeUrl() {
  if (state.ra === null) return;
  history.replaceState(null, "", buildUrlState(state));
}

function viewFovDegrees() {
  return Math.max(state.fov * 3, 6) / 60;
}

function drawFovBox() {
  if (!aladin || state.ra === null) return;
  const half = state.fov / 60 / 2;
  const cosDec = Math.max(Math.cos((state.dec * Math.PI) / 180), 1e-6);
  const dRa = half / cosDec;
  const { ra, dec } = state;
  fovOverlay.removeAll();
  fovOverlay.add(A.polygon([
    [ra - dRa, dec - half], [ra + dRa, dec - half], [ra + dRa, dec + half], [ra - dRa, dec + half],
  ]));
}

function moveMap() {
  if (!aladin || state.ra === null) return;
  aladin.gotoRaDec(state.ra, state.dec);
  aladin.setFoV(viewFovDegrees());
  drawFovBox();
}

function applyPosition({ ra, dec, source, note = "", targetKey = null, queryText = null }) {
  positionVersion += 1;
  if (targetKey === null) targetKey = officialTargetAt(ra, dec)?.key ?? null;
  Object.assign(state, { ra, dec, source, note, targetKey });
  if (queryText !== null) query.value = queryText;
  writeUrl();
  renderSelection();
  moveMap();
  refreshFlipbook();
}

function chooseTarget(target) {
  const { ra, dec } = targetPosition(target);
  state.det = target.detector;
  detSelect.value = String(target.detector);
  const moved = separationArcsec(target.ra, target.dec, ra, dec);
  applyPosition({
    ra, dec,
    source: `Official target: ${target.label}`,
    note: `SIMBAD J2000 position moved to ${VIEW_EPOCH.toFixed(1)} with its proper motion (${moved.toFixed(1)}″). ` +
      `Detector D${target.detector} suggested. ${target.lookFor}${oldMapWarning(moved)}`,
    targetKey: target.key,
    queryText: target.label,
  });
  setStatus(`Showing ${target.label}.`, "ok");
}

async function search(text) {
  const clean = text.trim();
  const known = TARGETS.find((t) => t.label.toLowerCase() === clean.toLowerCase());
  if (known) return chooseTarget(known);

  try {
    const { ra, dec } = parseCoordinates(clean);
    applyPosition({ ra, dec, source: "Typed position", note: "Used exactly as typed (no motion correction)." });
    setStatus("Position set.", "ok");
    return;
  } catch (parseError) {
    if (!looksLikeName(clean)) {
      setStatus(parseError.message, "error");
      return;
    }
  }

  setStatus(`Looking up "${clean}" in SIMBAD…`, "info");
  goButton.disabled = true;
  const versionAtStart = positionVersion;
  try {
    const star = await resolveName(clean);
    if (positionVersion !== versionAtStart) {
      setStatus(`Found ${star.simbadId}, but you chose another position meanwhile, so it was not used.`, "warn");
      return;
    }
    let { ra, dec } = star;
    let note = `SIMBAD (${star.server}) J2000 position. No proper motion in SIMBAD, so not moved.`;
    if (star.pmra !== null && star.pmdec !== null) {
      ({ ra, dec } = positionAt(star.ra, star.dec, star.pmra, star.pmdec, star.epoch, VIEW_EPOCH));
      const moved = separationArcsec(star.ra, star.dec, ra, dec);
      note = `SIMBAD (${star.server}) J2000 position moved to ${VIEW_EPOCH.toFixed(1)} with its proper motion (${moved.toFixed(1)}″).${oldMapWarning(moved)}`;
    }
    applyPosition({ ra, dec, source: `SIMBAD: ${star.simbadId}`, note, queryText: clean });
    setStatus(`Found ${star.simbadId}.`, "ok");
  } catch (err) {
    setStatus(err.message, err instanceof NameNotFound ? "warn" : "error");
  } finally {
    goButton.disabled = false;
  }
}

async function copyLink() {
  const result = $("copy-result");
  try {
    await navigator.clipboard.writeText(location.href);
    result.textContent = "Link copied.";
  } catch {
    result.textContent = location.href;
  }
}

// ---------- sky map ----------

// The npm build of Aladin Lite 3.8 is an ES module (export default), not a global script.
async function loadAladin() {
  for (const src of ALADIN_SCRIPTS) {
    try {
      return (await import(src)).default;
    } catch {
      // try the next CDN
    }
  }
  return null;
}

async function startMap() {
  A = await loadAladin();
  if (!A) {
    mapMessage.textContent = "The sky map could not load (Aladin Lite is unreachable). Search, targets and share links still work.";
    return;
  }
  try {
    await A.init;
  } catch (err) {
    mapMessage.textContent = `The sky map could not start (${err}). Search, targets and share links still work.`;
    return;
  }
  mapMessage.remove();
  const first = state.ra !== null ? state : targetPosition(TARGETS[0]);
  aladin = A.aladin("#aladin", {
    survey: SURVEYS[0].url,
    target: `${first.ra} ${first.dec}`,
    fov: state.ra !== null ? viewFovDegrees() : 0.5,
    cooFrame: "ICRS",
    showReticle: true,
    showZoomControl: true,
    showFullscreenControl: true,
    showLayersControl: false,
    showGotoControl: false,
    showProjectionControl: false,
    showSimbadPointerControl: false,
    showShareControl: false,
    showCooGrid: false,
    showFrame: true,
  });
  fovOverlay = A.graphicOverlay({ color: "#ffc04d", lineWidth: 2 });
  aladin.addOverlay(fovOverlay);
  // Aladin sometimes reports the end of a pan as a click; only a still press picks a position.
  const mapBox = $("aladin");
  let pressedAt = null;
  let wasDrag = false;
  mapBox.addEventListener("pointerdown", (e) => { pressedAt = [e.clientX, e.clientY]; wasDrag = false; }, true);
  mapBox.addEventListener("pointerup", (e) => {
    wasDrag = pressedAt !== null && Math.hypot(e.clientX - pressedAt[0], e.clientY - pressedAt[1]) > 5;
    pressedAt = null;
  }, true);
  aladin.on("click", (event) => {
    if (event.isDragging || wasDrag) return;
    applyPosition({
      ra: event.ra,
      dec: event.dec,
      source: "Clicked on the sky map",
      note: "Position picked on the map.",
      queryText: `${event.ra.toFixed(5)} ${event.dec.toFixed(5)}`,
    });
    setStatus("Position set from the map.", "ok");
  });
  drawFovBox();
}

function changeSurvey() {
  const survey = SURVEYS.find((s) => s.id === surveySelect.value);
  if (!aladin || !survey) return;
  aladin.setBaseImageLayer(A.imageHiPS(survey.url, { name: survey.name }));
}

// ---------- start ----------

function start() {
  renderDetectors();
  renderSurveys();
  renderTargets();

  const fromUrl = readUrlState(location.search);
  state.fov = fromUrl.fov;
  state.det = fromUrl.det;
  fovInput.value = String(state.fov);
  fovValue.textContent = String(state.fov);
  detSelect.value = String(state.det);
  if (fromUrl.problems.length) setStatus(fromUrl.problems.join(" "), "warn");
  const diffView = createDiffView();
  const lightCurve = createLightCurve();
  flipbook = createFlipbook({
    onDetector: setDetector,
    onFrames: (loaded) => { diffView.show(loaded); lightCurve.show(loaded); },
    onPixel: (p) => lightCurve.showPixel(p),
  });
  if (fromUrl.ra !== null) {
    const target = officialTargetAt(fromUrl.ra, fromUrl.dec);
    applyPosition({
      ra: fromUrl.ra,
      dec: fromUrl.dec,
      source: target ? `Official target: ${target.label}` : "Shared link",
      note: "Position from the link.",
      targetKey: target ? target.key : null,
      queryText: target ? target.label : `${fromUrl.ra.toFixed(5)} ${fromUrl.dec.toFixed(5)}`,
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    search(query.value);
  });
  fovInput.addEventListener("input", () => {
    fovValue.textContent = fovInput.value;
  });
  fovInput.addEventListener("change", () => {
    state.fov = Number(fovInput.value);
    writeUrl();
    renderSelection();
    moveMap();
    refreshFlipbook();
  });
  detSelect.addEventListener("change", () => setDetector(Number(detSelect.value)));
  surveySelect.addEventListener("change", changeSurvey);

  startMap();
}

start();
