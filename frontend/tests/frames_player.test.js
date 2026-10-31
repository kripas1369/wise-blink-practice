import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";

import {
  FramesUnavailable, checkManifest, frameLabel, loadIndex, loadManifest, manifestUrl, spanDays, wavelengthText,
} from "../js/frames.js";
import { defaultBlinkPair, intervalMs, nextIndex, prevIndex } from "../js/player.js";

const FRAMES = new URL("../frames/", import.meta.url);
const readJson = (url) => JSON.parse(readFileSync(url, "utf8"));
const barnard = () => readJson(new URL("barnard/d2/manifest.json", FRAMES));

function fakeFetch(files) {
  return async (url) => (url in files
    ? { ok: true, status: 200, json: async () => structuredClone(files[url]) }
    : { ok: false, status: 404, json: async () => ({}) });
}

test("every prepared manifest passes the check and its images exist", () => {
  const index = readJson(new URL("index.json", FRAMES));
  const pairs = Object.entries(index.available).flatMap(([t, bands]) => bands.map((b) => [t, b]));
  assert.ok(pairs.length >= 1);
  for (const [target, band] of pairs) {
    const m = checkManifest(readJson(new URL(`${target}/d${band}/manifest.json`, FRAMES)));
    assert.equal(m.target, target);
    assert.equal(m.band, band);
    for (const f of m.frames) {
      for (const png of [f.png, f.flags_png].filter(Boolean)) {
        assert.ok(existsSync(new URL(`${target}/d${band}/${png}`, FRAMES)), `${target} d${band} ${png} missing`);
      }
    }
  }
  for (const target of readdirSync(FRAMES, { withFileTypes: true }).filter((d) => d.isDirectory())) {
    for (const band of readdirSync(new URL(`${target.name}/`, FRAMES))) {
      if (!existsSync(new URL(`${target.name}/${band}/manifest.json`, FRAMES))) continue;
      assert.ok((index.available[target.name] || []).includes(Number(band.slice(1))),
        `${target.name}/${band} has a manifest but is not in index.json`);
    }
  }
});

test("Barnard D2 add-up: real values give the expected label", () => {
  const m = checkManifest(barnard());
  assert.equal(m.mode, "coadd");
  assert.equal(m.frames.length, 3);
  assert.equal(m.size_px, 29);
  const f = m.frames[0];
  assert.equal(
    frameLabel(f, 0, 3),
    "Visit 1 of 3 · 2025-08-26 11:57 UTC · D2, 1.235–1.629 µm at the star (band 1.10–1.65 µm) · " +
      "8 exposures added of 18 in this visit · 2.6% pixels flagged · 0.2% with no value (striped)",
  );
  assert.ok(f.pct_no_value > 0, "Barnard's core is saturated, so some pixels have no value");
  assert.doesNotMatch(frameLabel({ ...f, pct_no_value: 0 }, 0, 3), /no value/);
  assert.ok(spanDays(m.frames) > 300 && spanDays(m.frames) < 400);
});

test("label wording for single exposures, add-ups and unknown wavelength", () => {
  const single = { ...barnard().frames[0], n_images: 1, wl_target_range_um: undefined };
  assert.match(frameLabel(single, 0, 3), / · 1 exposure of 18 in this visit · /);
  const frame = { ...barnard().frames[0], n_images: 7, n_images_in_epoch: undefined, wl_target_um: null };
  assert.match(frameLabel(frame, 1, 3), /^Visit 2 of 3 · .* · 7 exposures added · /);
  assert.match(wavelengthText(frame), /^wavelength at the star unknown \(band /);
  const mixed = { ...frame, wl_target_um: 1.2, wl_target_range_um: [1.18, 1.25] };
  assert.match(wavelengthText(mixed), /^1\.180–1\.250 µm at the star \(band /);
  assert.match(wavelengthText({ ...mixed, wl_target_range_um: [1.2, 1.2] }), /^1\.200 µm at the star/);
});

test("bad manifests are refused, not shown", () => {
  const cases = [
    [(m) => { m.format = "other"; }, /format/],
    [(m) => { delete m.size_px; }, /size_px/],
    [(m) => { m.scale.vmax = m.scale.vmin; }, /scale/],
    [(m) => { m.frames = []; }, /no frames/],
    [(m) => { m.frames[1].band = 6; }, /D6 in a D2/],
    [(m) => { delete m.frames[0].mjd; }, /observation time/],
    [(m) => { m.frames[2].mjd = m.frames[0].mjd; }, /time order/],
    [(m) => { delete m.frames[0].pct_flagged; }, /counts/],
    [(m) => { m.notes = "look closely"; }, /notes/],
  ];
  for (const [breakIt, message] of cases) {
    const m = barnard();
    breakIt(m);
    assert.throws(() => checkManifest(m), message);
  }
});

test("loading: missing files mean 'not prepared', server errors are reported", async () => {
  const m = barnard();
  const fetchFn = fakeFetch({
    "frames/index.json": { available: { barnard: [2] } },
    [manifestUrl("barnard", 2)]: m,
  });
  assert.deepEqual(await loadIndex(fetchFn), { barnard: [2] });
  assert.equal((await loadManifest("barnard", 2, fetchFn)).frames.length, 3);
  assert.equal(await loadManifest("barnard", 6, fetchFn), null);
  assert.deepEqual(await loadIndex(fakeFetch({})), {});
  const broken = async () => ({ ok: false, status: 500 });
  await assert.rejects(loadManifest("barnard", 2, broken), FramesUnavailable);
  const offline = async () => { throw new TypeError("network"); };
  await assert.rejects(loadIndex(offline), FramesUnavailable);
});

test("player: stepping, looping, blink pair and speed", () => {
  assert.equal(nextIndex(0, 3, false), 1);
  assert.equal(nextIndex(2, 3, false), null);
  assert.equal(nextIndex(2, 3, true), 0);
  assert.equal(prevIndex(0, 3, false), null);
  assert.equal(prevIndex(0, 3, true), 2);
  assert.equal(nextIndex(0, 0, true), null);
  assert.deepEqual(defaultBlinkPair(5), [0, 4]);
  assert.deepEqual(defaultBlinkPair(1), [0, 0]);
  assert.equal(intervalMs(2), 500);
  assert.equal(intervalMs(0.5), 2000);
});
