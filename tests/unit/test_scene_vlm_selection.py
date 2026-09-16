"""Q-021: VQA and captions use the Qwen scene model when available, BLIP otherwise."""
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
