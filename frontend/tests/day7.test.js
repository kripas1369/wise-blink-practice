import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { chanceText, halfFoundText, levelRows, psfText } from "../js/recovery.js";
import { exposureCaption, knownSummary, objectLine, sinceFirst, spanText } from "../js/visitflip.js";

const FRAMES = new URL("../frames/", import.meta.url);
const read = (path) => JSON.parse(readFileSync(new URL(path, FRAMES), "utf8"));

test("planted movers: one table row per level, level 0 has no brightness", () => {
  const r = read("rw_aur/d1/recovery.json");
  const pair = r.pairs[0];
  const rows = levelRows(pair);
  assert.equal(rows.length, pair.levels.length);
  assert.deepEqual(rows[0].slice(0, 1).concat(rows[0].slice(2)), ["0σ (none planted)", "–", "–", "–", "–"]);
  for (const row of rows.slice(1)) {
    assert.match(row[0], /^\d+σ$/);
    assert.match(row[3], /^[\d.]+% \/ [\d.]+% \/ [\d.]+%$/);
    assert.match(row[5], /^\d+\.\d$/);
  }
  assert.match(chanceText(pair, r.rules.found_px), /^With nothing planted, [\d.]+% of random places/);
  assert.match(psfText(r.psf), /^PSF width [\d.]+″ \(FWHM\), /);
});

test("planted movers: the half-found sentence covers all three cases", () => {
  const levels = [{ peak_sigma: 0, found_pct: 4 }, { peak_sigma: 20, found_pct: 31 }];
  assert.match(halfFoundText({ half_found: { peak_sigma: 4.9, flux_mjy: 0.1656, ab_mag: 18.35 }, levels }, 5),
    /^Half of the fakes are found at about 4\.9σ .* 0\.166 mJy, AB magnitude 18\.4\. The spot finder's own limit is 5σ\.$/);
  assert.match(halfFoundText({ half_found: null, levels }, 5), /even at 20σ \(31%\)/);
  assert.match(halfFoundText({ half_found: { below_lowest: 3 }, levels }, 5), /faintest level tried \(3σ\)/);
});

test("inside one visit: times, captions and known-object words", () => {
  assert.equal(sinceFirst(0), "first exposure");
  assert.equal(sinceFirst(3.25), "+3.3 h");
  assert.equal(sinceFirst(60), "+2.5 d");
  const v = read("rw_aur/d1/visits.json");
  const visit = v.visits[0];
  assert.match(exposureCaption(visit, 0), /^Exposure 1 of \d+ · 20\d\dW\d\d_\w+ · 20\d\d-\d\d-\d\d \d\d:\d\d:\d\d UTC · first exposure · [\d.]+ µm/);
  assert.match(spanText(visit), /^\d+ exposures over /);
  const o = { name: "32455 (2000 SW60)", mag: 18.24, rate_arcsec_per_h: 41.2, distance_au: 1.83 };
  assert.equal(objectLine(o), "32455 (2000 SW60): V 18.2, moving 41.2″/h, 1.83 AU away (JPL prediction)");
  assert.match(knownSummary({ outcome: "objects", objects: [o] }).headline, /^1 known object in the frame$/);
  const none = knownSummary({ outcome: "none", objects: [] }, 20.5);
  assert.equal(none.headline, "No known asteroid or comet brighter than V 20.5 in the frame");
  assert.ok(none.lines.join(" ").includes("would still not be a new object"));
  assert.deepEqual(knownSummary({ outcome: "unavailable", reason: "JPL answered HTTP 500" }).lines, ["JPL answered HTTP 500."]);
  assert.equal(knownSummary({ outcome: "not_asked" }).lines.length, 0);
});
