"""
Minimal smoke test verifying Grounding DINO Hugging Face Transformers dependencies,
AutoProcessor, AutoModelForZeroShotObjectDetection, and prompt normalization logic.
"""

import pytest
from transformers import (
    AutoProcessor,
    AutoModelForZeroShotObjectDetection,
    GroundingDinoForObjectDetection,
    GroundingDinoProcessor,
)
from transformers.models.auto.modeling_auto import MODEL_FOR_ZERO_SHOT_OBJECT_DETECTION_MAPPING_NAMES


def test_grounding_dino_classes_available():
    assert "grounding-dino" in MODEL_FOR_ZERO_SHOT_OBJECT_DETECTION_MAPPING_NAMES
    assert MODEL_FOR_ZERO_SHOT_OBJECT_DETECTION_MAPPING_NAMES["grounding-dino"] == "GroundingDinoForObjectDetection"
    assert GroundingDinoForObjectDetection is not None
    assert GroundingDinoProcessor is not None


def test_prompt_normalization():
    def normalize_grounding_prompt(prompt: str) -> str:
        p = prompt.strip().lower()
        if not p.endswith("."):
            p += "."
        return p

    assert normalize_grounding_prompt("Aircraft") == "aircraft."
    assert normalize_grounding_prompt("solar panel . building .") == "solar panel . building ."
    assert normalize_grounding_prompt("  Oil storage tank  ") == "oil storage tank."
