"""
SatQuery AI — Detection verification agent.

A second, independent agent that checks whether a detector's candidate box actually contains the
object the user asked for. Grounding DINO proposes and scores boxes; RemoteCLIP — a different model
trained on different data — scores the same crop against the query label *and* a remote-sensing
vocabulary of alternatives, and returns one of three verdicts:

  VERIFIED      the queried category ranks in the top-k of the vocabulary
  CONTRADICTED  not top-k, and the best match is a different *object* category (e.g. "vehicle"
                when the user asked for "airplane") — the agents disagree, so the caller backtracks
  UNVERIFIED    not top-k, but the best match is only scene context ("road", "parking lot") —
                typical of tiny objects, so it is flagged as unconfirmed rather than rejected

A hard top-k veto was measured and rejected: it discarded 45-67% of real vehicles, and loosening it
to keep vehicles let 27-35% of non-vehicles through (detection_verifier_sweep_20260914.json).

Why contrastive rather than a raw similarity floor: CLIP cosine similarities sit in a narrow band
(mean 0.278 for true labels vs 0.207 for wrong ones on VRSBench crops), so one absolute threshold
does not transfer across categories. Ranking against alternatives does. Measured on 973 VRSBench
ground-truth crops (results/evaluations/remoteclip_verifier_probe_20260914.json):
  raw-similarity AUC 0.928 · contrastive AUC 0.955 (remoteclip_verifier_probe_20260914.json)
  pad 1.0 / min side 96 / top-3 (detection_verifier_3way_20260914.json):
    true label   → verified 80.7%  unverified 6.2%   contradicted 13.2%
    wrong label  → verified 6.3%   unverified 9.6%   contradicted 84.2%
    vehicle crop queried as "airplane" → verified 3.5%

`target_probability` is a softmax over the vocabulary — a relative score, not a calibrated
probability that the detection is correct.

Crops are kept inside the frame (Q-046). The original geometry handed PIL an out-of-bounds box,
which PIL fills with black. Re-measuring the probe above on a rebuilt 973-crop sample, 711 of the
crops (73.1%) left the frame and were 45.5% fabricated by area on average.
See `DetectionVerifier.crop`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from PIL import Image

from backend.app.config import AgentVerificationSettings, settings
from backend.app.logging import logger


VERIFIED = "verified"
UNVERIFIED = "unverified"
CONTRADICTED = "contradicted"


@dataclass
class VerificationVerdict:
    status: str
    accepted: bool
    target_label: str
    target_group: str
    target_probability: float
    target_rank: int
    top_k: int
    top_alternatives: List[Tuple[str, float]] = field(default_factory=list)
    crop_box: List[int] = field(default_factory=list)

    def as_dict(self) -> Dict:
        d = asdict(self)
        d["top_alternatives"] = [{"label": l, "probability": p} for l, p in self.top_alternatives]
        return d


class DetectionVerifier:
    """RemoteCLIP-backed contrastive verifier for detector candidates."""

    def __init__(self, clip_adapter=None, cfg: Optional[AgentVerificationSettings] = None,
                 crop_mode: str = "inset"):
        self.cfg = cfg or settings.agent_verification
        if crop_mode not in self.CROP_MODES:
            raise ValueError(f"crop_mode must be one of {self.CROP_MODES}, got {crop_mode!r}")
        self.crop_mode = crop_mode
        self._clip = clip_adapter
        self._text_cache: Dict[Tuple[str, ...], torch.Tensor] = {}
        self._group_of: Dict[str, str] = {}
        for group in self.cfg.synonyms:
            if not group:
                continue
            key = group[0].lower()
            for member in group:
                self._group_of[member.lower()] = key

    # ------------------------------------------------------------------ helpers
    @property
    def clip(self):
        if self._clip is None:
            from backend.app.ml.registry import model_registry

            self._clip = model_registry.get_adapter("remoteclip")
        return self._clip

    def is_available(self) -> bool:
        if not self.cfg.enabled:
            return False
        try:
            return bool(self.clip.is_available())
        except Exception as e:  # registry/config problems must not break detection
            logger.warning(f"Detection verifier unavailable: {e}")
            return False

    def group_of(self, label: str) -> str:
        label = label.strip().lower().replace("-", " ")
        if label in self._group_of:
            return self._group_of[label]
        # multi-word queries such as "white car": match on any word that names a group
        for word in label.split():
            if word in self._group_of:
                return self._group_of[word]
        return label

    # Crop geometry (Q-046). `Image.crop` fills out-of-bounds coordinates with black — a crop taken
    # 20 px outside a solid 64x64 image comes back 75% exact zeros — so the pre-Q-046 geometry fed
    # RemoteCLIP fabricated pixels whenever the padded square left the frame: 711 of the 973 rebuilt
    # probe crops, 45.5% of the crop by area on average, scored by the encoder as image content.
    # All three geometries were measured on one sample in one process
    # (results/evaluations/verifier_edge_crops_20260921.json):
    #   "inset"  the square side is capped at min(width, height) and the window is translated back
    #            inside the frame. No fabricated pixels; the side, and so the object's scale inside
    #            the crop, is preserved; and the window contains the whole box whenever a square
    #            in-frame window can -- i.e. whenever max(box_w, box_h) <= min(width, height), since
    #            the side is at least the box's longer edge and shifting it in by the overhang cannot
    #            push the box out. A box longer than the image's short side cannot be contained by ANY
    #            square in-frame window, so it is cropped; measured over 576 synthetic boxes across
    #            512x512, 400x300 and 97x640 frames, all 48 non-containing cases were exactly that
    #            impossible geometry and none was a defect (Q-046 §2).
    #            Best true/wrong separation (contrastive AUC 0.9755 vs 0.9626) and the only geometry
    #            that removes the false contradiction from both DISPUTED answers on 05945_0000.png.
    #            This is what ships.
    #   "clamp"  the window edges are clamped: also free of fabricated pixels, but the crop stops
    #            being square and the open_clip transform centre-crops the longer axis away. AUC
    #            0.9725, and it repairs only one of the two 05945 answers.
    #   "pad"    the pre-Q-046 geometry, kept only so the harness can re-measure the old numbers.
    CROP_MODES = ("inset", "clamp", "pad")

    def crop(self, image: Image.Image, box: Sequence[float]) -> Tuple[Image.Image, List[int]]:
        """Square crop around the box with context padding, kept inside the frame."""
        width, height = image.size
        x1, y1, x2, y2 = [float(v) for v in box[:4]]
        side = max(x2 - x1, y2 - y1, 1.0) * (1.0 + self.cfg.crop_pad)
        side = max(side, float(self.cfg.min_crop_side))
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        cb = [int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2)]
        if self.crop_mode == "pad" or (cb[0] >= 0 and cb[1] >= 0 and cb[2] <= width and cb[3] <= height):
            # Already inside the frame: no geometry to repair, and returning the identical box keeps
            # every non-edge measurement bit-identical to the pre-Q-046 numbers.
            return image.crop(tuple(cb)), cb

        if self.crop_mode == "clamp":
            cb = [max(0, cb[0]), max(0, cb[1]), min(width, cb[2]), min(height, cb[3])]
        else:  # "inset"
            s = max(1, min(int(round(side)), width, height))
            left = min(max(int(round(cx - s / 2.0)), 0), width - s)
            top = min(max(int(round(cy - s / 2.0)), 0), height - s)
            cb = [left, top, left + s, top + s]
        return image.crop(tuple(cb)), cb

    @torch.no_grad()
    def _text_features(self, labels: Tuple[str, ...]) -> torch.Tensor:
        if labels not in self._text_cache:
            clip = self.clip
            prompts = [self.cfg.prompt_template.format(label=l) for l in labels]
            feats = clip._model.encode_text(clip._tokenizer(prompts).to(clip.device))
            self._text_cache[labels] = feats / feats.norm(dim=-1, keepdim=True)
        return self._text_cache[labels]

    # --------------------------------------------------------------------- main
    @torch.no_grad()
    def verify(self, image: Image.Image, box: Sequence[float], target_label: str) -> VerificationVerdict:
        clip = self.clip
        clip.load_model()

        target = target_label.strip().lower().replace("-", " ")
        target_group = self.group_of(target)
        labels = list(dict.fromkeys([v.lower() for v in self.cfg.vocabulary] + [target]))
        text = self._text_features(tuple(labels))

        crop_img, crop_box = self.crop(image.convert("RGB"), box)
        img = clip._model.encode_image(clip._preprocess(crop_img).unsqueeze(0).to(clip.device))
        img = img / img.norm(dim=-1, keepdim=True)
        cos = (img @ text.T).squeeze(0).float().cpu().numpy()

        # Collapse synonyms: each group is represented by its best-matching phrasing, so "car" and
        # "vehicle" do not split one vote between them.
        group_cos: Dict[str, float] = {}
        for label, c in zip(labels, cos):
            g = self.group_of(label)
            group_cos[g] = max(group_cos.get(g, -1.0), float(c))
        groups = list(group_cos)
        scale = float(clip._model.logit_scale.exp()) if hasattr(clip._model, "logit_scale") else 100.0
        logits = np.array([group_cos[g] for g in groups]) * scale
        probs = np.exp(logits - logits.max())
        probs = probs / probs.sum()

        order = np.argsort(-probs)
        ranked = [(groups[i], float(probs[i])) for i in order]
        rank = 1 + [g for g, _ in ranked].index(target_group)
        context = {self.group_of(c) for c in self.cfg.context_labels}
        if rank <= self.cfg.top_k:
            status = VERIFIED
        elif ranked[0][0] in context:
            status = UNVERIFIED
        else:
            status = CONTRADICTED
        return VerificationVerdict(
            status=status,
            accepted=status == VERIFIED,
            target_label=target,
            target_group=target_group,
            target_probability=round(float(probs[groups.index(target_group)]), 4),
            target_rank=rank,
            top_k=self.cfg.top_k,
            top_alternatives=[(g, round(p, 4)) for g, p in ranked[:3]],
            crop_box=crop_box,
        )
