import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";

import { scaleText } from "../js/flipbook.js";
import { checkManifest } from "../js/frames.js";
import {
  circleTravelPx, comparisonLines, offChart, lightCurveWarnings, pointTitle, ticks, timeChart, wavelengthChart, wavelengthColour, yRange,
} from "../js/lightcurve.js";

const FRAMES = new URL("../frames/", import.meta.url);
const readJson = (url) => JSON.parse(readFileSync(url, "utf8"));
const load = (t, b, name) => readJson(new URL(`${t}/d${b}/${name}`, FRAMES));
const folders = () => readdirSync(FRAMES, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .flatMap((d) => readdirSync(new URL(`${d.name}/`, FRAMES)).map((b) => [d.name, Number(b.slice(1))]));

test("every prepared folder has a light curve that matches its manifest", () => {
  const all = folders();
  assert.ok(all.length >= 6);
  for (const [t, b] of all) {
    const m = load(t, b, "manifest.json");
    const lc = load(t, b, "lightcurve.json");
    assert.equal(lc.format, "spherex-blink-lightcurve/1", `${t} D${b}`);
    assert.equal(lc.band, m.band);
    assert.equal(lc.unit, "mJy");
    if (lc.method === "none") {
      assert.ok(lc.reason.length > 40, `${t} D${b}: a method "none" light curve must say why`);
      assert.deepEqual(lc.points, []);
      continue;
    }
    for (const p of lc.points) {
      assert.ok(p.frame >= 0 && p.frame < m.frames.length);
      if (p.flux_mjy !== null) assert.ok(p.err_mjy > 0, `${t} D${b} ${p.obs_id}: every flux needs an error`);
    }
  }
});

test("the brightness scale: linear and asinh pass, unknown stretches fail", () => {
  const m = load("eps_ind_b", 2, "manifest.json");
  assert.doesNotThrow(() => checkManifest(m));
  const rdra = load("r_dra", 2, "manifest.json");
  assert.equal(rdra.scale.stretch, "asinh");
  assert.doesNotThrow(() => checkManifest(rdra));
  assert.throws(() => checkManifest({ ...m, scale: { ...m.scale, stretch: "log" } }), /stretch/);
  assert.throws(() => checkManifest({ ...m, scale: { ...m.scale, stretch: "asinh" } }), /asinh_softening/);
  assert.match(scaleText(rdra.scale), /not proportional/);
  assert.doesNotMatch(scaleText(m.scale), /asinh/);
});

test("wavelength colours run from blue to red and clamp at the ends", () => {
  assert.equal(wavelengthColour(1.1, [1.1, 1.62]), "hsl(260, 85%, 62%)");
  assert.equal(wavelengthColour(1.62, [1.1, 1.62]), "hsl(0, 85%, 62%)");
  assert.equal(wavelengthColour(5, [1.1, 1.62]), "hsl(0, 85%, 62%)");
  assert.equal(wavelengthColour(null, [1.1, 1.62]), "#9aa7c2");
});

test("ticks are round numbers inside the range, and the y range holds every error bar", () => {
  assert.deepEqual(ticks(0, 100), [0, 20, 40, 60, 80, 100]);
  assert.deepEqual(ticks(1.1, 1.62, 6), [1.1, 1.2, 1.3, 1.4, 1.5, 1.6]);
  const [lo, hi] = yRange([{ flux_mjy: 10, err_mjy: 2 }, { flux_mjy: -1, err_mjy: 1 }]);
  assert.equal(lo, -2);
  assert.ok(hi >= 12);
});

test("RW Aur: comparisons list the clean pair first, then the flagged-only pair, and name the neighbour", () => {
  const m = load("rw_aur", 2, "manifest.json");
  const lc = load("rw_aur", 2, "lightcurve.json");
  const lines = comparisonLines(lc, m);
  assert.match(lines[0], /^visit 1 .* → visit 3 .*: 1 pair at the same wavelength, brightness ratio 1\.235\.$/);
  assert.ok(lines.some((l) => /including exposures with flagged pixels/.test(l) && /0\.889–1\.027/.test(l)));
  assert.deepEqual(offChart(lc.points), [], "flagged exposures of a bright star stay on the chart");
  const warnings = lightCurveWarnings(lc);
  const neighbour = warnings.find((w) => w.includes("156430822114424576"));
  assert.ok(neighbour && !neighbour.includes("follows"), "RW Aur moves 0.004 px, so no moving-circle warning");
  assert.ok(warnings.some((w) => /16 of 24 exposures/.test(w)));
  assert.ok(warnings.some((w) => /not known here/.test(w)), "no field star in this frame: say the floor is unknown");
});

test("WISE 0855 D2: the circle moves past the G 16.31 Gaia star, and the page says so", () => {
  const lc = load("wise0855", 2, "lightcurve.json");
  assert.ok(circleTravelPx(lc.points) >= 0.1);
  assert.ok(lightCurveWarnings(lc).some((w) => w.includes("5756956644387831296") && /follows the target/.test(w)));
});

test("WISE 0855 D6: one flagged 520 mJy exposure is drawn off the chart and named, not hidden", () => {
  const m = load("wise0855", 6, "manifest.json");
  const lc = load("wise0855", 6, "lightcurve.json");
  const off = offChart(lc.points);
  assert.deepEqual(off.map((p) => p.obs_id), ["2025W46_1A_0076_2"]);
  assert.ok(off[0].n_flagged > 0);
  const [, hi] = yRange(lc.points);
  assert.ok(hi < 10, "the scale follows the exposures without flagged pixels");
  assert.ok(lightCurveWarnings(lc).some((w) => w.includes("2025W46_1A_0076_2") && w.includes("520.6")));
  const svg = timeChart(lc, m);
  assert.equal((svg.match(/lc-off/g) || []).length, 1);
  assert.equal((svg.match(/<circle/g) || []).length, lc.points.length - 1);
  const wl = wavelengthChart(lc, m);
  const ys = [...wl.matchAll(/<path d="([^"]+)" class="lc-line"/g)]
    .flatMap((d) => [...d[1].matchAll(/[ML][\d.]+,([\d.-]+)/g)].map((v) => Number(v[1])));
  assert.ok(ys.every((y) => y >= 12 && y <= 202), "no line runs to the off-chart point");
});

test("Barnard: the field-star floor is reported, and no light curve is drawn", () => {
  const lc = load("barnard", 2, "lightcurve.json");
  assert.equal(lc.method, "none");
  assert.match(lightCurveWarnings({ ...lc, points: [], same_wavelength: { n_excluded: 0 } })[0], /4\.5%/);
});

test("charts: one point per measured exposure, flagged points hollow, wavelength lines per visit", () => {
  const m = load("rw_aur", 2, "manifest.json");
  const lc = load("rw_aur", 2, "lightcurve.json");
  const n = lc.points.filter((p) => p.flux_mjy !== null).length;
  const time = timeChart(lc, m);
  assert.equal((time.match(/<circle/g) || []).length, n);
  const hollow = lc.points.filter((p) => p.flux_mjy !== null && (p.n_flagged > 0 || p.flux_mjy < 5 * p.err_mjy)).length;
  assert.equal((time.match(/fill="none"/g) || []).length, hollow);
  const wl = wavelengthChart(lc, m);
  assert.equal((wl.match(/<circle/g) || []).length, n);
  assert.ok((wl.match(/class="lc-line"/g) || []).length >= 2);
});

test("a point's tooltip gives visit, date, wavelength, flux with error, flags and the exposure id", () => {
  const p = { date_iso: "2025-09-09 20:08 UTC", wl_um: 1.1787, flux_mjy: 169.3686, err_mjy: 1.0647, n_flagged: 2,
    obs_id: "2025W37_1A_0366_1" };
  assert.equal(pointTitle(p, 1),
    "Visit 1 · 2025-09-09 20:08 UTC · 1.179 µm · 169.37 ± 1.06 mJy · 2 flagged pixels in the circle · 2025W37_1A_0366_1");
});
