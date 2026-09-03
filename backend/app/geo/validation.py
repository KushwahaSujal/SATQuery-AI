from typing import List, Optional, Tuple
from backend.app.geo.metadata import RasterMetadata
from backend.app.geo.alignment import check_alignment, AlignmentReport
from backend.app.exceptions import PairValidationError, InvalidInputError


def validate_single_image(meta: RasterMetadata) -> None:
    """Validates that a single raster is readable and has valid dimensions."""
    if meta.width <= 0 or meta.height <= 0:
        raise InvalidInputError(f"Invalid raster dimensions: {meta.width}x{meta.height}")
    if meta.bands <= 0:
        raise InvalidInputError("Raster has 0 spectral bands.")


def validate_pair(meta1: RasterMetadata, meta2: RasterMetadata) -> AlignmentReport:
    """Validates that two rasters exist, are readable, and checks their alignment."""
    validate_single_image(meta1)
    validate_single_image(meta2)
    return check_alignment(meta1, meta2)


def validate_temporal_pair(
    meta1: RasterMetadata,
    meta2: RasterMetadata,
    modality1: str,
    modality2: str
) -> AlignmentReport:
    """
    Validates a bi-temporal image pair.
    Requirements:
      - Both images cover the same spatial area (co-registered or matching dimensions).
      - Cross-modal optical+SAR is REJECTED here (must use validate_optical_sar_pair instead).
    """
    if (modality1 == "sar" and modality2 in ["optical", "multispectral"]) or \
       (modality2 == "sar" and modality1 in ["optical", "multispectral"]):
        raise PairValidationError(
            "Pair contains one Optical and one SAR image. This is a cross-modal pair, "
            "not a bi-temporal change pair. Please use the Optical-SAR workflow."
        )

    alignment = validate_pair(meta1, meta2)
    if not alignment.bounds_overlap and not (meta1.width == meta2.width and meta1.height == meta2.height):
        raise PairValidationError(
            f"Images do not cover the same spatial area (Bounds overlap: {alignment.bounds_overlap}).",
            details=alignment.details
        )
    return alignment


def validate_optical_sar_pair(
    meta1: RasterMetadata,
    meta2: RasterMetadata,
    modality1: str,
    modality2: str
) -> Tuple[RasterMetadata, RasterMetadata, AlignmentReport]:
    """
    Validates an Optical + SAR image pair.
    Returns (optical_meta, sar_meta, alignment_report).
    """
    alignment = validate_pair(meta1, meta2)

    if modality1 in ["optical", "multispectral"] and modality2 == "sar":
        return meta1, meta2, alignment
    elif modality2 in ["optical", "multispectral"] and modality1 == "sar":
        return meta2, meta1, alignment
    else:
        raise PairValidationError(
            f"Optical-SAR workflow requires exactly one Optical and one SAR image. "
            f"Provided modalities: '{modality1}' and '{modality2}'."
        )
