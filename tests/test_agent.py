import pytest
from backend.app.agent.state import AgentState
from backend.app.agent.planner import RuleBasedPlanner
from backend.app.agent.validator import PlanValidator
from backend.app.schemas.agent import WorkflowPlan, TaskType
from backend.app.exceptions import WorkflowError


def test_rule_based_planner():
    planner = RuleBasedPlanner()
    state = AgentState(
        request_id="test-req-1",
        query="What changed between these images?",
        image_paths=["t1.tif", "t2.tif"],
        modalities=["optical", "optical"]
    )
    plan = planner.create_plan(state)
    assert plan.task == TaskType.BI_TEMPORAL_CHANGE_VQA
    assert "run_change_detection" in plan.steps


def test_validator_rejects_unauthorized_tool():
    bad_plan = WorkflowPlan(
        workflow_id="bad_flow",
        task=TaskType.SINGLE_IMAGE_VQA,
        reason="Test bad plan",
        selected_models=["general_rs_vlm"],
        steps=["inspect_raster", "unauthorized_shell_command"]
    )
    with pytest.raises(WorkflowError):
        PlanValidator.validate_plan(bad_plan)
