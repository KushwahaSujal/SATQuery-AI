from typing import Any, Dict, Optional
from pathlib import Path
import sys
import torch
import numpy as np

from backend.app.models.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger
from backend.app.models.device import warn_if_cpu_for_heavy_model
from backend.app.geo.optical_preprocessing import preprocess_optical_image
from backend.app.geo.sar_preprocessing import SARPreprocessor


class DOFAAdapter(BaseModelAdapter):
    """
    Adapter for DOFA: Dynamic Earth Observation Foundation Model for Multi-Modal Remote Sensing.
    Extracts cross-modal visual representations across optical and SAR bands.
    Architecture: 12-layer Vision Transformer with Dynamic Wavelength-conditioned Patch Embeddings (111M parameters).
    Checkpoint: checkpoints/dofa/DOFA_ViT_base_e100.pth (447 MB)
    """
    def __init__(self):
        super().__init__("dofa")
        self._dofa_model = None

    def load_model(self) -> None:
        if self._loaded:
            return
        self.ensure_available()
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading DOFA checkpoint from {self.checkpoint_path}...")
        
        try:
            dofa_dir = Path("checkpoints/dofa")
            if str(dofa_dir.resolve()) not in sys.path:
                sys.path.insert(0, str(dofa_dir.resolve()))

            from modeling_dofa import DOFAModel, DOFAConfig
            
            config = DOFAConfig.from_pretrained(str(dofa_dir))
            model = DOFAModel(config)
            
            checkpoint_file = Path(self.checkpoint_path)
            if checkpoint_file.exists():
                state_dict = torch.load(str(checkpoint_file), map_location="cpu")
                model.load_state_dict(state_dict, strict=False)

            model.to(self.device)
            model.eval()
            self._dofa_model = model
            self._loaded = True
            logger.info("DOFA foundation model and weights loaded successfully onto %s.", self.device)
        except Exception as e:
            logger.error(f"Failed to load DOFA: {e}")
            raise InferenceError(f"Failed to load DOFA weights: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if "optical_arr" not in context and "sar_arr" not in context and "tensor" not in context:
            raise InvalidInputError("DOFA requires at least one optical or SAR input array or preprocessed tensor.")

    def extract_features(
        self, 
        optical_arr: Optional[np.ndarray] = None, 
        sar_arr: Optional[np.ndarray] = None
    ) -> Dict[str, torch.Tensor]:
        """Extracts optical and SAR feature embeddings from DOFA encoder."""
        self.load_model()
        results: Dict[str, torch.Tensor] = {}

        with torch.no_grad():
            if optical_arr is not None:
                # Preprocess optical to [1, 3, 224, 224]
                opt_tensor = preprocess_optical_image(optical_arr).to(self.device)
                if opt_tensor.shape[-1] != 224 or opt_tensor.shape[-2] != 224:
                    opt_tensor = torch.nn.functional.interpolate(opt_tensor, size=(224, 224), mode="bilinear", align_corners=False)
                # Standard RGB Sentinel-2 central wavelengths in micrometers: B02 (0.49), B03 (0.56), B04 (0.665)
                opt_wavelengths = [0.49, 0.56, 0.665]
                opt_out = self._dofa_model(pixel_values=opt_tensor, wavelengths=opt_wavelengths)
                results["optical_features"] = opt_out.last_hidden_state.squeeze(0).cpu()  # [197, 768]
                results["optical_cls"] = results["optical_features"][0]  # [768]

            if sar_arr is not None:
                # Preprocess SAR to [1, 2, 224, 224] or [1, 3, 224, 224]
                sar_tensor = SARPreprocessor.preprocess_sar(sar_arr).to(self.device)
                if sar_tensor.shape[-1] != 224 or sar_tensor.shape[-2] != 224:
                    sar_tensor = torch.nn.functional.interpolate(sar_tensor, size=(224, 224), mode="bilinear", align_corners=False)
                if sar_tensor.shape[1] == 1:
                    sar_tensor = sar_tensor.repeat(1, 3, 1, 1)
                elif sar_tensor.shape[1] == 2:
                    # Pad to 3 channels for ViT
                    sar_tensor = torch.cat([sar_tensor, sar_tensor[:, :1]], dim=1)
                # Sentinel-1 C-band SAR wavelength (~5.5 cm = 55,000 um)
                sar_wavelengths = [55000.0, 55000.0, 55000.0]
                sar_out = self._dofa_model(pixel_values=sar_tensor, wavelengths=sar_wavelengths)
                results["sar_features"] = sar_out.last_hidden_state.squeeze(0).cpu()  # [197, 768]
                results["sar_cls"] = results["sar_features"][0]  # [768]

        return results

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()

        opt_arr = context.get("optical_arr")
        sar_arr = context.get("sar_arr")

        try:
            feats = self.extract_features(opt_arr, sar_arr)
            meta: Dict[str, Any] = {
                "backbone": "DOFA-ViT-Base-e100",
                "embedding_dim": 768,
                "tokens_count": 197,
            }
            if "optical_features" in feats:
                meta["optical_shape"] = list(feats["optical_features"].shape)
                meta["optical_cls_norm"] = float(torch.norm(feats["optical_cls"]).item())
            if "sar_features" in feats:
                meta["sar_shape"] = list(feats["sar_features"].shape)
                meta["sar_cls_norm"] = float(torch.norm(feats["sar_cls"]).item())

            return ModelResult(
                model_name=self.name,
                task="representation",
                answer="Multi-modal optical and SAR feature representations successfully extracted via DOFA.",
                confidence=1.0 if ("optical_features" in feats or "sar_features" in feats) else 0.0,
                metadata=meta
            )
        except Exception as e:
            logger.error(f"DOFA feature extraction failed: {e}")
            raise InferenceError(f"DOFA execution error: {e}", model_name=self.name)
