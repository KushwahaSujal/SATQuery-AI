# Locally trained segmenters and the crater detector

Four models trained on this project's own data pipeline, now reachable through the model registry.
**Nothing routes to them yet.** The router, the agent and the workflows are unchanged: this layer is
the adapters, the config entries and the tests only. Wiring prompts to them is a separate change and
gets its own QNA entry (project/qna.md Q-031 lists the gate each capability must pass).

All numbers below are copied from the QNA transcript. Nothing here is estimated.

| Registry key | Checkpoint | Architecture | QNA |
|---|---|---|---|
| `roads_segmenter` | `checkpoints/roads_all_r50_seg/best.pt` | smp U-Net, ResNet-50, 1 class | Q-025, Q-030, Q-032 |
| `buildings_segmenter` | `checkpoints/buildings_whu_ma_r50_seg/best.pt` | smp U-Net, ResNet-50, 1 class | Q-026, Q-032 |
| `landcover_segmenter` | `checkpoints/landcover_dg_lv_oem_seg/best.pt` | smp U-Net, ResNet-34, 7 classes | Q-029 |
| `crater_detector` | `checkpoints/craters_yolo/weights/best.pt` | ultralytics YOLO11s, 1 class | Q-028 |

## The 0.5 m assumption

Every tile the three segmenters were trained on was resampled to **0.5 m ground sampling distance**
(`training/segmentation/datasets.py`, `TARGET_GSD_M = 0.5`), so a road is the same number of pixels
wide whichever dataset it came from. The adapters do **not** resample: they run the model at the
resolution they are given. Imagery much coarser (Sentinel-2 at 10 m) or much finer (drone imagery,
ISPRS at 5–9 cm) is outside the measured range, and nothing in Q-025 to Q-032 measures how the
models behave there. A caller that knows its GSD should resample to 0.5 m before calling.

Normalisation is the trainer's: ImageNet mean/std over 0–255 RGB (`MEAN`, `STD` in
`training/segmentation/datasets.py`). The adapters import those constants and the trainer's
`build_model`, `infer_prob` and `infer_logits` rather than re-implementing them, so serving cannot
silently drift from training.

The crater detector runs at **832 px** with `max_det=1000`, as it was trained: LU3M6TGT craters are
tiny (median box about 9 px) and dense (up to 506 per tile).

## Roads — `roads_segmenter`

`roads_all_r50`: U-Net / ResNet-50 on DeepGlobe + Massachusetts + SpaceNet-3 (all four cities),
60 epochs, best epoch 54, decision threshold **0.35** frozen on validation (val IoU 0.583).

Test IoU, each split scored once at that threshold (Q-032):

| Test split | ResNet-34 | ResNet-50 (this checkpoint) | + 4-flip TTA |
|---|---|---|---|
| DeepGlobe (297 tiles, our hash split) | 0.554 | 0.557 | 0.569 |
| Massachusetts (49, official) | 0.610 | 0.616 | 0.622 |
| SpaceNet-3, 4 cities (122) | 0.558 | 0.565 | 0.571 |

Against the live Grounding DINO + V4 + SAM 2 pipeline on the same tiles, with the ResNet-34 model
(Q-025): DeepGlobe 0.031 → 0.540, Massachusetts 0.021 → 0.606. Per-city SpaceNet, ResNet-34
(Q-030): Vegas 0.631, Paris 0.549, Shanghai 0.500, Khartoum 0.532.

Caveats recorded in the transcript: the DeepGlobe test split is our own 90/5/5 hash split, **not**
the DeepGlobe benchmark, so these numbers are not comparable to published leaderboards; single-seed
runs; and `roads_all_r50` was interrupted by a power cut at epoch 38 and continued with
`--warm-start`, so AdamW's moment estimates restarted (Q-032 §1).

## Buildings — `buildings_segmenter`

`buildings_whu_ma_r50`: U-Net / ResNet-50 on WHU Building + Massachusetts Buildings, 256 px crops at
0.5 m, best epoch 37, decision threshold **0.45** frozen on validation (val IoU 0.832).

| Test split | ResNet-34 | ResNet-50 (this checkpoint) | + 4-flip TTA |
|---|---|---|---|
| WHU (1228 tiles, official) | 0.823 | 0.834 | 0.840 |
| Massachusetts (10, official) | 0.686 | 0.695 | 0.700 |

Against the live pipeline on the same tiles, ResNet-34 (Q-026): WHU 0.635 → 0.831,
Massachusetts 0.191 → 0.686. The pipeline is not bad at buildings — they are compact objects a box
detector handles well — and the gap opens on the dense 1 m Massachusetts scenes. The model's
training context was 256 px at 0.5 m (128 m), so very large buildings such as warehouses and airport
terminals were rare in training and have not been measured.

## Land cover — `landcover_segmenter`

`landcover_dg_lv_oem`: U-Net / ResNet-34 with a 7-class head on DeepGlobe Land Cover + LoveDA +
OpenEarthMap, best epoch 32, val mIoU 0.706. Classes come from the checkpoint:
`other, built_up, agriculture, rangeland, forest, water, barren` (255 = ignore in training).

| Test split | mIoU | pixel acc | built_up | agriculture | rangeland | forest | water | barren | other |
|---|---|---|---|---|---|---|---|---|---|
| DeepGlobe (38) | 0.682 | 0.881 | 0.647 | 0.885 | 0.265 | 0.807 | 0.793 | 0.698 | — |
| OpenEarthMap (500) | 0.600 | 0.805 | 0.823 | 0.684 | 0.498 | 0.654 | 0.654 | 0.286 | — |
| LoveDA (1669) | 0.428 | 0.601 | 0.433 | 0.568 | — | 0.321 | 0.590 | 0.287 | 0.367 |

**There is no head-to-head**: the live system has no pixel-level land-cover capability to compare
against (BigEarthNet gives scene-level multi-label tags on Sentinel-2). The taxonomy merge is lossy
by design — LoveDA's building and road both become `built_up`, as do OpenEarthMap's developed space,
road and building — so these numbers are not comparable to published leaderboards. Weak classes:
rangeland (0.27 on DeepGlobe) and barren (0.29 on OpenEarthMap and LoveDA). LoveDA is weak overall,
trained on about half of its official train set (the HF mirror has 1366 of 2522 tiles).

A ResNet-50 variant (`landcover_full_r50`) is queued behind the full LoveDA download. The adapter
reads `arch`, `encoder` and `classes` from the checkpoint, so it will load that one too; only the
`checkpoint_path` in `configs/models.yaml` needs changing.

## Craters — `crater_detector`

YOLO11s from COCO weights, 60 epochs at 832 px, on LU3M6TGT (Moon) plus a small Kaggle Mars/Lunar
set. Best weights chosen by ultralytics' validation fitness; test scored once (Q-028).

| Test split | mAP50 | mAP50-95 | P | R |
|---|---|---|---|---|
| LU3M6TGT (793) | 0.965 | 0.870 | 0.912 | 0.892 |
| Mars/Lunar (19) | 0.648 | 0.345 | 0.657 | 0.596 |

AP50 from this project's own scorer, against zero-shot Grounding DINO prompted `"crater."` on the
same tiles: LU3M6TGT 150 tiles, GD 0.024 at its most favourable threshold (0.01) against YOLO 0.963;
Mars/Lunar 19 tiles, GD 0.377 against YOLO 0.642.

The Mars/Lunar set is small (98 train, 19 test tiles), so its 0.65 mAP50 is correspondingly
uncertain — the model mostly learned LU3M6TGT's lunar imagery. LU3M6TGT labels come from a
catalogue, so very small or degraded craters may be missing from the labels and count against
precision.

### Licence — AGPL-3.0

**ultralytics is AGPL-3.0** (user's decision, 2026-09-17). Serving this model from the backend over a
network may carry source-disclosure obligations. The adapter therefore imports `ultralytics` lazily,
inside `load_model()`, so importing `backend.app.ml.registry` never pulls an AGPL dependency into
the process; `tests/unit/test_trained_adapters.py` asserts that. It is installed `--no-deps` so its
`opencv-python` requirement does not clash with the backend's `opencv-python-headless`
(`training/requirements.txt`).

## Calling the adapters

Each is lazy: constructing costs nothing, the first `predict` loads the weights, and `unload()`
frees them and returns the CUDA cache to the driver. All four accept a PIL image, a path, a
`numpy` array (HWC or CHW, uint8 or float) or a context dict with `image` / `image_pil` /
`image_path` / `arr`.

```python
from backend.app.ml.registry import model_registry

roads = model_registry.get_adapter("roads_segmenter")
if roads.is_available():                       # False when the checkpoint is not on disk
    result = roads.predict(rgb_array)          # or predict({"image": rgb_array})
    mask = result.masks[0]["binary_mask"]      # uint8 (H, W), values {0, 1}
    prob = result.masks[0]["probability_map"]  # float32 (H, W), [0, 1]
    result.metadata["threshold"]               # 0.35, from the checkpoint
    result.metadata["pixel_count"]             # foreground pixels
    result.metadata["coverage_pct"]            # share of the tile, percent
    roads.unload()
```

Signatures:

- `BinarySegmenterAdapter.predict(image_or_context=None, *, threshold=None, tta=None) -> ModelResult`
  — `roads_segmenter` and `buildings_segmenter`. `threshold` overrides the checkpoint's frozen
  threshold for one call; `tta` turns on 4-flip averaging (4x slower, +0.005 to +0.012 IoU).
  `task = "segmentation"`. One `masks` entry: `binary_mask`, `probability_map`, `label`,
  `pixel_count`, `shape`. `metadata` carries `class_name`, `threshold`, `threshold_source`
  (`request` / `config` / `checkpoint` / `default`), `pixel_count`, `total_pixel_count`,
  `coverage_pct`, `tta`, `arch`, `encoder`, `trained_gsd_m`.
- `LandCoverSegmenterAdapter.predict(image_or_context=None) -> ModelResult` — `task =
  "land_cover_segmentation"`. One `masks` entry per class **present in the prediction**, sorted by
  descending pixel count: `binary_mask`, `label`, `class_index`, `pixel_count`, `area_pct`,
  `mean_probability`. The largest entry also carries `class_map` (uint8 (H, W) of class indices) and
  `confidence_map`. `metadata` carries `classes`, `area_pct` and `pixel_counts` for **every** class
  including the absent ones, and `dominant_class`. `adapter.classes` is populated once loaded.
- `CraterDetectorAdapter.predict(image_or_context=None, *, confidence_threshold=None) -> ModelResult`
  — `task = "detection"`. `boxes` follow the Grounding DINO shape, sorted by descending score:
  `{"xyxy": [x1, y1, x2, y2] in pixels, "score": float, "label": "crater", "box_2d": [ymin, xmin,
  ymax, xmax] normalised}`. `box_2d` is included so `SAM2Adapter._parse_box` accepts a crater box
  unchanged.

`configs/models.yaml` drives the checkpoint path, device, `class_name` and `tta` for the binary
segmenters, and `input_size` / `box_threshold` for the detector. `threshold` is left `null` for both
segmenters so the threshold frozen on validation — which lives inside the checkpoint — is the one
used; set it in the config only to override that deliberately.

## Tests

- `tests/unit/test_trained_adapters.py` — construction, config parsing, registry wiring,
  `is_available()` false with the checkpoint missing, input validation, the AGPL lazy-import check.
  Needs no weights.
- `tests/models/test_trained_adapters.py` — one real inference per adapter on a tile from
  `datasets/raw/`, on CPU, unloading between models. Skips when the checkpoint or the tile is
  missing (both are gitignored). These check the output contract, not accuracy.

```
.venv/bin/python -m pytest tests/unit/test_trained_adapters.py tests/models/test_trained_adapters.py -q
```
