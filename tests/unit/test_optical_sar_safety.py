"""
Regression test for Optical-SAR zero-fabrication safety.
Verifies that uncalibrated/untrained Optical-SAR fusion never returns fabricated
predictions, false class percentages, or simulated confidence scores.
"""
import pytest
import numpy as np
from pathlib import Path

from backend.app.ml.registry import model_registry
from backend.app.exceptions import InvalidInputError
from backend.app.agent.state import AgentState
from backend.app.agent.tools.inference import run_optical_sar


def test_optical_sar_adapter_reports_not_configured():
    """
    Adapter must explicitly report status=NOT_CONFIGURED, confidence=None,
    and null prediction when fusion head is uncalibrated.
    """
    adapter = model_registry.get_adapter("satquery_optical_sar_fusion")
    opt_feat = np.random.randn(1, 768).astype(np.float32)
    sar_feat = np.random.randn(1, 768).astype(np.float32)

    result = adapter.predict({
        "optical_features": opt_feat,
        "sar_features": sar_feat
    })

    # Schema-level status and metadata
    assert result.status == "NOT_CONFIGURED"
    assert result.metadata.get("status") == "NOT_CONFIGURED"
    assert result.confidence is None
    assert result.metadata.get("prediction") is None

    # Zero fabrication checks
    assert "%" not in result.answer
    assert "Permanently irrigated land" not in result.answer
    assert "surface_roughness" not in result.metadata
    assert "builtup_index" not in result.metadata
    assert "top_classes" not in result.metadata

    # Explanatory reason present
    assert "reason" in result.metadata
    assert "NOT_CONFIGURED" in result.metadata["reason"]


def test_optical_sar_adapter_rejects_missing_inputs():
    """Adapter must validate inputs and reject missing optical or SAR data."""
    adapter = model_registry.get_adapter("satquery_optical_sar_fusion")

    with pytest.raises(InvalidInputError):
        adapter.predict({"optical_features": np.random.randn(1, 768)})

    with pytest.raises(InvalidInputError):
        adapter.predict({"sar_features": np.random.randn(1, 768)})

    with pytest.raises(InvalidInputError):
        adapter.predict({})


def test_run_optical_sar_tool_propagates_not_configured_safely():
    """
    Executing run_optical_sar in agent pipeline must propagate NOT_CONFIGURED,
    leave confidence as None, and append safety warnings.
    """
    repo_root = Path(__file__).resolve().parents[2]
    opt_path = repo_root / "datasets" / "samples" / "optical_sar_pair" / "optical_sentinel2.png"
    sar_path = repo_root / "datasets" / "samples" / "optical_sar_pair" / "sentinel1_sar_cband.png"

    assert opt_path.exists(), f"Missing test fixture: {opt_path}"
    assert sar_path.exists(), f"Missing test fixture: {sar_path}"

    state = AgentState(
        request_id="test-optical-sar-safety",
        query="Analyze optical and SAR data for land cover",
        image_paths=[str(opt_path), str(sar_path)],
        modalities=["optical", "sar"]
    )

    run_optical_sar(state)

    assert len(state.model_results) == 1
    res = state.model_results[0]

    assert res.status == "NOT_CONFIGURED"
    assert res.confidence is None
    assert state.confidence is None
    assert "NOT_CONFIGURED" in state.answer
    assert "%" not in state.answer
    assert any("NOT_CONFIGURED" in w for w in state.warnings)
