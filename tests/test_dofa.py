import pytest
import numpy as np
import torch

from backend.app.models.dofa import DOFAAdapter
from backend.app.models.registry import model_registry
from backend.app.exceptions import InvalidInputError


def test_dofa_adapter_registration():
    adapter = model_registry.get_adapter("dofa")
    assert isinstance(adapter, DOFAAdapter)
    assert adapter.name.lower() == "dofa"


def test_dofa_adapter_input_validation():
    adapter = DOFAAdapter()
    with pytest.raises(InvalidInputError):
        adapter.predict({})


def test_dofa_adapter_optical_feature_extraction():
    adapter = DOFAAdapter()
    dummy_optical = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    result = adapter.predict({"optical_arr": dummy_optical})
    assert result.model_name.lower() == "dofa"
    assert result.task == "representation"
    assert "optical_shape" in result.metadata
    assert result.metadata["optical_shape"] == [197, 768]
    assert "optical_cls_norm" in result.metadata
    assert result.metadata["optical_cls_norm"] > 0


def test_dofa_adapter_multimodal_optical_sar_extraction():
    adapter = DOFAAdapter()
    dummy_optical = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    dummy_sar = np.random.randn(256, 256, 2).astype(np.float32)
    result = adapter.predict({"optical_arr": dummy_optical, "sar_arr": dummy_sar})
    assert result.model_name.lower() == "dofa"
    assert "optical_shape" in result.metadata
    assert "sar_shape" in result.metadata
    assert result.metadata["optical_shape"] == [197, 768]
    assert result.metadata["sar_shape"] == [197, 768]
