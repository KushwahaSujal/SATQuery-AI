from typing import Any, ClassVar, Dict, FrozenSet, List, Optional
from pydantic import BaseModel, Field, model_validator


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
    load_state: str = "NOT_CONFIGURED"  # NOT_CONFIGURED | AVAILABLE | PRESENT_NOT_SERVING | LOADED | FAILED
    loaded: bool = False
    # `available`/`loaded` only ever meant "the checkpoint file is on disk" and "the weights are in
    # RAM". Two adapters load their real checkpoints and still refuse to produce an output on
    # purpose, so a capability listing that reports only those two booleans reads as "this works"
    # (Q-045). `serving` is the field that answers "will a request to this model return a result?"
    # and `refusal_reason` says why not. PRESENT_NOT_SERVING is the load_state that goes with
    # serving=False: the checkpoint is present, so this is NOT the missing-checkpoint case that
    # NOT_CONFIGURED and ModelUnavailableError/503 mean.
    serving: bool = False
    refusal_reason: Optional[str] = None
    validation_status: str = "PENDING_VERIFICATION"  # PENDING_VERIFICATION | VERIFIED | FAILED | NOT_APPLICABLE
    last_error: Optional[str] = None
    latency: Optional[float] = None
    memory: Optional[float] = None
    device: str = "auto"
    precision: Optional[str] = None
    status: str = "NOT_CONFIGURED"  # mirrors load_state


class ModelResult(BaseModel):
    """Normalized output contract from all model adapters.

    `status` is enforced here, not advisory (Q-045). Before this, two adapters set
    `status="NOT_CONFIGURED"` to mean "I deliberately produced nothing" and nothing in the backend
    read the field, so the whole refusal rested on the prose in `answer` — which a caller, a
    serializer or an LLM answer-writer is free to replace. The validator below makes the
    contradiction "a refusal that also carries a payload" unconstructible, and guarantees that the
    status is visible in both `answer` and `warnings` no matter what the adapter wrote.
    """

    #: Statuses that mean "this adapter deliberately returned no output". Distinct from a missing
    #: checkpoint (`ModelUnavailableError`, code MODEL_CHECKPOINT_MISSING, HTTP 503) and from an
    #: inference failure: a refusal is a legitimate, informative answer.
    REFUSAL_STATUSES: ClassVar[FrozenSet[str]] = frozenset({"NOT_CONFIGURED"})

    model_name: str
    task: str
    status: Optional[str] = None
    answer: Optional[str] = None
    confidence: Optional[float] = None  # None if model doesn't compute true probability
    boxes: List[Dict[str, Any]] = Field(default_factory=list)
    masks: List[Dict[str, Any]] = Field(default_factory=list)
    logits: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    @property
    def is_refusal(self) -> bool:
        """True when this result is a deliberate refusal and carries no model output."""
        return (self.status or "").strip().upper() in self.REFUSAL_STATUSES

    @property
    def refusal_reason(self) -> Optional[str]:
        """The adapter's own explanation for a refusal, or None if this is not a refusal."""
        if not self.is_refusal:
            return None
        reason = self.metadata.get("reason") or self.metadata.get("blocker")
        return str(reason) if reason else self.answer

    @model_validator(mode="after")
    def _enforce_refusal_carries_no_result(self):
        """A refusal may not carry a payload, and must name its status in the text a caller renders.

        Raising rather than quietly emptying the payload is deliberate: a refusal that also has a
        mask is a contradiction inside one adapter, not a recoverable input problem, and silently
        dropping the mask would hide the bug that produced it. No adapter does this today, so this
        branch is a guard against the next one.
        """
        if not self.is_refusal:
            return self
        status = (self.status or "").strip().upper()
        populated = [f for f in ("boxes", "masks") if getattr(self, f)]
        if self.logits is not None:
            populated.append("logits")
        if self.confidence is not None:
            populated.append("confidence")
        if populated:
            raise ValueError(
                f"ModelResult for '{self.model_name}' has status={status!r} but also carries "
                f"{', '.join(populated)}. A refusal must carry no model output: either drop the "
                f"payload or do not report {status}."
            )
        if not self.answer:
            self.answer = (
                f"{status}: '{self.model_name}' returned no result for task '{self.task}' on this "
                f"deployment."
            )
        elif status not in self.answer.upper():
            self.answer = f"{status}: {self.answer}"
        if not any(status in (w or "").upper() for w in self.warnings):
            self.warnings.insert(
                0,
                f"{self.model_name} returned {status} for task '{self.task}': no model output was "
                f"produced and nothing below may be read as one.",
            )
        return self
