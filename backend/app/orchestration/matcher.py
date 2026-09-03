"""
SatQuery AI — Capability Matcher & Priority Resolution Engine
Matches extracted user intent, input modality facts, and system capabilities.
Strictly enforces priority precedence (Grounding > generic VQA).
"""
from typing import List, Optional, Tuple
from backend.app.orchestration.schemas import (
    CapabilityDefinition,
    IntentClassificationResult,
    ModalityType,
)
from backend.app.orchestration.capability_registry import capability_registry
from backend.app.orchestration.input_analyzer import InputAnalysisFacts
from backend.app.logging import logger


class CapabilityMatcher:
    """
    Evaluates capabilities against facts and intent, returning the optimal matching capability.
    """

    @classmethod
    def match(
        cls,
        intent: IntentClassificationResult,
        input_facts: InputAnalysisFacts
    ) -> Tuple[CapabilityDefinition, str]:
        """
        Returns (selected_capability, observable_routing_reason)
        """
        all_caps = capability_registry.list_enabled()

        # 1. Video matching
        if input_facts.overall_modality_type == ModalityType.VIDEO:
            target_id = intent.task if intent.task.startswith("video_") else "video_grounding"
            cap = capability_registry.get(target_id) or capability_registry.get("video_grounding")
            reason = f"Video footage input detected with duration {input_facts.video_metadata.get('duration_seconds', 0)}s. Routed to video capability."
            return cap, reason

        # 2. Dual-image matching
        if input_facts.total_files >= 2:
            if input_facts.overall_modality_type == ModalityType.OPTICAL_PLUS_SAR or intent.task == "optical_sar_analysis":
                cap = capability_registry.get("optical_sar_analysis")
                reason = "Dual cross-modal Optical + SAR images provided for sensor fusion."
                return cap, reason

            if intent.task == "temporal_change_vqa":
                cap = capability_registry.get("temporal_change_vqa")
                reason = "Paired bi-temporal images provided with natural-language change query."
                return cap, reason

            cap = capability_registry.get("temporal_change_detection")
            reason = "Paired bi-temporal images provided for change mapping and area quantification."
            return cap, reason

        # 3. Single-image matching
        # PRIORITY RULE: Grounding intent strictly overrides generic VQA
        if intent.task == "single_image_grounding":
            cap = capability_registry.get("single_image_grounding")
            target_obj = intent.extracted_entities.object_class or "target object"
            reason = f"Single image provided with spatial grounding/referral query targeting '{target_obj}'."
            return cap, reason

        if input_facts.overall_modality_type == ModalityType.MULTISPECTRAL_RASTER and intent.task == "multispectral_analysis":
            cap = capability_registry.get("multispectral_analysis")
            reason = "Multispectral raster (>3 bands) provided with spectral index/composite request."
            return cap, reason

        if input_facts.overall_modality_type == ModalityType.SAR_RASTER and intent.task == "sar_analysis":
            cap = capability_registry.get("sar_analysis")
            reason = "SAR radar raster provided with polarimetry analysis request."
            return cap, reason

        if intent.task == "single_image_caption":
            cap = capability_registry.get("single_image_caption")
            reason = "Single image provided with scene captioning/summarization query."
            return cap, reason

        # Default Single Image VQA
        cap = capability_registry.get("single_image_vqa")
        reason = "Single image provided with general natural-language visual inquiry."
        return cap, reason
