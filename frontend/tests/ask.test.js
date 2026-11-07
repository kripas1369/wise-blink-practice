import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { askUrl, checkLine, claimLine, MAX_QUESTION, savedNote, sourceLine } from "../js/ask.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("the question goes to /api/ask with the frames' own location parameters", () => {
  assert.equal(askUrl({ targetKey: "barnard", det: 2, fov: 3 }).split("?")[0], "/api/ask");
  assert.match(askUrl({ targetKey: "barnard", det: 2, fov: 3 }), /target=barnard/);
  assert.match(askUrl({ targetKey: null, ra: 10.5, dec: -3.25, det: 4, fov: 3 }), /ra=10\.5.*dec=-3\.25.*band=4/);
});

test("number check line: unchecked numbers are named, otherwise how many were checked", () => {
  assert.match(checkLine({ numbers_checked: 4, numbers_not_found: ["3.14"] }), /3\.14 is not in this view's data\. Treat it as unchecked/);
  assert.match(checkLine({ numbers_checked: 4, numbers_not_found: ["3.14", "50"] }), /3\.14, 50 are not .* Treat them/);
  assert.match(checkLine({ numbers_checked: 5, numbers_not_found: [] }), /all 5 numbers in the answer appear/);
  assert.match(checkLine({ numbers_checked: 1, numbers_not_found: [] }), /the 1 number in the answer appears in/);
  assert.match(checkLine({ numbers_checked: 0, numbers_not_found: [] }), /no numbers to check/);
});

test("a discovery-sounding answer gets a warning that the tool cannot show anything is new", () => {
  assert.equal(claimLine({ claim_warning: null }), "");
  const w = claimLine({ claim_warning: "It is a new asteroid." });
  assert.match(w, /“It is a new asteroid\.”/);
  assert.match(w, /cannot show that anything is new/);
  assert.match(w, /Minor Planet Center/);
});

test("sources and saved answers are spelled out", () => {
  assert.equal(sourceLine({ id: "F6", source: "proof.json", text: "Moved 1.59 px." }), "F6 · proof.json: Moved 1.59 px.");
  assert.equal(savedNote({ cached: false, asked_at: "x" }), "");
  assert.equal(savedNote({ cached: true, asked_at: "2026-11-07 10:00 UTC" }), " Saved answer from 2026-11-07 10:00 UTC.");
});

test("the page has the panel, the example questions and a length limit that matches the server", () => {
  for (const id of ["ask-view", "ask-form", "ask-input", "ask-submit", "ask-status", "ask-answer"]) {
    assert.match(html, new RegExp(`id="${id}"`), id);
  }
  assert.equal((html.match(/class="btn btn-small ask-starter"/g) || []).length, 5);
  assert.match(html, new RegExp(`id="ask-input"[^>]*maxlength="${MAX_QUESTION}"`));
  const server = readFileSync(new URL("../../backend/app/ask.py", import.meta.url), "utf8");
  assert.match(server, new RegExp(`MAX_QUESTION = ${MAX_QUESTION}\\b`));
});
