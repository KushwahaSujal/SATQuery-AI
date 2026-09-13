from typing import Any, Dict, List, Optional
from pathlib import Path
import re
import numpy as np
from PIL import Image
import torch

from backend.app.ml.base import BaseModelAdapter
from backend.app.exceptions import InvalidInputError, InferenceError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


class LocateAnythingResult(dict):
    """
    Normalized result container for LocateAnything detections.

    Mirrors ``GroundingDINOAdapter.GroundingResult`` so the production grounding
    pipeline (``workflows/grounding.py``) and the V4 reasoner consume it
    identically: ``result.get("boxes", [])`` and ``box["xyxy"]``.
    Supports both dictionary and attribute access.
    """

    def __init__(
        self,
        boxes: List[Dict[str, Any]],
        confidence: Optional[float],
        answer: str,
        model_name: str,
        metadata: Dict[str, Any],
    ):
        super().__init__(
            boxes=boxes,
            confidence=confidence,
            answer=answer,
            model_name=model_name,
            metadata=metadata,
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


# LocateAnything emits structured boxes as: <box><x1><y1><x2><y2></box>
# where each coordinate is a quantized token in [0, 1000] (coord_start..coord_end).
# Only 4-coordinate boxes are matched; 2-coordinate points (<box><x><y></box>)
# and empty boxes (<box>none</box>) are intentionally ignored for detection.
_BOX_RE = re.compile(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>")

# Coordinates are normalized integers in [0, 1000]; scale back to a 0..1 fraction.
_COORD_SCALE = 1000.0

# LocateAnything does not emit per-instance confidence in its text output. A
# neutral default is used -- it also matches the V4 reasoner's own default when
# a candidate score is absent (rank_v4_candidates falls back to 0.5).
_DEFAULT_CONFIDENCE = 0.5


class LocateAnythingAdapter(BaseModelAdapter):
    """
    Production adapter for LocateAnything-3B (nvidia/LocateAnything-3B).

    A Qwen2.5-3B + MoonViT vision-language model that performs open-vocabulary
    visual grounding by emitting structured ``<box><x1><y1><x2><y2></box>``
    coordinate tokens via a custom Multi-Token-Prediction (MTP) generator.

    The adapter wraps the model's reference prompt template and parser so it
    yields the same normalized candidate dicts that SatQuery's grounding
    pipeline, V4 reasoner, and evidence engine already expect.
    """
    DEFAULT_MODEL_ID = "nvidia/LocateAnything-3B"
    DEFAULT_MAX_NEW_TOKENS = 2048

    def __init__(self):
        super().__init__("locate_anything")
        self._processor: Optional[Any] = None
        self._tokenizer = None
        self._torch_dtype: Optional[torch.dtype] = None
        # HF hub id used for metadata; loading prefers the local checkpoint repo.
        self.model_id = getattr(self.config, "model_id", None) or self.DEFAULT_MODEL_ID

    def is_available(self) -> bool:
        """True only if enabled AND the local checkpoint repo (or deps) are usable."""
        if not self.config or not self.config.enabled:
            return False
        p = self.checkpoint_path
        if p is not None and p.exists():
            return True
        try:
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def load(self) -> None:
        """Public lazy-load entry point (matches GroundingDINO / SAM2 naming)."""
        self.load_model()

    def load_model(self) -> None:
        """Lazily loads the LocateAnything processor + model onto the selected device."""
        if self._loaded and self._model is not None and self._processor is not None:
            return

        self.ensure_available()
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading LocateAnything ({self.model_id}) onto device {self.device}...")

        try:
            from transformers import AutoModel, AutoProcessor

            # Prefer the on-disk HF checkpoint repo (offline-capable); fall back
            # to the Hub id only if the local repo is missing.
            source = (
                str(self.checkpoint_path)
                if (self.checkpoint_path and self.checkpoint_path.exists())
                else self.model_id
            )

            self._processor = AutoProcessor.from_pretrained(
                source, trust_remote_code=True
            )
            self._tokenizer = self._processor.tokenizer

            # NOTE: use AutoModel (NOT AutoModelForCausalLM). The model's config
            # only registers `AutoModel` -> `LocateAnythingForConditionalGeneration`
            # in its `auto_map`. AutoModelForCausalLM has no mapping for this custom
            # architecture and would refuse to load it. This mirrors the model's own
            # reference worker. `.to(device)` (not device_map) is used because the
            # custom MTP generate loop assumes a single device for kv-cache indexing.
            self._model = (
                AutoModel.from_pretrained(source, torch_dtype="auto", trust_remote_code=True)
                .to(self.device)
                .eval()
            )
            self._torch_dtype = next(self._model.parameters()).dtype
            self._loaded = True
            logger.info("LocateAnything processor and model weights loaded successfully.")
        except Exception as e:
            self._loaded = False
            self._model = None
            self._processor = None
            self._tokenizer = None
            self._torch_dtype = None
            err_msg = f"Failed to load LocateAnything model '{self.model_id}': {e}"
            logger.error(err_msg)
            raise ModelUnavailableError(
                model_name=self.name,
                message=err_msg,
                details={
                    "model_id": self.model_id,
                    "source": source if 'source' in locals() else None,
                    "device": str(self.device),
                },
            ) from e

    def unload(self) -> None:
        """Releases processor, tokenizer, model weights and frees VRAM where possible."""
        if getattr(self, "_model", None) is not None:
            del self._model
            self._model = None
        if getattr(self, "_processor", None) is not None:
            del self._processor
            self._processor = None
        if getattr(self, "_tokenizer", None) is not None:
            del self._tokenizer
            self._tokenizer = None
        self._torch_dtype = None
        self._loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info(f"LocateAnything model unloaded from {self.device}.")

    def _extract_image(self, image_input: Any) -> Image.Image:
        """Converts various image input types into a standard RGB PIL Image."""
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                raise InvalidInputError(f"Image file not found at '{p}'.")
            return Image.open(p).convert("RGB")
        if isinstance(image_input, np.ndarray):
            arr = image_input
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            elif arr.ndim == 3 and arr.shape[0] in (1, 3, 4) and arr.shape[2] not in (1, 3, 4):
                arr = np.transpose(arr, (1, 2, 0))
            if arr.shape[2] == 4:
                arr = arr[:, :, :3]
            return Image.fromarray(arr.astype(np.uint8)).convert("RGB")
        raise InvalidInputError(f"Unsupported image input type: {type(image_input)}")

    def _resolve_query(self, text_query: Optional[str], kwargs: Dict[str, Any]) -> str:
        for candidate in (text_query, kwargs.get("query"), kwargs.get("prompt"), kwargs.get("target_phrase")):
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        return ""

    @staticmethod
    def _format_prompt(query: str) -> str:
        """Builds a LocateAnything multi-instance grounding prompt.

        Matches the model's reference `ground_multi` template:
            "Locate all the instances that match the following description: {query}."
        """
        q = query.strip().rstrip(".").strip()
        return f"Locate all the instances that match the following description: {q}."

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        """Validates that an input image and a non-empty text query are present."""
        if "image" not in context and "image_pil" not in context and "image_path" not in context:
            raise InvalidInputError(
                "LocateAnything requires an input image (image, image_pil, or image_path)."
            )
        prompt = (
            context.get("text_query")
            or context.get("prompt")
            or context.get("target_phrase")
            or context.get("query")
        )
        if not prompt or not str(prompt).strip():
            raise InvalidInputError("LocateAnything requires a non-empty text query.")

    def predict(
        self,
        image_or_context: Any = None,
        text_query: Optional[str] = None,
        box_threshold: Optional[float] = None,
        text_threshold: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
        temperature: float = 0.7,
        generation_mode: str = "hybrid",
        **kwargs: Any,
    ) -> LocateAnythingResult:
        """
        Performs LocateAnything open-vocabulary visual grounding.

        Accepts either a context dictionary (codebase convention, e.g.
        ``{"image_pil": img, "query": "vehicle"}``) or direct arguments
        (``predict(image, "vehicle")``), so it is a drop-in replacement for
        ``GroundingDINOAdapter.predict`` in the production grounding pipeline.

        Returns a ``LocateAnythingResult`` whose ``boxes`` is a list of:
            {"xyxy":   [x1, y1, x2, y2]  (pixel coords, original image space),
             "bbox":   [x1, y1, x2, y2]  (alias of xyxy),
             "box_2d": [ymin, xmin, ymax, xmax] (normalized 0..1),
             "score":  float,
             "label":  str}
        """
        # Support a context dictionary OR direct (image, text_query) arguments.
        if isinstance(image_or_context, dict):
            ctx = image_or_context
            self.validate_inputs(ctx)
            raw_img = ctx.get("image") or ctx.get("image_pil") or ctx.get("image_path")
            text_query = self._resolve_query(
                ctx.get("text_query") or ctx.get("prompt") or ctx.get("target_phrase") or ctx.get("query"),
                {},
            )
        else:
            raw_img = image_or_context
            text_query = self._resolve_query(text_query, kwargs)

        if raw_img is None:
            raise InvalidInputError("LocateAnything requires an input image.")
        if not text_query or not str(text_query).strip():
            raise InvalidInputError("LocateAnything requires a non-empty text query.")

        # Lazy model loading (genuine weight load, not a stub).
        self.load_model()
        if self._model is None or self._processor is None or self._tokenizer is None:
            raise InferenceError("LocateAnything model/processor is not initialized.", model_name=self.name)

        image_pil = self._extract_image(raw_img)
        orig_w, orig_h = image_pil.size
        prompt = self._format_prompt(text_query)

        try:
            # 1. Format inputs using LocateAnything's chat template / prompt template.
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image_pil},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            text = self._processor.py_apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            images, videos = self._processor.process_vision_info(messages)
            inputs = self._processor(
                text=[text], images=images, videos=videos, return_tensors="pt"
            ).to(self.device)

            pixel_values = inputs["pixel_values"].to(self._torch_dtype)
            input_ids = inputs["input_ids"]
            attention_mask = inputs.get("attention_mask")
            image_grid_hws = inputs.get("image_grid_hws")

            # 2. Run genuine model inference (LocateAnything's custom MTP/hybrid generator).
            response = self._model.generate(
                pixel_values=pixel_values,
                input_ids=input_ids,
                attention_mask=attention_mask,
                image_grid_hws=image_grid_hws,
                tokenizer=self._tokenizer,
                max_new_tokens=max_new_tokens or self.DEFAULT_MAX_NEW_TOKENS,
                use_cache=True,
                generation_mode=generation_mode,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                repetition_penalty=1.1,
                verbose=False,
            )

            answer_text = response[0] if isinstance(response, tuple) else response
            if not isinstance(answer_text, str):
                answer_text = str(answer_text)

            # 3. Parse structured <box><x1><y1><x2><y2></box> output tokens.
            # 4. Convert normalized [0,1000] coords to [x1, y1, x2, y2] pixel coords
            #    in the ORIGINAL image space (the image processor resizes
            #    proportionally, so normalized coords map back to the source image).
            boxes: List[Dict[str, Any]] = []
            for match in _BOX_RE.finditer(answer_text):
                x1n, y1n, x2n, y2n = (int(g) for g in match.groups())

                x1 = x1n / _COORD_SCALE * orig_w
                y1 = y1n / _COORD_SCALE * orig_h
                x2 = x2n / _COORD_SCALE * orig_w
                y2 = y2n / _COORD_SCALE * orig_h

                # Sanitize ordering and clip to image bounds.
                x1 = max(0.0, min(float(x1), float(orig_w)))
                x2 = max(0.0, min(float(x2), float(orig_w)))
                y1 = max(0.0, min(float(y1), float(orig_h)))
                y2 = max(0.0, min(float(y2), float(orig_h)))
                x_lo, x_hi = (x1, x2) if x1 <= x2 else (x2, x1)
                y_lo, y_hi = (y1, y2) if y1 <= y2 else (y2, y1)

                boxes.append({
                    "xyxy": [round(x_lo, 2), round(y_lo, 2), round(x_hi, 2), round(y_hi, 2)],
                    "bbox": [round(x_lo, 2), round(y_lo, 2), round(x_hi, 2), round(y_hi, 2)],
                    "box_2d": [
                        round(y_lo / orig_h, 4) if orig_h else 0.0,
                        round(x_lo / orig_w, 4) if orig_w else 0.0,
                        round(y_hi / orig_h, 4) if orig_h else 1.0,
                        round(x_hi / orig_w, 4) if orig_w else 1.0,
                    ],
                    "score": _DEFAULT_CONFIDENCE,
                    "label": text_query,
                })

            avg_conf = float(np.mean([b["score"] for b in boxes])) if boxes else None
            if boxes:
                answer = (
                    f"LocateAnything detected {len(boxes)} instance(s) matching '{text_query}'."
                )
            else:
                answer = (
                    f"LocateAnything found no box instances matching '{text_query}' in the image."
                )

            return LocateAnythingResult(
                boxes=boxes,
                confidence=avg_conf,
                answer=answer,
                model_name=self.name,
                metadata={
                    "prompt": prompt,
                    "query": text_query,
                    "generation_mode": generation_mode,
                    "max_new_tokens": max_new_tokens or self.DEFAULT_MAX_NEW_TOKENS,
                    "temperature": temperature,
                    "image_dimensions": {"width": orig_w, "height": orig_h},
                    "coord_scale": int(_COORD_SCALE),
                    "candidate_count": len(boxes),
                    "confidence_note": (
                        "LocateAnything emits structural coordinate tokens without calibrated "
                        "per-instance confidence; a neutral default is used."
                    ),
                    "raw_answer": answer_text,
                    "device": str(self.device),
                },
            )
        except (InvalidInputError, ModelUnavailableError):
            raise
        except Exception as e:
            logger.error(f"LocateAnything inference execution failed: {e}", exc_info=True)
            raise InferenceError(
                f"LocateAnything inference error: {e}", model_name=self.name
            ) from e
