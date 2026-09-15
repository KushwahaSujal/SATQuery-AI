"""
SatQuery AI — Evidence Adjudicator: ChangeFormer vs CDVQA on bi-temporal questions.

Two agents answer the same change question from different evidence:

  ChangeFormer   pixel mask of **building** change (LEVIR-CD labels buildings only); test IoU 0.7385,
                 precision 0.8656 (project/qna.md Q-007)
  CDVQA          a 19-class answer (yes/no, ten change-ratio buckets, six land-cover classes) about
                 **all** land-cover change (SECOND-CDVQA); accuracy depends heavily on question type,
                 83.6% for change-or-not down to 37.8% for change ratio (docs/models/CDVQA.md §18)

They measure different things, so a naive comparison is wrong. Building change is a *subset* of all
change. That makes only some disagreements genuine:

  - CDVQA "no change" while ChangeFormer finds substantial building change  -> CONFLICT
  - CDVQA "yes" while ChangeFormer finds no building change                 -> consistent for a
    general question (the change may not be buildings); CONFLICT only for a building question
  - CDVQA ratio bucket whose upper bound is below ChangeFormer's building-only ratio
    (discounted by its precision)                                            -> CONFLICT
  - CDVQA answer of the wrong *type* for the question (a ratio for a yes/no
    question), which a closed-vocabulary classifier can do                   -> TYPE_MISMATCH:
    CDVQA's answer is set aside and the answer comes from ChangeFormer evidence where it can

CDVQA is also checked against itself before any comparison. On LEVIR-CD-256 test imagery it answered
"yes, changes are observed" for 53.9% of *identical* image pairs, and its yes/no answers agreed with the
building ground truth 48.6% of the time (results/evaluations/cdvqa_on_levircd_test_20260914.json and
cdvqa_counterfactual_probe_levircd_20260914.json). So the same question is also put to CDVQA with the
first image twice; if it gives the same change-claiming answer when nothing changed, its answer carries
no information about this pair and is set aside (CDVQA_UNINFORMATIVE). That probe flagged 46% of its
yes/no and 75% of its ratio answers on that split.

"CONSISTENT" means the evidence does not refute CDVQA, not that it confirms it.

No confidence is invented. Each model's own score is reported; the adjudicated confidence is the
answering model's own score when the evidence agrees, and None when it conflicts.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from backend.app.config import ChangeAdjudicationSettings, settings
from backend.app.logging import logger
from backend.app.schemas.evidence import AdjudicationResult, ConflictReport
from backend.app.schemas.models import ModelResult

YES_NO, RATIO, CLASS, UNKNOWN = "yes_no", "ratio", "class", "unknown"
_CLASS_WORDS = r"building|buildings|house|houses|tree|trees|water|vegetation|vegetated|ground|surface|playground|playgrounds"
_BUILDING_WORDS = r"building|buildings|house|houses|construct|constructed|construction|built|demolish|demolished|structure|structures"


def classify_question(query: str) -> Tuple[str, str]:
    """(SECOND-CDVQA question type, expected answer type) from the user's wording."""
    q = query.lower()
    if re.search(r"\blargest\b", q):
        return "largest_change", CLASS
    if re.search(r"\bsmallest\b", q):
        return "smallest_change", CLASS
    if re.search(r"change[sd]? (in)?to\b|turned into|converted (in)?to", q):
        return "change_to_what", CLASS
    if re.search(r"percent|percentage|proportion|ratio|how much|what fraction", q):
        return ("change_ratio_types" if re.search(_CLASS_WORDS, q) else "change_ratio"), RATIO
    if re.search(r"\b(increase|increased|expand|expanded|grow|grew|more)\b", q):
        return "increase_or_not", YES_NO
    if re.search(r"\b(decrease|decreased|reduce|reduced|shrink|shrank|less|fewer|demolish|demolished|removed)\b", q):
        return "decrease_or_not", YES_NO
    if re.match(r"\s*(is|are|has|have|did|does|do|was|were|any)\b", q) or re.search(r"\bany (new )?(change|building)", q):
        return "change_or_not", YES_NO
    return UNKNOWN, UNKNOWN


def answer_type(raw_answer: str) -> Tuple[str, Optional[Tuple[float, float]]]:
    """(answer type, ratio bounds as fractions) for a CDVQA raw answer token."""
    if raw_answer in ("yes", "no"):
        return YES_NO, None
    if raw_answer == "0":
        return RATIO, (0.0, 0.0)
    m = re.fullmatch(r"(\d+)_to_(\d+)", raw_answer or "")
    if m:
        return RATIO, (int(m.group(1)) / 100.0, int(m.group(2)) / 100.0)
    return CLASS, None


class EvidenceAdjudicator:
    """Deterministic, auditable adjudication of ChangeFormer and CDVQA answers to one change question."""

    @classmethod
    def adjudicate_change_vqa(
        cls,
        query: str,
        changeformer_result: ModelResult,
        cdvqa_result: ModelResult,
        job_id: Optional[str] = None,
        cfg: Optional[ChangeAdjudicationSettings] = None,
        cdvqa_identity_result: Optional[ModelResult] = None,
        inputs_identical: bool = False,
    ) -> AdjudicationResult:
        cfg = cfg or settings.change_adjudication
        q_type, expected = classify_question(query)
        building_question = bool(re.search(_BUILDING_WORDS, query.lower()))

        md = changeformer_result.metadata or {}
        cf_px = int(md.get("change_pixel_count", 0))
        cf_total = int(md.get("aoi_pixel_count") or md.get("total_pixel_count") or 0)
        cf_ratio = (cf_px / cf_total) if cf_total else 0.0
        cf_regions = int(md.get("region_count", 0))
        cf_conf = changeformer_result.confidence
        buildings_changed = cf_ratio >= cfg.building_change_present_ratio
        no_building_change = cf_ratio < cfg.building_change_absent_ratio

        raw = str((cdvqa_result.metadata or {}).get("raw_answer", "")).strip()
        cdvqa_text = (cdvqa_result.answer or raw).strip()
        cdvqa_conf = cdvqa_result.confidence
        a_type, bounds = answer_type(raw)
        type_accuracy = cfg.cdvqa_accuracy_by_question_type.get(q_type)

        cf_summary = (f"ChangeFormer building change: {cf_ratio:.2%} of the analysed area "
                      f"({cf_px:,} px, {cf_regions} region{'s' if cf_regions != 1 else ''})")
        contributing = [
            {"model": "ChangeFormer", "task": "building_change_detection", "confidence": cf_conf,
             "change_pixel_count": cf_px, "analysed_pixel_count": cf_total, "building_change_ratio": round(cf_ratio, 6),
             "region_count": cf_regions, "measures": "building change only (LEVIR-CD)"},
            {"model": "CDVQA", "task": "change_vqa", "confidence": cdvqa_conf, "raw_answer": raw,
             "answer": cdvqa_text, "answer_type": a_type, "measures": "all land-cover change (SECOND-CDVQA)",
             "measured_accuracy_for_question_type": type_accuracy},
        ]
        provenance = {
            "timestamp": datetime.now(timezone.utc).isoformat(), "job_id": job_id,
            "question_type": q_type, "expected_answer_type": expected, "building_question": building_question,
            "inputs_identical": inputs_identical,
            "cdvqa_identity_probe_answer": (cdvqa_identity_result.metadata or {}).get("raw_answer") if cdvqa_identity_result else None,
            "thresholds": {"building_change_present_ratio": cfg.building_change_present_ratio,
                           "building_change_absent_ratio": cfg.building_change_absent_ratio,
                           "changeformer_precision": cfg.changeformer_precision},
        }
        # Accuracy measured on CDVQA's own dataset; it does not transfer to other imagery (on LEVIR-CD its
        # yes/no answers matched building ground truth 48.6% of the time), so the note names the dataset.
        acc_note = (f" CDVQA's measured accuracy on {q_type} questions is {type_accuracy:.1%} on SECOND-CDVQA imagery; "
                    f"it is not measured on this imagery." if type_accuracy else "")

        def result(status, rule, answer, confidence, conflict=None):
            logger.info(f"[{job_id}] change adjudication: {status} via {rule}")
            return AdjudicationResult(
                adjudicated_answer=answer, adjudication_status=status, confidence=confidence,
                contributing_evidence=contributing, applied_rule=rule, provenance=provenance,
                conflict_details=conflict or ConflictReport(has_conflict=False),
            )

        def conflict(kind, description, **metrics):
            return ConflictReport(has_conflict=True, conflict_type=kind, description=description,
                                  disagreeing_models=["ChangeFormer", "CDVQA"], metrics=metrics)

        def from_changeformer_only() -> str:
            # Only "did it change?" can be answered from a building mask; increase/decrease needs direction.
            if q_type == "change_or_not":
                if buildings_changed:
                    return f"Yes — building change is detected. {cf_summary}"
                if no_building_change:
                    return f"No building change is detected. {cf_summary}; change in other land cover is not assessed"
                return f"Only marginal building change is detected. {cf_summary}"
            if expected == RATIO:
                return f"{cf_summary}. Total land-cover change cannot be estimated reliably from this evidence"
            return f"{cf_summary}"

        # 0a. Identical inputs: nothing can have changed, whatever either model says.
        if inputs_identical:
            claims_change = raw not in ("no", "0") or cf_px > 0
            return result(
                "INPUTS_IDENTICAL", "RULE_IDENTICAL_INPUTS_MEANS_NO_CHANGE",
                f"No change: the two images are identical. CDVQA answered '{cdvqa_text}'; ChangeFormer found {cf_px:,} changed px.",
                None, conflict("IDENTICAL_INPUTS", "A model reported change between identical images.", cdvqa_answer=raw,
                               changeformer_changed_pixels=cf_px) if claims_change else None)

        # 0b. Counterfactual probe: CDVQA gives the same change claim when nothing changed.
        if cdvqa_identity_result is not None:
            probe_raw = str((cdvqa_identity_result.metadata or {}).get("raw_answer", "")).strip()
            if probe_raw == raw and raw not in ("no", "0"):
                return result(
                    "CDVQA_UNINFORMATIVE", "RULE_COUNTERFACTUAL_IDENTITY_PROBE",
                    f"{from_changeformer_only()}. CDVQA's answer '{cdvqa_text}' was set aside: it gives the same answer when "
                    f"shown the first image twice, so it says nothing about the difference between these images.{acc_note}",
                    None, conflict("CDVQA_SAME_ANSWER_FOR_IDENTICAL_INPUTS",
                                   "CDVQA's answer does not depend on whether anything changed.", cdvqa_answer=raw,
                                   identity_probe_answer=probe_raw))

        # 1. CDVQA answered the wrong kind of question.
        if expected != UNKNOWN and a_type != expected:
            # ChangeFormer can say whether buildings changed, not whether they increased or decreased.
            if q_type == "change_or_not":
                if buildings_changed:
                    verdict = "Yes — building change is detected"
                elif no_building_change:
                    verdict = ("No building change is detected" if building_question else
                               "No building change is detected; other land-cover change cannot be assessed")
                else:
                    verdict = "Only marginal building change is detected"
                answer = (f"{verdict}. {cf_summary}. CDVQA answered '{cdvqa_text}', which does not answer a yes/no "
                          f"question, so it was set aside.")
            else:
                answer = (f"No reliable answer: CDVQA answered '{cdvqa_text}' ({a_type}) to a {expected} question, "
                          f"and ChangeFormer only measures building change. {cf_summary}.")
            return result("CDVQA_ANSWER_TYPE_MISMATCH", "RULE_ANSWER_TYPE_MUST_MATCH_QUESTION", answer, None,
                          conflict("ANSWER_TYPE_MISMATCH", f"CDVQA returned a {a_type} answer to a {expected} question.",
                                   question_type=q_type, cdvqa_answer=raw))

        # 2. Yes/no questions.
        if a_type == YES_NO:
            says_yes = raw == "yes"
            if not says_yes and buildings_changed:
                return result(
                    "CONFLICT", "RULE_BUILDING_CHANGE_CONTRADICTS_NO",
                    f"CONFLICT: CDVQA answered '{cdvqa_text}', but {cf_summary}. Building change is change, so the two "
                    f"agents disagree; review the change mask.{acc_note}",
                    None, conflict("TEXT_NO_CHANGE_VS_SPATIAL_CHANGE", "CDVQA says no; ChangeFormer finds building change.",
                                   building_change_ratio=round(cf_ratio, 6), cdvqa_answer=raw))
            if says_yes and no_building_change and building_question:
                return result(
                    "CONFLICT", "RULE_NO_BUILDING_CHANGE_CONTRADICTS_YES",
                    f"CONFLICT: CDVQA answered '{cdvqa_text}' to a building question, but {cf_summary}.{acc_note}",
                    None, conflict("TEXT_CHANGE_VS_NO_BUILDING_CHANGE", "CDVQA says yes to a building question; ChangeFormer finds none.",
                                   building_change_ratio=round(cf_ratio, 6), cdvqa_answer=raw))
            if says_yes and no_building_change:
                return result(
                    "CONSISTENT_WITH_CAVEAT", "RULE_NON_BUILDING_CHANGE_POSSIBLE",
                    f"{cdvqa_text} {cf_summary}, so the change CDVQA reports is not buildings.{acc_note}",
                    cdvqa_conf)
            return result("CONSISTENT", "RULE_YES_NO_CONSISTENT", f"{cdvqa_text} {cf_summary}.{acc_note}", cdvqa_conf)

        # 3. Ratio questions: building change is a subset of all change.
        if a_type == RATIO and bounds is not None:
            lo, hi = bounds
            building_floor = cf_ratio * cfg.changeformer_precision
            # A "0%" bucket would be contradicted by a handful of false-positive pixels, so it needs the same
            # evidence as any other claim that buildings changed.
            if building_floor > hi and (hi > 0.0 or buildings_changed):
                return result(
                    "CONFLICT", "RULE_BUILDING_CHANGE_EXCEEDS_CDVQA_TOTAL",
                    f"CONFLICT: CDVQA estimates {cdvqa_text.rstrip('.')} in total, but {cf_summary} — at least "
                    f"{building_floor:.1%} after allowing for ChangeFormer's precision, already above that range.{acc_note}",
                    None, conflict("RATIO_BELOW_BUILDING_CHANGE", "CDVQA's total change ratio is below building change alone.",
                                   cdvqa_bucket=[lo, hi], building_change_ratio=round(cf_ratio, 6),
                                   building_change_floor=round(building_floor, 6)))
            if building_question and not (lo <= cf_ratio <= hi or (hi == 0.0 and no_building_change)):
                return result(
                    "CONFLICT", "RULE_BUILDING_RATIO_OUTSIDE_BUCKET",
                    f"CONFLICT: for building change CDVQA estimates {cdvqa_text.rstrip('.')}, but {cf_summary}.{acc_note}",
                    None, conflict("BUILDING_RATIO_OUTSIDE_BUCKET", "Building change ratio falls outside CDVQA's bucket.",
                                   cdvqa_bucket=[lo, hi], building_change_ratio=round(cf_ratio, 6)))
            return result(
                "CONSISTENT", "RULE_RATIO_CONSISTENT_WITH_BUILDING_SUBSET",
                f"{cdvqa_text} {cf_summary}, which is consistent: building change is part of total change.{acc_note}",
                cdvqa_conf)

        # 4. Land-cover class answers: only 'buildings' can be checked against ChangeFormer.
        if raw == "buildings" and no_building_change:
            return result(
                "CONFLICT", "RULE_BUILDINGS_ANSWER_WITHOUT_BUILDING_CHANGE",
                f"CONFLICT: CDVQA names buildings ('{cdvqa_text}'), but {cf_summary}.{acc_note}",
                None, conflict("CLASS_BUILDINGS_VS_NO_BUILDING_CHANGE", "CDVQA names buildings; ChangeFormer finds none.",
                               building_change_ratio=round(cf_ratio, 6), cdvqa_answer=raw))
        return result(
            "NOT_COMPARABLE", "RULE_CLASS_ANSWER_OUTSIDE_CHANGEFORMER_SCOPE",
            f"{cdvqa_text} ChangeFormer cannot check this answer because it only measures building change; {cf_summary}.{acc_note}",
            cdvqa_conf)
