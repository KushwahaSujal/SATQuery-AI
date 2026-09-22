"""Q-021: the analyze response carries the written answer and the template facts."""
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
