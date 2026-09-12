from pathlib import Path
from typing import Any, Dict, Optional
import torch
import numpy as np
from PIL import Image
from transformers import BlipProcessor, BlipForQuestionAnswering

from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger
from backend.app.geo.optical_preprocessing import to_pil_rgb
from backend.app.ml.device import warn_if_cpu_for_heavy_model


class GeneralRSVLMAdapter(BaseModelAdapter):
    """
    General Remote-Sensing Vision-Language Model (RS-VLM) Adapter.
    Performs open-ended natural-language visual question answering (VQA),
    scene description, and semantic identification on satellite/aerial imagery.
    Utilizes local, verified weights in checkpoints/general_rs_vlm.
    """
    def __init__(self):
        super().__init__("general_rs_vlm")
        self._processor: Optional[BlipProcessor] = None

    def load_model(self) -> None:
        if self._loaded and self._model is not None and self._processor is not None:
            return

        self.ensure_available()
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading General RS-VLM weights and processor from {self.checkpoint_path} onto {self.device}...")

        try:
            model_dir = str(self.checkpoint_path)
            self._processor = BlipProcessor.from_pretrained(model_dir)
            self._model = BlipForQuestionAnswering.from_pretrained(model_dir).to(self.device).eval()
            self._loaded = True
            logger.info("General RS-VLM loaded and verified successfully.")
        except Exception as e:
            logger.error(f"Failed to load General RS-VLM: {e}", exc_info=True)
            raise InferenceError(f"Failed to load General RS-VLM weights: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        has_image = (
            "image_arr" in context
            or "image_pil" in context
            or "image_path" in context
            or "image" in context
        )
        if not has_image:
            raise InvalidInputError("General RS-VLM requires an input image (image_arr, image_pil, or image_path).")

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()

        # Extract PIL image
        image: Optional[Image.Image] = None
        if "image_pil" in context and isinstance(context["image_pil"], Image.Image):
            image = context["image_pil"]
        elif "image_arr" in context and isinstance(context["image_arr"], np.ndarray):
            image = to_pil_rgb(context["image_arr"])
        elif "image_path" in context:
            image = Image.open(context["image_path"]).convert("RGB")
        elif "image" in context:
            if isinstance(context["image"], Image.Image):
                image = context["image"]
            elif isinstance(context["image"], np.ndarray):
                image = to_pil_rgb(context["image"])
            elif isinstance(context["image"], (str, Path)):
                image = Image.open(str(context["image"])).convert("RGB")

        if image is None:
            raise InvalidInputError("Could not resolve a valid PIL image for General RS-VLM.")

        prompt = context.get("query") or context.get("question") or context.get("text") or "What is in this remote sensing image?"
        # Standardize question format for VQA
        if not prompt.endswith("?"):
            prompt = prompt.strip() + "?"

        try:
            inputs = self._processor(image, prompt, return_tensors="pt").to(self.device)
            with torch.no_grad():
                out = self._model.generate(
                    **inputs,
                    max_new_tokens=50,
                    num_beams=3,
                    early_stopping=True,
                    return_dict_in_generate=True,
                    output_scores=True
                )
                generated_ids = out.sequences
                answer = self._processor.decode(generated_ids[0], skip_special_tokens=True).strip()

                # Calculate confidence score from beam transition scores if available
                confidence: float = 0.85
                if hasattr(out, "sequences_scores") and out.sequences_scores is not None:
                    confidence = float(torch.exp(out.sequences_scores[0]).clamp(0.01, 0.99).item())

            # Format natural, informative answer
            full_answer = f"{answer.capitalize()}."

            return ModelResult(
                model_name=self.name,
                task="vqa",
                answer=full_answer,
                confidence=confidence,
                metadata={
                    "model_class": "GeneralRSVLM-BLIP",
                    "prompt": prompt,
                    "raw_answer": answer,
                    "device": str(self.device)
                }
            )
        except Exception as e:
            logger.error(f"General RS-VLM inference failed: {e}", exc_info=True)
            raise InferenceError(f"General RS-VLM execution failed: {e}", model_name=self.name)
