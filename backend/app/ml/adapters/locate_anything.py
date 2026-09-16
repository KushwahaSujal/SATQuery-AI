from typing import Any, Dict, List, Optional, Tuple
import importlib.util
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

# End-of-turn token. Its absence from the decoded answer means the vendor generate
# loop stopped on max_new_tokens rather than on its own.
_IM_END = "<|im_end|>"

# Load / decoding defaults. All are overridable from configs/models.yaml
# (models.locate_anything.*) and, for decoding, per call via predict() kwargs.
# See the comments in configs/models.yaml for the measurements behind them.
_QUANTIZATION_CHOICES = ("none", "8bit", "4bit")
_DEFAULT_QUANTIZATION = "4bit"
_DEFAULT_GENERATION_MODE = "slow"
_DEFAULT_TEMPERATURE = 0.0
_DEFAULT_REPETITION_PENALTY = 1.0
# Modules kept in bf16 when quantizing: the MoonViT vision tower, the vision->LLM
# connector and the output head. Quantizing them costs accuracy for little memory.
_QUANT_SKIP_MODULES = ["vision_model", "mlp1", "lm_head"]


def is_truncated(answer_text: str) -> bool:
    """True when the answer never reached <|im_end|> (generation hit max_new_tokens)."""
    return _IM_END not in (answer_text or "")


def parse_boxes(
    answer_text: str,
    width: int,
    height: int,
    label: str,
    score: float = _DEFAULT_CONFIDENCE,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Parses LocateAnything ``<box><x1><y1><x2><y2></box>`` tokens into candidate dicts.

    Pure function (no model): coordinates are integers normalized to [0, 1000] in
    x1, y1, x2, y2 order; they are scaled to pixel coordinates of the ORIGINAL
    image and clipped to its bounds. The processor resizes each axis independently
    to a patch multiple, which normalized coordinates are invariant to.

    Dropped, and counted in the returned stats:
      * degenerate boxes -- x2 <= x1 or y2 <= y1 after clipping. The model always
        emits x1 < x2, y1 < y2, so a reversed or zero-area box is decoding noise,
        not a box to be re-ordered.
      * exact duplicates of an earlier box (same four normalized integers).

    ``<box>None</box>`` and 2-coordinate points are not matched by the regex.

    Returns ``(boxes, stats)`` with stats keys ``raw_box_count``,
    ``dropped_degenerate`` and ``dropped_duplicate``.
    """
    w, h = float(width), float(height)
    boxes: List[Dict[str, Any]] = []
    seen = set()
    raw = degenerate = duplicate = 0
    for match in _BOX_RE.finditer(answer_text or ""):
        raw += 1
        norm = tuple(int(g) for g in match.groups())
        x1n, y1n, x2n, y2n = norm

        x1 = max(0.0, min(x1n / _COORD_SCALE * w, w))
        y1 = max(0.0, min(y1n / _COORD_SCALE * h, h))
        x2 = max(0.0, min(x2n / _COORD_SCALE * w, w))
        y2 = max(0.0, min(y2n / _COORD_SCALE * h, h))
        if x2 <= x1 or y2 <= y1:
            degenerate += 1
            continue
        if norm in seen:
            duplicate += 1
            continue
        seen.add(norm)

        xyxy = [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]
        boxes.append({
            "xyxy": xyxy,
            "bbox": list(xyxy),
            "box_2d": [
                round(y1 / h, 4) if h else 0.0,
                round(x1 / w, 4) if w else 0.0,
                round(y2 / h, 4) if h else 1.0,
                round(x2 / w, 4) if w else 1.0,
            ],
            "score": score,
            "label": label,
        })
    stats = {
        "raw_box_count": raw,
        "dropped_degenerate": degenerate,
        "dropped_duplicate": duplicate,
    }
    return boxes, stats


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

    # ------------------------------------------------------------------ config

    def _cfg(self, field: str, default: Any) -> Any:
        value = getattr(self.config, field, None) if self.config else None
        return default if value is None else value

    @property
    def quantization(self) -> str:
        q = str(self._cfg("quantization", _DEFAULT_QUANTIZATION)).strip().lower()
        return "none" if q in ("", "null", "bf16", "bfloat16") else q

    def _missing_dependencies(self) -> List[str]:
        """Python packages the vendor remote code (or quantized loading) imports at load time."""
        required = ["transformers", "accelerate", "peft", "decord", "lmdb"]
        if self.quantization != "none":
            required.append("bitsandbytes")
        return [m for m in required if importlib.util.find_spec(m) is None]

    def _unavailable_reason(self) -> Optional[str]:
        if not self.config or not self.config.enabled:
            return "disabled in configs/models.yaml"
        if self.quantization not in _QUANTIZATION_CHOICES:
            return (
                f"invalid quantization '{self.quantization}' "
                f"(expected one of {', '.join(_QUANTIZATION_CHOICES)})"
            )
        missing = self._missing_dependencies()
        if missing:
            return f"missing Python packages: {', '.join(missing)}"
        return None

    def is_available(self) -> bool:
        """True only if enabled, the required packages import, and weights are reachable.

        Weights come from the local checkpoint repo, or the HF Hub id when that repo is
        absent (transformers downloads it on first load).
        """
        reason = self._unavailable_reason()
        if reason is not None:
            if self.config and self.config.enabled:
                logger.warning(f"LocateAnything unavailable: {reason}")
            return False
        return True

    def ensure_available(self) -> None:
        reason = self._unavailable_reason()
        if reason is not None:
            raise ModelUnavailableError(
                model_name=self.name,
                message=f"Model '{self.name}' is unavailable: {reason}.",
                details={
                    "model_key": self.model_key,
                    "reason": reason,
                    "quantization": self.quantization,
                    "expected_path": str(self.checkpoint_path) if self.checkpoint_path else None,
                },
            )

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
            from transformers import AutoModel, AutoProcessor, BitsAndBytesConfig

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
            # reference worker.
            #
            # Weights are bf16 (7.66 GB), which does not fit an 8 GB card next to a
            # desktop. `quantization` (configs/models.yaml) picks bitsandbytes 4-bit
            # nf4 or 8-bit for the Qwen2 decoder; the vision tower, connector and
            # lm_head always stay bf16. "none" loads bf16 and lets device_map="auto"
            # offload what does not fit to CPU.
            quantization = self.quantization
            load_kwargs: Dict[str, Any] = {
                "trust_remote_code": True,
                "dtype": torch.bfloat16,
                "device_map": "auto" if self.device.type == "cuda" else "cpu",
            }
            if quantization == "4bit":
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    llm_int8_skip_modules=list(_QUANT_SKIP_MODULES),
                )
            elif quantization == "8bit":
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_skip_modules=list(_QUANT_SKIP_MODULES),
                )

            first_error: Optional[str] = None
            try:
                self._model = AutoModel.from_pretrained(source, **load_kwargs).eval()
            except (torch.OutOfMemoryError, ValueError) as e:
                # A bitsandbytes model refuses to load when device_map="auto" would have to
                # put some layers on CPU (ValueError), and a full load can OOM outright. On an
                # 8 GB card that happens when other models are resident: release them (they
                # reload lazily) and retry once.
                if self.device.type != "cuda":
                    raise
                first_error = str(e)
            if first_error is not None:
                # Retry outside the except block: the live exception's traceback still
                # references the half-built first attempt, which would keep its VRAM pinned.
                import gc
                from backend.app.ml.registry import model_registry

                self._model = None
                released = model_registry.release_gpu_memory(exclude=("locate_anything",))
                gc.collect()
                torch.cuda.empty_cache()
                logger.warning(
                    f"LocateAnything load failed ({first_error[:120]}); released {released}, "
                    f"{torch.cuda.memory_allocated() / 2**30:.2f} GiB still allocated; retrying."
                )
                self._model = AutoModel.from_pretrained(source, **load_kwargs).eval()
            self._torch_dtype = torch.bfloat16
            self._loaded = True
            logger.info(
                f"LocateAnything processor and model weights loaded "
                f"(quantization={quantization}, dtype=bfloat16)."
            )
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
        temperature: Optional[float] = None,
        generation_mode: Optional[str] = None,
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

        Decoding defaults are deterministic (greedy, ``generation_mode="slow"``).
        ``generation_mode``, ``temperature``, ``max_new_tokens`` and the kwargs
        ``repetition_penalty``, ``top_p``, ``top_k`` override configs/models.yaml.
        Note the vendor sampler samples iff ``temperature > 0``; ``do_sample`` is
        ignored by it, so ``top_p``/``top_k`` are only forwarded when sampling.
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

        generation_mode = str(generation_mode or self._cfg("generation_mode", _DEFAULT_GENERATION_MODE))
        if generation_mode not in ("slow", "hybrid", "fast"):
            raise InvalidInputError(
                f"Unsupported LocateAnything generation_mode '{generation_mode}' (slow | hybrid | fast)."
            )
        temperature = float(
            temperature if temperature is not None else self._cfg("temperature", _DEFAULT_TEMPERATURE)
        )
        repetition_penalty = float(
            kwargs.get("repetition_penalty")
            or self._cfg("repetition_penalty", _DEFAULT_REPETITION_PENALTY)
        )
        max_new_tokens = int(
            max_new_tokens or self._cfg("max_new_tokens", self.DEFAULT_MAX_NEW_TOKENS)
        )
        sampling_kwargs: Dict[str, Any] = {"temperature": temperature}
        if temperature > 0:
            for key in ("top_p", "top_k"):
                if kwargs.get(key) is not None:
                    sampling_kwargs[key] = kwargs[key]

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
            model_device = next(self._model.parameters()).device
            inputs = self._processor(
                text=[text], images=images, videos=videos, return_tensors="pt"
            ).to(model_device)

            # Vision tower is never quantized and runs in bf16.
            pixel_values = inputs["pixel_values"].to(torch.bfloat16)
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
                max_new_tokens=max_new_tokens,
                use_cache=True,
                generation_mode=generation_mode,
                repetition_penalty=repetition_penalty,
                verbose=False,
                **sampling_kwargs,
            )

            answer_text = response[0] if isinstance(response, tuple) else response
            if not isinstance(answer_text, str):
                answer_text = str(answer_text)

            # 3. Parse <box><x1><y1><x2><y2></box> tokens into pixel boxes in the
            #    ORIGINAL image space (see parse_boxes).
            boxes, parse_stats = parse_boxes(answer_text, orig_w, orig_h, text_query)
            truncated = is_truncated(answer_text)
            if truncated:
                logger.warning(
                    f"LocateAnything hit max_new_tokens={max_new_tokens} without <|im_end|> "
                    f"for '{text_query}' ({parse_stats['raw_box_count']} raw boxes)."
                )

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
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "repetition_penalty": repetition_penalty,
                    "quantization": self.quantization,
                    "truncated": truncated,
                    **parse_stats,
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
