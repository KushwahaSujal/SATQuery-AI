import pytest
import numpy as np
import torch
from PIL import Image

from backend.app.ml.registry import model_registry
from backend.app.ml.adapters.general_rs_vlm import GeneralRSVLMAdapter
from backend.app.ml.adapters.fusion import OpticalSARFusionModel


def test_general_rs_vlm_registered_and_available():
    assert "general_rs_vlm" in model_registry.ADAPTER_CLASSES
    assert model_registry.is_model_available("general_rs_vlm")


def test_optical_sar_fusion_registered_and_available():
    assert "satquery_optical_sar_fusion" in model_registry.ADAPTER_CLASSES
    assert model_registry.is_model_available("satquery_optical_sar_fusion")


def test_general_rs_vlm_inference():
    adapter = model_registry.get_adapter("general_rs_vlm")
    img = Image.new("RGB", (224, 224), color=(34, 139, 34))  # Forest green
    result = adapter.predict({
        "image_pil": img,
        "query": "What is the primary terrain color?"
    })
    assert result.model_name in ("general_rs_vlm", "GeneralRSVLM")
    assert result.task == "vqa"
    assert len(result.answer) > 0
    assert result.confidence is not None
    assert result.confidence > 0.0


def test_optical_sar_fusion_inference():
    adapter = model_registry.get_adapter("satquery_optical_sar_fusion")
    opt_feat = np.random.randn(1, 768).astype(np.float32)
    sar_feat = np.random.randn(1, 768).astype(np.float32)

    result = adapter.predict({
        "optical_features": opt_feat,
        "sar_features": sar_feat
    })
    assert result.model_name in ("satquery_optical_sar_fusion", "OpticalSARFusionModel")
    assert result.task == "optical_sar_analysis"
    assert result.status == "NOT_CONFIGURED"
    assert result.metadata.get("status") == "NOT_CONFIGURED"
    assert result.confidence is None
    assert result.metadata.get("prediction") is None
    assert "NOT_CONFIGURED" in result.answer
    assert "%" not in result.answer
    assert "reason" in result.metadata
    assert len(result.metadata["reason"]) > 0
