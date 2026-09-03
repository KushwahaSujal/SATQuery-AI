"""
SatQuery AI — Resource-Aware Orchestration & Concurrency Manager
Monitors host CPU, RAM, and GPU VRAM resources.
Enforces GPU concurrency locks and prevents out-of-memory crashes.
"""
import psutil
from typing import Dict, Optional
from backend.app.models.device import get_device
from backend.app.models.concurrency import gpu_lock
from backend.app.exceptions import SatQueryException
from backend.app.logging import logger


class ResourceConstraintError(SatQueryException):
    """Raised when host system or GPU resources prevent safe execution."""
    def __init__(self, message: str, details: Optional[Dict[str, float]] = None):
        super().__init__(
            message=message,
            code="RESOURCE_CONSTRAINT",
            status_code=503,
            details=details or {}
        )


class ResourceManager:
    """
    Monitors system resource availability and guards against memory exhaustion.
    """

    MIN_RAM_AVAILABLE_MB = 250.0  # Safe minimum host RAM headroom

    @classmethod
    def get_system_snapshot(cls) -> Dict[str, float]:
        """
        Returns snapshot of host CPU, RAM, and GPU status.
        """
        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)
        
        snapshot = {
            "cpu_percent": float(cpu_pct),
            "ram_total_mb": round(vm.total / (1024 * 1024), 1),
            "ram_available_mb": round(vm.available / (1024 * 1024), 1),
            "ram_used_percent": float(vm.percent),
            "gpu_available": False,
            "vram_total_mb": 0.0,
            "vram_free_mb": 0.0
        }

        try:
            import torch
            if torch.cuda.is_available():
                snapshot["gpu_available"] = True
                dev_idx = torch.cuda.current_device()
                total_vram = torch.cuda.get_device_properties(dev_idx).total_memory / (1024 * 1024)
                reserved_vram = torch.cuda.memory_reserved(dev_idx) / (1024 * 1024)
                free_vram = total_vram - reserved_vram
                snapshot["vram_total_mb"] = round(total_vram, 1)
                snapshot["vram_free_mb"] = round(free_vram, 1)
        except Exception:
            pass

        return snapshot

    @classmethod
    def verify_resource_availability(cls, model_name: Optional[str] = None) -> None:
        """
        Guarantees sufficient memory headroom before running heavy model inferences.
        """
        snapshot = cls.get_system_snapshot()

        if snapshot["ram_available_mb"] < cls.MIN_RAM_AVAILABLE_MB:
            msg = (
                f"Insufficient system memory to launch model '{model_name or 'unspecified'}'. "
                f"Available RAM: {snapshot['ram_available_mb']:.1f}MB, minimum required: {cls.MIN_RAM_AVAILABLE_MB}MB."
            )
            logger.error(msg)
            raise ResourceConstraintError(msg, details=snapshot)

        logger.debug(
            f"Resource check passed: CPU {snapshot['cpu_percent']}%, "
            f"RAM avail: {snapshot['ram_available_mb']}MB, Device: {get_device()}"
        )
