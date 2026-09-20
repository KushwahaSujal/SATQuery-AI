# Prithvi-EO v2 300M Burn-Scars Checkpoint

## Project

SatQuery AI

## Task

Burn-scar semantic segmentation using six HLS reflectance bands.

## Model

Prithvi-EO v2 300M

## Training

- Training type: From scratch
- Backbone pretrained: False
- Backbone frozen: False
- Total training epochs: 10
- Selected checkpoint: Epoch 8
- Split seed: 42
- Training scenes: 432
- Internal validation scenes: 108
- Held-out test scenes: 264

## Input bands

1. BLUE
2. GREEN
3. RED
4. NIR_NARROW
5. SWIR_1
6. SWIR_2

## Classes

- Class 0: Not burned
- Class 1: Burn scar

## Inference threshold

0.40

The threshold was selected using the internal validation split.

## Checkpoint

PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt

## SHA-256

bb1ce3b5a9901415cbc33076c785aa234b80e06e1dd54ad4f5c2bbcea18a8dc8

## Important evaluation note

The HLS Burn Scars dataset does not provide an official independent test split.

The original 264-scene validation partition was treated as the held-out test set after creating a new 432/108 split from the original training partition.

The 264-scene held-out test set was not used for threshold selection.

## Files

- Model checkpoint
- From-scratch model configuration
- Test metrics
- Per-scene metrics
- Internal validation threshold analysis
- Train/validation split
- Failure-analysis visualizations
- Model manifest

## Environment

The checkpoint was trained using:

- Python 3.12
- PyTorch
- TerraTorch
- CUDA GPU environment

Before inference, recreate the compatible Python environment and verify the TerraTorch and PyTorch versions.

Do not report synthetic predictions or invented confidence values.
