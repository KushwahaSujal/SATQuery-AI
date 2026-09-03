from abc import ABC, abstractmethod
from backend.app.agent.state import AgentState
from backend.app.schemas.responses import AnalyzeResponse


class BaseWorkflow(ABC):
    """Abstract base workflow."""
    @abstractmethod
    async def execute(self, state: AgentState) -> AnalyzeResponse:
        pass
