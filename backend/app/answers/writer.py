"""
Final-answer writer (Q-021). The pipeline's template answer is built from measurements; an LLM rephrases it for the
user's question from the evidence JSON only (never the image). Gemini first, NVIDIA NIM second, template last.
Any number in the written answer that is not in the evidence rejects that answer.
"""
import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

from backend.app.logging import logger


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key_env: str
    model_env: str
    default_model: str


DEFAULT_PROVIDERS: Tuple[Provider, ...] = (
    Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "GEMINI_MODEL",
             "gemini-2.5-flash"),
    Provider("nvidia", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY", "NVIDIA_MODEL",
             "meta/llama-3.3-70b-instruct"),
)

SYSTEM_PROMPT = (
    "You write the final answer for a satellite-image analysis tool. Use ONLY the facts in the EVIDENCE JSON. "
    "Do not add objects, numbers, places, dates or causes that are not in it. Copy numbers exactly as they appear. "
    "If the evidence says something was not found, is unconfirmed, disputed or not configured, say so plainly. "
    "Answer the QUESTION directly in 1 to 4 sentences of plain English, without markdown."
)

# Evidence metadata worth giving the writer; the rest (per-instance boxes, traces) adds tokens, not facts.
WRITER_METADATA_KEYS = ("instance_count", "instance_filters", "agent_deliberation", "aoi", "change_inference")

_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


@dataclass
class WrittenAnswer:
    text: str
    source: str
    attempts: List[Dict[str, Any]] = field(default_factory=list)


def _numbers(text: str) -> List[float]:
    out = []
    for m in _NUMBER.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            continue
    return out


def numbers_grounded(answer: str, evidence_text: str) -> bool:
    allowed = set(_numbers(evidence_text))
    for n in _numbers(answer):
        if n in allowed:
            continue
        if any(abs(n - a) <= max(0.051, abs(a) * 0.005) for a in allowed):
            continue
        if any(abs(a) <= 1 and abs(n - a * 100) <= 0.051 for a in allowed):
            continue
        return False
    return True


def answer_writer_enabled() -> bool:
    return os.getenv("SATQUERY_ANSWER_WRITER", "off").lower() in ("on", "1", "true")


def write_answer(
    query: str,
    evidence: Dict[str, Any],
    template_answer: str,
    providers: Sequence[Provider] = DEFAULT_PROVIDERS,
    http: Optional[httpx.Client] = None,
    timeout: float = 8.0,
) -> WrittenAnswer:
    evidence_text = json.dumps({"query": query, "measured_answer": template_answer, **evidence},
                               default=str, ensure_ascii=False)
    attempts: List[Dict[str, Any]] = []
    client = http or httpx.Client()
    try:
        for p in providers:
            key = os.getenv(p.api_key_env)
            if not key:
                attempts.append({"provider": p.name, "status": "no_key"})
                continue
            model = os.getenv(p.model_env, p.default_model)
            try:
                r = client.post(
                    f"{p.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "temperature": 0.2, "max_tokens": 300, "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"QUESTION: {query}\n\nEVIDENCE: {evidence_text}"},
                    ]},
                    timeout=timeout,
                )
                r.raise_for_status()
                text = (r.json()["choices"][0]["message"]["content"] or "").strip()
            except Exception as e:
                logger.warning(f"Answer writer provider '{p.name}' failed: {type(e).__name__}")
                attempts.append({"provider": p.name, "status": "error", "error": type(e).__name__})
                continue
            if not text:
                attempts.append({"provider": p.name, "status": "empty"})
                continue
            if not numbers_grounded(text, evidence_text):
                attempts.append({"provider": p.name, "status": "rejected_ungrounded_number"})
                continue
            attempts.append({"provider": p.name, "status": "ok"})
            return WrittenAnswer(text, f"{p.name}:{model}", attempts)
    finally:
        if http is None:
            client.close()
    return WrittenAnswer(template_answer, "template", attempts)


def evidence_for_writer(state: Any) -> Dict[str, Any]:
    ev = state.evidence.model_dump(mode="json")
    spatial = ev.get("spatial") or {}
    meta = ev.get("metadata") or {}
    scene = [r.answer for r in state.model_results
             if getattr(r, "model_name", "") in ("SceneVLM", "GeneralRSVLM") and r.answer]
    return {
        "task": getattr(state.task, "value", state.task),
        "models_used": list(state.selected_models),
        "confidence": state.confidence,
        "statistics": spatial.get("statistics"),
        "detections": [{"label": b.get("label"), "score": b.get("score")} for b in (spatial.get("boxes") or [])][:50],
        "facts": {k: meta[k] for k in WRITER_METADATA_KEYS if k in meta},
        "scene_model_answer": scene[0] if scene else None,
        "warnings": list(state.warnings),
    }


async def apply_answer_writer(state: Any) -> Tuple[str, Optional[str]]:
    facts = state.answer
    if not state.answer or not answer_writer_enabled():
        return "template", facts
    try:
        written = await asyncio.to_thread(write_answer, state.query, evidence_for_writer(state), state.answer)
    except Exception as e:
        logger.warning(f"Answer writer failed: {type(e).__name__}")
        state.add_trace(
            "Answer written from measured evidence",
            status="warning",
            details=f"source=template; writer error: {type(e).__name__}",
        )
        return "template", facts
    state.add_trace(
        "Answer written from measured evidence",
        status="success" if written.source != "template" else "warning",
        details=f"source={written.source}; attempts={written.attempts}",
    )
    state.answer = written.text
    return written.source, facts
