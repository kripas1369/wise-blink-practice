import assert from "node:assert/strict";
import { test } from "node:test";

import { formatDec, formatRa, looksLikeName, parseCoordinates } from "../js/coords.js";

const close = (a, b, tol = 1e-6) => assert.ok(Math.abs(a - b) < tol, `${a} != ${b}`);

test("reads letters, colons, spaces and degrees (WISE 0855 from the challenge text)", () => {
  for (const text of [
    "08h55m10.831s -07d14m42.53s",
    "08:55:10.831 -07:14:42.53",
    "08 55 10.831 -07 14 42.53",
    "08h55m10.831s, -07d14m42.53s",
  ]) {
    const { ra, dec } = parseCoordinates(text);
    close(ra, 133.7951292, 1e-6);
    close(dec, -7.2451472, 1e-6);
  }
  const { ra, dec } = parseCoordinates("269.446 4.768");
  close(ra, 269.446);
  close(dec, 4.768);
});

test("a negative Dec below one degree keeps its sign", () => {
  close(parseCoordinates("12:00:00 -00:30:00").dec, -0.5);
});

test("bad input raises instead of guessing", () => {
  for (const text of ["", "269.4", "400 10", "10 95", "12:61:00 +10:00:00", "1 2 3"]) {
    assert.throws(() => parseCoordinates(text), Error, text);
  }
});

test("names are told apart from numbers", () => {
  assert.equal(looksLikeName("Barnard's Star"), true);
  assert.equal(looksLikeName("M31"), true);
  assert.equal(looksLikeName("17h57m48s +04d41m36s"), false);
  assert.equal(looksLikeName("269.45 4.69"), false);
});

test("formatting gives back the same position", () => {
  assert.equal(formatRa(133.7951292), "08h55m10.83s");
  assert.equal(formatDec(-7.2451472), "-07°14′42.5″");
  const again = parseCoordinates(`${formatRa(269.446269).replace(/[hms]/g, ":").slice(0, -1)} 4.768204`);
  close(again.ra, 269.446269, 1e-4);
});
