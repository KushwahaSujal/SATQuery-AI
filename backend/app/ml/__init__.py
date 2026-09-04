"""
SatQuery AI — machine-learning layer.

Everything that touches model weights lives here: the adapter contract
(`base`), the registry, device/concurrency helpers, and one module or package
per model under `adapters/`.
"""
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.registry import ModelRegistry, model_registry

__all__ = ["BaseModelAdapter", "ModelRegistry", "model_registry"]
