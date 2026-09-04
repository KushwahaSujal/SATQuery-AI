"""
TEST ONLY MOCK ADAPTERS.
DO NOT USE IN PRODUCTION INFERENCE.
These deterministic mock objects are used strictly for unit testing the agent pipeline,
response serialization, and error recovery without requiring gigabytes of GPU model weights.
"""
from typing import Any, Dict
import numpy as np
from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult


class TestMockGeneralRSVLMAdapter(BaseModelAdapter):
    """TEST ONLY: Mock General RS VLM adapter for unit testing."""
    def __init__(self):
        super().__init__("general_rs_vlm")

    def is_available(self) -> bool:
        return True

    def load_model(self) -> None:
        self._loaded = True

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        pass

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        return ModelResult(
            model_name="General RS VLM (Mock Unit Test)",
            task="vqa",
            answer="The image displays high-density residential buildings surrounded by road networks and green vegetation.",
            confidence=None,
            metadata={"test_mode": True}
        )


class TestMockChangeFormerAdapter(BaseModelAdapter):
    """TEST ONLY: Mock ChangeFormer adapter for unit testing."""
    def __init__(self):
        super().__init__("changeformer")

    def is_available(self) -> bool:
        return True

    def load_model(self) -> None:
        self._loaded = True

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        pass

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        mask = np.zeros((128, 128), dtype=np.uint8)
        mask[30:70, 30:70] = 1  # 1600 changed pixels
        return ModelResult(
            model_name="ChangeFormer (Mock Unit Test)",
            task="change_detection",
            answer="Change detection test mask generated.",
            confidence=0.92,
            masks=[{"binary_mask": mask, "change_prob_map": mask.astype(np.float32)}]
        )
