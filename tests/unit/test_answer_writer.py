"""Q-021: answers written from measured evidence, with a guard against invented numbers."""
import asyncio
import json
from types import SimpleNamespace

import httpx

from backend.app.answers import writer
from backend.app.answers.writer import WrittenAnswer, numbers_grounded, write_answer
from backend.app.schemas.evidence import EvidencePackage

EVIDENCE = {"task": "bi_temporal_change", "statistics": {"changed_pixels": 118997, "change_ratio": 0.1135}}
TEMPLATE = "Change detection completed: 118,997 pixels changed (11.35% of monitored area)."


def _reply(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def _keys(monkeypatch, gemini=True, nvidia=True):
    for name, on in (("GEMINI_API_KEY", gemini), ("NVIDIA_API_KEY", nvidia)):
        if on:
            monkeypatch.setenv(name, name.lower())
        else:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)


def test_numbers_grounded_accepts_formatting_rounding_and_percent_of_ratio():
    ev = json.dumps({"query": "detect changes", "measured_answer": TEMPLATE, **EVIDENCE})
    assert numbers_grounded("118,997 pixels changed, about 11.35% of the area.", ev)
    assert numbers_grounded("Roughly 11.4% of the area changed.", ev)
    assert not numbers_grounded("About 250,000 pixels changed.", ev)


def test_first_provider_answer_is_used(monkeypatch):
    _keys(monkeypatch)
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        assert request.headers["authorization"] == "Bearer gemini_api_key"
        assert "data:image" not in request.content.decode()
        return _reply("Yes: 118,997 pixels changed, 11.35% of the monitored area.")

    out = write_answer("detect changes", EVIDENCE, TEMPLATE, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert out.source == "gemini:gemini-2.5-flash"
    assert hosts == ["generativelanguage.googleapis.com"]


def test_provider_error_falls_through_to_nvidia(monkeypatch):
    _keys(monkeypatch)

    def handler(request):
        if request.url.host == "generativelanguage.googleapis.com":
            return httpx.Response(429, json={"error": "quota"})
        return _reply("11.35% of the area changed (118,997 pixels).")

    out = write_answer("detect changes", EVIDENCE, TEMPLATE, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert out.source == "nvidia:meta/llama-3.3-70b-instruct"
    assert [a["status"] for a in out.attempts] == ["error", "ok"]


def test_invented_numbers_fall_back_to_template(monkeypatch):
    _keys(monkeypatch)
    out = write_answer("detect changes", EVIDENCE, TEMPLATE,
                       http=httpx.Client(transport=httpx.MockTransport(lambda r: _reply("42 new buildings appeared."))))
    assert out.source == "template" and out.text == TEMPLATE
    assert [a["status"] for a in out.attempts] == ["rejected_ungrounded_number", "rejected_ungrounded_number"]


def test_no_keys_means_no_network_and_template(monkeypatch):
    _keys(monkeypatch, gemini=False, nvidia=False)

    def handler(request):
        raise AssertionError("no request expected")

    out = write_answer("detect changes", EVIDENCE, TEMPLATE, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert out.source == "template"
    assert [a["status"] for a in out.attempts] == ["no_key", "no_key"]


def _state():
    traces = []
    return SimpleNamespace(
        query="detect changes", answer=TEMPLATE, task=None, selected_models=["changeformer"], confidence=0.87,
        evidence=EvidencePackage(), warnings=[], model_results=[], status="COMPLETED", traces=traces,
        add_trace=lambda step, status="success", details=None, **kw: traces.append((step, status, details)),
    )


def test_apply_answer_writer_disabled_leaves_answer(monkeypatch):
    monkeypatch.setenv("SATQUERY_ANSWER_WRITER", "off")
    state = _state()
    assert asyncio.run(writer.apply_answer_writer(state)) == ("template", TEMPLATE)
    assert state.answer == TEMPLATE and state.traces == []


def test_apply_answer_writer_replaces_answer_and_keeps_facts(monkeypatch):
    monkeypatch.setenv("SATQUERY_ANSWER_WRITER", "on")
    monkeypatch.setattr(writer, "write_answer",
                        lambda q, ev, t: WrittenAnswer("Written answer.", "gemini:x", [{"provider": "gemini", "status": "ok"}]))
    state = _state()
    assert asyncio.run(writer.apply_answer_writer(state)) == ("gemini:x", TEMPLATE)
    assert state.answer == "Written answer."
    assert state.traces[0][0] == "Answer written from measured evidence"
