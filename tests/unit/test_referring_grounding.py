"""
Referring-expression path of the grounding pipeline (project/qna.md Q-083, Q-084): a single-target referring query
goes, as its full text, to the DIOR-RSVG fine-tune; its top box is the answer at score >= 0.35, otherwise "not
found". Category, "find all", counting queries and callers that inject a detector keep today's path. CPU only,
no weights: every model is a fake.
"""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.app.config import settings
from backend.app.evidence.verifier import CONTRADICTED, UNVERIFIED, VERIFIED, VerificationVerdict
from backend.app.exceptions import InferenceError, ModelUnavailableError
from backend.app.ml.adapters.grounding_dino import GroundingDINOReferringAdapter
from backend.app.ml.adapters.sam2 import SAM2Result
from backend.app.ml.registry import model_registry
from backend.app.workflows import grounding as G
from backend.app.workflows.grounding import (REFERRING_STRATEGY, _wants_all_instances, is_referring_query,
                                             referring_prompt, run_grounding_pipeline)
from backend.app.workflows.grounding_reasoner import parse_v4_query

A = [10.0, 10.0, 40.0, 40.0]
B = [100.0, 100.0, 130.0, 130.0]
IMG = Image.new("RGB", (200, 200), (120, 120, 120))
K = lambda b: tuple(round(v) for v in b)  # noqa: E731
REFERRING_Q = "the small vehicle on the top-left"


def routed(q: str) -> bool:
    p = parse_v4_query(q)
    return is_referring_query(p, _wants_all_instances(q, "", p))


class Referring:
    """Fake fine-tuned detector: returns fixed (box, score) pairs and records the expression it got."""
    model_id = "/fake/checkpoints/grounding_dino_rsvg"

    def __init__(self, boxes, raises=None):
        self.boxes, self.raises, self.expressions = boxes, raises, []

    def predict_referring(self, image, expression, top_k=20):
        self.expressions.append(expression)
        if self.raises is not None:
            raise self.raises
        return {"boxes": [{"xyxy": b, "score": s, "label": "referring"} for b, s in self.boxes]}


class Base:
    """Fake base detector; `explode` makes any call fail the test."""
    model_id = "IDEA-Research/grounding-dino-base"

    def __init__(self, boxes=((A, 0.8),), explode=False):
        self.boxes, self.explode, self.prompts = list(boxes), explode, []

    def predict(self, image_or_context, prompt, box_threshold=0.25, text_threshold=0.25):
        assert not self.explode, "the base detector must not run on the referring path"
        self.prompts.append(prompt)
        return {"boxes": [{"xyxy": b, "score": s, "label": "vehicle"} for b, s in self.boxes]}


class Sam:
    def __init__(self):
        self.calls = 0

    def predict(self, image_or_context, box, multimask_output=True):
        self.calls += 1
        m = np.zeros((200, 200), dtype=np.uint8); m[20:30, 20:30] = 1
        return SAM2Result(mask=m, score=0.9, scores=[0.9], pixel_count=100, masks=[], boxes=[box],
                          confidence=0.9, answer="", model_name="sam2", metadata={})


class ScriptedVerifier:
    def __init__(self, by_box):
        self.by_box, self.seen = by_box, []

    def is_available(self):
        return True

    def verify(self, image, box, target_label):
        key = K(box)
        self.seen.append(key)
        status = self.by_box[key]
        return VerificationVerdict(status=status, accepted=status == VERIFIED, target_label=target_label,
                                   target_group=target_label, target_probability=0.7 if status == VERIFIED else 0.05,
                                   target_rank=1 if status == VERIFIED else 9, top_k=3,
                                   top_alternatives=[("airplane", 0.6)], crop_box=[0, 0, 1, 1])


def steps(r):
    return [s["step"] for s in r["trace"]]


# ---------------------------------------------------------------------------------------- routing rule
@pytest.mark.parametrize("q", [
    "The large yellow vehicle situated closest to the green area.",
    "The small dark-colored vehicle located at the top-right corner of the image.",
    "The harbor located on the extreme left-hand side of the image.",
    "segment the largest building",
    "the second ship from the left",
    "find the white car near the red house",
    "show me the storage tank on the right",
])
def test_single_target_referring_queries_take_the_referring_path(q):
    assert routed(q)


@pytest.mark.parametrize("q", [
    "mask airplanes", "find all vehicles", "mark cars near houses", "mask white houses",
    "how many ships are there?", "find the vehicle", "ship", "segment the water bodies", "where is the bridge",
])
def test_category_all_and_count_queries_keep_the_base_path(q):
    assert not routed(q)


def test_referring_prompt_strips_only_a_leading_directive():
    assert referring_prompt("segment the largest building") == "the largest building"
    assert referring_prompt("show me the storage tank on the right") == "the storage tank on the right"
    q = "The ship located towards the middle-left of the image."
    assert referring_prompt(q) == q


# ------------------------------------------------------------------------------------- pipeline behaviour
def test_referring_path_takes_the_top_score_box_with_the_full_expression():
    ref = Referring([(A, 0.5), (B, 0.7)])
    sam = Sam()
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=ref, grounding_adapter=Base(explode=True),
                               sam2_adapter=sam, verifier=ScriptedVerifier({K(B): VERIFIED}))
    assert ref.expressions == [REFERRING_Q]
    assert r["selected_box"] == B and r["strategy"] == REFERRING_STRATEGY
    assert r["detector"] == "grounding_dino_referring" and r["detector_model_id"] == Referring.model_id
    assert r["instance_boxes"] == [B] and sam.calls == 1
    d = r["agent_deliberation"]
    assert d["mode"] == "referring_expression_label_only" and d["path"] == "referring_expression"
    assert d["decision"] == "accepted_verified" and len(d["attempts"]) == 1 and d["backtracks"] == 0
    assert "select_referring_top1" in steps(r) and "run_grounding_reasoner" not in steps(r)
    assert r["evidence"]["referring_expression"]["score_threshold"] == settings.referring_grounding.score_threshold
    assert "0.700 >= 0.35" in r["answer"]


def test_below_threshold_is_not_found_without_sam_or_a_base_retry():
    sam = Sam()
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([(A, 0.30)]),
                               grounding_adapter=Base(explode=True), sam2_adapter=sam,
                               verifier=ScriptedVerifier({K(A): VERIFIED}))
    d = r["agent_deliberation"]
    assert r["selected_box"] is None and r["segmentation_mask"] is None and sam.calls == 0
    assert d["decision"] == "not_found" and not d["re_evaluated"]
    assert r["evidence"]["reasoning_strategy"] == "referring_score_below_threshold"
    assert "0.300" in r["answer"] and "0.35" in r["answer"]


def test_exactly_the_threshold_is_accepted():
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([(A, 0.35)]), sam2_adapter=Sam(),
                               verifier=ScriptedVerifier({K(A): VERIFIED}))
    assert r["selected_box"] == A


def test_verifier_labels_but_never_replaces_the_referring_box():
    v = ScriptedVerifier({K(A): CONTRADICTED, K(B): VERIFIED})
    ref = Referring([(A, 0.8), (B, 0.6)])
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=ref, sam2_adapter=Sam(), verifier=v)
    d = r["agent_deliberation"]
    assert r["selected_box"] == A and d["decision"] == "accepted_disputed"
    assert v.seen == [K(A)] and len(ref.expressions) == 1
    assert r["answer"].startswith("DISPUTED") and "referring-expression detector selected it" in r["answer"]


def test_unconfirmed_box_is_kept_and_labelled():
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([(A, 0.8)]), sam2_adapter=Sam(),
                               verifier=ScriptedVerifier({K(A): UNVERIFIED}))
    assert r["selected_box"] == A and r["agent_deliberation"]["decision"] == "accepted_unconfirmed"


def test_aoi_picks_the_best_box_centred_inside_it():
    aoi = np.zeros((200, 200), dtype=np.uint8); aoi[90:200, 90:200] = 1
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([(A, 0.9), (B, 0.5)]),
                               sam2_adapter=Sam(), verifier=ScriptedVerifier({K(B): VERIFIED}), aoi_mask=aoi)
    assert r["selected_box"] == B and "filter_area_of_interest" in steps(r)


def test_injected_base_detector_keeps_todays_path():
    base = Base([(A, 0.8)])
    r = run_grounding_pipeline(IMG, REFERRING_Q, grounding_adapter=base, sam2_adapter=Sam(),
                               verifier=ScriptedVerifier({K(A): VERIFIED}))
    assert r["strategy"] == "V4_RELATIONAL" and base.prompts and "select_referring_top1" not in steps(r)


def test_disabled_flag_sends_referring_queries_to_the_base_path(monkeypatch):
    monkeypatch.setattr(settings.referring_grounding, "enabled", False)
    ref = Referring([(A, 0.9)])
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=ref, grounding_adapter=Base([(A, 0.8)]),
                               sam2_adapter=Sam(), verifier=ScriptedVerifier({K(A): VERIFIED}))
    assert r["strategy"] == "V4_RELATIONAL" and ref.expressions == []


def test_unavailable_referring_model_falls_back_and_says_so(monkeypatch):
    base = Base([(A, 0.8)])
    monkeypatch.setattr(model_registry, "is_model_available", lambda k: k != "grounding_dino_referring")
    monkeypatch.setattr(model_registry, "get_adapter", lambda k: base)
    r = run_grounding_pipeline(IMG, REFERRING_Q, sam2_adapter=Sam(), verifier=ScriptedVerifier({K(A): VERIFIED}))
    warn = next(s for s in r["trace"] if s["step"] == "referring_detector_unavailable")
    assert warn["details"]["fallback"] == "grounding_dino_v4_reasoner"
    assert r["strategy"] == "V4_RELATIONAL" and base.prompts


def test_load_failure_falls_back_to_the_base_path():
    err = ModelUnavailableError(model_name="GroundingDINO-RSVG", message="weights missing")
    r = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([], raises=err),
                               grounding_adapter=Base([(A, 0.8)]), sam2_adapter=Sam(),
                               verifier=ScriptedVerifier({K(A): VERIFIED}))
    assert "referring_detector_failed" in steps(r) and r["strategy"] == "V4_RELATIONAL"


def test_inference_errors_propagate_for_the_executors_oom_retry():
    with pytest.raises(InferenceError):
        run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([], raises=RuntimeError("CUDA out of memory")),
                               grounding_adapter=Base(explode=True), sam2_adapter=Sam(),
                               verifier=ScriptedVerifier({}))


def test_result_keys_match_the_base_path():
    ref = run_grounding_pipeline(IMG, REFERRING_Q, referring_adapter=Referring([(A, 0.8)]), sam2_adapter=Sam(),
                                 verifier=ScriptedVerifier({K(A): VERIFIED}))
    base = run_grounding_pipeline(IMG, REFERRING_Q, grounding_adapter=Base([(A, 0.8)]), sam2_adapter=Sam(),
                                  verifier=ScriptedVerifier({K(A): VERIFIED}))
    assert set(ref) == set(base)
    assert set(base["evidence"]) <= set(ref["evidence"])
    assert all("xyxy" in c and "score" in c for c in ref["evidence"]["all_candidates"])


# ------------------------------------------------------------------------------------------- adapter
def test_adapter_is_unavailable_without_its_weight_files(tmp_path, monkeypatch):
    a = GroundingDINOReferringAdapter()
    monkeypatch.setattr(type(a), "checkpoint_path", property(lambda self: tmp_path / "missing"))
    assert not a.is_available()
    (tmp_path / "missing").mkdir()
    (tmp_path / "missing" / "config.json").write_text("{}")
    assert not a.is_available()  # model.safetensors still missing
    with pytest.raises(ModelUnavailableError):
        a.load_model()


def test_adapter_path_is_absolute_and_independent_of_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = GroundingDINOReferringAdapter()
    assert Path(a.model_id).is_absolute() and a.model_id.startswith(str(settings.root_dir))
    assert a.processor_id == "IDEA-Research/grounding-dino-base"


def test_referring_model_is_optional_for_the_grounding_capability():
    from backend.app.orchestration.capability_registry import capability_registry
    cap = capability_registry.get("single_image_grounding")
    assert "grounding_dino_referring" in cap.optional_models and "grounding_dino_referring" not in cap.required_models


def test_pipeline_module_exposes_the_strategy_name():
    assert G.REFERRING_STRATEGY == "referring_expression_detector"
