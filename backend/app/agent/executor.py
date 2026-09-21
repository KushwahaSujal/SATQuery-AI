import asyncio
import time
import torch
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
    def _is_cuda_oom(error: BaseException) -> bool:
        seen = set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            if isinstance(error, torch.OutOfMemoryError) or "out of memory" in str(error).lower():
                return True
            error = error.__cause__ or error.__context__
        return False

    @staticmethod
    async def execute_tool(tool_name: str, state: AgentState) -> None:
        """Run one tool.

        The tool functions are synchronous and CPU/GPU bound. Calling them directly from
        this coroutine blocked the event loop for the whole analysis, so every other
        request -- health, job polling, artifact images -- queued behind it and the UI
        looked frozen or broken mid-run. They are dispatched to a worker thread instead.
        GPU concurrency is unchanged: heavy tools still serialize on `gpu_lock`, so
        exactly one runs at a time, as before.
        """
        if tool_name not in TOOL_REGISTRY:
            raise KeyError(f"Tool '{tool_name}' not found in registered tools.")

        tool_func = TOOL_REGISTRY[tool_name]
        start_iso = datetime.utcnow().isoformat() + "Z"
        start_time = time.perf_counter()

        logger.info(f"[{state.request_id}] Executing tool: {tool_name}")

        try:
            if tool_name in SafeToolExecutor.HEAVY_INFERENCE_TOOLS:
                async with gpu_lock.acquire(tool_name):
                    first_error: Optional[str] = None
                    try:
                        await asyncio.to_thread(tool_func, state)
                    except Exception as e:
                        if not SafeToolExecutor._is_cuda_oom(e):
                            raise
                        first_error = str(e)
                    if first_error is not None:
                        # Resident models from earlier queries can exhaust an 8 GB GPU. Release them
                        # all (they reload lazily) and retry once; recorded in the trace, never silent.
                        # This runs outside the except block on purpose: the live exception's
                        # traceback keeps the failed call's frames (model, activations) alive, so
                        # releasing inside it frees nothing.
                        import gc
                        from backend.app.ml.registry import model_registry
                        released = model_registry.release_gpu_memory()
                        gc.collect()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        state.add_trace(
                            step_name=f"GPU memory released after out-of-memory in {tool_name}; retrying once",
                            status="warning",
                            tool=tool_name,
                            details=f"Released: {released}. First error: {first_error[:200]}",
                        )
                        await asyncio.to_thread(tool_func, state)
            else:
                await asyncio.to_thread(tool_func, state)

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
