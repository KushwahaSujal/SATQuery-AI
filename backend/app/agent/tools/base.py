"""
SatQuery AI — Tool contract and self-registering tool registry.

A *tool* is one step the agent can execute. It takes the mutable `AgentState`,
does its work in place, and returns nothing.

Registering a tool is a single decorator on the function — there is no separate
dictionary to keep in sync:

    from backend.app.agent.tools.base import register_tool

    @register_tool("inspect_raster")
    def inspect_raster(state: AgentState) -> None:
        ...

Why a decorator rather than the previous hand-maintained `TOOL_REGISTRY` dict:
a tool used to have to be written *and* added to the dict *and* referenced by a
DAG node. Missing any one of those failed silently — a capability would route
successfully and then quietly do nothing (see project/decisions.md D-104/D-105).
Registration is now impossible to forget, and `validate_registry()` turns the
remaining mismatches into a loud failure at import time.
"""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List

from backend.app.agent.state import AgentState
from backend.app.logging import logger

ToolFn = Callable[[AgentState], None]

#: name -> callable. Populated by @register_tool at import time.
TOOL_REGISTRY: Dict[str, ToolFn] = {}


def register_tool(name: str) -> Callable[[ToolFn], ToolFn]:
    """Registers a function as an agent tool under `name`."""

    def decorator(fn: ToolFn) -> ToolFn:
        if name in TOOL_REGISTRY:
            raise RuntimeError(
                f"Duplicate tool registration for '{name}': "
                f"{TOOL_REGISTRY[name].__module__}.{TOOL_REGISTRY[name].__qualname__} "
                f"and {fn.__module__}.{fn.__qualname__}"
            )
        TOOL_REGISTRY[name] = fn
        return fn

    return decorator


def get_tool(name: str) -> ToolFn:
    """Returns the registered tool, or raises with the full list of valid names."""
    try:
        return TOOL_REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown tool '{name}'. Registered tools: {sorted(TOOL_REGISTRY)}"
        ) from None


def registered_tools() -> List[str]:
    return sorted(TOOL_REGISTRY)


def validate_declared_tools(declared: Iterable[str], source: str) -> None:
    """
    Fails loudly if any declared tool name is not registered.

    Called at import time for every capability definition, so a typo or a tool
    that was never written surfaces at startup rather than as a workflow that
    silently produces nothing.
    """
    missing = sorted({t for t in declared if t not in TOOL_REGISTRY})
    if missing:
        raise RuntimeError(
            f"{source} declares tools that are not registered: {missing}. "
            f"Registered: {sorted(TOOL_REGISTRY)}"
        )


def log_registry_summary() -> None:
    logger.info(f"ToolRegistry initialized with {len(TOOL_REGISTRY)} tools.")
