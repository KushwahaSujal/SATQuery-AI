from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import numpy as np
from PIL import Image
import torch

from backend.app.ml.base import BaseModelAdapter
from backend.app.exceptions import InvalidInputError, InferenceError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


class GroundingResult(dict):
    """
    Normalized result container for Grounding DINO detections.
    Supports both dictionary access (result["boxes"]) and attribute access (result.boxes).
    """
    def __init__(
        self,
        boxes: List[Dict[str, Any]],
        confidence: Optional[float],
        answer: str,
        model_name: str,
        metadata: Dict[str, Any]
    ):
        super().__init__(
            boxes=boxes,
            confidence=confidence,
            answer=answer,
            model_name=model_name,
            metadata=metadata
        )

    @property
    def boxes(self) -> List[Dict[str, Any]]:
        return self["boxes"]

    @property
    def confidence(self) -> Optional[float]:
        return self["confidence"]

    @property
    def answer(self) -> str:
        return self["answer"]

    @property
    def model_name(self) -> str:
        return self["model_name"]

    @property
    def task(self) -> str:
        return "grounding"

    @property
    def metadata(self) -> Dict[str, Any]:
        return self["metadata"]

    @property
    def masks(self) -> List[Dict[str, Any]]:
        return []


class GroundingDINOAdapter(BaseModelAdapter):
    """
    Production Adapter for Grounding DINO (IDEA-Research/grounding-dino-base).
    Provides zero-shot object grounding for remote sensing imagery without prompt reasoning.
    """
    DEFAULT_MODEL_ID = "IDEA-Research/grounding-dino-base"

    def __init__(self):
        super().__init__("grounding_dino")
        self._processor: Optional[Any] = None
        self.model_id = getattr(self.config, "model_id", self.DEFAULT_MODEL_ID) if self.config else self.DEFAULT_MODEL_ID

    def is_available(self) -> bool:
        """Checks if Grounding DINO dependencies and model weights are accessible."""
        if not self.config or not self.config.enabled:
            return False
        p = self.checkpoint_path
        if p is not None and p.exists():
            return True
        try:
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
            return True
        except ImportError:
            return False

    def load(self) -> None:
        """Public load interface. Lazily initializes processor and model weights."""
        self.load_model()

    def load_model(self) -> None:
        """Lazily loads Hugging Face Transformers Grounding DINO model and processor."""
        if self._loaded and self._model is not None and self._processor is not None:
            return

        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading Grounding DINO ({self.model_id}) onto device {self.device}...")

        try:
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

            # Load processor
            self._processor = AutoProcessor.from_pretrained(self.model_id)

            # Load model onto target device
            self._model = AutoModelForZeroShotObjectDetection.from_pretrained(self.model_id)
            self._model.to(self.device)
            self._model.eval()

            self._loaded = True
            logger.info("Grounding DINO processor and model weights loaded successfully.")
        except Exception as e:
            self._loaded = False
            self._model = None
            self._processor = None
            err_msg = f"Failed to load Grounding DINO model '{self.model_id}': {e}"
            logger.error(err_msg)
            raise ModelUnavailableError(
                model_name=self.name,
                message=err_msg,
                details={"model_id": self.model_id, "device": str(self.device)}
            ) from e

    def unload(self) -> None:
        """Releases model and processor weights and frees memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        self._loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info(f"Grounding DINO model unloaded from {self.device}.")

    def _normalize_prompt(self, prompt: str) -> str:
        """
        Normalizes text prompt according to official Grounding DINO requirements:
        lowercased and strictly ending with a period.
        """
        cleaned = prompt.strip().lower()
        if not cleaned.endswith("."):
            cleaned += "."
        return cleaned

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        """Validates input image and prompt parameters."""
        if "image" not in context and "image_pil" not in context and "image_path" not in context:
            raise InvalidInputError("Grounding DINO requires an input image (image, image_pil, or image_path).")
        prompt = context.get("prompt") or context.get("target_phrase") or context.get("query")
        if not prompt or not str(prompt).strip():
            raise InvalidInputError("Grounding DINO requires a non-empty text prompt.")

    def _extract_image(self, image_input: Any) -> Image.Image:
        """Converts various image input types into a standard RGB PIL Image."""
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        elif isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                raise InvalidInputError(f"Image file not found at '{p}'.")
            return Image.open(p).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if image_input.ndim == 2:
                return Image.fromarray(image_input).convert("RGB")
            elif image_input.ndim == 3:
                if image_input.shape[0] in (1, 3, 4) and image_input.shape[2] not in (1, 3, 4):
                    image_input = np.transpose(image_input, (1, 2, 0))
                if image_input.shape[2] == 4:
                    return Image.fromarray(image_input).convert("RGB")
                return Image.fromarray(image_input.astype(np.uint8)).convert("RGB")
        raise InvalidInputError(f"Unsupported image input type: {type(image_input)}")

    def predict(
        self,
        image_or_context: Any = None,
        prompt: Optional[str] = None,
        box_threshold: Optional[float] = None,
        text_threshold: Optional[float] = None,
        **kwargs: Any
    ) -> GroundingResult:
        """
        Performs Grounding DINO zero-shot object detection.

        Parameters:
            image_or_context: PIL Image, path, ndarray, or context dictionary.
            prompt: Text query phrase (e.g. "small vehicle.").
            box_threshold: Confidence threshold for candidate bounding boxes.
            text_threshold: Association threshold for text tokens.

        Returns:
            GroundingResult with normalized candidate boxes in original image coordinates:
            {
                "boxes": [
                    {
                        "xyxy": [x1, y1, x2, y2],
                        "score": float,
                        "label": str
                    }
                ]
            }
        """
        # Support context dictionary or direct arguments
        if isinstance(image_or_context, dict):
            ctx = image_or_context
            self.validate_inputs(ctx)
            raw_img = ctx.get("image") or ctx.get("image_pil") or ctx.get("image_path")
            prompt_str = ctx.get("prompt") or ctx.get("target_phrase") or ctx.get("query")
            box_thresh = ctx.get("box_threshold", box_threshold)
            text_thresh = ctx.get("text_threshold", text_threshold)
        else:
            raw_img = image_or_context
            prompt_str = prompt or kwargs.get("target_phrase") or kwargs.get("query")
            box_thresh = box_threshold
            text_thresh = text_threshold

        if raw_img is None:
            raise InvalidInputError("Grounding DINO requires an input image.")
        if not prompt_str or not str(prompt_str).strip():
            raise InvalidInputError("Grounding DINO requires a non-empty text prompt.")

        # Resolve thresholds
        if box_thresh is None:
            box_thresh = getattr(self.config, "box_threshold", 0.30) if self.config else 0.30
        if text_thresh is None:
            text_thresh = getattr(self.config, "text_threshold", 0.25) if self.config else 0.25

        box_thresh = float(box_thresh)
        text_thresh = float(text_thresh)

        # Lazy loading
        self.load_model()
        if self._model is None or self._processor is None:
            raise InferenceError("Grounding DINO model or processor is not initialized.", model_name=self.name)

        image_pil = self._extract_image(raw_img)
        orig_w, orig_h = image_pil.size
        normalized_prompt = self._normalize_prompt(prompt_str)

        try:
            # 1. Use official processor for image normalization, resize, and text tokenization
            inputs = self._processor(
                images=image_pil,
                text=normalized_prompt,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 2. Genuine model inference
            with torch.no_grad():
                outputs = self._model(**inputs)

            # 3. Post-process to original image pixel coordinate system [x1, y1, x2, y2]
            target_sizes = [(orig_h, orig_w)]
            kwargs_post = {
                "outputs": outputs,
                "input_ids": inputs["input_ids"],
                "target_sizes": target_sizes,
                "text_threshold": text_thresh,
            }
            import inspect
            sig = inspect.signature(self._processor.post_process_grounded_object_detection)
            if "box_threshold" in sig.parameters:
                kwargs_post["box_threshold"] = box_thresh
            else:
                kwargs_post["threshold"] = box_thresh

            processed = self._processor.post_process_grounded_object_detection(**kwargs_post)[0]

            det_boxes = processed["boxes"].detach().cpu().numpy()
            det_scores = processed["scores"].detach().cpu().numpy()
            det_labels = processed["labels"]

            boxes: List[Dict[str, Any]] = []
            for box, score, label in zip(det_boxes, det_scores, det_labels):
                x1, y1, x2, y2 = box.tolist()
                # Clip to original image boundaries
                x1 = max(0.0, min(float(x1), float(orig_w)))
                y1 = max(0.0, min(float(y1), float(orig_h)))
                x2 = max(0.0, min(float(x2), float(orig_w)))
                y2 = max(0.0, min(float(y2), float(orig_h)))

                # Normalized box [ymin, xmin, ymax, xmax] in [0, 1] for ToolRegistry
                norm_box_2d = [
                    y1 / orig_h if orig_h > 0 else 0.0,
                    x1 / orig_w if orig_w > 0 else 0.0,
                    y2 / orig_h if orig_h > 0 else 1.0,
                    x2 / orig_w if orig_w > 0 else 1.0
                ]

                candidate = {
                    "xyxy": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    "score": round(float(score), 4),
                    "label": str(label).strip(),
                    "box_2d": norm_box_2d
                }
                boxes.append(candidate)

            avg_conf = float(np.mean([b["score"] for b in boxes])) if boxes else None
            if boxes:
                answer = f"Grounding detected {len(boxes)} candidate instances matching '{prompt_str}'."
            else:
                answer = f"No candidate instances matching '{prompt_str}' were detected at box_threshold={box_thresh}."

            return GroundingResult(
                boxes=boxes,
                confidence=avg_conf,
                answer=answer,
                model_name=self.name,
                metadata={
                    "prompt": prompt_str,
                    "normalized_prompt": normalized_prompt,
                    "box_threshold": box_thresh,
                    "text_threshold": text_thresh,
                    "image_dimensions": {"width": orig_w, "height": orig_h},
                    "candidate_count": len(boxes),
                    "device": str(self.device)
                }
            )

        except Exception as e:
            if isinstance(e, (InvalidInputError, ModelUnavailableError)):
                raise e
            logger.error(f"Grounding DINO inference execution failed: {e}")
            raise InferenceError(f"Grounding DINO inference error: {e}", model_name=self.name) from e
