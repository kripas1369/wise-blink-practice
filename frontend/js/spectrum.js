// Spectrum panel: the target's brightness against wavelength, one colour per visit, across every detector
// that has frames (spectrum.json, made by backend/app/spectrum.py). Every point is one exposure of a light curve.
import { loadExtra } from "./frames.js";
import { VISIT_COLOURS, chart, offChart, pointTitle, ticks } from "./lightcurve.js";

const $ = (id) => document.getElementById(id);
const isHollow = (p) => p.n_flagged > 0 || p.flux_mjy < 5 * p.err_mjy;
const range = (r) => `${r[0].toFixed(2)}–${r[1].toFixed(2)} µm`;

/** The spectrum file sits in the target's folder, one level above the detector folder. */
export const targetBase = (base) => base.replace(/\/d[1-6]$/, "");

export function spectrumChart(spec) {
  const ranges = spec.detectors.map((d) => d.band_range_um);
  const lo = Math.min(...ranges.map((r) => r[0]));
  const hi = Math.max(...ranges.map((r) => r[1]));
  const points = spec.visits.flatMap((v) => v.points.map((p) => ({
    ...p, x: p.wl_um, colour: VISIT_COLOURS[v.visit % VISIT_COLOURS.length], hollow: isHollow(p),
    title: `D${p.band} · ${pointTitle(p, v.visit + 1)}`,
  })));
  const key = (p) => `${p.band}:${p.obs_id}`;
  const off = new Set(offChart(points).map(key));
  // One line per visit and detector: the detectors do not overlap, so a line across a boundary would invent values.
  const lines = spec.visits.flatMap((v) => v.bands.map((band) => ({
    colour: VISIT_COLOURS[v.visit % VISIT_COLOURS.length],
    points: v.points.filter((p) => p.band === band && !off.has(key(p)))
      .sort((a, b) => a.wl_um - b.wl_um).map((p) => ({ x: p.wl_um, y: p.flux_mjy })),
  }))).filter((l) => l.points.length > 1);
  return chart({
    points,
    xRange: [lo, hi],
    xTicks: ticks(lo, hi, 8).map((v) => ({ value: v, label: v.toFixed(1) })),
    xLabel: "wavelength at the position (µm)",
    lines,
    vlines: [...spec.detectors].sort((a, b) => a.band - b.band)
      .map((d) => ({ x: d.band_range_um[0], label: `D${d.band}` })),
  });
}

/** One line per detector: how many exposures it adds, or why it adds none. */
export function detectorLines(spec) {
  return [...spec.detectors].sort((a, b) => a.band - b.band).map((d) => {
    if (d.method === "none") return `D${d.band} (${range(d.band_range_um)}): no points. ${d.reason}`;
    const psf = d.psf_fwhm ? ` · PSF ${d.psf_fwhm.median_arcsec}″ wide (FWHM, from the headers)` : "";
    return `D${d.band} (${range(d.band_range_um)}): ${d.n_measured} of ${d.n_exposures} exposures measured${psf}`;
  });
}

export function spectrumSummary(spec) {
  const n = spec.visits.reduce((s, v) => s + v.n_points, 0);
  const bands = spec.detectors.filter((d) => d.method !== "none").map((d) => `D${d.band}`).join(", ");
  return `${spec.label} · ${bands || "no detector"} · ${spec.visits.length} visit${spec.visits.length === 1 ? "" : "s"} · ${n} points`;
}

export function createSpectrum() {
  const el = {
    box: $("spec-view"), message: $("spec-message"), body: $("spec-body"), summary: $("spec-summary"),
    chart: $("spec-chart"), legend: $("spec-legend"), detectors: $("spec-detectors"),
    warnings: $("spec-warnings"), method: $("spec-method"),
  };
  let version = 0;

  function fill(box, lines) {
    box.querySelector("ul").replaceChildren(...lines.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }));
    box.hidden = lines.length === 0;
  }

  function hide(message = "") {
    el.box.hidden = !message;
    el.body.hidden = true;
    el.message.hidden = !message;
    el.message.textContent = message;
  }

  /** Spectrum for frames that were just shown ({ manifest, base }), or hide (null). */
  async function show(frames) {
    const v = ++version;
    if (!frames) return hide();
    let spec;
    try {
      spec = await loadExtra(targetBase(frames.base), "spectrum.json");
    } catch (err) {
      if (v === version) hide(`Could not load the spectrum: ${err.message}`);
      return;
    }
    if (v !== version) return;
    if (!spec) return hide(`No spectrum for ${frames.manifest.label} yet: it needs light curves from the detectors.`);
    el.box.hidden = false;
    el.message.hidden = true;
    el.body.hidden = false;
    el.summary.textContent = spectrumSummary(spec);
    el.chart.innerHTML = spec.visits.length ? spectrumChart(spec) : "";
    el.legend.replaceChildren(...spec.visits.map((vis) => {
      const item = document.createElement("span");
      item.className = "lc-key";
      item.style.setProperty("--key", VISIT_COLOURS[vis.visit % VISIT_COLOURS.length]);
      item.textContent = `visit ${vis.visit + 1}: ${vis.date} (D${vis.bands.join(", D")})`;
      return item;
    }));
    fill(el.detectors, detectorLines(spec));
    fill(el.warnings, spec.warnings);
    el.method.textContent = `How: ${spec.method}; visits: ${spec.visit_rule}.`;
  }

  hide();
  return { show };
}
