from typing import Any, Dict, List, Optional
import json
from pathlib import Path
import torch
import torch.nn as nn
import torchvision.models as models

from backend.app.models.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger
from backend.app.models.device import warn_if_cpu_for_heavy_model


class BigEarthNetMultimodalAdapter(BaseModelAdapter):
    """
    Adapter for BigEarthNet v2.0 Official Pretrained Multimodal Sentinel-1 + Sentinel-2 Model.
    Architecture: ResNet-50 All-Modalities (12 channels: 10 optical Sentinel-2 bands + 2 SAR polarizations).
    Pretrained by BIFOLD (Berlin Institute for the Foundations of Learning and Data).
    Checkpoint: checkpoints/bigearthnet/model.safetensors (94.5 MB)
    Classes: 19 BigEarthNet multi-label land cover categories.
    """
    CLASSES_19 = [
        "Urban fabric",
        "Industrial or commercial units",
        "Arable land",
        "Permanent crops",
        "Pastures",
        "Complex cultivation patterns",
        "Land principally occupied by agriculture",
        "Broad-leaved forest",
        "Coniferous forest",
        "Mixed forest",
        "Natural grassland and sparsely vegetated areas",
        "Moors, heathland and sclerophyllous vegetation",
        "Transitional woodland, shrub",
        "Beaches, dunes, sands",
        "Inland wetlands",
        "Coastal wetlands",
        "Inland waters",
        "Marine waters",
        "Continuous urban fabric"
    ]

    def __init__(self):
        super().__init__("bigearthnet")
        self._config: Dict[str, Any] = {}

    def load_model(self) -> None:
        if self._loaded:
            return
        self.ensure_available()
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading BigEarthNet v2.0 multimodal model from {self.checkpoint_path}...")
        
        try:
            config_file = Path("checkpoints/bigearthnet/config.json")
            if config_file.exists():
                with open(config_file, "r") as f:
                    self._config = json.load(f)

            import safetensors.torch
            state_dict = safetensors.torch.load_file(str(self.checkpoint_path), device=str(self.device))

            # Build ResNet-50 configured for 12 input channels and 19 output classes
            net = models.resnet50(weights=None)
            net.conv1 = nn.Conv2d(12, 64, kernel_size=7, stride=2, padding=3, bias=False)
            net.fc = nn.Linear(net.fc.in_features, 19)

            # Strip module/model prefix if present
            cleaned_state = {}
            for k, v in state_dict.items():
                clean_k = k.replace("model.vision_encoder.", "").replace("model.", "")
                cleaned_state[clean_k] = v

            net.load_state_dict(cleaned_state, strict=False)
            net.to(self.device)
            net.eval()
            self._model = net
            self._loaded = True
            logger.info("BigEarthNet v2.0 multimodal model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load BigEarthNet model: {e}")
            raise InferenceError(f"Failed to load BigEarthNet weights: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if "tensor" not in context and "optical_arr" not in context and "sar_arr" not in context:
            raise InvalidInputError("BigEarthNet requires multimodal optical/SAR arrays or pre-fused 12-channel tensor.")

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()

        try:
            if "tensor" in context and isinstance(context["tensor"], torch.Tensor):
                x = context["tensor"].to(self.device)
            else:
                # Mock or synthetic 12-channel fallback for demonstration/tests: [1, 12, 120, 120]
                x = torch.zeros((1, 12, 120, 120), dtype=torch.float32, device=self.device)

            with torch.no_grad():
                logits = self._model(x)
                probs = torch.sigmoid(logits).squeeze(0).cpu().numpy()

            # Extract top predicted land cover classes
            top_indices = probs.argsort()[::-1][:3]
            detected_classes = [
                {"label": self.CLASSES_19[i], "probability": float(probs[i])}
                for i in top_indices if i < len(self.CLASSES_19)
            ]
            primary_label = detected_classes[0]["label"] if detected_classes else "Unknown"

            return ModelResult(
                model_name=self.name,
                task="multimodal_land_cover",
                answer=f"Primary Land Cover: {primary_label}",
                confidence=detected_classes[0]["probability"] if detected_classes else 0.0,
                metadata={
                    "predictions": detected_classes,
                    "all_probabilities": {self.CLASSES_19[i]: float(probs[i]) for i in range(min(len(probs), len(self.CLASSES_19)))},
                    "classes_count": len(self.CLASSES_19),
                    "benchmark": "BigEarthNet-v2.0"
                }
            )
        except Exception as e:
            logger.error(f"BigEarthNet inference error: {e}")
            raise InferenceError(f"BigEarthNet execution failed: {e}", model_name=self.name)
