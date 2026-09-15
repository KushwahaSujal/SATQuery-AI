"""
Two-agent deliberation in the grounding pipeline: the detector proposes, the reasoner ranks, the
verification agent confirms / contradicts / cannot confirm; contradictions backtrack, and if nothing
survives the detector is re-run once at a relaxed threshold before reporting NOT_FOUND.
"""
import numpy as np
from PIL import Image

from backend.app.evidence.verifier import CONTRADICTED, UNVERIFIED, VERIFIED, VerificationVerdict
from backend.app.ml.adapters.sam2 import SAM2Result
from backend.app.workflows.grounding import run_grounding_pipeline

A = [10.0, 10.0, 40.0, 40.0]     # highest detector score -> reasoner's first choice
B = [100.0, 100.0, 130.0, 130.0]
C = [150.0, 20.0, 180.0, 50.0]   # only appears at the relaxed threshold


class Detector:
    def __init__(self, strict, relaxed=None):
        self.strict, self.relaxed, self.calls = strict, relaxed, []

    def predict(self, image_or_context, prompt, box_threshold=0.25, text_threshold=0.25):
        self.calls.append(box_threshold)
        boxes = self.strict if box_threshold >= 0.25 or self.relaxed is None else self.relaxed
        return {"boxes": [{"xyxy": b, "score": s, "label": "vehicle"} for b, s in boxes]}


class Sam:
    def predict(self, image_or_context, box, multimask_output=True):
        m = np.zeros((200, 200), dtype=np.uint8); m[20:30, 20:30] = 1
        return SAM2Result(mask=m, score=0.9, scores=[0.9], pixel_count=100, masks=[], boxes=[box],
                          confidence=0.9, answer="", model_name="sam2", metadata={})


class ScriptedVerifier:
    """Returns a fixed verdict per box; records what it was asked."""
    def __init__(self, by_box, available=True):
        self.by_box, self.available, self.seen = by_box, available, []

    def is_available(self):
        return self.available

    def verify(self, image, box, target_label):
        key = tuple(round(v) for v in box)
        self.seen.append(key)
        status = self.by_box[key]
        top = target_label if status == VERIFIED else ("road" if status == UNVERIFIED else "airplane")
        return VerificationVerdict(status=status, accepted=status == VERIFIED, target_label=target_label,
                                   target_group=target_label, target_probability=0.7 if status == VERIFIED else 0.05,
                                   target_rank=1 if status == VERIFIED else 9, top_k=3,
                                   top_alternatives=[(top, 0.6)], crop_box=[0, 0, 1, 1])


IMG = Image.new("RGB", (200, 200), (120, 120, 120))
K = lambda b: tuple(round(v) for v in b)


def run(detector, verifier):
    return run_grounding_pipeline(IMG, "find the vehicle", grounding_adapter=detector, sam2_adapter=Sam(), verifier=verifier)


def test_accepts_first_candidate_both_agents_confirm():
    v = ScriptedVerifier({K(A): VERIFIED, K(B): VERIFIED})
    r = run(Detector([(A, 0.8), (B, 0.6)]), v)
    d = r["agent_deliberation"]
    assert r["selected_box"] == A
    assert d["decision"] == "accepted_verified" and d["backtracks"] == 0 and not d["re_evaluated"]
    assert v.seen == [K(A)]
    assert "confirmed by two agents" in r["answer"]


def test_backtracks_past_contradicted_candidate():
    v = ScriptedVerifier({K(A): CONTRADICTED, K(B): VERIFIED})
    r = run(Detector([(A, 0.8), (B, 0.6)]), v)
    d = r["agent_deliberation"]
    assert r["selected_box"] == B
    assert d["backtracks"] == 1
    assert [a["decision"] for a in d["attempts"]] == ["backtrack", "accepted"]
    assert d["attempts"][0]["detector_confidence"] == 0.8 and d["attempts"][0]["verifier_status"] == CONTRADICTED
    assert "Backtracked past 1" in r["answer"]


def test_prefers_verified_over_earlier_unconfirmed():
    v = ScriptedVerifier({K(A): UNVERIFIED, K(B): VERIFIED})
    r = run(Detector([(A, 0.8), (B, 0.6)]), v)
    assert r["selected_box"] == B
    assert r["agent_deliberation"]["decision"] == "accepted_verified"


def test_unconfirmed_is_returned_but_labelled():
    v = ScriptedVerifier({K(A): UNVERIFIED, K(B): CONTRADICTED})
    det = Detector([(A, 0.8), (B, 0.6)])
    r = run(det, v)
    assert r["selected_box"] == A
    assert r["agent_deliberation"]["decision"] == "accepted_unconfirmed"
    assert r["answer"].startswith("UNCONFIRMED")
    assert det.calls == [0.25]  # an unconfirmed candidate exists, so no re-evaluation


def test_re_evaluates_with_relaxed_threshold_when_all_contradicted():
    v = ScriptedVerifier({K(A): CONTRADICTED, K(B): CONTRADICTED, K(C): VERIFIED})
    det = Detector(strict=[(A, 0.8), (B, 0.6)], relaxed=[(A, 0.8), (B, 0.6), (C, 0.2)])
    r = run(det, v)
    d = r["agent_deliberation"]
    assert det.calls == [0.25, 0.15]
    assert d["re_evaluated"] and r["selected_box"] == C
    # contradicted boxes are not re-verified on the second pass
    assert v.seen.count(K(A)) == 1 and v.seen.count(K(B)) == 1


def test_not_found_when_nothing_survives():
    v = ScriptedVerifier({K(A): CONTRADICTED, K(B): CONTRADICTED})
    r = run(Detector([(A, 0.8), (B, 0.6)]), v)
    d = r["agent_deliberation"]
    assert r["selected_box"] is None and r["segmentation_mask"] is None
    assert d["decision"] == "not_found" and d["re_evaluated"] and d["backtracks"] == 2
    assert r["answer"].startswith("No vehicle found") and "airplane" in r["answer"]


def test_without_verifier_behaves_as_single_agent():
    v = ScriptedVerifier({}, available=False)
    r = run(Detector([(A, 0.8), (B, 0.6)]), v)
    assert r["selected_box"] == A
    assert r["agent_deliberation"]["decision"] == "accepted_without_verification"
    assert v.seen == []


def test_relaxed_pass_does_not_accept_unconfirmed_candidates():
    v = ScriptedVerifier({K(A): CONTRADICTED, K(B): CONTRADICTED, K(C): UNVERIFIED})
    det = Detector(strict=[(A, 0.8), (B, 0.6)], relaxed=[(A, 0.8), (B, 0.6), (C, 0.2)])
    r = run(det, v)
    d = r["agent_deliberation"]
    assert r["selected_box"] is None and d["decision"] == "not_found"
    assert d["attempts"][-1]["decision"] == "rejected_unconfirmed_after_relaxation"


def run_attr(detector, verifier, query="find the largest vehicle"):
    return run_grounding_pipeline(IMG, query, grounding_adapter=detector, sam2_adapter=Sam(), verifier=verifier)


def test_attribute_query_is_labelled_not_backtracked_when_disputed():
    v = ScriptedVerifier({K(A): CONTRADICTED, K(B): VERIFIED})
    det = Detector([(A, 0.8), (B, 0.6)])
    r = run_attr(det, v)
    d = r["agent_deliberation"]
    assert d["mode"] == "attribute_query_label_only"
    assert r["selected_box"] is not None and d["decision"] == "accepted_disputed"
    assert d["backtracks"] == 0 and not d["re_evaluated"] and len(v.seen) == 1
    assert r["answer"].startswith("DISPUTED")
    assert det.calls == [0.25]


def test_attribute_query_verified_top_is_confirmed():
    r = run_attr(Detector([(A, 0.8), (B, 0.6)]), ScriptedVerifier({K(A): VERIFIED, K(B): VERIFIED}))
    assert r["agent_deliberation"]["decision"] == "accepted_verified"


def test_category_query_mode_recorded():
    r = run(Detector([(A, 0.8)]), ScriptedVerifier({K(A): VERIFIED}))
    assert r["agent_deliberation"]["mode"] == "category_query_backtracking"
