// Proof panel: the target's measured motion against Gaia DR3, and the data it rests on (proof.json,
// made by backend/app/proof.py). Every number comes from that file.
import { loadExtra } from "./frames.js";
import { directionText } from "./sky.js";

const $ = (id) => document.getElementById(id);

const VERDICTS = {
  agrees: "Agrees with Gaia DR3",
  disagrees: "Does not agree with Gaia DR3",
  too_small: "Too small to test",
  not_measurable: "Not measurable",
  no_gaia_target: "Nothing to compare with",
  one_visit: "Only one visit",
};

const arcsec = (px, scale) => `${(px * scale).toFixed(1)}″`;

/** { verdict, lines } for the motion card. */
export function motionText(proof) {
  const m = proof.motion;
  const verdict = VERDICTS[m.status] || m.status;
  if (!("expected_px" in m)) return { verdict, lines: [m.reason] };
  const s = proof.pixel_arcsec;
  const [d0, d1] = m.visits;
  const lines = [
    `Expected (Gaia DR3 ${m.gaia_source_id}, ${d0} to ${d1}): ${m.expected_size_px.toFixed(2)} px ` +
      `(${arcsec(m.expected_size_px, s)})` +
      (m.expected_size_px >= 0.05 ? ` toward the ${directionText(...m.expected_px)}.` : "."),
  ];
  if ("measured_px" in m) {
    lines.push(`Measured (${m.method}): ${m.measured_size_px.toFixed(2)} px (${arcsec(m.measured_size_px, s)})` +
      (m.measured_size_px >= 0.05 ? ` toward the ${directionText(...m.measured_px)}.` : "."));
  }
  if (m.status === "agrees" || m.status === "disagrees") {
    const l = m.limits;
    lines.push(`Difference: ${m.difference_px.toFixed(2)} px (limit ${l.max_error_px} px, from our plan's C4 test) and ` +
      `${m.direction_difference_deg}° in direction (limit ${l.max_direction_deg}°, our choice).`);
  }
  if (m.reason) lines.push(m.reason);
  return { verdict, lines };
}

function releaseText(name, r) {
  return `${name} (${r.n_exposures} exposure${r.n_exposures === 1 ? "" : "s"}, released ${r.release_date.slice(0, 10)})`;
}

/** Lines for the data card. */
export function dataLines(proof) {
  const d = proof.data;
  const [lo, hi] = d.pct_flagged_range;
  const lines = [
    `${d.n_visits} visit${d.n_visits === 1 ? "" : "s"} over ${Math.round(d.span_days)} days.`,
    `${d.n_exposures_used} of the ${d.n_exposures_taken} exposures taken in these visits are added up.`,
    `Flagged pixels: ${lo === hi ? `${lo}%` : `${lo}–${hi}%`} per visit.`,
    `Newest exposure: ${d.newest_exposure}.`,
  ];
  if (d.releases) {
    lines.push(`Data releases: ${Object.entries(d.releases).map(([n, r]) => releaseText(n, r)).join(", ")}; ` +
      `looked up at IRSA ${d.asked_irsa_at}.`);
  }
  if (d.releases_reason) lines.push(`Data release${d.releases ? " note" : ": unknown"} (${d.releases_reason}).`);
  lines.push(`Frames made ${d.frames_made_at}.`);
  return lines;
}

export function createProof() {
  const el = {
    box: $("proof-view"), message: $("proof-message"), body: $("proof-body"), summary: $("proof-summary"),
    verdict: $("proof-verdict"), motion: $("proof-motion"), data: $("proof-data"), method: $("proof-method"),
  };
  let version = 0;

  function fill(ul, lines) {
    ul.replaceChildren(...lines.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }));
  }

  function hide(message = "") {
    el.box.hidden = !message;
    el.body.hidden = true;
    el.message.hidden = !message;
    el.message.textContent = message;
  }

  /** Proof for frames that were just shown ({ manifest, base }), or hide (null). */
  async function show(frames) {
    const v = ++version;
    if (!frames) return hide();
    let proof;
    try {
      proof = await loadExtra(frames.base, "proof.json");
    } catch (err) {
      if (v === version) hide(`Could not load the proof panel: ${err.message}`);
      return;
    }
    if (v !== version) return;
    if (!proof) return hide("No proof panel was made for these frames yet.");
    const { verdict, lines } = motionText(proof);
    el.box.hidden = false;
    el.message.hidden = true;
    el.body.hidden = false;
    el.summary.textContent = `${frames.manifest.label} · D${frames.manifest.band}`;
    el.verdict.textContent = verdict;
    el.verdict.dataset.status = proof.motion.status;
    fill(el.motion, lines);
    fill(el.data, dataLines(proof));
    el.method.textContent = `How: ${proof.method}.`;
  }

  hide();
  return { show };
}
