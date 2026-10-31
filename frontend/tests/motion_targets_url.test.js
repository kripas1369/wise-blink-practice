import assert from "node:assert/strict";
import { test } from "node:test";

import { positionAt, separationArcsec, VIEW_EPOCH } from "../js/motion.js";
import { TARGETS } from "../js/targets.js";
import { buildUrlState, readUrlState } from "../js/urlstate.js";

// Positions at 2026.0 computed by the Python backend (notes/DAY1_REPORT.md, cache/day1_report.json).
const BACKEND_2026 = {
  barnard: [269.446269, 4.768204],
  eps_ind_b: [331.096644, -56.80066],
  wise0855: [133.759765, -7.242186],
  rw_aur: [76.956587, 30.401291],
  r_dra: [248.167233, 66.755024],
};

test("target buttons land where the backend searched (within 0.1 arcsec)", () => {
  assert.equal(VIEW_EPOCH, 2026.0);
  for (const t of TARGETS) {
    const { ra, dec } = positionAt(t.ra, t.dec, t.pmra, t.pmdec, 2000.0, VIEW_EPOCH);
    const [bra, bdec] = BACKEND_2026[t.key];
    assert.ok(separationArcsec(ra, dec, bra, bdec) < 0.1, t.label);
  }
});

test("Barnard's Star moved about 270 arcsec from 2000 to 2026", () => {
  const b = TARGETS.find((t) => t.key === "barnard");
  const p = positionAt(b.ra, b.dec, b.pmra, b.pmdec, 2000.0, 2026.0);
  const moved = separationArcsec(b.ra, b.dec, p.ra, p.dec);
  assert.ok(Math.abs(moved - 270.2) < 0.5, String(moved));
});

test("RA wraps around 360", () => {
  const p = positionAt(359.9999, 0, 3.6e6, 0, 0, 1);
  assert.ok(p.ra >= 0 && p.ra < 1);
});

test("share link round trip", () => {
  const url = buildUrlState({ ra: 269.446269, dec: 4.768204, fov: 5, det: 6 });
  assert.equal(url, "?ra=269.446269&dec=4.768204&fov=5&det=6");
  const back = readUrlState(url);
  assert.deepEqual(back, { ra: 269.446269, dec: 4.768204, fov: 5, det: 6, problems: [] });
});

test("bad links fall back to defaults and say why", () => {
  const s = readUrlState("?ra=500&dec=10&fov=99&det=9");
  assert.equal(s.ra, null);
  assert.equal(s.fov, 3);
  assert.equal(s.det, 2);
  assert.equal(s.problems.length, 3);
  assert.deepEqual(readUrlState(""), { ra: null, dec: null, fov: 3, det: 2, problems: [] });
});
