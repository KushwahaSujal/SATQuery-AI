"""
SatQuery AI — agent tools.

Importing this package registers every tool via the @register_tool decorator in
its module. Import order is irrelevant; the registry is keyed by name.
"""
from backend.app.agent.tools.base import (
    TOOL_REGISTRY,
    get_tool,
    register_tool,
    registered_tools,
    validate_declared_tools,
    log_registry_summary,
)

# Side-effecting imports: each module registers its tools on import.
from backend.app.agent.tools import raster        # noqa: F401,E402
from backend.app.agent.tools import validation    # noqa: F401,E402
from backend.app.agent.tools import inference     # noqa: F401,E402
from backend.app.agent.tools import evidence      # noqa: F401,E402

log_registry_summary()

__all__ = [
    "TOOL_REGISTRY",
    "get_tool",
    "register_tool",
    "registered_tools",
    "validate_declared_tools",
]
