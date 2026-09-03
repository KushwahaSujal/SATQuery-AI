from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from .agent import JobStatus, TaskType, ExecutionStep, WorkflowPlan
from .models import ModelCapabilityInfo
from .evidence import EvidencePackage


class RasterMetadataResponse(BaseModel):
    filename: str
    format: str
    width: int
    height: int
    bands: int
    dtype: str
    crs: Optional[str] = None
    bounds: Optional[List[float]] = None
    transform: Optional[List[float]] = None
    resolution: Optional[List[float]] = None
    nodata: Optional[float] = None
    band_descriptions: List[str] = Field(default_factory=list)
    tags: Dict[str, Any] = Field(default_factory=dict)
    detected_modality: str
    modality_confidence: float
    modality_reason: str
    preview_url: Optional[str] = None


class UploadResponse(BaseModel):
    request_id: str
    job_id: Optional[str] = None
    uploaded_files: List[str]
    metadata: List[RasterMetadataResponse]

    @model_validator(mode="after")
    def sync_job_id(self):
        if not self.job_id:
            self.job_id = self.request_id
        return self


class AnalyzeResponse(BaseModel):
    request_id: str
    job_id: Optional[str] = None
    status: JobStatus
    task: TaskType
    workflow_id: str
    workflow: Optional[str] = None
    workflow_reason: str
    answer: Optional[str] = None
    confidence: Optional[float] = None  # None if model did not produce genuine score
    models_used: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    evidence: EvidencePackage = Field(default_factory=EvidencePackage)
    execution_trace: List[ExecutionStep] = Field(default_factory=list)
    trace: List[ExecutionStep] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    artifacts: Dict[str, List[str]] = Field(default_factory=dict)
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)
    orchestration: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def sync_aliases(self):
        if not self.job_id:
            self.job_id = self.request_id
        if not self.workflow:
            self.workflow = self.workflow_id
        if not self.trace and self.execution_trace:
            self.trace = self.execution_trace
        elif not self.execution_trace and self.trace:
            self.execution_trace = self.trace
        return self


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    device: str
    models_available: Dict[str, bool]
    database_connected: bool = True


class ModelsListResponse(BaseModel):
    models: List[ModelCapabilityInfo]
