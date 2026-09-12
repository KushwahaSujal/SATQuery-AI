import pytest
import numpy as np
from unittest.mock import patch
from pathlib import Path

from backend.app.ml.adapters.changeformer import ChangeFormerAdapter
from backend.app.exceptions import ModelUnavailableError, InvalidInputError


def test_changeformer_lazy_loading():
    adapter = ChangeFormerAdapter()
    assert adapter._loaded is False
    assert adapter._model is None


def test_changeformer_missing_checkpoint():
    adapter = ChangeFormerAdapter()
    with patch.object(adapter, "_resolve_checkpoint_path", return_value=Path("nonexistent_ckpt.pt")):
        with pytest.raises(ModelUnavailableError) as exc_info:
            adapter.load_model()
        assert exc_info.value.code == "MODEL_CHECKPOINT_MISSING"


def test_changeformer_invalid_inputs():
    adapter = ChangeFormerAdapter()
    with pytest.raises(InvalidInputError) as exc_info:
        adapter.predict(None, None)
    assert exc_info.value.code == "INVALID_INPUT"


def test_changeformer_inference_with_verified_checkpoint():
    adapter = ChangeFormerAdapter()
    ckpt_path = adapter._resolve_checkpoint_path()
    if not ckpt_path.is_file():
        pytest.skip(f"Checkpoint not available at {ckpt_path}")

    img1 = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)
    img2 = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)

    result = adapter.predict(img1, img2, threshold=0.5)

    assert result.model_name.lower() == "changeformer"
    assert result.task == "change_detection"
    assert len(result.masks) == 1

    mask_dict = result.masks[0]
    assert "binary_mask" in mask_dict
    assert "change_prob_map" in mask_dict
    assert "logits" in mask_dict

    bin_mask = mask_dict["binary_mask"]
    prob_map = mask_dict["change_prob_map"]
    logits = mask_dict["logits"]

    assert bin_mask.shape == (128, 128)
    assert prob_map.shape == (128, 128)
    assert logits.shape == (1, 2, 128, 128)

    assert np.all((prob_map >= 0.0) & (prob_map <= 1.0))
    assert result.confidence is not None
    assert 0.0 <= result.confidence <= 1.0
