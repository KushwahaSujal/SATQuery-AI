"""Qwen3-VL-4B-Instruct (4-bit NF4) scene model: VQA and captions in full sentences (Q-021)."""
from typing import Any, Dict

import torch
from PIL import Image

from backend.app.exceptions import InferenceError, InvalidInputError
from backend.app.logging import logger
from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult

INSTRUCTION = (
    "You are analysing a satellite or aerial image. Answer only from what is visible. "
    "If something cannot be determined from the image, say so. Answer in one to three sentences."
)


class SceneVLMAdapter(BaseModelAdapter):
    def __init__(self):
        super().__init__("scene_vlm")
        self._processor = None

    def is_available(self) -> bool:
        # Pre-quantized bitsandbytes weights run on CUDA only; never auto-download ~9 GB during a request.
        if not self.config or not self.config.enabled or not torch.cuda.is_available():
            return False
        p = self.checkpoint_path
        return p is not None and p.exists()

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return
        self.ensure_available()
        from transformers import AutoModelForImageTextToText, AutoProcessor
        src = str(self.checkpoint_path)
        try:
            self._processor = AutoProcessor.from_pretrained(src)
            self._model = AutoModelForImageTextToText.from_pretrained(
                src, device_map={"": self.device.index or 0}, dtype=torch.float16
            ).eval()
            self._loaded = True
            logger.info(f"Scene VLM loaded from {src}.")
        except Exception as e:
            raise InferenceError(f"Failed to load Scene VLM: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if not isinstance(context.get("image_pil"), Image.Image):
            raise InvalidInputError("Scene VLM requires 'image_pil'.")

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()
        image = context["image_pil"].convert("RGB")
        image.thumbnail((1024, 1024))
        question = (context.get("query") or "Describe this image.").strip()
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": f"{INSTRUCTION}\n\n{question}"},
        ]}]
        try:
            inputs = self._processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt"
            ).to(self._model.device)
            with torch.inference_mode():
                out = self._model.generate(**inputs, max_new_tokens=200, do_sample=False)
            text = self._processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
        except Exception as e:
            logger.error(f"Scene VLM inference failed: {e}", exc_info=True)
            raise InferenceError(f"Scene VLM inference failed: {e}", model_name=self.name)
        return ModelResult(model_name=self.name, task="vqa", answer=text, confidence=None,
                           metadata={"model_class": "Qwen3-VL-4B-Instruct", "quantization": "bnb-nf4",
                                     "device": str(self.device)})
