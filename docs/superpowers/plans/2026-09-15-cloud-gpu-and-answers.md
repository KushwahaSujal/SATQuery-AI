# Cloud GPU + Better Replies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve every SatQuery AI model from a free Modal T4 GPU behind an API key, and replace one- or two-word replies with grounded answers written from measured evidence.

**Architecture:** The existing FastAPI backend is deployed unchanged as a Modal ASGI app (weights and HF cache on a Modal Volume, Supabase for the database). The laptop runs only the Next.js frontend, which stores the API URL and key in the browser. A scene model (Qwen3-VL-4B, 4-bit) replaces BLIP for VQA and captions; after every pipeline run, an answer writer asks Gemini, then NVIDIA NIM, to phrase the answer from the evidence JSON, rejects any answer containing a number not in the evidence, and otherwise keeps the template answer.

**Tech Stack:** Python 3.11, FastAPI/Starlette, httpx, transformers 5.x + bitsandbytes, Modal, Next.js 16 / React / TypeScript, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-15-cloud-gpu-and-answers-design.md`

## Global Constraints

- Branch `prototype`; run commands from `/home/natsu/dev/isro`; Python is `.venv/bin/python`.
- Cloud GPU: Modal `gpu="T4"` by default, overridable with `SATQUERY_MODAL_GPU` (fallback `L4`).
- Answer providers, in order: Gemini (`https://generativelanguage.googleapis.com/v1beta/openai`, key `GEMINI_API_KEY`, model `GEMINI_MODEL` default `gemini-2.5-flash`) → NVIDIA NIM (`https://integrate.api.nvidia.com/v1`, key `NVIDIA_API_KEY`, model `NVIDIA_MODEL` default `meta/llama-3.3-70b-instruct`) → template answer. No other providers.
- Writer runs only when `SATQUERY_ANSWER_WRITER=on`. Provider timeout 8 s.
- API keys: env `SATQUERY_API_KEYS` (comma-separated). Accepted as `Authorization: Bearer <key>`, `X-API-Key: <key>`, or `?key=<key>`. Empty → auth disabled. `/api/health`, `/docs`, `/redoc`, `/openapi.json` stay open.
- CORS origins override: env `SATQUERY_CORS_ORIGINS` (comma-separated).
- Never send images to the answer writer. Never commit keys, `.env`, or `deploy/.env.modal`.
- Every change that spans > 3 files, touches routing/model registry, or is demo-claimed gets a `project/qna.md` entry (append-only, measured numbers).
- Commit trailer:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01XxouHLVW9DnLfqaBPtP5PS
  ```
- Stop the local uvicorn server before running `pytest` (both need the 8 GB GPU).

---

### Task 1: API-key middleware and configurable CORS

**Files:**
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py` (the `app.add_middleware(CORSMiddleware, ...)` block, ~line 42)
- Modify: `backend/app/config.py` (env override block, after the `SATQUERY_RESULTS_DIR` override, ~line 262)
- Test: `tests/unit/test_api_key_auth.py`

**Interfaces:**
- Produces: `ApiKeyMiddleware` (Starlette middleware), `configured_keys() -> set[str]`.

- [ ] **Step 1: Write the failing test**

```python
"""Q-020: API keys for the cloud backend."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MISSING = "/api/results/q020-no-such-job"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_no_keys_configured_leaves_api_open(client, monkeypatch):
    monkeypatch.delenv("SATQUERY_API_KEYS", raising=False)
    assert client.get(MISSING).status_code == 404


@pytest.mark.parametrize("how", ["bearer", "header", "query"])
def test_valid_key_in_any_accepted_form_passes(client, monkeypatch, how):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one, k-two")
    if how == "bearer":
        r = client.get(MISSING, headers={"Authorization": "Bearer k-two"})
    elif how == "header":
        r = client.get(MISSING, headers={"X-API-Key": "k-one"})
    else:
        r = client.get(f"{MISSING}?key=k-one")
    assert r.status_code == 404


def test_missing_or_wrong_key_is_401_with_cors_header(client, monkeypatch):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one")
    origin = {"Origin": "http://localhost:3000"}
    for headers in (origin, {**origin, "Authorization": "Bearer nope"}):
        r = client.get(MISSING, headers=headers)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_health_stays_open_with_keys(client, monkeypatch):
    monkeypatch.setenv("SATQUERY_API_KEYS", "k-one")
    assert client.get("/api/health").status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_api_key_auth.py -q -p no:cacheprovider`
Expected: FAIL — `test_missing_or_wrong_key_is_401_with_cors_header` gets 404 instead of 401.

- [ ] **Step 3: Write the middleware**

`backend/app/api/auth.py`:

```python
"""API keys for the hosted backend (Q-020). No keys configured means auth is off, as for local runs."""
import hmac
import os
from typing import Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

OPEN_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json"}


def configured_keys() -> Set[str]:
    return {k.strip() for k in os.getenv("SATQUERY_API_KEYS", "").split(",") if k.strip()}


def _presented_key(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # <video src> and download links cannot send headers, so media GETs pass the key as ?key=.
    return request.headers.get("x-api-key") or request.query_params.get("key")


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        keys = configured_keys()
        if not keys or request.method == "OPTIONS" or request.url.path in OPEN_PATHS:
            return await call_next(request)
        presented = _presented_key(request)
        if presented and any(hmac.compare_digest(presented, k) for k in keys):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid API key.", "details": {}}},
        )
```

In `backend/app/main.py`, directly **above** the existing `app.add_middleware(CORSMiddleware, ...)` call, add (middleware added earlier sits inside CORS, so 401 responses still carry CORS headers):

```python
from backend.app.api.auth import ApiKeyMiddleware

app.add_middleware(ApiKeyMiddleware)
```

In `backend/app/config.py`, after the `SATQUERY_RESULTS_DIR` override, add:

```python
        if os.getenv("SATQUERY_CORS_ORIGINS"):
            self.app.cors_origins = [o.strip() for o in os.getenv("SATQUERY_CORS_ORIGINS").split(",") if o.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_api_key_auth.py -q -p no:cacheprovider`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/auth.py backend/app/main.py backend/app/config.py tests/unit/test_api_key_auth.py
git commit -m "feat(api): API-key middleware and SATQUERY_CORS_ORIGINS for the hosted backend"
```

---

### Task 2: Video results without a database record

**Files:**
- Modify: `backend/app/api/v1/endpoints/video.py` (`get_video_analysis_result`, the `video_rec = await VideoRepository.get_video_by_job_id(...)` block)
- Test: `tests/unit/test_video_result_fallback.py`

**Interfaces:**
- Consumes: `artifact_manager.load_result_json(job_id)` (existing), video `result.json` written by `POST /api/video/analyze` (Q-017).

- [ ] **Step 1: Write the failing test**

```python
"""Q-020: GET /api/video/{id} is served from result.json when the database has no record."""
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app.artifacts.manager import artifact_manager
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_video_job_without_db_record_is_served_from_result_json(client):
    job = "q020-video-fallback"
    artifact_manager.save_result_json(job, {
        "job_id": job, "status": "COMPLETED", "task": "video_grounding",
        "workflow_id": "workflow_video_analysis", "workflow_reason": "Detected and flagged 1 important moment(s).",
        "video_metadata": {"filename": "x.mp4", "duration_sec": 30.16, "fps": 25.0, "width": 768, "height": 432,
                           "frame_count": 754, "codec": "h264"},
        "flags": [{"flag_id": "flag_1", "start_timestamp": 15.36, "end_timestamp": 18.72, "start_frame": 192,
                   "end_frame": 234, "peak_frame": 228, "label": "red car", "reason": "test", "event_score": 0.89,
                   "metadata": {"track": [{"t": 15.36, "frame": 192, "box_2d": [0.1, 0.2, 0.3, 0.4], "rgb": [120, 39, 53]}]}}],
        "models_used": ["grounding_dino", "sam2"], "execution_trace": [], "warnings": [], "errors": [], "artifacts": {},
    })
    try:
        r = client.get(f"/api/video/{job}")
        assert r.status_code == 200
        body = r.json()
        assert body["flags"][0]["end_timestamp"] == 18.72
        assert body["flags"][0]["metadata"]["track"][0]["rgb"] == [120, 39, 53]
    finally:
        shutil.rmtree(artifact_manager.get_job_dir(job), ignore_errors=True)


def test_unknown_video_job_is_still_404(client):
    assert client.get("/api/video/q020-no-such-video").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_video_result_fallback.py -q -p no:cacheprovider`
Expected: FAIL — first test gets 404.

- [ ] **Step 3: Implement the fallback**

Replace, in `get_video_analysis_result`:

```python
    video_rec = await VideoRepository.get_video_by_job_id(db, job_id)
    if not video_rec:
        raise JobNotFoundError(
```

with:

```python
    video_rec = None
    try:
        video_rec = await VideoRepository.get_video_by_job_id(db, job_id)
    except Exception as e:
        logger.warning(f"Video DB lookup failed for '{job_id}': {e}")
    if not video_rec:
        # The hosted backend may run without the database; the analyze endpoint also writes result.json (Q-017).
        saved = artifact_manager.load_result_json(job_id)
        if saved and "flags" in saved and "video_metadata" in saved:
            return VideoAnalysisResponse(**saved)
        raise JobNotFoundError(
```

(The rest of the `raise JobNotFoundError(...)` call is unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_video_result_fallback.py -q -p no:cacheprovider`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/video.py tests/unit/test_video_result_fallback.py
git commit -m "fix(video): serve GET /api/video/{id} from result.json when the database has no record"
```

---

### Task 3: Answer writer (Gemini → NVIDIA → template) with number guard

**Files:**
- Create: `backend/app/answers/__init__.py` (empty)
- Create: `backend/app/answers/writer.py`
- Modify: `tests/conftest.py` (force the writer off for the test suite)
- Test: `tests/unit/test_answer_writer.py`

**Interfaces:**
- Produces:
  - `WrittenAnswer(text: str, source: str, attempts: list[dict])` dataclass; `source` is `"<provider>:<model>"` or `"template"`.
  - `numbers_grounded(answer: str, evidence_text: str) -> bool`
  - `write_answer(query: str, evidence: dict, template_answer: str, providers=DEFAULT_PROVIDERS, http: httpx.Client | None = None, timeout: float = 8.0) -> WrittenAnswer`
  - `answer_writer_enabled() -> bool`
  - `evidence_for_writer(state) -> dict`
  - `async apply_answer_writer(state) -> tuple[str, str | None]` — returns `(answer_source, answer_facts)` and replaces `state.answer` when a provider succeeds.

- [ ] **Step 1: Force the writer off in tests**

In `tests/conftest.py`, directly after `import os`, add:

```python
# The answer writer calls external LLM APIs; tests that need it switch it on with monkeypatch.
os.environ["SATQUERY_ANSWER_WRITER"] = "off"
```

- [ ] **Step 2: Write the failing test**

```python
"""Q-020: answers written from measured evidence, with a guard against invented numbers."""
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_answer_writer.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.answers'`.

- [ ] **Step 4: Write the implementation**

`backend/app/answers/__init__.py`: empty file.

`backend/app/answers/writer.py`:

```python
"""
Final-answer writer (Q-020). The pipeline's template answer is built from measurements; an LLM rephrases it for the
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
    written = await asyncio.to_thread(write_answer, state.query, evidence_for_writer(state), state.answer)
    state.add_trace(
        "Answer written from measured evidence",
        status="success" if written.source != "template" else "warning",
        details=f"source={written.source}; attempts={written.attempts}",
    )
    state.answer = written.text
    return written.source, facts
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_answer_writer.py -q -p no:cacheprovider`
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/answers tests/unit/test_answer_writer.py tests/conftest.py
git commit -m "feat(answers): write final answers from evidence via Gemini then NVIDIA, with a number guard"
```

---

### Task 4: Wire the writer into the pipeline response

**Files:**
- Modify: `backend/app/schemas/responses.py` (`AnalyzeResponse`, after `answer: Optional[str] = None`)
- Modify: `backend/app/agent/controller.py` (`run_pipeline`, immediately before `response = AnalyzeResponse(`)
- Modify: `frontend/src/lib/types.ts` (`AnalysisResult`, after `answer?: string;`)
- Modify: `frontend/src/components/results/ResultsPanel.tsx` (answer `GlowCard`)
- Test: `tests/unit/test_answer_writer_wiring.py`

**Interfaces:**
- Consumes: `apply_answer_writer(state) -> (answer_source, answer_facts)` from Task 3.
- Produces: `AnalyzeResponse.answer_source: str = "template"`, `AnalyzeResponse.answer_facts: Optional[str] = None`; same optional fields on the TS `AnalysisResult`.

- [ ] **Step 1: Write the failing test**

```python
"""Q-020: the analyze response carries the written answer and the template facts."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.agent import controller
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_analyze_response_has_answer_source_and_facts(client, monkeypatch):
    async def fake_writer(state):
        facts = state.answer
        state.answer = "Written answer."
        return "gemini:test", facts

    monkeypatch.setattr(controller, "apply_answer_writer", fake_writer)
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (40, 120, 40)).save(buf, format="PNG")
    up = client.post("/api/upload", files={"files": ("q020.png", buf.getvalue(), "image/png")}).json()
    r = client.post("/api/analyze", json={"query": "compute NDVI for this scene", "image_filenames": ["q020.png"],
                                           "request_id": up["request_id"]})
    body = r.json()
    assert r.status_code == 200
    assert body["answer"] == "Written answer."
    assert body["answer_source"] == "gemini:test"
    assert body["answer_facts"] and body["answer_facts"] != "Written answer."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_answer_writer_wiring.py -q -p no:cacheprovider`
Expected: FAIL — `AttributeError: module 'backend.app.agent.controller' has no attribute 'apply_answer_writer'`.

- [ ] **Step 3: Implement**

`backend/app/schemas/responses.py`, in `AnalyzeResponse` after `answer: Optional[str] = None`:

```python
    answer_source: str = "template"  # "<provider>:<model>" when written by the answer writer (Q-020)
    answer_facts: Optional[str] = None  # the measured template answer the written answer was based on
```

`backend/app/agent/controller.py`: add to the imports at the top:

```python
from backend.app.answers.writer import apply_answer_writer
```

and immediately before `response = AnalyzeResponse(` add:

```python
        answer_source, answer_facts = "template", state.answer
        if state.status != JobStatus.FAILED:
            answer_source, answer_facts = await apply_answer_writer(state)
```

and add two keyword arguments to the `AnalyzeResponse(...)` call, after `answer=state.answer,`:

```python
            answer_source=answer_source,
            answer_facts=answer_facts,
```

`frontend/src/lib/types.ts`, in `AnalysisResult` after `answer?: string;`:

```ts
  answer_source?: string;
  answer_facts?: string;
```

`frontend/src/components/results/ResultsPanel.tsx`: replace the answer `GlowCard` block

```tsx
                  <GlowCard className="border-l-2 border-l-[var(--accent)]">
                    <p className="text-xs text-[var(--t1)] leading-relaxed m-0">
                      {result.answer}
                    </p>
                  </GlowCard>
```

with:

```tsx
                  <GlowCard className="border-l-2 border-l-[var(--accent)]">
                    <p className="text-xs text-[var(--t1)] leading-relaxed m-0">
                      {result.answer}
                    </p>
                    <p className="font-mono-data text-[10px] text-[var(--t4)] mt-2 mb-0" title={result.answer_facts}>
                      {result.answer_source && result.answer_source !== "template"
                        ? `Written by ${result.answer_source} from measured evidence`
                        : "Measured answer"}
                    </p>
                  </GlowCard>
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/unit/test_answer_writer_wiring.py tests/unit/test_answer_writer.py -q -p no:cacheprovider`
Expected: 9 passed.
Run: `cd frontend && npx tsc --noEmit && npx eslint src/components/results/ResultsPanel.tsx`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/responses.py backend/app/agent/controller.py tests/unit/test_answer_writer_wiring.py frontend/src/lib/types.ts frontend/src/components/results/ResultsPanel.tsx
git commit -m "feat(answers): return answer_source and answer_facts; show the answer's source in the results panel"
```

---

### Task 5: BLIP baseline on VRSBench (before switching models)

**Files:**
- Create: `scripts/eval_scene_vlm_vrsbench.py`
- Test: `tests/unit/test_eval_scene_vlm_metrics.py`
- Output: `results/evaluations/scene_vlm_vrsbench_general_rs_vlm_20260915.json`

**Interfaces:**
- Produces: `vqa_correct(pred: str, gt: str) -> bool`, `rouge_l(pred: str, ref: str) -> float`, CLI `--adapter {general_rs_vlm,scene_vlm} --n 200 --seed 0`.

- [ ] **Step 1: Write the failing test**

```python
from scripts.eval_scene_vlm_vrsbench import rouge_l, vqa_correct


def test_vqa_correct_normalises_case_punctuation_and_articles():
    assert vqa_correct("Yellow.", "yellow")
    assert vqa_correct("The buses are yellow.", "Yellow")
    assert not vqa_correct("Red", "yellow")
    assert not vqa_correct("yellowish", "yellow")


def test_rouge_l_bounds():
    assert rouge_l("a b c", "a b c") == 1.0
    assert rouge_l("", "a") == 0.0
    assert 0.0 < rouge_l("large yellow buses parked", "a group of large yellow buses") < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_eval_scene_vlm_metrics.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.eval_scene_vlm_vrsbench'`.

- [ ] **Step 3: Write the script**

`scripts/eval_scene_vlm_vrsbench.py`:

```python
"""Scene VLM on VRSBench val: VQA accuracy and caption ROUGE-L on a fixed random subset (Q-020)."""
import argparse
import json
import random
import re
import string
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("datasets/raw/vrsbench")
IMAGES = ROOT / "images" / "Images_val"
ARTICLES = {"a", "an", "the"}


def norm(s: str) -> str:
    s = (s or "").lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(w for w in s.split() if w not in ARTICLES)


def vqa_correct(pred: str, gt: str) -> bool:
    p, g = norm(pred), norm(gt)
    return bool(g) and (p == g or re.search(rf"\b{re.escape(g)}\b", p) is not None)


def rouge_l(pred: str, ref: str) -> float:
    a, b = norm(pred).split(), norm(ref).split()
    if not a or not b:
        return 0.0
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a)):
        for j in range(len(b)):
            dp[i + 1][j + 1] = dp[i][j] + 1 if a[i] == b[j] else max(dp[i][j + 1], dp[i + 1][j])
    lcs = dp[-1][-1]
    if lcs == 0:
        return 0.0
    p, r = lcs / len(a), lcs / len(b)
    return 2 * p * r / (p + r)


def sample(path: Path, n: int, seed: int):
    rows = [r for r in json.load(open(path)) if (IMAGES / r["image_id"]).exists()]
    return random.Random(seed).sample(rows, min(n, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", choices=["general_rs_vlm", "scene_vlm"], required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    from PIL import Image
    from backend.app.ml.registry import model_registry

    adapter = model_registry.get_adapter(args.adapter)
    t0 = time.time()
    vqa, caps = [], []
    for r in sample(ROOT / "VRSBench_EVAL_vqa.json", args.n, args.seed):
        img = Image.open(IMAGES / r["image_id"]).convert("RGB")
        pred = adapter.predict({"image_pil": img, "query": r["question"]}).answer or ""
        vqa.append({"image": r["image_id"], "type": r["type"], "question": r["question"], "gt": r["ground_truth"],
                    "pred": pred, "correct": vqa_correct(pred, r["ground_truth"])})
    for r in sample(ROOT / "VRSBench_EVAL_Cap.json", args.n, args.seed):
        img = Image.open(IMAGES / r["image_id"]).convert("RGB")
        pred = adapter.predict({"image_pil": img, "query": "Describe the image in detail."}).answer or ""
        caps.append({"image": r["image_id"], "gt": r["ground_truth"], "pred": pred, "rouge_l": rouge_l(pred, r["ground_truth"])})
    secs = time.time() - t0
    out = {
        "adapter": args.adapter, "n": args.n, "seed": args.seed, "measured_at": datetime.now(timezone.utc).isoformat(),
        "vqa_accuracy": sum(v["correct"] for v in vqa) / max(len(vqa), 1),
        "caption_rouge_l": sum(c["rouge_l"] for c in caps) / max(len(caps), 1),
        "caption_mean_words": sum(len(c["pred"].split()) for c in caps) / max(len(caps), 1),
        "secs_per_sample": secs / max(len(vqa) + len(caps), 1),
        "vqa": vqa, "captions": caps,
    }
    dest = Path("results/evaluations") / f"scene_vlm_vrsbench_{args.adapter}_{datetime.now():%Y%m%d}.json"
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("vqa", "captions")}, indent=1), "->", dest)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the unit test**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_eval_scene_vlm_metrics.py -q -p no:cacheprovider`
Expected: 2 passed.

- [ ] **Step 5: Measure the BLIP baseline** (stop the local server first)

Run: `PYTHONPATH=. .venv/bin/python scripts/eval_scene_vlm_vrsbench.py --adapter general_rs_vlm --n 200`
Expected: prints `vqa_accuracy`, `caption_rouge_l`, `caption_mean_words` and writes the JSON. Record the numbers.

- [ ] **Step 6: Commit**

```bash
git add scripts/eval_scene_vlm_vrsbench.py tests/unit/test_eval_scene_vlm_metrics.py
git commit -m "test(eval): VRSBench VQA/caption scoring script; BLIP baseline measured"
```

(`results/` is gitignored; the measured numbers go into the Q-020 entry in Task 9.)

---

### Task 6: Qwen3-VL scene model, used for VQA and captions when it measures better

**Files:**
- Create: `scripts/prepare_scene_vlm.py`
- Create: `backend/app/ml/adapters/scene_vlm.py`
- Modify: `backend/app/ml/registry.py` (import, `ADAPTER_CLASSES`, metadata dict next to `"general_rs_vlm"`)
- Modify: `configs/models.yaml` (new `scene_vlm` block after `general_rs_vlm`)
- Modify: `backend/app/agent/tools/inference.py` (`run_vqa`, `run_caption`)
- Modify: `backend/requirements.txt` (add `bitsandbytes>=0.45.0`, `accelerate>=1.0.0`)
- Test: `tests/unit/test_scene_vlm_selection.py`

**Interfaces:**
- Consumes: `BaseModelAdapter` (`load_model`, `validate_inputs`, `predict` abstract; `checkpoint_path`, `ensure_available`, `device`).
- Produces: registry key `scene_vlm`, adapter `name == "SceneVLM"` (read by `evidence_for_writer` in Task 3); helper `_scene_adapter() -> tuple[str | None, adapter | None]` in `inference.py`.

- [ ] **Step 1: Install dependencies and prepare the 4-bit model locally**

```bash
.venv/bin/pip install "bitsandbytes>=0.45.0" "accelerate>=1.0.0"
```

`scripts/prepare_scene_vlm.py`:

```python
"""Download Qwen3-VL-4B-Instruct, quantize to 4-bit NF4 and save it pre-quantized (Q-020). Needs a CUDA GPU."""
import argparse
import subprocess
from pathlib import Path

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

ap = argparse.ArgumentParser()
ap.add_argument("--model-id", default="Qwen/Qwen3-VL-4B-Instruct")
ap.add_argument("--out", default="checkpoints/scene_vlm_qwen3vl4b_nf4")
args = ap.parse_args()

quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                           bnb_4bit_use_double_quant=True)
model = AutoModelForImageTextToText.from_pretrained(args.model_id, quantization_config=quant, device_map={"": 0},
                                                    dtype=torch.float16)
AutoProcessor.from_pretrained(args.model_id).save_pretrained(args.out)
model.save_pretrained(args.out)
print(subprocess.run(["du", "-sh", args.out], capture_output=True, text=True).stdout.strip())
```

Run (server stopped): `PYTHONPATH=. .venv/bin/python scripts/prepare_scene_vlm.py`
Expected: prints the saved folder size (spec estimate ~3 GB; record the measured value).

- [ ] **Step 2: Write the failing test**

```python
"""Q-020: VQA and captions use the Qwen scene model when available, BLIP otherwise."""
from PIL import Image

from backend.app.agent.state import AgentState
from backend.app.agent.tools import inference
from backend.app.schemas.models import ModelResult


class FakeAdapter:
    def __init__(self, name):
        self.name, self.calls = name, []

    def predict(self, context):
        self.calls.append(context["query"])
        return ModelResult(model_name=self.name, task="vqa", answer=f"{self.name} answer", confidence=None)


def _state(tmp_path, query):
    p = tmp_path / "scene.png"
    Image.new("RGB", (32, 32), (10, 90, 10)).save(p)
    return AgentState(request_id="q020-scene", query=query, image_paths=[str(p)])


def _registry(monkeypatch, available):
    adapters = {"scene_vlm": FakeAdapter("SceneVLM"), "general_rs_vlm": FakeAdapter("GeneralRSVLM")}
    monkeypatch.setattr(inference.model_registry, "is_model_available", lambda key: key in available)
    monkeypatch.setattr(inference.model_registry, "get_adapter", lambda key: adapters[key])
    return adapters


def test_vqa_prefers_scene_vlm(tmp_path, monkeypatch):
    adapters = _registry(monkeypatch, {"scene_vlm", "general_rs_vlm"})
    state = _state(tmp_path, "What is in this image?")
    inference.run_vqa(state)
    assert state.answer == "SceneVLM answer"
    assert state.selected_models == ["scene_vlm"]
    assert adapters["general_rs_vlm"].calls == []


def test_caption_falls_back_to_blip(tmp_path, monkeypatch):
    _registry(monkeypatch, {"general_rs_vlm"})
    state = _state(tmp_path, "describe this image")
    inference.run_caption(state)
    assert state.answer == "GeneralRSVLM answer"
    assert state.selected_models == ["general_rs_vlm"]


def test_no_scene_model_reports_not_configured(tmp_path, monkeypatch):
    _registry(monkeypatch, set())
    state = _state(tmp_path, "What is in this image?")
    inference.run_vqa(state)
    assert "NOT_CONFIGURED" in state.answer
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_scene_vlm_selection.py -q -p no:cacheprovider`
Expected: FAIL — `test_vqa_prefers_scene_vlm` gets the BLIP answer.

- [ ] **Step 4: Implement adapter, registry, config and selection**

`backend/app/ml/adapters/scene_vlm.py`:

```python
"""Qwen3-VL-4B-Instruct (4-bit NF4) scene model: VQA and captions in full sentences (Q-020)."""
from typing import Any, Dict

import torch
from PIL import Image

from backend.app.exceptions import InferenceError, InvalidInputError
from backend.app.logging import logger
from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult

INSTRUCTION = (
    "You are analysing a satellite or aerial image. Answer only from what is visible. "
    "If something cannot be determined from the image, say so. Answer in one to three sentences."
)


class SceneVLMAdapter(BaseModelAdapter):
    def __init__(self):
        super().__init__("scene_vlm")
        self._processor = None

    def is_available(self) -> bool:
        # Pre-quantized bitsandbytes weights run on CUDA only; never auto-download ~9 GB during a request.
        if not self.config or not self.config.enabled or not torch.cuda.is_available():
            return False
        p = self.checkpoint_path
        return p is not None and p.exists()

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return
        self.ensure_available()
        from transformers import AutoModelForImageTextToText, AutoProcessor
        src = str(self.checkpoint_path)
        try:
            self._processor = AutoProcessor.from_pretrained(src)
            self._model = AutoModelForImageTextToText.from_pretrained(
                src, device_map={"": self.device.index or 0}, dtype=torch.float16
            ).eval()
            self._loaded = True
            logger.info(f"Scene VLM loaded from {src}.")
        except Exception as e:
            raise InferenceError(f"Failed to load Scene VLM: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if not isinstance(context.get("image_pil"), Image.Image):
            raise InvalidInputError("Scene VLM requires 'image_pil'.")

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()
        image = context["image_pil"].convert("RGB")
        image.thumbnail((1024, 1024))
        question = (context.get("query") or "Describe this image.").strip()
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": f"{INSTRUCTION}\n\n{question}"},
        ]}]
        try:
            inputs = self._processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt"
            ).to(self._model.device)
            with torch.inference_mode():
                out = self._model.generate(**inputs, max_new_tokens=200, do_sample=False)
            text = self._processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
        except Exception as e:
            logger.error(f"Scene VLM inference failed: {e}", exc_info=True)
            raise InferenceError(f"Scene VLM inference failed: {e}", model_name=self.name)
        return ModelResult(model_name=self.name, task="vqa", answer=text, confidence=None,
                           metadata={"model_class": "Qwen3-VL-4B-Instruct", "quantization": "bnb-nf4",
                                     "device": str(self.device)})
```

`configs/models.yaml`, after the `general_rs_vlm` block:

```yaml
  scene_vlm:
    name: "SceneVLM"
    version: "qwen3-vl-4b-instruct-nf4"
    task: "vqa"
    supported_tasks:
      - "single_image_vqa"
      - "single_image_caption"
    supported_modalities:
      - "optical"
      - "multispectral"
    input_count: 1
    input_relationship: "single"
    enabled: true
    checkpoint_path: "checkpoints/scene_vlm_qwen3vl4b_nf4"
    model_id: "Qwen/Qwen3-VL-4B-Instruct"
    device: "auto"
    precision: "float16"
```

`backend/app/ml/registry.py`: add `from backend.app.ml.adapters.scene_vlm import SceneVLMAdapter`; add `"scene_vlm": SceneVLMAdapter,` to `ADAPTER_CLASSES`; add next to the `"general_rs_vlm"` metadata entry:

```python
        "scene_vlm": {
            "family": "Qwen3-VL-4B-Instruct (4-bit NF4)",
            "source": "checkpoints/scene_vlm_qwen3vl4b_nf4",
            "license": "Apache-2.0",
            "capabilities": ["single_image_vqa", "scene_understanding", "captioning"],
            "input_requirements": {"image": "RGB (H, W, 3)", "query": "string"},
            "output_schema": {"answer": "string"},
            "device_requirements": {"min_vram_gb": 4.0, "preferred": "cuda"},
        },
```

`backend/app/agent/tools/inference.py`: replace the bodies of `run_vqa` and `run_caption` with:

```python
def _scene_adapter():
    for key in ("scene_vlm", "general_rs_vlm"):
        if model_registry.is_model_available(key):
            return key, model_registry.get_adapter(key)
    return None, None


def _run_scene_model(state: AgentState, question: str, unavailable_msg: str) -> None:
    key, adapter = _scene_adapter()
    if adapter is None:
        state.warnings.append("No scene model (Qwen3-VL or BLIP) is configured on this deployment.")
        state.answer = unavailable_msg
        state.confidence = None
        return
    arr, _ = RasterInspector.read_as_array(state.image_paths[0])
    res = adapter.predict({"image_pil": to_pil_rgb(arr), "query": question})
    state.model_results.append(res)
    state.answer = res.answer
    state.confidence = res.confidence
    if key not in state.selected_models:
        state.selected_models.append(key)
    if res.warnings:
        state.warnings.extend(res.warnings)


@register_tool("run_vqa")
def run_vqa(state: AgentState) -> None:
    _run_scene_model(state, state.query, (
        "Scene question answering is currently NOT_CONFIGURED on this deployment. "
        "Grounding DINO + SAM 2 remain active for detection and segmentation; ChangeFormer and CDVQA for change."
    ))


@register_tool("run_caption")
def run_caption(state: AgentState) -> None:
    _run_scene_model(state, "Describe this image: land cover, main objects and how they are laid out.", (
        "Scene captioning is currently NOT_CONFIGURED on this deployment. "
        "Grounding DINO + SAM 2 remain active for detection and segmentation; ChangeFormer and CDVQA for change."
    ))
```

`backend/requirements.txt`: add lines `bitsandbytes>=0.45.0` and `accelerate>=1.0.0` after `transformers>=4.41.0`.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/unit/test_scene_vlm_selection.py -q -p no:cacheprovider`
Expected: 3 passed.

- [ ] **Step 6: Measure Qwen3-VL and decide**

Run: `PYTHONPATH=. .venv/bin/python scripts/eval_scene_vlm_vrsbench.py --adapter scene_vlm --n 200`
Decision rule (record both result files' numbers in Q-020):
- If `scene_vlm` VQA accuracy ≥ BLIP's **and** caption ROUGE-L > BLIP's → keep `scene_vlm.enabled: true`.
- Otherwise set `scene_vlm.enabled: false` in `configs/models.yaml` (BLIP stays) and say so in Q-020.

- [ ] **Step 7: Full suite and commit**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider`
Expected: all pass (previous 267 + new tests), 1 skipped.

```bash
git add scripts/prepare_scene_vlm.py backend/app/ml/adapters/scene_vlm.py backend/app/ml/registry.py configs/models.yaml backend/app/agent/tools/inference.py backend/requirements.txt tests/unit/test_scene_vlm_selection.py
git commit -m "feat(models): Qwen3-VL-4B scene model for VQA and captions, BLIP as fallback"
```

---

### Task 7: Modal deployment and setup manual

**Files:**
- Create: `deploy/modal_app.py`
- Create: `deploy/.env.modal.example`
- Create: `deploy/README.md` (the manual — content already written; update measured values)
- Modify: `.gitignore` (add `deploy/.env.modal`)

**Interfaces:**
- Consumes: FastAPI `backend.app.main:app`; env `SATQUERY_RESULTS_DIR`, `HF_HOME`, `SATQUERY_API_KEYS`, `DATABASE_URL`, `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `SATQUERY_CORS_ORIGINS`, `SATQUERY_ANSWER_WRITER`.
- Produces: HTTPS URL `https://<workspace>--satquery-ai-api.modal.run`; Modal volumes `satquery-models`, `satquery-results`; function `warm_hf_cache`.

- [ ] **Step 1: Write `deploy/modal_app.py`**

```python
"""
SatQuery AI on Modal (Q-021): the unchanged FastAPI backend on a cloud GPU.
  modal deploy deploy/modal_app.py              # deploy / update
  modal run deploy/modal_app.py::warm_hf_cache  # one-off: download HF models into the volume
Env at deploy time: SATQUERY_MODAL_GPU (default T4), SATQUERY_MIN_CONTAINERS (default 0; 1 keeps it warm).
"""
import os
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
REMOTE = "/root/isro"
GPU = os.environ.get("SATQUERY_MODAL_GPU", "T4")
MIN_CONTAINERS = int(os.environ.get("SATQUERY_MIN_CONTAINERS", "0"))

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0", "ffmpeg")
    .env({"SAM2_BUILD_CUDA": "0"})
    # cu128 wheels still target Turing (T4, sm_75); record the installed torch version in Q-021.
    .pip_install("torch", "torchvision", index_url="https://download.pytorch.org/whl/cu128")
    .pip_install_from_requirements(str(REPO / "backend" / "requirements.txt"))
    .env({"HF_HOME": "/models/hf", "SATQUERY_RESULTS_DIR": "/results", "PYTHONPATH": REMOTE,
          "SATQUERY_ANSWER_WRITER": "on"})
    .run_commands(f"mkdir -p {REMOTE}", f"ln -s /models/checkpoints {REMOTE}/checkpoints")
    .add_local_dir(str(REPO / "backend"), f"{REMOTE}/backend", ignore=["**/__pycache__", "**/*.pyc"])
    .add_local_dir(str(REPO / "configs"), f"{REMOTE}/configs")
)

app = modal.App("satquery-ai")
models = modal.Volume.from_name("satquery-models", create_if_missing=True)
results = modal.Volume.from_name("satquery-results", create_if_missing=True)
secrets = [modal.Secret.from_dotenv(str(REPO / "deploy"), filename=".env.modal")]


@app.function(image=image, gpu=GPU, volumes={"/models": models, "/results": results}, secrets=secrets,
              scaledown_window=300, timeout=900, min_containers=MIN_CONTAINERS, max_containers=1)
@modal.concurrent(max_inputs=4)
@modal.asgi_app()
def api():
    os.chdir(REMOTE)
    from backend.app.main import app as fastapi_app
    return fastapi_app


@app.function(image=image, volumes={"/models": models}, timeout=3600)
def warm_hf_cache():
    from huggingface_hub import snapshot_download
    for repo in ("IDEA-Research/grounding-dino-base", "facebook/sam2.1-hiera-small"):
        print(repo, "->", snapshot_download(repo))
    models.commit()
```

- [ ] **Step 2: Write `deploy/.env.modal.example` and ignore the real file**

```
# Copy to deploy/.env.modal (gitignored) and fill in. Read at `modal deploy` time.
SATQUERY_API_KEYS=make-a-long-random-key
DATABASE_URL=postgresql+asyncpg://...pooler.supabase.com:6543/postgres
GEMINI_API_KEY=
NVIDIA_API_KEY=
SATQUERY_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Append to `.gitignore`: `deploy/.env.modal`

- [ ] **Step 3: Upload weights and deploy** (follow `deploy/README.md` §3–§5)

```bash
.venv/bin/modal volume put satquery-models checkpoints/changeformer/changeformer_v6_levir_levircd256_epoch20_best.pt /checkpoints/changeformer/
.venv/bin/modal volume put satquery-models checkpoints/cdvqa /checkpoints/cdvqa
.venv/bin/modal volume put satquery-models checkpoints/remoteclip /checkpoints/remoteclip
.venv/bin/modal volume put satquery-models checkpoints/dofa /checkpoints/dofa
.venv/bin/modal volume put satquery-models checkpoints/optical_sar /checkpoints/optical_sar
.venv/bin/modal volume put satquery-models checkpoints/bigearthnet /checkpoints/bigearthnet
.venv/bin/modal volume put satquery-models checkpoints/scene_vlm_qwen3vl4b_nf4 /checkpoints/scene_vlm_qwen3vl4b_nf4
.venv/bin/modal run deploy/modal_app.py::warm_hf_cache
.venv/bin/modal deploy deploy/modal_app.py
```

Expected: deploy prints the `api` URL.

- [ ] **Step 4: Smoke-check the cloud API**

```bash
URL=https://<workspace>--satquery-ai-api.modal.run; KEY=$(grep ^SATQUERY_API_KEYS deploy/.env.modal | cut -d= -f2 | cut -d, -f1)
time curl -s "$URL/api/health" | head -c 300; echo
curl -s -o /dev/null -w "no key: %{http_code}\n" "$URL/api/results/none"
curl -s -o /dev/null -w "with key: %{http_code}\n" -H "Authorization: Bearer $KEY" "$URL/api/results/none"
```

Expected: health JSON with `"device":"cuda"` (record cold-start seconds); `no key: 401`; `with key: 404`.
If any model path fails on T4 with a bfloat16 error, redeploy with `SATQUERY_MODAL_GPU=L4 .venv/bin/modal deploy deploy/modal_app.py` and record it.

- [ ] **Step 5: Commit**

```bash
git add deploy/modal_app.py deploy/.env.modal.example deploy/README.md .gitignore
git commit -m "feat(deploy): Modal GPU deployment of the backend with volumes, keys and setup manual"
```

---

### Task 8: Frontend connection settings (API URL + key)

**Files:**
- Create: `frontend/src/lib/connection.ts`
- Create: `frontend/src/components/system/ConnectionPanel.tsx`
- Modify: `frontend/src/lib/api.ts` (`http()` and every `${API_BASE}${...}` URL builder: lines ~18, 103, 149, 210, 211, 229, 236, 239, 242, 248)
- Modify: `frontend/src/app/system/page.tsx` (render `<ConnectionPanel />`)

**Interfaces:**
- Produces: `getApiBase(): string`, `getApiKey(): string | null`, `setConnection(base: string, key: string): void`, `authHeaders(): Record<string, string>`, `mediaUrl(path: string): string`.

- [ ] **Step 1: Write `frontend/src/lib/connection.ts`**

```ts
const BASE_KEY = "satquery.apiBase";
const API_KEY = "satquery.apiKey";
const DEFAULT_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function read(name: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(name);
  } catch {
    return null;
  }
}

export function getApiBase(): string {
  return (read(BASE_KEY) || DEFAULT_BASE).replace(/\/+$/, "");
}

export function getApiKey(): string | null {
  return read(API_KEY);
}

export function setConnection(base: string, key: string): void {
  try {
    window.localStorage.setItem(BASE_KEY, base.trim());
    if (key.trim()) window.localStorage.setItem(API_KEY, key.trim());
    else window.localStorage.removeItem(API_KEY);
  } catch {
    // storage blocked: the defaults keep working for a local backend
  }
}

export function authHeaders(): Record<string, string> {
  const key = getApiKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

/** Absolute URL for media the browser fetches itself (<img>, <video>, downloads), which cannot send headers. */
export function mediaUrl(path: string): string {
  const url = /^https?:\/\//.test(path) ? path : `${getApiBase()}${path}`;
  const key = getApiKey();
  return key ? `${url}${url.includes("?") ? "&" : "?"}key=${encodeURIComponent(key)}` : url;
}
```

- [ ] **Step 2: Route all API traffic through it**

In `frontend/src/lib/api.ts`:
- change the import to `import { endpoints } from "./endpoints";` and add `import { authHeaders, getApiBase, mediaUrl } from "./connection";`
- in `http()`: `fetch(\`${getApiBase()}${path}\`, { ...init, headers: { Accept: "application/json", ...authHeaders(), ...init?.headers } })`
- replace each `` `${API_BASE}${X}` `` with `mediaUrl(X)`, e.g. `mediaUrl(meta.preview_url)`, `mediaUrl(res.video_url || endpoints.videoStream(res.job_id as string))`, `mediaUrl(\`${endpoints.exportLayer(jobId, layerId)}?format=${format}\`)`.

Then run `grep -rn "API_BASE\|fetch(" frontend/src --include=*.ts --include=*.tsx` — the only remaining `fetch(` must be inside `http()`, and `API_BASE` may appear only in `endpoints.ts`. In `frontend/src/app/video/[jobId]/page.tsx`, wrap `f.keyframe_url` as `f.keyframe_url ? mediaUrl(f.keyframe_url) : undefined` (import `mediaUrl` from `@/lib/connection`).

- [ ] **Step 3: Write `frontend/src/components/system/ConnectionPanel.tsx`**

```tsx
"use client";

import { useState } from "react";
import { authHeaders, getApiBase, getApiKey, setConnection } from "@/lib/connection";

type Check = { state: "idle" | "checking" | "waking" | "ok" | "error"; detail?: string };

export default function ConnectionPanel() {
  const [base, setBase] = useState(() => getApiBase());
  const [key, setKey] = useState(() => getApiKey() ?? "");
  const [check, setCheck] = useState<Check>({ state: "idle" });

  const save = async () => {
    setConnection(base, key);
    setCheck({ state: "checking" });
    const started = performance.now();
    const waking = setTimeout(() => setCheck({ state: "waking" }), 3000);
    try {
      const r = await fetch(`${getApiBase()}/api/results/connection-check`, { headers: authHeaders() });
      const secs = ((performance.now() - started) / 1000).toFixed(1);
      if (r.status === 401) setCheck({ state: "error", detail: "API key rejected" });
      else setCheck({ state: "ok", detail: `reachable in ${secs}s` });
    } catch {
      setCheck({ state: "error", detail: `backend unreachable at ${getApiBase()}` });
    } finally {
      clearTimeout(waking);
    }
  };

  const status =
    check.state === "waking" ? "Waking GPU (~60 s)…"
    : check.state === "checking" ? "Checking…"
    : check.state === "ok" ? `Connected · ${check.detail}`
    : check.state === "error" ? `Not connected · ${check.detail}`
    : "";

  return (
    <div className="border border-[#1a1a1a] rounded p-4 space-y-2" data-testid="connection-panel">
      <p className="font-mono-data text-[11px] text-[#737373] m-0">Backend connection</p>
      <input className="w-full bg-transparent border border-[#262626] rounded px-2 py-1 font-mono-data text-[11px] text-[#d4d4d4]"
             value={base} onChange={(e) => setBase(e.target.value)} placeholder="https://…modal.run or http://localhost:8000" />
      <input className="w-full bg-transparent border border-[#262626] rounded px-2 py-1 font-mono-data text-[11px] text-[#d4d4d4]"
             value={key} onChange={(e) => setKey(e.target.value)} type="password" placeholder="API key (empty for local)" />
      <div className="flex items-center gap-3">
        <button type="button" onClick={save}
                className="font-mono-data text-[11px] border border-[#262626] rounded px-2.5 py-1 text-[#d4d4d4] hover:border-[#404040]">
          Save &amp; test
        </button>
        <span className="font-mono-data text-[11px] text-[#a3a3a3]" data-testid="connection-status">{status}</span>
      </div>
    </div>
  );
}
```

(The check uses `/api/results/connection-check`: 404 means reachable and authorised, 401 means a wrong key.)

- [ ] **Step 4: Render it on `/system`**

In `frontend/src/app/system/page.tsx` add `import ConnectionPanel from "@/components/system/ConnectionPanel";` and render `<ConnectionPanel />` as the first child of the outermost element returned by `SystemPage`.

- [ ] **Step 5: Verify**

Run: `cd frontend && npx tsc --noEmit && npx eslint src/lib src/components/system src/app/system && npx next build`
Expected: exit 0.
With the local backend started with `SATQUERY_API_KEYS=test-key`: Playwright → `/system`, enter `http://localhost:8000` + `test-key`, Save → status "Connected"; wrong key → "API key rejected"; then run a masking query on the home page and confirm the overlay image, video playback (`?key=`) and Download Results all load (no 401 in `browser_network_requests`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/connection.ts frontend/src/lib/api.ts frontend/src/components/system/ConnectionPanel.tsx frontend/src/app/system/page.tsx "frontend/src/app/video/[jobId]/page.tsx"
git commit -m "feat(frontend): configurable backend URL and API key for the hosted GPU"
```

---

### Task 9: End-to-end on the cloud, measurements, record, push

**Files:**
- Create: `scripts/cloud_smoke.py`
- Modify: `project/qna.md` (append Q-020 answer writer + scene model; Q-021 cloud deployment)
- Modify: `deploy/README.md` (fill measured cold/warm times)

- [ ] **Step 1: Write `scripts/cloud_smoke.py`**

```python
"""Runs the demo prompts against a SatQuery backend and records latency and answer sources (Q-021)."""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

BASE, KEY = sys.argv[1].rstrip("/"), (sys.argv[2] if len(sys.argv) > 2 else "")
H = {"Authorization": f"Bearer {KEY}"} if KEY else {}
R = Path("demo_resources")
CASES = [
    ("image", [R / "1_masking/airport_airplanes__P0173_0003.png"], "mask airplanes"),
    ("image", [R / "1_masking/suburb_white_houses_red_cars__P0897_0048.png"], "mask white houses"),
    ("image", [R / "1_masking/street_houses_trees_cars__P0725_0005.png"], "what is in this image?"),
    ("image", [R / "2_change_detection/levir_scene_100/before.png", R / "2_change_detection/levir_scene_100/after.png"],
     "has any new building been constructed?"),
    ("video", [R / "4_video/real_aerial_footage.mp4"], "find red car"),
]
rows = []
with httpx.Client(timeout=900, headers=H) as c:
    t = time.time(); c.get(f"{BASE}/api/health").raise_for_status(); rows.append({"case": "health", "secs": round(time.time() - t, 1)})
    for kind, files, q in CASES:
        t = time.time()
        if kind == "video":
            d = c.post(f"{BASE}/api/video/analyze", files={"file": (files[0].name, files[0].read_bytes(), "video/mp4")}, data={"query": q}).json()
            job, summary = d["job_id"], {"flags": [(f["start_timestamp"], f["end_timestamp"]) for f in d.get("flags", [])]}
        else:
            up = c.post(f"{BASE}/api/upload", files=[("files", (f.name, f.read_bytes())) for f in files]).json()
            d = c.post(f"{BASE}/api/analyze", json={"query": q, "image_filenames": [f.name for f in files], "request_id": up["request_id"]}).json()
            job, summary = d["request_id"], {"answer": d.get("answer"), "answer_source": d.get("answer_source"), "status": d.get("status")}
        z = c.get(f"{BASE}/api/results/{job}/download")
        rows.append({"case": q, "secs": round(time.time() - t, 1), "zip_status": z.status_code, "zip_bytes": len(z.content), **summary})
        print(json.dumps(rows[-1])[:300])
out = Path("results/evaluations") / f"cloud_smoke_{datetime.now():%Y%m%d_%H%M}.json"
out.write_text(json.dumps({"base": BASE, "rows": rows}, indent=1))
print("->", out)
```

- [ ] **Step 2: Run against the cloud from a machine with the GPU hidden**

```bash
CUDA_VISIBLE_DEVICES="" .venv/bin/python scripts/cloud_smoke.py "$URL" "$KEY"      # cold (after 5+ min idle)
CUDA_VISIBLE_DEVICES="" .venv/bin/python scripts/cloud_smoke.py "$URL" "$KEY"      # warm
```

Expected: every case `status` COMPLETED (video: 1 flag near 15.36–18.72 s), `zip_status` 200, `answer_source` not `template` for at least the change question when keys are set. Record cold and warm `secs`.

- [ ] **Step 3: UI check against the cloud**

Stop the local backend. `cd frontend && npx next start -p 3000`; in Playwright set `/system` connection to the Modal URL + key; run "mask airplanes" and "find red car"; screenshot the overlay, the tracking box, and click Download Results.

- [ ] **Step 4: Record and push**

Append Q-020 (writer + scene model: BLIP vs Qwen numbers, number-guard behaviour, provider attempts seen live) and Q-021 (Modal: volume size measured with `modal volume ls satquery-models /checkpoints`, cold/warm latency, GPU used, credit used from the Modal dashboard) to `project/qna.md`; fill measured values in `deploy/README.md`.

```bash
.venv/bin/python -m pytest tests -q -p no:cacheprovider
git add scripts/cloud_smoke.py project/qna.md deploy/README.md
git commit -m "test(deploy): cloud smoke run; record Q-020 and Q-021"
git push origin prototype
```
