from backend.app.workflows.base import BaseWorkflow
from backend.app.agent.state import AgentState
from backend.app.schemas.responses import AnalyzeResponse
from backend.app.agent.controller import agent_controller


class TemporalChangeWorkflow(BaseWorkflow):
    """
    Workflow C: Bi-temporal Change Detection (ChangeFormer) & Change VQA (CDVQA).
    """
    async def execute(self, state: AgentState) -> AnalyzeResponse:
        return await agent_controller.run_pipeline(state)
