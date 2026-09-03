import torch
from typing import Literal
from backend.app.logging import logger
from backend.app.config import settings

DeviceType = Literal["cuda", "mps", "cpu"]


def get_device(preferred: str = "auto") -> torch.device:
    """
    Selects the optimal torch compute device based on configuration and hardware availability.
    Supports CUDA (NVIDIA), MPS (Apple Silicon), and CPU fallback.
    """
    pref = preferred.lower() if preferred else settings.device.preferred.lower()
    
    if pref == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        logger.warning("CUDA requested but not available. Falling back to CPU.")
        return torch.device("cpu")

    if pref == "mps":
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        logger.warning("MPS requested but not available. Falling back to CPU.")
        return torch.device("cpu")

    if pref == "cpu":
        return torch.device("cpu")

    # Auto detection
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


def warn_if_cpu_for_heavy_model(model_name: str, device: torch.device):
    """Logs a warning if a heavyweight model is being executed on CPU."""
    if device.type == "cpu":
        logger.warning(
            f"Heavy remote sensing model '{model_name}' is running on CPU. "
            "Inference may be slow. Consider configuring a GPU if available."
        )
