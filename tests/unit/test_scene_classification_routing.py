"""Routing and response-shape tests for `single_image_classification` — the route to the trained
EuroSAT scene classifier (EfficientNet-B0, EuroSAT RGB, Sentinel-2 10 m/px; held-out test accuracy
0.9832 over 4050 samples, project/qna.md Q-041).

No checkpoint and no model I/O. `IntentClassifier.classify_intent` is pure regex over the query, the
capability assertions read the registry, and the workflow is exercised only on its
model-unavailable path and through a stub adapter — never with real weights, so this file stays in
the default (non-`models`) suite alongside tests/unit/test_trained_segmenter_dispatch.py. Live
inference on the real checkpoint belongs in tests/models/.
"""
from typing import Any, Dict, List

import pytest

# Imported first on purpose. `CapabilityRegistry._validate_all` imports backend.app.agent.tools,
# whose package __init__ pulls in the controller -> planner -> capability_registry, so importing
# capability_registry as the very first backend module in a process is a circular import. This is
# pre-existing (tests/unit/test_orchestration_capabilities.py cannot be collected on its own either)
# and out of this change's file scope; importing the tools package first breaks the cycle and lets
# this module run standalone.
import backend.app.agent.tools  # noqa: F401  (import-order fix, see above)
from backend.app.orchestration.capability_registry import capability_registry
from backend.app.orchestration.intent_classifier import IntentClassifier
from backend.app.orchestration.schemas import CapabilityPriority
from backend.app.schemas.models import ModelResult
from backend.app.workflows import scene_classification
from backend.app.workflows.scene_classification import (
    MODEL_KEY,
    STRATEGY,
    STRATEGY_UNAVAILABLE,
    run_scene_classification,
)

TASK = "single_image_classification"


def task_for(query: str, num_inputs: int = 1) -> str:
    return IntentClassifier.classify_intent(
        query, num_inputs=num_inputs, modalities=["optical"] * num_inputs
    ).task


# --- intent: queries that must reach the classifier ------------------------------------------

@pytest.mark.parametrize("query", [
    # The three phrasings this capability exists to serve.
    "what land cover is this?",
    "classify this scene",
    "what type of terrain is this",
    # Variants measured against the real classifier, not guessed.
    "what land cover class is this tile",
    "classify the land cover",
    "what is the land use here",
    "scene classification",
    "land cover classification",
    "what land cover type is shown in this image",
    "classify this image",
    "what kind of terrain is shown",
    "what land cover category does this tile belong to",
])
def test_land_cover_queries_route_to_scene_classification(query):
    assert task_for(query) == TASK


def test_routing_confidence_is_below_grounding_and_captioning():
    """Router confidence, not ML accuracy: it must not outrank the more specific tasks above it."""
    res = IntentClassifier.classify_intent("classify this scene", num_inputs=1)
    assert res.task == TASK
    assert res.routing_confidence == 0.87
    assert res.routing_confidence < IntentClassifier.classify_intent(
        "describe this image", num_inputs=1).routing_confidence
    assert res.routing_confidence < IntentClassifier.classify_intent(
        "mask all roads", num_inputs=1).routing_confidence


# --- intent: the control set that must NOT reach the classifier ------------------------------

@pytest.mark.parametrize("query,num_inputs,expected", [
    # Grounding must keep every mask/box query: this is the hijack the priority choice prevents.
    ("mask all roads", 1, "single_image_grounding"),
    ("segment buildings", 1, "single_image_grounding"),
    ("find the vehicle", 1, "single_image_grounding"),
    ("detect flood extent in the eastern district", 1, "single_image_grounding"),
    ("locate the ship", 1, "single_image_grounding"),
    ("mask all water", 1, "single_image_grounding"),
    # Captioning and VQA.
    ("describe this image", 1, "single_image_caption"),
    ("what does this image show?", 1, "single_image_caption"),
    ("summarise this scene", 1, "single_image_caption"),
    ("how many airplanes are there", 1, "single_image_vqa"),
    ("how many buildings are in this image", 1, "single_image_vqa"),
    # Spectral, SAR and temporal change all return before this check.
    ("compute NDVI", 1, "multispectral_analysis"),
    ("what is the vv backscatter", 1, "sar_analysis"),
    ("what changed between these images", 2, "temporal_change_vqa"),
])
def test_control_set_is_unchanged_by_this_capability(query, num_inputs, expected):
    assert task_for(query, num_inputs) == expected


@pytest.mark.parametrize("query,expected", [
    # A classification verb aimed at an object, not the scene: EuroSAT has no vehicle class.
    ("classify the vehicles in this image", "single_image_vqa"),
    ("classify this warehouse", "single_image_grounding"),
    # "mask"/"segment" is a grounding verb even when the noun is land cover — pixels are wanted.
    ("mask all land cover", "single_image_grounding"),
    ("segment the land cover", "single_image_grounding"),
    # Sub-region, relational, ordinal and temporal scopes a whole-tile label cannot answer.
    ("what land cover is in the north", "single_image_vqa"),
    ("what land cover is around the lake", "single_image_vqa"),
    ("what is the land cover of the first tile", "single_image_vqa"),
    ("what land cover changed here", "single_image_vqa"),
])
def test_scope_guards_leave_queries_on_their_existing_route(query, expected):
    assert task_for(query) == expected


# --- capability definition -------------------------------------------------------------------

def test_capability_is_registered_and_enabled():
    cap = capability_registry.get(TASK)
    assert cap is not None and cap.enabled
    assert cap.required_models == ["eurosat_classifier"]
    assert cap.validation_requirements == {"min_images": 1, "max_images": 1}
    assert cap.workflow == "workflow_scene_classification"
    assert TASK in [c.capability_id for c in capability_registry.list_enabled()]


def test_capability_priority_does_not_outrank_grounding():
    """The load-bearing assertion: "classify this" must never be able to pre-empt "mask all roads"."""
    cap = capability_registry.get(TASK)
    grounding = capability_registry.get("single_image_grounding")
    assert cap.priority < grounding.priority
    assert cap.priority == CapabilityPriority.CAPTION
    # Lower than the generic VQA capability too — the conservative direction if any future resolver
    # ever ranks by priority instead of the matcher's explicit rules.
    assert cap.priority <= capability_registry.get("single_image_vqa").priority


# --- workflow: unavailable model degrades, never crashes -------------------------------------

class _UnavailableAdapter:
    """Stands in for an adapter whose checkpoint is missing. `predict` would be a test failure."""
    checkpoint_path = "checkpoints/eurosat_efficientnet_b0/best_model.pt"
    available = False

    def predict(self, *a: Any, **k: Any) -> Any:  # pragma: no cover - must never be reached
        raise AssertionError("predict() must not be called when the model is unavailable.")


class _StubAdapter:
    """Returns the exact `ModelResult` shape backend/app/ml/adapters/eurosat.py produces, so the
    workflow's response shape is tested without loading 5.3 M parameters onto an 8 GB GPU."""
    checkpoint_path = "checkpoints/eurosat_efficientnet_b0/best_model.pt"
    available = True

    CLASS_NAMES: List[str] = [
        "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
        "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
    ]

    def predict(self, image_or_context: Any = None, **kwargs: Any) -> ModelResult:
        self.top_k_seen = kwargs.get("top_k")
        return ModelResult(
            model_name=MODEL_KEY,
            task="classification",
            answer=(
                "Scene-level land cover is Forest (91.2% confidence). This model assigns one label "
                "to the whole tile and does not localise anything; it was trained on Sentinel-2 "
                "imagery at 10 m/px."
            ),
            confidence=0.912345,
            metadata={
                "label": "Forest",
                "label_index": 1,
                "class_names": self.CLASS_NAMES,
                "probabilities": [0.0] * 10,
                "top_k": [
                    {"label": "Forest", "probability": 0.912345},
                    {"label": "HerbaceousVegetation", "probability": 0.051},
                    {"label": "Pasture", "probability": 0.0121},
                ],
                "scene_level_only": True,
                "input_shape": [64, 64],
                "model_input_size": 224,
                "trained_gsd_m": 10.0,
                "test_accuracy": 0.9832098765432099,
                "test_samples": 4050,
                "checkpoint_epoch": 12,
                "best_val_accuracy": 0.9856,
                "device": "cpu",
                "model_class": "torchvision.efficientnet_b0",
            },
        )


def _patch_adapter(monkeypatch: pytest.MonkeyPatch, adapter: Any) -> None:
    monkeypatch.setattr(
        scene_classification.model_registry, "get_adapter", lambda key: adapter, raising=True
    )


def test_unavailable_model_degrades_with_a_trace_step_and_no_fabricated_label(monkeypatch):
    _patch_adapter(monkeypatch, _UnavailableAdapter())
    out = run_scene_classification("ignored.png", query="what land cover is this?")

    assert out["strategy"] == STRATEGY_UNAVAILABLE
    assert out["label"] is None
    assert out["confidence"] is None
    assert out["top_k"] == []
    assert "NOT_CONFIGURED" in out["answer"]
    assert out["warnings"] and MODEL_KEY in out["warnings"][0]
    steps = [s["step"] for s in out["trace"]]
    assert "eurosat_classifier_unavailable" in steps
    warning = next(s for s in out["trace"] if s["step"] == "eurosat_classifier_unavailable")
    assert warning["status"] == "warning"
    assert warning["details"]["reason"] == "checkpoint_unavailable"


# --- workflow: response shape and the limits the answer must state ---------------------------

@pytest.fixture()
def stub_result(monkeypatch) -> Dict[str, Any]:
    _patch_adapter(monkeypatch, _StubAdapter())
    return run_scene_classification("ignored.png", query="classify this scene")


def test_response_shape(stub_result):
    assert stub_result["task"] == "classification"
    assert stub_result["strategy"] == STRATEGY
    assert stub_result["model"] == MODEL_KEY
    assert stub_result["label"] == "Forest"
    assert stub_result["label_index"] == 1
    assert stub_result["scene_level_only"] is True
    # Structurally absent, present as None so a caller written against the grounding contract
    # reads "no localisation" instead of raising KeyError.
    assert stub_result["selected_box"] is None
    assert stub_result["segmentation_mask"] is None
    assert len(stub_result["class_names"]) == 10


def test_confidence_is_the_adapter_softmax_maximum_not_a_substitute(stub_result):
    assert stub_result["confidence"] == pytest.approx(0.912345)
    assert stub_result["evidence"]["model_confidence"] == pytest.approx(0.912345)
    assert stub_result["confidence"] == stub_result["top_k"][0]["probability"]


def test_top_three_ranked_classes_are_returned_and_quoted(stub_result):
    ranked = stub_result["top_k"]
    assert [r["label"] for r in ranked] == ["Forest", "HerbaceousVegetation", "Pasture"]
    assert [r["probability"] for r in ranked] == sorted(
        (r["probability"] for r in ranked), reverse=True
    )
    # The runners-up reach the user, not only the JSON.
    assert "Next most likely" in stub_result["answer"]
    assert "HerbaceousVegetation" in stub_result["answer"]


def test_answer_states_the_limits_that_are_load_bearing_for_a_demo(stub_result):
    answer = stub_result["answer"]
    # From the adapter's own sentence, kept rather than restated.
    assert "does not localise anything" in answer
    # Stated exactly once: the adapter says it, `_compose_answer` does not repeat it.
    assert answer.count("10 m/px") == 1
    # Added here because the adapter does not say them.
    assert "0.9832" in answer
    assert "4,050 EuroSAT samples" in answer
    assert "64x64 px upsampled to 224 px" in answer
    assert "NOT MEASURED" in answer
    assert stub_result["evidence"]["aerial_accuracy"] == "NOT MEASURED"
    # The adapter's sentence appears exactly once: extended, not duplicated.
    assert answer.count("Scene-level land cover is Forest") == 1


def test_trace_records_the_model_call(stub_result):
    steps = [s["step"] for s in stub_result["trace"]]
    assert steps[0] == "receive_query"
    assert steps.count("call_scene_classifier") == 2  # started + success
    assert "build_classification_evidence" in steps
    assert steps[-1] == "complete_pipeline"
    success = [s for s in stub_result["trace"] if s["step"] == "call_scene_classifier"][-1]
    assert success["status"] == "success"
    assert success["details"]["label"] == "Forest"


def test_query_text_is_provenance_only_because_the_model_takes_no_text(stub_result):
    assert stub_result["evidence"]["query"] == "classify this scene"
    assert stub_result["trace"][0]["details"]["text_conditioned"] is False


def test_top_k_is_passed_through_to_the_adapter(monkeypatch):
    adapter = _StubAdapter()
    _patch_adapter(monkeypatch, adapter)
    run_scene_classification("ignored.png", query="classify this scene", top_k=5)
    assert adapter.top_k_seen == 5
