"""The flood segmenter's refusal contract: it loads real weights but never serves a flood mask.

No weights and no imagery: everything here runs with the checkpoints absent. The point of these
tests is that the refusal is not an accident and cannot quietly become a mask — the training-time
normalisation was never documented and none of 17 swept preprocessing/threshold combinations
reproduced the delivered global flood IoU 0.6292 over the Sen1Floods11 official test split (90
scenes) or validation split (89 scenes). See project/qna.md Q-041 §5, docs/models/flood/ and
project/handoff/ayushman-delivery-2026-09-20.md.
"""

import numpy as np
import pytest
import torch

from backend.app.config import settings
from backend.app.exceptions import InvalidInputError, ModelUnavailableError
from backend.app.ml.adapters.flood_segmenter import (
    BEST_RECOVERED_IOU_ARGMAX,
    DELIVERED_THRESHOLD,
    REPORTED_TEST_IOU,
    FloodSegmenterAdapter,
)
from backend.app.ml.adapters.flood_unet import FLOOD_CHANNEL_NAMES, FLOOD_INPUT_CHANNELS
from backend.app.ml.registry import model_registry


def test_config_entry_does_not_carry_the_delivered_threshold():
    """The delivered 0.30 provably does not transfer, so configs/models.yaml must leave it null."""
    spec = settings.models["flood_segmenter"]
    assert spec.enabled is True
    assert spec.checkpoint_path == "checkpoints/flood_seg/best.pt"
    assert spec.threshold is None
    assert spec.trained_gsd_m == pytest.approx(10.0)


def test_construction_loads_nothing():
    adapter = FloodSegmenterAdapter()
    assert adapter.model_key == "flood_segmenter"
    assert adapter.loaded is False
    assert adapter._model is None
    assert adapter.trained_gsd_m == pytest.approx(10.0)
    assert len(adapter.channel_names) == FLOOD_INPUT_CHANNELS == 16
    assert adapter.channel_names == list(FLOOD_CHANNEL_NAMES)


def test_registry_metadata_states_the_sixteen_channel_requirement():
    meta = model_registry.MODEL_METADATA["flood_segmenter"]
    assert meta["capabilities"] == ["flood_segmentation"]
    requirement = meta["input_requirements"]["image"]
    assert "16" in requirement
    assert "DEM" in requirement and "S1" in requirement and "Sentinel-2" in requirement


def test_missing_checkpoint_raises_model_unavailable(tmp_path):
    adapter = FloodSegmenterAdapter()
    adapter.checkpoint_path = tmp_path / "definitely_not_here.pt"
    assert adapter.is_available() is False
    with pytest.raises(ModelUnavailableError) as exc:
        adapter.load_model()
    assert exc.value.code == "MODEL_CHECKPOINT_MISSING"


def sixteen_channel_stack(layout: str = "chw") -> np.ndarray:
    if layout == "chw":
        return np.zeros((FLOOD_INPUT_CHANNELS, 32, 32), np.float32)
    return np.zeros((32, 32, FLOOD_INPUT_CHANNELS), np.float32)


@pytest.mark.parametrize("layout", ["chw", "hwc"])
def test_validate_inputs_accepts_a_sixteen_channel_stack(layout):
    adapter = FloodSegmenterAdapter()
    adapter.validate_inputs({"arr": sixteen_channel_stack(layout)})
    adapter.validate_inputs({"image": torch.from_numpy(sixteen_channel_stack(layout))})
    # Batched is accepted too, and validation never touches the weights.
    adapter.validate_inputs({"stack": sixteen_channel_stack(layout)[None, ...]})
    assert adapter.loaded is False


@pytest.mark.parametrize(
    "rgb",
    [
        np.zeros((64, 64, 3), np.uint8),
        np.zeros((3, 64, 64), np.uint8),
        np.zeros((1, 3, 64, 64), np.float32),
    ],
)
def test_validate_inputs_rejects_three_channel_rgb_and_names_the_channel_order(rgb):
    """RGB is what the pipeline supplies and it can never satisfy this model."""
    adapter = FloodSegmenterAdapter()
    with pytest.raises(InvalidInputError) as exc:
        adapter.validate_inputs({"arr": rgb})
    message = str(exc.value)
    assert "16" in message
    for band in ("S1_VV", "S1_VH", "S2_B8A", "DEM"):
        assert band in message
    assert adapter.loaded is False


def test_validate_inputs_rejects_a_context_without_a_stack():
    adapter = FloodSegmenterAdapter()
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({})
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"arr": None})
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs("not a dict")
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"arr": "not an array"})
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"arr": np.zeros((16, 16), np.float32)})  # 2-D, no channel axis


def test_predict_reports_not_configured_and_never_returns_a_mask():
    adapter = FloodSegmenterAdapter()
    result = adapter.predict({"arr": sixteen_channel_stack()})

    assert result.status == "NOT_CONFIGURED"
    assert result.confidence is None
    assert result.masks == []
    assert result.boxes == []
    assert result.logits is None
    assert result.metadata["flood_mask"] is None
    assert result.metadata["status"] == "NOT_CONFIGURED"
    assert result.metadata["code"] == "MODEL_NOT_CONFIGURED"
    assert result.warnings

    # The answer has to say plainly what is wrong, not just that something is.
    answer = result.answer
    assert "NOT_CONFIGURED" in answer
    assert str(REPORTED_TEST_IOU) in answer
    assert "normalisation" in answer
    assert "No flood extent can be reported." in answer

    # Nothing was loaded to produce the refusal.
    assert adapter.loaded is False
    assert adapter._model is None


def test_predict_metadata_carries_the_measured_numbers():
    meta = FloodSegmenterAdapter().predict({"arr": sixteen_channel_stack()}).metadata
    assert meta["preprocessing"] == "UNKNOWN"
    assert meta["threshold_transferable"] is False
    assert meta["delivered_threshold"] == pytest.approx(DELIVERED_THRESHOLD)
    assert meta["reported_test_iou"] == pytest.approx(0.6292)
    assert meta["best_recovered_iou_argmax"] == pytest.approx(0.7034)
    assert meta["best_recovered_iou_at_delivered_threshold"] == pytest.approx(0.7273)
    assert meta["closest_raw_value_scheme_iou"] == pytest.approx(0.5403)
    assert meta["preprocessing_combinations_swept"] == 17
    assert meta["test_split_scenes"] == 90
    assert meta["validation_split_scenes"] == 89
    assert meta["required_channels"] == 16
    assert meta["channel_names"] == list(FLOOD_CHANNEL_NAMES)
    assert meta["trained_gsd_m"] == pytest.approx(10.0)
    assert meta["blocker"]
    # The recovered score being *higher* than the delivered one is the red flag, not a win.
    assert BEST_RECOVERED_IOU_ARGMAX > REPORTED_TEST_IOU


@pytest.mark.parametrize("context", [None, {}, {"arr": np.zeros((64, 64, 3), np.uint8)}])
def test_predict_refuses_regardless_of_input_and_without_the_checkpoint(context, tmp_path):
    """The blocker is unconditional, so predict never raises and never needs the weights."""
    adapter = FloodSegmenterAdapter()
    adapter.checkpoint_path = tmp_path / "definitely_not_here.pt"
    result = adapter.predict(context)
    assert result.status == "NOT_CONFIGURED"
    assert result.masks == []
    assert result.confidence is None
    assert adapter.loaded is False


def test_unload_is_safe_before_a_load():
    adapter = FloodSegmenterAdapter()
    adapter.unload()
    assert adapter.loaded is False
    assert adapter._model is None
