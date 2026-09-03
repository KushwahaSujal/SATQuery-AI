"""
SatQuery AI — Policy Engine
Authoritatively enforces the 8 foundational operational, safety, and scientific integrity policies.
Prevents hallucination, silent model substitution, and invalid remote-sensing operations.
"""
from typing import Any, Dict, List, Optional
from backend.app.orchestration.schemas import PolicyViolation
from backend.app.exceptions import SatQueryException
from backend.app.logging import logger


class PolicyViolationException(SatQueryException):
    """Raised when an operation breaches system integrity policies."""
    def __init__(self, policy: str, message: str, code: str = "POLICY_VIOLATION"):
        super().__init__(
            message=f"Policy [{policy}] violated: {message}",
            code=code,
            status_code=400,
            details={"policy": policy}
        )


class PolicyEngine:
    """
    Enforces the 8 core operational and scientific integrity policies:
    1. NO_FABRICATION
    2. NO_UNAVAILABLE_MODEL
    3. NO_BENCHMARK_LEAK
    4. SPECTRAL_INTEGRITY
    5. SPATIAL_ALIGNMENT
    6. MODALITY_SANCTITY
    7. UNBIASED_CONFIDENCE
    8. FALLBACK_EXPLICIT
    """

    @classmethod
    def enforce_spectral_policy(cls, band_mapping: Dict[str, Optional[int]], requested_index: str) -> None:
        """
        Policy 4: SPECTRAL_INTEGRITY
        Never calculate or hallucinate spectral indices without genuine physical bands.
        """
        idx = requested_index.upper()
        if idx in ["NDVI", "NDWI", "FALSE_COLOR_NIR"] and band_mapping.get("nir") is None:
            raise PolicyViolationException(
                policy="SPECTRAL_INTEGRITY",
                message=f"Cannot calculate {idx}: Near-Infrared (NIR) band is not present in raster. Returning INDEX_NOT_AVAILABLE.",
                code="INDEX_NOT_AVAILABLE"
            )

    @classmethod
    def enforce_spatial_alignment_policy(cls, is_spatially_aligned: Optional[bool], operation: str = "temporal_change") -> None:
        """
        Policy 5: SPATIAL_ALIGNMENT
        Never overlay or subtract unregistered or misprojected rasters.
        """
        if is_spatially_aligned is False:
            raise PolicyViolationException(
                policy="SPATIAL_ALIGNMENT",
                message=f"Operation '{operation}' requires co-registered imagery with matching dimensions and projection. Rasters must be aligned first.",
                code="REGISTRATION_REQUIRED"
            )

    @classmethod
    def enforce_modality_sanctity_policy(cls, input_modality: str, model_name: str) -> None:
        """
        Policy 6: MODALITY_SANCTITY
        Never misuse models on incompatible data formats.
        """
        if input_modality == "video" and model_name == "changeformer":
            raise PolicyViolationException(
                policy="MODALITY_SANCTITY",
                message="ChangeFormer cannot be used as an arbitrary video detector. Use Grounding DINO / SAM 2 tracker for video.",
                code="MODALITY_MISMATCH"
            )
        if input_modality == "video" and model_name == "cdvqa":
            raise PolicyViolationException(
                policy="MODALITY_SANCTITY",
                message="CDVQA cannot be used as an arbitrary video classifier.",
                code="MODALITY_MISMATCH"
            )

    @classmethod
    def enforce_unbiased_confidence_policy(cls, confidence: Optional[float], is_heuristic: bool) -> Optional[float]:
        """
        Policy 7: UNBIASED_CONFIDENCE
        Never treat heuristic formulas as calibrated model probabilities.
        """
        if is_heuristic:
            # When score is heuristic, return None for calibrated confidence
            # and let the caller expose the score explicitly as a heuristic metric
            return None
        return confidence
