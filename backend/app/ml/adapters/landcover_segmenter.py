"""Multi-class land-cover segmenter trained by `training/segmentation/train_landcover.py`.

The checkpoint dict is {"model", "arch", "encoder", "classes", "epoch", "val"}; the class names,
architecture and encoder all come from it, so both `landcover_dg_lv_oem` (ResNet-34) and a later
`landcover_full_r50` load without a code change.

Seven shared classes (other, built_up, agriculture, rangeland, forest, water, barren) merged across
DeepGlobe, LoveDA and OpenEarthMap; the merge is lossy by design (LoveDA's building and road both
become built_up). Trained at 0.5 m. Measured scores: project/qna.md Q-029.

Nothing routes to this adapter yet.
"""
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from backend.app.exceptions import InferenceError, InvalidInputError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.ml.adapters.binary_segmenter import normalise, to_rgb_array
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.device import warn_if_cpu_for_heavy_model
from backend.app.schemas.models import ModelResult


class LandCoverSegmenterAdapter(BaseModelAdapter):
    """RGB tile in; a per-class binary mask, a class-index map and per-class area shares out."""

    def __init__(self) -> None:
        super().__init__("landcover_segmenter")
        self._classes: Optional[List[str]] = None
        self._arch: Optional[str] = None
        self._encoder: Optional[str] = None

    @property
    def classes(self) -> List[str]:
        """Class names from the checkpoint; empty until the weights are loaded."""
        return list(self._classes) if self._classes else []

    def load(self) -> None:
        self.load_model()

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return
        self.ensure_available()

        from training.segmentation.datasets import LANDCOVER_CLASSES
        from training.segmentation.train_seg import build_model

        ckpt_file = self.checkpoint_path
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading land-cover segmenter from {ckpt_file} onto {self.device}...")
        try:
            ckpt = torch.load(str(ckpt_file), map_location="cpu", weights_only=False)
            if not isinstance(ckpt, dict) or "model" not in ckpt:
                raise ValueError(
                    f"Expected a trainer checkpoint dict with a 'model' key, got {type(ckpt).__name__}."
                )
            classes = list(ckpt.get("classes") or LANDCOVER_CLASSES)
            if len(classes) != len(LANDCOVER_CLASSES):
                # infer_logits() allocates its windowed accumulator from the trainer's K, so a
                # checkpoint with a different taxonomy needs the trainer updated, not the adapter.
                raise ValueError(
                    f"Checkpoint has {len(classes)} classes but training.segmentation.datasets."
                    f"LANDCOVER_CLASSES has {len(LANDCOVER_CLASSES)}; the two must agree."
                )
            self._arch = str(ckpt.get("arch", "unet"))
            self._encoder = str(ckpt.get("encoder", "resnet34"))

            model = build_model(self._arch, self._encoder)
            head = model.segmentation_head[0]
            model.segmentation_head[0] = torch.nn.Conv2d(
                head.in_channels, len(classes), head.kernel_size, padding=head.padding
            )
            model.load_state_dict(ckpt["model"], strict=True)
            model.to(self.device).eval()

            self._classes = classes
            self._model = model
            self._loaded = True
            logger.info(
                f"{self.name}: {self._arch}/{self._encoder}, {len(classes)} classes, "
                f"epoch {ckpt.get('epoch')}, val {ckpt.get('val')}."
            )
        except Exception as e:
            self._model = None
            self._loaded = False
            self._classes = None
            if isinstance(e, ModelUnavailableError):
                raise
            logger.error(f"Failed to load {self.name} checkpoint {ckpt_file}: {e}", exc_info=True)
            raise InferenceError(f"Failed to load {self.name} checkpoint: {e}", model_name=self.name)

    def unload(self) -> None:
        if self._model is not None:
            del self._model
        self._model = None
        self._loaded = False
        self._classes = None
        self._arch = self._encoder = None
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

    def predict(self, image_or_context: Any = None, **kwargs: Any) -> ModelResult:
        """
        Classifies every pixel of one RGB tile.

            adapter.predict(pil_or_ndarray_or_path)
            adapter.predict({"image": arr})

        Returns a ModelResult with one `masks` entry per class present in the prediction
        (`binary_mask` uint8 (H, W), `label`, `pixel_count`, `area_pct`), plus `class_map`
        (uint8 (H, W) of class indices) and `confidence_map` in the first entry. `metadata`
        carries `classes`, `area_pct` for every class (including zeros) and `dominant_class`.
        """
        if isinstance(image_or_context, dict):
            self.validate_inputs(image_or_context)
            raw = (image_or_context.get("image") or image_or_context.get("image_pil")
                   or image_or_context.get("image_path") or image_or_context.get("arr"))
        else:
            raw = image_or_context
        if raw is None:
            raise InvalidInputError(f"{self.name} requires an input image.")

        self.load_model()

        from training.segmentation.datasets import TARGET_GSD_M
        from training.segmentation.train_landcover import infer_logits

        img = to_rgb_array(raw)
        h, w = img.shape[:2]
        try:
            x = normalise(img).to(self.device)
            # infer_logits already returns per-class softmax probabilities, windowed if the tile is large.
            prob = infer_logits(self._model, x)[0].detach().cpu().numpy().astype(np.float32)
        except Exception as e:
            logger.error(f"{self.name} inference failed: {e}", exc_info=True)
            raise InferenceError(f"{self.name} inference failed: {e}", model_name=self.name)

        class_map = prob.argmax(0).astype(np.uint8)
        confidence_map = prob.max(0)
        total = int(class_map.size)
        classes = self.classes

        area_pct: Dict[str, float] = {}
        pixel_counts: Dict[str, int] = {}
        masks: List[Dict[str, Any]] = []
        for i, label in enumerate(classes):
            m = (class_map == i).astype(np.uint8)
            n = int(m.sum())
            pixel_counts[label] = n
            area_pct[label] = round(100.0 * n / total, 4) if total else 0.0
            if n:
                masks.append({
                    "binary_mask": m,
                    "label": label,
                    "class_index": i,
                    "pixel_count": n,
                    "area_pct": area_pct[label],
                    "mean_probability": round(float(prob[i][m > 0].mean()), 4),
                    "shape": [h, w],
                })
        masks.sort(key=lambda d: d["pixel_count"], reverse=True)
        if masks:
            masks[0]["class_map"] = class_map
            masks[0]["confidence_map"] = confidence_map

        dominant = masks[0]["label"] if masks else None
        summary = ", ".join(f"{d['label']} {d['area_pct']:.1f}%" for d in masks[:4])
        return ModelResult(
            model_name=self.name,
            task="land_cover_segmentation",
            answer=(
                f"Land cover over {total:,} pixels: {summary}."
                if masks else "Land-cover segmentation produced no classified pixels."
            ),
            confidence=float(confidence_map.mean()),
            masks=masks,
            metadata={
                "classes": classes,
                "area_pct": area_pct,
                "pixel_counts": pixel_counts,
                "dominant_class": dominant,
                "total_pixel_count": total,
                "arch": self._arch,
                "encoder": self._encoder,
                "trained_gsd_m": TARGET_GSD_M,
                "output_shape": [h, w],
                "device": str(self.device),
                "model_class": "smp.Unet",
            },
        )
