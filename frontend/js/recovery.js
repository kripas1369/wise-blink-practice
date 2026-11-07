// Planted-mover test for the Before / After / Difference view (recovery.json, made by backend/app/recovery.py):
// how often the 5σ spot finder finds a fake moving star of known brightness in this pair's real frames.
import { loadExtra } from "./frames.js";

const $ = (id) => document.getElementById(id);

const fmt = (v, digits) => (v === null || v === undefined ? "–" : v.toFixed(digits));

/** The one-sentence answer for a pair: where half of the fakes are found. */
export function halfFoundText(pair, limit) {
  const h = pair.half_found;
  if (h === null) {
    const top = pair.levels[pair.levels.length - 1];
    return `Fewer than half of the fakes are found even at ${top.peak_sigma}σ (${top.found_pct}%): ` +
      "this pair's difference is too noisy to trust single spots.";
  }
  if (h.below_lowest !== undefined) {
    return `Half or more of the fakes are found already at the faintest level tried (${h.below_lowest}σ).`;
  }
  return `Half of the fakes are found at about ${h.peak_sigma}σ in the difference map: about ` +
    `${fmt(h.flux_mjy, 3)} mJy, AB magnitude ${fmt(h.ab_mag, 1)}. The spot finder's own limit is ${limit}σ.`;
}

/** Table rows: [label, found, both ends, lost (no value / blended / too faint), mJy, AB]. */
export function levelRows(pair) {
  return pair.levels.map((r) => [
    r.peak_sigma === 0 ? "0σ (none planted)" : `${r.peak_sigma}σ`,
    `${r.found_pct}%`,
    r.peak_sigma === 0 ? "–" : `${r.both_ends_pct}%`,
    r.peak_sigma === 0 ? "–" : `${r.lost.no_z_pct}% / ${r.lost.blended_pct}% / ${r.lost.too_faint_pct}%`,
    r.flux_mjy === undefined || r.flux_mjy === null ? "–" : fmt(r.flux_mjy, 3),
    r.ab_mag === undefined || r.ab_mag === null ? "–" : fmt(r.ab_mag, 1),
  ]);
}

/** The chance-match sentence from level 0. */
export function chanceText(pair, foundPx) {
  const zero = pair.levels.find((r) => r.peak_sigma === 0);
  if (!zero) return "";
  return `With nothing planted, ${zero.found_pct}% of random places still have a real spot within ${foundPx} px: ` +
    "found rates near that are chance.";
}

export function psfText(psf) {
  return `PSF width ${psf.fwhm_arcsec}″ (FWHM), ${psf.source}.`;
}

export function createRecovery() {
  const el = {
    box: $("rec-view"), summary: $("rec-summary"), half: $("rec-half"), table: $("rec-table"),
    chance: $("rec-chance"), method: $("rec-method"), limits: $("rec-limits"),
  };
  let cache = { base: null, data: null };
  let version = 0;

  function cell(tag, text) {
    const n = document.createElement(tag);
    n.textContent = text;
    return n;
  }

  /** Called by the difference view after it draws a pair. */
  async function show(loaded, a, b) {
    const v = ++version;
    if (!loaded) { el.box.hidden = true; return; }
    if (cache.base !== loaded.base) {
      let data = null;
      try {
        data = await loadExtra(loaded.base, "recovery.json");
      } catch {
        data = null;
      }
      if (v !== version) return;
      cache = { base: loaded.base, data };
    }
    const data = cache.data;
    const pair = data && data.pairs.find((p) => p.a === a && p.b === b);
    if (!pair) { el.box.hidden = true; return; }
    el.box.hidden = false;
    el.summary.textContent = `${data.rules.per_level} fakes per level · ${data.rules.step_px} px step`;
    el.half.textContent = halfFoundText(pair, data.limit_sigma);
    el.table.querySelector("tbody").replaceChildren(...levelRows(pair).map((row) => {
      const tr = document.createElement("tr");
      row.forEach((t, i) => tr.append(cell(i === 0 ? "th" : "td", t)));
      return tr;
    }));
    el.chance.textContent = chanceText(pair, data.rules.found_px);
    el.method.textContent = `${data.method}. ${psfText(data.psf)} Made by ${data.made_by}, ${data.made_at}.`;
    el.limits.replaceChildren(...data.limits.map((t) => cell("li", t)));
  }

  return { show };
}
