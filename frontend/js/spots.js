// Spot evidence for the Before / After / Difference view (spots.json, made by backend/app/spots.py) and
// the known-object check (/api/known-objects, NASA JPL). A spot is never called a new object.
import { formatDec, formatRa } from "./coords.js";
import { framesQuery, hasApi, loadExtra } from "./frames.js";
import { percentAt } from "./sky.js";

const $ = (id) => document.getElementById(id);

/** One line of the spot list. */
export function spotLine(spot, index) {
  const sign = spot.sign > 0 ? "brighter in B" : "fainter in B";
  const parts = [`${index + 1}`, `${spot.peak_sigma > 0 ? "+" : ""}${spot.peak_sigma}σ ${sign}`, `${spot.n_pixels} px`];
  const g = spot.gaia_star;
  if (g && g.distance_px <= 1.5) {
    parts.push(`Gaia ${g.g_mag === null ? "star" : `G ${g.g_mag}`} at ${g.distance_px} px${g.target ? " (target)" : ""}`);
  } else {
    parts.push("no Gaia star within 1.5 px");
  }
  if (spot.artifact_flags.length) parts.push(`possible artifact: ${spot.artifact_flags.join(", ")}`);
  return parts.join(" · ");
}

function objectText(o) {
  return `${o.name} at ${o.distance_arcsec}″` + (o.v_mag === null ? "" : ` (V ${o.v_mag})`) +
    (o.est_error_arcsec && o.est_error_arcsec[0] !== null ? `, JPL's position error ${o.est_error_arcsec[0]}″` : "");
}

/** { headline, lines } for a known-object answer. */
export function knownText(r) {
  if (r.outcome === "unavailable") return { headline: "Check unavailable", lines: [`${r.reason}.`] };
  const lines = [`JPL ${r.pass_used}, asked ${r.asked_at}; match = ${r.match_rule}, ${r.match_radius_arcsec}″.`];
  if (r.outcome === "match") {
    lines.unshift(`Known: ${r.matches.map(objectText).join("; ")}.`);
    return { headline: `Matches known object ${r.matches[0].name}`, lines: [...lines, ...r.notes] };
  }
  lines.unshift(`${r.n_in_box} known object${r.n_in_box === 1 ? "" : "s"} in the ${r.search_half_deg * 120}′ box` +
    (r.nearby.length ? `, nearest ${objectText(r.nearby[0])}.` : "."));
  lines.push("No match does not make the spot a new object: most spots come from stars, artifacts or noise.");
  return { headline: "No known object within the match radius", lines: [...lines, ...r.notes] };
}

export function createSpotList({ onPick }) {
  const el = {
    box: $("spot-view"), count: $("spot-count"), list: $("spot-list"), detail: $("spot-detail"),
    title: $("spot-detail-title"), why: $("spot-why"), alt: $("spot-else"), confirm: $("spot-confirm"),
    jpl: $("spot-jpl"), result: $("spot-jpl-result"), marks: $("diff-marks-d"),
  };
  let current = null; // { loaded, a, b, pair, index }
  let version = 0;
  let spotsFor = { base: null, data: null };

  function fill(ul, lines) {
    ul.replaceChildren(...lines.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }));
  }

  function mark(spot, i) {
    const size = current.loaded.manifest.size_px;
    const box = document.createElement("span");
    box.className = "spot-mark";
    const { left, top } = percentAt(spot.xy, size);
    Object.assign(box.style, { left: `${left}%`, top: `${top}%`, width: `${(100 / size) * 1.8}%` });
    box.dataset.label = String(i + 1);
    el.marks.append(box);
  }

  function select(index) {
    current.index = index;
    const spot = current.pair.spots[index];
    for (const [i, li] of [...el.list.children].entries()) li.querySelector("button").setAttribute("aria-pressed", String(i === index));
    el.detail.hidden = false;
    el.title.textContent = `Spot ${index + 1} · RA ${formatRa(spot.ra)} Dec ${formatDec(spot.dec)} · ` +
      `visit ${spot.sign > 0 ? "B" : "A"} (${current.loaded.manifest.frames.find((f) => f.epoch_id === spot.frame).date_iso})`;
    el.why.textContent = spot.why;
    fill(el.alt, spot.what_else);
    fill(el.confirm, spot.confirm);
    el.result.replaceChildren();
    el.jpl.disabled = false;
    onPick(spot.peak_xy);
  }

  async function askJpl() {
    if (!current || current.index === null) return;
    const v = ++version;
    const { loaded, a, b, index } = current;
    if (!(await hasApi())) {
      el.result.textContent = "The known-object check needs the data API (uvicorn backend.app.main:app).";
      return;
    }
    el.jpl.disabled = true;
    el.result.textContent = "Asking NASA JPL… this can take one to several minutes (JPL was slow and unreliable on 31 Oct 2026).";
    const url = framesQuery(loaded.where).replace("/api/frames?", "/api/known-objects?") + `&a=${a}&b=${b}&spot=${index}`;
    let body;
    let resp;
    try {
      resp = await fetch(url, { cache: "no-cache" });
      body = await resp.json();
    } catch {
      if (v === version) { el.result.textContent = "Could not reach the data API."; el.jpl.disabled = false; }
      return;
    }
    if (v !== version) return;
    el.jpl.disabled = false;
    if (!resp.ok) {
      el.result.textContent = body.error || `The data API answered HTTP ${resp.status}`;
      return;
    }
    const { headline, lines } = knownText(body);
    const strong = document.createElement("p");
    strong.className = "proof-verdict";
    strong.textContent = headline;
    const ul = document.createElement("ul");
    fill(ul, lines);
    el.result.replaceChildren(strong, ul);
  }

  /** Called by the difference view after it draws a pair (loaded = { manifest, base, where }). */
  async function show(loaded, a, b) {
    const v = ++version;
    current = null;
    el.detail.hidden = true;
    if (!loaded) { el.box.hidden = true; return; }
    if (spotsFor.base !== loaded.base) {
      let data = null;
      try {
        data = await loadExtra(loaded.base, "spots.json");
      } catch {
        data = null;
      }
      if (v !== version) return;
      spotsFor = { base: loaded.base, data };
    }
    const data = spotsFor.data;
    const pair = data && data.pairs.find((p) => p.a === a && p.b === b);
    if (!pair) {
      el.box.hidden = false;
      el.count.textContent = "";
      el.list.replaceChildren();
      el.detail.hidden = true;
      el.list.textContent = "No spot list was made for these frames yet.";
      return;
    }
    current = { loaded, a, b, pair, index: null };
    el.box.hidden = false;
    el.count.textContent = pair.n_spots > pair.spots.length
      ? `${pair.spots.length} strongest of ${pair.n_spots}` : `${pair.n_spots} found`;
    el.list.replaceChildren(...pair.spots.map((s, i) => {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "spot-item";
      button.setAttribute("aria-pressed", "false");
      button.textContent = spotLine(s, i);
      button.addEventListener("click", () => select(i));
      li.append(button);
      return li;
    }));
    if (!pair.spots.length) el.list.textContent = "No pixel group reaches 5σ in this difference.";
    pair.spots.forEach(mark);
  }

  el.jpl.addEventListener("click", askJpl);
  return { show };
}
