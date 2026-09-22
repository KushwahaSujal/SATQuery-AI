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


def test_numbers_grounded_query_not_treated_as_evidence():
    # The guard text (unlike the prompt text) must not include the query.
    guard = json.dumps({"measured_answer": "17 buildings were detected.", "instance_count": 17})
    assert not numbers_grounded("Yes, there are 42 buildings.", guard)


def test_write_answer_rejects_number_only_present_in_query(monkeypatch):
    _keys(monkeypatch)
    evidence = {"instance_count": 17}
    template = "17 buildings were detected."
    out = write_answer("Were 42 buildings built?", evidence, template,
                        http=httpx.Client(transport=httpx.MockTransport(
                            lambda r: _reply("Yes, there are 42 buildings."))))
    assert out.source == "template" and out.text == template
    assert [a["status"] for a in out.attempts] == ["rejected_ungrounded_number", "rejected_ungrounded_number"]


def test_numbers_grounded_is_sign_insensitive():
    ev = json.dumps({"measured_answer": "", "statistics": {"change_pct": -3.2}})
    assert numbers_grounded("The area decreased by 3.2%.", ev)


def test_numbers_grounded_ratio_times_100_rule_still_applies():
    # numbers_grounded itself is field-name agnostic; `write_answer` is what strips `confidence`
    # out of the guard text before calling it (see test_write_answer_excludes_confidence_from_guard).
    # The existing ratio-field ×100 rule must still pass here.
    ev_ratio = json.dumps({"measured_answer": TEMPLATE, **EVIDENCE})
    assert numbers_grounded("Roughly 11.35% of the area changed.", ev_ratio)


def test_write_answer_excludes_confidence_from_guard(monkeypatch):
    _keys(monkeypatch)
    evidence = {"confidence": 0.85}
    template = "Detection completed."
    out = write_answer("how many ships", evidence, template,
                        http=httpx.Client(transport=httpx.MockTransport(
                            lambda r: _reply("There are 85 ships."))))
    assert out.source == "template" and out.text == template
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


def test_apply_answer_writer_degrades_to_template_on_exception(monkeypatch):
    monkeypatch.setenv("SATQUERY_ANSWER_WRITER", "on")

    def boom(q, ev, t):
        raise RuntimeError("boom")

    monkeypatch.setattr(writer, "write_answer", boom)
    state = _state()
    assert asyncio.run(writer.apply_answer_writer(state)) == ("template", TEMPLATE)
    assert state.answer == TEMPLATE
    assert len(state.traces) == 1
    assert state.traces[0][0] == "Answer written from measured evidence"
    assert state.traces[0][1] == "warning"
