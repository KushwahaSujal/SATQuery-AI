"""The 16-channel U-Net architecture behind Ayushman's Sen1Floods11 flood segmenter.

Reconstructed from the delivered checkpoint's own state_dict rather than from training code (the
training script was not part of the delivery — only `best.pt`, `last.pt`, metadata and evaluation
reports; see docs/models/flood/). Every layer name, shape and bias flag below was read off the 118
entries in `best.pt["model_state_dict"]`, and `load_state_dict(..., strict=True)` in
`FloodSegmenterAdapter.load_model` is what proves the reconstruction is exact: a single wrong
channel count or a spurious bias makes it fail loudly rather than serve wrong numbers.

The cautionary precedent is `backend/app/ml/adapters/changeformer/network.py`: a reimplementation
there matched all 373 parameter names and loaded strict=True, yet measured IoU 0.019 against 0.726
because `num_heads` differed. Parameter-name agreement is necessary, not sufficient.

**Numerical confirmation, added 2026-09-21 (project/qna.md Q-044).** The delivery never documented
the training-time normalisation, and an earlier label-based search over 17 candidate schemes failed to
reproduce the delivered test IoU of 0.6292 (Q-041 §5). It has since been recovered *without* labels, by
treating the checkpoint's 18 BatchNorm layers as a fingerprint of the training-time input distribution
— see `normalise_flood_input` below. Under the recovered preprocessing the reconstruction scores
**global flood IoU 0.6244 / F1 0.7684** on the official 90-scene Sen1Floods11 test split against the
delivery's **0.6292 / 0.7724** on its own 67-scene subset, and reproduces the delivered threshold
response in both direction and magnitude. That is a reproduction, so the reconstruction is now
confirmed numerically and not only by `strict=True`.

It is still an *inference* about what training did, not a statement from the author. Serving therefore
stays gated: see `FloodSegmenterAdapter` and `configs/models.yaml`'s `preprocessing` key.

Channel order is fixed by training and must not be reordered (docs/models/flood/README.md):
    0    Sentinel-1 VV          (gamma0, dB)
    1    Sentinel-1 VH          (gamma0, dB)
    2-14 Sentinel-2 L1C B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B10,B11,B12
    15   Copernicus DEM         (metres)
"""
from typing import Optional

import torch
import torch.nn as nn

#: Channel count the checkpoint's first convolution demands.
FLOOD_INPUT_CHANNELS = 16

#: Four 2x max-pools with no padding in the skip concatenations, so each spatial extent must be a
#: multiple of 2**4. Training used 512x512.
_SIZE_DIVISOR = 16

#: Band order, for error messages and for the adapter's metadata.
FLOOD_CHANNEL_NAMES = (
    "S1_VV", "S1_VH",
    "S2_B1", "S2_B2", "S2_B3", "S2_B4", "S2_B5", "S2_B6",
    "S2_B7", "S2_B8", "S2_B8A", "S2_B9", "S2_B10", "S2_B11", "S2_B12",
    "DEM",
)


#: The per-scene percentile pair recovered from the model's own BatchNorm statistics (Q-044).
FLOOD_CLIP_PERCENTILE = 2.0


def normalise_flood_input(x: "np.ndarray", percentile: float = FLOOD_CLIP_PERCENTILE) -> "np.ndarray":
    """Scale each of the 16 channels into [0, 1] using its own per-scene percentile range.

    **This preprocessing was recovered, not supplied.** The delivery never documented it. It was
    identified by treating the checkpoint's 18 BatchNorm layers as a fingerprint of the training-time
    input distribution: each stores `running_mean`/`running_var` estimated from its own input during
    training, so the normalisation that reproduces those statistics across the whole stack is the one
    training used. Selection used only the TRAIN split and no labels at all; see
    `scripts/flood_preproc_recovery/flood_bn_fingerprint_all_layers.py` and project/qna.md Q-044.

    Percentiles are nan-aware and non-finite pixels are replaced *after* scaling: 6 of the 90 official
    test scenes carry NaN in the Sentinel-1 bands (one entirely NaN), and a plain `np.percentile`
    returns NaN for such a channel, which silently poisons the whole scene. That bug invalidated part
    of the earlier label-based search (Q-044 §2).
    """
    import numpy as np

    if x.ndim != 3 or x.shape[0] != FLOOD_INPUT_CHANNELS:
        raise ValueError(
            f"Expected ({FLOOD_INPUT_CHANNELS}, H, W), got {tuple(x.shape)}."
        )
    flat = x.reshape(FLOOD_INPUT_CHANNELS, -1)
    if percentile <= 0.0:
        lo = np.nanmin(flat, axis=1)
        hi = np.nanmax(flat, axis=1)
    else:
        lo = np.nanpercentile(flat, percentile, axis=1)
        hi = np.nanpercentile(flat, 100.0 - percentile, axis=1)
    lo = np.nan_to_num(lo).reshape(-1, 1, 1)
    hi = np.nan_to_num(hi).reshape(-1, 1, 1)
    y = (x - lo) / np.maximum(hi - lo, 1e-6)
    y = np.clip(y, 0.0, 1.0)
    return np.nan_to_num(y, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)


class DoubleConv(nn.Module):
    """Conv-BN-ReLU twice, both convolutions 3x3 with padding 1 and no bias.

    Indices matter: the checkpoint stores `block.0` / `block.3` as the convolutions and `block.1` /
    `block.4` as the BatchNorms, so the ReLUs must sit at 2 and 5 for the state_dict to line up.
    """

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UNetFromScratch(nn.Module):
    """U-Net, `base_channels` 16, four down/up stages, 2-class logits at full resolution.

    Widths are not free parameters: the checkpoint fixes them at 16, 32, 64, 128 with a 256-channel
    bottleneck, and `output_layer` is a 1x1 convolution to `num_classes`.
    """

    def __init__(
        self,
        in_channels: int = FLOOD_INPUT_CHANNELS,
        num_classes: int = 2,
        base_channels: int = 16,
    ) -> None:
        super().__init__()
        c1 = base_channels
        c2, c3, c4, c5 = c1 * 2, c1 * 4, c1 * 8, c1 * 16

        self.encoder1 = DoubleConv(in_channels, c1)
        self.encoder2 = DoubleConv(c1, c2)
        self.encoder3 = DoubleConv(c2, c3)
        self.encoder4 = DoubleConv(c3, c4)
        self.bottleneck = DoubleConv(c4, c5)

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        self.up4 = nn.ConvTranspose2d(c5, c4, kernel_size=2, stride=2)
        self.decoder4 = DoubleConv(c4 * 2, c4)
        self.up3 = nn.ConvTranspose2d(c4, c3, kernel_size=2, stride=2)
        self.decoder3 = DoubleConv(c3 * 2, c3)
        self.up2 = nn.ConvTranspose2d(c3, c2, kernel_size=2, stride=2)
        self.decoder2 = DoubleConv(c2 * 2, c2)
        self.up1 = nn.ConvTranspose2d(c2, c1, kernel_size=2, stride=2)
        self.decoder1 = DoubleConv(c1 * 2, c1)

        self.output_layer = nn.Conv2d(c1, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Four 2x pools with no padding or cropping in the skip concatenations, so both spatial
        # extents must be divisible by 16. Without this check a 513x513 tile fails deep inside the
        # decoder with "Expected size 512 but got size 513", which says nothing about the cause.
        # Training was at 512x512. Raising here cannot change any computation that would otherwise
        # have succeeded — it only replaces an opaque error with a specific one.
        if x.ndim != 4:
            raise ValueError(f"Expected a 4-D (N, C, H, W) batch, got shape {tuple(x.shape)}.")
        h, w = int(x.shape[-2]), int(x.shape[-1])
        if h % _SIZE_DIVISOR or w % _SIZE_DIVISOR or h == 0 or w == 0:
            raise ValueError(
                f"Spatial size {h}x{w} is not usable: this U-Net pools four times, so height and "
                f"width must each be a positive multiple of {_SIZE_DIVISOR} (it was trained at "
                f"512x512). Pad or tile the input before calling."
            )
        e1 = self.encoder1(x)
        e2 = self.encoder2(self.pool(e1))
        e3 = self.encoder3(self.pool(e2))
        e4 = self.encoder4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))

        d4 = self.decoder4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.decoder3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.decoder2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.decoder1(torch.cat([self.up1(d2), e1], dim=1))
        return self.output_layer(d1)


def build_flood_model(
    in_channels: int = FLOOD_INPUT_CHANNELS,
    num_classes: int = 2,
    base_channels: int = 16,
    state_dict: Optional[dict] = None,
) -> UNetFromScratch:
    """Builds the network and, when given one, loads a state_dict with strict=True."""
    model = UNetFromScratch(in_channels, num_classes, base_channels)
    if state_dict is not None:
        model.load_state_dict(state_dict, strict=True)
    return model
