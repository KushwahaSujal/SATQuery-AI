from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
import torch
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import ModelUnavailableError
from backend.app.config import settings
from backend.app.models.device import get_device, warn_if_cpu_for_heavy_model
from backend.app.logging import logger


class BaseModelAdapter(ABC):
    """
    Abstract base class for all SatQuery AI remote-sensing model adapters.
    Enforces lazy weight loading, strict input validation, real checkpoint verification,
    and safe resource unloading.
    """
    def __init__(self, model_key: str):
        self.model_key = model_key
        self.config = settings.models.get(model_key)
        self.device = get_device(self.config.device if self.config else "auto")
        self._model: Optional[Any] = None
        self._loaded: bool = False
        self._model_id: Optional[str] = None

    @property
    def name(self) -> str:
        return self.config.name if self.config else self.model_key

    @property
    def version(self) -> Optional[str]:
        return self.config.version if self.config else None

    @property
    def available(self) -> bool:
        """Convenience property for is_available()."""
        return self.is_available()

    @property
    def loaded(self) -> bool:
        """Returns True if model weights are currently resident in memory."""
        return bool(self._loaded)

    @property
    def model_id(self) -> Optional[str]:
        """Returns model ID if applicable (e.g. Hugging Face repository name)."""
        if hasattr(self, "_model_id") and self._model_id is not None:
            return self._model_id
        return getattr(self.config, "model_id", None) if self.config else None

    @model_id.setter
    def model_id(self, value: Optional[str]) -> None:
        self._model_id = value

    @property
    def checkpoint_path(self) -> Optional[Path]:
        if hasattr(self, "_checkpoint_path") and self._checkpoint_path is not None:
            return Path(self._checkpoint_path)
        if self.config and self.config.checkpoint_path:
            p = Path(self.config.checkpoint_path)
            if not p.is_absolute():
                p = settings.root_dir / p
            return p
        return None

    @checkpoint_path.setter
    def checkpoint_path(self, value: Optional[Any]) -> None:
        self._checkpoint_path = Path(value) if value is not None else None

    def is_available(self) -> bool:
        """
        Returns True ONLY if model is enabled and its checkpoint file/directory actually exists.
        Never fabricates availability.
        """
        if not self.config or not self.config.enabled:
            return False
        p = self.checkpoint_path
        if p is None:
            return False
        return p.exists()

    def ensure_available(self) -> None:
        """Raises ModelUnavailableError if checkpoint is missing."""
        if not self.is_available():
            p_str = str(self.checkpoint_path) if self.checkpoint_path else "None"
            raise ModelUnavailableError(
                model_name=self.name,
                message=f"Model '{self.name}' is unavailable because its checkpoint was not found at '{p_str}'.",
                details={
                    "model_key": self.model_key,
                    "expected_path": p_str,
                    "enabled": self.config.enabled if self.config else False,
                }
            )

    @abstractmethod
    def load_model(self) -> None:
        """Lazily load checkpoint weights into compute device."""
        pass

    @abstractmethod
    def validate_inputs(self, context: Dict[str, Any]) -> None:
        """Validates that input tensors, arrays, or queries meet model requirements."""
        pass

    @abstractmethod
    def predict(self, context: Dict[str, Any]) -> ModelResult:
        """
        Performs genuine model inference.
        Must return normalized ModelResult and NEVER fabricate fake outputs.
        """
        pass

    def unload(self) -> None:
        """Releases model weights and frees VRAM where possible."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Model '{self.name}' unloaded from {self.device}.")
