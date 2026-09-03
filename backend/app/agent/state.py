from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.app.schemas.agent import JobStatus, TaskType, ExecutionStep, WorkflowPlan
from backend.app.schemas.models import ModelResult
from backend.app.schemas.evidence import EvidencePackage
from backend.app.geo.metadata import RasterMetadata


@dataclass
class AgentState:
    """
    Central state machine object for tracking the full lifecycle of a SatQuery AI job.
    """
    request_id: str
    query: str
    image_paths: List[str]
    metadata: List[RasterMetadata] = field(default_factory=list)
    modalities: List[str] = field(default_factory=list)
    timestamps: List[Optional[str]] = field(default_factory=list)
    
    status: JobStatus = JobStatus.QUEUED
    task: Optional[TaskType] = None
    workflow_id: Optional[str] = None
    reason: Optional[str] = None  # Observable concise workflow selection reason
    selected_models: List[str] = field(default_factory=list)
    plan: Optional[WorkflowPlan] = None
    
    model_results: List[ModelResult] = field(default_factory=list)
    evidence: EvidencePackage = field(default_factory=EvidencePackage)
    answer: Optional[str] = None
    confidence: Optional[float] = None
    
    execution_trace: List[ExecutionStep] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, List[str]] = field(default_factory=dict)

    # Advanced Orchestration Layer additions
    capability_id: Optional[str] = None
    routing_confidence: Optional[float] = None
    query_entities: Optional[Dict[str, Any]] = None
    dag_plan: Optional[Dict[str, Any]] = None
    provenance_graph: Optional[Dict[str, Any]] = None
    quality_status: str = "PASS"
    quality_flags: List[str] = field(default_factory=list)
    cache_hit: bool = False

    def add_trace(
        self,
        step_name: str,
        status: str = "success",
        model: Optional[str] = None,
        tool: Optional[str] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        duration_ms: Optional[float] = None,
        details: Optional[str] = None
    ) -> None:
        now_iso = datetime.utcnow().isoformat() + "Z"
        step = ExecutionStep(
            timestamp=now_iso,
            step=step_name,
            status=status,
            model=model,
            tool=tool,
            started_at=started_at or now_iso,
            completed_at=completed_at,
            duration_ms=duration_ms,
            details=details
        )
        self.execution_trace.append(step)
