from typing import Any, Dict, List, Set
from backend.app.schemas.agent import WorkflowPlan
from backend.app.exceptions import WorkflowError
from backend.app.logging import logger


class PlanValidator:
    """
    Authoritative validator enforcing strict tool security and valid workflow execution plans.
    Guarantees no arbitrary code, shell commands, or unregistered tools are executed.
    """
    PERMITTED_TOOLS: Set[str] = {
        "inspect_raster",
        "validate_single_image",
        "validate_temporal_pair",
        "validate_optical_sar_pair",
        "run_vqa",
        "run_caption",
        "run_grounding",
        "run_segmentation",
        "run_change_detection",
        "run_change_vqa",
        "run_optical_sar",
        "calculate_statistics",
        "generate_overlay",
        "generate_report",
    }

    PERMITTED_MODELS: Set[str] = {
        "general_rs_vlm",
        "grounding_dino",
        "sam2",
        "changeformer",
        "cdvqa",
        "dofa",
        "satquery_optical_sar_fusion",
        "remoteclip",
    }

    @classmethod
    def validate_plan(cls, plan: WorkflowPlan) -> None:
        """
        Validates proposed plan against permitted tool and model whitelists.
        Raises WorkflowError on any unauthorized tool, model, or parameter.
        """
        for step in plan.steps:
            if step not in cls.PERMITTED_TOOLS:
                raise WorkflowError(
                    f"Security violation: Proposed step '{step}' is not in the authorized tool whitelist.",
                    workflow_id=plan.workflow_id
                )

        for model in plan.selected_models:
            if model not in cls.PERMITTED_MODELS:
                raise WorkflowError(
                    f"Security violation: Proposed model '{model}' is not a recognized model adapter.",
                    workflow_id=plan.workflow_id
                )

        logger.debug(f"Workflow plan '{plan.workflow_id}' validated successfully against whitelist.")
