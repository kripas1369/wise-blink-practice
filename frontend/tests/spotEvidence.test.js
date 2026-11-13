import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { pairSignificanceLine } from "../js/diffview.js";
import { buildSpotEvidence } from "../js/spotEvidence.js";

const FRAMES = new URL("../frames/", import.meta.url);
const load = (t, b, name) => JSON.parse(readFileSync(new URL(`${t}/d${b}/${name}`, FRAMES), "utf8"));

test("difference map significance line is honest about scatter", () => {
  const pair = load("barnard", 2, "diff.json").pairs.find((p) => p.a === 0 && p.b === 2);
  assert.match(pairSignificanceLine(pair), /strongest \+.*σ.*scatter on good pixels 7\.88×/);
});

test("spot evidence JSON bundles file fields only", () => {
  const manifest = load("barnard", 2, "manifest.json");
  const spots = load("barnard", 2, "spots.json");
  const pair = spots.pairs[0];
  const diffPair = load("barnard", 2, "diff.json").pairs.find((p) => p.a === pair.a && p.b === pair.b);
  const bundle = buildSpotEvidence({
    manifest,
    base: "frames/barnard/d2",
    pair,
    spotIndex: 0,
    jpl: { outcome: "no_match", n_in_box: 0 },
    diffPair,
  });
  assert.equal(bundle.format, "spherex-blink-spot-evidence/1");
  assert.ok(bundle.disclaimer.includes("not make this a new discovery"));
  assert.equal(bundle.spot.index, 1);
  assert.equal(bundle.jpl_known_objects.outcome, "no_match");
  assert.equal(bundle.difference_map.scatter_sigma, diffPair.scatter_sigma);
});
