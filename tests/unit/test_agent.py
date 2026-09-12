import pytest
from backend.app.agent.validator import PlanValidator
from backend.app.schemas.agent import WorkflowPlan, TaskType
from backend.app.exceptions import WorkflowError


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
