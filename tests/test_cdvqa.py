import pytest
import torch
from PIL import Image
from backend.app.ml.adapters.cdvqa import CDVQAAdapter, READABLE_ANSWER_MAP
from backend.app.ml.adapters.cdvqa.network import (
    CDVQAModel,
    ChangeEnhancingModule,
    CDVQA_ANSWER_CLASSES,
    tokenize_question,
    WORD2IDX
)
from backend.app.exceptions import InvalidInputError


def test_cdvqa_adapter_lazy_loading():
    adapter = CDVQAAdapter()
    assert adapter.model_key == "cdvqa"
    # Lazy loading: model should NOT be resident in memory upon initialization
    assert not adapter.loaded


def test_cdvqa_tokenizer():
    q = "What changed between the first and second image?"
    tokens = tokenize_question(q, max_len=24)
    assert isinstance(tokens, torch.Tensor)
    assert tokens.dtype == torch.long
    assert tokens.shape == (24,)
    # 'what', 'changed', 'image', etc. should be mapped to non-pad indices
    assert tokens[0].item() != 0


def test_cdvqa_input_validation():
    adapter = CDVQAAdapter()
    # Missing query
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"image1": Image.new("RGB", (10, 10)), "image2": Image.new("RGB", (10, 10))})

    # Missing image2
    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"image1": Image.new("RGB", (10, 10)), "query": "Is there change?"})


def test_cdvqa_cem_module():
    cem = ChangeEnhancingModule(channels=512)
    f1 = torch.randn(2, 512, 8, 8)
    f2 = torch.randn(2, 512, 8, 8)
    fc1, fc2, mce = cem(f1, f2)

    assert fc1.shape == (2, 512, 8, 8)
    assert fc2.shape == (2, 512, 8, 8)
    assert mce.shape == (2, 1, 8, 8)


def test_cdvqa_model_forward_shape():
    model = CDVQAModel(
        num_classes=len(CDVQA_ANSWER_CLASSES),
        vocab_size=len(WORD2IDX),
        feature_dim=512,
        freeze_backbone=True,
        pretrained=False
    )
    img1 = torch.randn(2, 3, 256, 256)
    img2 = torch.randn(2, 3, 256, 256)
    tokens = torch.randint(0, len(WORD2IDX), (2, 24))

    out = model(img1, img2, tokens)
    assert "logits" in out
    assert "change_map" in out
    assert out["logits"].shape == (2, 19)
    assert out["change_map"].shape == (2, 1, 8, 8)
