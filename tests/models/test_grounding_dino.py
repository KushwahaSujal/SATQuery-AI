"""
Unit tests for the production GroundingDINOAdapter.
Verifies lazy loading, validation rules, availability, and prediction interface.
"""

import pytest
import numpy as np
from PIL import Image
from backend.app.ml.adapters.grounding_dino import GroundingDINOAdapter
from backend.app.exceptions import InvalidInputError


def test_grounding_dino_adapter_initialization():
    adapter = GroundingDINOAdapter()
    assert adapter.name == "GroundingDINO"
    assert adapter.is_available() is True
    assert adapter._loaded is False
    assert adapter._model is None
    assert adapter._processor is None


def test_grounding_dino_input_validation():
    adapter = GroundingDINOAdapter()
    
    # Missing image
    with pytest.raises(InvalidInputError):
        adapter.predict(image_or_context=None, prompt="car.")

    # Missing prompt
    dummy_img = Image.new("RGB", (64, 64), color="red")
    with pytest.raises(InvalidInputError):
        adapter.predict(image_or_context=dummy_img, prompt="")

    with pytest.raises(InvalidInputError):
        adapter.validate_inputs({"image": dummy_img, "prompt": "   "})


def test_grounding_dino_prompt_normalization():
    adapter = GroundingDINOAdapter()
    assert adapter._normalize_prompt("Airplane") == "airplane."
    assert adapter._normalize_prompt("  building . car .  ") == "building . car ."
    assert adapter._normalize_prompt("storage tank.") == "storage tank."
