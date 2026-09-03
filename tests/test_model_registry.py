import pytest
from backend.app.models.registry import ModelRegistry
from backend.app.models.grounding_dino import GroundingDINOAdapter
from backend.app.models.sam2 import SAM2Adapter


def test_registry_contains_grounding_dino_and_sam2():
    registry = ModelRegistry()
    assert "grounding_dino" in registry.ADAPTER_CLASSES
    assert "sam2" in registry.ADAPTER_CLASSES
    assert registry.ADAPTER_CLASSES["grounding_dino"] == GroundingDINOAdapter
    assert registry.ADAPTER_CLASSES["sam2"] == SAM2Adapter


def test_lazy_loading_and_exposed_properties():
    registry = ModelRegistry()

    # 1. Verify heavy weights are NOT loaded at startup / registry creation
    assert registry.is_model_loaded("grounding_dino") is False
    assert registry.is_model_loaded("sam2") is False

    # 2. Retrieve Grounding DINO adapter
    gd_adapter = registry.get_adapter("grounding_dino")
    assert isinstance(gd_adapter, GroundingDINOAdapter)
    # Heavy weights must remain unloaded (lazy)
    assert gd_adapter.loaded is False
    assert gd_adapter.available is True
    assert gd_adapter.device is not None
    assert gd_adapter.model_id == "IDEA-Research/grounding-dino-base"

    # 3. Retrieve SAM 2 adapter
    sam2_adapter = registry.get_adapter("sam2")
    assert isinstance(sam2_adapter, SAM2Adapter)
    # Heavy weights must remain unloaded (lazy)
    assert sam2_adapter.loaded is False
    assert sam2_adapter.available is True
    assert sam2_adapter.device is not None
    assert sam2_adapter.model_id == "facebook/sam2.1-hiera-small"

    # 4. Verify get_model_status exposes all four required fields
    gd_status = registry.get_model_status("grounding_dino")
    assert "available" in gd_status
    assert "loaded" in gd_status
    assert "device" in gd_status
    assert "model_id" in gd_status
    assert gd_status["available"] is True
    assert gd_status["loaded"] is False
    assert gd_status["model_id"] == "IDEA-Research/grounding-dino-base"

    sam2_status = registry.get_model_status("sam2")
    assert "available" in sam2_status
    assert "loaded" in sam2_status
    assert "device" in sam2_status
    assert "model_id" in sam2_status
    assert sam2_status["available"] is True
    assert sam2_status["loaded"] is False
    assert sam2_status["model_id"] == "facebook/sam2.1-hiera-small"


def test_list_capabilities_exposes_required_fields():
    registry = ModelRegistry()
    caps = registry.list_capabilities()
    cap_map = {c.name.lower(): c for c in caps}

    assert "groundingdino" in cap_map
    gd_cap = cap_map["groundingdino"]
    assert hasattr(gd_cap, "available")
    assert hasattr(gd_cap, "loaded")
    assert hasattr(gd_cap, "device")
    assert hasattr(gd_cap, "model_id")
    assert gd_cap.available is True
    assert gd_cap.loaded is False
    assert gd_cap.model_id == "IDEA-Research/grounding-dino-base"

    assert "sam2" in cap_map
    sam2_cap = cap_map["sam2"]
    assert hasattr(sam2_cap, "available")
    assert hasattr(sam2_cap, "loaded")
    assert hasattr(sam2_cap, "device")
    assert hasattr(sam2_cap, "model_id")
    assert sam2_cap.available is True
    assert sam2_cap.loaded is False
    assert sam2_cap.model_id == "facebook/sam2.1-hiera-small"
