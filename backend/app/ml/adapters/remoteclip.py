from typing import Any, Dict, List, Optional

import torch
from PIL import Image

from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


class RemoteCLIPAdapter(BaseModelAdapter):
    """
    Adapter for RemoteCLIP: Vision-Language Model for Remote Sensing.

    Supports zero-shot land cover classification and image-text similarity, the
    latter used by the video pipeline to reject detections that do not actually
    match the query (project/pre-demo.md 2.1a).

    The checkpoint is an open_clip ViT-B/32 state dict (302 tensors), so the
    architecture has to be built by open_clip and the weights loaded into it.
    A previous version called torch.load() and kept the resulting dict, which
    left the adapter reporting loaded while holding no model at all.
    """

    ARCH = "ViT-B-32"

    def __init__(self):
        super().__init__("remoteclip")
        self._preprocess = None
        self._tokenizer = None

    def load_model(self) -> None:
        if self._loaded:
            return
        self.ensure_available()
        warn_if_cpu_for_heavy_model(self.name, self.device)
        logger.info(f"Loading RemoteCLIP checkpoint from {self.checkpoint_path}...")

        try:
            import open_clip

            model, _, preprocess = open_clip.create_model_and_transforms(self.ARCH)
            state_dict = torch.load(str(self.checkpoint_path), map_location="cpu", weights_only=False)
            missing, unexpected = model.load_state_dict(state_dict, strict=False)
            if missing:
                logger.warning(f"RemoteCLIP: {len(missing)} missing keys, first few: {missing[:3]}")
            if unexpected:
                logger.warning(f"RemoteCLIP: {len(unexpected)} unexpected keys, first few: {unexpected[:3]}")

            self._model = model.to(self.device).eval()
            self._preprocess = preprocess
            self._tokenizer = open_clip.get_tokenizer(self.ARCH)
            self._loaded = True
            logger.info(
                f"RemoteCLIP {self.ARCH} loaded onto {self.device} "
                f"({len(state_dict)} tensors, {len(missing)} missing, {len(unexpected)} unexpected)."
            )
        except Exception as e:
            logger.error(f"Failed to load RemoteCLIP: {e}")
            raise InferenceError(f"Failed to load RemoteCLIP: {e}", model_name=self.name)

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        if "image_pil" not in context and "image_path" not in context and "image_arr" not in context:
            raise InvalidInputError("RemoteCLIP requires an input image (image_arr, image_pil, or image_path).")

    def _resolve_image(self, context: Dict[str, Any]) -> Image.Image:
        if "image_pil" in context:
            return context["image_pil"].convert("RGB")
        if "image_path" in context:
            return Image.open(context["image_path"]).convert("RGB")
        import numpy as np

        return Image.fromarray(np.asarray(context["image_arr"]).astype("uint8")).convert("RGB")

    @torch.no_grad()
    def _similarities(self, image: Image.Image, texts: List[str]) -> List[float]:
        """Cosine similarity in [0, 1] between the image and each text."""
        img_t = self._preprocess(image).unsqueeze(0).to(self.device)
        tok = self._tokenizer(texts).to(self.device)

        img_f = self._model.encode_image(img_t)
        txt_f = self._model.encode_text(tok)
        img_f = img_f / img_f.norm(dim=-1, keepdim=True)
        txt_f = txt_f / txt_f.norm(dim=-1, keepdim=True)

        # Cosine similarity is in [-1, 1]; map to [0, 1] so callers can use a
        # plain floor. This is a similarity, NOT a calibrated probability.
        cos = (img_f @ txt_f.T).squeeze(0)
        return [float((c + 1.0) / 2.0) for c in cos.detach().cpu()]

    def similarity(self, image: Image.Image, text: str) -> float:
        """Image-text similarity in [0, 1]. Used for detection verification."""
        self.load_model()
        return self._similarities(image, [text])[0]

    def predict(self, context: Dict[str, Any]) -> ModelResult:
        self.validate_inputs(context)
        self.load_model()

        image = self._resolve_image(context)
        candidate_labels: List[str] = context.get(
            "candidate_labels", ["Urban", "Agriculture", "Forest", "Water", "Barren"]
        )
        if not candidate_labels:
            raise InvalidInputError("RemoteCLIP requires at least one candidate label.")

        try:
            scores = self._similarities(image, candidate_labels)
            ranked = sorted(zip(candidate_labels, scores), key=lambda p: p[1], reverse=True)
            top_label, top_score = ranked[0]

            return ModelResult(
                model_name=self.name,
                task="zero_shot_classification",
                answer=f"Zero-shot classification: {top_label}",
                confidence=round(top_score, 4),
                metadata={
                    "candidate_labels": candidate_labels,
                    "scores": {lbl: round(s, 4) for lbl, s in ranked},
                    "score_type": "cosine_similarity_rescaled_0_1",
                    "architecture": self.ARCH,
                    "device": str(self.device),
                },
            )
        except Exception as e:
            logger.error(f"RemoteCLIP inference error: {e}")
            raise InferenceError(f"RemoteCLIP execution failed: {e}", model_name=self.name)
