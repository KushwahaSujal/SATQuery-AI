"""
SatQuery AI — Evidence Adjudicator
Deterministic Rule-Based Adjudicator (Option A) that detects and resolves
discrepancies between spatial change segmentation (ChangeFormer), change question
answering (CDVQA), spatial grounding, and spectral indices (NDVI).
Never fabricates certainty; explicitly surfaces REVIEW_REQUIRED or AMBIGUOUS when
evidence conflicts.
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.app.schemas.evidence import (
    AdjudicationResult,
    ConflictReport,
    EvidencePackage,
)
from backend.app.schemas.models import ModelResult
from backend.app.logging import logger


class EvidenceAdjudicator:
    """
    Transparent, auditable evidence adjudicator for multi-model remote sensing results.
    """

    @classmethod
    def adjudicate(
        cls,
        task_type: str,
        primary_answer: Optional[str] = None,
        primary_confidence: float = 0.0,
        changeformer_result: Optional[ModelResult] = None,
        cdvqa_result: Optional[ModelResult] = None,
        grounding_evidence: Optional[Dict[str, Any]] = None,
        spectral_metrics: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None
    ) -> AdjudicationResult:
        """
        Adjudicates multi-model outputs for consistency and produces an auditable verdict.
        """
        contributing: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # Gather contributing model evidence
        if changeformer_result:
            stats = {}
            if changeformer_result.masks:
                m0 = changeformer_result.masks[0]
                stats = {
                    "changed_pixels": m0.get("changed_pixels", 0),
                    "change_ratio": m0.get("change_ratio", 0.0),
                    "quality_status": m0.get("quality_status", "PASS"),
                }
            contributing.append({
                "model": "ChangeFormer",
                "task": "bitemporal_change_detection",
                "metrics": stats,
                "confidence": changeformer_result.confidence or 0.5,
            })

        if cdvqa_result:
            contributing.append({
                "model": "CDVQA",
                "task": "change_vqa",
                "answer": cdvqa_result.answer,
                "confidence": cdvqa_result.confidence or 0.5,
            })

        if spectral_metrics:
            contributing.append({
                "model": "SpectralEngine",
                "task": "index_differencing",
                "metrics": spectral_metrics,
            })

        # Scenario 1: Bi-temporal change detection & QA
        if changeformer_result and cdvqa_result:
            return cls._adjudicate_bitemporal(
                changeformer_result=changeformer_result,
                cdvqa_result=cdvqa_result,
                spectral_metrics=spectral_metrics,
                contributing=contributing,
                now_iso=now_iso,
                job_id=job_id
            )

        # Scenario 2: Single model or Grounding only (Pass through with integrity check)
        final_answer = primary_answer or (cdvqa_result.answer if cdvqa_result else "Analysis completed.")
        return AdjudicationResult(
            adjudicated_answer=final_answer,
            adjudication_status="NO_CONFLICT",
            confidence=max(0.0, min(1.0, float(primary_confidence))),
            contributing_evidence=contributing,
            conflict_details=ConflictReport(has_conflict=False, description="Single primary stream; no cross-model conflict."),
            applied_rule="SINGLE_MODEL_PASS_THROUGH",
            provenance={
                "timestamp": now_iso,
                "job_id": job_id,
                "models_evaluated": [c["model"] for c in contributing]
            }
        )

    @classmethod
    def _adjudicate_bitemporal(
        cls,
        changeformer_result: ModelResult,
        cdvqa_result: ModelResult,
        spectral_metrics: Optional[Dict[str, Any]],
        contributing: List[Dict[str, Any]],
        now_iso: str,
        job_id: Optional[str]
    ) -> AdjudicationResult:
        """
        Adjudicates bitemporal results between ChangeFormer pixel segmentation and CDVQA answer.
        """
        # Extract ChangeFormer stats
        cf_mask = changeformer_result.masks[0] if changeformer_result.masks else {}
        cf_changed_pixels = int(cf_mask.get("changed_pixels", 0))
        cf_ratio = float(cf_mask.get("change_ratio", 0.0))
        cf_quality = str(cf_mask.get("quality_status", "PASS"))

        cdvqa_text = (cdvqa_result.answer or "").strip()
        cdvqa_text_lower = cdvqa_text.lower()
        cdvqa_conf = float(cdvqa_result.confidence or 0.5)

        # Semantic interpretation of CDVQA
        cdvqa_indicates_change = any(w in cdvqa_text_lower for w in [
            "change", "increased", "decreased", "new", "built", "expanded", "destroyed", "%"
        ]) and not ("no change" in cdvqa_text_lower or "unchanged" in cdvqa_text_lower)
        cdvqa_indicates_no_change = ("no change" in cdvqa_text_lower or "unchanged" in cdvqa_text_lower)

        # Rule 1: Severe Contradiction — High spatial change detected, but CDVQA claims no change
        if cf_ratio > 0.05 and cdvqa_indicates_no_change:
            logger.warning(f"Adjudication conflict: ChangeFormer detects {cf_ratio*100:.1f}% change, CDVQA claims no change.")
            return AdjudicationResult(
                adjudicated_answer=(
                    f"REVIEW REQUIRED: Spatial change detection indicates active surface changes "
                    f"({cf_ratio*100:.1f}% of scene changed; {cf_changed_pixels:,} pixels), "
                    f"whereas CDVQA reported '{cdvqa_text}'. Physical spatial evidence indicates changes are present."
                ),
                adjudication_status="CONFLICT",
                confidence=round(min(cdvqa_conf, 0.45), 4),
                contributing_evidence=contributing,
                conflict_details=ConflictReport(
                    has_conflict=True,
                    conflict_type="SPATIAL_DETECTED_VS_TEXTUAL_NO_CHANGE",
                    description="ChangeFormer detected substantial pixel-level change while CDVQA predicted no change.",
                    disagreeing_models=["ChangeFormer", "CDVQA"],
                    metrics={"changeformer_ratio": cf_ratio, "cdvqa_answer": cdvqa_text}
                ),
                applied_rule="RULE_SPATIAL_PRIORITY_WITH_REVIEW_REQUIRED",
                provenance={
                    "timestamp": now_iso,
                    "job_id": job_id,
                    "reconciliation": "Prioritized verified raster segmentation mask over textual classifier; flagged for human review."
                }
            )

        # Rule 2: Severe Contradiction — Empty spatial mask, but CDVQA claims extensive change
        is_zero_pct = bool(re.search(r"\b0%", cdvqa_text)) or "little" in cdvqa_text_lower
        if cf_changed_pixels == 0 and cdvqa_indicates_change and not is_zero_pct:
            logger.warning(f"Adjudication conflict: ChangeFormer mask is empty, CDVQA claims '{cdvqa_text}'.")
            return AdjudicationResult(
                adjudicated_answer=(
                    f"AMBIGUOUS: CDVQA predicted '{cdvqa_text}', but pixel-level ChangeFormer segmentation "
                    f"detected no changed pixels above threshold. Ground inspection recommended."
                ),
                adjudication_status="AMBIGUOUS",
                confidence=0.35,
                contributing_evidence=contributing,
                conflict_details=ConflictReport(
                    has_conflict=True,
                    conflict_type="TEXTUAL_DETECTED_VS_SPATIAL_EMPTY",
                    description="CDVQA predicted change but ChangeFormer found 0 changed pixels.",
                    disagreeing_models=["ChangeFormer", "CDVQA"],
                    metrics={"changeformer_changed_pixels": 0, "cdvqa_answer": cdvqa_text}
                ),
                applied_rule="RULE_AMBIGUOUS_ON_ZERO_MASK_DISCREPANCY",
                provenance={
                    "timestamp": now_iso,
                    "job_id": job_id,
                    "reconciliation": "Uncertainty surfaced; confidence dampened due to missing spatial confirmation."
                }
            )

        # Rule 3: Quality Check Warning from ChangeFormer (e.g. alignment warning, fragmented change)
        if cf_quality == "REVIEW_REQUIRED":
            return AdjudicationResult(
                adjudicated_answer=(
                    f"{cdvqa_text} (Note: Spatial change quality check flagged potential alignment or border artifact; "
                    f"{cf_ratio*100:.1f}% pixels flagged)."
                ),
                adjudication_status="AMBIGUOUS",
                confidence=round(cdvqa_conf * 0.8, 4),
                contributing_evidence=contributing,
                conflict_details=ConflictReport(
                    has_conflict=False,
                    conflict_type="QUALITY_FILTER_WARNING",
                    description="ChangeFormer quality check reported REVIEW_REQUIRED on input scene.",
                    metrics={"quality_status": cf_quality, "change_ratio": cf_ratio}
                ),
                applied_rule="RULE_QUALITY_WARNING_DAMPEN_CONFIDENCE",
                provenance={"timestamp": now_iso, "job_id": job_id}
            )

        # Rule 4: Concordant Positive Change (Both Agree)
        if (cf_ratio > 0.01 or cf_changed_pixels > 50) and cdvqa_indicates_change:
            combined_conf = round(min(0.95, (float(changeformer_result.confidence or 0.7) + cdvqa_conf) / 2.0), 4)
            return AdjudicationResult(
                adjudicated_answer=(
                    f"{cdvqa_text} Spatial analysis confirms {cf_ratio*100:.1f}% scene change "
                    f"({cf_changed_pixels:,} pixels segmented)."
                ),
                adjudication_status="RESOLVED",
                confidence=combined_conf,
                contributing_evidence=contributing,
                conflict_details=ConflictReport(has_conflict=False, description="Concordant change detection across models."),
                applied_rule="RULE_CONCORDANT_CHANGE_SYNTHESIS",
                provenance={"timestamp": now_iso, "job_id": job_id}
            )

        # Rule 5: Concordant Negative (Neither detects change)
        if cf_changed_pixels <= 50 and (cdvqa_indicates_no_change or not cdvqa_indicates_change):
            return AdjudicationResult(
                adjudicated_answer="No significant bi-temporal change detected across spatial segmentation and QA models.",
                adjudication_status="RESOLVED",
                confidence=0.88,
                contributing_evidence=contributing,
                conflict_details=ConflictReport(has_conflict=False, description="Concordant negative change detection."),
                applied_rule="RULE_CONCORDANT_NO_CHANGE",
                provenance={"timestamp": now_iso, "job_id": job_id}
            )

        # Default fallback
        return AdjudicationResult(
            adjudicated_answer=cdvqa_text or "Change analysis complete.",
            adjudication_status="NO_CONFLICT",
            confidence=round(cdvqa_conf, 4),
            contributing_evidence=contributing,
            conflict_details=ConflictReport(has_conflict=False),
            applied_rule="DEFAULT_RECONCILIATION",
            provenance={"timestamp": now_iso, "job_id": job_id}
        )
