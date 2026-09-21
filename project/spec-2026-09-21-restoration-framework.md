# Spec — `backend/app/restoration/`: quality assessment, planning, fused correction

**Date:** 2026-09-21 · **Branch:** `prototype` · **Written against:** `7d209db`
**Owner:** Ushnik. **Blocking hand-off:** §2 (`restoration/schemas.py`) — Ayushman's
salt-and-pepper stage (`split-ushnik-ayushman.md` Ayushman #3) is built against it.
**Status:** specification only. No code in `backend/` was created or modified for this document.

**File location and name.** Working specs and plans live in `project/`, dated, one file per
piece of work — `project/plan-2026-09-14-agent-parity-geo.md` is the precedent. `docs/` holds
the team's public-facing dossiers, not internal specs (`project/README.md`), so this belongs in
`project/`. Named `spec-` rather than `plan-` because it defines contracts rather than
sequencing a night's work.

---

## 0. Provenance of this design — read this first

The task list says "the design is already agreed in this session's brainstorm". **The recorded
brainstorm is three lines long.** Everything found in the repository:

- **`project/memory.md:340-342`** — "Brainstormed (not built) the image-restoration subsystem:
  detectors, a fused single-pass matrix correction, salt-and-pepper for stills and video, and a
  confidence critique agent; upscaling is post-demo with learned SR."
- **`project/memory.md:81`** — "Image restoration agents + confidence critique agent + learned
  SR — post-demo."
- **`project/split-ushnik-ayushman.md:83-86`** — the component list: schemas, quality detectors,
  planner, the fused single-pass matrix/LUT correction, the `assess_quality` / `restore_input`
  DAG nodes. Plus: the confidence critique agent "consumes model scores, the verifier's verdict
  and the restoration receipt, and can only hold or lower confidence."
- **`project/split-ushnik-ayushman.md:105-109`** — salt-and-pepper is a switching median for
  stills and video, **gated by measured impulse density**, self-contained in
  `restoration/stages.py`. Learned SR "stays disabled until" the weights are verified and
  measured on a held-out set.
- **`project/qna.md`** — **nothing.** `grep -i restor project/qna.md` returns 4 hits, all
  unrelated: a restored `frontend/src/lib`, a renamed trace step, a patched file, a `git revert`.
  There is no Q-entry for the restoration brainstorm, and no entry mentions impulse density,
  median filtering, LUTs, Real-ESRGAN or SwinIR.

So the following are **agreed and recorded**:

1. The component list, and that it lives in `backend/app/restoration/`.
2. The correction is **fused** and **single-pass**, matrix/LUT.
3. Salt-and-pepper is a **switching median**, covers **stills and video**, and is **gated on
   measured impulse density**.
4. Learned super-resolution is **out of scope until verified and measured**.
5. The confidence critique agent consumes the receipt and **can only hold or lower** confidence.
6. `restoration/schemas.py` is the hand-off artefact and comes before Ayushman's stage.

Everything below that level of detail — **every field name, type, unit, default, threshold, the
decision table, the DAG node placement and the receipt shape** — is **not recorded anywhere** and
is therefore a **PROPOSAL REQUIRING CONFIRMATION**. It is written decisively, because Ayushman is
blocked on it and ambiguity costs him a day, but it carries no more authority than one person's
reconstruction. Sections marked **[PROPOSAL]** are mine. Sections marked **[RECORDED]** trace to
the table above.

**Numbers in this document.** Every numeric threshold here is labelled `TARGET`, `ASSUMPTION` or
`NOT MEASURED`. Nothing in this document is a measured result. Byte figures labelled
`ARITHMETIC` are computed from array shapes, not observed.

---

## 1. Scope and non-goals

### 1.1 In scope

| # | Deliverable | Owner |
|---|---|---|
| 1 | `restoration/schemas.py` — the contracts in §2 | Ushnik |
| 2 | `restoration/detectors.py` — the measurements in §3 | Ushnik |
| 3 | `restoration/planner.py` — detector output → ordered stage list (§4) | Ushnik |
| 4 | `restoration/correction.py` — the fused matrix/LUT pass (§5) | Ushnik |
| 5 | `restoration/stages.py` — the stage registry, plus the switching median | Ushnik (registry) · Ayushman (median) |
| 6 | `agent/tools/restoration.py` — `assess_quality`, `restore_input` (§6) | Ushnik |

### 1.2 Non-goals

- **Learned super-resolution is out of scope.** `[RECORDED]` Real-ESRGAN / SwinIR "stays
  disabled until" the weights are verified with `scripts/verify_checkpoints.py` and measured on a
  held-out set (`split-ushnik-ayushman.md:107-109`). The `super_resolve` stage **does** exist in
  this spec, and it exists precisely so that it can return `NOT_CONFIGURED` with a reason rather
  than being silently absent. It never runs in v1.
- **Restoration never creates information.** `[PROPOSAL]` Inpainting, cloud gap-filling and
  any generative completion are permanently out of scope, not merely deferred: they synthesise
  pixels, which `project/rules.md` §1.2 forbids outright ("no placeholder predictions rendered
  as findings"). Learned SR is deferred rather than forbidden only because a measured held-out
  score would make its output defensible.
- **No geometric change.** `[PROPOSAL]` No resampling, no GSD change, no co-registration, no
  orthorectification, no rotation, no crop. Output width, height, band count, dtype, CRS,
  transform and nodata are identical to input. This is load-bearing: boxes, masks and GeoJSON
  produced downstream map 1:1 onto the original raster, so `geometry_preserved` is asserted, not
  hoped for. Resampling to the segmenters' 0.5 m training GSD is a **separate** future concern
  (`docs/models/trained_segmenters.md`, "The 0.5 m assumption") and is not restoration.
- **No atmospheric or radiometric calibration.** TOA/BOA conversion needs per-scene sensor
  calibration metadata we do not have for arbitrary uploads.
- **No changes to any model adapter.** Adapters keep their training-time preprocessing exactly
  (`rules.md` §3, `decisions.md` D-011). Restoration happens strictly upstream of
  `preprocess_optical_image` / the trainers' `MEAN`/`STD`.
- **Not a capability.** `[PROPOSAL]` Restoration is not user-requestable and does not appear in
  `capability_registry.py` as a `capability_id`. It is two tool nodes added to existing
  capabilities. Nothing routes to "restore my image".
- **No new dependency.** numpy + scipy + `opencv-python-headless` are already allowed
  (`rules.md` §2); nothing here needs more.

---

## 2. `restoration/schemas.py` — the blocking deliverable **[PROPOSAL]**

Pydantic v2 `BaseModel`, because the receipt crosses the API boundary (`rules.md` §3). Enums are
`(str, Enum)`, matching `orchestration/schemas.py`. No dataclasses: `AgentState` is a dataclass
but everything it carries into a response is pydantic.

### 2.1 Array and unit conventions Ayushman must code against

These four lines are the whole contract for a stage author:

1. **Array layout** is `(bands, height, width)`, C-order — what
   `RasterInspector.read_as_array` returns (`geo/raster.py:242`).
2. **dtype is preserved.** A stage receives the native dtype (`uint8`, `uint16`, `float32`) and
   must return the same dtype and the same shape. Internal float work is fine; the return is
   cast back.
3. **`dn_max`** is the band's full-scale value: 255 for `uint8`, 65535 for `uint16`, and for
   float rasters the measured 99.99th percentile of finite values (recorded in the assessment, so
   it is never guessed twice).
4. **`valid_mask`** is a `bool` array of shape `(height, width)`, True where the pixel is finite
   and not equal to `RasterMetadata.nodata`. Every detector and every stage takes it and must
   leave invalid pixels **bit-identical**. Averaging nodata into real pixels is the single
   easiest way to fabricate data here.

Units used throughout: `fraction` = of valid pixels, in [0, 1]. `dn` = digital numbers in the
band's native scale. `dimensionless` = a normalised ratio. `ms` = milliseconds. `m` = metres.

### 2.2 Enumerations

```python
class DegradationKind(str, Enum):
    IMPULSE_NOISE       = "IMPULSE_NOISE"        # salt and pepper
    GAUSSIAN_NOISE      = "GAUSSIAN_NOISE"
    SATURATION_CLIPPING = "SATURATION_CLIPPING"  # pixels pinned at 0 or dn_max
    LOW_DYNAMIC_RANGE   = "LOW_DYNAMIC_RANGE"
    BRIGHTNESS_BIAS     = "BRIGHTNESS_BIAS"
    COLOR_CAST          = "COLOR_CAST"
    BLUR                = "BLUR"
    STRIPING            = "STRIPING"
    MISSING_DATA        = "MISSING_DATA"         # nodata / non-finite coverage
    LOW_RESOLUTION      = "LOW_RESOLUTION"       # reported only; SR is out of scope


class DetectorStatus(str, Enum):
    MEASURED       = "MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"   # e.g. a colour metric on a 1-band raster
    NOT_CONFIGURED = "NOT_CONFIGURED"   # detector exists but is disabled / unimplemented
    FAILED         = "FAILED"           # it ran and raised; value stays None, never 0.0


class ThresholdBasis(str, Enum):
    """Why this threshold is allowed to gate a stage. See §3.4."""
    PRINCIPLED     = "PRINCIPLED"      # definitional or read from metadata; may gate
    PROVISIONAL    = "PROVISIONAL"     # plausible but uncalibrated on our imagery; may gate,
                                       # and every receipt it fires says PROVISIONAL
    NOT_CALIBRATED = "NOT_CALIBRATED"  # advisory only; the planner refuses to gate on it


class QualityVerdict(str, Enum):
    CLEAN        = "CLEAN"          # nothing gate-eligible exceeded its threshold
    DEGRADED     = "DEGRADED"       # at least one did
    UNASSESSABLE = "UNASSESSABLE"   # the raster could not be read or measured


class StageStatus(str, Enum):
    APPLIED                  = "APPLIED"
    SKIPPED_BELOW_THRESHOLD  = "SKIPPED_BELOW_THRESHOLD"
    SKIPPED_NOT_APPLICABLE   = "SKIPPED_NOT_APPLICABLE"
    NOT_CONFIGURED           = "NOT_CONFIGURED"
    FAILED                   = "FAILED"


class RestorationStatus(str, Enum):
    NOT_REQUESTED     = "NOT_REQUESTED"      # the feature is switched off in config
    ASSESSED_NO_ACTION = "ASSESSED_NO_ACTION"  # measured, nothing to do — the common case
    RESTORED          = "RESTORED"
    PARTIAL           = "PARTIAL"            # some stages applied, some NOT_CONFIGURED/FAILED
    NOT_CONFIGURED    = "NOT_CONFIGURED"
    FAILED            = "FAILED"


class ConfidencePosture(str, Enum):
    NEUTRAL  = "NEUTRAL"
    CAUTION  = "CAUTION"
    DEGRADED = "DEGRADED"


class SourceKind(str, Enum):
    RASTER      = "RASTER"
    VIDEO_FRAME = "VIDEO_FRAME"
```

### 2.3 `QualityMetric` — one measurement

```python
class QualityMetric(BaseModel):
    """One measured quantity. Never carries a value it did not measure."""
    name: str                                  # stable id, e.g. "impulse_density"
    kind: DegradationKind
    status: DetectorStatus = DetectorStatus.MEASURED
    value: Optional[float] = None              # None unless status == MEASURED
    unit: str                                  # "fraction" | "dn" | "dimensionless" | "m"
    per_band: Dict[str, float] = Field(default_factory=dict)   # "0","1",... -> value
    reduction: str = "max_over_bands"          # how value was reduced from per_band
    threshold: Optional[float] = None          # the gate, in the same unit as value
    threshold_basis: ThresholdBasis = ThresholdBasis.NOT_CALIBRATED
    exceeds_threshold: Optional[bool] = None   # None when value or threshold is None
    gate_eligible: bool = False                # threshold_basis in (PRINCIPLED, PROVISIONAL)
    sample_fraction: float = 1.0               # 1.0 = every valid pixel was examined
    detector_version: str                      # e.g. "impulse@1"
    reason: Optional[str] = None               # REQUIRED when status != MEASURED
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _honesty(self):
        if self.status is DetectorStatus.MEASURED:
            if self.value is None:
                raise ValueError(f"{self.name}: MEASURED requires a value")
        else:
            if self.value is not None:
                raise ValueError(f"{self.name}: {self.status} must not carry a value")
            if not self.reason:
                raise ValueError(f"{self.name}: {self.status} requires a reason")
        self.gate_eligible = self.threshold_basis in (
            ThresholdBasis.PRINCIPLED, ThresholdBasis.PROVISIONAL)
        if self.value is not None and self.threshold is not None:
            self.exceeds_threshold = self.value >= self.threshold
        else:
            self.exceeds_threshold = None
        return self
```

### 2.4 `QualityAssessment` — the `assess_quality` output, one per input

```python
class QualityAssessment(BaseModel):
    assessment_id: str                    # f"qa_{job_id}_{image_index}" (or _f{frame_index})
    source_kind: SourceKind = SourceKind.RASTER
    image_index: int                      # position in state.image_paths
    image_path: str
    frame_index: Optional[int] = None     # VIDEO_FRAME only
    timestamp_sec: Optional[float] = None # VIDEO_FRAME only

    width: int
    height: int
    bands: int
    dtype: str                            # numpy dtype name as read
    dn_max: float                         # §2.1 rule 3
    nodata: Optional[float] = None
    valid_pixel_count: int
    total_pixel_count: int

    metrics: List[QualityMetric] = Field(default_factory=list)
    verdict: QualityVerdict = QualityVerdict.CLEAN
    degradations_detected: List[DegradationKind] = Field(default_factory=list)  # gate-eligible,
                                                                               # over threshold
    advisories: List[str] = Field(default_factory=list)   # NOT_CALIBRATED metrics that looked bad
    detector_config_hash: str             # sha256 of the restoration config block, 16 hex chars
    duration_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)

    def metric(self, name: str) -> Optional[QualityMetric]: ...
```

### 2.5 `RestorationPlan`

```python
class PlannedStage(BaseModel):
    stage_id: str                         # "impulse_denoise" | "photometric_correct" | ...
    order: int                            # 10, 20, 30 ... — see §4.1
    params: Dict[str, Any] = Field(default_factory=dict)
    triggered_by: List[str] = Field(default_factory=list)   # QualityMetric.name values
    threshold_basis: ThresholdBasis                          # weakest basis among triggers
    fused: bool = False                   # True when executed inside the single matrix/LUT pass


class RestorationPlan(BaseModel):
    plan_id: str
    image_index: int
    stages: List[PlannedStage] = Field(default_factory=list)
    is_noop: bool = True
    rationale: str = ""                   # one human sentence, goes into the trace step
    decision_table_version: str = "dt@1"  # bump on any change to §4.2
```

### 2.6 `StageReceipt` — one per stage, applied or not

```python
class StageReceipt(BaseModel):
    stage_id: str
    stage_version: str                    # e.g. "switching_median@1"
    status: StageStatus
    reason: Optional[str] = None          # REQUIRED unless status == APPLIED
    order: int
    params: Dict[str, Any] = Field(default_factory=dict)   # the values actually used
    triggered_by: List[str] = Field(default_factory=list)
    threshold_basis: Optional[ThresholdBasis] = None
    fused: bool = False

    pixels_total: Optional[int] = None
    pixels_modified: Optional[int] = None
    fraction_modified: Optional[float] = None   # pixels_modified / valid pixels
    max_abs_delta_dn: Optional[float] = None
    mean_abs_delta_dn: Optional[float] = None

    frames_total: Optional[int] = None          # VIDEO only
    frames_modified: Optional[int] = None       # VIDEO only

    is_geometric: bool = False             # must be False in v1; see §1.2
    input_sha256: Optional[str] = None
    output_sha256: Optional[str] = None
    duration_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _honesty(self):
        if self.status is not StageStatus.APPLIED and not self.reason:
            raise ValueError(f"{self.stage_id}: {self.status} requires a reason")
        if self.status is StageStatus.APPLIED and self.fraction_modified is None:
            raise ValueError(f"{self.stage_id}: APPLIED must report fraction_modified")
        if self.is_geometric:
            raise ValueError(f"{self.stage_id}: geometric stages are out of scope (spec §1.2)")
        return self
```

### 2.7 `ConfidenceAdvice` — the contract with the critique agent

```python
class ConfidenceAdvice(BaseModel):
    """
    What the restoration receipt is allowed to say about confidence.

    There is deliberately no field that can RAISE confidence. max_confidence_multiplier is
    bounded at 1.0, so the critique agent's arithmetic
        final = model_confidence * advice.max_confidence_multiplier
    can only hold or lower. `blocking` sets confidence to None, matching the precedent in
    AdjudicationResult.confidence (schemas/evidence.py:70-74), which is None on conflict rather
    than an invented number.
    """
    posture: ConfidencePosture = ConfidencePosture.NEUTRAL
    max_confidence_multiplier: float = Field(default=1.0, ge=0.0, le=1.0)
    blocking: bool = False                # True -> confidence must become None
    reasons: List[str] = Field(default_factory=list)   # one string per contributing fact
```

### 2.8 `RestorationReceipt` — travels with the response

```python
class RestoredInput(BaseModel):
    image_index: int
    original_path: str
    consumed_path: str                    # what the model actually read; == original if untouched
    was_modified: bool
    original_sha256: Optional[str] = None
    consumed_sha256: Optional[str] = None
    georeferencing_preserved: Optional[bool] = None   # None for non-georeferenced input


class RestorationReceipt(BaseModel):
    schema_version: str = "restoration-receipt@1"
    receipt_id: str
    job_id: str
    status: RestorationStatus = RestorationStatus.NOT_REQUESTED

    # --- the one bit everything else hangs off ------------------------------------------
    input_modified: bool = False

    assessments: List[QualityAssessment] = Field(default_factory=list)
    plans: List[RestorationPlan] = Field(default_factory=list)
    stages: List[StageReceipt] = Field(default_factory=list)
    inputs: List[RestoredInput] = Field(default_factory=list)

    stages_planned: int = 0
    stages_applied: int = 0
    stages_skipped: int = 0
    stages_not_configured: int = 0
    stages_failed: int = 0

    # --- what the critique agent reads (see §7) ------------------------------------------
    residual_degradations: List[DegradationKind] = Field(default_factory=list)
    unmeasured_degradations: List[DegradationKind] = Field(default_factory=list)
    out_of_measured_range: List[str] = Field(default_factory=list)
    provisional_gates_fired: List[str] = Field(default_factory=list)
    geometry_preserved: bool = True
    confidence_advice: ConfidenceAdvice = Field(default_factory=ConfidenceAdvice)

    config_version: str = "restoration@1"
    detector_config_hash: str = ""
    decision_table_version: str = "dt@1"
    total_duration_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _counts_and_honesty(self):
        self.stages_planned = len(self.stages)
        self.stages_applied = sum(s.status is StageStatus.APPLIED for s in self.stages)
        self.stages_skipped = sum(
            s.status in (StageStatus.SKIPPED_BELOW_THRESHOLD,
                         StageStatus.SKIPPED_NOT_APPLICABLE) for s in self.stages)
        self.stages_not_configured = sum(
            s.status is StageStatus.NOT_CONFIGURED for s in self.stages)
        self.stages_failed = sum(s.status is StageStatus.FAILED for s in self.stages)
        really_modified = any(
            s.status is StageStatus.APPLIED and (s.fraction_modified or 0.0) > 0.0
            for s in self.stages)
        if self.input_modified != really_modified:
            raise ValueError(
                "input_modified must equal 'some stage APPLIED and changed pixels' "
                f"(field={self.input_modified}, stages say={really_modified})")
        if self.input_modified and not any(i.was_modified for i in self.inputs):
            raise ValueError("input_modified is True but no RestoredInput is marked modified")
        self.geometry_preserved = not any(s.is_geometric for s in self.stages)
        return self
```

### 2.9 The stage interface Ayushman implements

```python
StageFn = Callable[[np.ndarray, np.ndarray, QualityAssessment, Dict[str, Any]],
                   Tuple[np.ndarray, StageReceipt]]
#              (arr, valid_mask, assessment, params) -> (arr_out, receipt)

STAGE_REGISTRY: Dict[str, "StageSpec"] = {}

def register_stage(stage_id: str, *, order: int, version: str,
                   fusable: bool = False) -> Callable[[StageFn], StageFn]:
    """
    Mirrors agent/tools/base.py::register_tool — a decorator, not a hand-maintained dict,
    for exactly the reason given there: a stage that is written but not registered fails
    silently. Duplicate ids raise at import time.
    """
```

Ayushman's stage is therefore, in full:

```python
@register_stage("impulse_denoise", order=20, version="switching_median@1")
def impulse_denoise(arr, valid_mask, assessment, params):
    ...
    return out, StageReceipt(
        stage_id="impulse_denoise", stage_version="switching_median@1",
        status=StageStatus.APPLIED, order=20,
        params={"window": 3, "dev_dn": 40, "max_similar_neighbours": 2},
        triggered_by=["impulse_density"],
        threshold_basis=ThresholdBasis.PROVISIONAL,
        pixels_total=int(valid_mask.sum()), pixels_modified=n_changed,
        fraction_modified=n_changed / max(int(valid_mask.sum()), 1),
        max_abs_delta_dn=float(delta.max()), mean_abs_delta_dn=float(delta.mean()),
        duration_ms=elapsed_ms)
```

He needs nothing from any other module: `arr`, `valid_mask`, the measured
`assessment.metric("impulse_density")` and `params` are everything. If his stage cannot run —
window larger than the raster, unsupported dtype, video frame unreadable — it returns the input
array **unchanged** together with `status=NOT_CONFIGURED` or `FAILED` **and a reason**. It must
never return the input array with `status=APPLIED`; the `_honesty` validator in §2.6 plus the
receipt-level check in §2.8 make that combination unrepresentable.

### 2.10 Where the receipt lives

`[PROPOSAL]` `state.evidence.metadata["restoration"] = receipt.model_dump(mode="json")`.

This needs **no change to `schemas/responses.py`**: `EvidencePackage.metadata` is a free
`Dict[str, Any]` (`schemas/evidence.py:55-59`) and is already used this way for
`state.evidence.metadata["aoi"]` (`agent/tools/raster.py`) and
`state.evidence.metadata["change_adjudication"]` (`agent/tools/inference.py:346`). The response
path is `AnalyzeResponse.evidence.metadata.restoration`.

A typed `restoration: Optional[RestorationReceipt]` field on `AgentState` is nicer and should be
added later, but `AgentState` is under concurrent edit and the dict route ships without touching
it.

### 2.11 Worked JSON example

A single 4096×4096 uint8 RGB upload with real salt-and-pepper, one fused photometric pass, and
super-resolution recommended but out of scope. Every number here is **illustrative, not
measured**.

```json
{
  "schema_version": "restoration-receipt@1",
  "receipt_id": "rst_9f2c1a7b",
  "job_id": "req_2026_09_21_0007",
  "status": "PARTIAL",
  "input_modified": true,
  "assessments": [
    {
      "assessment_id": "qa_req_2026_09_21_0007_0",
      "source_kind": "RASTER",
      "image_index": 0,
      "image_path": "/data/jobs/req_2026_09_21_0007/input/scene.tif",
      "width": 4096, "height": 4096, "bands": 3, "dtype": "uint8",
      "dn_max": 255.0, "nodata": null,
      "valid_pixel_count": 16777216, "total_pixel_count": 16777216,
      "metrics": [
        {
          "name": "impulse_density", "kind": "IMPULSE_NOISE", "status": "MEASURED",
          "value": 0.0181, "unit": "fraction",
          "per_band": {"0": 0.0181, "1": 0.0176, "2": 0.0179},
          "reduction": "max_over_bands",
          "threshold": 0.001, "threshold_basis": "PROVISIONAL",
          "exceeds_threshold": true, "gate_eligible": true,
          "sample_fraction": 1.0, "detector_version": "impulse@1",
          "reason": null, "notes": "8-neighbour isolation test, dev_dn=40"
        },
        {
          "name": "saturation_high", "kind": "SATURATION_CLIPPING", "status": "MEASURED",
          "value": 0.0092, "unit": "fraction",
          "per_band": {"0": 0.0092, "1": 0.0088, "2": 0.0090},
          "reduction": "max_over_bands",
          "threshold": 0.02, "threshold_basis": "PRINCIPLED",
          "exceeds_threshold": false, "gate_eligible": true,
          "sample_fraction": 1.0, "detector_version": "saturation@1"
        },
        {
          "name": "dynamic_range_p2_p98", "kind": "LOW_DYNAMIC_RANGE", "status": "MEASURED",
          "value": 0.21, "unit": "dimensionless",
          "per_band": {"0": 0.21, "1": 0.24, "2": 0.23},
          "reduction": "min_over_bands",
          "threshold": 0.30, "threshold_basis": "PROVISIONAL",
          "exceeds_threshold": true, "gate_eligible": true,
          "sample_fraction": 1.0, "detector_version": "dynrange@1"
        },
        {
          "name": "blur_laplacian_variance", "kind": "BLUR", "status": "MEASURED",
          "value": 0.00041, "unit": "dimensionless",
          "per_band": {}, "reduction": "luminance",
          "threshold": null, "threshold_basis": "NOT_CALIBRATED",
          "exceeds_threshold": null, "gate_eligible": false,
          "sample_fraction": 1.0, "detector_version": "blur@1",
          "notes": "advisory only: scene-content dependent, no calibration on our imagery"
        },
        {
          "name": "stripe_score", "kind": "STRIPING", "status": "NOT_CONFIGURED",
          "value": null, "unit": "dimensionless",
          "threshold": null, "threshold_basis": "NOT_CALIBRATED",
          "exceeds_threshold": null, "gate_eligible": false,
          "sample_fraction": 0.0, "detector_version": "stripe@0",
          "reason": "Destriping detector is not implemented; striping is neither measured nor corrected."
        },
        {
          "name": "gsd_m", "kind": "LOW_RESOLUTION", "status": "MEASURED",
          "value": 10.0, "unit": "m",
          "threshold": null, "threshold_basis": "PRINCIPLED",
          "exceeds_threshold": null, "gate_eligible": false,
          "sample_fraction": 1.0, "detector_version": "gsd@1",
          "notes": "read from RasterMetadata.resolution; not estimated"
        }
      ],
      "verdict": "DEGRADED",
      "degradations_detected": ["IMPULSE_NOISE", "LOW_DYNAMIC_RANGE"],
      "advisories": [
        "blur_laplacian_variance is low but its threshold is NOT_CALIBRATED; no deblur was run."
      ],
      "detector_config_hash": "3f1c9ab27d5e4081",
      "duration_ms": 612.4,
      "warnings": []
    }
  ],
  "plans": [
    {
      "plan_id": "rp_req_2026_09_21_0007_0",
      "image_index": 0,
      "stages": [
        {"stage_id": "impulse_denoise", "order": 20,
         "params": {"window": 3, "dev_dn": 40, "max_similar_neighbours": 2},
         "triggered_by": ["impulse_density"], "threshold_basis": "PROVISIONAL",
         "fused": false},
        {"stage_id": "photometric_correct", "order": 50,
         "params": {"black_level": true, "grey_world_gain": true,
                    "percentile_stretch": [2.0, 98.0], "gamma": 1.0},
         "triggered_by": ["dynamic_range_p2_p98"], "threshold_basis": "PROVISIONAL",
         "fused": true},
        {"stage_id": "super_resolve", "order": 90, "params": {},
         "triggered_by": ["gsd_m"], "threshold_basis": "NOT_CALIBRATED", "fused": false}
      ],
      "is_noop": false,
      "rationale": "impulse_density 0.0181 >= 0.001 (PROVISIONAL) -> switching median; p2-p98 range 0.21 < 0.30 (PROVISIONAL) -> fused photometric pass; super-resolution recommended but NOT_CONFIGURED.",
      "decision_table_version": "dt@1"
    }
  ],
  "stages": [
    {
      "stage_id": "impulse_denoise", "stage_version": "switching_median@1",
      "status": "APPLIED", "reason": null, "order": 20,
      "params": {"window": 3, "dev_dn": 40, "max_similar_neighbours": 2},
      "triggered_by": ["impulse_density"], "threshold_basis": "PROVISIONAL", "fused": false,
      "pixels_total": 16777216, "pixels_modified": 302841,
      "fraction_modified": 0.01805, "max_abs_delta_dn": 255.0, "mean_abs_delta_dn": 171.3,
      "frames_total": null, "frames_modified": null,
      "is_geometric": false,
      "input_sha256": "a1b2...", "output_sha256": "c3d4...",
      "duration_ms": 2841.7, "warnings": []
    },
    {
      "stage_id": "photometric_correct", "stage_version": "fused_matrix_lut@1",
      "status": "APPLIED", "reason": null, "order": 50,
      "params": {"matrix": [[1.04, 0, 0], [0, 1.0, 0], [0, 0, 0.97]],
                 "lut_entries": 256, "black_level_dn": [6, 5, 7],
                 "percentile_stretch": [2.0, 98.0], "gamma": 1.0,
                 "fitted_on_sample_fraction": 1.0, "transfer": "lut"},
      "triggered_by": ["dynamic_range_p2_p98"], "threshold_basis": "PROVISIONAL",
      "fused": true,
      "pixels_total": 16777216, "pixels_modified": 16590112,
      "fraction_modified": 0.98885, "max_abs_delta_dn": 58.0, "mean_abs_delta_dn": 19.6,
      "is_geometric": false,
      "input_sha256": "c3d4...", "output_sha256": "e5f6...",
      "duration_ms": 934.2, "warnings": []
    },
    {
      "stage_id": "super_resolve", "stage_version": "none@0",
      "status": "NOT_CONFIGURED",
      "reason": "Learned super-resolution is disabled on this deployment: no Real-ESRGAN or SwinIR checkpoint has been verified with scripts/verify_checkpoints.py and no held-out score has been measured (project/split-ushnik-ayushman.md, Ayushman #4). The image was NOT upscaled.",
      "order": 90, "params": {}, "triggered_by": ["gsd_m"],
      "threshold_basis": "NOT_CALIBRATED", "fused": false,
      "is_geometric": false, "duration_ms": 0.0,
      "warnings": ["super_resolve NOT_CONFIGURED; resolution was not changed."]
    }
  ],
  "inputs": [
    {
      "image_index": 0,
      "original_path": "/data/jobs/req_2026_09_21_0007/input/scene.tif",
      "consumed_path": "/data/jobs/req_2026_09_21_0007/restored/scene.restored.tif",
      "was_modified": true,
      "original_sha256": "a1b2...", "consumed_sha256": "e5f6...",
      "georeferencing_preserved": true
    }
  ],
  "stages_planned": 3, "stages_applied": 2, "stages_skipped": 0,
  "stages_not_configured": 1, "stages_failed": 0,
  "residual_degradations": [],
  "unmeasured_degradations": ["STRIPING", "BLUR", "GAUSSIAN_NOISE"],
  "out_of_measured_range": [
    "gsd 10.0 m: the trained segmenters were trained at 0.5 m (docs/models/trained_segmenters.md)."
  ],
  "provisional_gates_fired": ["impulse_density", "dynamic_range_p2_p98"],
  "geometry_preserved": true,
  "confidence_advice": {
    "posture": "CAUTION",
    "max_confidence_multiplier": 1.0,
    "blocking": false,
    "reasons": [
      "The image was modified before the model saw it: 2 stages changed 98.9% of pixels (max delta 255 DN).",
      "impulse_density and dynamic_range_p2_p98 fired on PROVISIONAL, uncalibrated thresholds.",
      "STRIPING, BLUR and GAUSSIAN_NOISE were not measured on this input.",
      "Input GSD 10.0 m is outside the segmenters' measured 0.5 m range."
    ]
  },
  "config_version": "restoration@1",
  "detector_config_hash": "3f1c9ab27d5e4081",
  "decision_table_version": "dt@1",
  "total_duration_ms": 4388.3,
  "warnings": [
    "Input image was corrected before analysis: impulse_denoise, photometric_correct.",
    "super_resolve NOT_CONFIGURED; resolution was not changed."
  ]
}
```

Note `max_confidence_multiplier: 1.0` with `posture: CAUTION`. **Advice is not automatically a
penalty.** There is no measured basis for a numeric penalty, so v1 emits 1.0 and lets the
critique agent — which sees the model score and the verifier verdict too — decide. Inventing a
multiplier here would be inventing a number.

---

## 3. Quality detectors **[PROPOSAL, except the impulse gate's existence]**

All detectors run on `(bands, height, width)` in native DN, restricted to `valid_mask`. A
detector that cannot run returns a `QualityMetric` with `status=NOT_CONFIGURED`/`FAILED`,
`value=None` and a reason. **It never returns 0.0 as a stand-in** — a fabricated zero would read
as "measured clean", which is the exact failure `rules.md` §1.1 forbids.

### 3.1 `impulse_density` — the one Ayushman's stage is gated on

`[RECORDED]` that the gate is "measured impulse density". `[PROPOSAL]` for everything about how.

For each band independently, on valid pixels only:

1. `med` = the 3×3 median of the band (`scipy.ndimage.median_filter`, `mode="nearest"`, invalid
   pixels filled with the band median before filtering so nodata does not leak).
2. `dev = |x - med|`, in DN.
3. `extreme = (x <= extreme_tol_dn) | (x >= dn_max - extreme_tol_dn)`, default
   `extreme_tol_dn = 2` for uint8, scaled by `dn_max/255` otherwise.
4. `isolated` = at most `max_similar_neighbours` of the 8 neighbours are within `dev_dn` of `x`.
5. A pixel is an **impulse candidate** iff `dev >= dev_dn` **and** `isolated` **and**
   (`extreme` **or** `dev >= 2 * dev_dn`).
6. `impulse_density[band] = candidates / valid_pixels` — a **fraction in [0, 1]**.
7. The reported `value` is `max` over bands: one corrupt band is enough to justify the median,
   and a per-band breakdown is kept in `per_band`.

Why each clause exists — this is what makes it defensible rather than a magic formula:

- Clause 3 (`extreme`) is what makes it *salt and pepper* rather than generic outliers. Classical
  salt-and-pepper corruption pins pixels at the extremes of the representable range.
- Clause 4 (`isolated`) is the false-positive guard that matters most for **our** imagery: a
  one-pixel-wide bright road, a car roof, a thin river or a field boundary is a legitimate
  high-deviation pixel with *similar neighbours along the structure*. Without clause 4 the
  detector would report high impulse density on clean DeepGlobe road tiles and the median would
  be applied to imagery it can only damage. The regression test in §9 asserts exactly this.
- Clause 5's `dev >= 2 * dev_dn` alternative catches impulses that landed short of the extremes
  (e.g. after an earlier stretch) without letting ordinary texture in.

**Gate.** `impulse_density >= impulse_gate` fires `impulse_denoise`.
`impulse_gate = 0.001` (0.1% of valid pixels) — **ASSUMPTION, not measured**, and its
`threshold_basis` is `PROVISIONAL` for exactly that reason. What the gate *means*: below it, the
expected number of corrupted pixels is small enough that the median's own damage to thin
structures is the larger risk; above it, the corruption is the larger risk. **That trade-off
point has not been measured on our imagery.** §9 specifies the experiment that settles it, and
until it runs, every receipt the gate fires carries `threshold_basis: PROVISIONAL` and the metric
name appears in `provisional_gates_fired`.

`dev_dn = 40` (of 255) and `max_similar_neighbours = 2` are likewise **ASSUMPTION**. All three
live in `configs/app.yaml` under `restoration:`, never in code (`rules.md` §3).

### 3.2 The full detector set

| Metric | Definition | Unit | Gate | Basis |
|---|---|---|---|---|
| `impulse_density` | §3.1 | fraction | `>= 0.001` | PROVISIONAL |
| `nodata_fraction` | pixels equal to `RasterMetadata.nodata` or non-finite | fraction | `>= 0.0` reported; `>= 0.5` warns | PRINCIPLED |
| `saturation_high` | valid pixels `>= dn_max` | fraction | `>= 0.02` | PRINCIPLED |
| `saturation_low` | valid pixels `<= 0` | fraction | `>= 0.02` | PRINCIPLED |
| `dynamic_range_p2_p98` | `(p98 - p2) / dn_max`, min over bands | dimensionless | `< 0.30` | PROVISIONAL |
| `black_level_dn` | per-band p0.5 | dn | no gate; a **parameter** for §5 | PRINCIPLED |
| `grey_world_gain` | per-band gain equalising band means to the mean of band means | dimensionless | `max/min > 1.15` | PROVISIONAL |
| `gaussian_noise_sigma_dn` | `1.4826 × MAD` of the high-pass residual `x - med3x3`, after impulse candidates are excluded | dn | `>= 0.04 × dn_max` | PROVISIONAL |
| `blur_laplacian_variance` | `var(Laplacian3x3(luma)) / dn_max²` | dimensionless | **none** | NOT_CALIBRATED |
| `stripe_score` | `var(column means) / var(all pixels)`, and the row equivalent | dimensionless | **none** | NOT_CALIBRATED |
| `gsd_m` | `RasterMetadata.resolution[0]`, read not estimated | m | **none** | PRINCIPLED |

### 3.3 Which thresholds are honest, stated plainly

- **Principled without calibration:** `saturation_high`, `saturation_low`, `nodata_fraction`,
  `black_level_dn`, `gsd_m`. Each is either definitional (a pixel at `dn_max` *is* clipped;
  a pixel equal to nodata *is* missing) or read straight from metadata. No dataset is needed to
  justify the threshold; only the 0.02 saturation figure is a policy choice about when it is
  worth telling the user, and it is an **ASSUMPTION**.
- **Plausible but uncalibrated on our imagery (PROVISIONAL):** `impulse_density`,
  `dynamic_range_p2_p98`, `grey_world_gain`, `gaussian_noise_sigma_dn`. They are allowed to gate
  because doing nothing is not obviously safer than acting, but every receipt they fire says
  PROVISIONAL and names them in `provisional_gates_fired`. They are **NOT MEASURED**.
- **Cannot gate anything (NOT_CALIBRATED):** `blur_laplacian_variance`, `stripe_score`. Laplacian
  variance is dominated by scene content — a calm-water or bare-desert tile is genuinely
  low-variance and sharp, an urban tile is high-variance and may be blurred. There is no
  threshold that separates blur from content without a labelled set, and we have none. Striping
  is the same problem plus a sensor-specific period. Both are **measured and reported as
  advisories**, and the planner refuses to build a stage from them. A `NOT_CALIBRATED` metric
  appearing in `advisories` with no corresponding stage is the design working, not a gap.

### 3.4 The gating rule

**A metric may only gate a stage when `threshold_basis` is `PRINCIPLED` or `PROVISIONAL`.** The
planner asserts this and raises `WorkflowError` if a decision-table row references a
`NOT_CALIBRATED` metric — a loud import/plan-time failure, in the spirit of
`capability_registry._validate_all()`. This is the mechanism that stops the framework from
quietly growing a deblur stage fired by a number nobody trusts.

### 3.5 Cost

Detectors run on a **subsample** when the raster is large. `sample_fraction` in the metric
records what was examined: 1.0 for rasters under `full_scan_megapixels` (**ASSUMPTION: 16 MP**),
otherwise a regular grid of tiles totalling that budget, with `sample_fraction` set accordingly.
Percentiles and means are unbiased under grid sampling; `impulse_density` is estimated with a
sampling error that is **NOT MEASURED** and is noted in the metric's `notes`.

---

## 4. The planner **[PROPOSAL]**

`planner.plan(assessment: QualityAssessment) -> RestorationPlan`. Pure function of the
assessment and the config — no I/O, no array access. That is what makes §9's table test possible.

### 4.1 Order, and why it is not arbitrary

| Order | Stage | Fused? | v1 state |
|---|---|---|---|
| 10 | `mask_invalid` — build `valid_mask`, never write pixels | no | always runs |
| 20 | `impulse_denoise` — switching median | no | **Ayushman** |
| 30 | `gaussian_denoise` | no | `NOT_CONFIGURED` |
| 40 | `destripe` | no | `NOT_CONFIGURED` |
| 50 | `photometric_correct` — the fused matrix + LUT pass (§5) | **yes** | Ushnik |
| 90 | `super_resolve` | no | `NOT_CONFIGURED` (out of scope, §1.2) |

The order is forced by three facts, not by taste:

1. **`mask_invalid` first.** Every later stage must know which pixels are real. A median that
   averages nodata into a valid neighbourhood, or a percentile fitted over nodata, fabricates
   data.
2. **`impulse_denoise` before `photometric_correct`.** This is the important one. The fused pass
   is *fitted* on percentiles (`p2`, `p98`, `p0.5`) and band means. Salt-and-pepper pixels sit at
   the extremes of the histogram, so they are exactly what `p0.5` and `p98` latch onto. Fitting
   the stretch on corrupted statistics produces a wrong stretch for the whole raster — a global
   error caused by a local defect. Removing impulses first costs one extra pass and makes the
   fitted transfer function correct. The reverse order is cheap and wrong.
3. **`super_resolve` last.** Upscaling amplifies whatever noise survives, so it must see the
   cleanest input. It never runs in v1, but the ordering is fixed now so that enabling it later
   is a config change and not a redesign.

`gaussian_denoise` after `impulse_denoise` follows the same logic one level down: a linear
smoother spreads an impulse over its whole kernel instead of removing it.

### 4.2 Decision table — version `dt@1`

Read top to bottom; every matching row contributes a stage; stages execute in `order`.

| # | Condition (all on one assessment) | Stage | Order | Params derived from | Basis |
|---|---|---|---|---|---|
| 1 | always | `mask_invalid` | 10 | `nodata`, non-finite | PRINCIPLED |
| 2 | `impulse_density >= impulse_gate` (0.001) | `impulse_denoise` | 20 | `dev_dn`, `max_similar_neighbours`, `window=3` | PROVISIONAL |
| 3 | `gaussian_noise_sigma_dn >= 0.04 × dn_max` | `gaussian_denoise` | 30 | — | PROVISIONAL → emits `NOT_CONFIGURED` |
| 4 | `stripe_score` advisory only | — | — | — | NOT_CALIBRATED → **no stage**, advisory |
| 5 | `black_level_dn > 0` on any band | `photometric_correct` (offset term) | 50 | `black_level_dn` | PRINCIPLED |
| 6 | `dynamic_range_p2_p98 < 0.30` | `photometric_correct` (stretch term) | 50 | `p2`, `p98` per band | PROVISIONAL |
| 7 | `grey_world_gain` max/min `> 1.15` | `photometric_correct` (gain term) | 50 | per-band gains | PROVISIONAL |
| 8 | `saturation_high >= 0.02` or `saturation_low >= 0.02` | **no stage** | — | — | PRINCIPLED → warning + `residual_degradations` |
| 9 | `blur_laplacian_variance` advisory only | — | — | — | NOT_CALIBRATED → **no stage**, advisory |
| 10 | `gsd_m > sr_recommend_gsd_m` (ASSUMPTION: 2.0) | `super_resolve` | 90 | — | NOT_CALIBRATED → emits `NOT_CONFIGURED` |
| 11 | `nodata_fraction >= 0.5` | **no stage** | — | — | PRINCIPLED → warning, and `UNASSESSABLE` if `>= 0.95` |

Rows 5–7 all collapse into the **one** stage at order 50, which is what "fused" means (§5). Rows
4, 8, 9 and 11 deliberately produce **no stage**: they are conditions we can measure and cannot
fix, and the honest response is to say so in the receipt rather than to run something that looks
like a fix. Saturation in particular is **irreversible** — clipped pixels have lost their value
and no correction recovers it, so row 8 records `SATURATION_CLIPPING` in
`residual_degradations` where the critique agent will see it.

### 4.3 Doing nothing

If no row other than #1 contributes a stage, the plan is `is_noop=True` with a rationale naming
the metrics that were checked. Then:

- `restore_input` performs **no read, no write, no copy**. `state.image_paths` is untouched.
- The receipt exists with `status=ASSESSED_NO_ACTION`, `input_modified=False`, every
  `QualityAssessment` intact, `stages=[]` and `inputs[*].was_modified=False`.
- A trace step is still added: `"Quality assessed: CLEAN"` with the measured values.

**Skipped is not the same as absent.** A clean image still produces a full receipt; that is what
makes "the image was not modified" a claim backed by measurements rather than by silence.

### 4.4 Pairs and video

- **Temporal pairs.** One `QualityAssessment` and one `RestorationPlan` per image, but with one
  extra rule: `photometric_correct` on a temporal pair **must** be fitted jointly over both
  dates, never independently — stretching each date on its own manufactures radiometric change,
  which is precisely the bug `geo/optical_preprocessing.py:95-128` (`joint_rgb8_pair`) already
  exists to avoid. The planner therefore emits one shared `photometric_correct` whose params are
  fitted on the pooled histogram, with `triggered_by` listing both assessments' metric names, and
  the same `StageReceipt` referenced from both inputs. `impulse_denoise` is per-image; it is
  local and carries no cross-date bias.
- **Video.** `[RECORDED]` that salt-and-pepper covers video. Video does not run through the agent
  DAG at all (`capability_registry._validate_all()` docstring: `video_*` runs via
  `/api/video/analyze` → `VideoAnalysisWorkflow`), so the video hook lives in
  `workflows/video_analysis.py`, applied per **sampled** frame from `VideoSampler`, not to the
  whole clip. One `QualityAssessment` per assessed frame, with `source_kind=VIDEO_FRAME` and
  `frame_index`/`timestamp_sec` set; the plan is decided **once** from the first
  `video_assess_frames` (ASSUMPTION: 5) assessed frames and then held fixed for the clip, so the
  correction cannot flicker between frames. `StageReceipt.frames_total` /
  `frames_modified` carry the per-clip totals. Open question §10.6 covers whether per-frame
  assessments are kept in the response or summarised.

---

## 5. The fused single-pass matrix/LUT correction **[RECORDED that it is fused; PROPOSAL for how]**

### 5.1 What "fused" means

Not "fast". It means: **the output is computed in one pass over the pixels, from one 3×3 matrix
and one lookup table, instead of one pass per correction.**

A correction can be fused iff it is (a) **pointwise** — the output at a pixel depends only on
that pixel's own values — and (b) **spatially invariant** — the same function applies everywhere.
Given both, an arbitrary chain of such corrections is still a pointwise function, and a
pointwise function on a bounded integer domain **is** a lookup table.

Concretely, for each band `b` the chain

```
x  ->  x - black_level[b]            (offset, from p0.5)
   ->  x * gain[b]                   (grey-world white balance)
   ->  (x - p2[b]) / (p98[b] - p2[b]) * dn_max     (percentile stretch, affine)
   ->  clip(x, 0, dn_max) ** (1/gamma) rescaled    (gamma)
   ->  clip and quantise to the native dtype
```

is a single scalar function `f_b: DN -> DN`. Building it costs `dn_max + 1` evaluations of `f_b`
— **256 for uint8**, one per possible input value — after which applying it to a
100-megapixel band is one `numpy.take`. Cross-band corrections (grey-world expressed as a
diagonal 3×3, or any 3×3 colour matrix) compose by matrix multiplication into a single `M`.

So the whole of order 50 is:

```
out = quantise( LUT[ clip( M @ in ) ] )      # one matmul + one table lookup per pixel
```

executed tile-by-tile with `geo/tiling.py::RasterTiler`, because `M` and `LUT` are global
constants once fitted. Fitting happens in a **separate statistics pass** (or on the §3.5
subsample), so the full cost is: one statistics pass (possibly sampled) + one write pass. The
receipt records `transfer: "lut"`, `lut_entries`, the matrix and every fitted parameter, so the
transform is reproducible from the receipt alone.

### 5.2 What cannot be fused, and what happens to it

| Correction | Why it cannot fuse | Where it goes |
|---|---|---|
| Switching median (`impulse_denoise`) | spatial support: output depends on 8 neighbours | its own pass, order 20 |
| Gaussian / bilateral denoise | spatial support | own pass, order 30 |
| Destriping | spatially varying by column/row — not invariant | own pass, order 40 |
| CLAHE / local contrast | spatially varying transfer function | not in scope at all |
| Super-resolution | changes geometry and is learned | own pass, order 90, `NOT_CONFIGURED` |

Anything in this table gets its **own** `StageReceipt`, its own pass and its own `duration_ms`.
Pretending otherwise would be the one real dishonesty available in a performance section.

There is also a **float-raster** exception. For `float32`/`float64` inputs the DN domain is not
finite, so no table exists. The correction then applies `M` and evaluates `f_b` **analytically**
per pixel, and the receipt records `transfer: "analytic"`, `lut_entries: 0`. For `uint16` the
table is 65,536 entries — still trivial to build, and the LUT path is kept
(open question §10.8 asks whether that holds up on a real Sentinel-2 scene; it is **NOT
MEASURED**).

### 5.3 Why this matters for large rasters

A naive chain materialises one float32 intermediate per correction. For a 10,000 × 10,000 × 3
raster, one float32 copy is `10000 × 10000 × 3 × 4 = 1,200,000,000 bytes ≈ 1.12 GiB`
(**ARITHMETIC** from the shape, not a measurement). Five chained corrections is five of those
allocations; the uint8 source itself is 286 MiB. The fused form allocates the output tile and
nothing else.

This is not hypothetical on this project. The repository already carries two recorded
consequences of memory pressure on the same 8 GB GPU: ChangeFormer at native 1024 OOMs when
other models are resident (`project/plan-2026-09-14-agent-parity-geo.md`, ground-truth table),
and a run that silently fell back to 512-px windows after GPU OOM produced **wrong AOI numbers**
that had to be corrected in `qna.md` Q-014. Restoration runs on CPU and before the model loads,
so it competes for host RAM at the worst possible moment — right before a model wants to
allocate. A correction stage that triples peak host RAM would be a new source of exactly that
class of bug.

### 5.4 Exactness

The fused result must equal the naive chained result within **1 DN** for integer dtypes — that
is the §9 equivalence test, and it is the argument that fusion is an optimisation rather than a
change of behaviour. The 1 DN allowance is quantisation, not slack: the naive chain quantises at
each step and the LUT quantises once, so the LUT is in fact the *more* accurate of the two.

---

## 6. The `assess_quality` and `restore_input` DAG nodes **[PROPOSAL]**

### 6.1 Registration — five edits, none of them optional

`rules.md` §3 is explicit that a tool must be registered, referenced by a DAG node, listed in
the capability's `required_tools`, **and** whitelisted, or it is invisible or dead. For these two
tools that means:

| File | Edit |
|---|---|
| `backend/app/agent/tools/restoration.py` (new) | `@register_tool("assess_quality")`, `@register_tool("restore_input")` |
| `backend/app/agent/tools/__init__.py` | side-effecting import of the new module |
| `backend/app/orchestration/dependency_graph.py` | the two nodes in each image branch |
| `backend/app/orchestration/capability_registry.py` | both names in `required_tools` |
| `backend/app/agent/validator.py` | both names in `PlanValidator.PERMITTED_TOOLS` |

`tests/unit/test_routing_unsupported.py` already asserts that every DAG tool is registered and
whitelisted, so a missed edit fails a test rather than producing D-104's silent-fallback bug.
**All five of these files are under concurrent edit by other agents as of 2026-09-21**; this
spec only specifies the edits.

### 6.2 Placement

For `single_image_grounding` (the other image branches take the same two inserts):

```
inspect_raster
   ├── assess_quality            (deps: inspect_raster, is_parallelizable=True, 20 s)
   └── validate_single_image     (deps: inspect_raster)
restore_input                    (deps: assess_quality, validate_single_image, 60 s)
run_grounding                    (deps: restore_input)
run_segmentation → generate_overlay → generate_report      (unchanged)
```

Three placement decisions, each with a reason:

1. **After `inspect_raster`,** because every detector needs `dtype`, `nodata`, `bands` and
   `resolution` from `RasterMetadata`.
2. **`validate_*` runs on the ORIGINAL input, in parallel with assessment.** Validation judges
   what the user actually uploaded; if restoration ran first, a scene that should have been
   rejected could be waved through by a correction, and the rejection message would describe an
   image the user never sent. Restoration must not be able to flatter validation.
3. **Every model node depends on `restore_input`,** so no model can accidentally read the
   original path after restoration decided to change it. `is_parallelizable=False` on
   `restore_input`: it rewrites shared state.

### 6.3 `assess_quality` — consumes and emits

- **Consumes:** `state.image_paths`, `state.metadata`, `settings.restoration`.
- **Emits:** a `RestorationReceipt` with `assessments` and `plans` filled, `stages=[]`,
  `status=ASSESSED_NO_ACTION`, written to `state.evidence.metadata["restoration"]`. One trace
  step per input: `"Quality assessed: CLEAN"` / `"Quality assessed: DEGRADED"` with the measured
  metric values in `details`.
- **Never writes pixels.** It is safe to run on every job; it is the cheap half.
- **On failure:** the receipt becomes `status=FAILED` with a reason, `input_modified=False`, a
  warning is appended, and **the pipeline continues on the original imagery**. `rules.md` §4:
  fail fast before execution, degrade gracefully during it. A broken detector must not take down
  a working grounding query.

### 6.4 `restore_input` — consumes and emits

- **Consumes:** the receipt's `plans`, the original rasters, `valid_mask`.
- **Emits:** for each non-noop plan, a restored raster under
  `artifact_manager.get_job_dir(request_id) / "restored" / f"{stem}.restored{suffix}"`; a
  `StageReceipt` per planned stage **including the ones that did not run**; `inputs[*]` with both
  paths and both sha256; and `state.image_paths` rewritten to the restored paths.
- **Trace:** one step per stage, `status="warning"` for `NOT_CONFIGURED`/`FAILED`,
  `details` naming `fraction_modified` and `max_abs_delta_dn`.
- **Georeferencing is a hard gate.** The writer must reproduce `crs`, `transform` and `nodata`
  verbatim. This project has a recorded history here: without `rasterio`, the `tifffile`
  fallback hard-codes `crs=None, transform=None`, and a real UTM-14N GeoTIFF read as
  `is_georeferenced=False` (`plan-2026-09-14-agent-parity-geo.md` ground-truth table, `qna.md`
  Q-011). So: **if the restored raster cannot be written with its georeferencing intact, the
  stage is not applied.** The receipt reports `status=NOT_CONFIGURED` with that reason,
  `georeferencing_preserved=False`, `was_modified=False`, and `state.image_paths` is left
  pointing at the original. Silently dropping a CRS would corrupt every downstream geo claim —
  AOI areas, GeoJSON, `geo_bounds` on every box — which is a far worse outcome than an
  uncorrected image.
- **When restoration is skipped** (`is_noop`, feature disabled, assessment failed): the node
  still runs, still emits its trace step, writes nothing, changes nothing, and leaves the
  receipt's `input_modified=False`. It is never removed from the plan — a missing node is
  indistinguishable from a node that did nothing, and the whole point of the receipt is that the
  difference is visible.

### 6.5 Cache interaction — a required change

`orchestration_cache.compute_cache_key` hashes `image_paths`, query, capability and parameters
(`agent/controller.py`, step 5), and is computed **before** tools run, i.e. on the originals.
Two jobs on the same upload under different restoration settings would therefore collide and the
second would be served the first's answer. **`detector_config_hash` and
`decision_table_version` must be added to the cache key** (`orchestration/cache.py`). §9 has the
test; §10.4 records it as a decision to confirm.

---

## 7. Interaction with the confidence critique agent **[RECORDED constraint, PROPOSAL mechanism]**

`[RECORDED]` (`split-ushnik-ayushman.md:87-88`): the critique agent is rule-based, consumes model
scores, the verifier's verdict and the restoration receipt, and **can only hold or lower**
confidence.

### 7.1 What the receipt must expose, and why each field is needed

| Field | Why the critique agent cannot work without it |
|---|---|
| `input_modified: bool` | The single question "did the model see the user's image?" must be answerable without parsing anything. |
| `stages[*].status` + `reason` | Distinguishes "clean, nothing to do" from "dirty and we could not fix it" — opposite implications for confidence. |
| `stages[*].fraction_modified`, `max_abs_delta_dn` | Magnitude. A stage that changed 0.02% of pixels by 3 DN is not the same event as one that changed 98% by 255 DN. |
| `residual_degradations` | Degradations measured **above threshold and not corrected** (clipping, striping) — the strongest reason to lower confidence. |
| `unmeasured_degradations` | Degradations with **no configured detector**. Absence of evidence, not evidence of absence; it justifies caution, not a penalty. |
| `provisional_gates_fired` | Says the correction was triggered by an uncalibrated threshold, so the correction itself is a source of doubt. |
| `out_of_measured_range` | e.g. a 10 m GSD input to segmenters measured only at 0.5 m (`docs/models/trained_segmenters.md`). |
| `geometry_preserved` | If False, boxes and masks no longer align with the original raster and every spatial claim is void. Always True in v1, and asserted. |
| `confidence_advice.max_confidence_multiplier` (`le=1.0`) | The arithmetic hook. Bounded at 1.0 by the schema, so the type system enforces "hold or lower". |
| `confidence_advice.blocking` | The only way to reach `confidence=None`, matching `AdjudicationResult.confidence=None` on conflict. |
| `confidence_advice.reasons` | Human strings the critique agent can put straight into the trace and the answer. |

### 7.2 The rule the critique agent applies

```
final = model_confidence * receipt.confidence_advice.max_confidence_multiplier
final = None  if receipt.confidence_advice.blocking
```

Monotonicity is structural, not a convention someone has to remember: the receipt has **no**
field capable of raising a score, and `max_confidence_multiplier` is `ge=0.0, le=1.0`. A future
contributor who wants restoration to *increase* confidence has to change the schema, which is
visible in review.

### 7.3 v1 policy for `ConfidenceAdvice` — and why it does not invent a penalty

| Receipt condition | posture | multiplier | blocking |
|---|---|---|---|
| `status=ASSESSED_NO_ACTION`, nothing residual | NEUTRAL | 1.0 | false |
| `input_modified=True` | CAUTION | **1.0** | false |
| any `provisional_gates_fired` | CAUTION | **1.0** | false |
| `residual_degradations` non-empty | CAUTION | **1.0** | false |
| `verdict=UNASSESSABLE`, or `nodata_fraction >= 0.95` | DEGRADED | 1.0 | **true** |
| `geometry_preserved=False` | DEGRADED | 1.0 | **true** |

Every non-blocking multiplier is **1.0 in v1**. That is deliberate. There is no measurement
linking "the image was stretched" to "the model is N% less reliable", and putting 0.8 in this
table would be inventing a number (`rules.md` §1.1). What v1 delivers is a truthful, structured
**reason** and a `posture`; the critique agent — which also sees the model score and the
verifier's verdict — decides what to do with it, and its own thresholds get their own
calibration and their own `qna.md` entry. The two blocking rows are different in kind: they are
not penalties but statements that no confidence is computable at all.

---

## 8. Honesty requirements and how the design enforces them **[PROPOSAL]**

The project rule is that nothing fabricates output. Five mechanisms, in order of how hard they
are to bypass:

1. **Unrepresentable lies.** The `model_validator`s in §2.3, §2.6 and §2.8 make the dishonest
   states raise at construction: a metric with a value it did not measure, a non-`APPLIED` stage
   without a reason, an `APPLIED` stage that does not report how much it changed, a geometric
   stage, and `input_modified` disagreeing with the stage list. A stage author cannot return the
   input unchanged and call it `APPLIED`.
2. **`NOT_CONFIGURED`, never silence.** Following `ml/adapters/fusion/adapter.py:72` — which
   returns a `ModelResult` with `status="NOT_CONFIGURED"`, a full prose `reason`,
   `confidence=None` and a warning rather than a prediction — every stage that cannot run emits a
   `StageReceipt` with `status=NOT_CONFIGURED`, a reason naming **what** is missing and **what to
   do**, and a warning. `super_resolve` is the worked example: it appears in the plan, it appears
   in the receipt, it says the image was **not** upscaled, and it names the verification step that
   would enable it. A silently absent stage would be indistinguishable from a stage that ran.

   **This now has a stronger precedent than when the brainstorm happened.** As of 2026-09-21
   `ModelResult` *enforces* the refusal contract rather than documenting it:
   `REFUSAL_STATUSES = frozenset({"NOT_CONFIGURED"})` (`backend/app/schemas/models.py:61`), the
   `is_refusal` / `refusal_reason` properties, and `_enforce_refusal_carries_no_result`
   (`models.py:88`) which raises if a refusal also carries boxes, masks, logits or a confidence,
   and which rewrites `answer` and `warnings` so the status cannot be lost downstream. Refusals
   also surface as a top-level `AnalyzeResponse.model_refusals` list
   (`backend/app/schemas/responses.py:75`). `StageReceipt` is deliberately the same shape of
   object one level down: a status enum whose non-`APPLIED` members *require* a reason, validators
   that make "refused but also did something" unconstructible, and a top-level
   `stages_not_configured` count a consumer cannot miss. If a future change adds a
   `restoration_refusals`-style top-level field alongside `model_refusals`, the receipt already
   carries everything it would need.
3. **Visible modification.** When `input_modified=True`:
   - `state.warnings` gains `"Input image was corrected before analysis: <stage ids>."`;
   - `state.quality_status` becomes `REVIEW_REQUIRED` when any stage's `fraction_modified`
     exceeds `announce_fraction` (**ASSUMPTION: 0.001**), reusing the existing
     `quality_status`/`quality_flags` channel that already surfaces at
     `orchestration.quality_status` (`agent/controller.py:228-229`);
   - the answer text must state that the image was corrected before the model saw it. Precedent:
     the segmenter path runs at native resolution and "says so in the answer text"
     (`qna.md` Q-036 §, `docs/models/trained_segmenters.md`).
4. **Both versions kept, both hashed.** The original file is never overwritten; the restored
   raster is a new artefact under the job directory, and `RestoredInput` carries both paths and
   both sha256. Any claim in the receipt can be re-verified from disk afterwards. This is what
   makes the receipt evidence rather than an assertion.
5. **No fabricated zero.** A detector that fails reports `FAILED` with `value=None`. Zero would
   read as "measured clean" — the most dangerous available lie, because it is silent and
   plausible.

One more, in the same spirit: **restoration is not allowed to be the reason an answer exists.**
It changes pixel values; it never changes a `NOT_FOUND` into a detection by relaxing anything
downstream. No threshold, no `top_k`, no verifier setting is altered by restoration, and nothing
in the receipt is readable by the detector or verifier paths.

---

## 9. Test plan **[PROPOSAL]**

Layering follows `tests/conftest.py`: markers are applied automatically from the directory, so
`tests/unit/` needs no weights and `tests/models/` skips when a checkpoint or a tile is absent
(the established pattern is `pytest.skip(f"{adapter.name} checkpoint not available at
{adapter.checkpoint_path}")`, e.g. `tests/models/test_trained_adapters.py:30`).

**The gate to hold:** `pytest -m "not models" -q` → **430 passed, 3 failed**, the 3 being the
long-standing GDAL failures in `tests/unit/test_geotiff_georeferencing.py`
(`split-ushnik-ayushman.md`, working agreement). *Not run for this document — this is a spec, and
the instruction for this task was explicitly not to run pytest.*

### 9.1 `tests/unit/` — synthetic, no imagery needed

**`test_restoration_schemas.py`** — every validator fires. `MEASURED` without a value raises;
`FAILED` with a value raises; `FAILED` without a reason raises; a non-`APPLIED` stage without a
reason raises; `APPLIED` without `fraction_modified` raises; `is_geometric=True` raises;
`input_modified=True` with no modifying stage raises, and `False` with one raises;
`max_confidence_multiplier=1.01` raises. JSON round-trip is stable and the §2.11 document
validates.

**`test_restoration_detectors.py`** — impulse density on injected corruption at
0.000 / 0.001 / 0.010 / 0.050 recovers the injected fraction within ±15% relative (**TARGET**);
a constant image measures 0.0; **a synthetic 1-px-wide bright line on a dark field measures
< 0.0005** — the clause-4 false-positive guard, the test that stops us median-filtering road
tiles; nodata pixels are excluded from both numerator and denominator; a 1-band raster returns
`NOT_APPLICABLE` for colour metrics rather than a number; a detector raising internally yields
`FAILED` with `value=None`.

**`test_restoration_planner.py`** — every row of the §4.2 table: condition → the exact ordered
stage-id list. `NOT_CALIBRATED` metrics produce **no** stage and do produce an advisory. A
decision row referencing a `NOT_CALIBRATED` metric raises `WorkflowError`. The all-clean case is
`is_noop=True` with `stages == []`. Row 8 (saturation) puts `SATURATION_CLIPPING` into
`residual_degradations` and no stage. A temporal pair gets one shared `photometric_correct`
fitted jointly, not two.

**`test_restoration_fused.py`** — *equivalence:* fused `M`+LUT output equals the naive
step-by-step chain within 1 DN for `uint8` and `uint16`, over random arrays and over
`tests/data/sample_t1.png`. *Tiling:* tiled equals whole-image exactly. *Invariants:* dtype,
shape and band count preserved; nodata pixels bit-identical; a `float32` raster takes the
analytic branch and the receipt says `transfer: "analytic"`. *Receipt fidelity:* re-applying the
matrix and LUT recorded in `params` reproduces the output bit-exactly.

**`test_restoration_stage_registry.py`** — `register_stage` rejects duplicate ids at import; a
stage returning its input with `status=APPLIED` and `fraction_modified=0.0` is rejected at
receipt level via §2.8; every registered stage's `order` matches §4.1.

**`test_restoration_tools.py`** — with a fake `AgentState`: the noop path leaves
`state.image_paths` identical and still writes a receipt to
`state.evidence.metadata["restoration"]`; the applied path rewrites the paths and the restored
file exists; a detector exception leaves the pipeline running on the originals with
`status=FAILED` and a warning; `input_modified=True` appends the user-facing warning and sets
`quality_status=REVIEW_REQUIRED`; a write that loses the CRS results in `NOT_CONFIGURED` and
**unchanged** `image_paths`.

**`test_routing_unsupported.py`** (existing, extend) — `assess_quality` and `restore_input` are
registered, whitelisted, present in `required_tools`, and present in every image DAG branch.

**`test_restoration_cache_key.py`** — changing `detector_config_hash` changes
`compute_cache_key`. Without the §6.5 fix this test fails, which is the point of writing it.

### 9.2 `tests/models/` — needs real imagery and/or checkpoints, skips when absent

**`test_restoration_noop_identity.py`** — on a clean DeepGlobe / WHU tile the plan is a noop and
the routed segmenter's mask is **bit-identical** to a run without the restoration nodes.
Restoration must cost nothing on clean input. *Needs:* one tile plus the
`roads_segmenter` / `buildings_segmenter` checkpoint.

**`test_restoration_helps_downstream.py`** — the calibration experiment of §9.3(1): injected
impulse noise across a density sweep, IoU with and without `impulse_denoise`. *Needs:* ≥50
held-out tiles plus a checkpoint.

**`test_restoration_geotiff_preserved.py`** — a real georeferenced GeoTIFF survives restoration
with `crs`, `transform`, `bounds` and `nodata` unchanged and `is_georeferenced` still True; and
with `rasterio` absent, the stage refuses rather than dropping the CRS. *Needs:* a real UTM
GeoTIFF.

**`test_restoration_video_frames.py`** — per-frame assessment on a real clip; the plan is decided
once and then held; `frames_modified <= frames_total`. *Needs:* `real_aerial_footage.mp4`.

### 9.3 What genuinely needs real imagery, and what synthetic covers

**Synthetic is sufficient and preferable** for: detector arithmetic (the ground truth is the
injected corruption), fusion equivalence (algebra), the planner table (pure function), schema
validators, noop behaviour, and the false-positive guard.

**Real imagery is unavoidable** for the four claims synthetic cannot make:

1. **The impulse gate.** The sweep in `test_restoration_helps_downstream.py` is the experiment
   that turns `impulse_gate` from `PROVISIONAL` into `PRINCIPLED`: score a routed segmenter on
   ≥50 held-out tiles at injected densities {0, 0.0005, 0.001, 0.005, 0.01, 0.05}, with and
   without the median, and set the gate at the crossover where the median starts helping. Report
   the curve either way, including the region where it hurts. **Until that runs the gate stays
   PROVISIONAL and every receipt says so.**
2. **Whether the photometric stretch helps or hurts a trained segmenter**, whose training
   normalisation is the trainer's ImageNet mean/std over 0–255 RGB
   (`training/segmentation/datasets.py`). Changing radiometry changes what that normalisation
   sees. §10.5.
3. **Striping and blur thresholds**, which cannot be calibrated without labelled degraded real
   imagery. Until then both stay `NOT_CALIBRATED` and gate nothing.
4. **Georeferencing preservation**, which needs a real CRS-bearing GeoTIFF; the 3 known GDAL
   failures in `tests/unit/test_geotiff_georeferencing.py` are the standing baseline.

No new number enters `docs/` or a `qna.md` entry until it comes out of one of these runs.

---

## 10. Open questions

Each with who decides and what evidence settles it. None of these block §2, which is why §2 can
ship to Ayushman today.

**1 · What is `impulse_gate`?** 0.001 is an **ASSUMPTION**. *Decides:* Ushnik + Ayushman.
*Evidence:* the §9.3(1) sweep — IoU vs injected density, with and without the median, ≥50
held-out tiles, one routed segmenter. The crossover is the gate.

**2 · Do user-visible overlays and GeoJSON render on the original or the restored pixels?** My
proposal: the original, so the user sees their own imagery and the receipt reports the
difference. *Decides:* Ushnik (owns `evidence/`, `artifacts/`). *Evidence:* show both overlays
for one restored scene to someone who did not run it and ask which they would defend to a
reviewer.

**3 · Should `restore_input` rewrite `state.image_paths`, or should adapters receive an explicit
`restored_arr` in `context`?** Path-rewriting is simpler but couples restoration to the artifact
manager and to GeoTIFF writing. *Decides:* Ushnik. *Evidence:*
`grep -rn "state.image_paths" backend/app` — if any consumer depends on the original filename or
re-reads the original, rewriting is unsafe and the context route wins.

**4 · Must `detector_config_hash` enter `compute_cache_key`?** I claim yes (§6.5). *Decides:*
Ushnik. *Evidence:* `test_restoration_cache_key.py` — run the same query twice under two
restoration configs and show whether the second is wrongly served the first's answer.

**5 · Is a percentile stretch legitimate at all upstream of a segmenter** trained with the
trainer's ImageNet mean/std over 0–255 RGB? It may be undoing the very statistics the model
learned. *Decides:* Ayushman (owns `training/`). *Evidence:* the same held-out split scored with
and without the stretch, at native GSD, same threshold. If it does not help, drop rows 6–7 from
the decision table.

**6 · Video: a `QualityAssessment` per assessed frame in the response, or one aggregate plus a
per-frame summary?** *Decides:* Ushnik. *Evidence:* serialised response size for a 30 s clip at
the current `VideoSampler` rate. If the receipt dominates the payload, aggregate.

**7 · `STAGE_REGISTRY` decorator (my proposal, mirroring `register_tool`) versus a hard-coded
pipeline list in `planner.py`.** *Decides:* Ushnik. *Evidence:* whether Ayushman can add the
switching median **without editing `planner.py`**. If he cannot, the registry has failed its only
purpose.

**8 · For `uint16`, keep the 65,536-entry LUT or always take the analytic path?** *Decides:*
Ushnik. *Evidence:* wall-clock and peak RSS for both branches on one real Sentinel-2 `uint16`
scene. Currently **NOT MEASURED**.

**9 · Does the restoration receipt belong in the PDF report (`evidence/report.py`)?** An audit
report that omits "the image was modified" is incomplete. *Decides:* Ushnik. *Evidence:* read one
generated PDF for a restored job and check whether a reviewer could tell.

**10 · Should restoration be on by default, or opt-in per request via `parameters`?** Default-on
changes every existing answer's provenance; default-off means nobody ever sees it. My proposal:
assessment always on, correction default-on, with every stage gate-eligible only as in §3.4.
*Decides:* Ushnik. *Evidence:* the §9.2 noop-identity test — if restoration is provably free and
bit-identical on clean input, default-on is defensible.

---

## 11. Summary of what to build first

1. `restoration/schemas.py` exactly as §2 — **this unblocks Ayushman** and depends on nothing.
2. `restoration/stages.py` with `register_stage` and `STAGE_REGISTRY` only (no stages), so
   Ayushman has a registration point.
3. `restoration/detectors.py` with `impulse_density`, `saturation_*`, `nodata_fraction`,
   `dynamic_range_p2_p98`, `black_level_dn`, `gsd_m`, plus the `configs/app.yaml`
   `restoration:` block.
4. `restoration/planner.py` and the §4.2 table.
5. `restoration/correction.py` — the fused pass and `photometric_correct`.
6. `agent/tools/restoration.py` and the five registration edits of §6.1 — **last**, and only once
   the five files listed there are no longer under concurrent edit.

A `qna.md` entry is due when this is implemented: it spans more than 3 files, touches
orchestration, and will be claimed in the paper. The entry must record the impulse-gate sweep
numbers as measured, including any region where the median makes things worse.
