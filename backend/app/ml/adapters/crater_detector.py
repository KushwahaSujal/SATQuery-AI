"""Crater detector (ultralytics YOLO11s) trained by `training/detection/train_craters.py`.

Licence: **ultralytics is AGPL-3.0**. Serving this model from the backend over a network may carry
source-disclosure obligations; the user accepted that knowingly (project/qna.md Q-028). It is
therefore imported lazily inside `load_model()` and nowhere at module scope, so importing the model
registry never pulls an AGPL dependency into the process.

Single class ("crater"), trained on LU3M6TGT (Moon) plus a small Mars/Lunar set at 832 px with
`max_det=1000`, because LU3M6TGT craters are tiny (median box about 9 px) and dense (up to 506 per
tile). Boxes are returned in the Grounding DINO shape so downstream consumers need no special case.

Nothing routes to this adapter yet.
"""
import importlib.util
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from backend.app.exceptions import InferenceError, InvalidInputError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.ml.adapters.binary_segmenter import to_rgb_array
from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult


class CraterDetectorAdapter(BaseModelAdapter):
    """RGB tile in; crater bounding boxes with real model confidences out."""

    LABEL = "crater"
    #: Training resolution, and the detection cap that the dense lunar tiles need.
    _IMGSZ = 832
    _MAX_DET = 1000
    _DEFAULT_CONF = 0.25

    def __init__(self) -> None:
        super().__init__("crater_detector")
        self._imgsz: int = self._IMGSZ

    def is_available(self) -> bool:
        """Enabled, weights on disk, and ultralytics importable — never fabricated."""
        if not super().is_available():
            return False
        return importlib.util.find_spec("ultralytics") is not None

    @property
    def confidence_threshold(self) -> float:
        configured = self.config.box_threshold if self.config else None
        return float(configured) if configured is not None else self._DEFAULT_CONF

    def load(self) -> None:
        self.load_model()

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return
        self.ensure_available()

        # AGPL-3.0 dependency: imported only when the weights are actually being loaded.
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ModelUnavailableError(
                model_name=self.name,
                message="ultralytics (AGPL-3.0) is not installed; the crater detector cannot load.",
                details={"package": "ultralytics"},
            ) from e

        ckpt_file = self.checkpoint_path
        logger.info(f"Loading crater detector from {ckpt_file} onto {self.device}...")
        try:
            model = YOLO(str(ckpt_file))
            model.to(self.device)
            self._imgsz = int(self.config.input_size) if (self.config and self.config.input_size) else self._IMGSZ
            self._model = model
            self._loaded = True
            logger.info(f"Crater detector loaded (imgsz {self._imgsz}, classes {model.names}).")
        except Exception as e:
            self._model = None
            self._loaded = False
            logger.error(f"Failed to load crater detector {ckpt_file}: {e}", exc_info=True)
            raise InferenceError(f"Failed to load crater detector: {e}", model_name=self.name)

    def unload(self) -> None:
        if self._model is not None:
            del self._model
        self._model = None
        self._loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info(f"{self.name} unloaded from {self.device}.")

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if not isinstance(context, dict):
            raise InvalidInputError(f"{self.name} requires a context dictionary or an image.")
        if not any(context.get(k) is not None for k in ("image", "image_pil", "image_path", "arr")):
            raise InvalidInputError(
                f"{self.name} requires an input image ('image', 'image_pil', 'image_path' or 'arr')."
            )
        conf = context.get("confidence_threshold", context.get("box_threshold"))
        if conf is not None and not 0.0 < float(conf) <= 1.0:
            raise InvalidInputError(f"confidence_threshold must be in (0, 1], got {conf}.")

    def predict(self, image_or_context: Any = None, **kwargs: Any) -> ModelResult:
        """
        Detects craters in one RGB tile.

            adapter.predict(pil_or_ndarray_or_path, confidence_threshold=0.1)
            adapter.predict({"image": arr, "confidence_threshold": 0.1})

        Returns a ModelResult whose `boxes` follow the Grounding DINO shape:
        `{"xyxy": [x1, y1, x2, y2] in pixels, "score": float, "label": "crater",
        "box_2d": [ymin, xmin, ymax, xmax] normalised}`, sorted by descending score.
        """
        if isinstance(image_or_context, dict):
            self.validate_inputs(image_or_context)
            raw = (image_or_context.get("image") or image_or_context.get("image_pil")
                   or image_or_context.get("image_path") or image_or_context.get("arr"))
            conf = image_or_context.get("confidence_threshold", image_or_context.get("box_threshold"))
        else:
            raw = image_or_context
            conf = kwargs.get("confidence_threshold", kwargs.get("box_threshold"))
        if raw is None:
            raise InvalidInputError(f"{self.name} requires an input image.")
        if conf is not None and not 0.0 < float(conf) <= 1.0:
            raise InvalidInputError(f"confidence_threshold must be in (0, 1], got {conf}.")
        conf_thr = float(conf) if conf is not None else self.confidence_threshold

        self.load_model()
        img = to_rgb_array(raw)
        h, w = img.shape[:2]
        try:
            results = self._model.predict(
                source=img, imgsz=self._imgsz, conf=conf_thr, max_det=self._MAX_DET,
                device=str(self.device), verbose=False,
            )
        except Exception as e:
            logger.error(f"{self.name} inference failed: {e}", exc_info=True)
            raise InferenceError(f"Crater detection failed: {e}", model_name=self.name)

        boxes: List[Dict[str, Any]] = []
        for res in results:
            det = getattr(res, "boxes", None)
            if det is None or len(det) == 0:
                continue
            xyxy = det.xyxy.detach().cpu().numpy()
            scores = det.conf.detach().cpu().numpy()
            for (x1, y1, x2, y2), score in zip(xyxy, scores):
                x1 = float(np.clip(x1, 0.0, w)); x2 = float(np.clip(x2, 0.0, w))
                y1 = float(np.clip(y1, 0.0, h)); y2 = float(np.clip(y2, 0.0, h))
                boxes.append({
                    "xyxy": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    "score": round(float(score), 4),
                    "label": self.LABEL,
                    "box_2d": [y1 / h if h else 0.0, x1 / w if w else 0.0,
                               y2 / h if h else 1.0, x2 / w if w else 1.0],
                })
        boxes.sort(key=lambda b: b["score"], reverse=True)

        avg: Optional[float] = float(np.mean([b["score"] for b in boxes])) if boxes else None
        return ModelResult(
            model_name=self.name,
            task="detection",
            answer=(
                f"Detected {len(boxes)} craters at confidence threshold {conf_thr:.2f}."
                if boxes else f"No craters detected at confidence threshold {conf_thr:.2f}."
            ),
            confidence=avg,
            boxes=boxes,
            metadata={
                "label": self.LABEL,
                "confidence_threshold": conf_thr,
                "detection_count": len(boxes),
                "max_det": self._MAX_DET,
                "imgsz": self._imgsz,
                "image_dimensions": {"width": w, "height": h},
                "device": str(self.device),
                "model_class": "ultralytics.YOLO11s",
                "license": "AGPL-3.0 (ultralytics)",
            },
        )
