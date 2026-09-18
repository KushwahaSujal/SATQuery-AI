# ISPRS 2D semantic labelling — very-high-resolution urban segmentation

`isprs_urban` is a segmentation task of its own, separate from `landcover`. It is the only source
in the repo at centimetre resolution, and the only one with a **car** class or a split between
**impervious surface** and **building**.

Code: `training/segmentation/datasets.py` (`ISPRS_CLASSES`, `ISPRS_SOURCES`, `IsprsTiles`,
`read_isprs`, `decode_isprs_label`, `isprs_split`, `SEG_TASKS`) and
`training/segmentation/train_landcover.py` (`--taxonomy isprs_urban`).
Tests: `tests/unit/test_isprs_dataset.py`.

## The data

Downloaded read-only under `datasets/raw/isprs_potsdam_vaihingen/`.

| source | tiles | tile size | native GSD | bands read | labels |
|---|---|---|---|---|---|
| `isprs_potsdam` | 38 | 6000 × 6000 | 0.05 m | `2_Ortho_RGB` bands 1,2,3 = R,G,B | `5_Labels_all` |
| `isprs_potsdam_irrg` | 38 | 6000 × 6000 | 0.05 m | `4_Ortho_RGBIR` bands 4,1,2 = IR,R,G | `5_Labels_all` |
| `isprs_vaihingen` | 33 | ~1900 × 2500 | 0.09 m | `top/` bands 1,2,3 = **IR,R,G** | `..._ground_truth_COMPLETE` |

Vaihingen's imagery is IRRG, not RGB — this is easy to miss and it is why the band indices are
carried in the registry item rather than assumed.

The `*_noBoundary` / `*_eroded` label sets are present but not wired in. ISPRS's own protocol
scores against the eroded ground truth so that boundary pixels do not dominate; if we ever want to
report ISPRS-comparable numbers, point the registry at those label directories — the decoder
already maps their black (0,0,0) no-data colour to `IGNORE`, so nothing else has to change.

## Class list

Six classes, indices 0–5 (`ISPRS_CLASSES`), `255 = IGNORE`:

| idx | class | label colour (RGB) |
|---|---|---|
| 0 | `impervious` (impervious surfaces) | 255, 255, 255 |
| 1 | `building` | 0, 0, 255 |
| 2 | `low_vegetation` | 0, 255, 255 |
| 3 | `tree` | 0, 255, 0 |
| 4 | `car` | 255, 255, 0 |
| 5 | `clutter` (clutter / background) | 255, 0, 0 |

Pixel share, measured over every label tile:

- Potsdam (1.368 e9 px): impervious 29.6 %, building 25.7 %, low_vegetation 22.6 %, tree 15.5 %,
  **car 1.8 %**, clutter 4.8 %.
- Vaihingen (1.683 e8 px): impervious 27.8 %, building 26.0 %, low_vegetation 21.3 %, tree 22.9 %,
  **car 1.2 %**, clutter 0.8 %.

Car is the rare class in both, which drives the split ratio below. Note that the ISPRS leaderboard
headline is the mean over the **five** classes excluding clutter; our `val.iou` is the mean over
all six present classes, so it is not directly comparable even before the split caveat.

### Why this is not folded into `LANDCOVER_CLASSES`

The 7-class land-cover taxonomy (`other, built_up, agriculture, rangeland, forest, water, barren`)
cannot express this data. It has no car class at all, and it collapses `impervious` and `building`
into one `built_up` class — which is most of what this dataset is for. Mapping ISPRS into it would
throw away the two distinctions that make centimetre imagery worth having.

### Label decoding

`decode_isprs_label` thresholds each channel at 127 and looks the resulting cube corner up in an
8-entry table, rather than matching the six colours exactly. That is not stylistic — two of the 38
Potsdam label tiles are off-palette and an exact match silently drops their pixels:

- `top_potsdam_4_12_label.tif` was distributed as a lossy re-encode: **24 850 distinct colours**,
  e.g. `(9,222,221)` for cyan and `(225,227,227)` for white. An exact match decodes **0 %** of it —
  all 36 000 000 pixels fall through to unlabelled.
- `top_potsdam_6_7_label.tif` codes most of its cars as `(252,255,0)`. An exact match finds
  6 749 car pixels; thresholding finds **253 053**, a 37× difference on the rare class.

Measured across all 71 label tiles after thresholding: **0 unknown pixels**, and **0 pixels with
any channel within 40 DN of the 127 threshold** — so the rounding is never a close call.

## Resolution decision: 0.1 m (`ISPRS_GSD_M`)

The land-cover task's 0.5 m is wrong here, and so is training at native 0.05 m. Measured on the
labels themselves (connected components of the car class, 4 198 in Potsdam / 2 352 in Vaihingen):

| | car bbox, median | at 0.5 m | at 0.1 m | at 0.05 m |
|---|---|---|---|---|
| Potsdam | 2.45 m × 4.20 m | 5 × 8 px | **25 × 42 px** | 49 × 84 px |
| Vaihingen | 3.06 m × 4.14 m | 6 × 8 px | **31 × 41 px** | — |

Reasons for 0.1 m:

1. **A car survives it.** At the land-cover 0.5 m a car is 5 px on its short axis, i.e. it vanishes
   at the bottleneck of a /32 encoder. At 0.1 m it is ~25 px, comfortably segmentable.
2. **It does not go below ISPRS's own annotation precision.** The ISPRS eroded-boundary protocol
   erodes by 3 px at native GSD = 0.15 m (Potsdam) / 0.27 m (Vaihingen). At 0.1 m a roof edge is
   still ~3 px wide, so we are training at roughly the precision the labels actually have; going to
   0.05 m would be fitting annotation noise.
3. **Neither city is upsampled.** 0.05 → 0.1 m is an exact 2× box average (`cv2.INTER_AREA`);
   0.09 → 0.1 m is 0.9×, essentially native. No detail is invented for either source.
4. **Context per crop.** A 512 px crop covers 51 m at 0.1 m — a building plus its surroundings.
   At 0.05 m the same crop covers 25.6 m, which is less than one Potsdam building footprint, so
   the model would rarely see a whole object.

0.2 m was rejected on point 2: a kerb or roof edge would be 1–1.5 px, finer than the labels claim.

### Windowed reads

Tiles are up to 6000 × 6000 × 3 (108 MB). `read_isprs` picks the crop window in *source* pixels and
reads only that window through rasterio, then resamples the window. Measured on
`top_potsdam_2_10_RGB.tif` (a tiled TIFF, 608 px blocks): **13.7 ms for a 1024 px window vs
281 ms for the full tile** — 20×. Doing it the other way round (decode the tile, resample, then
crop) would make the data loader the bottleneck.

## One model or two? Two.

Decided on measured band statistics, not assumption. Per-class mean band value, sampled over 6
tiles × 8 × 512 px windows per city:

| class | Potsdam RGB | Potsdam IRRG | Vaihingen IRRG |
|---|---|---|---|
| building | 111.4, 121.7, 120.5 | 110.0, 111.4, 121.7 | 113.9, 97.2, 86.5 |
| impervious | 102.5, 112.1, 108.3 | 97.9, 102.5, 112.1 | 103.6, 93.9, 94.4 |
| low_vegetation | 78.4, 81.9, 70.1 | 110.4, 78.4, 81.9 | 120.5, 65.1, 67.4 |
| tree | 72.7, 76.9, 66.8 | 108.2, 72.7, 76.9 | 140.3, 55.7, 60.0 |
| car | 113.7, 127.8, 133.6 | 100.8, 113.7, 127.8 | 111.1, 108.4, 105.3 |

The decisive number is channel 0 for `tree` relative to `building`:

- Potsdam **RGB**: 72.7 / 111.4 = **0.65** — vegetation is *darker* than roofs.
- Vaihingen **IRRG**: 140.3 / 113.9 = **1.23** — vegetation is *brighter* than roofs.

That is a sign flip on the single most discriminative cue for the two vegetation classes. A shared
first convolution would have to learn opposite responses for the same input channel, which it
cannot do. Training Potsdam-as-RGB together with Vaihingen-as-IRRG is therefore not a domain gap,
it is a contradiction. **Default: one model per city.**

The obvious fix — read Potsdam as IRRG from `4_Ortho_RGBIR` so both cities share a band space — is
available as the `isprs_potsdam_irrg` source, and it does narrow the gap: mean |per-class band
difference| against Vaihingen falls from **20.1 DN (Potsdam RGB) to 15.2 DN (Potsdam IRRG)**, and
the tree/building channel-0 ratio moves from 0.65 to 0.98. But 0.98 is still not 1.23, and 15.2 DN
is still a large residual (different sensor, different season, 5 cm vs 9 cm). So the joint run is
offered, not assumed:

```bash
# joint, on a shared IRRG band space — an experiment, not the default
.venv/bin/python -m training.segmentation.train_landcover --task isprs_urban_joint \
    --taxonomy isprs_urban --sources isprs_potsdam_irrg isprs_vaihingen
```

`isprs_potsdam` and `isprs_potsdam_irrg` hold out the *same* tiles (the split is hashed on the
scene id, not the filename), so mixing the two variants cannot leak test tiles into training.
This is asserted in `test_potsdam_rgb_and_irrg_hold_out_the_same_tiles`.

## Splits — **not the official benchmark split**

ISPRS's official test tiles are the ones whose labels were withheld from participants. We hold the
COMPLETE ground truth for all 71 tiles, so we define our own split and **scores from this task are
not comparable to the ISPRS leaderboard**. This is the same caveat as the DeepGlobe split recorded
in `project/qna.md` Q-025.

`isprs_split(tile_id)` uses the same sha1-mod-100 bucketing as `hash_split` but at **70/15/15**
instead of 90/5/5. The land-cover ratio is degenerate at this tile count — measured, it gives
Potsdam **37 train / 0 val / 1 test** — and with car at 1–2 % of pixels, a per-class IoU computed
from one tile is noise. Tile ids are `potsdam_<r>_<c>` and `vaihingen_area<n>`.

| source | train | val | test |
|---|---|---|---|
| `isprs_potsdam` | 29 | 5 | 4 |
| `isprs_potsdam_irrg` | 29 | 5 | 4 |
| `isprs_vaihingen` | 22 | 5 | 6 |

- Potsdam val: `2_10, 2_11, 6_11, 6_14, 7_13` — test: `2_12, 4_15, 5_12, 7_7`
- Vaihingen val: `area2, area3, area7, area20, area32` — test: `area8, area12, area13, area21,
  area22, area33`

Four Potsdam test tiles is 4 × 6000² = 144 Mpx of held-out label, so the tile count is small but
the evaluated area is not.

## Citation requirement

**Mandatory.** From `datasets/raw/isprs_potsdam_vaihingen/docs/complexscenes_revision_v4.pdf`,
§2.1.5 "Conditions of Use": the data are research-use only, must not be redistributed, and

> Any scientific papers whose results are based on the Vaihingen test data must cite
> [Cramer, 2010] and must contain the following acknowledgement:
> "The Vaihingen data set was provided by the German Society for Photogrammetry, Remote Sensing
> and Geoinformation (DGPF) [Cramer, 2010]:
> http://www.ifp.uni-stuttgart.de/dgpf/DKEP-Allg.html."

> Cramer, M., 2010. The DGPF test on digital aerial camera evaluation — overview and test design.
> *Photogrammetrie – Fernerkundung – Geoinformation* 2(2010): 73–82.

The same document also asks that the DGPF Secretary be informed by e-mail of any published paper
based on the Vaihingen data.

Note: the PDF shipped with our download is revision v4, which covers Vaihingen and Toronto only —
it contains no Potsdam section and therefore no Potsdam-specific conditions of use. Potsdam's terms
come from the ISPRS WG II/4 benchmark page and should be checked there before publication; do not
assume the Vaihingen wording covers it.

## Training command

Run these when the GPU is free (nothing here has been trained yet — the data layer and trainer
support are in place, no run has been launched). One model per city:

```bash
cd /home/natsu/dev/isro

# Potsdam (RGB, 5 cm)
.venv/bin/python -m training.segmentation.train_landcover \
    --task isprs_potsdam --taxonomy isprs_urban --sources isprs_potsdam \
    --arch unet --encoder resnet34 --crop 512 --batch 8 --epochs 40 \
    --samples-per-epoch 4000 --lr 3e-4 --workers 4 --max-val-tiles 5

# Vaihingen (IRRG, 9 cm)
.venv/bin/python -m training.segmentation.train_landcover \
    --task isprs_vaihingen --taxonomy isprs_urban --sources isprs_vaihingen \
    --arch unet --encoder resnet34 --crop 512 --batch 8 --epochs 40 \
    --samples-per-epoch 4000 --lr 3e-4 --workers 4 --max-val-tiles 5
```

Run them one at a time — the mem guard in `scripts/mem_guard.sh` and the 8 GB RTX 3070 will not
hold two. Progress: `scripts/watch_training.py` reads the epoch JSON lines unchanged (per-class IoU
is under `per_class`). Outputs land in `checkpoints/<task>_seg/` (`best.pt`, `last.pt`,
`report.json`); `--resume` continues from `last.pt`.

Sanity-check the wiring without a GPU first:

```bash
CUDA_VISIBLE_DEVICES="" .venv/bin/python -m training.segmentation.train_landcover \
    --task isprs_smoke --taxonomy isprs_urban --sources isprs_vaihingen \
    --crop 128 --batch 2 --workers 0 --encoder resnet18 --smoke
```

## Non-regression

`--taxonomy` defaults to `landcover`, and `SEG_TASKS["landcover"]` is
`(LANDCOVER_CLASSES, LANDCOVER_SOURCES, 0.5, LandCoverTiles)` — the previous hard-coded values.
The class count in the trainer is now read from the model head / the task's class list instead of a
module-level constant, so the existing land-cover runs produce byte-identical batches and the same
`report.json` shape. Verified by loading the same `deepglobe_landcover` sample through the old and
the new `datasets.py` side by side: identical tile index (714/51/38), identical whole-tile eval
tensor, and identical `read_lc` crops at three seeds.
