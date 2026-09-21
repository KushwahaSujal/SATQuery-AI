"""EuroSAT scene-level land-cover classifier (EfficientNet-B0), trained by Ayushman.

Scene classification, not segmentation: one label for the whole tile. It cannot localise anything,
so it is registered and callable but deliberately not routed from the grounding pipeline — that
pipeline's response contract is a mask or a box, and this model produces neither. See
docs/models/eurosat/ for the delivery and project/qna.md Q-041.

The architecture is torchvision's `efficientnet_b0` with the 1000-way head replaced by a
`Linear(1280, len(class_names))`; the class names, the training image size and the best validation
accuracy are read from the checkpoint dict ({"model_state_dict", "class_names", "image_size",
"best_val_accuracy", "epoch"}) rather than hard-coded, so a re-trained checkpoint with a different
label set loads without a code change.

Measured on the delivered held-out test split (4050 samples, docs/models/eurosat/evaluation/):
accuracy 0.9832, balanced accuracy 0.9824, macro ROC-AUC 0.9996. Those numbers were recomputed
from the delivered per-sample predictions and matched the delivered report exactly (Q-041 §4); the
EuroSAT images themselves are not in this repository, so the score has NOT been re-measured here
from pixels.

Resolution: EuroSAT RGB tiles are Sentinel-2 at 10 m/px, 64x64, upsampled to 224 for training. Its
accuracy on sub-metre aerial photography has NOT been measured.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from PIL import Image

from backend.app.exceptions import InferenceError, InvalidInputError
from backend.app.logging import logger
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.device import warn_if_cpu_for_heavy_model
from backend.app.schemas.models import ModelResult

#: ImageNet statistics, as recorded in the delivery's inference_config.json. Kept here because that
#: file is documentation and is not read at runtime; changing one without the other would silently
#: break serving, so the doc cross-references this constant.
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

#: Ground sampling distance the tiles were captured at (Sentinel-2), metres/pixel.
EUROSAT_GSD_M = 10.0

#: Only used when the checkpoint carries no `image_size`.
_FALLBACK_IMAGE_SIZE = 224


def to_rgb_array(image_input: Any) -> np.ndarray:
    """Converts a PIL image, path, tensor or array into a uint8 RGB (H, W, 3) array."""
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
        if arr.ndim == 4:
            arr = arr[0]
        if arr.ndim == 3 and arr.shape[0] in (1, 3, 4) and arr.shape[0] < arr.shape[-1]:
            arr = np.transpose(arr, (1, 2, 0))
        if arr.ndim == 2:
            arr = np.stack([arr] * 3, axis=-1)
        if arr.ndim != 3:
            raise InvalidInputError(f"Expected a 2-D or 3-D image array, got shape {arr.shape}.")
        if arr.shape[-1] == 1:
            arr = np.repeat(arr, 3, axis=-1)
        if arr.shape[-1] == 4:
            arr = arr[..., :3]
        if arr.shape[-1] != 3:
            raise InvalidInputError(f"Expected 1, 3 or 4 channels, got {arr.shape[-1]}.")
        if arr.size == 0:
            raise InvalidInputError(f"Image array is empty (shape {arr.shape}).")
        if arr.dtype != np.uint8:
            a = arr.astype(np.float32)
            # Refuse rather than clip. Both of these used to pass silently and come back with a
            # >99%-confidence label: a non-finite array became a black tile (NaN casts to 0), and
            # Sentinel-2 L1C reflectance (0-10000, the native scale of this model's own training
            # data) saturated to a white tile. A confident answer about a blank image is worse than
            # an error, so the caller is told to scale its pixels itself.
            if not np.isfinite(a).all():
                raise InvalidInputError(
                    "Image contains NaN or infinite values; refusing to guess replacements."
                )
            hi = float(a.max())
            lo = float(a.min())
            if lo < 0.0:
                raise InvalidInputError(f"Image has negative pixel values (min {lo:g}).")
            if hi <= 1.0:
                a = a * 255.0            # float image in [0, 1] by convention
            elif hi > 255.0:
                raise InvalidInputError(
                    f"Image pixel values reach {hi:g}, beyond 8-bit range. This classifier expects "
                    f"8-bit RGB or floats in [0, 1]; scale 16-bit or reflectance imagery (e.g. "
                    f"Sentinel-2 L1C 0-10000) before calling, since clipping it here would "
                    f"saturate the tile to white and still return a confident label."
                )
            arr = np.clip(a, 0, 255).astype(np.uint8)
        return np.ascontiguousarray(arr)
    raise InvalidInputError(f"Unsupported image input type '{type(image_input).__name__}'.")


def preprocess(img: np.ndarray, image_size: int) -> torch.Tensor:
    """(H, W, 3) uint8 -> (1, 3, image_size, image_size) float32, ImageNet-normalised.

    Bilinear resize matching the training transform, then the ImageNet mean/std the model was
    trained with. EuroSAT tiles are 64x64, so this is normally an upsample.
    """
    pil = Image.fromarray(img).resize((image_size, image_size), Image.BILINEAR)
    x = (np.asarray(pil, dtype=np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))).unsqueeze(0)


class EuroSatLandCoverAdapter(BaseModelAdapter):
    """`eurosat_efficientnet_b0`: EfficientNet-B0 on EuroSAT RGB, 10 classes (Q-041).

    Held-out test accuracy 0.9832 over 4050 samples; balanced accuracy 0.9824. Scene-level only:
    it labels the whole tile and localises nothing. Sentinel-2 at 10 m/px.
    """

    def __init__(self) -> None:
        super().__init__("eurosat_classifier")
        self._class_names: Optional[List[str]] = None
        self._image_size: Optional[int] = None
        self._val_accuracy: Optional[float] = None
        self._epoch: Optional[int] = None

    # ---- properties read from the checkpoint ------------------------------------------------

    @property
    def class_names(self) -> List[str]:
        """The label set, in the checkpoint's own index order. Requires the model to be loaded."""
        if self._class_names is None:
            raise InferenceError(
                f"{self.name}: class names are unknown until the checkpoint is loaded.",
                model_name=self.name,
            )
        return list(self._class_names)

    @property
    def image_size(self) -> int:
        """Config override, else the checkpoint's training size, else 224."""
        configured = self.config.input_size if self.config else None
        if configured is not None:
            return int(configured)
        if self._image_size is not None:
            return int(self._image_size)
        return _FALLBACK_IMAGE_SIZE

    @property
    def trained_gsd_m(self) -> float:
        """Metres/pixel the tiles were captured at; config wins so a re-train can correct it."""
        configured = self.config.trained_gsd_m if self.config else None
        return float(configured) if configured is not None else EUROSAT_GSD_M

    # ---- lifecycle -------------------------------------------------------------------------

    def load(self) -> None:
        """Alias for load_model(), for parity with the other adapters."""
        self.load_model()

    def load_model(self) -> None:
        """Builds EfficientNet-B0 with a len(class_names)-way head and loads the real weights."""
        if self._loaded and self._model is not None:
            return
        self.ensure_available()
        ckpt_file = self.checkpoint_path

        try:
            import torch.nn as nn
            from torchvision.models import efficientnet_b0

            warn_if_cpu_for_heavy_model(self.name, self.device)
            ckpt = torch.load(str(ckpt_file), map_location="cpu", weights_only=False)
            if not isinstance(ckpt, dict) or "model_state_dict" not in ckpt:
                raise ValueError(
                    f"{self.name}: expected a checkpoint dict with a 'model_state_dict' key, "
                    f"got {type(ckpt).__name__} with keys "
                    f"{sorted(ckpt)[:8] if isinstance(ckpt, dict) else 'n/a'}."
                )
            state = ckpt["model_state_dict"]

            names = ckpt.get("class_names")
            if not names:
                raise ValueError(
                    f"{self.name}: checkpoint carries no 'class_names', so predictions could not "
                    f"be labelled. Refusing to guess the label order."
                )
            # The head decides the class count; a mismatch with class_names means the two were
            # saved out of step and every label would be wrong.
            head = state.get("classifier.1.weight")
            if head is None:
                raise ValueError(f"{self.name}: checkpoint has no 'classifier.1.weight'.")
            if int(head.shape[0]) != len(names):
                raise ValueError(
                    f"{self.name}: head predicts {int(head.shape[0])} classes but the checkpoint "
                    f"lists {len(names)} class names."
                )

            model = efficientnet_b0(weights=None)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(names))
            model.load_state_dict(state, strict=True)
            model.to(self.device).eval()

            self._model = model
            self._class_names = list(names)
            self._image_size = int(ckpt["image_size"]) if ckpt.get("image_size") else None
            self._val_accuracy = (
                float(ckpt["best_val_accuracy"]) if ckpt.get("best_val_accuracy") is not None else None
            )
            self._epoch = int(ckpt["epoch"]) if ckpt.get("epoch") is not None else None
            self._loaded = True
            logger.info(
                f"{self.name}: efficientnet_b0, {len(names)} classes, epoch {self._epoch}, "
                f"input {self.image_size}px, best val accuracy {self._val_accuracy}."
            )
        except Exception as e:
            self._model = None
            self._loaded = False
            self._class_names = None
            if type(e).__name__ == "ModelUnavailableError":
                raise
            logger.error(f"{self.name} failed to load: {e}", exc_info=True)
            raise InferenceError(f"{self.name} failed to load: {e}", model_name=self.name)

    def unload(self) -> None:
        """Releases the weights and returns the CUDA cache to the driver."""
        if self._model is not None:
            del self._model
        self._model = None
        self._loaded = False
        self._class_names = None
        self._image_size = None
        self._val_accuracy = None
        self._epoch = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info(f"{self.name} unloaded from {self.device}.")

    # ---- inference -------------------------------------------------------------------------

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        """Requires one image under 'image', 'image_pil', 'image_path' or 'arr'."""
        if not isinstance(context, dict):
            raise InvalidInputError("Expected a context dict.")
        if all(context.get(k) is None for k in ("image", "image_pil", "image_path", "arr")):
            raise InvalidInputError(
                "No image supplied: expected one of 'image', 'image_pil', 'image_path' or 'arr'."
            )
        self._validate_top_k(context.get("top_k"))

    @staticmethod
    def _validate_top_k(top_k: Any) -> None:
        """`top_k` must be absent or a positive int. `bool` is rejected: True would mean top-1."""
        if top_k is None:
            return
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise InvalidInputError(f"top_k must be a positive integer, got {top_k!r}.")

    def _resolve_inputs(self, image_or_context: Any, kwargs: Dict[str, Any]) -> Any:
        """Accepts either a positional image or a context dict; returns (raw image, top_k).

        `top_k` is validated on every path, not only the dict one. Before this was hoisted out of
        the branches, `predict(img, top_k=-3)` silently returned `order[:-3]` — seven classes for a
        request of minus three — while the identical dict call was a clean 400, and
        `predict(img, top_k="x")` escaped as a bare ValueError (a 500) because the `int()` happened
        outside predict's try block. `binary_segmenter._resolve_inputs` checks `threshold` after its
        if/else for the same reason.
        """
        raw: Any = image_or_context
        top_k = kwargs.get("top_k")
        if isinstance(image_or_context, dict):
            ctx = dict(image_or_context)
            ctx.update(kwargs)
            self.validate_inputs(ctx)
            top_k = ctx.get("top_k")
            for key in ("image", "image_pil", "image_path", "arr"):
                if ctx.get(key) is not None:
                    return ctx[key], top_k
            return None, top_k
        if image_or_context is None:
            self.validate_inputs(dict(kwargs))
            for key in ("image", "image_pil", "image_path", "arr"):
                if kwargs.get(key) is not None:
                    return kwargs[key], top_k
            return None, top_k
        self._validate_top_k(top_k)
        return raw, top_k

    def predict(self, image_or_context: Any = None, **kwargs: Any) -> ModelResult:
        """
        Classifies the land cover of one RGB tile.

            adapter.predict(pil_or_ndarray_or_path, top_k=3)
            adapter.predict({"image": arr, "top_k": 3})

        `confidence` is the real softmax probability of the winning class. `metadata["top_k"]`
        holds the ranked (label, probability) pairs and `metadata["probabilities"]` the full
        distribution over `metadata["class_names"]`, in the checkpoint's index order.
        """
        raw, top_k = self._resolve_inputs(image_or_context, kwargs)
        self.load_model()
        names = self.class_names
        k = min(top_k if top_k is not None else 3, len(names))

        img = to_rgb_array(raw)
        h, w = img.shape[:2]
        try:
            x = preprocess(img, self.image_size).to(self.device)
            with torch.no_grad():
                logits = self._model(x)
                probs = torch.softmax(logits.float(), dim=1)[0].detach().cpu().numpy()
        except Exception as e:
            logger.error(f"{self.name} inference failed: {e}", exc_info=True)
            raise InferenceError(f"{self.name} inference failed: {e}", model_name=self.name)

        order = np.argsort(-probs)
        best = int(order[0])
        label = names[best]
        confidence = float(probs[best])
        ranked = [{"label": names[int(i)], "probability": round(float(probs[int(i)]), 6)} for i in order[:k]]

        return ModelResult(
            model_name=self.name,
            task="classification",
            answer=(
                f"Scene-level land cover is {label} ({confidence * 100:.1f}% confidence). "
                f"This model assigns one label to the whole tile and does not localise anything; "
                f"it was trained on Sentinel-2 imagery at {self.trained_gsd_m:g} m/px."
            ),
            confidence=confidence,
            metadata={
                "label": label,
                "label_index": best,
                "class_names": names,
                "probabilities": [round(float(p), 6) for p in probs.tolist()],
                "top_k": ranked,
                "scene_level_only": True,
                "input_shape": [h, w],
                "model_input_size": self.image_size,
                "trained_gsd_m": self.trained_gsd_m,
                "test_accuracy": 0.9832098765432099,
                "test_samples": 4050,
                "checkpoint_epoch": self._epoch,
                "best_val_accuracy": self._val_accuracy,
                "device": str(self.device),
                "model_class": "torchvision.efficientnet_b0",
            },
        )
