"""Offline tests for Ask about this view (ask.py, POST /api/ask). Gemini is replaced by fakes: the tests check the
facts we send, our number and claim checks on the answer, the cache, the key handling and the endpoint."""
import io
import json
import re
import urllib.error
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import ask, main

FRAMES = Path("frontend/frames")
FOLDERS = sorted(p.parent for p in FRAMES.glob("*/d*/manifest.json"))
IDS = lambda p: f"{p.parent.name}/{p.name}"
BARNARD = FRAMES / "barnard" / "d2"


@pytest.fixture(autouse=True)
def clean(monkeypatch, tmp_path):
    monkeypatch.setattr(ask, "CACHE", tmp_path / "ask")
    monkeypatch.setattr(ask, "_model", None)
    monkeypatch.setattr(ask, "_missing", set())
    monkeypatch.setattr(ask, "_resting", {})
    monkeypatch.setattr(ask, "_recent", {})


def fake_gemini(answer, calls=None):
    def call(system, prompt):
        if calls is not None:
            calls.append((system, prompt))
        return answer, "gemini-test"
    return call


# ---------- the facts we send ----------

@pytest.mark.parametrize("folder", FOLDERS, ids=IDS)
def test_facts_of_every_folder_are_numbered_and_filled_in(folder):
    facts = ask.build_facts(folder, {})
    assert [f["id"] for f in facts] == [f"F{i + 1}" for i in range(len(facts))]
    assert sum("(shown now)" in f["text"] for f in facts) == 1
    assert sum(len(f["text"]) for f in facts) < 12000
    for f in facts:
        assert f["text"].strip() and f["source"]
        assert not re.search(r"\b(None|nan|null)\b", f["text"]), f["text"]
    assert facts[-len(ask.GLOSSARY):] == [{"id": f"F{len(facts) - len(ask.GLOSSARY) + i + 1}",
                                          "source": "how the tool works", "text": t} for i, t in enumerate(ask.GLOSSARY)]


def test_facts_follow_the_view_and_ignore_impossible_values():
    plain = ask.build_facts(BARNARD, {})
    chosen = ask.build_facts(BARNARD, {"visit": 2, "spot": 0, "exposure": 1})
    texts = [f["text"] for f in chosen]
    assert any(t.startswith("Visit 3 (shown now)") for t in texts)
    assert any(t.startswith("Spot 1 (chosen now)") for t in texts)
    assert any(t.startswith("Spot 1, why:") for t in texts)
    assert any(t.startswith("Spot 1, what would confirm it:") for t in texts)
    assert any(t.startswith("Exposure 2 shown now") for t in texts)
    odd = ask.build_facts(BARNARD, {"visit": 99, "spot": "x", "exposure": -1, "a": "0", "b": None})
    assert [f["text"] for f in odd] == [f["text"] for f in plain]


def test_no_match_with_jpl_is_never_written_as_new():
    for folder in FOLDERS:
        for f in ask.build_facts(folder, {}):
            assert ask.check_answer(f["text"], [])["claim_warning"] is None, f["text"]


# ---------- our checks on the answer ----------

def test_numbers_in_skips_ids_and_detectors_and_reads_devanagari():
    assert ask.numbers_in("F12 says D2 moved 1.59 px over ३६०.२ days, −173.7σ") == ["1.59", "360.2", "-173.7"]


def test_rounded_numbers_count_as_found_but_others_do_not():
    known = [1.59, 360.2, 7.88]
    assert ask.number_found("1.6", known)
    assert ask.number_found("2", [1.59])
    assert ask.number_found("360", known)
    assert not ask.number_found("1.7", known)
    assert not ask.number_found("3.14", known)


def test_check_flags_invented_numbers_and_discovery_claims():
    facts = [{"text": "the star moved 1.59 px; Gaia DR3 predicts 1.67 px"}, {"text": "Spot 1: 9.5σ brighter in B"}]
    out = ask.check_answer("It moved about 1.6 px (Gaia: 1.67 px). Spot 1 was 3.14σ. It is a new asteroid.", facts)
    assert out == {"numbers_checked": 4, "numbers_not_found": ["3.14"], "claim_warning": "It is a new asteroid."}
    for honest in ("This is not a new object.", "Planet X cannot be detected by this tool.",
                   "No known asteroid was found, which does not mean a discovery.",
                   "A spot is simply a place to look rather than a new discovery.",
                   "Planet X is far fainter than what SPHEREx can see.",
                   "For distant planets like Planet Nine, the predicted brightness is far fainter than SPHEREx can detect."):
        assert ask.check_answer(honest, facts)["claim_warning"] is None, honest
    for claim in ("Maybe this is Planet Nine!", "This could be the long-sought Planet X.", "SPHEREx found Planet 9."):
        assert ask.check_answer(claim, facts)["claim_warning"] == claim, claim


# ---------- the whole answer ----------

ANSWER = {"general": "Barnard's Star moved 1.59 px, as Gaia predicts.", "details": "See the proof panel.",
          "facts_used": ["F6", "F6", "F999", "F2"], "answerable": True,
          "suggested_questions": ["a?", "b?", "c?", "d?"]}


def test_answer_maps_facts_drops_unknown_ids_and_is_labelled(monkeypatch):
    monkeypatch.setattr(ask, "call_gemini", fake_gemini(ANSWER))
    out = ask.ask(BARNARD, "  Did   it move? ", "en", {})
    facts = ask.build_facts(BARNARD, {})
    assert out["format"] == ask.FORMAT and out["question"] == "Did it move?"
    assert [s["id"] for s in out["sources"]] == ["F6", "F2"]
    assert out["sources"][0] == facts[5]
    assert out["suggested"] == ["a?", "b?", "c?"]
    assert out["check"]["numbers_not_found"] == [] and out["check"]["claim_warning"] is None
    assert "Google Gemini (gemini-test)" in out["label"] and "data only" in out["label"]
    assert out["cached"] is False and out["n_facts"] == len(facts)


def test_same_question_on_same_view_is_answered_from_the_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(ask, "call_gemini", fake_gemini(ANSWER, calls))
    first = ask.ask(BARNARD, "Did it move?")
    again = ask.ask(BARNARD, "did it  MOVE?")
    other_view = ask.ask(BARNARD, "Did it move?", view={"spot": 0})
    nepali = ask.ask(BARNARD, "Did it move?", "ne")
    assert len(calls) == 3 and again["cached"] is True
    assert {k: v for k, v in again.items() if k != "cached"} == {k: v for k, v in first.items() if k != "cached"}
    assert other_view["cached"] is False and nepali["cached"] is False
    assert "Nepali" in calls[-1][0]
    assert "FACTS:\nF1 [official target list] Barnard's Star" in calls[0][1]


def test_bad_questions_are_refused_before_gemini(monkeypatch):
    monkeypatch.setattr(ask, "call_gemini", lambda *a: pytest.fail("Gemini should not be called"))
    for question, lang in (("   ", "en"), ("x" * 401, "en"), ("ok?", "fr")):
        with pytest.raises(ValueError):
            ask.ask(BARNARD, question, lang)


# ---------- Gemini ----------

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gemini_reply(answer):
    return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]}).encode())


def http_error(code, text=""):
    return urllib.error.HTTPError("url", code, "error", {}, io.BytesIO(text.encode()))


def test_no_key_means_unavailable(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(ask, "REPO_ROOT", tmp_path)
    with pytest.raises(ask.AskUnavailable, match="GEMINI_API_KEY"):
        ask.call_gemini("system", "prompt")


def test_key_from_dotenv_goes_in_the_header_never_the_url(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    (tmp_path / ".env").write_text("OTHER=1\nGEMINI_API_KEY='secret-key'\n")
    monkeypatch.setattr(ask, "REPO_ROOT", tmp_path)
    sent = []

    def urlopen(req, timeout):
        sent.append(req)
        return gemini_reply(ANSWER)

    monkeypatch.setattr(ask.urllib.request, "urlopen", urlopen)
    answer, model = ask.call_gemini("system text", "prompt text")
    assert answer == ANSWER and model == ask.MODELS[0]
    req = sent[0]
    assert "secret-key" not in req.full_url and req.full_url.endswith(f"/models/{ask.MODELS[0]}:generateContent")
    assert req.get_header("X-goog-api-key") == "secret-key"
    body = json.loads(req.data)
    assert body["systemInstruction"]["parts"][0]["text"] == "system text"
    assert body["generationConfig"]["responseSchema"] == ask.SCHEMA
    assert body["generationConfig"]["temperature"] <= 0.3


def fake_models(monkeypatch, failures, listed=()):
    """Gemini where `failures[model]` (an exception) is raised for that model; others answer. Returns the URLs asked."""
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    urls = []

    def urlopen(req, timeout):
        urls.append(req.full_url)
        if "/models?" in req.full_url:
            return FakeResponse(json.dumps({"models": [
                {"name": f"models/{n}", "supportedGenerationMethods": ["generateContent"]} for n in listed]}).encode())
        model = req.full_url.split("/models/")[1].split(":")[0]
        if model in failures:
            raise failures[model]()
        return gemini_reply(ANSWER)

    monkeypatch.setattr(ask.urllib.request, "urlopen", urlopen)
    return urls


@pytest.mark.parametrize("error", [lambda: http_error(503), lambda: http_error(429), lambda: http_error(404),
                                   lambda: TimeoutError("read timed out"),
                                   lambda: urllib.error.URLError(TimeoutError("timed out"))])
def test_a_busy_slow_missing_or_spent_model_hands_over_to_the_next(monkeypatch, error):
    urls = fake_models(monkeypatch, {ask.MODELS[0]: error})
    assert ask.call_gemini("s", "p") == (ANSWER, ask.MODELS[1])
    assert len(urls) == 2
    ask.call_gemini("s", "p")
    assert len(urls) == 3 and urls[-1].endswith(f"/models/{ask.MODELS[1]}:generateContent")


def test_a_busy_model_rests_and_is_asked_again_later(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(ask.time, "time", lambda: clock[0])
    failures = {ask.MODELS[0]: lambda: http_error(503)}
    urls = fake_models(monkeypatch, failures)
    assert ask.call_gemini("s", "p")[1] == ask.MODELS[1]
    clock[0] += ask.REST_S - 1
    assert ask.call_gemini("s", "p")[1] == ask.MODELS[1] and len(urls) == 3
    failures.clear()
    clock[0] += 2
    assert ask.call_gemini("s", "p")[1] == ask.MODELS[0]


def test_low_thinking_is_asked_for(monkeypatch):
    sent = []
    fake_models(monkeypatch, {})
    real = ask.urllib.request.urlopen
    monkeypatch.setattr(ask.urllib.request, "urlopen", lambda req, timeout: sent.append(json.loads(req.data)) or real(req, timeout))
    ask.call_gemini("s", "p")
    assert sent[0]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}


def test_when_every_listed_model_is_gone_the_newest_flash_of_the_key_is_used(monkeypatch):
    gone = {m: (lambda: http_error(404, "model not found")) for m in ask.MODELS}
    urls = fake_models(monkeypatch, gone, ("gemini-2.0-flash", "gemini-4.1-flash", "gemini-4.1-flash-lite", "gemini-4.1-pro"))
    assert ask.call_gemini("s", "p")[1] == "gemini-4.1-flash"
    n = len(urls)
    assert ask.call_gemini("s", "p")[1] == "gemini-4.1-flash" and len(urls) == n + 1


@pytest.mark.parametrize("error, reason", [
    (lambda: http_error(429), "quota"),
    (lambda: http_error(503), "busy"),
    (lambda: TimeoutError("read timed out"), "busy"),
    (lambda: http_error(400, "API key not valid"), "refused the API key"),
    (lambda: http_error(502), "HTTP 502"),
    (lambda: urllib.error.URLError("offline"), "could not reach Gemini"),
])
def test_gemini_errors_become_plain_reasons(monkeypatch, error, reason):
    fake_models(monkeypatch, {m: error for m in ask.MODELS})
    with pytest.raises(ask.AskUnavailable, match=reason):
        ask.call_gemini("s", "p")


def test_unreadable_or_blocked_answers_are_unavailable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    for reply in ({"promptFeedback": {"blockReason": "SAFETY"}}, {"candidates": []},
                  {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}):
        monkeypatch.setattr(ask.urllib.request, "urlopen", lambda req, timeout, r=reply: FakeResponse(json.dumps(r).encode()))
        with pytest.raises(ask.AskUnavailable):
            ask.call_gemini("s", "p")


def test_rate_limit_per_client_and_minute():
    assert all(ask.allow("a", 1000 + i) for i in range(ask.PER_MINUTE))
    assert not ask.allow("a", 1010)
    assert ask.allow("b", 1010)
    assert ask.allow("a", 1000 + 61)


# ---------- the endpoint ----------

client = TestClient(main.app)
URL = "/api/ask?target=barnard&band=2"


def test_endpoint_answers_with_the_view(monkeypatch):
    calls = []
    monkeypatch.setattr(ask, "call_gemini", fake_gemini(ANSWER, calls))
    r = client.post(URL, json={"question": "Is this spot real?", "lang": "en", "view": {"a": 0, "b": 2, "spot": 0}})
    assert r.status_code == 200
    assert r.json()["sources"][0]["id"] == "F6"
    assert "Spot 1 (chosen now)" in calls[0][1]


def test_endpoint_errors(monkeypatch, tmp_path):
    assert client.post(URL, json={"question": " "}).status_code == 400
    assert client.post(URL, json={"lang": "en"}).status_code == 400
    assert client.post("/api/ask?target=nowhere&band=2", json={"question": "hi"}).status_code in (400, 404)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(ask, "REPO_ROOT", tmp_path)
    r = client.post(URL, json={"question": "What am I looking at?"})
    assert r.status_code == 503 and "not set up" in r.json()["error"]
    monkeypatch.setattr(main, "allow_question", lambda client: False)
    r = client.post(URL, json={"question": "What am I looking at?"})
    assert r.status_code == 429 and str(ask.PER_MINUTE) in r.json()["error"]
