from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBoxEvidence(BaseModel):
    label: str
    box_2d: List[float]  # [ymin, xmin, ymax, xmax] in normalized 0-1 or pixel coords
    score: Optional[float] = None
    geo_bounds: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat] in EPSG:4326
    source_crs: Optional[str] = None  # Original CRS of the raster if georeferenced
    target_crs: Optional[str] = None  # "EPSG:4326" when georeferenced
    coordinate_space: str = "image_coordinates"  # "geographic" | "image_coordinates"


class AreaStatistics(BaseModel):
    changed_pixels: int = 0
    raw_changed_pixels: Optional[int] = None
    total_valid_pixels: int = 0
    change_ratio: float = 0.0
    threshold: float = 0.5
    region_count: int = 0
    quality_status: str = "PASS"
    quality_warning: Optional[str] = None
    diagnostic_flags: List[str] = Field(default_factory=list)
    estimated_area_sq_m: Optional[float] = None
    estimated_area_sq_km: Optional[float] = None
    area_unit: str = "sq_meters"
    metric_crs: Optional[str] = None


class SpatialEvidence(BaseModel):
    boxes: List[BoundingBoxEvidence] = Field(default_factory=list)
    has_mask: bool = False
    mask_path: Optional[str] = None
    geojson_path: Optional[str] = None
    overlay_path: Optional[str] = None
    statistics: Optional[AreaStatistics] = None
    geojson_data: Optional[Dict[str, Any]] = None
    candidate_boxes: List[List[float]] = Field(default_factory=list)
    candidate_scores: List[float] = Field(default_factory=list)
    selected_box: Optional[List[float]] = None
    reasoning_strategy: Optional[str] = None
    reasoning_score: Optional[float] = None
    sam2_artifact: Optional[str] = None
    sam2_score: Optional[float] = None


class ConsistencySignal(BaseModel):
    signal_type: str
    agreement: bool
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)


class EvidencePackage(BaseModel):
    spatial: SpatialEvidence = Field(default_factory=SpatialEvidence)
    consistency: List[ConsistencySignal] = Field(default_factory=list)
    summary: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConflictReport(BaseModel):
    has_conflict: bool = False
    conflict_type: Optional[str] = None
    description: str = ""
    disagreeing_models: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class AdjudicationResult(BaseModel):
    adjudicated_answer: str
    adjudication_status: str = "NO_CONFLICT"  # "RESOLVED" | "AMBIGUOUS" | "CONFLICT" | "NO_CONFLICT"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    contributing_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    conflict_details: Optional[ConflictReport] = None
    applied_rule: str = "PASS_THROUGH"
    provenance: Dict[str, Any] = Field(default_factory=dict)

