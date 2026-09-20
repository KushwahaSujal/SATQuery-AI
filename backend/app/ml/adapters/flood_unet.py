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

**This reconstruction has NOT been numerically confirmed against the delivered metrics, and cannot
be.** The delivery documents the channel order but never states the training-time normalisation, so
there is no way to run the model as it was evaluated. 17 candidate preprocessing schemes were swept
over the official Sen1Floods11 splits and none reproduced the delivered test IoU of 0.6292
(project/qna.md Q-041 §5). The structure is therefore proven by `strict=True` alone, and by that
standard only — which the ChangeFormer precedent above says is not enough to trust the outputs. That
is exactly why `FloodSegmenterAdapter.predict` refuses to serve a flood mask.

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

#: Band order, for error messages and for the adapter's metadata.
FLOOD_CHANNEL_NAMES = (
    "S1_VV", "S1_VH",
    "S2_B1", "S2_B2", "S2_B3", "S2_B4", "S2_B5", "S2_B6",
    "S2_B7", "S2_B8", "S2_B8A", "S2_B9", "S2_B10", "S2_B11", "S2_B12",
    "DEM",
)


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
