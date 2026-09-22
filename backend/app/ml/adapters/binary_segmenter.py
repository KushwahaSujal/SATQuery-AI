"""Binary aerial segmenters (roads, buildings) trained by `training/segmentation/train_seg.py`.

One adapter class serves both checkpoints; everything that differs (weights, foreground class
name, decision threshold, TTA) comes from `configs/models.yaml` and from the checkpoint itself.
The architecture, encoder and threshold are read from the checkpoint dict written by the trainer
({"model", "arch", "encoder", "threshold", "epoch", "val"}), so a re-trained checkpoint with a
different encoder loads without a code change.

Each checkpoint has its own training resolution, carried by `configs/models.yaml`'s
`trained_gsd_m` (the binary trainer records `--target-gsd` in report.json only, not in the
checkpoint): roads and buildings 0.5 m, water 10 m (Sentinel-2), cloud 30 m (Landsat 8). Inputs far
from a model's own resolution are outside its measured range; see docs/models/trained_segmenters.md.

Routing: roads and buildings (Q-038), and water and cloud (this change), dispatch from
`backend/app/workflows/trained_segmenter.py`.
"""
import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
from PIL import Image

from backend.app.exceptions import InferenceError, InvalidInputError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.device import warn_if_cpu_for_heavy_model
from backend.app.schemas.models import ModelResult


def trainer_importable() -> bool:
    """True when `training.segmentation` is on the path, which the segmenter adapters need.

    The trainer is part of this repository but the backend can be deployed without it (the Modal
    image ships `backend/` and `configs/` only), so availability is reported honestly instead of
    failing at the first request. find_spec imports the empty package __init__ files, not the
    trainer module itself, so this stays cheap.
    """
    try:
        return (importlib.util.find_spec("training.segmentation.train_seg") is not None
                and importlib.util.find_spec("training.segmentation.datasets") is not None)
    except (ImportError, ValueError):
        return False


def to_rgb_array(image_input: Any) -> np.ndarray:
    """Converts a PIL image, path or array into a uint8 RGB (H, W, 3) array."""
    if isinstance(image_input, Image.Image):
        return np.array(image_input.convert("RGB"), dtype=np.uint8)
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.is_file():
            raise InvalidInputError(f"Image file not found at '{p}'.")
        return np.array(Image.open(p).convert("RGB"), dtype=np.uint8)
    if isinstance(image_input, torch.Tensor):
        arr = image_input.detach().cpu().numpy()
        if arr.ndim == 4:
            arr = arr[0]
        return to_rgb_array(arr)
    if isinstance(image_input, np.ndarray):
        arr = image_input
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
        elif arr.ndim == 3 and arr.shape[0] in (1, 3, 4) and arr.shape[2] not in (1, 3, 4):
            arr = np.transpose(arr, (1, 2, 0))
        if arr.ndim != 3:
            raise InvalidInputError(f"Expected a 2-D or 3-D image array, got shape {arr.shape}.")
        if arr.shape[2] == 1:
            arr = np.repeat(arr, 3, axis=-1)
        elif arr.shape[2] > 3:
            arr = arr[:, :, :3]
        if arr.dtype != np.uint8:
            # Float arrays produced upstream are either [0, 1] or already [0, 255].
            arr = (arr * 255.0 if float(np.nanmax(arr)) <= 1.0 else arr).clip(0, 255).astype(np.uint8)
        return arr
    raise InvalidInputError(f"Unsupported image input type: {type(image_input)}")


def normalise(img: np.ndarray) -> torch.Tensor:
    """(H, W, 3) uint8 -> (1, 3, H, W) float32, with the trainer's ImageNet mean/std."""
    from training.segmentation.datasets import MEAN, STD

    x = ((img.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1)
    return torch.from_numpy(np.ascontiguousarray(x)).unsqueeze(0)


class BinarySegmenterAdapter(BaseModelAdapter):
    """
    Single-class U-Net segmenter: RGB tile in, probability map and binary mask out.

    Subclassed once per registered checkpoint (`RoadSegmenterAdapter`, `BuildingSegmenterAdapter`)
    so the registry can instantiate it with no arguments; the subclass supplies only the model key
    and a fallback class name.
    """

    #: Only used when neither the config nor the checkpoint names one.
    _FALLBACK_THRESHOLD = 0.5

    def __init__(self, model_key: str, class_name: str = "foreground"):
        super().__init__(model_key)
        self._fallback_class_name = class_name
        self._threshold: Optional[float] = None
        self._arch: Optional[str] = None
        self._encoder: Optional[str] = None

    def is_available(self) -> bool:
        """Enabled, weights on disk, and the trainer module importable."""
        return super().is_available() and trainer_importable()

    @property
    def class_name(self) -> str:
        configured = getattr(self.config, "class_name", None) if self.config else None
        return str(configured) if configured else self._fallback_class_name

    @property
    def tta(self) -> bool:
        """4-flip averaging: 4x slower, +0.005 to +0.012 test IoU (project/qna.md Q-032)."""
        configured = getattr(self.config, "tta", None) if self.config else None
        return bool(configured) if configured is not None else False

    @property
    def threshold(self) -> float:
        """Config threshold if set, else the one frozen on validation inside the checkpoint."""
        configured = self.config.threshold if self.config else None
        if configured is not None:
            return float(configured)
        if self._threshold is not None:
            return float(self._threshold)
        return self._FALLBACK_THRESHOLD

    @property
    def trained_gsd_m(self) -> float:
        """Metres/pixel this checkpoint was trained at.

        `train_seg.py` writes `--target-gsd` only into `report.json`'s args, never into the
        checkpoint dict, so unlike `threshold` there is nothing to read back from the weights:
        `configs/models.yaml` is the only machine-readable source. Getting this from config rather
        than the module-level default matters — roads and buildings are 0.5 m, but water is 10 m
        (Sentinel-2) and cloud 30 m (Landsat 8), so the old hard-coded `TARGET_GSD_M` would have
        under-reported water's training scale by 20x in the answer text (project/qna.md Q-035).
        """
        from training.segmentation.datasets import TARGET_GSD_M

        configured = getattr(self.config, "trained_gsd_m", None) if self.config else None
        return float(configured) if configured is not None else float(TARGET_GSD_M)

    def load(self) -> None:
        """Public load interface, as on the other adapters."""
        self.load_model()

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return
        self.ensure_available()

        # Imported here, not at module scope: segmentation_models_pytorch and albumentations are
        # training dependencies and cost seconds to import.
        from training.segmentation.train_seg import build_model

        ckpt_file = self.checkpoint_path
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading {self.name} segmenter from {ckpt_file} onto {self.device}...")
        try:
            ckpt = torch.load(str(ckpt_file), map_location="cpu", weights_only=False)
            if not isinstance(ckpt, dict) or "model" not in ckpt:
                raise ValueError(
                    f"Expected a trainer checkpoint dict with a 'model' key, got {type(ckpt).__name__}."
                )
            self._arch = str(ckpt.get("arch", "unet"))
            self._encoder = str(ckpt.get("encoder", "resnet34"))
            self._threshold = ckpt.get("threshold")

            model = build_model(self._arch, self._encoder)
            model.load_state_dict(ckpt["model"], strict=True)
            model.to(self.device).eval()
            self._model = model
            self._loaded = True
            logger.info(
                f"{self.name}: {self._arch}/{self._encoder}, epoch {ckpt.get('epoch')}, "
                f"threshold {self.threshold}, val {ckpt.get('val')}."
            )
        except Exception as e:
            self._model = None
            self._loaded = False
            if isinstance(e, ModelUnavailableError):
                raise
            logger.error(f"Failed to load {self.name} checkpoint {ckpt_file}: {e}", exc_info=True)
            raise InferenceError(f"Failed to load {self.name} checkpoint: {e}", model_name=self.name)

    def unload(self) -> None:
        """Releases the weights and returns the CUDA cache to the driver."""
        if self._model is not None:
            del self._model
        self._model = None
        self._loaded = False
        self._arch = self._encoder = None
        self._threshold = None
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
        thr = context.get("threshold")
        if thr is not None and not 0.0 < float(thr) < 1.0:
            raise InvalidInputError(f"threshold must be in (0, 1), got {thr}.")

    def _resolve_inputs(
        self, image_or_context: Any, kwargs: Dict[str, Any]
    ) -> Tuple[Any, Optional[float], Optional[bool]]:
        """Image plus the per-call threshold and TTA overrides (None when not given)."""
        if isinstance(image_or_context, dict):
            ctx = image_or_context
            self.validate_inputs(ctx)
            raw = ctx.get("image") or ctx.get("image_pil") or ctx.get("image_path")
            if raw is None:
                raw = ctx.get("arr")
            thr = ctx.get("threshold")
            tta = ctx.get("tta")
        else:
            raw = image_or_context
            thr = kwargs.get("threshold")
            tta = kwargs.get("tta")
        if raw is None:
            raise InvalidInputError(f"{self.name} requires an input image.")
        if thr is not None and not 0.0 < float(thr) < 1.0:
            raise InvalidInputError(f"threshold must be in (0, 1), got {thr}.")
        return raw, float(thr) if thr is not None else None, None if tta is None else bool(tta)

    def predict(self, image_or_context: Any = None, **kwargs: Any) -> ModelResult:
        """
        Segments one RGB tile.

            adapter.predict(pil_or_ndarray_or_path, threshold=0.4, tta=True)
            adapter.predict({"image": arr, "threshold": 0.4})

        Returns a ModelResult whose single `masks` entry holds `binary_mask` (uint8 (H, W)) and
        `probability_map` (float32 (H, W)); the pixel count, area percentage and the threshold
        actually used are in `metadata`.
        """
        raw, thr_override, tta_override = self._resolve_inputs(image_or_context, kwargs)
        # Loaded before the threshold is resolved: unless config or the caller overrides it, the
        # threshold is the one frozen on validation and stored in the checkpoint.
        self.load_model()
        thr = self.threshold if thr_override is None else thr_override
        tta = self.tta if tta_override is None else tta_override

        from training.segmentation.train_seg import infer_prob

        img = to_rgb_array(raw)
        h, w = img.shape[:2]
        try:
            x = normalise(img).to(self.device)
            prob = infer_prob(self._model, x, tta=tta)[0, 0].detach().cpu().numpy().astype(np.float32)
        except Exception as e:
            logger.error(f"{self.name} inference failed: {e}", exc_info=True)
            raise InferenceError(f"{self.name} inference failed: {e}", model_name=self.name)

        mask = (prob >= thr).astype(np.uint8)
        pixel_count = int(mask.sum())
        total = int(mask.size)
        coverage_pct = 100.0 * pixel_count / total if total else 0.0
        # Mean foreground probability where the model fired; the background mean otherwise, so the
        # number always describes the prediction that was actually made.
        confidence = float(prob[mask > 0].mean()) if pixel_count else float(1.0 - prob.mean())

        return ModelResult(
            model_name=self.name,
            task="segmentation",
            answer=(
                f"{self.class_name.capitalize()} segmentation covers {pixel_count:,} of {total:,} pixels "
                f"({coverage_pct:.2f}% of the tile) at threshold {thr:.2f}."
            ),
            confidence=confidence,
            masks=[{
                "binary_mask": mask,
                "probability_map": prob,
                "label": self.class_name,
                "pixel_count": pixel_count,
                "shape": [h, w],
            }],
            metadata={
                "class_name": self.class_name,
                "threshold": thr,
                "threshold_source": (
                    "request" if thr_override is not None
                    else "config" if (self.config and self.config.threshold is not None)
                    else "checkpoint" if self._threshold is not None
                    else "default"
                ),
                "pixel_count": pixel_count,
                "total_pixel_count": total,
                "coverage_pct": round(coverage_pct, 4),
                "tta": tta,
                "arch": self._arch,
                "encoder": self._encoder,
                "trained_gsd_m": self.trained_gsd_m,
                "output_shape": [h, w],
                "device": str(self.device),
                "model_class": "smp.Unet",
            },
        )


class RoadSegmenterAdapter(BinarySegmenterAdapter):
    """`roads_all_r50`: U-Net / ResNet-50 on DeepGlobe + Massachusetts + SpaceNet-3 (Q-030, Q-032)."""

    def __init__(self) -> None:
        super().__init__("roads_segmenter", class_name="road")


class BuildingSegmenterAdapter(BinarySegmenterAdapter):
    """`buildings_whu_ma_r50`: U-Net / ResNet-50 on WHU Building + Massachusetts (Q-026, Q-032)."""

    def __init__(self) -> None:
        super().__init__("buildings_segmenter", class_name="building")


class WaterSegmenterAdapter(BinarySegmenterAdapter):
    """`water_seg`: U-Net / ResNet-34 on the Kaggle Water Bodies set, Sentinel-2 at 10 m (Q-035).

    Headline pooled test IoU is 0.475, but that number is a pixel-weighted artefact of a tile set
    whose areas span ~4000x: per tile the median is 0.866 and the mean 0.772, with 1 of 131 test
    tiles below 0.05 IoU (Q-035 §2). The per-tile figures are the ones that describe what a user
    sees on one image.
    """

    def __init__(self) -> None:
        super().__init__("water_segmenter", class_name="water")


class CloudSegmenterAdapter(BinarySegmenterAdapter):
    """`cloud_seg`: U-Net / ResNet-34 on 95-Cloud, Landsat 8 at 30 m (Q-035).

    Pooled test IoU 0.703, split by Landsat scene id so neighbouring patches cannot leak across
    splits. The val->test recall drop (0.93 -> 0.74) is recorded as an open question in Q-035, not
    an explained effect.
    """

    def __init__(self) -> None:
        super().__init__("cloud_segmenter", class_name="cloud")
