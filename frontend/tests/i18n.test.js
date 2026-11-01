import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { NE, savedLanguage } from "../js/i18n.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const keys = new Set([...html.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]));

test("every tagged element has a Nepali text, and every Nepali text is used", () => {
  assert.ok(keys.size > 50);
  assert.deepEqual([...keys].filter((k) => !(k in NE)), []);
  assert.deepEqual(Object.keys(NE).filter((k) => !keys.has(k)), []);
});

test("Nepali texts keep the numbers, symbols and markup of the English page", () => {
  for (const [key, ne] of Object.entries(NE)) {
    assert.match(ne, /[\u0900-\u097F]/, `${key} has no Devanagari`);
    const en = html.match(new RegExp(`<(\\w+)[^>]*data-i18n="${key.replace(".", "\\.")}"[^>]*>([\\s\\S]*?)</\\1>`));
    assert.ok(en, key);
    for (const tag of ["code", "sub", "span"]) {
      const n = (s) => (s.match(new RegExp(`<${tag}[ >]`, "g")) || []).length;
      assert.equal(n(ne), n(en[2]), `${key}: <${tag}> count`);
    }
  }
  assert.match(NE["diff.fainter"], /−5σ/);
  assert.match(NE["search.help"], /<code>269\.446 4\.768<\/code>/);
});

test("language choice: only 'ne' switches, anything else (or no storage) is English", () => {
  const store = (v) => ({ getItem: () => v });
  assert.equal(savedLanguage(store("ne")), "ne");
  assert.equal(savedLanguage(store("fr")), "en");
  assert.equal(savedLanguage(null), "en");
  assert.equal(savedLanguage({ getItem: () => { throw new Error("blocked"); } }), "en");
});
