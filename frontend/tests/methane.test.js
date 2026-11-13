import assert from "node:assert/strict";
import { test } from "node:test";

import { downloadLines, markerStyle, numberLines, verdictTitle, visitCaption } from "../js/methane.js";

const data = {
  settings: {
    absorbed: { band: 4, range_um: [3.15, 3.5] }, window: { band: 5, range_um: [3.9, 4.2] }, ref_um: 4,
    methane_excess: 2, glow_sigma: 5, normal_sigma: 3,
  },
  calibration: { k: 1.02, rule: "median of 3 field sources" },
  target: {
    colour: {
      testable: true, excess: 7.8, excess_err: 0.3, excess_is_lower_limit: false, glow_sigma: 59.4,
      absorbed_mjy: 6.1, absorbed_err_mjy: 0.05, window_mjy: 48.2, window_err_mjy: 0.1,
    },
    verdict: { status: "glows", text: "Glows." },
  },
  all: { n_absorbed: 12, n_window: 30 },
  visits: [
    { date: "2025-10-08", absorbed: { n: 1, wl_um: [3.4969] }, window: { n: 2, wl_um: [3.9583, 4.0983] },
      colour: { testable: false } },
    { date: "2026-04-23", absorbed: { n: 4, wl_um: [3.2, 3.45] }, window: { n: 4, wl_um: [3.95, 4.15] },
      colour: { testable: true, glow_sigma: 60.2 } },
  ],
  downloads: { D4: { n_in_archive: 43, n_considered: 43, n_in_window: 12, n_off_grid: 1, n_failed: 0 } },
};

test("verdict titles name every status from backend/app/methane.py", () => {
  for (const s of ["glows", "normal", "bluer", "unclear", "too_faint", "not_testable"]) {
    assert.notEqual(verdictTitle(s), s);
  }
});

test("number lines come from the file", () => {
  const lines = numberLines(data);
  assert.match(lines[0], /3\.90–4\.20 µm it has 7\.8 ± 0\.3× .* 3\.15–3\.50 µm light .*\(\+59\.4σ\)/);
  assert.match(lines[2], /k = 1\.02: median of 3 field sources/);
  const limit = numberLines({ ...data, target: { ...data.target, colour: { ...data.target.colour, excess_is_lower_limit: true, excess_err: null } } });
  assert.match(limit[0], /at least 7\.8×/);
  assert.equal(numberLines({ ...data, target: { ...data.target, colour: { testable: false } } }).length, 2);
  const withNull = numberLines({ ...data, null_test: { n_places: 131, scatter: 1.33, largest: 3.7, factor: 1.33 } });
  assert.match(withNull[4], /131 places .* ±1\.33σ \(largest 3\.7σ\), so every σ here is divided by 1\.33/);
});

test("captions say which exposures each picture adds up", () => {
  assert.match(visitCaption(data, null), /12 exposures at 3\.15–3\.50 µm \(D4\) and 30 at 3\.90–4\.20 µm \(D5\)/);
  assert.equal(visitCaption(data, 0), "Visit 1 of 2 · 2025-10-08 · 1 exposure at 3.50–3.50 µm and 2 at 3.96–4.10 µm");
  assert.match(visitCaption(data, 1), /4 exposures .* · target \+60\.2σ$/);
});

test("markers sit on pixel centres", () => {
  assert.deepEqual(markerStyle([14, 14], 29), { left: `${(14.5 / 29) * 100}%`, top: `${(14.5 / 29) * 100}%` });
});

test("download lines report what was left out", () => {
  assert.deepEqual(downloadLines(data), [
    "D4: 43 images in the archive, 43 looked at, 12 at the right wavelength, 1 left out (target near the image edge).",
  ]);
});
