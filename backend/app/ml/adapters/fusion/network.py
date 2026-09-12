"""
SatQuery AI — Optical-SAR cross-attention fusion network definition.

WARNING: the shipped checkpoint for this network is randomly initialised.
See project/decisions.md D-102 before trusting its output.
"""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, InferenceError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


CLASSES_19 = [
    "Continuous urban fabric",
    "Discontinuous urban fabric",
    "Industrial or commercial units",
    "Road and rail networks",
    "Port areas",
    "Airports",
    "Mineral extraction sites",
    "Dump sites",
    "Construction sites",
    "Non-irrigated arable land",
    "Permanently irrigated land",
    "Rice fields",
    "Vineyards",
    "Fruit trees and berry plantations",
    "Olive groves",
    "Pastures",
    "Annual crops associated with permanent crops",
    "Complex cultivation patterns",
    "Broad-leaved forest"
]


class CrossAttentionFusionNet(nn.Module):
    def __init__(self, embed_dim: int = 768, num_heads: int = 8, num_classes: int = 19):
        super().__init__()
        self.opt_proj = nn.Linear(embed_dim, embed_dim)
        self.sar_proj = nn.Linear(embed_dim, embed_dim)
        self.cross_attn_opt2sar = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.cross_attn_sar2opt = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.ln_opt = nn.LayerNorm(embed_dim)
        self.ln_sar = nn.LayerNorm(embed_dim)
        self.fusion_mlp = nn.Sequential(
            nn.Linear(embed_dim * 2, embed_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(embed_dim, 256),
            nn.GELU(),
            nn.Linear(256, num_classes)
        )
        self.roughness_head = nn.Sequential(
            nn.Linear(embed_dim * 2, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        self.builtup_head = nn.Sequential(
            nn.Linear(embed_dim * 2, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, opt_feat: torch.Tensor, sar_feat: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if opt_feat.dim() == 2:
            opt_feat = opt_feat.unsqueeze(1)
        if sar_feat.dim() == 2:
            sar_feat = sar_feat.unsqueeze(1)
        opt_p = self.opt_proj(opt_feat)
        sar_p = self.sar_proj(sar_feat)
        f_opt, _ = self.cross_attn_opt2sar(opt_p, sar_p, sar_p)
        f_sar, _ = self.cross_attn_sar2opt(sar_p, opt_p, opt_p)
        opt_fused = self.ln_opt(opt_p + f_opt).squeeze(1)
        sar_fused = self.ln_sar(sar_p + f_sar).squeeze(1)
        combined = torch.cat([opt_fused, sar_fused], dim=-1)
        logits = self.fusion_mlp(combined)
        roughness = self.roughness_head(combined)
        builtup = self.builtup_head(combined)
        return logits, roughness, builtup
