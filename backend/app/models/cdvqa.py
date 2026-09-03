import os
from typing import Any, Dict, Optional, List
import torch
import torch.nn.functional as F
from PIL import Image
import torchvision.transforms as T

from pathlib import Path
from backend.app.config import settings
from backend.app.models.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError, ModelUnavailableError
from backend.app.logging import logger
from backend.app.models.device import warn_if_cpu_for_heavy_model
from backend.app.models.cdvqa_model import (
    CDVQAModel,
    CDVQA_ANSWER_CLASSES,
    IDX2ANSWER,
    tokenize_question,
    WORD2IDX
)


# Human-friendly readable mapping for vocabulary tokens
READABLE_ANSWER_MAP: Dict[str, str] = {
    "no": "No change observed.",
    "yes": "Yes, changes are observed.",
    "0": "0% change.",
    "0_to_10": "0% to 10% change.",
    "10_to_20": "10% to 20% change.",
    "20_to_30": "20% to 30% change.",
    "30_to_40": "30% to 40% change.",
    "40_to_50": "40% to 50% change.",
    "50_to_60": "50% to 60% change.",
    "60_to_70": "60% to 70% change.",
    "70_to_80": "70% to 80% change.",
    "80_to_90": "80% to 90% change.",
    "90_to_100": "90% to 100% change.",
    "NVG_surface": "Non-vegetated ground surface.",
    "buildings": "Buildings.",
    "low_vegetation": "Low vegetation.",
    "trees": "Trees / Woodland.",
    "water": "Water bodies.",
    "playgrounds": "Playgrounds / Sports fields."
}


class CDVQAAdapter(BaseModelAdapter):
    """
    Production Adapter for Change Detection Visual Question Answering (CDVQA).
    Executes the verified Siamese ResNet-18 + Change Enhancing Module (CEM) architecture.
    """
    def __init__(self, checkpoint_path: Optional[str] = None):
        super().__init__("cdvqa")
        if checkpoint_path is not None:
            self._checkpoint_path = checkpoint_path

        self.transform = T.Compose([
            T.Resize((256, 256)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def _resolve_checkpoint_path(self) -> Optional[str]:
        env_ckpt = os.getenv("CDVQA_CHECKPOINT")
        if env_ckpt and os.path.exists(env_ckpt):
            return env_ckpt

        if hasattr(self, "_checkpoint_path") and self._checkpoint_path and os.path.exists(self._checkpoint_path):
            return self._checkpoint_path

        candidates = [
            settings.root_dir / "checkpoints" / "cdvqa" / "cdvqa_satquery.pt",
            Path("checkpoints/cdvqa/cdvqa_satquery.pt"),
            self.checkpoint_path,
        ]
        for c in candidates:
            if c and Path(c).is_file():
                return str(c)

        return None

    def is_available(self) -> bool:
        if not self.config or not self.config.enabled:
            return False
        resolved = self._resolve_checkpoint_path()
        return resolved is not None and os.path.isfile(resolved)

    def load_model(self) -> None:
        if self._loaded and self._model is not None:
            return

        ckpt_path = self._resolve_checkpoint_path()
        if not ckpt_path or not os.path.exists(ckpt_path):
            raise ModelUnavailableError(
                "CDVQA model checkpoint is not configured. Please train or place weights at "
                "'checkpoints/cdvqa/cdvqa_satquery.pt'.",
                model_name=self.name
            )

        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading verified CDVQA Siamese ResNet-18+CEM weights from {ckpt_path} onto {self.device}...")

        try:
            device = torch.device(self.device if torch.cuda.is_available() and self.device != "cpu" else "cpu")
            checkpoint = torch.load(ckpt_path, map_location=device)

            model = CDVQAModel(
                num_classes=len(CDVQA_ANSWER_CLASSES),
                vocab_size=len(WORD2IDX),
                feature_dim=512,
                freeze_backbone=True,
                pretrained=False
            ).to(device)

            if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
                model.load_state_dict(checkpoint["state_dict"])
            elif isinstance(checkpoint, dict):
                model.load_state_dict(checkpoint)
            else:
                model = checkpoint

            model.eval()
            self._model = model
            self._loaded = True
            logger.info("CDVQA model loaded and verified successfully.")
        except Exception as e:
            logger.error(f"Failed to load CDVQA model: {e}")
            raise InferenceError(f"Failed to load CDVQA model: {e}", model_name=self.name)

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        self._loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("CDVQA model unloaded.")

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if "image1" not in context or "image2" not in context:
            raise InvalidInputError("CDVQA requires two input images ('image1' and 'image2').")
        if "query" not in context:
            raise InvalidInputError("CDVQA requires a query question.")

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()

        img1_in = context["image1"]
        img2_in = context["image2"]
        query = context["query"]

        if not isinstance(img1_in, Image.Image):
            img1 = Image.fromarray(img1_in).convert("RGB")
        else:
            img1 = img1_in.convert("RGB")

        if not isinstance(img2_in, Image.Image):
            img2 = Image.fromarray(img2_in).convert("RGB")
        else:
            img2 = img2_in.convert("RGB")

        device = next(self._model.parameters()).device

        try:
            t1 = self.transform(img1).unsqueeze(0).to(device)
            t2 = self.transform(img2).unsqueeze(0).to(device)
            q_tokens = tokenize_question(query).unsqueeze(0).to(device)

            with torch.no_grad():
                outputs = self._model(t1, t2, q_tokens)
                logits = outputs["logits"]
                probs = F.softmax(logits, dim=-1)
                conf, pred_idx = torch.max(probs, dim=-1)

                pred_idx_val = int(pred_idx.item())
                confidence_val = float(conf.item())

            raw_answer = IDX2ANSWER.get(pred_idx_val, "unknown")
            answer = READABLE_ANSWER_MAP.get(raw_answer, raw_answer)

            # Optional change attention map for visual explanation
            change_map_2d = None
            if "change_map" in outputs and outputs["change_map"] is not None:
                cm = outputs["change_map"][0, 0].cpu().numpy()
                change_map_2d = cm.tolist()

            return ModelResult(
                model_name=self.name,
                task="change_vqa",
                answer=answer,
                confidence=confidence_val,
                metadata={
                    "query": query,
                    "raw_answer": raw_answer,
                    "answer_class_index": pred_idx_val,
                    "change_map": change_map_2d
                }
            )
        except Exception as e:
            logger.error(f"CDVQA execution failed: {e}")
            raise InferenceError(f"CDVQA execution error: {e}", model_name=self.name)
