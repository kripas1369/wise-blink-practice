import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { originalsList, originalsNote } from "../js/files.js";

const FRAMES = new URL("../frames/", import.meta.url);
const originals = JSON.parse(readFileSync(new URL("barnard/d2/originals.json", FRAMES), "utf8"));
const manifest = JSON.parse(readFileSync(new URL("barnard/d2/manifest.json", FRAMES), "utf8"));

test("originals: one group per flipbook visit, every exposure links to IRSA", () => {
  const list = originalsList(originals);
  assert.equal(list.length, manifest.frames.length);
  list.forEach((v, i) => assert.equal(v.exposures.length, manifest.frames[i].n_images));
  assert.match(list[0].heading, /^Visit 1 · 2025-08-26 · 8 exposures$/);
  for (const e of list.flatMap((v) => v.exposures)) {
    assert.match(e.text, /^20\d\dW\d\d_\w+ D2 · QR\d$/);
    assert.match(e.file_url, /^https:\/\/irsa\.ipac\.caltech\.edu\/ibe\/data\/spherex\/qr\d\/level2\/.*D2_spx_.*\.fits$/);
    assert.match(e.datalink_url, /^https:\/\/irsa\.ipac\.caltech\.edu\/datalink\/links\/spherex\?ID=ivo:\/\/irsa\.ipac\/spherex_qr\d\?.*\/D2$/);
  }
});

test("originals note: counts exposures and says what is missing", () => {
  assert.match(originalsNote(originals), /^The 24 exposures added up in these frames\./);
  assert.ok(!originalsNote(originals).includes("could not be found"));
  assert.match(originalsNote({ ...originals, missing: ["x"] }), /1 could not be found at IRSA\.$/);
});
