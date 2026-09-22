"""Multi-class semantic segmenters trained by `training/segmentation/train_landcover.py`.

The checkpoint dict is {"model", "arch", "encoder", "classes", "epoch", "val"} and, for the newer
runs, "taxonomy" and "target_gsd". The class names, class *count*, architecture, encoder and
training resolution all come from the checkpoint, so one adapter class serves every taxonomy this
trainer produces; a subclass supplies only the registry key.

Two taxonomies are registered today:
  - `landcover_segmenter` — 7 classes (other, built_up, agriculture, rangeland, forest, water,
    barren) merged across DeepGlobe, LoveDA and OpenEarthMap, at 0.5 m. The merge is lossy by
    design (LoveDA's building and road both become built_up). Scores: project/qna.md Q-029, Q-037.
  - `isprs_potsdam_segmenter` / `isprs_vaihingen_segmenter` — 6 ISPRS classes (impervious,
    building, low_vegetation, tree, car, clutter) at 0.1 m. Two separate models because the cities
    disagree on their most discriminative cue: Potsdam is RGB (vegetation darker than roofs),
    Vaihingen is IRRG (vegetation brighter), so a shared first conv cannot serve both
    (project/qna.md Q-036).

Routing: none of these auto-route. A multi-class result does not fit `run_grounding_pipeline`'s
single-binary-mask response contract, and the ISPRS pair additionally cannot be auto-selected
without GSD and band metadata the pipeline does not have. They are registered so they are callable
directly. See docs/models/trained_segmenters.md.
"""
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from backend.app.exceptions import InferenceError, InvalidInputError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.ml.adapters.binary_segmenter import normalise, to_rgb_array, trainer_importable
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.device import warn_if_cpu_for_heavy_model
from backend.app.schemas.models import ModelResult


class LandCoverSegmenterAdapter(BaseModelAdapter):
    """RGB tile in; a per-class binary mask, a class-index map and per-class area shares out.

    Taxonomy-agnostic: the class list and its length come from the checkpoint, so subclassing for a
    different taxonomy (ISPRS's 6 urban classes) needs only a different registry key.
    """

    #: What this taxonomy's output is called in the answer; ISPRS's 6 urban classes are not
    #: "land cover" in the sense the 7-class model means it.
    _RESULT_NOUN = "Land cover"

    def __init__(self, model_key: str = "landcover_segmenter") -> None:
        super().__init__(model_key)
        self._classes: Optional[List[str]] = None
        self._arch: Optional[str] = None
        self._encoder: Optional[str] = None
        self._trained_gsd_m: Optional[float] = None

    def is_available(self) -> bool:
        """Enabled, weights on disk, and the trainer module importable."""
        return super().is_available() and trainer_importable()

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
            if not classes:
                raise ValueError("Checkpoint carries an empty class list; cannot size the head.")
            # No check that len(classes) matches the trainer's LANDCOVER_CLASSES. An earlier version
            # required it, on the grounds that infer_logits() sizes its windowed accumulator from the
            # trainer's K — that is not what it does: train_landcover.infer_logits reads
            # `K = model.segmentation_head[0].out_channels`, i.e. from the model this adapter builds
            # just below out of len(classes). So any K the checkpoint declares is self-consistent,
            # and the old check did nothing but lock the adapter to the 7-class taxonomy and reject
            # the 6-class ISPRS checkpoints (project/qna.md Q-036).
            self._arch = str(ckpt.get("arch", "unet"))
            self._encoder = str(ckpt.get("encoder", "resnet34"))
            gsd = ckpt.get("target_gsd")
            if gsd is None:
                gsd = getattr(self.config, "trained_gsd_m", None) if self.config else None
            self._trained_gsd_m = float(gsd) if gsd is not None else None

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
                f"{self.name}: {self._arch}/{self._encoder}, {len(classes)} classes "
                f"({ckpt.get('taxonomy', 'landcover')}), {self._trained_gsd_m} m/px, "
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
        self._trained_gsd_m = None
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
                f"{self._RESULT_NOUN} over {total:,} pixels: {summary}."
                if masks else f"{self._RESULT_NOUN} segmentation produced no classified pixels."
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
                "trained_gsd_m": self._trained_gsd_m,
                "output_shape": [h, w],
                "device": str(self.device),
                "model_class": "smp.Unet",
            },
        )


class IsprsPotsdamSegmenterAdapter(LandCoverSegmenterAdapter):
    """`isprs_potsdam_seg`: U-Net / ResNet-34, 6 ISPRS classes, **RGB** at 0.1 m (Q-036).

    Test mIoU 0.700 over 4 held-out tiles — a small test set, so the figure carries wide
    uncertainty and is not comparable to the ISPRS leaderboard (which scores on eroded boundaries
    and excludes clutter from its headline mean).

    Expects true-colour RGB. Feeding it Vaihingen-style IRRG inverts the vegetation/roof contrast
    it keys on, so the two ISPRS models are not interchangeable.
    """

    _RESULT_NOUN = "Urban semantic labelling"

    def __init__(self) -> None:
        super().__init__("isprs_potsdam_segmenter")


class IsprsVaihingenSegmenterAdapter(LandCoverSegmenterAdapter):
    """`isprs_vaihingen_seg`: U-Net / ResNet-34, 6 ISPRS classes, **IRRG** at 0.1 m (Q-036).

    Test mIoU 0.729 over 6 held-out tiles, same small-test-set caveat as Potsdam.

    Expects infrared/red/green composites, not RGB: on Vaihingen's IRRG, channel 0 makes vegetation
    *brighter* than buildings (ratio 1.23) where Potsdam's RGB makes it darker (0.65). Handing this
    model an ordinary RGB image is a band mismatch, not merely a domain shift.
    """

    _RESULT_NOUN = "Urban semantic labelling"

    def __init__(self) -> None:
        super().__init__("isprs_vaihingen_segmenter")
