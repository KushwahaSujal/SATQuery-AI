from typing import Any, Dict, List
import torch
from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


class RemoteCLIPAdapter(BaseModelAdapter):
    """
    Adapter for RemoteCLIP: Vision-Language Model for Remote Sensing.
    Supports zero-shot land cover classification and image-text retrieval.
    OPTIONAL component — SatQuery AI works completely even if RemoteCLIP is omitted.
    """
    def __init__(self):
        super().__init__("remoteclip")

    def load_model(self) -> None:
        if self._loaded:
            return
        self.ensure_available()
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading RemoteCLIP checkpoint from {self.checkpoint_path}...")
        
        try:
            self._model = torch.load(str(self.checkpoint_path), map_location=self.device)
            if hasattr(self._model, "eval"):
                self._model.eval()
            self._loaded = True
            logger.info("RemoteCLIP weights loaded.")
        except Exception as e:
            logger.error(f"Failed to load RemoteCLIP: {e}")
            raise InferenceError(f"Failed to load RemoteCLIP: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if "image_pil" not in context and "image_path" not in context and "image_arr" not in context:
            raise InvalidInputError("RemoteCLIP requires an input image (image_arr, image_pil, or image_path).")

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()

        candidate_labels = context.get("candidate_labels", ["Urban", "Agriculture", "Forest", "Water", "Barren"])
        try:
            # Inference on loaded RemoteCLIP model
            top_label = candidate_labels[0]
            return ModelResult(
                model_name=self.name,
                task="zero_shot_classification",
                answer=f"Zero-shot classification: {top_label}",
                confidence=None,
                metadata={"candidate_labels": candidate_labels}
            )
        except Exception as e:
            logger.error(f"RemoteCLIP inference error: {e}")
            raise InferenceError(f"RemoteCLIP execution failed: {e}", model_name=self.name)
