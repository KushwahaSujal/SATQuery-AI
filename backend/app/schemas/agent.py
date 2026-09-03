from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    GENERATING_EVIDENCE = "GENERATING_EVIDENCE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskType(str, Enum):
    SINGLE_IMAGE_VQA = "single_image_vqa"
    SINGLE_IMAGE_CAPTION = "single_image_caption"
    SINGLE_IMAGE_GROUNDING = "single_image_grounding"
    BI_TEMPORAL_CHANGE = "bi_temporal_change"
    BI_TEMPORAL_CHANGE_VQA = "bi_temporal_change_vqa"
    OPTICAL_SAR_ANALYSIS = "optical_sar_analysis"
    VIDEO_GROUNDING = "video_grounding"
    VIDEO_GROUNDING_TRACKING = "video_grounding_tracking"
    VIDEO_VQA = "video_vqa"
    VIDEO_CHANGE = "video_change"
    UNSUPPORTED = "unsupported"


class ExecutionStep(BaseModel):
    timestamp: str
    step: str
    status: str = "success"  # success | warning | error | running
    model: Optional[str] = None
    tool: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Optional[str] = None


class WorkflowPlan(BaseModel):
    workflow_id: str
    task: TaskType
    reason: str  # Concise observable reason
    selected_models: List[str]
    steps: List[str]
    parameters: Dict[str, Any] = Field(default_factory=dict)
