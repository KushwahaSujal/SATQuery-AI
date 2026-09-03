"""
SatQuery AI — Input Modality & Raster Analyzer
Performs deep structural pre-routing inspection of raster and video inputs.
Extracts dimensional, spectral, spatial reference, and temporal metadata.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.geo.raster import RasterInspector
from backend.app.geo.modality import ModalityDetector
from backend.app.geo.metadata import RasterMetadata
from backend.app.orchestration.schemas import ModalityType
from backend.app.logging import logger


class InputAnalysisFacts(BaseModel):
    """
    Comprehensive facts discovered about the user inputs before planning.
    """
    total_files: int = 0
    file_types: List[str] = Field(default_factory=list)
    modalities: List[str] = Field(default_factory=list)
    overall_modality_type: ModalityType = ModalityType.UNKNOWN
    
    # Raster dimensional properties
    dimensions: List[Dict[str, int]] = Field(default_factory=list)
    bands: List[int] = Field(default_factory=list)
    dtypes: List[str] = Field(default_factory=list)
    crss: List[Optional[str]] = Field(default_factory=list)
    resolutions: List[Optional[List[float]]] = Field(default_factory=list)
    is_georeferenced: List[bool] = Field(default_factory=list)
    
    # Pair & Temporal alignment
    is_spatially_aligned: Optional[bool] = None
    temporal_order_valid: Optional[bool] = None
    timestamps: List[Optional[str]] = Field(default_factory=list)
    
    # Video properties
    video_metadata: Optional[Dict[str, Any]] = None
    
    warnings: List[str] = Field(default_factory=list)


class InputAnalyzer:
    """
    Pre-execution analyzer that supplies verified structural facts to the planner.
    """

    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

    @classmethod
    def analyze(cls, file_paths: List[str]) -> Tuple[InputAnalysisFacts, List[RasterMetadata]]:
        facts = InputAnalysisFacts(total_files=len(file_paths))
        metadata_list: List[RasterMetadata] = []

        if not file_paths:
            facts.warnings.append("No input files provided.")
            return facts, metadata_list

        for p_str in file_paths:
            p = Path(p_str)
            ext = p.suffix.lower()

            if ext in cls.VIDEO_EXTENSIONS:
                facts.file_types.append("video")
                facts.modalities.append("video")
                # Video metadata discovery
                try:
                    import cv2
                    cap = cv2.VideoCapture(str(p))
                    if cap.isOpened():
                        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                        fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        dur = fc / fps if fps > 0 else 0.0
                        cap.release()
                        facts.video_metadata = {
                            "fps": round(fps, 2),
                            "frame_count": fc,
                            "width": w,
                            "height": h,
                            "duration_seconds": round(dur, 2)
                        }
                except Exception as e:
                    facts.warnings.append(f"Video metadata read warning for {p.name}: {e}")
            else:
                facts.file_types.append("raster")
                try:
                    meta = RasterInspector.inspect(str(p))
                    metadata_list.append(meta)
                    mod, conf, reason = ModalityDetector.detect(meta)
                    facts.modalities.append(mod)
                    facts.dimensions.append({"width": meta.width, "height": meta.height})
                    facts.bands.append(meta.bands)
                    facts.dtypes.append(meta.dtype)
                    facts.crss.append(meta.crs)
                    facts.resolutions.append(meta.resolution)
                    facts.is_georeferenced.append(meta.is_georeferenced)
                    facts.timestamps.append(meta.tags.get("acquisition_time"))
                except Exception as e:
                    facts.warnings.append(f"Failed to inspect raster {p.name}: {e}")

        # Classify overall modality type
        if any(t == "video" for t in facts.file_types):
            facts.overall_modality_type = ModalityType.VIDEO
        elif len(metadata_list) >= 2:
            is_cross = (
                ("optical" in facts.modalities[0] and "sar" in facts.modalities[1]) or
                ("sar" in facts.modalities[0] and "optical" in facts.modalities[1])
            )
            if is_cross:
                facts.overall_modality_type = ModalityType.OPTICAL_PLUS_SAR
            else:
                facts.overall_modality_type = ModalityType.MULTI_IMAGE
        elif len(metadata_list) == 1:
            mod = facts.modalities[0] if facts.modalities else "optical"
            if mod == "sar":
                facts.overall_modality_type = ModalityType.SAR_RASTER
            elif mod == "multispectral" or (facts.bands and facts.bands[0] > 3):
                facts.overall_modality_type = ModalityType.MULTISPECTRAL_RASTER
            else:
                facts.overall_modality_type = ModalityType.OPTICAL_RASTER

        # Check alignment if 2 rasters
        if len(metadata_list) >= 2:
            m1, m2 = metadata_list[0], metadata_list[1]
            aligned = (m1.width == m2.width and m1.height == m2.height)
            if m1.crs and m2.crs:
                aligned = aligned and (m1.crs == m2.crs)
            facts.is_spatially_aligned = aligned
            if not aligned:
                facts.warnings.append(
                    f"Rasters have mismatched dimensions or coordinate reference systems: "
                    f"({m1.width}x{m1.height}, {m1.crs}) vs ({m2.width}x{m2.height}, {m2.crs})."
                )

        return facts, metadata_list
