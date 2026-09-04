"""
End-to-end AgentController pipeline tests.

WHY THIS FILE EXISTS
--------------------
During the S3 tool-registry refactor, renaming a tool function to
`validate_single_image` made it shadow the imported
`geo.validation.validate_single_image`, so the tool called itself with a
RasterMetadata instead of an AgentState. Every workflow broke.

The full suite — 104 tests — passed anyway, because every test exercised units
in isolation and nothing ran the controller end to end.

These tests close that gap. They drive the real pipeline over a real image with
no mocking of the orchestration layer, and assert that it reaches COMPLETED with
no errors. They need no model checkpoints: the VQA path degrades gracefully to a
NOT_CONFIGURED message, which still exercises planning, dependency checking,
resource checking, plan validation, tool execution and evidence/report writing.
"""
import uuid

import pytest
from PIL import Image

from backend.app.agent.controller import agent_controller
from backend.app.agent.state import AgentState
from backend.app.agent.tools import TOOL_REGISTRY
from backend.app.schemas.agent import JobStatus


@pytest.fixture
def sample_image(tmp_path):
    p = tmp_path / "scene.png"
    Image.new("RGB", (256, 256), (90, 110, 90)).save(p)
    return p


async def _run(query: str, paths):
    state = AgentState(
        request_id=f"test-{uuid.uuid4().hex[:8]}",
        query=query,
        image_paths=[str(p) for p in paths],
    )
    return await agent_controller.run_pipeline(state)


async def test_single_image_pipeline_completes(sample_image):
    """A plain single-image query must complete without errors."""
    resp = await _run("What land cover is visible in this scene?", [sample_image])

    assert resp.status == JobStatus.COMPLETED, f"pipeline failed: {resp.errors}"
    assert resp.errors == [], f"unexpected errors: {resp.errors}"
    assert resp.answer, "pipeline produced no answer"


async def test_pipeline_executes_every_planned_tool(sample_image):
    """
    Every tool the planner selects must actually run and succeed.

    This is the assertion that catches a broken tool: a tool raising is recorded
    in the trace with status 'error' while the pipeline may still finish.
    """
    resp = await _run("Describe this satellite image.", [sample_image])

    errored = [
        s.step for s in resp.execution_trace
        if getattr(s, "status", None) == "error"
    ]
    assert not errored, f"tools failed during execution: {errored}"

    executed = {s.tool for s in resp.execution_trace if getattr(s, "tool", None)}
    assert "inspect_raster" in executed
    assert "validate_single_image" in executed


async def test_pipeline_emits_observable_trace(sample_image):
    """The execution trace is the audited deliverable — it must not be empty."""
    resp = await _run("What is in this image?", [sample_image])

    assert len(resp.execution_trace) >= 5
    assert resp.workflow_id and resp.workflow_id != "unknown"
    assert resp.orchestration is not None
    assert 0.0 < resp.orchestration["routing_confidence"] <= 1.0


def test_every_registered_tool_is_callable():
    """Guards against a decorator registering something that is not callable."""
    assert len(TOOL_REGISTRY) == 14
    for name, fn in TOOL_REGISTRY.items():
        assert callable(fn), f"tool '{name}' is not callable"


def test_no_tool_shadows_its_own_imports():
    """
    Regression guard for the S3 shadowing bug.

    A tool function whose name collides with something imported into the same
    module will silently call the wrong thing.
    """
    import ast
    import pathlib

    tools_dir = pathlib.Path(__file__).resolve().parents[2] / "backend/app/agent/tools"
    offenders = {}
    for path in sorted(tools_dir.glob("*.py")):
        tree = ast.parse(path.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.update(a.asname or a.name for a in node.names)
            elif isinstance(node, ast.Import):
                imported.update((a.asname or a.name).split(".")[0] for a in node.names)
        defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        clash = imported & defined
        if clash:
            offenders[path.name] = sorted(clash)

    assert not offenders, f"tool functions shadow imported names: {offenders}"
