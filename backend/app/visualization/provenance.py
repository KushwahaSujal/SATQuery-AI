"""
SatQuery AI — Visualization Provenance & Data Models
Defines scientific provenance enums, 15 visualization types, and layer descriptors.
Ensures zero-fabrication: clearly distinguishes original sensor data, derived spectral
indices, model predictions, continuous probabilities, and analytical heuristics.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator


class LayerProvenance(str, Enum):
    SOURCE_DATA = "SOURCE_DATA"
    DERIVED_INDEX = "DERIVED_INDEX"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    MODEL_PROBABILITY = "MODEL_PROBABILITY"
    HEURISTIC_ANALYSIS = "HEURISTIC_ANALYSIS"


class VisualizationType(str, Enum):
    TRUE_COLOR = "TRUE_COLOR"                     # 1. RGB using authentic red/green/blue channels
    GRAYSCALE = "GRAYSCALE"                       # 2. Single-channel panchromatic/grayscale view
    FALSE_COLOR = "FALSE_COLOR"                   # 3. Configurable multispectral composite (e.g. NIR/R/G)
    SINGLE_BAND = "SINGLE_BAND"                   # 4. Individual band inspection with colormap
    BAND_DIFFERENCE = "BAND_DIFFERENCE"           # 5. Normalized or absolute band difference
    SPECTRAL_INDEX = "SPECTRAL_INDEX"             # 6. Scientific index (NDVI, NDWI, NDBI)
    PROBABILITY_HEATMAP = "PROBABILITY_HEATMAP"   # 7. Continuous model probability heatmap
    BINARY_MASK = "BINARY_MASK"                   # 8. Discrete prediction mask (0/1)
    CONFIDENCE_MAP = "CONFIDENCE_MAP"             # 9. Spatial model confidence map
    BBOX_OVERLAY = "BBOX_OVERLAY"                 # 10. Bounding box overlay on imagery
    SEGMENTATION_OVERLAY = "SEGMENTATION_OVERLAY" # 11. SAM 2 alpha mask overlay
    TEMPORAL_CHANGE_OVERLAY = "TEMPORAL_CHANGE_OVERLAY" # 12. ChangeFormer bi-temporal change overlay
    SAR_POLARIZATION = "SAR_POLARIZATION"         # 13. Radar backscatter (VV, VH, HH, HV, dual-pol ratio)
    OPTICAL_SAR_COMPARISON = "OPTICAL_SAR_COMPARISON"   # 14. Co-registered optical vs SAR split view
    VIDEO_FLAG_REGION = "VIDEO_FLAG_REGION"       # 15. Flagged moment keyframe overlay for video
    REGION_MAP = "REGION_MAP"                     # 16. Connected change/grounding region map


class LayerMetadata(BaseModel):
    layer_id: str
    layer_type: VisualizationType
    title: str
    provenance: LayerProvenance
    source_model: Optional[str] = None
    available: bool = True
    artifact_url: Optional[str] = None
    mime_type: str = "image/png"
    units: str = "DN"
    min: float = 0.0
    max: float = 255.0
    threshold: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    min_value: float = 0.0
    max_value: float = 255.0
    mean_value: Optional[float] = None
    display_stretch: str = "2%-98% Percentile Stretch"
    valid_pixel_pct: float = 100.0
    crs: Optional[str] = None
    bounds: Optional[List[float]] = None
    resolution: Optional[List[float]] = None
    colormap: Optional[str] = None
    legend_labels: Optional[Dict[str, str]] = None
    scientific_values_preserved: bool = True
    co_registered: bool = True
    legend_url: Optional[str] = None
    raw_stats: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def sync_bounds_min_max(self):
        if self.min == 0.0 and self.min_value != 0.0:
            self.min = self.min_value
        elif self.min_value == 0.0 and self.min != 0.0:
            self.min_value = self.min
        if self.max == 255.0 and self.max_value != 255.0:
            self.max = self.max_value
        elif self.max_value == 255.0 and self.max != 255.0:
            self.max_value = self.max
        return self
