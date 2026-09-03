"""
SatQuery AI — Pre-Execution Dependency Checker
Verifies tools, models, checkpoints, inputs, and resources before launching workflows.
Fails fast with structured errors rather than crashing mid-pipeline.
"""
from typing import List, Optional
from backend.app.orchestration.schemas import CapabilityDefinition, DAGPlanNode
from backend.app.agent.registry import TOOL_REGISTRY
from backend.app.models.registry import model_registry
from backend.app.exceptions import SatQueryException
from backend.app.logging import logger


class CapabilityRequirementError(SatQueryException):
    """Raised when a required tool, model, or input condition is not met."""
    def __init__(self, message: str, code: str = "CAPABILITY_REQUIREMENT_FAILED", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class DependencyChecker:
    """
    Validates all dependencies before a workflow begins execution.
    """

    @classmethod
    def verify_plan_dependencies(
        cls,
        capability: CapabilityDefinition,
        nodes: List[DAGPlanNode],
        num_images: int
    ) -> None:
        """
        Validates:
        1. Tool registration
        2. Model registration
        3. Model checkpoint presence (where required)
        4. Input count requirements
        """
        # 1. Input count check
        val_req = capability.validation_requirements
        min_imgs = val_req.get("min_images")
        max_imgs = val_req.get("max_images")

        if min_imgs is not None and num_images < min_imgs:
            raise CapabilityRequirementError(
                f"Capability '{capability.name}' requires at least {min_imgs} image(s), but received {num_images}.",
                code="INPUT_INSUFFICIENT"
            )
        if max_imgs is not None and num_images > max_imgs:
            raise CapabilityRequirementError(
                f"Capability '{capability.name}' accepts at most {max_imgs} image(s), but received {num_images}.",
                code="INPUT_EXCESSIVE"
            )

        # 2. Tool registration check
        for node in nodes:
            if node.tool_name not in TOOL_REGISTRY:
                raise CapabilityRequirementError(
                    f"Tool '{node.tool_name}' required by node '{node.node_id}' is not registered in TOOL_REGISTRY.",
                    code="TOOL_NOT_REGISTERED",
                    status_code=500
                )

        # 3. Model checkpoint check
        for model_name in capability.required_models:
            if not model_registry.is_model_available(model_name):
                # If general_rs_vlm is not configured, we allow graceful fallback in agent state
                if model_name != "general_rs_vlm":
                    raise CapabilityRequirementError(
                        f"Model '{model_name}' required for capability '{capability.name}' is not configured or missing weights on disk.",
                        code="MODEL_NOT_CONFIGURED",
                        status_code=503
                    )

        logger.debug(f"Pre-execution dependency check passed for capability: {capability.capability_id}")
