# Flood Segmentation Model Delivery

Generated: 2026-09-19T22:46:35

## Model

- Architecture: U-Net from scratch
- Training type: From scratch
- Input channels: 16
- Modalities: S1 + S2 + DEM
- Image size: 512 x 512
- Number of classes: 2
- Ignore index: 255
- Best checkpoint: Epoch 9
- Validation loss: 0.374064

## Required Input Channel Order

1. Sentinel-1 VV
2. Sentinel-1 VH
3-15. Sentinel-2 bands:
    B1, B2, B3, B4, B5, B6, B7, B8,
    B8A, B9, B10, B11, B12
16. DEM

The inference implementation must preserve this channel order
and reproduce the training-time preprocessing.

## Checkpoint

Use:

checkpoints/best_model.pt

The last checkpoint is provided for backup:

checkpoints/last_model.pt

## Integration Requirements

- Load the real checkpoint.
- Do not use synthetic or dummy predictions.
- Validate that S1, S2, and DEM inputs are available.
- Preserve the training-time normalization procedure.
- Use ignore index 255 for invalid pixels.
- Return an explicit structured error if the checkpoint is missing.
- Do not report confidence unless it is calculated from real model outputs.
- Keep the model's input channel order unchanged.

## Included Files

- checkpoints/best_model.pt
- checkpoints/last_model.pt
- metadata/model_metadata.json
- metadata/training_config.json
- metadata/selected_flood_threshold.json
- evaluation/final_model_evaluation_summary.json
- evaluation/test_evaluation_report.json
- evaluation/calibrated_test_evaluation_report.json
- SHA256SUMS.json
