"""Construction, config parsing and input validation for the locally trained adapters.

No weights and no imagery: everything here runs with the checkpoints absent.

Covers every locally trained adapter in the registry: the four aerial/planetary models, the water
and cloud segmenters (registered in Q-035 but never added here), and the two from Q-041 — the
EuroSAT scene classifier and the flood segmenter, which loads a real checkpoint but deliberately
never serves a mask. Flood-specific behaviour is in tests/unit/test_flood_segmenter.py.
"""

import numpy as np
import pytest
from PIL import Image

from backend.app.config import settings
from backend.app.exceptions import InferenceError, InvalidInputError, ModelUnavailableError
from backend.app.ml.adapters import binary_segmenter as binary_module
from backend.app.ml.adapters import crater_detector as crater_module
from backend.app.ml.adapters import landcover_segmenter as landcover_module
from backend.app.ml.adapters.binary_segmenter import (
    BinarySegmenterAdapter,
    BuildingSegmenterAdapter,
    CloudSegmenterAdapter,
    RoadSegmenterAdapter,
    WaterSegmenterAdapter,
    to_rgb_array,
)
from backend.app.ml.adapters.crater_detector import CraterDetectorAdapter
from backend.app.ml.adapters.eurosat import EuroSatLandCoverAdapter
from backend.app.ml.adapters.flood_segmenter import FloodSegmenterAdapter
from backend.app.ml.adapters.landcover_segmenter import LandCoverSegmenterAdapter
from backend.app.ml.registry import model_registry

ADAPTERS = {
    "roads_segmenter": RoadSegmenterAdapter,
    "buildings_segmenter": BuildingSegmenterAdapter,
    "water_segmenter": WaterSegmenterAdapter,
    "cloud_segmenter": CloudSegmenterAdapter,
    "landcover_segmenter": LandCoverSegmenterAdapter,
    "crater_detector": CraterDetectorAdapter,
    "eurosat_classifier": EuroSatLandCoverAdapter,
    "flood_segmenter": FloodSegmenterAdapter,
}

#: Everything above except the flood segmenter, which needs all 16 S1+S2+DEM bands and rejects a
#: plain RGB tile by design, and which reports NOT_CONFIGURED instead of raising on a bad request
#: (project/qna.md Q-041 §5). Its own contract is asserted in tests/unit/test_flood_segmenter.py.
RGB_INPUT_ADAPTERS = {k: v for k, v in ADAPTERS.items() if k != "flood_segmenter"}


@pytest.mark.parametrize("key,cls", ADAPTERS.items())
def test_registry_returns_the_new_adapters(key, cls):
    assert model_registry.ADAPTER_CLASSES[key] is cls
    assert isinstance(model_registry.get_adapter(key), cls)
    # Singleton, as for every other registered model.
    assert model_registry.get_adapter(key) is model_registry.get_adapter(key)
    assert key in model_registry.MODEL_METADATA


@pytest.mark.parametrize("key,cls", ADAPTERS.items())
def test_config_entry_parses_and_nothing_is_loaded_on_construction(key, cls):
    spec = settings.models[key]
    assert spec.enabled is True
    assert spec.input_count == 1
    assert spec.checkpoint_path
    assert spec.supported_tasks and spec.supported_modalities

    adapter = cls()
    assert adapter.model_key == key
    assert adapter.name == spec.name
    assert adapter.loaded is False
    assert adapter._model is None


def test_binary_segmenter_reads_class_name_and_tta_from_config():
    assert RoadSegmenterAdapter().class_name == "road"
    assert BuildingSegmenterAdapter().class_name == "building"
    assert WaterSegmenterAdapter().class_name == "water"
    assert CloudSegmenterAdapter().class_name == "cloud"
    # configs/models.yaml leaves TTA off: 4x the latency for +0.012 IoU (project/qna.md Q-032).
    for cls in (RoadSegmenterAdapter, BuildingSegmenterAdapter, WaterSegmenterAdapter,
                CloudSegmenterAdapter):
        assert cls().tta is False


def test_binary_segmenter_falls_back_when_no_config_entry_exists():
    adapter = BinarySegmenterAdapter("not_in_models_yaml", class_name="water")
    assert adapter.config is None
    assert adapter.class_name == "water"
    assert adapter.tta is False
    assert adapter.threshold == BinarySegmenterAdapter._FALLBACK_THRESHOLD
    assert adapter.is_available() is False


def test_crater_detector_config_thresholds():
    adapter = CraterDetectorAdapter()
    assert settings.models["crater_detector"].input_size == 832
    assert adapter.confidence_threshold == pytest.approx(0.25)
    assert adapter.LABEL == "crater"


def test_segmenters_are_unavailable_without_the_trainer_module(monkeypatch):
    """The adapters import training.segmentation; a deploy without it must report unavailable."""
    monkeypatch.setattr(binary_module, "trainer_importable", lambda: False)
    monkeypatch.setattr(landcover_module, "trainer_importable", lambda: False)
    assert RoadSegmenterAdapter().is_available() is False
    assert BuildingSegmenterAdapter().is_available() is False
    assert WaterSegmenterAdapter().is_available() is False
    assert CloudSegmenterAdapter().is_available() is False
    assert LandCoverSegmenterAdapter().is_available() is False


def test_ultralytics_is_not_imported_at_module_scope():
    """ultralytics is AGPL-3.0, so importing the registry must not pull it in (Q-028)."""
    assert not hasattr(crater_module, "YOLO")
    assert "ultralytics" not in {n for n in vars(crater_module) if isinstance(n, str)}


@pytest.mark.parametrize("cls", ADAPTERS.values())
def test_is_available_is_false_when_the_checkpoint_is_missing(cls, tmp_path):
    adapter = cls()
    adapter.checkpoint_path = tmp_path / "definitely_not_here.pt"
    assert adapter.is_available() is False
    with pytest.raises(ModelUnavailableError) as exc:
        adapter.load_model()
    assert exc.value.code == "MODEL_CHECKPOINT_MISSING"


@pytest.mark.parametrize("cls", RGB_INPUT_ADAPTERS.values())
def test_validate_inputs_rejects_a_context_without_an_image(cls):
    adapter = cls()
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({})
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"image": None})
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs("not a dict")
    # A present image is accepted, and validation never touches the weights.
    adapter.validate_inputs({"image": np.zeros((8, 8, 3), np.uint8)})
    assert adapter.loaded is False


@pytest.mark.parametrize("cls", RGB_INPUT_ADAPTERS.values())
def test_predict_without_an_image_raises_before_loading(cls):
    adapter = cls()
    with pytest.raises(InvalidInputError):
        adapter.predict(None)
    with pytest.raises(InvalidInputError):
        adapter.predict({})
    assert adapter.loaded is False


@pytest.mark.parametrize("bad", [0.0, 1.0, 1.5, -0.2])
def test_binary_segmenter_rejects_thresholds_outside_the_open_unit_interval(bad):
    adapter = RoadSegmenterAdapter()
    img = np.zeros((16, 16, 3), np.uint8)
    with pytest.raises(InvalidInputError):
        adapter.predict(img, threshold=bad)
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"image": img, "threshold": bad})
    assert adapter.loaded is False


@pytest.mark.parametrize("bad", [0.0, 1.5, -0.2])
def test_crater_detector_rejects_confidence_thresholds_outside_range(bad):
    adapter = CraterDetectorAdapter()
    img = np.zeros((16, 16, 3), np.uint8)
    with pytest.raises(InvalidInputError):
        adapter.predict(img, confidence_threshold=bad)
    assert adapter.loaded is False


def test_unload_is_safe_before_a_load():
    for cls in ADAPTERS.values():
        adapter = cls()
        adapter.unload()
        assert adapter.loaded is False
        assert adapter._model is None


def test_to_rgb_array_accepts_the_shapes_the_backend_passes_around(tmp_path):
    assert to_rgb_array(np.zeros((4, 5), np.uint8)).shape == (4, 5, 3)
    assert to_rgb_array(np.zeros((3, 4, 5), np.uint8)).shape == (4, 5, 3)   # CHW -> HWC
    assert to_rgb_array(np.zeros((4, 5, 4), np.uint8)).shape == (4, 5, 3)   # RGBA -> RGB
    assert to_rgb_array(Image.new("RGB", (5, 4))).shape == (4, 5, 3)

    # Floats in [0, 1] are rescaled, not truncated to black.
    out = to_rgb_array(np.ones((4, 5, 3), np.float32))
    assert out.dtype == np.uint8 and out.max() == 255

    path = tmp_path / "tile.png"
    Image.new("RGB", (5, 4), (10, 20, 30)).save(path)
    assert to_rgb_array(path).shape == (4, 5, 3)
    assert to_rgb_array(str(path)).shape == (4, 5, 3)

    with pytest.raises(InvalidInputError):
        to_rgb_array(tmp_path / "missing.png")
    with pytest.raises(InvalidInputError):
        to_rgb_array(object())


def test_landcover_classes_are_empty_until_the_weights_are_loaded():
    assert LandCoverSegmenterAdapter().classes == []


def test_eurosat_reads_its_input_size_and_gsd_from_config():
    """224 px and 10 m/px (Sentinel-2) come from configs/models.yaml, not from a constant."""
    adapter = EuroSatLandCoverAdapter()
    assert settings.models["eurosat_classifier"].input_size == 224
    assert adapter.image_size == 224
    assert adapter.trained_gsd_m == pytest.approx(10.0)
    assert settings.models["eurosat_classifier"].task == "classification"


def test_eurosat_class_names_are_unknown_until_the_checkpoint_is_loaded():
    """The label set lives in the checkpoint, so guessing it before loading is refused (Q-041)."""
    adapter = EuroSatLandCoverAdapter()
    with pytest.raises(InferenceError):
        _ = adapter.class_names
    assert adapter.loaded is False
