import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from backend.app.logging import logger
from backend.app.config import settings


class GPUExecutionLock:
    """
    Global asynchronous lock to ensure heavyweight model inference steps
    do not saturate GPU memory or compute concurrently on constrained devices.
    """
    def __init__(self):
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, model_name: str = "model") -> AsyncGenerator[None, None]:
        timeout = settings.concurrency.gpu_lock_timeout_seconds
        logger.debug(f"Acquiring GPU execution lock for model '{model_name}' (timeout={timeout}s)...")
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            logger.debug(f"GPU lock acquired for '{model_name}'.")
            try:
                yield
            finally:
                self._lock.release()
                logger.debug(f"GPU lock released for '{model_name}'.")
        except asyncio.TimeoutError:
            logger.error(f"Timed out waiting for GPU execution lock for '{model_name}'.")
            raise TimeoutError(f"Inference execution lock timed out after {timeout} seconds.")


# Global inference lock
gpu_lock = GPUExecutionLock()
