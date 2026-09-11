"""
RemoteCLIP adapter — real weights required.

The adapter used to be a stub: load_model() called torch.load() and kept the
resulting 302-key state dict (never building a model, so .eval() silently
skipped while _loaded was set True), and predict() returned candidate_labels[0]
without running any inference. Nothing tested it, so a 605 MB checkpoint sat
loaded-but-inert and no capability referenced it.
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from backend.app.ml.registry import model_registry

LEVIR_PARQUET = Path("datasets/raw/levircd/data/test-00000-of-00001-31d7c3e3444e5b5d.parquet")


@pytest.fixture(scope="module")
def adapter():
    a = model_registry.get_adapter("remoteclip")
    if not a.is_available():
        pytest.skip("RemoteCLIP checkpoint not present")
    a.load_model()
    return a


@pytest.fixture(scope="module")
def aerial_image():
    if not LEVIR_PARQUET.is_file():
        pytest.skip("LEVIR-CD parquet not present")
    import pyarrow.parquet as pq

    row = pq.ParquetFile(LEVIR_PARQUET).read().to_pylist()[0]
    return Image.open(io.BytesIO(row["imageA"]["bytes"])).convert("RGB")


def test_checkpoint_loads_into_open_clip_architecture(adapter):
    """A real model, not a state dict masquerading as one."""
    assert adapter._model is not None
    assert adapter._preprocess is not None and adapter._tokenizer is not None
    assert hasattr(adapter._model, "encode_image")
    assert hasattr(adapter._model, "encode_text")


def test_image_embeddings_actually_depend_on_the_image(adapter, aerial_image):
    """Guards the stub failure mode: identical output for different inputs."""
    import torch

    other = Image.new("RGB", aerial_image.size, "white")
    with torch.no_grad():
        a = adapter._model.encode_image(adapter._preprocess(aerial_image).unsqueeze(0).to(adapter.device))
        b = adapter._model.encode_image(adapter._preprocess(other).unsqueeze(0).to(adapter.device))
    assert float((a - b).abs().sum()) > 1e-3, "encoder ignored the image content"


def test_predict_returns_real_scores_not_the_first_label(adapter, aerial_image):
    """The stub returned candidate_labels[0] unconditionally with confidence None."""
    labels = ["Water", "Urban", "Forest"]
    res = adapter.predict({"image_pil": aerial_image, "candidate_labels": labels})
    assert res.confidence is not None, "confidence was None — inference did not run"
    scores = res.metadata["scores"]
    assert set(scores) == set(labels)
    assert len(set(scores.values())) > 1, "all labels scored identically"
