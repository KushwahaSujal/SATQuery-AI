import time
from datetime import datetime
from typing import Optional
from backend.app.agent.state import AgentState
from backend.app.agent.tools import TOOL_REGISTRY
from backend.app.ml.concurrency import gpu_lock
from backend.app.logging import logger


class SafeToolExecutor:
    """
    Executes whitelisted tools sequentially while logging observable execution traces with precise timings.
    Acquires the GPU execution lock for heavy ML inference tools.
    """
    HEAVY_INFERENCE_TOOLS = {
        "run_vqa", "run_caption", "run_grounding", "run_segmentation",
        "run_change_detection", "run_change_vqa", "run_optical_sar"
    }

    @staticmethod
    async def execute_tool(tool_name: str, state: AgentState) -> None:
        if tool_name not in TOOL_REGISTRY:
            raise KeyError(f"Tool '{tool_name}' not found in registered tools.")

        tool_func = TOOL_REGISTRY[tool_name]
        start_iso = datetime.utcnow().isoformat() + "Z"
        start_time = time.perf_counter()

        logger.info(f"[{state.request_id}] Executing tool: {tool_name}")

        try:
            if tool_name in SafeToolExecutor.HEAVY_INFERENCE_TOOLS:
                async with gpu_lock.acquire(tool_name):
                    tool_func(state)
            else:
                tool_func(state)

            end_time = time.perf_counter()
            end_iso = datetime.utcnow().isoformat() + "Z"
            duration_ms = (end_time - start_time) * 1000.0

            state.add_trace(
                step_name=f"Tool executed: {tool_name}",
                status="success",
                tool=tool_name,
                started_at=start_iso,
                completed_at=end_iso,
                duration_ms=round(duration_ms, 2),
                details=f"Completed in {duration_ms:.1f}ms."
            )
        except Exception as e:
            end_time = time.perf_counter()
            end_iso = datetime.utcnow().isoformat() + "Z"
            duration_ms = (end_time - start_time) * 1000.0

            err_msg = str(e)
            logger.error(f"[{state.request_id}] Tool '{tool_name}' failed: {err_msg}")
            state.errors.append(f"Tool '{tool_name}' error: {err_msg}")
            
            state.add_trace(
                step_name=f"Tool failed: {tool_name}",
                status="error",
                tool=tool_name,
                started_at=start_iso,
                completed_at=end_iso,
                duration_ms=round(duration_ms, 2),
                details=err_msg
            )
            raise e
