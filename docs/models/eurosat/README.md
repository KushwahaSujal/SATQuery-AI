# SatQuery AI — EuroSAT Landcover Model

## Model

- Model: EfficientNet-B0
- Dataset: EuroSAT RGB
- Task: Landcover Classification
- Classes: 10
- Checkpoint: best_model.pt

## Actual Evaluation Results

| Metric | Value |
|---|---:|
| Test Samples | 4050 |
| Accuracy | 0.983210 |
| Balanced Accuracy | 0.982422 |
| ROC-AUC OvR Macro | 0.999596 |
| ROC-AUC OvR Weighted | 0.999615 |
| PR-AUC Macro | 0.996736 |
| PR-AUC Weighted | 0.996880 |

## Class Order

0. AnnualCrop
1. Forest
2. HerbaceousVegetation
3. Highway
4. Industrial
5. Pasture
6. PermanentCrop
7. Residential
8. River
9. SeaLake

## Required Preprocessing

Read preprocessing configuration from:

inference_config.json

The deployed preprocessing must match the training pipeline.

## Integration

Expected integration directory:

SatQuery AI/checkpoints/eurosat_efficientnet_b0/

Required checkpoint:

best_model.pt

## Model Behavior

- Load the real trained checkpoint.
- Apply the correct preprocessing.
- Return the predicted landcover class.
- Return actual model confidence.
- Do not fabricate outputs if the checkpoint is missing.
- Return MODEL_CHECKPOINT_MISSING when the checkpoint is unavailable.

## Limitations

This model performs scene-level landcover classification.
It does not directly perform pixel-level segmentation or object detection.

## Generated Artifacts

- evaluation_metrics.json
- classification_report.csv
- figures/
- predictions/

Generated: 2026-09-20T17:26:59
