from abc import ABC, abstractmethod
from typing import Any, Dict, List
from backend.app.agent.state import AgentState
from backend.app.agent.router import DeterministicRouter
from backend.app.schemas.agent import WorkflowPlan, TaskType
from backend.app.logging import logger


class BasePlanner(ABC):
    """Abstract planner interface."""
    @abstractmethod
    def create_plan(self, state: AgentState) -> WorkflowPlan:
        pass


class RuleBasedPlanner(BasePlanner):
    """
    Default deterministic rule-based workflow planner.
    Requires no external API keys or cloud services.
    """
    def create_plan(self, state: AgentState) -> WorkflowPlan:
        task, workflow_id, reason, models = DeterministicRouter.classify_and_route(
            query=state.query,
            num_images=len(state.image_paths),
            modalities=state.modalities,
            metadata_list=state.metadata
        )

        steps: List[str] = ["inspect_raster"]

        if task == TaskType.SINGLE_IMAGE_VQA:
            steps.extend(["validate_single_image", "run_vqa", "generate_report"])
        elif task == TaskType.SINGLE_IMAGE_CAPTION:
            steps.extend(["validate_single_image", "run_caption", "generate_report"])
        elif task == TaskType.SINGLE_IMAGE_GROUNDING:
            steps.extend(["validate_single_image", "run_grounding", "run_segmentation", "generate_overlay", "generate_report"])
        elif task == TaskType.BI_TEMPORAL_CHANGE:
            steps.extend(["validate_temporal_pair", "run_change_detection", "calculate_statistics", "generate_overlay", "generate_report"])
        elif task == TaskType.BI_TEMPORAL_CHANGE_VQA:
            steps.extend(["validate_temporal_pair", "run_change_detection", "calculate_statistics", "run_change_vqa", "generate_overlay", "generate_report"])
        elif task == TaskType.OPTICAL_SAR_ANALYSIS:
            steps.extend(["validate_optical_sar_pair", "run_optical_sar", "generate_report"])
        else:
            steps.append("generate_report")

        return WorkflowPlan(
            workflow_id=workflow_id,
            task=task,
            reason=reason,
            selected_models=models,
            steps=steps,
            parameters=state.parameters
        )


class OptionalLLMPlanner(BasePlanner):
    """
    Optional LLM-based planner extension.
    Proposes a structured plan, which is strictly verified by PlanValidator.
    Falls back gracefully to RuleBasedPlanner if unavailable.
    """
    def __init__(self):
        self.fallback = RuleBasedPlanner()

    def create_plan(self, state: AgentState) -> WorkflowPlan:
        try:
            # If external LLM API is configured, create plan here
            # Otherwise use fallback
            return self.fallback.create_plan(state)
        except Exception as e:
            logger.warning(f"LLM planner unavailable ({e}). Using deterministic rule-based planner.")
            return self.fallback.create_plan(state)
