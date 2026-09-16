"""
The grounding workflow falls back to LocateAnything when Grounding DINO finds nothing.

Plumbing only (mocks, no weights): the fallback was silently skipped for days because the real
adapter could not load, so the trace step it records is the thing under test.
"""

from PIL import Image

import backend.app.workflows.grounding as grounding
from tests.models.test_grounding_workflow import AlwaysVerifies, MockGroundingDINOAdapter, MockSAM2Adapter


class MockLocateAnythingAdapter:
    name = "locate_anything"

    def __init__(self):
        self.calls = []

    def predict(self, image_or_context=None, prompt=None, box_threshold=None, text_threshold=None, **kw):
        self.calls.append(prompt)
        return {"boxes": [{"xyxy": [10.0, 10.0, 30.0, 30.0], "score": 0.5, "label": "vehicle"}]}


def _patch_registry(monkeypatch, available: bool):
    fake = MockLocateAnythingAdapter()
    registry = grounding.model_registry
    real_get = registry.get_adapter
    monkeypatch.setattr(registry, "get_adapter",
                        lambda key: fake if key == "locate_anything" else real_get(key))
    monkeypatch.setattr(registry, "is_model_available",
                        lambda key: available if key == "locate_anything" else True)
    return fake


def _trace(result):
    return {(s["step"], s["status"]) for s in result["trace"]}


def _run(grounding_model="auto"):
    return grounding.run_grounding_pipeline(
        image=Image.new("RGB", (200, 200), color=(128, 128, 128)),
        query="the small vehicle on the top-left",
        grounding_adapter=MockGroundingDINOAdapter(boxes=[]),
        grounding_model=grounding_model,
        sam2_adapter=MockSAM2Adapter(),
        verifier=AlwaysVerifies(),
    )


def test_empty_grounding_dino_falls_back_to_locate_anything(monkeypatch):
    fake = _patch_registry(monkeypatch, available=True)
    result = _run()

    steps = _trace(result)
    assert ("fallback_to_locate_anything", "success") in steps
    assert ("call_locate_anything", "success") in steps
    assert fake.calls, "LocateAnything was never called"
    assert result["selected_box"] == [10.0, 10.0, 30.0, 30.0]


def test_fallback_is_recorded_as_skipped_when_unavailable(monkeypatch):
    fake = _patch_registry(monkeypatch, available=False)
    result = _run()

    assert ("fallback_to_locate_anything", "skipped") in _trace(result)
    assert fake.calls == []


def test_no_fallback_when_a_detector_is_named_explicitly(monkeypatch):
    fake = _patch_registry(monkeypatch, available=True)
    result = _run(grounding_model="grounding_dino")

    assert not any(step == "fallback_to_locate_anything" for step, _ in _trace(result))
    assert fake.calls == []
