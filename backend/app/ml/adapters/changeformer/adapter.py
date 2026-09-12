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

def preprocess_changeformer_input(
    img: Union[np.ndarray, Image.Image, torch.Tensor],
    target_size: Tuple[int, int] = (512, 512)
) -> Tuple[torch.Tensor, Tuple[int, int]]:
    """
    Reproduces the exact training-time preprocessing for ChangeFormer:
      1. Converts input to 3-channel RGB float array.
      2. Rescales [0, 255] to [0.0, 1.0].
      3. Normalizes using standard ImageNet mean/std:
         mean = [0.485, 0.456, 0.406], std = [0.229, 0.224, 0.225].
      4. Resizes to target_size (divisible by 32).
      5. Returns (tensor, original_hw).
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

    # ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    # Transpose to (C, H, W)
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).float()

    # Resize if not matching target size
    if (orig_h, orig_w) != target_size:
        tensor = F.interpolate(tensor, size=target_size, mode="bilinear", align_corners=False)

    return tensor, (orig_h, orig_w)


# ============================================================================
# ChangeFormer Adapter with Verified Checkpoint Integration
# ============================================================================

class ChangeFormerAdapter(BaseModelAdapter):
    """
    Adapter for ChangeFormer: Transformer-based Siamese Architecture for Remote Sensing Change Detection.
    Loads checkpoints/changeformer/satquery_changeformer_best.pt and runs inference.
    """
    def __init__(self):
        super().__init__("changeformer")
        self._model: Optional[ChangeFormerV6] = None

    def _resolve_checkpoint_path(self) -> Path:
        candidates = [
            Path("checkpoints/changeformer/satquery_changeformer_best.pt"),
            self.checkpoint_path,
            Path("checkpoints/changeformer/changeformer_satquery.pth"),
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
            model = ChangeFormerV6()
            ckpt = torch.load(str(ckpt_file), map_location=self.device)

            if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                state_dict = ckpt["model_state_dict"]
            elif isinstance(ckpt, dict):
                state_dict = ckpt
            else:
                raise ValueError(f"Unexpected checkpoint payload type: {type(ckpt)}")

            model.load_state_dict(state_dict, strict=True)
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
            thresh = threshold or context.get("threshold", self.config.threshold if self.config else 0.5)
        else:
            arr1 = image_a
            arr2 = image_b
            thresh = threshold or kwargs.get("threshold", self.config.threshold if self.config else 0.5)

        if arr1 is None or arr2 is None:
            raise InvalidInputError("ChangeFormer requires two valid non-null images.")

        self.load_model()
        if self._model is None:
            raise ModelUnavailableError(f"Model '{self.name}' is not loaded.")

        target_size = kwargs.get("target_size", (512, 512))

        try:
            t1_tensor, orig_shape1 = preprocess_changeformer_input(arr1, target_size=target_size)
            t2_tensor, orig_shape2 = preprocess_changeformer_input(arr2, target_size=target_size)
            t1_tensor = t1_tensor.to(self.device)
            t2_tensor = t2_tensor.to(self.device)

            with torch.no_grad():
                # Forward pass through ChangeFormerV6
                logits = self._model(t1_tensor, t2_tensor)  # (1, 2, 512, 512)

                # Interpolate logits back to native input resolution
                orig_h, orig_w = orig_shape1
                if logits.shape[2:] != (orig_h, orig_w):
                    logits = F.interpolate(logits, size=(orig_h, orig_w), mode="bilinear", align_corners=False)

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
                    "target_inference_size": target_size,
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
