from .state import AgentState
from .validator import PlanValidator
from .tools import TOOL_REGISTRY, get_tool, register_tool, registered_tools
from .executor import SafeToolExecutor


def __getattr__(name: str):
    # Lazy, to break an import cycle: controller -> planner -> capability_registry, whose start-up check imports
    # this package's tools. Importing the controller eagerly here made `import capability_registry` fail when it
    # came first (tests/unit/test_orchestration_capabilities.py could not be collected; project/qna.md Q-084).
    if name in ("AgentController", "agent_controller"):
        from . import controller
        return getattr(controller, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentState",
    "PlanValidator",
    "TOOL_REGISTRY",
    "get_tool",
    "register_tool",
    "registered_tools",
    "SafeToolExecutor",
    "AgentController",
    "agent_controller",
]
