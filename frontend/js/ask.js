// Ask about this view: a plain-words question goes to POST /api/ask (backend/app/ask.py), where Google Gemini
// answers only from the facts behind the current view and our code checks every number in the answer.
// Without the data API or a Gemini key the panel says so; the written panels below never depend on it.
import { framesQuery, hasApi } from "./frames.js";

const $ = (id) => document.getElementById(id);

export const MAX_QUESTION = 400;

/** /api/ask for the frames on screen (same location parameters as /api/frames). */
export function askUrl(where) {
  return framesQuery(where).replace("/api/frames?", "/api/ask?");
}

/** One line about our number check ({ numbers_checked, numbers_not_found }). */
export function checkLine(check) {
  const missing = check.numbers_not_found || [];
  if (missing.length) {
    return `Number check: ${missing.join(", ")} ${missing.length === 1 ? "is" : "are"} not in this view's data. ` +
      "Treat " + (missing.length === 1 ? "it" : "them") + " as unchecked.";
  }
  if (check.numbers_checked) {
    const n = check.numbers_checked;
    return `Number check: ${n === 1 ? "the 1 number in the answer appears" : `all ${n} numbers in the answer appear`} in this view's data.`;
  }
  return "Number check: the answer has no numbers to check.";
}

/** The warning shown when the answer sounds like a discovery claim, or "". */
export function claimLine(check) {
  if (!check.claim_warning) return "";
  return `The answer says “${check.claim_warning}” This tool cannot show that anything is new: a spot or a ` +
    "JPL no-match is a place to look, and confirming a new object needs follow-up observations and the Minor Planet Center.";
}

export function sourceLine(fact) {
  return `${fact.id} · ${fact.source}: ${fact.text}`;
}

/** "(saved answer from …)" for a cached answer, else "". */
export function savedNote(answer) {
  return answer.cached ? ` Saved answer from ${answer.asked_at}.` : "";
}

export function createAsk() {
  const el = {
    view: $("ask-view"), form: $("ask-form"), input: $("ask-input"), submit: $("ask-submit"),
    status: $("ask-status"), answer: $("ask-answer"), starters: document.querySelectorAll("#ask-view .ask-starter"),
  };
  let loaded = null;
  let state = { visit: 0, a: null, b: null, spot: null, exposure: null };
  let version = 0;

  function node(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function status(text) {
    el.status.textContent = text;
    el.status.hidden = !text;
  }

  function render(a) {
    const parts = [node("p", "ask-label", a.label + savedNote(a))];
    parts.push(node("p", `ask-general${a.answerable ? "" : " ask-unanswerable"}`, a.general));
    if (a.details) {
      const more = node("details", "ask-more");
      more.append(node("summary", "", "More detail"), node("p", "", a.details));
      parts.push(more);
    }
    const claim = claimLine(a.check);
    if (claim) parts.push(node("p", "ask-warning", claim));
    parts.push(node("p", `ask-check${a.check.numbers_not_found.length ? " ask-warning" : ""}`, checkLine(a.check)));
    if (a.sources.length) {
      const src = node("details", "ask-sources");
      const list = node("ul");
      list.append(...a.sources.map((f) => node("li", "", sourceLine(f))));
      src.append(node("summary", "", `Facts it used (${a.sources.length} of ${a.n_facts} from this view's files)`), list);
      parts.push(src);
    } else {
      parts.push(node("p", "ask-check ask-warning", "It named none of this view's facts, so nothing above is backed by the data."));
    }
    if (a.suggested.length) {
      const row = node("div", "ask-starters");
      row.append(node("span", "help", "Ask next:"));
      for (const q of a.suggested) {
        const b = node("button", "btn btn-small ask-starter", q);
        b.type = "button";
        b.addEventListener("click", () => send(q));
        row.append(b);
      }
      parts.push(row);
    }
    el.answer.replaceChildren(...parts);
    el.answer.hidden = false;
  }

  async function send(text) {
    const question = text.trim().slice(0, MAX_QUESTION);
    if (!question || !loaded) return;
    el.input.value = question;
    const v = ++version;
    if (!(await hasApi())) {
      status("The AI explainer needs the data API (uvicorn backend.app.main:app). The panels below explain this view without it.");
      return;
    }
    el.submit.disabled = true;
    el.answer.hidden = true;
    status("Gemini is reading this view's data…");
    let resp;
    let body;
    try {
      resp = await fetch(askUrl(loaded.where), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, view: state }),
      });
      body = await resp.json();
    } catch {
      if (v === version) { status("Could not reach the data API."); el.submit.disabled = false; }
      return;
    }
    if (v !== version) return;
    el.submit.disabled = false;
    if (!resp.ok) {
      status(`${body.error || `The data API answered HTTP ${resp.status}`} The panels below explain this view without it.`);
      return;
    }
    status("");
    render(body);
  }

  el.form.addEventListener("submit", (event) => { event.preventDefault(); send(el.input.value); });
  el.starters.forEach((b) => b.addEventListener("click", () => send(b.textContent)));

  // The flipbook calls visit() on every blink, so view changes only update what the next question sends.
  const update = (changes) => { state = { ...state, ...changes }; };

  return {
    /** New frames ({ manifest, base, where } or null); the flipbook has already reported its visit. */
    show(next) {
      loaded = next;
      version += 1;
      update({ a: null, b: null, spot: null, exposure: null });
      el.view.hidden = !next;
      el.answer.hidden = true;
      el.submit.disabled = false;
      status("");
    },
    visit(i) { if (i !== state.visit) update({ visit: i, exposure: null }); },
    pair(a, b) { update({ a: a ?? null, b: b ?? null, spot: null }); },
    spot(i) { update({ spot: i }); },
    exposure(visit, k) { update({ visit, exposure: k }); },
  };
}
