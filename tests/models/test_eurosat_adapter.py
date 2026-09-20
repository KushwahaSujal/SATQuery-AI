"""Real inference for the EuroSAT scene classifier, on CPU, one image at a time.

Skips when the checkpoint or the input tile is missing, pins the adapter to CPU so the suite never
competes with a training job for GPU memory, and unloads in a finally block.

These assert the output CONTRACT — the label set, the probability distribution, the label/index
agreement — and deliberately not the correctness of the label. The only real imagery in this
repository is sub-metre aerial photography from `demo_resources/`, while this model was trained on
Sentinel-2 at 10 m/px (64x64 tiles upsampled to 224): a wrong land-cover label on such an image is
expected and is not a defect. The measured accuracy is 0.9832 over the delivered held-out test split
of 4050 samples, and that evidence lives in docs/models/eurosat/ and project/qna.md Q-041.
"""
from pathlib import Path
from typing import Optional

import numpy as np
import pytest
import torch
from PIL import Image

from backend.app.config import settings
from backend.app.ml.adapters.eurosat import EuroSatLandCoverAdapter

DEMO = settings.root_dir / "demo_resources"


def cpu_adapter(cls):
    """An adapter pinned to CPU, or a skip when its checkpoint is not on disk."""
    adapter = cls()
    if not adapter.is_available():
        pytest.skip(f"{adapter.name} checkpoint not available at {adapter.checkpoint_path}")
    adapter.device = torch.device("cpu")
    return adapter


def first_demo_tile() -> Optional[Path]:
    """Any real image already in the repository; the label it earns is not asserted."""
    if not DEMO.is_dir():
        return None
    return next(iter(sorted(DEMO.glob("*/*.png"))), None)


def demo_rgb() -> np.ndarray:
    path = first_demo_tile()
    if path is None:
        pytest.skip(f"No demo tile under {DEMO}")
    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


def test_eurosat_classification_contract_on_a_real_image():
    img = demo_rgb()
    adapter = cpu_adapter(EuroSatLandCoverAdapter)
    try:
        result = adapter.predict(img)

        assert result.task == "classification"
        assert result.model_name == adapter.name

        meta = result.metadata
        assert len(meta["class_names"]) == 10
        assert len(meta["probabilities"]) == 10

        # The reported confidence is the winning softmax probability, not a stand-in.
        assert result.confidence == pytest.approx(max(meta["probabilities"]))
        assert sum(meta["probabilities"]) == pytest.approx(1.0, abs=1e-3)
        assert all(0.0 <= p <= 1.0 for p in meta["probabilities"])

        # Label and index cannot disagree, or every reported label would be untrustworthy.
        assert meta["label"] == meta["class_names"][meta["label_index"]]
        assert meta["label_index"] == int(np.argmax(meta["probabilities"]))

        assert meta["trained_gsd_m"] == 10.0
        assert meta["scene_level_only"] is True
        assert meta["model_input_size"] == 224

        # Scene-level means no localisation: no mask and no box may appear.
        assert result.masks == []
        assert result.boxes == []
    finally:
        adapter.unload()
    assert adapter.loaded is False


def test_eurosat_top_k_is_ranked_and_agrees_with_the_distribution():
    img = demo_rgb()
    adapter = cpu_adapter(EuroSatLandCoverAdapter)
    try:
        result = adapter.predict(img, top_k=5)
        ranked = result.metadata["top_k"]
        assert len(ranked) == 5
        probabilities = [entry["probability"] for entry in ranked]
        assert probabilities == sorted(probabilities, reverse=True)
        assert ranked[0]["label"] == result.metadata["label"]
        assert ranked[0]["probability"] == pytest.approx(result.confidence, abs=1e-5)
        assert all(entry["label"] in result.metadata["class_names"] for entry in ranked)
    finally:
        adapter.unload()
    assert adapter.loaded is False
