from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelCapabilityInfo(BaseModel):
    model_id: Optional[str] = None
    name: str
    family: Optional[str] = None
    version: Optional[str] = None
    task: str
    capabilities: List[str] = Field(default_factory=list)
    supported_tasks: List[str] = Field(default_factory=list)
    supported_modalities: List[str] = Field(default_factory=list)
    input_count: int = 1
    input_relationship: str = "single"  # single | temporal | cross_modal
    adapter: Optional[str] = None
    checkpoint: Optional[str] = None
    checkpoint_path: Optional[str] = None
    source: Optional[str] = None
    license: Optional[str] = None
    input_requirements: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    device_requirements: Dict[str, Any] = Field(default_factory=dict)
    lazy_load: bool = True
    availability: bool = False
    available: bool = False
    load_state: str = "NOT_CONFIGURED"  # NOT_CONFIGURED | AVAILABLE | LOADED | FAILED
    loaded: bool = False
    validation_status: str = "PENDING_VERIFICATION"  # PENDING_VERIFICATION | VERIFIED | FAILED
    last_error: Optional[str] = None
    latency: Optional[float] = None
    memory: Optional[float] = None
    device: str = "auto"
    precision: Optional[str] = None
    status: str = "NOT_CONFIGURED"  # NOT_CONFIGURED | AVAILABLE | LOADED | FAILED


class ModelResult(BaseModel):
    """Normalized output contract from all model adapters."""
    model_name: str
    task: str
    answer: Optional[str] = None
    confidence: Optional[float] = None  # None if model doesn't compute true probability
    boxes: List[Dict[str, Any]] = Field(default_factory=list)
    masks: List[Dict[str, Any]] = Field(default_factory=list)
    logits: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
