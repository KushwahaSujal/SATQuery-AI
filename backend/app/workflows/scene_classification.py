"""Scene-level land-cover classification — the executable path behind `single_image_classification`.

Model: `eurosat_classifier` — torchvision EfficientNet-B0 with a 10-way head, trained by Ayushman on
EuroSAT RGB. Sensor and scale: Sentinel-2, 10 m/px, 64x64 tiles bilinearly upsampled to 224 px.
Measured on the delivered held-out test split: accuracy 0.9832, balanced accuracy 0.9824, macro
ROC-AUC 0.9996 over 4050 samples (project/qna.md Q-041, docs/models/eurosat/evaluation/). Accuracy
on sub-metre aerial photography is NOT MEASURED. The model localises nothing: one label per tile,
no mask and no box.

Why this is its own workflow rather than a branch of the grounding pipeline: `run_grounding_pipeline`
(backend/app/workflows/grounding.py) returns a mask or a box, and every consumer of its
`segmentation_mask` treats that field as one binary mask. A scene label is neither, which is the same
argument backend/app/workflows/trained_segmenter.py makes for refusing to route the 7-class
land-cover *segmenter* through that pipeline, and which
backend/app/ml/adapters/eurosat.py states in its own docstring. So the classifier gets its own
capability (`single_image_classification`, backend/app/orchestration/capability_registry.py) reached
through its own intent (`IntentClassifier.SCENE_CLASSIFICATION_PATTERNS`,
backend/app/orchestration/intent_classifier.py).

This module provides:
  - `run_scene_classification`: loads the adapter, runs one forward pass, and returns a structured
    result plus its own observable trace, shaped like `run_grounding_pipeline`'s return.
  - Graceful degradation: when the checkpoint is absent the same function returns
    `strategy="eurosat_classifier_unavailable"` with `label=None`, `confidence=None` and a warning
    trace step — mirroring `run_grounding_pipeline`'s `trained_segmenter_unavailable` handling
    (grounding.py ~line 238). It never raises for a missing checkpoint, and never invents a label or
    a confidence.

Execution wiring (deliberate gap): `CapabilityMatcher.match`, `DependencyGraph`'s DAG branches and
the agent tool registry all live outside this change's file scope, so as of this commit the
capability is registered and this module is callable, but no DAG executes it yet — the intent and the
capability are routable, the tool is not. `CapabilityRegistry._validate_all` logs exactly that gap on
every boot, which is the D-104/D-105 mechanism (project/decisions.md) working as designed rather than
an invisible hole. Routing is measured in tests/unit/test_scene_classification_routing.py.
"""
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.exceptions import InferenceError
from backend.app.logging import logger
from backend.app.ml.registry import model_registry

#: The only model this workflow can run. Declared as `required_models` on the capability.
MODEL_KEY = "eurosat_classifier"

#: Strategy strings, so this path is traceable and never confusable in logs or evidence with a VLM
#: caption/VQA answer (`run_caption`/`run_vqa`) or with a segmenter mask.
STRATEGY = "eurosat_scene_classifier"
STRATEGY_UNAVAILABLE = "eurosat_classifier_unavailable"

#: Ranked classes reported alongside the winner. Three is what the adapter defaults to and what the
#: answer text quotes; `run_scene_classification(top_k=...)` overrides it.
DEFAULT_TOP_K = 3


def _compose_answer(adapter_answer: str, ranked: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
    """Extends the adapter's own sentence instead of restating it.

    `backend/app/ml/adapters/eurosat.py` already states the label, the real softmax confidence, that
    the model assigns one label to the whole tile and localises nothing, and the 10 m/px training
    GSD. What it does not state, and what a reviewer will ask for, is the ranked runners-up, the
    measured held-out score, the 64x64 -> 224 upsample, and that nothing has been measured on
    sub-metre aerial imagery. Only those are added here, so the two texts do not contradict or
    duplicate each other.
    """
    parts = [adapter_answer.strip()]

    if len(ranked) > 1:
        runners = ", ".join(f"{r['label']} {float(r['probability']) * 100:.1f}%" for r in ranked[1:])
        parts.append(f"Next most likely: {runners}.")

    accuracy = metadata.get("test_accuracy")
    samples = metadata.get("test_samples")
    if accuracy is not None and samples:
        parts.append(
            f"Held-out test accuracy {float(accuracy):.4f} over {int(samples):,} EuroSAT samples "
            f"(project/qna.md Q-041)."
        )

    gsd = metadata.get("trained_gsd_m")
    input_size = int(metadata["model_input_size"]) if metadata.get("model_input_size") else 224
    scale = f"Those training tiles are 64x64 px upsampled to {input_size} px"
    # The adapter's own sentence already gives the GSD; repeat it only if it somehow did not, so the
    # combined text states it exactly once.
    if gsd is not None and f"{float(gsd):g} m/px" not in adapter_answer:
        scale += f", captured at {float(gsd):g} m/px"
    scale += ", and the label describes the whole tile rather than any part of it"
    parts.append(scale)
    parts.append(
        "Accuracy on sub-metre aerial photography is NOT MEASURED. This is a scene-level label only: "
        "for a mask or a bounding box, ask for segmentation or detection instead, because this model "
        "produces neither."
    )
    return " ".join(p if p.endswith((".", "!", "?")) else p + "." for p in parts)


def run_scene_classification(
    image: Any,
    query: str = "",
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """Classifies the land cover of one scene and returns a structured, traced result.

    `image` is anything `backend.app.ml.adapters.eurosat.to_rgb_array` accepts: a PIL image, a path,
    a torch tensor or a numpy array. `query` is carried into the trace and the evidence block for
    provenance only — this model takes no text input, so the query cannot change the answer, and
    pretending otherwise would be a fabricated capability.

    Never raises for a missing checkpoint: an unavailable model returns
    `strategy="eurosat_classifier_unavailable"`, `label=None` and `confidence=None`, with a warning
    trace step, exactly as `run_grounding_pipeline` degrades on `trained_segmenter_unavailable`.
    Inference failures on an *available* model are still raised as `InferenceError`, because a
    checkpoint that loads and then fails is a real fault, not a deployment that lacks a model.
    """
    trace: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    def record_step(
        step_name: str,
        status: str,
        tool: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        trace.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step_name,
            "status": status,
            "tool": tool,
            "details": details or {},
        })

    record_step("receive_query", "success", details={
        "query": query, "top_k": top_k, "text_conditioned": False,
    })

    # Availability, before anything heavy. `is_model_available` only stats the checkpoint file
    # (backend/app/ml/base.py is_available) — it loads no weights.
    checkpoint_path: Optional[Path] = None
    adapter = None
    try:
        adapter = model_registry.get_adapter(MODEL_KEY)
        checkpoint_path = adapter.checkpoint_path
        available = bool(adapter.available)
    except Exception as e:  # unregistered key, or an adapter that cannot even be constructed
        logger.warning(f"{MODEL_KEY} could not be resolved from the model registry: {e}")
        available = False

    if not available:
        record_step("eurosat_classifier_unavailable", "warning", details={
            "model": MODEL_KEY,
            "reason": "checkpoint_unavailable",
            "expected_checkpoint": str(checkpoint_path) if checkpoint_path else None,
            "fallback": "none",
        })
        record_step("complete_pipeline", "success", details={
            "elapsed_seconds": round(time.perf_counter() - t0, 3)
        })
        return {
            "task": "classification",
            "answer": (
                "Scene-level land-cover classification is currently NOT_CONFIGURED on this "
                f"deployment: the {MODEL_KEY} checkpoint was not found at "
                f"{checkpoint_path if checkpoint_path else 'its configured path'}. No label and no "
                "confidence are reported rather than guessed ones."
            ),
            "label": None,
            "label_index": None,
            "confidence": None,
            "top_k": [],
            "class_names": [],
            "probabilities": [],
            "scene_level_only": True,
            "selected_box": None,
            "segmentation_mask": None,
            "strategy": STRATEGY_UNAVAILABLE,
            "model": MODEL_KEY,
            "evidence": {
                "model_key": MODEL_KEY,
                "checkpoint": str(checkpoint_path) if checkpoint_path else None,
                "available": False,
                "query": query,
            },
            "warnings": [
                f"{MODEL_KEY} is not available on this deployment; no land-cover label was produced."
            ],
            "trace": trace,
        }

    record_step("call_scene_classifier", "started", tool=type(adapter).__name__, details={
        "model": MODEL_KEY, "checkpoint": str(checkpoint_path), "top_k": top_k,
    })
    try:
        result = adapter.predict(image, top_k=top_k)
    except Exception as e:
        record_step("call_scene_classifier", "error", tool=type(adapter).__name__,
                    details={"error": str(e)})
        raise InferenceError(
            f"{type(adapter).__name__} inference error: {e}", model_name=MODEL_KEY
        ) from e

    metadata: Dict[str, Any] = dict(result.metadata or {})
    ranked: List[Dict[str, Any]] = list(metadata.get("top_k") or [])
    label = metadata.get("label")
    # The real softmax maximum from the adapter. Never substituted, never rounded up to a
    # presentable number: a fabricated confidence is the one thing this response must not contain.
    confidence = float(result.confidence) if result.confidence is not None else None

    record_step("call_scene_classifier", "success", tool=type(adapter).__name__, details={
        "label": label,
        "confidence": confidence,
        "top_k": ranked,
        "class_count": len(metadata.get("class_names") or []),
        "device": metadata.get("device"),
    })

    answer = _compose_answer(result.answer or "", ranked, metadata)

    evidence: Dict[str, Any] = {
        "model_key": MODEL_KEY,
        "checkpoint": str(checkpoint_path) if checkpoint_path else None,
        "available": True,
        "query": query,
        "label": label,
        "label_index": metadata.get("label_index"),
        "model_confidence": round(confidence, 6) if confidence is not None else None,
        "top_k": ranked,
        "class_names": metadata.get("class_names") or [],
        "probabilities": metadata.get("probabilities") or [],
        # Localisation is structurally absent, not merely unfilled: stated so a report or the UI
        # cannot mistake a missing mask for a failed one.
        "localisation": None,
        "scene_level_only": bool(metadata.get("scene_level_only", True)),
        "trained_gsd_m": metadata.get("trained_gsd_m"),
        "model_input_size": metadata.get("model_input_size"),
        "input_shape": metadata.get("input_shape"),
        "test_accuracy": metadata.get("test_accuracy"),
        "test_samples": metadata.get("test_samples"),
        "aerial_accuracy": "NOT MEASURED",
        "checkpoint_epoch": metadata.get("checkpoint_epoch"),
        "best_val_accuracy": metadata.get("best_val_accuracy"),
        "model_class": metadata.get("model_class"),
    }

    record_step("build_classification_evidence", "success", details={
        "label": label, "confidence": confidence, "ranked_classes": len(ranked),
    })
    record_step("complete_pipeline", "success", details={
        "elapsed_seconds": round(time.perf_counter() - t0, 3)
    })

    return {
        "task": "classification",
        "answer": answer,
        "label": label,
        "label_index": metadata.get("label_index"),
        "confidence": round(confidence, 6) if confidence is not None else None,
        "top_k": ranked,
        "class_names": metadata.get("class_names") or [],
        "probabilities": metadata.get("probabilities") or [],
        "scene_level_only": bool(metadata.get("scene_level_only", True)),
        # Present and explicitly None so a caller written against the grounding contract sees
        # "no localisation" rather than a KeyError.
        "selected_box": None,
        "segmentation_mask": None,
        "strategy": STRATEGY,
        "model": MODEL_KEY,
        "evidence": evidence,
        "warnings": list(result.warnings or []),
        "trace": trace,
    }
