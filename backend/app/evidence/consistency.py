from typing import Any, Dict, List, Optional
import numpy as np
from backend.app.schemas.evidence import ConsistencySignal
from backend.app.schemas.models import ModelResult


class ConsistencyChecker:
    """
    Validates semantic and spatial agreement across multiple models in a workflow.
    Records positive agreement signals or warns of contradictions.
    """
    @staticmethod
    def check_change_consistency(
        change_result: Optional[ModelResult],
        vqa_result: Optional[ModelResult],
        changed_pixels: int
    ) -> List[ConsistencySignal]:
        signals: List[ConsistencySignal] = []

        if change_result and vqa_result:
            has_spatial_change = (changed_pixels > 0)
            vqa_answer_lower = (vqa_result.answer or "").lower()
            
            # Simple keyword matching on change presence
            vqa_indicates_change = any(w in vqa_answer_lower for w in ["change", "increased", "decreased", "new", "built", "expanded", "destroyed", "loss", "growth"])
            vqa_indicates_no_change = any(w in vqa_answer_lower for w in ["no change", "unchanged", "identical", "same"])

            if has_spatial_change and vqa_indicates_change:
                signals.append(ConsistencySignal(
                    signal_type="spatial_vqa_agreement",
                    agreement=True,
                    description="ChangeFormer mask detected spatial changes and CDVQA answer confirmed observed changes.",
                    details={"changed_pixels": changed_pixels}
                ))
            elif not has_spatial_change and vqa_indicates_no_change:
                signals.append(ConsistencySignal(
                    signal_type="spatial_vqa_agreement",
                    agreement=True,
                    description="ChangeFormer detected no significant change, which agrees with CDVQA answer.",
                    details={"changed_pixels": changed_pixels}
                ))
            elif has_spatial_change and vqa_indicates_no_change:
                signals.append(ConsistencySignal(
                    signal_type="spatial_vqa_contradiction",
                    agreement=False,
                    description="Discrepancy: ChangeFormer detected spatial changes but CDVQA reported no change.",
                    details={"changed_pixels": changed_pixels}
                ))

        return signals
