import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { coverageRows, groupVisits, monthTicks, timelineChart, timelineSummary } from "../js/timeline.js";

const FRAMES = new URL("../frames/", import.meta.url);
const coverage = JSON.parse(readFileSync(new URL("barnard/coverage.json", FRAMES), "utf8"));
const manifest = JSON.parse(readFileSync(new URL("barnard/d2/manifest.json", FRAMES), "utf8"));

test("visits: a gap of more than 30 days, or more than 60 days in one visit, starts a new one", () => {
  assert.deepEqual(groupVisits([10, 0, 5]), [{ mjd_min: 0, mjd_max: 10, n: 3 }]);
  assert.equal(groupVisits([0, 31]).length, 2);
  assert.equal(groupVisits([0, 30]).length, 1);
  assert.equal(groupVisits([0, 25, 50, 61]).length, 2);
  assert.deepEqual(groupVisits([]), []);
});

test("month ticks: first of the month, every 2 or 3 months for long spans", () => {
  const short = monthTicks(60900, 61000);   // 2025-08-13 .. 2025-11-21
  assert.deepEqual(short.map((t) => t.label), ["2025-09", "2025-10", "2025-11"]);
  const year = monthTicks(60900, 61310);   // 13.5 months
  assert.ok(year.every((t) => Number(t.label.slice(5)) % 2 === 1));
  const long = monthTicks(60900, 61400);   // 16.4 months
  assert.ok(long.every((t) => Number(t.label.slice(5)) % 3 === 1));
  assert.ok(long.every((t, i) => i === 0 || t.mjd > long[i - 1].mjd));
});

test("rows: every image is in one detector row, and the rows agree with the server's counts", () => {
  const rows = coverageRows(coverage);
  assert.deepEqual(rows.map((r) => r.band), [1, 2, 3, 4, 5, 6]);
  assert.equal(rows.reduce((s, r) => s + r.mjds.length, 0), coverage.summary.n_images);
  for (const r of rows) assert.equal(r.mjds.length, coverage.summary.per_detector[String(r.band)]);
  assert.equal(rows.find((r) => r.band === 2).visits.length, manifest.frames.length);
});

test("chart: one tick per image, a clickable row per detector, ▼ only in the current row", () => {
  const svg = timelineChart(coverage, { det: 2, frameMjds: manifest.frames.map((f) => f.mjd) });
  assert.equal((svg.match(/class="tl-image"/g) || []).length, coverage.summary.n_images);
  assert.equal((svg.match(/class="tl-row/g) || []).length, 6);
  assert.equal((svg.match(/tl-row tl-current" data-band="2"/g) || []).length, 1);
  assert.equal((svg.match(/class="tl-frame"/g) || []).length, manifest.frames.length);
  assert.equal((timelineChart(coverage).match(/class="tl-frame"/g) || []).length, 0);
});

test("summary: from the file, and says why the flipbook can show fewer visits", () => {
  const [all, d2] = timelineSummary(coverage, 2, 3);
  assert.match(all, /^359 images \(181 exposures\) from 2025-08-15 to 2026-09-22 · releases: qr2 240, qr3 119/);
  assert.equal(d2, "D2: 61 images in 3 visits; the flipbook shows all 3.");
  assert.match(timelineSummary(coverage, 2, 2)[1], /shows 2 \(a visit is left out/);
  const empty = { ...coverage, summary: { n_images: 0 }, images: [] };
  assert.deepEqual(timelineSummary(empty, 2), ["SPHEREx has no images of this position yet."]);
});
