import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { stepPair } from "../js/diffview.js";
import { dataLines, motionText } from "../js/proof.js";
import { detectorLines, spectrumChart, spectrumSummary, targetBase } from "../js/spectrum.js";
import { knownText, spotLine } from "../js/spots.js";

const FRAMES = new URL("../frames/", import.meta.url);
const load = (t, b, name) => JSON.parse(readFileSync(new URL(`${t}/d${b}/${name}`, FRAMES), "utf8"));

test("proof: Barnard's Star agrees with Gaia and says which limit is ours", () => {
  const { verdict, lines } = motionText(load("barnard", 2, "proof.json"));
  assert.equal(verdict, "Agrees with Gaia DR3");
  assert.match(lines[0], /^Expected \(Gaia DR3 4472832130942575872, 2025-08-26 to 2026-08-21\): 1\.67 px \(10\.3″\) toward the north/);
  assert.match(lines[1], /^Measured \(saturated-core centre\): 1\.59 px/);
  assert.match(lines[2], /0\.18 px \(limit 0\.5 px, from our plan's C4 test\).*\(limit 30°, our choice\)/);
});

test("proof: too-small and missing motions are not shown as a pass", () => {
  const rw = motionText(load("rw_aur", 2, "proof.json"));
  assert.equal(rw.verdict, "Too small to test");
  assert.ok(rw.lines.some((l) => l.includes("cannot test")));
  assert.ok(!rw.lines.some((l) => l.startsWith("Difference")));
  const wise = motionText(load("wise0855", 6, "proof.json"));
  assert.equal(wise.verdict, "Nothing to compare with");
  assert.deepEqual(wise.lines, [load("wise0855", 6, "proof.json").motion.reason]);
});

test("proof: data lines come from the file", () => {
  const p = load("barnard", 2, "proof.json");
  const lines = dataLines(p);
  assert.equal(lines[0], "3 visits over 360 days.");
  assert.equal(lines[1], `${p.data.n_exposures_used} of the ${p.data.n_exposures_taken} exposures taken in these visits are added up.`);
  assert.equal(lines[2], "Flagged pixels: 2.6–3.6% per visit.");
  assert.ok(lines.some((l) => /^Data releases: spherex_qr2 \(16 exposures, released 2026-04-21\), spherex_qr3 \(8 exposures, released 2026-09-30\)/.test(l)));
  const offline = { ...p, data: { ...p.data, releases: null, releases_reason: "not looked up (made offline)" } };
  assert.ok(dataLines(offline).includes("Data release: unknown (not looked up (made offline))."));
});

test("spot lines: sign, size, Gaia neighbour and artifact flags", () => {
  const pair = load("wise0855", 6, "spots.json").pairs.find((p) => p.a === 1 && p.b === 2);
  assert.equal(spotLine(pair.spots[0], 0),
    "1 · -8.3σ fainter in B · 2 px · no Gaia star within 1.5 px · possible artifact: touches the frame edge");
  assert.equal(spotLine(pair.spots[1], 1), "2 · +5.2σ brighter in B · 1 px · Gaia G 16.31 at 0.61 px");
});

test("known-object answers: three outcomes, never a new object", () => {
  const base = { match_rule: "within 2 px (ours)", match_radius_arcsec: 12.3, asked_at: "2026-10-31 15:38 UTC",
    pass_used: "first pass (two-body orbits, rougher)", search_half_deg: 0.05, notes: ["note"] };
  const ceres = { name: "1 Ceres (A801 AA)", distance_arcsec: 10.1, v_mag: 8.96, est_error_arcsec: [13.24, 13.24] };
  const match = knownText({ ...base, outcome: "match", matches: [ceres], nearby: [ceres], n_in_box: 8 });
  assert.equal(match.headline, "Matches known object 1 Ceres (A801 AA)");
  assert.equal(match.lines[0], "Known: 1 Ceres (A801 AA) at 10.1″ (V 8.96), JPL's position error 13.24″.");
  const none = knownText({ ...base, outcome: "no_match", matches: [], nearby: [], n_in_box: 0 });
  assert.equal(none.headline, "No known object within the match radius");
  assert.equal(none.lines[0], "0 known objects in the 6′ box.");
  assert.ok(none.lines.some((l) => l.startsWith("No match does not make the spot a new object")));
  const off = knownText({ outcome: "unavailable", reason: "second pass: JPL answered HTTP 500" });
  assert.deepEqual(off, { headline: "Check unavailable", lines: ["second pass: JPL answered HTTP 500."] });
});

test("visit stepper keeps A before B and stops at the ends", () => {
  const ids = [0, 1, 2, 3];
  assert.deepEqual(stepPair(ids, 0, 2, "a", 1), [1, 2]);
  assert.equal(stepPair(ids, 1, 2, "a", 1), null);
  assert.equal(stepPair(ids, 0, 2, "a", -1), null);
  assert.deepEqual(stepPair(ids, 0, 2, "b", 1), [0, 3]);
  assert.equal(stepPair(ids, 0, 3, "b", 1), null);
  assert.equal(stepPair(ids, 0, 1, "b", -1), null);
});

test("spectrum: file sits above the detector folders; every point drawn, one line per visit and detector", () => {
  assert.equal(targetBase("frames/wise0855/d6"), "frames/wise0855");
  assert.equal(targetBase("/jobframes/ra133.8_dec-7.2/d2"), "/jobframes/ra133.8_dec-7.2");
  const spec = JSON.parse(readFileSync(new URL("wise0855/spectrum.json", FRAMES), "utf8"));
  const svg = spectrumChart(spec);
  const n = spec.visits.reduce((s, v) => s + v.n_points, 0);
  assert.equal((svg.match(/class="lc-point/g) || []).length, n);
  const segments = spec.visits.reduce((s, v) => s + v.bands.filter(
    (b) => v.points.filter((p) => p.band === b).length > 1).length, 0);
  assert.ok((svg.match(/class="lc-line"/g) || []).length <= segments);
  assert.ok(svg.includes(">D6</text>") && svg.includes('class="lc-band"'));
});

test("spectrum: detector lines and summary come from the file", () => {
  const spec = JSON.parse(readFileSync(new URL("wise0855/spectrum.json", FRAMES), "utf8"));
  const lines = detectorLines(spec);
  assert.match(lines[0], /^D2 \(1\.10–1\.62 µm\): \d+ of \d+ exposures measured · PSF 5\.15″ wide/);
  assert.match(lines[1], /^D6 \(4\.42–5\.00 µm\): \d+ of \d+ exposures measured · PSF 6\.61″ wide/);
  assert.match(spectrumSummary(spec), /^WISE 0855 · D2, D6 · 3 visits · \d+ points$/);
  const none = { label: "Barnard's Star", visits: [], detectors: [{ band: 2, band_range_um: [1.1, 1.62], method: "none",
    reason: "Saturated core." }] };
  assert.deepEqual(detectorLines(none), ["D2 (1.10–1.62 µm): no points. Saturated core."]);
  assert.equal(spectrumSummary(none), "Barnard's Star · no detector · 0 visits · 0 points");
});
