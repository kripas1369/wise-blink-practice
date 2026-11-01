// Coverage timeline: when SPHEREx looked at the position, one row per detector, from /api/coverage (or the
// prepared frames/<target>/coverage.json, made by backend/app/coverage.py). Each tick is one image; each bar
// is one visit, grouped per detector with the same rule as backend/app/archive.group_epochs, so a row's bars
// are the visits the flipbook can show for that detector.
import { hasApi, loadExtra, remember, FRAMES_ROOT } from "./frames.js";
import { DETECTORS } from "./urlstate.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

export const EPOCH_GAP_DAYS = 30;
export const EPOCH_MAX_SPAN_DAYS = 60;
const MJD_UNIX_EPOCH = 40587;
const SVG_W = 640;
const ROW_H = 26;
const PAD = { left: 44, right: 12, top: 22, bottom: 30 };

export const mjdToDate = (mjd) => new Date((mjd - MJD_UNIX_EPOCH) * 86400000);
const isoDay = (mjd) => mjdToDate(mjd).toISOString().slice(0, 10);

/** Visits of one detector's images (sorted or not): [{ mjd_min, mjd_max, n }]. */
export function groupVisits(mjds, gap = EPOCH_GAP_DAYS, maxSpan = EPOCH_MAX_SPAN_DAYS) {
  const visits = [];
  for (const t of [...mjds].sort((a, b) => a - b)) {
    const last = visits[visits.length - 1];
    if (!last || t - last.mjd_max > gap || t - last.mjd_min > maxSpan) visits.push({ mjd_min: t, mjd_max: t, n: 0 });
    const v = visits[visits.length - 1];
    v.mjd_max = t;
    v.n += 1;
  }
  return visits;
}

/** First day of every month (or every 3 months for long spans) between two MJDs. */
export function monthTicks(m0, m1) {
  const start = mjdToDate(m0);
  const months = (m1 - m0) / 30.4;
  const step = months > 15 ? 3 : months > 7 ? 2 : 1;
  const out = [];
  const d = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1));
  while (d.getUTCMonth() % step) d.setUTCMonth(d.getUTCMonth() + 1);
  for (; d.getTime() / 86400000 + MJD_UNIX_EPOCH <= m1; d.setUTCMonth(d.getUTCMonth() + step)) {
    out.push({ mjd: d.getTime() / 86400000 + MJD_UNIX_EPOCH, label: d.toISOString().slice(0, 7) });
  }
  return out;
}

/** Rows D1–D6: { band, mjds, visits }. */
export function coverageRows(coverage) {
  return Object.keys(DETECTORS).map(Number).map((band) => {
    const mjds = coverage.images.filter((im) => im.band === band).map((im) => im.mjd);
    return { band, mjds, visits: groupVisits(mjds) };
  });
}

/** The SVG: ticks per image, a bar per visit, ▼ at the flipbook's frames in the current detector's row. */
export function timelineChart(coverage, { det = null, frameMjds = [] } = {}) {
  const rows = coverageRows(coverage);
  const all = coverage.images.map((im) => im.mjd);
  const pad = Math.max(5, (Math.max(...all) - Math.min(...all)) * 0.03);
  const m0 = Math.min(...all) - pad;
  const m1 = Math.max(...all) + pad;
  const h = PAD.top + rows.length * ROW_H + PAD.bottom;
  const sx = (m) => PAD.left + ((m - m0) / (m1 - m0)) * (SVG_W - PAD.left - PAD.right);
  const rowY = (i) => PAD.top + i * ROW_H;
  const parts = [];
  for (const t of monthTicks(m0, m1)) {
    parts.push(`<line x1="${sx(t.mjd)}" x2="${sx(t.mjd)}" y1="${PAD.top}" y2="${h - PAD.bottom}" class="lc-grid"/>`,
      `<text x="${sx(t.mjd)}" y="${h - PAD.bottom + 16}" class="lc-tick" text-anchor="middle">${t.label}</text>`);
  }
  rows.forEach((row, i) => {
    const y = rowY(i);
    const current = row.band === det;
    parts.push(`<g class="tl-row${current ? " tl-current" : ""}" data-band="${row.band}" role="button" tabindex="0" ` +
      `aria-label="Show detector D${row.band}">` +
      `<title>D${row.band} (${DETECTORS[row.band]}): ${row.mjds.length} images in ${row.visits.length} visits. Click to show this detector.</title>` +
      `<rect x="0" y="${y}" width="${SVG_W}" height="${ROW_H}" class="tl-hit"/>` +
      `<text x="${PAD.left - 8}" y="${y + ROW_H / 2 + 4}" class="lc-tick tl-label" text-anchor="end">D${row.band}</text>`);
    for (const v of row.visits) {
      const x0 = sx(v.mjd_min) - 2;
      const w = Math.max(4, sx(v.mjd_max) - sx(v.mjd_min) + 4);
      parts.push(`<rect x="${x0}" y="${y + 5}" width="${w}" height="${ROW_H - 10}" rx="3" class="tl-visit">` +
        `<title>D${row.band}: ${v.n} images, ${isoDay(v.mjd_min)} to ${isoDay(v.mjd_max)}</title></rect>`);
    }
    parts.push(row.mjds.map((m) => `<line x1="${sx(m).toFixed(1)}" x2="${sx(m).toFixed(1)}" y1="${y + 7}" ` +
      `y2="${y + ROW_H - 7}" class="tl-image"/>`).join(""), "</g>");
    if (current) {
      for (const m of frameMjds) {
        const x = sx(m);
        parts.push(`<path d="M${x - 5},${y - 1}L${x + 5},${y - 1}L${x},${y + 6}Z" class="tl-frame">` +
          `<title>Shown in the flipbook: ${isoDay(m)}</title></path>`);
      }
    }
  });
  return `<svg viewBox="0 0 ${SVG_W} ${h}" class="lc-svg tl-svg" role="img" ` +
    `aria-label="SPHEREx images of this position over time, per detector">${parts.join("")}</svg>`;
}

/** One sentence for the whole position, and one for the flipbook's detector. */
export function timelineSummary(coverage, det = null, nFrames = null) {
  const s = coverage.summary;
  if (!s.n_images) return ["SPHEREx has no images of this position yet."];
  const releases = Object.entries(s.per_collection || {}).map(([c, n]) => `${c.replace("spherex_", "")} ${n}`).join(", ");
  const out = [`${s.n_images} images (${s.n_exposures} exposures) from ${s.first} to ${s.last}` +
    `${releases ? ` · releases: ${releases}` : ""} · newest image released ${String(s.latest_release).slice(0, 10)} · ` +
    `IRSA asked ${coverage.asked_at}.`];
  if (det !== null) {
    const row = coverageRows(coverage).find((r) => r.band === det);
    let line = `D${det}: ${row.mjds.length} images in ${row.visits.length} visit${row.visits.length === 1 ? "" : "s"}`;
    if (nFrames !== null) {
      line += nFrames === row.visits.length
        ? `; the flipbook shows all ${nFrames}.`
        : `; the flipbook shows ${nFrames} (a visit is left out when none of its images covers enough of the square, ` +
          `and visits released after the frames were made are not in them yet).`;
    } else {
      line += ".";
    }
    out.push(line);
  }
  return out;
}

async function loadCoverage(where, fetchFn = fetch) {
  if (await hasApi(fetchFn)) {
    const params = new URLSearchParams({ ra: where.ra.toFixed(6), dec: where.dec.toFixed(6) });
    const url = `/api/coverage?${params}`;
    return remember(fetchFn, `coverage:${url}`, async () => {
      let resp;
      try {
        resp = await fetchFn(url, { cache: "no-cache" });
      } catch {
        throw new Error("Could not reach the data API");
      }
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(body.error || `The data API answered HTTP ${resp.status}`);
      return body;
    });
  }
  if (!where.targetKey) throw new Error("The timeline for any position needs the data API; this server only has the 5 prepared targets.");
  const prepared = await loadExtra(`${FRAMES_ROOT}/${where.targetKey}`, "coverage.json", fetchFn);
  if (!prepared) throw new Error("No coverage file was prepared for this target.");
  return prepared;
}

export function createTimeline({ onDetector = () => {} } = {}) {
  const el = { box: $("tl-view"), message: $("tl-message"), body: $("tl-body"), chart: $("tl-chart"), summary: $("tl-summary") };
  let version = 0;
  let coverage = null;
  let coverageKey = "";
  let det = null;
  let frameMjds = [];

  function draw() {
    if (!coverage) return;
    el.chart.innerHTML = coverage.images.length ? timelineChart(coverage, { det, frameMjds }) : "";
    el.summary.replaceChildren(...timelineSummary(coverage, det, frameMjds.length ? frameMjds.length : null).map((t) => {
      const p = document.createElement("p");
      p.className = "help";
      p.textContent = t;
      return p;
    }));
  }

  function message(text) {
    el.box.hidden = false;
    el.body.hidden = true;
    el.message.hidden = false;
    el.message.textContent = text;
  }

  /** A new position or detector ({ ra, dec, det, targetKey }). */
  async function show(where) {
    det = where.det;
    frameMjds = [];
    const key = `${where.ra.toFixed(5)},${where.dec.toFixed(5)}`;
    if (key === coverageKey && coverage) return draw();
    const v = ++version;
    coverage = null;
    coverageKey = key;
    message("Asking NASA IRSA when SPHEREx looked here…");
    try {
      const answer = await loadCoverage(where);
      if (v !== version) return;
      coverage = answer;
    } catch (err) {
      if (v === version) { coverageKey = ""; message(String(err.message)); }
      return;
    }
    el.message.hidden = true;
    el.body.hidden = false;
    draw();
  }

  /** The flipbook loaded frames: mark their dates. */
  function markFrames(loaded) {
    frameMjds = loaded ? loaded.manifest.frames.map((f) => f.mjd) : [];
    draw();
  }

  el.chart.addEventListener("click", (e) => {
    const row = e.target.closest("[data-band]");
    if (row) onDetector(Number(row.dataset.band));
  });
  el.chart.addEventListener("keydown", (e) => {
    const row = e.target.closest("[data-band]");
    if (row && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onDetector(Number(row.dataset.band)); }
  });
  return { show, markFrames };
}
