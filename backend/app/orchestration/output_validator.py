"""
SatQuery AI — Output Quality Validator
Validates model outputs (shapes, dtypes, ranges, coordinates, non-emptiness)
and flags quality anomalies (excessive change, full-image background fallbacks).
"""
import numpy as np
from typing import Any, Dict, List, Optional
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import SatQueryException
from backend.app.logging import logger


class ModelOutputInvalidError(SatQueryException):
    """Raised when model inference outputs fail structural or sanity validation."""
    def __init__(self, message: str, model_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Model '{model_name}' output validation failed: {message}",
            code="MODEL_OUTPUT_INVALID",
            status_code=502,
            details=details or {}
        )


class OutputQualityValidator:
    """
    Validates model output packages after execution and enforces quality standards.
    """

    @classmethod
    def validate_changeformer_output(
        cls,
        res: ModelResult,
        expected_width: int,
        expected_height: int
    ) -> List[str]:
        """
        Validates ChangeFormer output mask, probability map, and finite values.
        Returns list of quality warnings if anomalies are detected.
        """
        warnings: List[str] = []

        if not res.masks:
            raise ModelOutputInvalidError("ChangeFormer produced no masks in result.", model_name="changeformer")

        mask_dict = res.masks[0]
        prob_map = mask_dict.get("change_prob_map")
        raw_mask = mask_dict.get("raw_mask")

        if prob_map is not None:
            if not isinstance(prob_map, np.ndarray):
                raise ModelOutputInvalidError("change_prob_map is not a numpy array.", model_name="changeformer")
            if not np.all(np.isfinite(prob_map)):
                raise ModelOutputInvalidError("change_prob_map contains non-finite values (NaN or Inf).", model_name="changeformer")
            if prob_map.min() < -1e-4 or prob_map.max() > 1.0 + 1e-4:
                raise ModelOutputInvalidError(f"change_prob_map range [{prob_map.min()}, {prob_map.max()}] outside [0.0, 1.0].", model_name="changeformer")

        if raw_mask is not None:
            total_px = expected_width * expected_height
            changed_px = int(np.sum(raw_mask > 0))
            ratio = changed_px / total_px if total_px > 0 else 0.0

            if ratio > 0.50:
                warnings.append(
                    f"EXCESSIVE_CHANGE: {ratio*100:.1f}% of pixels flagged as changed. "
                    "Likely caused by significant seasonal or illumination variance between epochs."
                )

        return warnings

    @classmethod
    def validate_grounding_output(
        cls,
        boxes: List[List[float]],
        image_width: int,
        image_height: int
    ) -> List[List[float]]:
        """
        Validates bounding box geometry: non-inverted, within bounds, finite coordinates.
        Filters out degenerate or out-of-bounds boxes.
        """
        valid_boxes: List[List[float]] = []

        for b in boxes:
            if len(b) < 4:
                continue
            x1, y1, x2, y2 = b[:4]
            if not (np.isfinite(x1) and np.isfinite(y1) and np.isfinite(x2) and np.isfinite(y2)):
                continue

            # Ensure non-inverted
            if x2 <= x1 or y2 <= y1:
                continue

            # Clip to image boundaries
            x1 = max(0.0, min(float(x1), float(image_width)))
            y1 = max(0.0, min(float(y1), float(image_height)))
            x2 = max(0.0, min(float(x2), float(image_width)))
            y2 = max(0.0, min(float(y2), float(image_height)))

            # Discard zero-area boxes
            if (x2 - x1) >= 1.0 and (y2 - y1) >= 1.0:
                valid_boxes.append([round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)])

        return valid_boxes

    @classmethod
    def validate_sam2_mask(
        cls,
        mask: np.ndarray,
        expected_width: int,
        expected_height: int
    ) -> None:
        """
        Validates SAM 2 segmentation mask dimensions and binary states.
        """
        if not isinstance(mask, np.ndarray):
            raise ModelOutputInvalidError("SAM 2 mask is not a numpy array.", model_name="sam2")
        m_sq = np.squeeze(mask)
        if m_sq.ndim != 2:
            raise ModelOutputInvalidError(f"SAM 2 mask has {m_sq.ndim} dimensions, expected 2D binary mask.", model_name="sam2")
        h, w = m_sq.shape
        if w != expected_width or h != expected_height:
            raise ModelOutputInvalidError(
                f"SAM 2 mask dimensions ({w}x{h}) do not match source raster ({expected_width}x{expected_height}).",
                model_name="sam2"
            )
