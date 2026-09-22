# Locally trained segmenters and the crater detector

Models trained on this project's own data pipeline, reachable through the model registry. The
capability router (`intent_classifier.py`) and the agent are unchanged; routing happens one level
down, inside `run_grounding_pipeline`, which dispatches plain whole-image category masks to a
trained segmenter. **Roads, buildings, water and cloud route; land cover and the two ISPRS models
are registered and callable but deliberately do not.** See the two "Wired in" sections at the end of
this file (project/qna.md Q-038 and the water/cloud/land-cover/ISPRS change that follows it).

All numbers below are copied from the QNA transcript. Nothing here is estimated.

| Registry key | Checkpoint | Architecture | Routed? | QNA |
|---|---|---|---|---|
| `roads_segmenter` | `checkpoints/roads_all_r50_seg/best.pt` | smp U-Net, ResNet-50, 1 class | yes | Q-025, Q-030, Q-032 |
| `buildings_segmenter` | `checkpoints/buildings_whu_ma_r50_seg/best.pt` | smp U-Net, ResNet-50, 1 class | yes | Q-026, Q-032 |
| `water_segmenter` | `checkpoints/water_seg/best.pt` | smp U-Net, ResNet-34, 1 class | yes | Q-035 |
| `cloud_segmenter` | `checkpoints/cloud_seg/best.pt` | smp U-Net, ResNet-34, 1 class | yes | Q-035 |
| `landcover_segmenter` | `checkpoints/landcover_full_r50_seg/best.pt` | smp U-Net, ResNet-50, 7 classes | no | Q-029, Q-037 |
| `isprs_potsdam_segmenter` | `checkpoints/isprs_potsdam_seg/best.pt` | smp U-Net, ResNet-34, 6 classes | no | Q-036 |
| `isprs_vaihingen_segmenter` | `checkpoints/isprs_vaihingen_seg/best.pt` | smp U-Net, ResNet-34, 6 classes | no | Q-036 |
| `crater_detector` | `checkpoints/craters_yolo/weights/best.pt` | ultralytics YOLO11s, 1 class | no | Q-028 |

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

**As of this change `landcover_segmenter` points at `landcover_full_r50`**, not the older
`landcover_dg_lv_oem`. `landcover_full_r50`: U-Net / **ResNet-50** with a 7-class head on DeepGlobe
Land Cover + the **complete** 2522-tile LoveDA train set + OpenEarthMap, best epoch 34, val mIoU
0.649. Classes come from the checkpoint:
`other, built_up, agriculture, rangeland, forest, water, barren` (255 = ignore in training).

Test mIoU, new checkpoint vs the one it replaces (project/qna.md Q-037):

| Test split | `landcover_dg_lv_oem` (R-34, partial LoveDA) | `landcover_full_r50` (R-50, full LoveDA) |
|---|---|---|
| DeepGlobe (38) | 0.682 | **0.698** |
| OpenEarthMap (500) | 0.600 | **0.603** |
| LoveDA (1669) | 0.428 | **0.488** |

Better on all three splits, so the repoint has no measured downside. Two changes landed in that one
training run (encoder *and* the corrected dataset), so their individual contributions to the +0.060
LoveDA gain are not separated. Per-class test IoU for the new checkpoint is in
`checkpoints/landcover_full_r50_seg/report.json`; the older per-class breakdown was:

| Test split (old ckpt) | mIoU | pixel acc | built_up | agriculture | rangeland | forest | water | barren | other |
|---|---|---|---|---|---|---|---|---|---|
| DeepGlobe (38) | 0.682 | 0.881 | 0.647 | 0.885 | 0.265 | 0.807 | 0.793 | 0.698 | — |
| OpenEarthMap (500) | 0.600 | 0.805 | 0.823 | 0.684 | 0.498 | 0.654 | 0.654 | 0.286 | — |
| LoveDA (1669) | 0.428 | 0.601 | 0.433 | 0.568 | — | 0.321 | 0.590 | 0.287 | 0.367 |

**There is no head-to-head**: the live system has no pixel-level land-cover capability to compare
against (BigEarthNet gives scene-level multi-label tags on Sentinel-2). The taxonomy merge is lossy
by design — LoveDA's building and road both become `built_up`, as do OpenEarthMap's developed space,
road and building — so these numbers are not comparable to published leaderboards. Weak classes:
rangeland (0.27 on DeepGlobe) and barren (0.29 on OpenEarthMap and LoveDA) in the old checkpoint.
The old checkpoint's LoveDA weakness was partly a data problem: it trained on about half of LoveDA's
official train set (the HF mirror held 1366 of 2522 tiles, rural only), which the current checkpoint
fixes.

The repoint needed no adapter change — `arch`, `encoder` and `classes` all come from the checkpoint,
so only `checkpoint_path` in `configs/models.yaml` moved.

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

`is_available()` is true only when the model is enabled, its checkpoint is on disk, and — for the
three segmenters — `training.segmentation` is importable, since they load the trainer's
`build_model` / `infer_prob` / `infer_logits`. For the crater detector it also requires
`ultralytics` to be installed. A deploy that ships `backend/` and `configs/` without `training/`
will report these three as unavailable rather than failing on the first request.

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

## Water and cloud

Trained 2026-09-18 (project/qna.md Q-035). Water: best epoch 21, threshold 0.20, val pooled IoU 0.800, test pooled IoU 0.475 — but per-tile median IoU is 0.857 (val) / 0.866 (test); the pooled test score is dragged down by a few very large tiles in this small, unofficial-split dataset, not by typical-tile performance. See Q-035 for the full breakdown. Cloud: best epoch 9, threshold 0.50, val pooled IoU 0.830, test pooled IoU 0.703 (not comparable to the official 38-Cloud/95-Cloud leaderboard test set, which this repo does not have — see below). Checkpoints: `checkpoints/water_seg/best.pt`, `checkpoints/cloud_seg/best.pt`. Neither is wired into the app.

The rest of this section (data layout, splits, resolution rationale) predates training and is still accurate as written.

### Resolution: why these two do not use the 0.5 m target

`TARGET_GSD_M = 0.5` exists so a road is the same number of pixels wide whichever sub-metre source
it came from. Both new sources are far coarser than that, and resampling them to 0.5 m would
invent 400x (water) to 3600x (cloud) more pixels than the sensors ever recorded — a 384x384
Landsat patch would become 23040x23040, which neither fits in memory nor adds information.

So each source keeps its true GSD in its `Item`, and the target is now per task: `train_seg.py`
takes `--target-gsd`, threaded through `SegTiles` into `read_pair` / `read_crop`. Passing the
source's own GSD makes the resample factor exactly 1, so tiles are used at native resolution.
The default is unchanged at 0.5 m, so the road, building and land-cover runs are bit-identical
(verified by loading a `deepglobe_roads` and a `whu_building` tile through `read_pair` and
`read_crop` before and after the change and comparing arrays: all identical).

### water_bodies

| | |
|---|---|
| Raw path | `datasets/raw/water_bodies_s2/Water Bodies Dataset/{Images,Masks}` |
| Sensor | Sentinel-2 L1C true-colour, RGB jpg |
| Native resolution | 10 m/px (`WATER_GSD_M`) |
| Tile size | variable, 5 to 5640 px per side; median short side 254 px |
| Mask | jpg-compressed greyscale, not exactly 0/255 — binarised at > 127 by `_finish` |
| Split | `hash_split` on the tile id (no official split ships with the dataset) |
| Tiles | train 2560 · val 129 · test 131 (2820 of 2841) |
| Foreground | water covers 32.9% of pixels on average (median 28.0%), over all 2841 tiles |

21 tiles are dropped because their short side is under 32 px; padded up to a crop they would be
almost entirely no-data. Image and mask always agree in size and every image has a mask — the
2841 pairs were all decoded and checked. No image contains a pure-white pixel, so the white
no-data convention `read_crop` uses for padding cannot swallow real data here.

### cloud95

| | |
|---|---|
| Raw path | `datasets/raw/cloud95_landsat8/95-cloud_training_only_additional_to38-cloud/` |
| Sensor | Landsat 8 OLI, one 16-bit TIF per band (red/green/blue/nir) |
| Native resolution | 30 m/px (`CLOUD_GSD_M`) |
| Tile size | 384x384, fixed |
| Mask | `train_gt_*`, uint8 {0, 255} |
| Split | `hash_split` on the Landsat **scene id**, not the patch id |
| Scenes | train 51 · val 3 · test 6 (60 scenes) |
| Patches | train 13768 · val 856 · test 1723 (16347) |
| Foreground | cloud covers 32.7% of pixels on average (median 5.0%) over a 60-patch random sample; 21 of those 60 are entirely cloud-free |

Notes:

- **Only half the release is on disk.** `datasets/raw/cloud95_landsat8/` holds the "95-Cloud
  additional to 38-Cloud" patches (26301) plus metadata. The 38-Cloud train patches and the
  38-Cloud/95-Cloud **test** imagery were not downloaded — only their `*_MTL.txt` metadata. The
  official test split is therefore unusable, and the split is made here instead.
- **Split is by scene, not by patch.** 95-Cloud patches tile a scene and neighbours are highly
  correlated, so a patch-level split would leak. `hash_split` is applied to the scene id parsed
  out of the patch name (`patch_<r>_<c>_by_<R>_<C>_<scene id>`), putting every patch of a scene in
  one split. 6 test scenes / 3 val scenes is what the 90/5/5 hash gives on 60 scenes.
- **Non-empty list respected.** Only the 16347 patches in `training_patches_95-cloud_nonempty.csv`
  that have ground truth on disk are indexed. "Non-empty" refers to the image (patches that are
  entirely scene-border no-data are excluded), not the label — cloud-free patches stay in and are
  the negatives the detector needs.
- **16 to 8 bit is a fixed shift, not a per-patch stretch.** `_read_cloud95` stacks red/green/blue
  and applies `>> 8`, capped at 254. A per-patch percentile stretch would leak the label, because
  an overcast patch and a clear one would end up with the same histogram. The 254 cap stops a
  bright cloud from becoming pure white, which `_finish` would otherwise read as no-data —
  exactly the foreground the model has to find.
- NIR (`train_nir_additional_to38cloud`) is on disk but unused: `build_model` builds a 3-channel
  encoder with ImageNet weights. A false-colour NIR/red/green variant would be a second entry in
  `_READERS` and one more `SOURCES` line if it is ever wanted.

## Wired in — roads and buildings (project/qna.md Q-038)

`run_grounding_pipeline` (`backend/app/workflows/grounding.py`) now dispatches a plain, unqualified
whole-image category request for roads or buildings straight to `roads_segmenter` /
`buildings_segmenter`, instead of Grounding DINO + V4 reasoning + SAM 2. The dispatch decision lives
in `backend/app/workflows/trained_segmenter.py` (`classify_trained_segmenter_target`, a pure function
tested with no weights in `tests/unit/test_trained_segmenter_dispatch.py`) and runs right after
`parse_v4_query`, before any detector call.

**Routes to the trained segmenter:** "mark all roads", "segment buildings", "find every road", "mask
all the buildings" — a category request with no size, position, ordinal, relational or colour
qualifier, and naming only roads or only buildings (reusing `_wants_all_instances`'s existing
category-vs-single-target signal, plus explicit checks on `relation` and `color`, which that function
does not itself look at).

**Falls through to the existing Grounding DINO + SAM 2 path, unchanged:** "the largest building"
(size/ordinal), "the road near the school" (relational), "red buildings" (colour-qualified), "roads
and buildings" (multiple classes in one query), any class without a trained segmenter (cars, ships,
planes, water, craters, ...). The capability-level routing in
`backend/app/orchestration/intent_classifier.py` is untouched — this dispatch is entirely inside the
grounding workflow, one level below where that file's road/building/water regex groups route a query
to `single_image_grounding` in the first place.

**Strategy strings**, distinct from `V4_RELATIONAL` so they are traceable in logs and evidence:
`trained_segmenter_roads`, `trained_segmenter_buildings`.

**Config flag:** `settings.trained_segmenter_routing.enabled` (`configs/app.yaml`,
`trained_segmenter_routing.enabled`, default `true`), env override
`SATQUERY_TRAINED_SEGMENTERS_ENABLED`. Setting it to `false` sends every query through the existing
detector + SAM 2 path, with no code change. If the checkpoint or `training.segmentation` is
unavailable for a route that matched (`model_registry.is_model_available()` false), the pipeline
falls back to the existing path too, with a `trained_segmenter_unavailable` trace step — the same
graceful-unavailability behaviour the adapters already have (`is_available()`), not a new failure
mode.

**Response shape:** matches `run_grounding_pipeline`'s existing contract. `selected_box` is `None`
(a road network or a scene's buildings are not one box; downstream code already handles a `None`
box with a mask present — `backend/app/evidence/fusion.py::build_grounding_evidence` builds the mask,
statistics and GeoJSON independent of `selected_box`, and only skips adding a bounding-box evidence
entry). `segmentation_mask` is the adapter's binary mask at the image's own resolution.
`grounding_score` is `None` (no detector ran); `sam2_score` carries the segmenter's own confidence
(mean foreground probability where it fired) so `run_grounding`'s existing
`pipeline_res.get("sam2_score") or pipeline_res.get("grounding_score")` read keeps working
unchanged. `evidence` adds a `trained_segmenter` block (`model_key`, `checkpoint`, `threshold`,
`threshold_source`, `coverage_pct`, `trained_gsd_m`, `encoder`, `tta`) alongside the usual
`mask_pixel_count` / `mask_area_ratio`. `trace` gets one `call_trained_segmenter` step (checkpoint
path, threshold, confidence) plus the existing `validate_image` / `receive_query` / `parse_query` /
`build_visual_evidence` / `complete_pipeline` steps; the detector- and SAM2-specific steps
(`call_grounding_dino`, `call_sam2`, `run_grounding_reasoner`, ...) never appear.

**Resolution / GSD caveat, unchanged from the rest of this document:** the checkpoints are trained
and validated at 0.5 m/px. `run_grounding_pipeline` has no GSD metadata for an arbitrary uploaded
image (`AgentState`/the calling context does not thread one this deep), so the model runs at the
image's native resolution — no unvalidated resampling step was added — and the answer text says so
explicitly. A caller that knows its image's GSD should resample to 0.5 m before calling.

**Measured end-to-end** (`tests/models/test_grounding_trained_segmenter.py`, CPU, one DeepGlobe tile,
`656960_sat.jpg`, 1024x1024): `run_grounding_pipeline(image, "mark all roads")` returned
`strategy = "trained_segmenter_roads"`, `selected_box = None`, predicted road fraction 0.67% against
a ground-truth fraction of 0.64%, IoU 0.746 against that tile's ground truth. This is one tile, not
the held-out test split Q-032 scores (DeepGlobe test IoU 0.557-0.569) — it checks the wiring is
correct, not the model's accuracy.

## Wired in — water and cloud; deliberately not wired — land cover and ISPRS

This section extends the roads/buildings dispatch above to the remaining trained checkpoints. The
mechanism is unchanged: `classify_trained_segmenter_target` in
`backend/app/workflows/trained_segmenter.py` maps a parsed query onto a registry key, or returns
`None` and lets the existing Grounding DINO + V4 + SAM 2 path handle it.

### What routes now

| Query shape | Model | Strategy string | Trained at |
|---|---|---|---|
| "mark all roads", "find every road", "show me the streets" | `roads_segmenter` | `trained_segmenter_roads` | 0.5 m |
| "segment buildings", "mask all the buildings" | `buildings_segmenter` | `trained_segmenter_buildings` | 0.5 m |
| "mask all water", "mask water bodies", "mask all lakes/rivers/ponds", "mask the reservoir" | `water_segmenter` | `trained_segmenter_water` | **10 m** (Sentinel-2) |
| "mask the clouds", "mask all clouds", "segment clouds", "mask cloud cover" | `cloud_segmenter` | `trained_segmenter_cloud` | **30 m** (Landsat 8) |

### Cloud is reachable — measured, not assumed

"Cloud" appears in no `OBJECT_PATTERNS` group in `intent_classifier.py`, which raises the fair
question of whether a cloud query ever reaches `run_grounding_pipeline` at all. It does, and the
split is a useful one. Measured against the real classifier:

| Query | `classify_intent` task | Reaches grounding? |
|---|---|---|
| "mask the clouds" | `single_image_grounding` | yes — category `clouds` |
| "mask all clouds" | `single_image_grounding` | yes |
| "segment clouds" | `single_image_grounding` | yes |
| "mask cloud cover" | `single_image_grounding` | yes |
| "is this scene cloudy" | `single_image_vqa` | no |
| "how cloudy is this image" | `single_image_vqa` | no |
| "remove the clouds" | `single_image_vqa` | no |

The mask-phrased queries arrive through the router's *fallback noun-phrase extractor*, which pulls
the noun following a grounding verb when the object dictionary misses. The genuinely
preprocessing/quality phrasings classify as VQA and never reach this dispatch — which is the
behaviour we want, and it needs no change to the capability router. Cloud masking is therefore wired
as an object query; "how cloudy is this scene?" remains a VQA question and is unaffected.

### Compound-noun exclusions

Bare `water` and `cloud` are in the vocabulary because "mask all water" and "mask the clouds" are
the canonical phrasings. That makes a small exclusion list necessary, since some compound nouns
contain a target word but name a different object entirely
(`TRAINED_SEGMENTER_EXCLUSIONS`):

| Query | Parsed category | Result |
|---|---|---|
| "mask all water tanks" | `water tanks` | falls back — a storage tank is the detector's job |
| "mask the water tower" | `water tower` | falls back |
| "mask the cloud shadows" | `cloud shadow` | falls back — 95-Cloud labels cloud, not its shadow |
| "mask water and roads" | `water roads` | falls back — two trained classes, ambiguous |
| "mask all waterfront buildings" | `waterfront buildings` | not water; `\b` already excludes it |
| "mask all cloudy areas" | `cloudy areas` | not cloud; `\b` already excludes it |

### Resolution caveats, per model

The binary adapter no longer reports a single hard-coded 0.5 m for every checkpoint. `train_seg.py`
writes `--target-gsd` into `report.json` only, never into the checkpoint dict, so
`configs/models.yaml`'s `trained_gsd_m` is the source for binary models (the multi-class checkpoints
do store `target_gsd`, which takes precedence). Without this fix the water answer would have claimed
"trained at 0.5 m/px" — wrong by 20x.

Water and cloud are the first routed models whose training imagery is a different *kind* of image
from the sub-metre aerial photography a user is most likely to upload, so their answers carry an
extra sentence naming the sensor and stating plainly that accuracy on high-resolution imagery has
not been measured. **No head-to-head measurement exists for water or cloud against the Grounding
DINO + SAM 2 path** — the Q-025t/Q-026t comparisons that justified routing roads and buildings were
never run for these two classes. They are routed on the same structural argument (a whole-image
region class is a poor fit for an open-vocabulary box detector), not on a measured win.

Water's headline pooled test IoU of 0.475 understates it: that figure is pixel-weighted over tiles
spanning ~4000x in area, and 7 of 131 test tiles dominate the total. Per tile the median is 0.866
and the mean 0.772 (Q-035). The per-tile number is the one that describes what a user sees on one
uploaded image.

### Land cover — registered, callable, deliberately not routed

`landcover_segmenter` returns a 7-class class-index map plus per-class area shares. It is **not**
auto-routed, for two independent reasons:

1. **The response contract cannot carry it.** `run_grounding_pipeline` returns one
   `segmentation_mask`, and every consumer treats it as a single binary mask:
   `backend/app/evidence/fusion.py::build_grounding_evidence` passes it to
   `calculate_area_statistics`, to `mask_to_geojson(binary_mask=...)`, and writes the PNG as
   `(segmentation_mask > 0) * 255`. Handing that a 7-class index map would silently reinterpret it
   as "class 0 is background, classes 1-6 are one object" — merging built-up, agriculture,
   rangeland, forest, water and barren into a single blob and producing area statistics and
   polygons that are wrong rather than merely unhelpful. Returning the dominant class alone, or
   `segmentation_mask = None`, both answer a different question than the user asked.
2. **Almost no land-cover phrasing reaches this dispatch anyway.** Measured: "show land cover",
   "what is this area used for", "land use map" and "classify land cover" all classify as
   `single_image_vqa`. Of the phrasings that do reach grounding, only "mask land cover" also sets
   `_wants_all_instances`; "segment land cover" and "show me the land cover" do not. Routing would
   cover one phrasing while risking the contract problem above.

Carrying a multi-class result properly needs a response field that does not exist yet (per-class
masks plus a class map), which is a change to the pipeline's contract and its consumers — out of
scope here, and recorded rather than improvised.

### ISPRS Potsdam / Vaihingen — registered, callable, deliberately not routed

`isprs_potsdam_segmenter` and `isprs_vaihingen_segmenter` are 6-class urban models at 0.1 m
(impervious, building, low_vegetation, tree, car, clutter; test mIoU 0.700 over 4 tiles and 0.729
over 6 tiles — small test sets, wide uncertainty, Q-036). They are registered so they can be called
directly, but nothing auto-selects them:

- **This is model selection, not vocabulary.** An ISPRS model answers the same "mask the buildings"
  question as `buildings_segmenter`, just at 5-9 cm instead of 0.5 m. Choosing between them requires
  knowing the image's GSD, and `run_grounding_pipeline` has none — the same known limitation that
  makes the roads/buildings path run at native resolution (Q-038). A resolution guesser was
  considered and rejected: there is no validated way to infer GSD from pixels alone, and a wrong
  guess silently selects a model trained on imagery 5x finer than the input.
- **The two cities are not interchangeable.** Potsdam is RGB, Vaihingen is IRRG. On channel 0,
  Potsdam's vegetation is *darker* than roofs (ratio 0.65) and Vaihingen's is *brighter* (1.23), so
  feeding one model the other's band order is a band mismatch, not a domain shift (Q-036). Nothing
  in the pipeline reports band composition either, so even with a GSD there would be no basis to
  pick a city.

The honest position is that these are a 0.1 m capability awaiting a caller that knows its own
imagery — not something the grounding pipeline can select on its own.

### Adapter generalisation needed for ISPRS

`LandCoverSegmenterAdapter` already read `classes`, `arch` and `encoder` from the checkpoint, but it
also *rejected* any checkpoint whose class count differed from the trainer's 7-element
`LANDCOVER_CLASSES`, which excluded the 6-class ISPRS checkpoints. The comment justifying that check
said `infer_logits()` sizes its windowed accumulator from the trainer's `K`. That is not what it
does — `train_landcover.infer_logits` reads `K = model.segmentation_head[0].out_channels`, i.e. from
the model the adapter itself builds out of `len(classes)`. The check was therefore unnecessary and
its only effect was to lock the adapter to one taxonomy; it is now a non-empty check. With
`model_key` parameterised, `IsprsPotsdamSegmenterAdapter` and `IsprsVaihingenSegmenterAdapter` are
each a three-line subclass. Verified: both ISPRS checkpoints load with 6 classes and run inference.

### Tests

- `tests/unit/test_trained_segmenter_dispatch.py` — 46 tests (was 20), no weights needed: every new
  route, every compound-noun exclusion, the word-boundary cases, and explicit fallback assertions
  for land cover and the ISPRS classes so the "deliberately not routed" decision is pinned rather
  than implicit.
- `tests/models/test_grounding_trained_segmenter.py` — 2 real end-to-end tests. The water one runs
  `run_grounding_pipeline(image, "mask all water")` on a genuinely held-out tile (the trainer's own
  `hash_split`) and asserts the route, the checkpoint-frozen threshold 0.20, and that the answer
  reports 10 m/px rather than 0.5 m.
