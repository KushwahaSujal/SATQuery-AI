"""
SatQuery AI — Orchestrated Workflow Planner
Transforms input files, raster metadata, and user queries into a policy-validated DAG plan.
Provides backward-compatible WorkflowPlan translation while preserving DAG stages.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.agent.state import AgentState
from backend.app.schemas.agent import WorkflowPlan, TaskType
from backend.app.orchestration.schemas import (
    CapabilityDefinition,
    DAGExecutionPlan,
    ExtractedQueryEntities,
    IntentClassificationResult,
)
from backend.app.orchestration.input_analyzer import InputAnalyzer, InputAnalysisFacts
from backend.app.orchestration.intent_classifier import IntentClassifier
from backend.app.orchestration.capability_registry import capability_registry
from backend.app.orchestration.matcher import CapabilityMatcher
from backend.app.orchestration.dependency_graph import DependencyGraph
from backend.app.logging import logger


class OrchestratedPlan(BaseModel):
    """
    Rich orchestration plan combining intent analysis, capability resolution, and execution DAG.
    """
    capability: CapabilityDefinition
    intent: IntentClassificationResult
    input_facts: InputAnalysisFacts
    dag_plan: DAGExecutionPlan
    linear_steps: List[str]
    observable_reason: str
    routing_confidence: float


class AdvancedWorkflowPlanner:
    """
    Main planner for the advanced agent orchestration layer.
    """

    @classmethod
    def plan(cls, state: AgentState) -> OrchestratedPlan:
        """
        Builds an authoritative execution plan from state facts.
        """
        # 1. Analyze inputs
        input_facts, metadata_list = InputAnalyzer.analyze(state.image_paths)
        if metadata_list:
            state.metadata = metadata_list
            state.modalities = input_facts.modalities

        # 2. Classify intent & extract entities
        intent = IntentClassifier.classify_intent(
            query=state.query,
            num_inputs=len(state.image_paths),
            input_types=input_facts.file_types,
            modalities=input_facts.modalities
        )

        # 3. Match capability with explicit priority rules
        capability, reason = CapabilityMatcher.match(intent, input_facts)

        # 4. Build execution DAG
        dag_plan = DependencyGraph.build_dag_for_capability(capability.capability_id)

        # Linear steps for backward compatibility with existing ToolExecutor
        linear_steps = [node.tool_name for node in dag_plan.nodes]

        return OrchestratedPlan(
            capability=capability,
            intent=intent,
            input_facts=input_facts,
            dag_plan=dag_plan,
            linear_steps=linear_steps,
            observable_reason=reason,
            routing_confidence=intent.routing_confidence
        )

    @classmethod
    def to_legacy_workflow_plan(cls, orchestrated_plan: OrchestratedPlan, parameters: Dict[str, Any]) -> WorkflowPlan:
        """
        Converts OrchestratedPlan to legacy WorkflowPlan schema for backward-compatible pipeline execution.
        """
        cap_id = orchestrated_plan.capability.capability_id

        # Map capability_id to legacy TaskType enum
        task_mapping = {
            "single_image_grounding": TaskType.SINGLE_IMAGE_GROUNDING,
            "temporal_change_vqa": TaskType.BI_TEMPORAL_CHANGE_VQA,
            "temporal_change_detection": TaskType.BI_TEMPORAL_CHANGE,
            "optical_sar_analysis": TaskType.OPTICAL_SAR_ANALYSIS,
            "single_image_vqa": TaskType.SINGLE_IMAGE_VQA,
            "single_image_caption": TaskType.SINGLE_IMAGE_CAPTION,
            "video_grounding": TaskType.VIDEO_GROUNDING,
            "video_grounding_tracking": TaskType.VIDEO_GROUNDING_TRACKING,
        }
        legacy_task = task_mapping.get(cap_id, TaskType.UNSUPPORTED)

        return WorkflowPlan(
            workflow_id=orchestrated_plan.capability.workflow,
            task=legacy_task,
            reason=orchestrated_plan.observable_reason,
            selected_models=orchestrated_plan.capability.required_models,
            steps=orchestrated_plan.linear_steps,
            parameters=parameters
        )
