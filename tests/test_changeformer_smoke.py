from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from backend.app.models.changeformer import ChangeFormerAdapter


def test_changeformer_smoke_real_images():
    """
    Integration smoke test for ChangeFormer:
      1. Loads the actual checkpoint;
      2. Executes actual inference on two real local sample images;
      3. Verifies output tensor and array shapes;
      4. Verifies all computed values (logits, probabilities, confidence) are finite;
      5. Verifies a valid binary change mask is produced.
    """
    # Verify sample images exist locally on disk
    data_dir = Path(__file__).parent / "data"
    img1_path = data_dir / "sample_t1.png"
    img2_path = data_dir / "sample_t2.png"

    assert img1_path.is_file(), f"Sample image T1 not found at {img1_path}"
    assert img2_path.is_file(), f"Sample image T2 not found at {img2_path}"

    # Load real images from disk
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    orig_w, orig_h = img1.size
    assert (orig_w, orig_h) == (256, 256)
    assert img2.size == (256, 256)

    # 1. Load actual checkpoint
    adapter = ChangeFormerAdapter()
    ckpt_path = adapter._resolve_checkpoint_path()
    assert ckpt_path.is_file(), f"Actual ChangeFormer checkpoint not found at: {ckpt_path}"

    adapter.load_model()
    assert adapter._loaded is True
    assert adapter._model is not None

    # 2. Execute actual inference (no mocks)
    result = adapter.predict(img1, img2, threshold=0.5)

    # 3. Verify output shape matches native image resolution
    assert len(result.masks) == 1
    mask_dict = result.masks[0]

    assert "logits" in mask_dict
    assert "change_prob_map" in mask_dict
    assert "binary_mask" in mask_dict

    logits = mask_dict["logits"]
    prob_map = mask_dict["change_prob_map"]
    binary_mask = mask_dict["binary_mask"]

    assert logits.shape == (1, 2, orig_h, orig_w), f"Expected logits shape (1, 2, {orig_h}, {orig_w}), got {logits.shape}"
    assert prob_map.shape == (orig_h, orig_w), f"Expected prob_map shape ({orig_h}, {orig_w}), got {prob_map.shape}"
    assert binary_mask.shape == (orig_h, orig_w), f"Expected binary_mask shape ({orig_h}, {orig_w}), got {binary_mask.shape}"

    # 4. Verify all output values are finite and mathematically valid
    assert np.all(np.isfinite(logits)), "Logits must contain only finite numbers (no NaN or Inf)"
    assert np.all(np.isfinite(prob_map)), "Probability map must contain only finite numbers"
    assert np.all((prob_map >= 0.0) & (prob_map <= 1.0)), "Probability values must be bounded in [0.0, 1.0]"

    assert result.confidence is not None, "Model confidence must not be None"
    assert np.isfinite(result.confidence), "Model confidence must be a finite float"
    assert 0.0 <= result.confidence <= 1.0, f"Confidence must be in [0.0, 1.0], got {result.confidence}"

    # 5. Verify a valid change mask is produced
    assert binary_mask.dtype == np.uint8, f"Binary mask must be uint8, got {binary_mask.dtype}"
    unique_vals = set(np.unique(binary_mask))
    assert unique_vals.issubset({0, 1}), f"Binary mask values must be subset of {{0, 1}}, got {unique_vals}"

    assert "change_pixel_count" in result.metadata
    assert "total_pixel_count" in result.metadata
    assert result.metadata["total_pixel_count"] == orig_h * orig_w
    assert result.metadata["change_pixel_count"] == int(np.sum(binary_mask > 0))

    # Verify meaningful text response
    assert result.answer is not None and len(result.answer) > 0
    assert "change detection completed" in result.answer.lower()
