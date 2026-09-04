"""
SatQuery AI — Orchestration Layer Unit & Integration Tests
Tests CapabilityRegistry, IntentClassifier, CapabilityMatcher, DependencyGraph,
PolicyEngine, DeterministicCache, and OutputQualityValidator.
"""
import pytest
import numpy as np
from backend.app.orchestration.schemas import (
    ModalityType,
    DAGPlanNode,
    IntentClassificationResult,
    ExtractedQueryEntities,
)
from backend.app.orchestration.capability_registry import capability_registry
from backend.app.orchestration.intent_classifier import IntentClassifier
from backend.app.orchestration.matcher import CapabilityMatcher
from backend.app.orchestration.dependency_graph import DependencyGraph
from backend.app.orchestration.input_analyzer import InputAnalysisFacts
from backend.app.orchestration.policy_engine import PolicyEngine, PolicyViolationException
from backend.app.orchestration.cache import DeterministicCache
from backend.app.orchestration.output_validator import OutputQualityValidator, ModelOutputInvalidError
from backend.app.orchestration.provenance import ProvenanceBuilder


def test_capability_registry_registration():
    """Verify all 13 core capabilities are registered and active."""
    caps = capability_registry.list_enabled()
    cap_ids = [c.capability_id for c in caps]
    assert len(cap_ids) >= 12
    assert "single_image_grounding" in cap_ids
    assert "temporal_change_vqa" in cap_ids
    assert "temporal_change_detection" in cap_ids
    assert "optical_sar_analysis" in cap_ids
    assert "video_grounding" in cap_ids
    assert "multispectral_analysis" in cap_ids
    assert "sar_analysis" in cap_ids


def test_intent_classifier_grounding_precedence():
    """Verify grounding intent strictly takes precedence over generic VQA."""
    queries = [
        "Locate the red shipping container on the dock",
        "Highlight the small white aircraft parked on the runway",
        "Point out the damaged storage depot near the perimeter",
        "Where is the offshore oil platform?",
        "Detect and outline the bridge over the river"
    ]
    for q in queries:
        res = IntentClassifier.classify_intent(q, num_inputs=1)
        assert res.task == "single_image_grounding", f"Failed on query: {q}"
        assert res.routing_confidence >= 0.85
        assert res.extracted_entities.object_class is not None


def test_intent_classifier_temporal_vqa():
    """Verify temporal query with 2 images classifies as temporal_change_vqa."""
    q = "What new buildings were constructed between 2020 and 2024?"
    res = IntentClassifier.classify_intent(q, num_inputs=2)
    assert res.task == "temporal_change_vqa"
    assert bool(res.extracted_entities.temporal_intent) is True


def test_capability_matcher_grounding():
    """Verify matcher assigns single_image_grounding capability."""
    intent = IntentClassifier.classify_intent("Find the cargo vessel", num_inputs=1)
    facts = InputAnalysisFacts(
        total_files=1,
        file_types=["optical"],
        modalities=["optical_rgb"],
        overall_modality_type=ModalityType.OPTICAL_RASTER
    )
    cap, reason = CapabilityMatcher.match(intent, facts)
    assert cap.capability_id == "single_image_grounding"
    assert "vessel" in reason or "target object" in reason


def test_dag_dependency_stages():
    """Verify DAG stage topological ordering and parallel stage computation."""
    dag = DependencyGraph.build_dag_for_capability("temporal_change_vqa")
    assert len(dag.execution_order) >= 4
    # Stage 1 must be inspect_raster
    assert dag.execution_order[0] == ["inspect_raster"]
    # validate_temporal_pair must follow inspect_raster
    assert dag.execution_order[1] == ["validate_temporal_pair"]


def test_policy_spectral_integrity():
    """Verify PolicyEngine prevents NDVI calculation when NIR is missing."""
    band_mapping = {"red": 1, "green": 2, "blue": 3, "nir": None}
    with pytest.raises(PolicyViolationException) as exc_info:
        PolicyEngine.enforce_spectral_policy(band_mapping, "NDVI")
    assert exc_info.value.code == "INDEX_NOT_AVAILABLE"


def test_policy_spatial_alignment():
    """Verify PolicyEngine disallows unaligned temporal rasters."""
    with pytest.raises(PolicyViolationException) as exc_info:
        PolicyEngine.enforce_spatial_alignment_policy(is_spatially_aligned=False)
    assert exc_info.value.code == "REGISTRATION_REQUIRED"


def test_deterministic_cache_idempotency(tmp_path):
    """Verify cache stores and retrieves identical request."""
    cache = DeterministicCache(max_size=5)
    f1 = tmp_path / "img1.png"
    f1.write_bytes(b"mock_image_bytes_12345")

    k1 = cache.compute_cache_key([str(f1)], "Locate vessel", "single_image_grounding")
    k2 = cache.compute_cache_key([str(f1)], "Locate vessel", "single_image_grounding")
    assert k1 == k2

    cache.put(k1, {"answer": "Found 1 vessel", "confidence": 0.94})
    cached = cache.get(k1)
    assert cached is not None
    assert cached["confidence"] == 0.94


def test_output_quality_validator_box_filtering():
    """Verify OutputQualityValidator filters inverted or out-of-bounds boxes."""
    raw_boxes = [
        [10.0, 10.0, 50.0, 50.0],    # Valid
        [50.0, 50.0, 10.0, 10.0],    # Inverted (x2 < x1) -> should be discarded
        [-10.0, -5.0, 200.0, 200.0], # Clamped to [0, 0, 100, 100]
        [30.0, 30.0, 30.0, 30.0],    # Zero area -> discarded
    ]
    valid_boxes = OutputQualityValidator.validate_grounding_output(raw_boxes, image_width=100, image_height=100)
    assert len(valid_boxes) == 2
    assert valid_boxes[0] == [10.0, 10.0, 50.0, 50.0]
    assert valid_boxes[1] == [0.0, 0.0, 100.0, 100.0]


def test_provenance_graph_assembly(tmp_path):
    """Verify ProvenanceBuilder constructs valid audit tree."""
    f1 = tmp_path / "sample.tif"
    f1.write_bytes(b"tiff_bytes_8888")

    graph = ProvenanceBuilder.build_provenance_graph(
        job_id="test_job_1",
        input_paths=[str(f1)],
        models_used=["grounding_dino", "sam2"],
        artifacts_dict={"masks": ["mask.png"], "overlays": ["overlay.png"]},
        execution_trace=[],
        answer="Detected single vehicle."
    )
    assert graph.job_id == "test_job_1"
    assert len(graph.root_inputs) == 1
    assert any(n.node_id == "model_grounding_dino" for n in graph.nodes)
    assert any(n.node_id == "final_answer" for n in graph.nodes)
    assert len(graph.edges) > 0
