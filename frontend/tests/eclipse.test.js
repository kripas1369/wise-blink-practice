import assert from "node:assert/strict";
import { test } from "node:test";

import { eclipsePart, pdmTheta, phaseOf } from "../js/eclipse.js";

test("phase puts the primary eclipse at 0 and wraps into [-0.5, 0.5)", () => {
  const P = 1.3;
  const t0 = 2000;
  for (const [cycles, want] of [[0, 0], [1, 0], [5.25, 0.25], [7.5, -0.5], [-2.75, 0.25]]) {
    assert.ok(Math.abs(phaseOf(t0 + cycles * P, P, t0) - want) < 1e-9, `${cycles}`);
  }
  assert.ok(Math.abs(phaseOf(t0 + 0.02 * P, P, t0, 0.02)) < 1e-9);
});

test("eclipse windows follow the TESS widths, secondary around sec_phase", () => {
  const eph = { prim_width: 0.1, sec_phase: -0.48, sec_width: 0.08 };
  assert.equal(eclipsePart(0.04, eph), 1);
  assert.equal(eclipsePart(0.06, eph), 0);
  assert.equal(eclipsePart(0.49, eph), 2);    // wraps: 0.49 is 0.03 from -0.48
  assert.equal(eclipsePart(-0.45, eph), 2);   // 0.03 from -0.48, inside the half-width 0.04
  assert.equal(eclipsePart(-0.40, eph), 0);
  assert.equal(eclipsePart(0.3, { ...eph, sec_phase: null, sec_width: null }), 0);
});

test("θ is lowest at the true period", () => {
  const P = 0.83;
  const t = Array.from({ length: 600 }, (_, i) => (i * 7.31) % 500);
  const y = t.map((x) => (Math.abs(phaseOf(x, P, 0)) < 0.05 ? 0.6 : 1) + 0.002 * Math.sin(i3(x)));
  const at = pdmTheta(t, y, P);
  const off = pdmTheta(t, y, P * 1.01);
  assert.ok(at < 0.2, `θ at P = ${at}`);
  assert.ok(off > 0.8, `θ off P = ${off}`);
});

function i3(x) { return x * 12.9898; }
