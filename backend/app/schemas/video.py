from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.agent import JobStatus, TaskType, ExecutionStep


class VideoMetadata(BaseModel):
    """Normalized metadata for decoded video stream."""
    filename: str
    duration_sec: float
    fps: float
    width: int
    height: int
    frame_count: int
    codec: str = "unknown"


class VideoSamplingConfig(BaseModel):
    """Configurable frame sampling parameters for video analysis."""
    sample_fps: float = Field(default=1.0, ge=0.1, le=30.0, description="Target frame sampling rate in frames-per-second.")
    max_frames: int = Field(default=120, ge=1, le=1000, description="Maximum total frames to sample across the video.")
    analysis_stride: int = Field(default=1, ge=1, description="Stride step between sampled frames.")
    event_refinement_window: int = Field(default=3, ge=0, description="Window of surrounding frames to sample during event refinement.")


class VideoFlagConfig(BaseModel):
    """Configurable temporal aggregation and event filtering parameters."""
    min_persistence_frames: int = Field(default=2, ge=1, description="Minimum consecutive/near detections to form an event flag.")
    min_persistence_seconds: float = Field(default=0.5, ge=0.0, description="Minimum temporal duration in seconds for an event flag.")
    max_gap_frames: int = Field(default=2, ge=0, description="Maximum frame gap allowed within a single continuous event cluster.")
    max_gap_seconds: float = Field(default=1.5, ge=0.0, description="Maximum temporal gap in seconds within a single continuous event cluster.")
    min_event_score: float = Field(default=0.20, ge=0.0, le=1.0, description="Minimum heuristic event score required to flag a moment.")
    min_detector_score: float = Field(
        default=0.35, ge=0.0, le=1.0,
        description=(
            "Minimum detector confidence for a candidate to be considered. Measured on "
            "real_aerial_footage.mp4: real vehicles score 0.67-0.89; a white parking-line "
            "marking and a degenerate full-frame box both scored 0.28, and those produced "
            "spurious events at 0-4s."
        ),
    )
    max_box_area_ratio: float = Field(
        default=0.90, gt=0.0, le=1.0,
        description=(
            "Reject candidates covering more than this fraction of the frame. Grounding DINO "
            "returned a 99.8%-area box for 'white cars.' on empty asphalt."
        ),
    )
    min_colour_score: float = Field(
        default=0.45, ge=0.0, le=1.0,
        description=(
            "Minimum photometric colour-consistency score required to keep a detection when the "
            "query names a colour. Grounding DINO returns a best-matching region for any prompt "
            "and its confidence does not separate present from absent targets (measured 0.83-0.92 "
            "for both). Pixel colour does: on datasets/samples/video/real_aerial_footage.mp4, "
            "colours present in the clip score 0.97-1.00 (red 1.000, white 0.969) and colours "
            "absent score 0.21-0.26 (yellow 0.230, blue 0.260, green 0.209). 0.45 sits in that gap."
        ),
    )


class VideoFlag(BaseModel):
    """
    Important-moment event flag.
    Combines start/end timestamps, peak keyframe, spatial bounding box, SAM2 mask,
    and a clearly documented heuristic event-ranking score.
    """
    flag_id: str
    video_id: Optional[str] = None
    start_timestamp: float
    end_timestamp: float
    start_frame: int
    end_frame: int
    peak_frame: int
    label: str
    reason: str
    event_score: float = Field(
        description="Heuristic event-ranking score; not calibrated model probability."
    )
    keyframe_url: Optional[str] = None
    overlay_url: Optional[str] = None
    mask_url: Optional[str] = None
    box_2d: Optional[List[float]] = None  # [ymin, xmin, ymax, xmax] in normalized 0-1 or pixel coords
    model_scores: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw scores from underlying specialist models (e.g. detector_score, v4_score, sam2_score)."
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VideoAnalysisRequest(BaseModel):
    """Request payload for video footage analysis."""
    request_id: Optional[str] = None
    query: str
    sampling: Optional[VideoSamplingConfig] = None
    flagging: Optional[VideoFlagConfig] = None


class VideoAnalysisResponse(BaseModel):
    """Response payload for video analysis and important-moment flagging."""
    job_id: str
    status: JobStatus
    task: TaskType
    workflow_id: str = "workflow_video_analysis"
    workflow_reason: str
    video_metadata: VideoMetadata
    flags: List[VideoFlag] = Field(default_factory=list)
    models_used: List[str] = Field(default_factory=list)
    execution_trace: List[ExecutionStep] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    artifacts: Dict[str, List[str]] = Field(default_factory=dict)
