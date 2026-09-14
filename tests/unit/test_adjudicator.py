"""
ChangeFormer (building change) vs CDVQA (all land-cover change) adjudication (project/qna.md Q-012).

Replaces the earlier tests, which asserted invented combined confidences and read mask keys
("changed_pixels", "change_ratio") that the ChangeFormer adapter never produces.
"""
import pytest

from backend.app.evidence.adjudicator import EvidenceAdjudicator, answer_type, classify_question
from backend.app.schemas.models import ModelResult


def cf(changed_px, total=1_048_576, regions=5, conf=0.87):
    return ModelResult(model_name="ChangeFormer", task="change_detection", confidence=conf,
                       metadata={"change_pixel_count": changed_px, "total_pixel_count": total, "region_count": regions})


def cdvqa(raw, conf=0.6):
    return ModelResult(model_name="CDVQA", task="change_vqa", answer=f"<{raw}>", confidence=conf, metadata={"raw_answer": raw})


def run(query, cf_px, raw, **kw):
    return EvidenceAdjudicator.adjudicate_change_vqa(query, cf(cf_px, **kw), cdvqa(raw))


@pytest.mark.parametrize("query,qtype,expected", [
    ("has any new building been constructed?", "change_or_not", "yes_no"),
    ("are there any changes?", "change_or_not", "yes_no"),
    ("have the buildings increased?", "increase_or_not", "yes_no"),
    ("has the water decreased?", "decrease_or_not", "yes_no"),
    ("what percentage of the area changed?", "change_ratio", "ratio"),
    ("what is the proportion of buildings changed?", "change_ratio_types", "ratio"),
    ("what is the largest change type?", "largest_change", "class"),
    ("what have the trees changed to?", "change_to_what", "class"),
    ("what changed between these two images?", "unknown", "unknown"),
])
def test_question_classification(query, qtype, expected):
    assert classify_question(query) == (qtype, expected)


def test_answer_types():
    assert answer_type("yes") == ("yes_no", None)
    assert answer_type("60_to_70") == ("ratio", (0.6, 0.7))
    assert answer_type("0") == ("ratio", (0.0, 0.0))
    assert answer_type("buildings") == ("class", None)


def test_ratio_answer_to_yes_no_question_is_set_aside():
    # The audit case: "has any new building been constructed?" -> CDVQA "60% to 70% change".
    r = run("has any new building been constructed?", 48_000, "60_to_70")
    assert r.adjudication_status == "CDVQA_ANSWER_TYPE_MISMATCH"
    assert r.confidence is None and r.conflict_details.has_conflict
    assert r.adjudicated_answer.startswith("Yes — building change is detected")


def test_direction_question_with_mismatched_answer_does_not_guess_direction():
    r = run("have the buildings decreased?", 48_000, "buildings")
    assert r.adjudication_status == "CDVQA_ANSWER_TYPE_MISMATCH"
    assert r.adjudicated_answer.startswith("No reliable answer")


def test_no_change_answer_conflicts_with_building_change():
    r = run("are there any changes?", 30_000, "no")  # 2.86% building change
    assert r.adjudication_status == "CONFLICT" and r.confidence is None
    assert r.conflict_details.conflict_type == "TEXT_NO_CHANGE_VS_SPATIAL_CHANGE"


def test_yes_without_building_change_is_consistent_for_a_general_question():
    r = run("are there any changes?", 0, "yes")
    assert r.adjudication_status == "CONSISTENT_WITH_CAVEAT" and r.confidence == 0.6
    assert "not buildings" in r.adjudicated_answer


def test_yes_without_building_change_conflicts_for_a_building_question():
    r = run("has any building been constructed?", 0, "yes")
    assert r.adjudication_status == "CONFLICT"


def test_small_false_positive_area_does_not_trigger_a_no_change_conflict():
    r = run("are there any changes?", 5_000, "no")  # 0.48%: below the 1% building-change threshold
    assert r.adjudication_status == "CONSISTENT" and r.confidence == 0.6


def test_ratio_below_building_change_alone_is_a_conflict():
    # 25% building change, x precision 0.8656 = 21.6% > CDVQA's upper bound of 10%
    r = run("what percentage of the area changed?", 262_144, "0_to_10")
    assert r.adjudication_status == "CONFLICT"
    assert r.conflict_details.conflict_type == "RATIO_BELOW_BUILDING_CHANGE"


def test_ratio_above_building_change_is_consistent():
    # the audit's "what changed" pair: CDVQA 10-20%, ChangeFormer ~4.6% building change
    r = run("what changed between these two images?", 48_000, "10_to_20")
    assert r.adjudication_status == "CONSISTENT" and r.confidence == 0.6


def test_zero_bucket_needs_real_building_change_to_conflict():
    assert run("what percentage changed?", 200, "0").adjudication_status == "CONSISTENT"
    assert run("what percentage changed?", 30_000, "0").adjudication_status == "CONFLICT"


def test_buildings_class_answer_without_building_change_conflicts():
    assert run("what is the largest change type?", 0, "buildings").adjudication_status == "CONFLICT"
    assert run("what is the largest change type?", 0, "trees").adjudication_status == "NOT_COMPARABLE"


def test_aoi_pixel_count_is_the_denominator():
    # 20,000 changed px inside a 100,000 px AOI = 20% (would be 1.9% of the full scene)
    r = EvidenceAdjudicator.adjudicate_change_vqa(
        "what percentage of the area changed?",
        ModelResult(model_name="ChangeFormer", task="change_detection", confidence=0.9,
                    metadata={"change_pixel_count": 20_000, "total_pixel_count": 1_048_576, "aoi_pixel_count": 100_000}),
        cdvqa("0_to_10"))
    assert r.contributing_evidence[0]["building_change_ratio"] == pytest.approx(0.2)
    assert r.adjudication_status == "CONFLICT"


def test_measured_cdvqa_accuracy_is_reported_per_question_type():
    r = run("what percentage of the area changed?", 48_000, "10_to_20")
    assert r.contributing_evidence[1]["measured_accuracy_for_question_type"] == pytest.approx(0.3776)
    assert "37.8% on SECOND-CDVQA imagery" in r.adjudicated_answer


def test_identical_inputs_mean_no_change_whatever_the_models_say():
    r = EvidenceAdjudicator.adjudicate_change_vqa("are there any changes?", cf(0), cdvqa("yes"), inputs_identical=True)
    assert r.adjudication_status == "INPUTS_IDENTICAL" and r.confidence is None
    assert r.adjudicated_answer.startswith("No change: the two images are identical")
    assert r.conflict_details.has_conflict  # CDVQA claimed change


def test_counterfactual_probe_sets_aside_an_answer_cdvqa_also_gives_for_no_change():
    r = EvidenceAdjudicator.adjudicate_change_vqa("are there any changes?", cf(48_000), cdvqa("yes"), cdvqa_identity_result=cdvqa("yes"))
    assert r.adjudication_status == "CDVQA_UNINFORMATIVE" and r.confidence is None
    assert r.adjudicated_answer.startswith("Yes — building change is detected")
    assert r.provenance["cdvqa_identity_probe_answer"] == "yes"


def test_probe_passes_when_cdvqa_answer_depends_on_the_change():
    r = EvidenceAdjudicator.adjudicate_change_vqa("are there any changes?", cf(48_000), cdvqa("yes"), cdvqa_identity_result=cdvqa("no"))
    assert r.adjudication_status == "CONSISTENT" and r.confidence == 0.6


def test_probe_on_ratio_question_answers_from_building_evidence():
    r = EvidenceAdjudicator.adjudicate_change_vqa("what percentage of the area changed?", cf(48_000), cdvqa("10_to_20"),
                                                  cdvqa_identity_result=cdvqa("10_to_20"))
    assert r.adjudication_status == "CDVQA_UNINFORMATIVE"
    assert "Total land-cover change cannot be estimated reliably" in r.adjudicated_answer
