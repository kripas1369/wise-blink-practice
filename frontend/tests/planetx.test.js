import assert from "node:assert/strict";
import { test } from "node:test";

import { abToMjy, neptuneTwinV, orbitArcsec, parallaxArcsec, planetFacts, planetLines } from "../js/planetx.js";

test("geometry: half a year moves Earth 2 AU, and a 1 AU parallax is 206265″", () => {
  assert.ok(Math.abs(parallaxArcsec(1, 365.25 / 2) - 2 * 206264.806) < 1e-6);
  assert.ok(Math.abs(parallaxArcsec(500, 365.25 / 2) - 825.06) < 0.01);   // 2/500 rad
  assert.equal(parallaxArcsec(500, 0), 0);
});

test("Kepler: a 100 AU orbit takes 1000 years, so 0.36° per year", () => {
  assert.ok(Math.abs(orbitArcsec(100, 365.25) - 1296) < 1e-9);
});

test("brightness: a Neptune twin at Neptune's distance is Neptune, 16× fainter per doubling", () => {
  assert.ok(Math.abs(neptuneTwinV(30.1) - 7.8) < 1e-9);
  assert.ok(Math.abs(neptuneTwinV(1000) - neptuneTwinV(500) - 10 * Math.log10(2)) < 0.01);
  assert.ok(Math.abs(abToMjy(0) - 3631e3) < 1e-6);
});

test("500 AU: about 1 px a day, leaves a 3′ square between visits", () => {
  const f = planetFacts(500);
  assert.ok(f.dayPx > 1 && f.dayPx < 1.5);
  assert.ok(f.halfYearArcmin > 14 && f.halfYearArcmin < 15);
  const lines = planetLines(f);
  assert.match(lines[2], /far outside a 3′ flipbook square\.$/);
  assert.match(lines[3], /^Brightness in visible light, if it were a Neptune twin: about V 20\.1 \(0\.03\d mJy\)/);
});
