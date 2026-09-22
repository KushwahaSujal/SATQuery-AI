"""The registry must not report a refusing model as AVAILABLE, and a refusal must not look like a result.

Two defects found by an adversarial audit of our own capability listing (Q-045):

1. `ModelRegistry.get_model_status()` / `list_capabilities()` derived the lifecycle state purely from
   `adapter.available`, i.e. "the checkpoint file exists". Both deliberate refusers — the flood
   segmenter (Q-041 §5, gated by `preprocessing` since Q-044) and the optical-SAR fusion head — load
   real checkpoints and never produce an output, and both were listed as AVAILABLE. A mentor reading
   that listing concludes they work.
2. `ModelResult.status` was advisory text. Nothing in the backend read it, so the honesty of a
   refusal rested entirely on the prose in `answer`.

These tests pin the mechanism rather than the two model keys: the point of the design is that the
flood segmenter's reported state follows `configs/models.yaml` with no edit in the registry, so
`test_the_flood_gate_drives_the_reported_state` is the test that would catch a hardcoded list.

No weights are loaded anywhere here.
"""
import pytest
from pydantic import ValidationError

from backend.app.config import settings
from backend.app.ml.registry import (
    SERVING_PROBES,
    ModelRegistry,
    _probe_accepted_value_gate,
    _probe_declared_serving,
    _probe_is_configured,
)
from backend.app.schemas.agent import JobStatus, TaskType
from backend.app.schemas.models import ModelCapabilityInfo, ModelResult
from backend.app.schemas.responses import AnalyzeResponse

#: The two adapters that load and deliberately refuse. Asserted as an exact set, so a third refuser
#: appearing without a QNA entry fails here.
REFUSING = {"flood_segmenter", "satquery_optical_sar_fusion"}

FLOOD = "flood_segmenter"
FUSION = "satquery_optical_sar_fusion"


@pytest.fixture
def registry():
    """A private registry, so adapter instances cached here never leak into another test."""
    return ModelRegistry()


# --- defect 1: the load state distinguishes "refuses" from "works" ------------------------------

def test_exactly_the_two_known_refusers_are_not_serving(registry):
    assert set(registry.list_refusals()) == REFUSING


@pytest.mark.parametrize("key", sorted(set(ModelRegistry.ADAPTER_CLASSES) - REFUSING))
def test_every_other_model_still_reports_serving(registry, key):
    """The change must be invisible to the other 18 adapters."""
    status = registry.get_model_status(key)
    assert status["serving"] is True
    assert status["refusal_reason"] is None
    assert status["load_state"] != "PRESENT_NOT_SERVING"
    assert status["validation_status"] != "NOT_APPLICABLE"


@pytest.mark.parametrize("key", sorted(REFUSING))
def test_a_refuser_reports_present_not_serving(registry, key):
    status = registry.get_model_status(key)
    assert status["serving"] is False
    assert status["load_state"] == "PRESENT_NOT_SERVING"
    assert status["status"] == "PRESENT_NOT_SERVING"
    # Verification is not "pending" — while the adapter refuses there is no inference to verify.
    assert status["validation_status"] == "NOT_APPLICABLE"
    assert status["refusal_reason"]
    assert registry.is_model_serving(key) is False


@pytest.mark.parametrize("key", sorted(REFUSING))
def test_present_not_serving_is_not_the_missing_checkpoint_state(registry, key):
    """`available` must keep meaning "the checkpoint exists".

    Routing (backend/app/orchestration/dependency_checker.py) and HTTP 503
    /MODEL_CHECKPOINT_MISSING are both built on that meaning, and these two checkpoints really are
    on disk. Overloading `available` to mean "serves" would turn a truthful refusal into a claim that
    the weights are absent.
    """
    if not registry.get_adapter(key).available:
        pytest.skip(f"{key} checkpoint is not on this machine; nothing to distinguish.")
    status = registry.get_model_status(key)
    assert status["available"] is True
    assert status["serving"] is False
    assert registry.is_model_available(key) is True


def test_the_flood_gate_drives_the_reported_state(registry, monkeypatch):
    """The real test of a dynamic mechanism: opening the Q-044 gate must flip the reported state.

    A hardcoded list of refusing model keys would keep reporting PRESENT_NOT_SERVING here, which is
    the rot this design exists to avoid — whoever sets `preprocessing` in configs/models.yaml has no
    reason to also edit the registry.
    """
    adapter = registry.get_adapter(FLOOD)
    accepted = adapter.RECOVERED_PREPROCESSING

    monkeypatch.setattr(settings.models[FLOOD], "preprocessing", None)
    assert registry.get_model_status(FLOOD)["load_state"] == "PRESENT_NOT_SERVING"
    assert adapter.predict({}).status == "NOT_CONFIGURED"

    monkeypatch.setattr(settings.models[FLOOD], "preprocessing", accepted)
    opened = registry.get_model_status(FLOOD)
    assert opened["serving"] is True
    assert opened["refusal_reason"] is None
    assert opened["load_state"] in ("AVAILABLE", "LOADED")
    assert opened["validation_status"] == "PENDING_VERIFICATION"


@pytest.mark.parametrize("value", [None, "", "raw", "p2p98", "bn_recovered", "BN_RECOVERED_P2P98"])
def test_only_the_accepted_preprocessing_value_opens_the_flood_gate(registry, monkeypatch, value):
    monkeypatch.setattr(settings.models[FLOOD], "preprocessing", value)
    assert registry.get_model_status(FLOOD)["serving"] is False, f"{value!r} must not open the gate"


def test_the_fusion_head_refuses_unconditionally(registry, monkeypatch):
    """No configs/models.yaml key opens it: the head was never trained, so nothing can be served."""
    monkeypatch.setattr(settings.models[FLOOD], "preprocessing", "bn_recovered_p2p98")
    for key in ("preprocessing", "threshold"):
        if hasattr(settings.models[FUSION], key):
            monkeypatch.setattr(settings.models[FUSION], key, "anything")
    assert registry.get_model_status(FUSION)["load_state"] == "PRESENT_NOT_SERVING"


def test_the_fusion_state_is_read_from_the_adapter_not_from_a_key_list(registry, monkeypatch):
    """Flipping the adapter's own gate flips the reported state — proof there is no key list."""
    adapter = registry.get_adapter(FUSION)
    assert adapter.is_configured is False
    monkeypatch.setattr(adapter, "is_configured", True)
    assert registry.serving_state(FUSION) == (True, None)


def test_capability_listing_marks_the_refusers_and_leaves_the_rest_alone(registry):
    caps = {c.name: c for c in registry.list_capabilities()}
    refusing_names = {settings.models[k].name for k in REFUSING}
    for name, cap in caps.items():
        if name in refusing_names:
            assert cap.serving is False, name
            assert cap.load_state == "PRESENT_NOT_SERVING", name
            assert cap.status == "PRESENT_NOT_SERVING", name
            assert cap.validation_status == "NOT_APPLICABLE", name
            assert cap.refusal_reason, name
        else:
            assert cap.serving is True, name
            assert cap.load_state != "PRESENT_NOT_SERVING", name
            assert cap.refusal_reason is None, name


def test_capability_schema_defaults_do_not_claim_a_model_serves():
    """A hand-built ModelCapabilityInfo must not default to "this works"."""
    cap = ModelCapabilityInfo(name="x", task="t")
    assert cap.serving is False
    assert cap.refusal_reason is None


# --- the probe protocol ------------------------------------------------------------------------

class _Plain:
    """An adapter exposing none of the refusal signals: the default must be "serves"."""


class _Declares:
    serving = False
    refusal_reason = "declared in the adapter"


def test_an_adapter_with_no_refusal_signal_serves():
    assert all(probe(_Plain()) is None for probe in SERVING_PROBES)


def test_the_declared_serving_property_is_authoritative():
    assert _probe_declared_serving(_Declares()) == (False, "declared in the adapter")
    assert _probe_declared_serving(_Plain()) is None
    assert SERVING_PROBES[0] is _probe_declared_serving


def test_probes_do_not_apply_when_their_signal_is_absent():
    assert _probe_is_configured(_Plain()) is None
    assert _probe_accepted_value_gate(_Plain()) is None


def test_unknown_keys_never_report_serving(registry):
    serving, reason = registry.serving_state("no_such_model")
    assert serving is False and reason
    assert registry.get_model_status("no_such_model")["serving"] is False


# --- defect 2: ModelResult.status is enforced, not advisory -------------------------------------

def _refusal(**kw):
    return ModelResult(model_name="flood_segmenter", task="segmentation",
                       status="NOT_CONFIGURED", **kw)


def test_a_refusal_is_recognised_as_one():
    res = _refusal(answer="Flood extent NOT_CONFIGURED: normalisation unknown.")
    assert res.is_refusal is True
    assert "NOT_CONFIGURED" in res.answer


def test_a_successful_result_is_not_a_refusal_and_is_left_untouched():
    res = ModelResult(model_name="water_segmenter", task="segmentation", status="OK",
                      answer="Water covers 12 pixels.", confidence=0.9,
                      masks=[{"label": "water"}])
    assert res.is_refusal is False
    assert res.refusal_reason is None
    assert res.answer == "Water covers 12 pixels."
    assert res.warnings == []
    assert res.confidence == 0.9


@pytest.mark.parametrize("payload", [
    {"masks": [{"binary_mask": [[1]]}]},
    {"boxes": [{"xyxy": [0, 0, 1, 1]}]},
    {"logits": [0.1, 0.9]},
    {"confidence": 0.87},
])
def test_a_refusal_cannot_carry_a_payload(payload):
    """The contradiction is unconstructible, so no caller can render one as a success."""
    with pytest.raises(ValidationError) as exc:
        _refusal(**payload)
    assert "must carry no model output" in str(exc.value)


def test_a_refusal_without_an_answer_still_says_so():
    res = _refusal()
    assert "NOT_CONFIGURED" in res.answer
    assert "flood_segmenter" in res.answer


def test_a_refusal_whose_answer_hides_the_status_gets_it_back():
    res = _refusal(answer="Flood extent could not be reported.")
    assert res.answer.startswith("NOT_CONFIGURED: ")


def test_a_refusal_always_carries_a_warning():
    res = _refusal(answer="Flood extent NOT_CONFIGURED: normalisation unknown.")
    assert any("NOT_CONFIGURED" in w for w in res.warnings)


def test_a_refusal_does_not_get_a_duplicate_warning():
    res = _refusal(answer="NOT_CONFIGURED: x", warnings=["already NOT_CONFIGURED here"])
    assert res.warnings == ["already NOT_CONFIGURED here"]


def test_the_refusal_reason_prefers_the_adapters_own_words():
    res = _refusal(answer="NOT_CONFIGURED: x", metadata={"reason": "normalisation undocumented"})
    assert res.refusal_reason == "normalisation undocumented"


def test_the_live_adapters_refusals_satisfy_the_contract(registry):
    """The two real refusals must pass the enforced schema unchanged, not be reshaped by it."""
    res = registry.get_adapter(FLOOD).predict({})
    assert res.is_refusal and res.masks == [] and res.confidence is None
    assert res.answer.startswith("Flood extent NOT_CONFIGURED")     # untouched by the validator
    assert res.refusal_reason and "normalisation" in res.refusal_reason


# --- defect 2 at the API boundary ---------------------------------------------------------------

def test_the_analyze_response_has_an_explicit_refusal_field():
    """`model_refusals` is a top-level field, so a consumer cannot render a refusal as a normal answer.

    Populated in backend/app/agent/controller.py from `ModelResult.is_refusal`. Empty by default, so
    "this run had no refusal" and "this response predates the field" are not confusable with
    "something refused".
    """
    assert "model_refusals" in AnalyzeResponse.model_fields
    assert AnalyzeResponse.model_fields["model_refusals"].annotation is not None
    resp = AnalyzeResponse(request_id="r", status=JobStatus.COMPLETED, task=TaskType.UNSUPPORTED,
                           workflow_id="w", workflow_reason="none")
    assert resp.model_refusals == []
    assert "model_refusals" in resp.model_dump()
