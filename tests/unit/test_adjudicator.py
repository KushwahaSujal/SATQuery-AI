"""
Unit tests for EvidenceAdjudicator.
Verifies concordant resolution, conflict surfacing, and uncertainty handling.
"""
import pytest
from backend.app.evidence.adjudicator import EvidenceAdjudicator
from backend.app.schemas.models import ModelResult


def test_adjudicator_concordant_change():
    cf_res = ModelResult(
        model_name="ChangeFormer",
        task="bitemporal_change_detection",
        confidence=0.85,
        masks=[{"changed_pixels": 1200, "change_ratio": 0.18, "quality_status": "PASS"}]
    )
    cdvqa_res = ModelResult(
        model_name="CDVQA",
        task="change_vqa",
        answer="10% to 20% change.",
        confidence=0.80
    )
    result = EvidenceAdjudicator.adjudicate(
        task_type="bitemporal_change",
        changeformer_result=cf_res,
        cdvqa_result=cdvqa_res
    )
    assert result.adjudication_status == "RESOLVED"
    assert "10% to 20% change." in result.adjudicated_answer
    assert result.confidence >= 0.80
    assert result.conflict_details.has_conflict is False


def test_adjudicator_conflict_spatial_vs_text_no_change():
    cf_res = ModelResult(
        model_name="ChangeFormer",
        task="bitemporal_change_detection",
        confidence=0.90,
        masks=[{"changed_pixels": 8500, "change_ratio": 0.13, "quality_status": "PASS"}]
    )
    cdvqa_res = ModelResult(
        model_name="CDVQA",
        task="change_vqa",
        answer="There is no change between the images.",
        confidence=0.75
    )
    result = EvidenceAdjudicator.adjudicate(
        task_type="bitemporal_change",
        changeformer_result=cf_res,
        cdvqa_result=cdvqa_res
    )
    assert result.adjudication_status == "CONFLICT"
    assert "REVIEW REQUIRED" in result.adjudicated_answer
    assert result.confidence <= 0.45
    assert result.conflict_details.has_conflict is True
    assert result.conflict_details.conflict_type == "SPATIAL_DETECTED_VS_TEXTUAL_NO_CHANGE"


def test_adjudicator_ambiguous_empty_mask_vs_text_change():
    cf_res = ModelResult(
        model_name="ChangeFormer",
        task="bitemporal_change_detection",
        confidence=0.90,
        masks=[{"changed_pixels": 0, "change_ratio": 0.0, "quality_status": "PASS"}]
    )
    cdvqa_res = ModelResult(
        model_name="CDVQA",
        task="change_vqa",
        answer="More than 50% new buildings were constructed.",
        confidence=0.80
    )
    result = EvidenceAdjudicator.adjudicate(
        task_type="bitemporal_change",
        changeformer_result=cf_res,
        cdvqa_result=cdvqa_res
    )
    assert result.adjudication_status == "AMBIGUOUS"
    assert "AMBIGUOUS" in result.adjudicated_answer
    assert result.conflict_details.has_conflict is True
