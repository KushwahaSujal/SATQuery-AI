"""
SatQuery AI — ChangeFormer adapter: preprocessing, checkpoint loading, inference.
"""
from typing import Any, Dict, Optional, Tuple, Union, List
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from PIL import Image

from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, ModelUnavailableError, InferenceError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


from backend.app.ml.adapters.changeformer.network import ChangeFormerV6


# ============================================================================
# Exact Training-Time Inference Preprocessing
# ============================================================================

#: Upstream wgcban/ChangeFormer datasets/data_utils.py normalises with mean=std=0.5.
_NORM_MEAN = 0.5
_NORM_STD = 0.5


def preprocess_changeformer_input(
    img: Union[np.ndarray, Image.Image, torch.Tensor],
) -> Tuple[torch.Tensor, Tuple[int, int]]:
    """
    Reproduces the upstream ChangeFormer training-time preprocessing:
      1. Converts input to a 3-channel RGB float array.
      2. Rescales [0, 255] to [0.0, 1.0].
      3. Normalises to [-1, 1] with mean = std = 0.5 (upstream data_utils.py).
      4. Returns ((1, 3, H, W) tensor, (H, W)). No resizing: the model is run at
         native resolution — resizing a 1024 LEVIR-CD scene to 256 measured IoU
         0.00-0.09 against 0.63-0.81 native (see project/qna.md).
    """
    if isinstance(img, Image.Image):
        arr = np.array(img.convert("RGB"), dtype=np.float32)
        orig_h, orig_w = arr.shape[0], arr.shape[1]
    elif isinstance(img, torch.Tensor):
        if img.ndim == 4:
            img = img.squeeze(0)
        if img.ndim == 3 and img.shape[0] in [1, 3, 4]:
            img = img.permute(1, 2, 0)
        arr = img.detach().cpu().numpy().astype(np.float32)
        orig_h, orig_w = arr.shape[0], arr.shape[1]
    elif isinstance(img, np.ndarray):
        arr = img.astype(np.float32)
        if arr.ndim == 2:
            orig_h, orig_w = arr.shape
            arr = np.stack([arr, arr, arr], axis=-1)
        elif arr.ndim == 3:
            if arr.shape[0] in [1, 3, 4] and arr.shape[0] < arr.shape[1] and arr.shape[0] < arr.shape[2]:
                arr = np.transpose(arr, (1, 2, 0))
            orig_h, orig_w = arr.shape[0], arr.shape[1]
            if arr.shape[-1] == 1:
                arr = np.repeat(arr, 3, axis=-1)
            elif arr.shape[-1] > 3:
                arr = arr[:, :, :3]
        else:
            raise InvalidInputError(f"Unsupported array shape for ChangeFormer: {arr.shape}")
    else:
        raise InvalidInputError(f"Unsupported input type for ChangeFormer: {type(img)}")

    # Handle float vs integer scaling
    if arr.max() > 1.0:
        arr = arr / 255.0

    arr = (arr - _NORM_MEAN) / _NORM_STD
    tensor = torch.from_numpy(np.ascontiguousarray(arr)).permute(2, 0, 1).unsqueeze(0).float()
    return tensor, (orig_h, orig_w)


# ============================================================================
# ChangeFormer Adapter with Verified Checkpoint Integration
# ============================================================================

class ChangeFormerAdapter(BaseModelAdapter):
    """
    Adapter for ChangeFormer: Transformer-based Siamese Architecture for Remote Sensing Change Detection.
    Loads the LEVIR-CD-256 epoch-20 ChangeFormerV6 checkpoint (upstream trainer format)
    and runs it at native resolution, windowing only above `max_native_side`.
    """

    #: Upstream encoder downsamples by 32 overall; inputs are reflect-padded to a multiple.
    _STRIDE = 32
    _DEFAULT_MAX_NATIVE_SIDE = 1024
    #: Frozen on the LEVIR-CD validation split before test evaluation (Ayushman's report).
    _DEFAULT_THRESHOLD = 0.435
    def __init__(self):
        super().__init__("changeformer")
        self._model: Optional[ChangeFormerV6] = None

    def _resolve_checkpoint_path(self) -> Path:
        candidates = [
            self.checkpoint_path,
            Path("checkpoints/changeformer/changeformer_v6_levir_levircd256_epoch20_best.pt"),
        ]
        for c in candidates:
            if c and Path(c).is_file():
                return Path(c)
        # If none exist, return default candidate
        return candidates[0]

    def is_available(self) -> bool:
        if not self.config or not self.config.enabled:
            return False
        return self._resolve_checkpoint_path().is_file()

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return

        ckpt_file = self._resolve_checkpoint_path()
        if not ckpt_file.is_file():
            logger.error(f"ChangeFormer checkpoint not found at: {ckpt_file}")
            raise ModelUnavailableError(
                self.name,
                message=f"ChangeFormer checkpoint '{ckpt_file}' is missing. Place the Kaggle checkpoint at '{ckpt_file}'."
            )

        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading verified ChangeFormer checkpoint from {ckpt_file} onto device {self.device}...")

        try:
            model = ChangeFormerV6(embed_dim=256)
            ckpt = torch.load(str(ckpt_file), map_location="cpu", weights_only=False)

            if not isinstance(ckpt, dict):
                raise ValueError(f"Unexpected checkpoint payload type: {type(ckpt)}")
            # Upstream trainer saves model_G_state_dict; earlier exports used model_state_dict.
            for key in ("model_G_state_dict", "model_state_dict"):
                if key in ckpt:
                    state_dict = ckpt[key]
                    break
            else:
                state_dict = ckpt

            model.load_state_dict(state_dict, strict=True)
            logger.info(
                f"ChangeFormer checkpoint epoch={ckpt.get('epoch_id', ckpt.get('epoch'))} "
                f"best_f1={ckpt.get('best_f1')}"
            )
            model.to(self.device)
            model.eval()

            self._model = model
            self._loaded = True
            logger.info("ChangeFormerV6 architecture and weights verified and loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load ChangeFormer checkpoint: {e}", exc_info=True)
            raise InferenceError(
                f"Failed to load ChangeFormer checkpoint: {e}",
                model_name=self.name,
                code="MODEL_INFERENCE_ERROR"
            )

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if "arr1" not in context and "image_a" not in context:
            raise InvalidInputError("ChangeFormer requires two input images ('arr1'/'image_a' and 'arr2'/'image_b').")
        if "arr2" not in context and "image_b" not in context:
            raise InvalidInputError("ChangeFormer requires two input images ('arr1'/'image_a' and 'arr2'/'image_b').")

    def _configured_threshold(self) -> float:
        if self.config and self.config.threshold is not None:
            return float(self.config.threshold)
        return self._DEFAULT_THRESHOLD

    @property
    def max_native_side(self) -> int:
        v = getattr(self.config, "max_native_side", None) if self.config else None
        return int(v) if v else self._DEFAULT_MAX_NATIVE_SIDE

    def _forward_logits_resilient(self, t1: torch.Tensor, t2: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """
        `_forward_logits` with CUDA out-of-memory recovery, in order of accuracy cost:
          1. release every other resident model and retry at native resolution (no accuracy cost);
          2. fall back to 512- then 256-pixel windows (256 measured 0.02-0.03 IoU below native on
             LEVIR-CD 1024 scenes, project/qna.md Q-007).
        What happened is returned so it is reported, not hidden.
        """
        info: Dict[str, Any] = {"oom_recovery": None}
        try:
            return self._forward_logits(t1, t2), info
        except torch.OutOfMemoryError:
            pass
        from backend.app.ml.registry import model_registry

        torch.cuda.empty_cache()
        released = model_registry.release_gpu_memory(exclude=("changeformer",))
        info["oom_recovery"] = {"released_models": released}
        try:
            logits = self._forward_logits(t1, t2)
            info["oom_recovery"]["resolved_by"] = "released_other_models"
            return logits, info
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
        for window in (512, 256):
            try:
                logits = self._forward_logits(t1, t2, window=window)
                info["oom_recovery"]["resolved_by"] = f"windowed_{window}"
                return logits, info
            except torch.OutOfMemoryError:
                torch.cuda.empty_cache()
        raise torch.OutOfMemoryError("ChangeFormer ran out of GPU memory even at 256-pixel windows after releasing other models.")

    def _forward_logits(self, t1: torch.Tensor, t2: torch.Tensor, window: Optional[int] = None) -> torch.Tensor:
        """
        Full-resolution 2-class logits (1, 2, H, W) for a (1, 3, H, W) pair.

        Runs the whole scene in one pass when both sides fit max_native_side (more context,
        no seams: IoU 0.63-0.81 native vs 0.60-0.79 with 256 tiles on LEVIR-CD 1024 scenes);
        otherwise non-overlapping windows of max_native_side, since stage-4 attention memory
        grows quadratically with area. Inputs are reflect-padded to a multiple of 32 and the
        logits cropped back, so arbitrary sizes are accepted.
        """
        _, _, h, w = t1.shape
        win = window or self.max_native_side
        tile_h = min(h, win)
        tile_w = min(w, win)
        logits = torch.empty((1, 2, h, w), dtype=torch.float32, device=t1.device)
        for y in range(0, h, tile_h):
            for x in range(0, w, tile_w):
                a = t1[..., y:y + tile_h, x:x + tile_w]
                b = t2[..., y:y + tile_h, x:x + tile_w]
                th, tw = a.shape[-2:]
                pad_h = (-th) % self._STRIDE
                pad_w = (-tw) % self._STRIDE
                if pad_h or pad_w:
                    mode = "reflect" if pad_h < th and pad_w < tw else "replicate"
                    a = F.pad(a, (0, pad_w, 0, pad_h), mode=mode)
                    b = F.pad(b, (0, pad_w, 0, pad_h), mode=mode)
                out = self._model(a, b)
                out = out[-1] if isinstance(out, (list, tuple)) else out
                logits[..., y:y + th, x:x + tw] = out[..., :th, :tw]
        return logits

    @staticmethod
    def postprocess_mask(
        raw_mask: np.ndarray,
        min_component_area: int = 25
    ) -> Tuple[np.ndarray, int, List[Dict[str, Any]]]:
        """
        Applies morphological opening and connected component filtering to suppress
        isolated noisy pixels and border artifacts while preserving authentic change regions.
        """
        import cv2
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(opened, connectivity=8)
        filtered = np.zeros_like(opened)
        region_list: List[Dict[str, Any]] = []
        for i in range(1, num_labels):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area >= min_component_area:
                filtered[labels == i] = 1
                x = int(stats[i, cv2.CC_STAT_LEFT])
                y = int(stats[i, cv2.CC_STAT_TOP])
                w = int(stats[i, cv2.CC_STAT_WIDTH])
                h = int(stats[i, cv2.CC_STAT_HEIGHT])
                cx, cy = float(centroids[i][0]), float(centroids[i][1])
                region_list.append({
                    "region_id": len(region_list) + 1,
                    "bbox": [x, y, x + w, y + h],
                    "area_pixels": area,
                    "centroid": [round(cx, 1), round(cy, 1)]
                })

        return filtered, len(region_list), region_list

    def predict(
        self,
        image_a: Any = None,
        image_b: Any = None,
        threshold: Optional[float] = None,
        **kwargs
    ) -> ModelResult:
        """
        Execute ChangeFormer inference on paired bi-temporal scenes.
        Supports both direct predict(image_a, image_b) and dictionary context predict(dict).
        """
        # Resolve inputs
        if isinstance(image_a, dict) and image_b is None:
            context = image_a
            arr1 = context.get("arr1", context.get("image_a"))
            arr2 = context.get("arr2", context.get("image_b"))
            thresh = threshold or context.get("threshold") or self._configured_threshold()
        else:
            arr1 = image_a
            arr2 = image_b
            thresh = threshold or kwargs.get("threshold") or self._configured_threshold()

        if arr1 is None or arr2 is None:
            raise InvalidInputError("ChangeFormer requires two valid non-null images.")

        self.load_model()
        if self._model is None:
            raise ModelUnavailableError(f"Model '{self.name}' is not loaded.")

        try:
            t1_tensor, orig_shape1 = preprocess_changeformer_input(arr1)
            t2_tensor, orig_shape2 = preprocess_changeformer_input(arr2)
            if orig_shape1 != orig_shape2:
                raise InvalidInputError(
                    f"ChangeFormer requires co-registered images of equal size; got "
                    f"{orig_shape1[1]}x{orig_shape1[0]} and {orig_shape2[1]}x{orig_shape2[0]}."
                )
            t1_tensor = t1_tensor.to(self.device)
            t2_tensor = t2_tensor.to(self.device)
            orig_h, orig_w = orig_shape1

            with torch.no_grad():
                logits, forward_info = self._forward_logits_resilient(t1_tensor, t2_tensor)  # (1, 2, H, W)

                # Softmax across 2 classes (0: background / no change, 1: change)
                probs = torch.softmax(logits, dim=1)  # (1, 2, orig_h, orig_w)
                change_prob_map = probs[0, 1].cpu().numpy()  # float32 [0.0, 1.0]

            # Generate binary mask based on probability threshold
            raw_mask = (change_prob_map >= thresh).astype(np.uint8)
            raw_pixel_count = int(np.sum(raw_mask > 0))
            total_pixel_count = int(raw_mask.size)
            raw_change_ratio = (raw_pixel_count / total_pixel_count) * 100.0

            # Post-processing morphological filtering & connected components
            filtered_mask, region_count, region_stats = self.postprocess_mask(raw_mask, min_component_area=25)
            filtered_pixel_count = int(np.sum(filtered_mask > 0))
            filtered_change_ratio = (filtered_pixel_count / total_pixel_count) * 100.0

            # Change Quality Sanity Check
            diagnostic_flags: List[str] = []
            if raw_change_ratio > 85.0:
                diagnostic_flags.append("FULL_IMAGE_CHANGE")
                quality_status = "REVIEW_REQUIRED"
                quality_warning = f"Near full-scene change detected ({raw_change_ratio:.1f}%). Check co-registration and radiometric consistency between T1 and T2."
            elif raw_change_ratio > 50.0:
                diagnostic_flags.append("EXCESSIVE_CHANGE")
                quality_status = "REVIEW_REQUIRED"
                quality_warning = f"Excessive change detected ({raw_change_ratio:.1f}%). Widespread radiometric or seasonal variation between T1 and T2 may cause false positives."
            elif raw_change_ratio < 0.01:
                diagnostic_flags.append("NEAR_EMPTY_CHANGE")
                quality_status = "PASS"
                quality_warning = "Negligible or near-zero spatial change detected between scenes."
            else:
                quality_status = "PASS"
                quality_warning = None

            # Genuine model confidence calculation
            if filtered_pixel_count > 0:
                confidence = float(np.mean(change_prob_map[filtered_mask > 0]))
            elif raw_pixel_count > 0:
                confidence = float(np.mean(change_prob_map[raw_mask > 0]))
            else:
                bg_prob = probs[0, 0].cpu().numpy()
                confidence = float(np.mean(bg_prob))

            answer = (
                f"Bi-temporal change detection completed. Changed pixels: {filtered_pixel_count:,} / {total_pixel_count:,} "
                f"({filtered_change_ratio:.2f}% of area at threshold {thresh:.2f}, {region_count} coherent change regions identified)."
            )
            if quality_warning:
                answer += f" Quality note: {quality_warning}"

            return ModelResult(
                model_name=self.name,
                task="change_detection",
                answer=answer,
                confidence=confidence,
                masks=[{
                    "change_prob_map": change_prob_map,
                    "binary_mask": filtered_mask,
                    "raw_mask": raw_mask,
                    "filtered_mask": filtered_mask,
                    "logits": logits.cpu().numpy(),
                }],
                metadata={
                    "threshold": thresh,
                    "inference_mode": (
                        (forward_info["oom_recovery"] or {}).get("resolved_by", "")
                        if str((forward_info["oom_recovery"] or {}).get("resolved_by", "")).startswith("windowed")
                        else ("native" if max(orig_h, orig_w) <= self.max_native_side else "windowed")
                    ),
                    "oom_recovery": forward_info["oom_recovery"],
                    "max_native_side": self.max_native_side,
                    "output_shape": [orig_h, orig_w],
                    "raw_change_pixel_count": raw_pixel_count,
                    "raw_change_ratio_pct": raw_change_ratio,
                    "change_pixel_count": filtered_pixel_count,
                    "total_pixel_count": total_pixel_count,
                    "change_ratio_pct": filtered_change_ratio,
                    "region_count": region_count,
                    "regions": region_stats[:50],  # Top 50 coherent regions
                    "quality_status": quality_status,
                    "diagnostic_flags": diagnostic_flags,
                    "quality_warning": quality_warning,
                    "model_class": "ChangeFormerV6"
                }
            )
        except Exception as e:
            if isinstance(e, (InvalidInputError, ModelUnavailableError)):
                raise
            logger.error(f"ChangeFormer execution failed: {e}", exc_info=True)
            raise InferenceError(
                f"ChangeFormer inference execution failed: {e}",
                model_name=self.name,
                code="MODEL_INFERENCE_ERROR"
            )
