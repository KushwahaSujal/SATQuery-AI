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

    def __init__(self, model_key: str = "grounding_dino"):
        super().__init__(model_key)
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

        # Lazy loading. Local references: a concurrent release_gpu_memory() (video runs in its own thread) may
        # null self._model mid-call, which would turn a recoverable OOM into a NoneType error.
        self.load_model()
        model, processor = self._model, self._processor
        if model is None or processor is None:
            raise InferenceError("Grounding DINO model or processor is not initialized.", model_name=self.name)

        image_pil = self._extract_image(raw_img)
        orig_w, orig_h = image_pil.size
        normalized_prompt = self._normalize_prompt(prompt_str)

        try:
            # 1. Use official processor for image normalization, resize, and text tokenization
            inputs = processor(
                images=image_pil,
                text=normalized_prompt,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 2. Genuine model inference
            with torch.no_grad():
                outputs = model(**inputs)

            # 3. Post-process to original image pixel coordinate system [x1, y1, x2, y2]
            target_sizes = [(orig_h, orig_w)]
            kwargs_post = {
                "outputs": outputs,
                "input_ids": inputs["input_ids"],
                "target_sizes": target_sizes,
                "text_threshold": text_thresh,
            }
            import inspect
            sig = inspect.signature(processor.post_process_grounded_object_detection)
            if "box_threshold" in sig.parameters:
                kwargs_post["box_threshold"] = box_thresh
            else:
                kwargs_post["threshold"] = box_thresh

            processed = processor.post_process_grounded_object_detection(**kwargs_post)[0]

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
                    "device": str(self.device),
                    "model_key": self.model_key,
                    "model_id": self.model_id,
                }
            )

        except Exception as e:
            if isinstance(e, (InvalidInputError, ModelUnavailableError)):
                raise e
            logger.error(f"Grounding DINO inference execution failed: {e}")
            raise InferenceError(f"Grounding DINO inference error: {e}", model_name=self.name) from e


class GroundingDINOReferringAdapter(GroundingDINOAdapter):
    """Grounding DINO base fine-tuned on leak-free DIOR-RSVG referring expressions (project/qna.md Q-079..Q-084).

    It reads the *full* referring expression ("the small vehicle on the top-left") and its single top-scoring box
    is the answer; the pipeline answers "not found" below settings.referring_grounding.score_threshold. Measured on
    two disjoint VRSBench-val samples: Acc@0.5 0.338 -> 0.525 and 0.298 -> 0.505 over today's pipeline, absent-object
    boxes 87.3% -> 59.3% and 85.0% -> 59.7% (Q-081, Q-083).

    Weights are local only (checkpoint_path, resolved against settings.root_dir, never the working directory) and
    never fall through to the Hub: a missing directory makes is_available() False, which the pipeline turns into a
    logged fallback to the base path. predict_referring() reproduces the measured scoring exactly - base processor,
    fp16 autocast on CUDA, per-query score = max token sigmoid, no box/text post-processing threshold - because
    post_process_grounded_object_detection's fp32 scores near 0.35 would move the operating point.
    """
    REQUIRED_FILES = ("config.json", "model.safetensors")

    def __init__(self) -> None:
        super().__init__("grounding_dino_referring")
        self.processor_id = (getattr(self.config, "processor_id", None) if self.config else None) or self.DEFAULT_MODEL_ID
        self.model_id = str(self.checkpoint_path) if self.checkpoint_path else None

    def is_available(self) -> bool:
        if not self.config or not self.config.enabled:
            return False
        p = self.checkpoint_path
        if p is None or not p.is_dir() or not all((p / f).is_file() for f in self.REQUIRED_FILES):
            return False
        try:
            from transformers import AutoModelForZeroShotObjectDetection  # noqa: F401
            return True
        except ImportError:
            return False

    def load_model(self) -> None:
        if self._loaded and self._model is not None and self._processor is not None:
            return
        if not self.is_available():
            raise ModelUnavailableError(
                model_name=self.name,
                message=f"Referring-expression Grounding DINO weights not found at {self.checkpoint_path}.",
                details={"model_key": self.model_key, "expected_path": str(self.checkpoint_path),
                         "required_files": list(self.REQUIRED_FILES)},
            )
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading referring-expression Grounding DINO ({self.checkpoint_path}) onto {self.device}...")
        try:
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

            self._processor = AutoProcessor.from_pretrained(self.processor_id)
            self._model = AutoModelForZeroShotObjectDetection.from_pretrained(str(self.checkpoint_path),
                                                                              local_files_only=True)
            self._model.to(self.device)
            self._model.eval()
            self._loaded = True
        except Exception as e:
            self._loaded, self._model, self._processor = False, None, None
            err_msg = f"Failed to load referring-expression Grounding DINO from {self.checkpoint_path}: {e}"
            logger.error(err_msg)
            raise ModelUnavailableError(model_name=self.name, message=err_msg,
                                        details={"model_key": self.model_key, "model_id": self.model_id}) from e

    @torch.no_grad()
    def predict_referring(self, image: Any, expression: str, top_k: int = 20) -> GroundingResult:
        """Boxes for one referring expression, highest score first, scored exactly as measured (see class doc)."""
        if not expression or not str(expression).strip():
            raise InvalidInputError("The referring-expression detector requires a non-empty expression.")
        self.load_model()
        model, processor = self._model, self._processor
        if model is None or processor is None:
            raise InferenceError("Referring-expression Grounding DINO is not initialized.", model_name=self.name)
        image_pil = self._extract_image(image)
        w, h = image_pil.size
        text = str(expression).lower().strip().rstrip(".").strip() + "."
        use_amp = torch.device(self.device).type == "cuda"
        try:
            inputs = {k: v.to(self.device) for k, v in processor(images=image_pil, text=[text], return_tensors="pt").items()}
            with torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
                out = model(**inputs)
            scores = out.logits.sigmoid().float().max(-1).values[0]
            order = scores.argsort(descending=True)[:top_k]
            boxes: List[Dict[str, Any]] = []
            for q in order.tolist():
                cx, cy, bw, bh = out.pred_boxes[0, q].float().tolist()
                x1, y1 = max(0.0, (cx - bw / 2) * w), max(0.0, (cy - bh / 2) * h)
                x2, y2 = min(float(w), (cx + bw / 2) * w), min(float(h), (cy + bh / 2) * h)
                boxes.append({"xyxy": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                              "score": round(float(scores[q]), 4), "label": "referring",
                              "box_2d": [y1 / h if h else 0.0, x1 / w if w else 0.0, y2 / h if h else 1.0, x2 / w if w else 1.0]})
        except Exception as e:
            if isinstance(e, (InvalidInputError, ModelUnavailableError)):
                raise
            raise InferenceError(f"Referring-expression Grounding DINO inference error: {e}", model_name=self.name) from e
        return GroundingResult(
            boxes=boxes,
            confidence=boxes[0]["score"] if boxes else None,
            answer=f"Top referring-expression box scores {boxes[0]['score']:.3f}." if boxes else "No box proposed.",
            model_name=self.name,
            metadata={"expression_sent": text, "image_dimensions": {"width": w, "height": h}, "top_k": top_k,
                      "autocast_fp16": use_amp, "device": str(self.device), "model_key": self.model_key,
                      "model_id": self.model_id, "processor_id": self.processor_id},
        )
