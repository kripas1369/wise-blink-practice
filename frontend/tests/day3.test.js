import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

import { findPair, pairFacts, pairWarnings, pixelText, shiftText } from "../js/diffview.js";
import { gaiaNote } from "../js/flipbook.js";
import { framesQuery, loadFrames, resetApiCheck } from "../js/frames.js";
import { separationArcsec } from "../js/motion.js";
import { directionText, expectedShift, percentAt, pixelToSky, pixelUnder, visibleStars } from "../js/sky.js";

const FRAMES = new URL("../frames/", import.meta.url);
const readJson = (url) => JSON.parse(readFileSync(url, "utf8"));
const folder = (t, b) => new URL(`${t}/d${b}/`, FRAMES);
const load = (t, b, name) => readJson(new URL(name, folder(t, b)));

test("pixel to sky: centre, one pixel north, one pixel west", () => {
  const m = { ra: 180, dec: 10, size_px: 29, pixel_arcsec: 6.15 };
  assert.deepEqual(pixelToSky(14, 14, m), { ra: 180, dec: 10 });
  const north = pixelToSky(14, 13, m);
  assert.ok(Math.abs(separationArcsec(180, 10, north.ra, north.dec) - 6.15) < 0.01);
  assert.ok(north.dec > 10);
  const west = pixelToSky(15, 14, m);
  assert.ok(west.ra < 180, "x grows to the west, so RA gets smaller");
  assert.ok(Math.abs(separationArcsec(180, 10, west.ra, west.dec) - 6.15) < 0.01);
});

test("percent positions and the pixel under a pointer", () => {
  assert.deepEqual(percentAt([0, 0], 10), { left: 5, top: 5 });
  const rect = { left: 100, top: 50, width: 290, height: 290 };
  assert.deepEqual(pixelUnder(100, 50, rect, 29), { x: 0, y: 0 });
  assert.deepEqual(pixelUnder(389.9, 339.9, rect, 29), { x: 28, y: 28 });
  assert.equal(pixelUnder(99, 60, rect, 29), null);
});

test("directions on a north-up, east-left frame", () => {
  assert.equal(directionText(0, -1), "north");
  assert.equal(directionText(-1, 0), "east");
  assert.equal(directionText(-0.6, 0.4), "south-east");
  assert.equal(directionText(0.01, 0), "no measurable direction");
});

test("every prepared folder has Gaia markers and difference maps that match its frames", () => {
  const index = readJson(new URL("index.json", FRAMES));
  for (const [target, bands] of Object.entries(index.available)) {
    for (const band of bands) {
      const m = load(target, band, "manifest.json");
      const g = load(target, band, "gaia.json");
      const d = load(target, band, "diff.json");
      assert.equal(g.frames.length, m.frames.length, `${target} d${band} gaia frames`);
      g.stars.forEach((s) => assert.equal(s.xy.length, m.frames.length));
      assert.equal(typeof g.stars[0].source_id, "string", "Gaia ids are text (too big for JS numbers)");
      const n = m.frames.length;
      assert.equal(d.pairs.length, (n * (n - 1)) / 2);
      for (const p of d.pairs) {
        assert.ok(existsSync(new URL(p.png, folder(target, band))), `${target} d${band} ${p.png}`);
        assert.equal(p.z.length, m.size_px);
      }
      assert.ok(findPair(d, d.default_pair.a, d.default_pair.b));
      for (const f of m.frames) assert.ok(existsSync(new URL(f.fits, folder(target, band))), `${target} ${f.fits}`);
    }
  }
});

test("Barnard's Star: Gaia says 1.67 px north from the first to the last visit", () => {
  const g = load("barnard", 2, "gaia.json");
  const s = expectedShift(g, 0, 2, 6.15);
  assert.ok(Math.abs(s.px - 1.67) < 0.01);
  assert.equal(directionText(s.dx, s.dy), "north");
  assert.match(gaiaNote(g, 6.15), /moves 1\.67 px \(10\.3″\) from the first to the last visit, toward the north\./);
  assert.ok(visibleStars(g, 16).length < visibleStars(g, null).length);
  assert.ok(visibleStars(g, 0).every((s2) => s2.target), "the target is always drawn");
});

test("WISE 0855 has no Gaia match, and the page says so", () => {
  const g = load("wise0855", 6, "gaia.json");
  assert.equal(g.target_match, null);
  assert.match(gaiaNote(g, 6.15), /no star within 3″ of the frame centre/);
  assert.match(shiftText(g, 0, 1, 6.15), /no expected motion/);
});

test("Barnard difference: facts, warnings and one pixel's readout", () => {
  const m = load("barnard", 2, "manifest.json");
  const d = load("barnard", 2, "diff.json");
  const pair = findPair(d, 0, 2);
  assert.match(pairFacts(pair, m.frames[0], m.frames[2]), /^360\.2 days apart · wavelength at the star /);
  const warnings = pairWarnings(pair, m.frames[0], m.frames[2]);
  assert.ok(warnings.some((w) => /scatters 7\.88× more/.test(w)), "Barnard's halo makes the scatter large");
  assert.ok(warnings.some((w) => /mixes wavelengths/.test(w)));
  assert.match(pixelText(d, pair, 0, 2, 14, 14, m), /^Pixel \(14, 14\) · RA 17h57m.* · A no value · B no value MJy\/sr · \(B − A\)\/σ none \(striped\)$/);
  assert.match(pixelText(d, pair, 0, 2, 0, 0, m), /A -?\d+\.\d{3} ± \d+\.\d{3} · B .* · \(B − A\)\/σ [+-]\d+\.\d$/);
  assert.match(shiftText(load("barnard", 2, "gaia.json"), 0, 2, 6.15), /should move 1\.67 px \(10\.3″\) toward the north/);
});

function fakeFetch(routes) {
  return async (url) => {
    const r = routes[url];
    if (r === undefined) return { ok: false, status: 404, json: async () => { throw new Error("not JSON"); } };
    return { ok: r.status === 200, status: r.status, json: async () => structuredClone(r.body) };
  };
}

test("frames come from the API when there is one: ready, working, none, error", async () => {
  const m = load("barnard", 2, "manifest.json");
  const where = { targetKey: "barnard", ra: m.ra, dec: m.dec, det: 2, fov: 3 };
  const health = { "/api/health": { status: 200, body: { ok: true } } };
  assert.equal(framesQuery(where), "/api/frames?target=barnard&band=2");
  assert.match(framesQuery({ ...where, targetKey: null, fov: 5 }), /^\/api\/frames\?ra=269\.446269&dec=4\.768204&band=2&fov_arcmin=5$/);

  resetApiCheck();
  const ready = await loadFrames(where, fakeFetch({
    ...health, [framesQuery(where)]: { status: 200, body: { ...m, base_url: "/frames/barnard/d2/", warnings: [] } },
  }));
  assert.equal(ready.status, "ready");
  assert.equal(ready.base, "/frames/barnard/d2");

  resetApiCheck();
  const working = await loadFrames(where, fakeFetch({
    ...health, [framesQuery(where)]: { status: 202, body: { status: "working", message: "Preparing…" } },
  }));
  assert.deepEqual(working, { status: "working", message: "Preparing…" });

  resetApiCheck();
  const none = await loadFrames(where, fakeFetch({ ...health, [framesQuery(where)]: { status: 404, body: { error: "No SPHEREx images" } } }));
  assert.deepEqual(none, { status: "none", message: "No SPHEREx images" });

  resetApiCheck();
  await assert.rejects(
    loadFrames(where, fakeFetch({ ...health, [framesQuery(where)]: { status: 502, body: { error: "IRSA did not answer" } } })),
    /IRSA did not answer/,
  );
});

test("without the API: prepared files for targets, an honest message for other positions", async () => {
  const m = load("barnard", 2, "manifest.json");
  resetApiCheck();
  const files = fakeFetch({ "frames/barnard/d2/manifest.json": { status: 200, body: m } });
  const ready = await loadFrames({ targetKey: "barnard", det: 2, fov: 3 }, files);
  assert.equal(ready.base, "frames/barnard/d2");
  resetApiCheck();
  const none = await loadFrames({ targetKey: null, ra: 10, dec: 20, det: 2, fov: 3 }, files);
  assert.equal(none.status, "none");
  assert.match(none.message, /need the data API/);
  resetApiCheck();
});
