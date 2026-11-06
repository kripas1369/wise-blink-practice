import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { gunzipSync } from "node:zlib";

import {
  CATEGORIES, binary32, bitUse, bitsSet, checkPixels, describeFlags, directionWords, greyLimits, hex32, loadPixels,
  pixelInfo, skyAt, startPixel,
} from "../js/pixels.js";

const FRAMES = new URL("../frames/", import.meta.url);
const raw = (path) => readFileSync(new URL(path, FRAMES));
const read = (path) => JSON.parse(gunzipSync(raw(path)).toString("utf8"));

test("pixels: FLAGS integers decode into bits, binary and hex", () => {
  assert.deepEqual(bitsSet(2228293), [0, 2, 6, 17, 21]);
  assert.deepEqual(bitsSet(0), []);
  assert.deepEqual(bitsSet(2 ** 31), [31]);
  assert.equal(binary32(2097153), "0000 0000 0010 0000 0000 0000 0000 0001");
  assert.equal(hex32(2228293), "0x00220045");
});

test("pixels: bits are named by the file's own header; unknown bits say so", () => {
  const bits = [
    { bit: 0, name: "TRANSIENT", meaning: "Transient detected during SUR", rejected: true },
    { bit: 21, name: "SOURCE", meaning: "Pixel mapped to a known source", rejected: false },
    { bit: 19, name: "OUTLIER", meaning: "Pixel flagged by Detect Outliers", rejected: false },
  ];
  const d = describeFlags(1 | (1 << 21) | (1 << 30), bits);
  assert.deepEqual(d.map((f) => f.name), ["TRANSIENT", "SOURCE", "bit 30"]);
  assert.equal(d[2].known, false);
  assert.equal(bitUse(bits[0]), "Rejected (official bad list)");
  assert.equal(bitUse(bits[1]), "Kept (label only)");
  assert.equal(bitUse(bits[2]), "Kept (not on the bad list)");
});

test("pixels: every prepared file passes the checks and its categories are known", () => {
  for (const name of ["barnard/d2/pixels0.json.gz", "wise0855/d6/pixels1.json.gz", "rw_aur/d4/pixels2.json.gz"]) {
    const p = checkPixels(read(name));
    assert.ok(p.categories.every((k) => k in CATEGORIES));
  }
  assert.throws(() => checkPixels({ format: "x" }), /Unknown pixel-file format/);
  const p = read("barnard/d2/pixels0.json.gz");
  p.exposures[0].value.pop();
  assert.throws(() => checkPixels(p), /"value" does not match its shape/);
});

test("pixels: the 618 MJy/sr WISE 0855 D6 pixel (Day 4) reads back with all five flags", () => {
  const p = read("wise0855/d6/pixels1.json.gz");
  const e = p.exposures.find((x) => x.obs_id === "2025W46_1A_0076_2");
  const i = e.flag_index.indexOf(e.flag_values.indexOf(2228293));
  const [, nx] = e.shape;
  const info = pixelInfo(p, e, i % nx, Math.floor(i / nx));
  assert.equal(info.value, 617.8);
  assert.equal(info.category, "transient");
  assert.deepEqual(info.flags.map((f) => f.name), ["TRANSIENT", "SUR_ERROR", "NONFUNC", "PERSIST", "SOURCE"]);
  assert.deepEqual(info.detector, [e.detector_origin[0] + (i % nx), e.detector_origin[1] + Math.floor(i / nx)]);
  assert.ok(info.wavelength > 4.42 && info.wavelength < 5.0);
  assert.ok(info.snr > 50);
});

test("pixels: sky position at the reference pixel is the reference; one pixel is about 6.15″", () => {
  const e = read("barnard/d2/pixels0.json.gz").exposures[0];
  const [x0, y0] = e.sky.ref_px;
  const ref = skyAt(e.sky, x0, y0);
  assert.ok(Math.abs(ref.ra - e.sky.ref_radec[0]) < 1e-9 && Math.abs(ref.dec - e.sky.ref_radec[1]) < 1e-9);
  const step = skyAt(e.sky, x0 + 1, y0);
  const arcsec = Math.hypot((step.ra - ref.ra) * Math.cos((ref.dec * Math.PI) / 180), step.dec - ref.dec) * 3600;
  assert.ok(Math.abs(arcsec - 6.15) < 0.1, `${arcsec}`);
  assert.equal(directionWords(e.sky.north_px), "down");   // this detector is not north-up
  assert.equal(directionWords([1, 0]), "right");
  assert.equal(directionWords([-0.7, 0.7]), "up-left");
});

test("pixels: the first chosen pixel is the one under the target ring", () => {
  const e = read("barnard/d2/pixels0.json.gz").exposures[0];
  assert.deepEqual(startPixel(e), { x: Math.round(e.target_px[0]), y: Math.round(e.target_px[1]) });
  assert.deepEqual(startPixel({ shape: [5, 7], target_px: null }), { x: 3, y: 2 });
});

test("pixels: brightness limits ignore missing values", () => {
  const values = [null, ...Array.from({ length: 1000 }, (_, i) => i)];
  const { lo, hi } = greyLimits(values);
  assert.equal(lo, 10);
  assert.equal(hi, 994);
  assert.equal(greyLimits([null, null]), null);
});

test("pixels: loadPixels unpacks gzip, accepts already-unpacked JSON, and says null for a missing file", async () => {
  const gz = raw("barnard/d2/pixels0.json.gz");
  const plain = gunzipSync(gz);
  const answer = (body, status = 200) => async () => new Response(status === 404 ? "nope" : body, { status });
  const a = await loadPixels("frames/barnard/d2", 0, answer(gz));
  assert.equal(a.exposures.length, 8);
  const b = await loadPixels("frames/barnard/d2", 0, answer(plain));
  assert.equal(b.exposures[0].obs_id, a.exposures[0].obs_id);
  assert.equal(await loadPixels("frames/x/d2", 0, answer("", 404)), null);
});
