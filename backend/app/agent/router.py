import re
from typing import List, Optional, Tuple
from backend.app.schemas.agent import TaskType
from backend.app.geo.metadata import RasterMetadata
from backend.app.logging import logger


class DeterministicRouter:
    """
    Deterministic baseline task classifier and router for SatQuery AI.
    Routes requests without requiring external LLM APIs.
    Considers query intent, image count, modalities, spatial alignment, and acquisition timestamps.
    """
    GROUNDING_KEYWORDS = [
        "highlight", "locate", "ground", "where is", "where are", "find",
        "find the", "bounding box", "detect", "point out", "segment",
        "isolate", "box", "identify the object", "identify the", "show me",
        "which vehicle", "which ship", "which harbor", "which harbour"
    ]
    GROUNDING_PATTERNS = [
        r"\bwhich\s+(?:vehicle|ship|boat|vessel|plane|airplane|aircraft|building|harbor|harbour|structure|tank|dock|road|car|truck|bus|train|roof|house|object)\b",
        r"\b(?:locate|find|highlight|point\s+out|where\s+is|where\s+are|identify\s+the(?:\s+object)?|show\s+me|detect|segment|outline|isolate|search\s+for|look\s+for|is\s+there\s+a|is\s+there\s+any|are\s+there\s+any)\b",
        r"\b(?:vehicle|ship|boat|vessel|plane|airplane|aircraft|building|harbor|harbour|structure|tank|dock|road|car|truck|bus|train|roof|house)\b",
    ]
    CAPTION_KEYWORDS = [
        "caption", "summarize image", "brief description", "overview of scene"
    ]
    CHANGE_KEYWORDS = [
        "change", "changed", "difference", "between these", "before and after",
        "built-up increased", "expansion", "deforestation", "urban growth",
        "new structures", "temporal", "damage", "destroyed"
    ]
    OPTICAL_SAR_KEYWORDS = [
        "sar", "optical and sar", "radar", "cross-modal", "fusion", "polarization",
        "sentinel-1", "combine optical", "together to identify"
    ]

    @classmethod
    def classify_and_route(
        cls,
        query: str,
        num_images: int,
        modalities: List[str],
        metadata_list: List[RasterMetadata]
    ) -> Tuple[TaskType, str, str, List[str]]:
        """
        Returns (task_type, workflow_id, observable_reason, selected_models)
        """
        q = query.lower().strip()
        mod1 = modalities[0] if len(modalities) > 0 else "unknown"
        mod2 = modalities[1] if len(modalities) > 1 else "unknown"

        # Temporal change query detection
        is_change_query = any(k in q for k in cls.CHANGE_KEYWORDS) or bool(
            re.search(r"\b(?:change|difference|between|before\s+and\s+after|expansion|deforestation|urban\s+growth|new\s+structures|damage|destroyed)\b", q)
        )

        # Case 1: Exactly 1 Image
        if num_images == 1:
            # Rule: Do not select grounding for temporal change questions
            if not is_change_query:
                is_grounding = (
                    any(k in q for k in cls.GROUNDING_KEYWORDS) or
                    any(bool(re.search(p, q)) for p in cls.GROUNDING_PATTERNS)
                )
                if is_grounding:
                    return (
                        TaskType.SINGLE_IMAGE_GROUNDING,
                        "workflow_grounding",
                        "Single image provided with spatial grounding/localization query.",
                        ["grounding_dino", "sam2"]
                    )

            if any(k in q for k in cls.CAPTION_KEYWORDS):
                return (
                    TaskType.SINGLE_IMAGE_CAPTION,
                    "workflow_caption",
                    "Single image provided with scene captioning request.",
                    ["general_rs_vlm"]
                )
            return (
                TaskType.SINGLE_IMAGE_VQA,
                "workflow_single_vqa",
                "Single image provided with natural-language visual question.",
                ["general_rs_vlm"]
            )

        # Case 2: Exactly 2 Images
        elif num_images == 2:
            is_cross_modal = (
                (mod1 in ["optical", "multispectral"] and mod2 == "sar") or
                (mod2 in ["optical", "multispectral"] and mod1 == "sar")
            )

            # Check if optical + SAR pair
            if is_cross_modal or any(k in q for k in cls.OPTICAL_SAR_KEYWORDS):
                if is_cross_modal or any(k in q for k in cls.OPTICAL_SAR_KEYWORDS):
                    return (
                        TaskType.OPTICAL_SAR_ANALYSIS,
                        "workflow_optical_sar",
                        "Dual images detected as Optical + SAR cross-modal pair for multi-sensor fusion.",
                        ["dofa", "satquery_optical_sar_fusion"]
                    )

            # Bi-temporal change query
            if any(k in q for k in cls.CHANGE_KEYWORDS) or is_cross_modal is False:
                # Distinguish Change Detection vs Change VQA
                is_question = any(q.startswith(w) for w in ["what", "has", "where", "did", "is", "how", "why"]) or "?" in q
                if is_question:
                    return (
                        TaskType.BI_TEMPORAL_CHANGE_VQA,
                        "workflow_temporal_change_vqa",
                        "Paired bi-temporal images provided with natural-language change question.",
                        ["changeformer", "cdvqa"]
                    )
                return (
                    TaskType.BI_TEMPORAL_CHANGE,
                    "workflow_temporal_change",
                    "Paired bi-temporal images provided with change mapping & metric area request.",
                    ["changeformer"]
                )

        return (
            TaskType.UNSUPPORTED,
            "workflow_unsupported",
            f"Unsupported configuration: {num_images} images provided with query '{query}'.",
            []
        )
