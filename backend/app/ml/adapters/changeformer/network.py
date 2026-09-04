"""
SatQuery AI — ChangeFormerV6 network definition.

Pure architecture: MiT Siamese encoder + difference decoder. No I/O, no
checkpoint handling — see adapter.py for that.
"""
from typing import Any, Dict, Optional, Tuple, Union, List
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from PIL import Image

from backend.app.ml.base import BaseModelAdapter
from backend.app.schemas.models import ModelResult
from backend.app.exceptions import InvalidInputError, ModelUnavailableError, InferenceError
from backend.app.logging import logger
from backend.app.ml.device import warn_if_cpu_for_heavy_model


# ============================================================================
# ChangeFormerV6 Architecture (Exact Training Specification)
# ============================================================================

class OverlapPatchEmbed(nn.Module):
    def __init__(self, patch_size: int = 7, stride: int = 4, in_chans: int = 3, embed_dim: int = 768):
        super().__init__()
        self.proj = nn.Conv2d(
            in_chans,
            embed_dim,
            kernel_size=patch_size,
            stride=stride,
            padding=patch_size // 2
        )
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, int, int]:
        x = self.proj(x)
        _, _, H, W = x.shape
        x = x.flatten(2).transpose(1, 2)
        x = self.norm(x)
        return x, H, W


class DWConv(nn.Module):
    def __init__(self, dim: int = 768):
        super().__init__()
        self.dwconv = nn.Conv2d(dim, dim, 3, 1, 1, bias=True, groups=dim)

    def forward(self, x: torch.Tensor, H: int, W: int) -> torch.Tensor:
        B, N, C = x.shape
        x = x.transpose(1, 2).view(B, C, H, W)
        x = self.dwconv(x)
        x = x.flatten(2).transpose(1, 2)
        return x


class Mlp(nn.Module):
    def __init__(self, in_features: int, hidden_features: Optional[int] = None, out_features: Optional[int] = None,
                 act_layer: Any = nn.GELU, drop: float = 0.0):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.dwconv = DWConv(hidden_features)
        self.act = act_layer()
        self.fc2 = nn.Linear(hidden_features, out_features)
        self.drop = nn.Dropout(drop)

    def forward(self, x: torch.Tensor, H: int, W: int) -> torch.Tensor:
        x = self.fc1(x)
        x = self.dwconv(x, H, W)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.drop(x)
        return x


class Attention(nn.Module):
    def __init__(self, dim: int, num_heads: int = 8, qkv_bias: bool = True, qk_scale: Optional[float] = None,
                 attn_drop: float = 0.0, proj_drop: float = 0.0, sr_ratio: int = 1):
        super().__init__()
        assert dim % num_heads == 0, f"dim {dim} should be divisible by num_heads {num_heads}"
        self.dim = dim
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = qk_scale or head_dim ** -0.5

        self.q = nn.Linear(dim, dim, bias=qkv_bias)
        self.kv = nn.Linear(dim, dim * 2, bias=qkv_bias)
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(proj_drop)

        self.sr_ratio = sr_ratio
        if sr_ratio > 1:
            self.sr = nn.Conv2d(dim, dim, kernel_size=sr_ratio, stride=sr_ratio)
            self.norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor, H: int, W: int) -> torch.Tensor:
        B, N, C = x.shape
        q = self.q(x).reshape(B, N, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)

        if self.sr_ratio > 1:
            x_ = x.permute(0, 2, 1).reshape(B, C, H, W)
            x_ = self.sr(x_).reshape(B, C, -1).permute(0, 2, 1)
            x_ = self.norm(x_)
            kv = self.kv(x_).reshape(B, -1, 2, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        else:
            kv = self.kv(x).reshape(B, -1, 2, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        k, v = kv[0], kv[1]

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        return x


class Block(nn.Module):
    def __init__(self, dim: int, num_heads: int, mlp_ratio: float = 4.0, qkv_bias: bool = True,
                 qk_scale: Optional[float] = None, drop: float = 0.0, attn_drop: float = 0.0,
                 act_layer: Any = nn.GELU, norm_layer: Any = nn.LayerNorm, sr_ratio: int = 1):
        super().__init__()
        self.norm1 = norm_layer(dim)
        self.attn = Attention(
            dim, num_heads=num_heads, qkv_bias=qkv_bias, qk_scale=qk_scale,
            attn_drop=attn_drop, proj_drop=drop, sr_ratio=sr_ratio
        )
        self.norm2 = norm_layer(dim)
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = Mlp(in_features=dim, hidden_features=mlp_hidden_dim, act_layer=act_layer, drop=drop)

    def forward(self, x: torch.Tensor, H: int, W: int) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), H, W)
        x = x + self.mlp(self.norm2(x), H, W)
        return x


class MixVisionTransformer(nn.Module):
    """
    Siamese MiT-B2 encoder backbone used in ChangeFormerV6.
    """
    def __init__(self, in_chans: int = 3, embed_dims: list = [64, 128, 320, 512],
                 num_heads: list = [1, 2, 5, 8], mlp_ratios: list = [4, 4, 4, 4],
                 qkv_bias: bool = True, qk_scale: Optional[float] = None, drop_rate: float = 0.0,
                 attn_drop_rate: float = 0.0, norm_layer: Any = nn.LayerNorm,
                 depths: list = [3, 3, 4, 3], sr_ratios: list = [8, 4, 2, 1]):
        super().__init__()
        self.patch_embed1 = OverlapPatchEmbed(patch_size=7, stride=4, in_chans=in_chans, embed_dim=embed_dims[0])
        self.patch_embed2 = OverlapPatchEmbed(patch_size=7, stride=2, in_chans=embed_dims[0], embed_dim=embed_dims[1])
        self.patch_embed3 = OverlapPatchEmbed(patch_size=7, stride=2, in_chans=embed_dims[1], embed_dim=embed_dims[2])
        self.patch_embed4 = OverlapPatchEmbed(patch_size=7, stride=2, in_chans=embed_dims[2], embed_dim=embed_dims[3])

        self.block1 = nn.ModuleList([
            Block(
                dim=embed_dims[0], num_heads=num_heads[0], mlp_ratio=mlp_ratios[0], qkv_bias=qkv_bias,
                qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, norm_layer=norm_layer,
                sr_ratio=sr_ratios[0]
            ) for _ in range(depths[0])
        ])
        self.norm1 = norm_layer(embed_dims[0])

        self.block2 = nn.ModuleList([
            Block(
                dim=embed_dims[1], num_heads=num_heads[1], mlp_ratio=mlp_ratios[1], qkv_bias=qkv_bias,
                qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, norm_layer=norm_layer,
                sr_ratio=sr_ratios[1]
            ) for _ in range(depths[1])
        ])
        self.norm2 = norm_layer(embed_dims[1])

        self.block3 = nn.ModuleList([
            Block(
                dim=embed_dims[2], num_heads=num_heads[2], mlp_ratio=mlp_ratios[2], qkv_bias=qkv_bias,
                qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, norm_layer=norm_layer,
                sr_ratio=sr_ratios[2]
            ) for _ in range(depths[2])
        ])
        self.norm3 = norm_layer(embed_dims[2])

        self.block4 = nn.ModuleList([
            Block(
                dim=embed_dims[3], num_heads=num_heads[3], mlp_ratio=mlp_ratios[3], qkv_bias=qkv_bias,
                qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, norm_layer=norm_layer,
                sr_ratio=sr_ratios[3]
            ) for _ in range(depths[3])
        ])
        self.norm4 = norm_layer(embed_dims[3])

    def forward(self, x: torch.Tensor) -> list:
        B = x.shape[0]
        out = []

        # Stage 1: 1/4 resolution
        x, H, W = self.patch_embed1(x)
        for blk in self.block1:
            x = blk(x, H, W)
        x = self.norm1(x)
        x1 = x.reshape(B, H, W, -1).permute(0, 3, 1, 2).contiguous()
        out.append(x1)

        # Stage 2: 1/8 resolution
        x, H, W = self.patch_embed2(x1)
        for blk in self.block2:
            x = blk(x, H, W)
        x = self.norm2(x)
        x2 = x.reshape(B, H, W, -1).permute(0, 3, 1, 2).contiguous()
        out.append(x2)

        # Stage 3: 1/16 resolution
        x, H, W = self.patch_embed3(x2)
        for blk in self.block3:
            x = blk(x, H, W)
        x = self.norm3(x)
        x3 = x.reshape(B, H, W, -1).permute(0, 3, 1, 2).contiguous()
        out.append(x3)

        # Stage 4: 1/32 resolution
        x, H, W = self.patch_embed4(x3)
        for blk in self.block4:
            x = blk(x, H, W)
        x = self.norm4(x)
        x4 = x.reshape(B, H, W, -1).permute(0, 3, 1, 2).contiguous()
        out.append(x4)

        return out


class MLP(nn.Module):
    def __init__(self, input_dim: int = 2048, embed_dim: int = 768):
        super().__init__()
        self.proj = nn.Linear(input_dim, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.flatten(2).transpose(1, 2)
        x = self.proj(x)
        return x


class ConvTransposed(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, ksize: int = 4, stride: int = 2, pad: int = 1):
        super().__init__()
        self.conv2d = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=ksize, stride=stride, padding=pad)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv2d(x)


class Conv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, ksize: int = 3, stride: int = 1, pad: int = 1):
        super().__init__()
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size=ksize, stride=stride, padding=pad)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv2d(x)


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = Conv(channels, channels, 3, 1, 1)
        self.conv2 = Conv(channels, channels, 3, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.conv1(x))
        out = self.conv2(out)
        out = out + residual
        return F.relu(out)


class Decoder(nn.Module):
    """
    Difference & fusion decoder of ChangeFormerV6.
    """
    def __init__(self, embed_dims: list = [64, 128, 320, 512], decoder_dim: int = 256, num_classes: int = 2):
        super().__init__()
        self.linear_c1 = MLP(embed_dims[0], decoder_dim)
        self.linear_c2 = MLP(embed_dims[1], decoder_dim)
        self.linear_c3 = MLP(embed_dims[2], decoder_dim)
        self.linear_c4 = MLP(embed_dims[3], decoder_dim)

        self.diff_c1 = nn.Sequential(
            nn.Conv2d(decoder_dim * 2, decoder_dim, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(decoder_dim),
            nn.Conv2d(decoder_dim, decoder_dim, 3, padding=1)
        )
        self.diff_c2 = nn.Sequential(
            nn.Conv2d(decoder_dim * 2, decoder_dim, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(decoder_dim),
            nn.Conv2d(decoder_dim, decoder_dim, 3, padding=1)
        )
        self.diff_c3 = nn.Sequential(
            nn.Conv2d(decoder_dim * 2, decoder_dim, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(decoder_dim),
            nn.Conv2d(decoder_dim, decoder_dim, 3, padding=1)
        )
        self.diff_c4 = nn.Sequential(
            nn.Conv2d(decoder_dim * 2, decoder_dim, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(decoder_dim),
            nn.Conv2d(decoder_dim, decoder_dim, 3, padding=1)
        )

        self.make_pred_c1 = nn.Sequential(
            nn.Conv2d(decoder_dim, num_classes, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(num_classes),
            nn.Conv2d(num_classes, num_classes, 3, padding=1)
        )
        self.make_pred_c2 = nn.Sequential(
            nn.Conv2d(decoder_dim, num_classes, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(num_classes),
            nn.Conv2d(num_classes, num_classes, 3, padding=1)
        )
        self.make_pred_c3 = nn.Sequential(
            nn.Conv2d(decoder_dim, num_classes, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(num_classes),
            nn.Conv2d(num_classes, num_classes, 3, padding=1)
        )
        self.make_pred_c4 = nn.Sequential(
            nn.Conv2d(decoder_dim, num_classes, 3, padding=1),
            nn.ReLU(),
            nn.BatchNorm2d(num_classes),
            nn.Conv2d(num_classes, num_classes, 3, padding=1)
        )

        self.linear_fuse = nn.Sequential(
            nn.Conv2d(decoder_dim * 4, decoder_dim, 1),
            nn.BatchNorm2d(decoder_dim),
            nn.ReLU()
        )

        self.convd2x = ConvTransposed(decoder_dim, decoder_dim, 4, 2, 1)
        self.dense_2x = nn.Sequential(ResidualBlock(decoder_dim))

        self.convd1x = ConvTransposed(decoder_dim, decoder_dim, 4, 2, 1)
        self.dense_1x = nn.Sequential(ResidualBlock(decoder_dim))

        self.change_probability = Conv(decoder_dim, num_classes, 3, 1, 1)

    def forward(self, features_a: list, features_b: list) -> torch.Tensor:
        B = features_a[0].shape[0]

        c1_a, c2_a, c3_a, c4_a = features_a
        c1_b, c2_b, c3_b, c4_b = features_b

        h1, w1 = c1_a.shape[2], c1_a.shape[3]
        h2, w2 = c2_a.shape[2], c2_a.shape[3]
        h3, w3 = c3_a.shape[2], c3_a.shape[3]
        h4, w4 = c4_a.shape[2], c4_a.shape[3]

        _c1_a = self.linear_c1(c1_a).permute(0, 2, 1).reshape(B, -1, h1, w1)
        _c1_b = self.linear_c1(c1_b).permute(0, 2, 1).reshape(B, -1, h1, w1)
        _c2_a = self.linear_c2(c2_a).permute(0, 2, 1).reshape(B, -1, h2, w2)
        _c2_b = self.linear_c2(c2_b).permute(0, 2, 1).reshape(B, -1, h2, w2)
        _c3_a = self.linear_c3(c3_a).permute(0, 2, 1).reshape(B, -1, h3, w3)
        _c3_b = self.linear_c3(c3_b).permute(0, 2, 1).reshape(B, -1, h3, w3)
        _c4_a = self.linear_c4(c4_a).permute(0, 2, 1).reshape(B, -1, h4, w4)
        _c4_b = self.linear_c4(c4_b).permute(0, 2, 1).reshape(B, -1, h4, w4)

        # Multi-scale differences
        d1 = self.diff_c1(torch.cat([_c1_a, _c1_b], dim=1))
        d2 = self.diff_c2(torch.cat([_c2_a, _c2_b], dim=1))
        d3 = self.diff_c3(torch.cat([_c3_a, _c3_b], dim=1))
        d4 = self.diff_c4(torch.cat([_c4_a, _c4_b], dim=1))

        # Upsample all differences to Stage 1 resolution
        d4_up = F.interpolate(d4, size=(h1, w1), mode="bilinear", align_corners=False)
        d3_up = F.interpolate(d3, size=(h1, w1), mode="bilinear", align_corners=False)
        d2_up = F.interpolate(d2, size=(h1, w1), mode="bilinear", align_corners=False)

        fuse = self.linear_fuse(torch.cat([d1, d2_up, d3_up, d4_up], dim=1))

        # 2x Transposed Convolution + Residual refinement
        u1 = self.convd2x(fuse)
        u1 = self.dense_2x(u1)

        # 2x Transposed Convolution + Residual refinement
        u2 = self.convd1x(u1)
        u2 = self.dense_1x(u2)

        change_logits = self.change_probability(u2)
        return change_logits


class ChangeFormerV6(nn.Module):
    """
    ChangeFormerV6: Complete Siamese Transformer architecture for change detection.
    Matches the exact 373-tensor state dictionary in satquery_changeformer_best.pt.
    """
    def __init__(self):
        super().__init__()
        self.Tenc_x2 = MixVisionTransformer(
            embed_dims=[64, 128, 320, 512],
            num_heads=[1, 2, 5, 8],
            mlp_ratios=[4, 4, 4, 4],
            qkv_bias=True,
            depths=[3, 3, 4, 3],
            sr_ratios=[8, 4, 2, 1]
        )
        self.TDec_x2 = Decoder(embed_dims=[64, 128, 320, 512], decoder_dim=256, num_classes=2)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        feat1 = self.Tenc_x2(x1)
        feat2 = self.Tenc_x2(x2)
        return self.TDec_x2(feat1, feat2)
