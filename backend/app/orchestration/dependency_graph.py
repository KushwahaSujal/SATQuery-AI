"""
SatQuery AI — Workflow Dependency Graph & DAG Engine
Models execution plans as a Directed Acyclic Graph (DAG) with explicit dependency checking
and identification of independent, parallelizable stages.
"""
from typing import Dict, List, Set
from backend.app.orchestration.schemas import (
    DAGExecutionPlan,
    DAGNodeStatus,
    DAGPlanNode,
)
from backend.app.exceptions import WorkflowError
from backend.app.logging import logger


class DependencyGraph:
    """
    Validates, manages, and executes DAG execution plans.
    """

    @classmethod
    def compute_execution_stages(cls, nodes: List[DAGPlanNode]) -> List[List[str]]:
        """
        Computes topological execution stages (waves).
        Nodes in the same stage have all dependencies satisfied by prior stages
        and can be safely executed concurrently if independent.
        """
        node_map: Dict[str, DAGPlanNode] = {n.node_id: n for n in nodes}
        dependencies: Dict[str, Set[str]] = {n.node_id: set(n.dependencies) for n in nodes}

        # Check for non-existent dependencies
        for node_id, deps in dependencies.items():
            for dep in deps:
                if dep not in node_map:
                    raise WorkflowError(
                        f"DAG plan error: Node '{node_id}' depends on non-existent node '{dep}'.",
                        workflow_id="dag_validation"
                    )

        stages: List[List[str]] = []
        completed: Set[str] = set()

        while len(completed) < len(nodes):
            current_stage: List[str] = []
            for node_id, deps in dependencies.items():
                if node_id not in completed and deps.issubset(completed):
                    current_stage.append(node_id)

            if not current_stage:
                unresolved = [n for n in node_map if n not in completed]
                raise WorkflowError(
                    f"Cyclic or unsatisfiable dependency detected in workflow DAG. Remaining: {unresolved}",
                    workflow_id="dag_validation"
                )

            stages.append(current_stage)
            completed.update(current_stage)

        return stages

    #: Capabilities that have a real DAG branch below. Anything not listed here
    #: falls back to a trivial inspect_raster -> generate_report plan, which
    #: produces no meaningful output — see has_branch_for().
    KNOWN_CAPABILITIES = frozenset({
        "single_image_grounding",
        "temporal_change_vqa",
        "temporal_change_detection",
        "single_image_vqa",
        "single_image_caption",
        "optical_sar_analysis",
    })

    @classmethod
    def has_branch_for(cls, capability_id: str) -> bool:
        """True if this capability has a real execution plan rather than the fallback."""
        return capability_id in cls.KNOWN_CAPABILITIES

    @classmethod
    def build_dag_for_capability(cls, capability_id: str) -> DAGExecutionPlan:
        """
        Constructs standard operational DAG for the given capability.
        """
        nodes: List[DAGPlanNode] = []

        if capability_id == "single_image_grounding":
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="validate_single_image", tool_name="validate_single_image", dependencies=["inspect_raster"], timeout_seconds=10.0),
                DAGPlanNode(node_id="run_grounding", tool_name="run_grounding", model_name="grounding_dino", dependencies=["validate_single_image"], timeout_seconds=60.0),
                DAGPlanNode(node_id="run_segmentation", tool_name="run_segmentation", model_name="sam2", dependencies=["run_grounding"], timeout_seconds=60.0),
                DAGPlanNode(node_id="generate_overlay", tool_name="generate_overlay", dependencies=["run_segmentation"], is_parallelizable=True, timeout_seconds=15.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["generate_overlay"], timeout_seconds=20.0),
            ]
        elif capability_id == "temporal_change_vqa":
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="validate_temporal_pair", tool_name="validate_temporal_pair", dependencies=["inspect_raster"], timeout_seconds=10.0),
                DAGPlanNode(node_id="run_change_detection", tool_name="run_change_detection", model_name="changeformer", dependencies=["validate_temporal_pair"], timeout_seconds=90.0),
                DAGPlanNode(node_id="calculate_statistics", tool_name="calculate_statistics", dependencies=["run_change_detection"], is_parallelizable=True, timeout_seconds=15.0),
                DAGPlanNode(node_id="run_change_vqa", tool_name="run_change_vqa", model_name="cdvqa", dependencies=["run_change_detection"], is_parallelizable=True, timeout_seconds=60.0),
                DAGPlanNode(node_id="generate_overlay", tool_name="generate_overlay", dependencies=["run_change_detection"], is_parallelizable=True, timeout_seconds=15.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["calculate_statistics", "run_change_vqa", "generate_overlay"], timeout_seconds=20.0),
            ]
        elif capability_id == "temporal_change_detection":
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="validate_temporal_pair", tool_name="validate_temporal_pair", dependencies=["inspect_raster"], timeout_seconds=10.0),
                DAGPlanNode(node_id="run_change_detection", tool_name="run_change_detection", model_name="changeformer", dependencies=["validate_temporal_pair"], timeout_seconds=90.0),
                DAGPlanNode(node_id="calculate_statistics", tool_name="calculate_statistics", dependencies=["run_change_detection"], is_parallelizable=True, timeout_seconds=15.0),
                DAGPlanNode(node_id="generate_overlay", tool_name="generate_overlay", dependencies=["run_change_detection"], is_parallelizable=True, timeout_seconds=15.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["calculate_statistics", "generate_overlay"], timeout_seconds=20.0),
            ]
        elif capability_id == "single_image_vqa":
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="validate_single_image", tool_name="validate_single_image", dependencies=["inspect_raster"], timeout_seconds=10.0),
                DAGPlanNode(node_id="run_vqa", tool_name="run_vqa", model_name="general_rs_vlm", dependencies=["validate_single_image"], timeout_seconds=60.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["run_vqa"], timeout_seconds=20.0),
            ]
        elif capability_id == "single_image_caption":
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="validate_single_image", tool_name="validate_single_image", dependencies=["inspect_raster"], timeout_seconds=10.0),
                DAGPlanNode(node_id="run_caption", tool_name="run_caption", model_name="general_rs_vlm", dependencies=["validate_single_image"], timeout_seconds=60.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["run_caption"], timeout_seconds=20.0),
            ]
        elif capability_id == "optical_sar_analysis":
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="validate_optical_sar_pair", tool_name="validate_optical_sar_pair", dependencies=["inspect_raster"], timeout_seconds=10.0),
                DAGPlanNode(node_id="run_optical_sar", tool_name="run_optical_sar", model_name="dofa", dependencies=["validate_optical_sar_pair"], timeout_seconds=90.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["run_optical_sar"], timeout_seconds=20.0),
            ]
        else:
            nodes = [
                DAGPlanNode(node_id="inspect_raster", tool_name="inspect_raster", timeout_seconds=15.0),
                DAGPlanNode(node_id="generate_report", tool_name="generate_report", dependencies=["inspect_raster"], timeout_seconds=20.0),
            ]

        stages = cls.compute_execution_stages(nodes)
        total_timeout = sum(max(node.timeout_seconds for node in [n for n in nodes if n.node_id in stage]) for stage in stages)

        return DAGExecutionPlan(
            plan_id=f"plan_{capability_id}",
            workflow_id=f"workflow_{capability_id}",
            capability_id=capability_id,
            nodes=nodes,
            execution_order=stages,
            total_estimated_timeout=round(total_timeout, 1)
        )
