"""
SatQuery AI — Advanced Orchestration Layer Schemas & Contracts
Formal definitions for Capabilities, Intents, Entities, DAG Execution Graphs,
Provenance Graphs, Policies, and Operational Metrics.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class CapabilityPriority(int, Enum):
    """
    Explicit execution precedence.
    Higher integer = evaluated first during matching.
    """
    GROUNDING = 100
    OPTICAL_SAR = 90
    TEMPORAL_CHANGE_VQA = 80
    TEMPORAL_CHANGE = 75
    MULTISPECTRAL = 70
    SAR = 65
    VIDEO = 60
    VQA = 50
    CAPTION = 40
    VISUALIZATION = 30
    PIXEL_INSPECTION = 20
    REPORT_GENERATION = 10


class ModalityType(str, Enum):
    IMAGE = "image"
    MULTI_IMAGE = "multi_image"
    VIDEO = "video"
    OPTICAL_RASTER = "optical_raster"
    MULTISPECTRAL_RASTER = "multispectral_raster"
    SAR_RASTER = "sar_raster"
    OPTICAL_PLUS_SAR = "optical_plus_sar"
    UNKNOWN = "unknown"


class ExtractedQueryEntities(BaseModel):
    """
    Structured attributes extracted from user natural language query.
    Enables explainable, query-aware reasoning without exposing private chain-of-thought.
    """
    object_class: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    position: Optional[str] = None
    reference_object: Optional[str] = None
    relation: Optional[str] = None
    ordering: Optional[str] = None
    temporal_intent: Optional[str] = None
    change_intent: Optional[str] = None
    raw_query: str = ""
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None


class IntentClassificationResult(BaseModel):
    """
    Output of the structured intent classifier.
    routing_confidence is strictly labeled as router confidence, NOT model ML accuracy.
    """
    task: str
    routing_confidence: float = Field(..., ge=0.0, le=1.0)
    input_requirements: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    relations: List[Dict[str, str]] = Field(default_factory=list)
    extracted_entities: ExtractedQueryEntities = Field(default_factory=ExtractedQueryEntities)
    is_ambiguous: bool = False
    suggested_clarification: Optional[str] = None


class CapabilityDefinition(BaseModel):
    """
    Formal capability specification. Every system capability declares its exact requirements.
    """
    capability_id: str
    name: str
    description: str
    accepted_input_types: List[str]
    required_modalities: List[str]
    optional_modalities: List[str] = Field(default_factory=list)
    output_types: List[str]
    required_models: List[str]
    optional_models: List[str] = Field(default_factory=list)
    required_tools: List[str]
    workflow: str
    priority: int = CapabilityPriority.VQA
    enabled: bool = True
    validation_requirements: Dict[str, Any] = Field(default_factory=dict)


class DAGNodeStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class DAGPlanNode(BaseModel):
    """
    Node in the Directed Acyclic Graph execution plan.
    """
    node_id: str
    tool_name: str
    model_name: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    is_parallelizable: bool = False
    timeout_seconds: float = 60.0
    status: DAGNodeStatus = DAGNodeStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class DAGExecutionPlan(BaseModel):
    """
    Structured DAG execution plan representing the entire workflow graph.
    """
    plan_id: str
    workflow_id: str
    capability_id: str
    nodes: List[DAGPlanNode] = Field(default_factory=list)
    execution_order: List[List[str]] = Field(default_factory=list)  # Stages of parallelizable nodes
    total_estimated_timeout: float = 120.0
    created_at: str = ""


class ProvenanceNode(BaseModel):
    """
    Granular record in the internal provenance tree.
    Tracks every artifact and decision directly back to its source files and checkpoints.
    """
    node_id: str
    artifact_id: Optional[str] = None
    source_type: str  # SOURCE_FILE | MODEL_CHECKPOINT | PREPROCESSING | INFERENCE | FUSION
    name: str
    model: Optional[str] = None
    model_version: Optional[str] = None
    checkpoint_hash: Optional[str] = None
    input_ids: List[str] = Field(default_factory=list)
    timestamp: str
    checksum_sha256: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceGraph(BaseModel):
    """
    Full provenance graph from raw imagery to final user-visible response.
    """
    job_id: str
    root_inputs: List[str] = Field(default_factory=list)
    nodes: List[ProvenanceNode] = Field(default_factory=list)
    edges: List[Dict[str, str]] = Field(default_factory=list)  # {"from": ..., "to": ...}


class PolicyViolation(BaseModel):
    policy_name: str
    violation_code: str
    message: str
    severity: str = "ERROR"  # ERROR | WARNING | ADVISORY


class OperationalMetrics(BaseModel):
    """
    Operational latency and reliability metrics. Strictly labeled as operational telemetry,
    never as ML benchmark accuracy.
    """
    job_id: str
    capability_id: str
    workflow_id: str
    total_duration_ms: float
    model_durations_ms: Dict[str, float] = Field(default_factory=dict)
    tool_durations_ms: Dict[str, float] = Field(default_factory=dict)
    cache_hit: bool = False
    cpu_percent: Optional[float] = None
    ram_mb_used: Optional[float] = None
    vram_mb_used: Optional[float] = None
    retry_count: int = 0
