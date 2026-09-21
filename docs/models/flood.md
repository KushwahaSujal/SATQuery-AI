# Sen1Floods11 flood segmentation — a real checkpoint that does not serve

**The conclusion first: the checkpoint is genuine, its architecture is proven exact by a
`strict=True` load of all 118 state_dict entries, and both files match their delivered sha256
manifest — but it does not serve, because its training-time normalisation was never documented and
could not be recovered.** On a BatchNorm network a wrong input scale does not crash; it silently
predicts badly. Seventeen preprocessing schemes were measured on real Sen1Floods11
imagery — 7 scored on test, 10 selected on validation — and none reproduced the delivered
configuration (project/qna.md Q-041 §5, Q-043). Counting thresholds and splits separately the number
of scored combinations is higher; 17 is the count of distinct preprocessing schemes.

`flood_segmenter` is therefore registered as **NOT_CONFIGURED**. Its `predict()` returns a structured
refusal naming the missing normalisation, and **never returns a mask**. The refusal is
*unconditional*: `predict()` deliberately neither validates the input nor loads the weights first,
because the blocker is the missing normalisation rather than anything the caller did, and demanding a
valid 16-band stack before refusing would imply the request is fixable. `load_model()` does work and
does load the real checkpoint with `strict=True`, for whoever recovers the preprocessing, and
`validate_inputs()` enforces the 16-channel contract for that path. Not routed, and it must not be
described as a working flood capability.

All numbers below are copied from the delivered artefacts under `docs/models/flood/`, from
`results/evaluations/flood_preproc_recovery_20260920/`, and from project/qna.md Q-041 §5, Q-042 §5-§6 (the
test-above-validation gap and the unrecorded sweep cells) and Q-043 (corrections). Nothing
here is estimated. Anything unmeasured says `NOT MEASURED`; anything measured but not written down
says `NOT RECORDED`.

| Registry key | Checkpoint | Architecture | Serves? | Routed? | QNA |
|---|---|---|---|---|---|
| `flood_segmenter` | `checkpoints/flood_seg/{best.pt,last.pt}` | U-Net from scratch, 16-channel input, 2 classes | **no** | no | Q-041 §2, §5 |

Adapter: `backend/app/ml/adapters/flood_segmenter.py` (`FloodSegmenterAdapter`) — the registered
entry point, which refuses.
Architecture module: `backend/app/ml/adapters/flood_unet.py` (`UNetFromScratch`, `build_flood_model`).
Its `forward` requires both spatial extents to be multiples of 16 (four 2x pools, no padding in the
skip concatenations) and raises a specific `ValueError` otherwise; training was at 512x512.
Config: `configs/models.yaml`, key `flood_segmenter`, `threshold: null` (see "the 0.30 threshold"
below). Frontend: a chip already advertises this capability — see the last section.

## Provenance and integrity — this part is solid

| File | Bytes | sha256 | Manifest |
|---|---|---|---|
| `checkpoints/flood_seg/best.pt` | 23,442,311 | `5d6a26b6de8556153fc0a96078966f05e8ca0e159d0598a8f55770ee1f7274f6` | ✅ match |
| `checkpoints/flood_seg/last.pt` | 23,442,311 | `281c86c46f5504f9839a2fde906b11e378c59599a0eec2750cea468e82192554` | ✅ match |

Both verified here against `docs/models/flood/SHA256SUMS.json`, which also covers all six delivered
metadata and evaluation JSONs. The files were renamed from the delivered
`best_model.pt`/`last_model.pt` to this repo's `best.pt`/`last.pt` convention; contents are
untouched, which is what the hashes above prove. Delivery generated 2026-09-19T22:46:35.

## The 16 input channels — exact order, fixed by training

From `docs/models/flood/README.md`. Reordering these silently destroys the prediction.

| idx | channel | source |
|---|---|---|
| 0 | S1 VV | Sentinel-1 gamma0 |
| 1 | S1 VH | Sentinel-1 gamma0 |
| 2 | S2 B1 | Sentinel-2 L1C |
| 3 | S2 B2 | Sentinel-2 L1C |
| 4 | S2 B3 | Sentinel-2 L1C |
| 5 | S2 B4 | Sentinel-2 L1C |
| 6 | S2 B5 | Sentinel-2 L1C |
| 7 | S2 B6 | Sentinel-2 L1C |
| 8 | S2 B7 | Sentinel-2 L1C |
| 9 | S2 B8 | Sentinel-2 L1C |
| 10 | S2 B8A | Sentinel-2 L1C |
| 11 | S2 B9 | Sentinel-2 L1C |
| 12 | S2 B10 | Sentinel-2 L1C |
| 13 | S2 B11 | Sentinel-2 L1C |
| 14 | S2 B12 | Sentinel-2 L1C |
| 15 | DEM | Copernicus DEM |

Two S1 + thirteen S2 + one DEM = 16. `training_config.json` confirms the split as
`s1_channels: 2`, `s2_channels: 13`, `dem_channels: 1`, `total_input_channels: 16`.

**An RGB image cannot satisfy this model.** That alone rules out routing it from the grounding
pipeline, independently of the normalisation problem.

## Architecture — reconstructed from the checkpoint, not from training code

No training script was delivered. Every layer name, width and bias flag in
`backend/app/ml/adapters/flood_unet.py` was read off the 118 entries in
`best.pt["model_state_dict"]`:

| | |
|---|---|
| encoder widths | 16 → 32 → 64 → 128 (`base_channels: 16`) |
| bottleneck | 256 |
| decoder | `ConvTranspose2d` upsampling, skip concatenation |
| `DoubleConv` block | Conv3x3(bias=False) → BN → ReLU, twice; ReLUs at `block` indices 2 and 5 so the stored `block.0/1/3/4` line up |
| `output_layer` | 1x1 convolution → 2 classes |
| bias | **only** the 18 `DoubleConv` 3x3 convolutions are bias-free; the four `ConvTranspose2d` upsamplers (`up4`..`up1`) and `output_layer` each carry a bias, as PyTorch defaults them |
| training input size | 512 x 512 |
| `ignore_index` | 255 |

**`strict=True` is what proves the reconstruction, and it passes.** A single wrong channel count or
a spurious bias makes the load fail loudly rather than serve wrong numbers.

The cautionary precedent is `backend/app/ml/adapters/changeformer/network.py`: a reimplementation
there matched all 373 parameter names and loaded `strict=True`, yet measured IoU 0.019 against
0.726 because `num_heads` differed. **Parameter-name agreement is necessary, not sufficient** — and
here the numerical check could not be completed, because the preprocessing is unknown. That is the
whole of this document's problem.

## Checkpoint training state

Read from `best.pt` itself (`metrics` key) and `docs/models/flood/metadata/model_metadata.json`:

| | |
|---|---|
| epoch | 9 (of 10 trained) |
| train loss | 0.38368453477303704 |
| validation loss | 0.374064 (0.37406443758652763) |
| validation pixel accuracy | 0.9560150921344757 |
| **validation flood IoU** | **0.4358341431549679** |
| epoch wall time | 94.22612166404724 s |
| selected threshold | 0.30000000000000004, by `global_validation_flood_iou` |

The threshold-calibration table that produced 0.30 was **not delivered**
(`selected_flood_threshold.json` points at a CSV on the sender's Windows machine), so the
validation sweep behind that choice is `NOT AVAILABLE` here.

## Delivered metrics — 67 scenes, the sender's own numbers

From `docs/models/flood/evaluation/test_evaluation_report.json` and
`calibrated_test_evaluation_report.json`. **These are the sender's measurements, not ours.**

| Metric — **all pooled/global over the 15,152,361 valid pixels** of the 67 scenes | argmax | threshold 0.30 |
|---|---|---|
| test scenes | 67 | 67 |
| pixel accuracy | 0.9557442566211298 | 0.9506767295208978 |
| precision | 0.7872536536758193 | 0.7219667371157437 |
| recall | 0.7580408192637181 | 0.8164432430199405 |
| F1 | 0.7723711112038946 | 0.7663040045428137 |
| flood IoU (global) | 0.6291568390520142 | 0.621144923355964 |
| TP / FP / FN / TN | 1137676 / 307444 / 363135 / 13344106 | 1225327 / 471880 / 275484 / 13179670 |
| loss | 0.3963821826697285 | — |

Two things in the sender's own numbers deserve attention before anyone quotes them.

**The per-scene mean is far below the pooled figure.** `test_evaluation_report.json` records
`per_scene_mean_flood_iou` **0.40749901569615216** against `flood_iou_global`
**0.6291568390520142**, and `per_scene_mean_pixel_accuracy` 0.9548709410340038. A 0.22 IoU gap
means the pooled score is carried by a few large or easy scenes; the per-scene figure is the one
that describes what a user would see on one uploaded scene. This is the same pooled-vs-per-tile
effect recorded for the water segmenter in Q-035.

**The reported test IoU is 0.19 above the same checkpoint's validation IoU.** Validation flood IoU
at epoch 9 is 0.4358341431549679 (in the checkpoint, selection metric named
`global_validation_flood_iou`) while the reported global test IoU is 0.6291568390520142. A test
split scoring 0.19 IoU above validation on the same weights is unusual and the delivery does not
explain it. One reading that fits the numbers is that the checkpoint's "global" validation figure
is in fact a per-scene mean — it sits next to the test per-scene mean 0.4075, not next to the test
global 0.6292 — but the delivery never states which reduction each number uses, so this is
`NOT ESTABLISHED`. Either way, two differently-defined IoUs are being compared, and neither the
0.436 nor the 0.629 should be quoted without saying which reduction it is.

## The recovery attempt — measured, and it failed

Measured against the **official** Sen1Floods11 test split, 90 scenes, all four modalities verified
present. The sender's report uses a 67-scene "multimodal eligible" subset whose manifest lives on
his Windows machine (`training_config.json` names
`test_multimodal_eligible_scenes.csv`), so **the two scene sets are not identical and the
comparison is not apples to apples.**

Scripts: `scripts/flood_preproc_recovery/`. Per-scene confusion counts at both thresholds for all
90 scenes: `results/evaluations/flood_preproc_recovery_20260920/flood_per_scene.json` (do not
delete — it is what keeps these numbers reproducible if the imagery is reclaimed).

### Sweep 1 — seven schemes scored on test (`flood_recover_preproc.py`)

| scheme | global IoU | per-scene IoU | precision | recall |
|---|---|---|---|---|
| `raw` (no normalisation) | **0.5403** | 0.3557 | 0.5695 | 0.9133 |
| `per_scene_minmax` | 0.4528 | 0.3327 | 0.9742 | 0.4583 |
| `s2/10k` (S2 ÷ 10000) | 0.3043 | 0.1228 | 0.4279 | 0.5130 |
| `s2/10k+dem/1k` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` |
| `s1shift+s2/10k+dem/1k` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` |
| `per_scene_z` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` |
| `s2/10k+z(s1,dem)` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` | `NOT RECORDED` |
| *delivered, 67 scenes, for reference* | *0.6292* | *0.4075* | *0.7873* | *0.7580* |

All seven were run; Q-041 §5 records the numbers only for the three worth reporting (the best, the
highest-precision and the most obvious wrong guess). The four marked `NOT RECORDED` were scored and
lost with the console output — the scheme definitions are in the script, the numbers are not in the
transcript, and they are not reconstructed here.

### Sweep 2 — ten schemes selected on validation, then scored once on test

Selecting on test and quoting that number would be selection on the test set, so the ten schemes in
`flood_preproc_val_search.py` were ranked on the **89-scene official validation split** and only the
winner was scored on test.

| | |
|---|---|
| schemes swept | `raw`, `s2/3000`, `s2/4000`, `s1clip30_s2/10k_dem0`, `raw_dem0`, `raw_s1_0`, `s2/10k_s1/10_dem/100`, `div255`, `raw_dem_centered`, `s2_p2p98` |
| best on validation | **`s1clip30_s2/10k_dem0`** — S1 clipped to [−30, 0] dB then mapped to [0, 1], S2 ÷ 10000, **DEM replaced with zeros** |
| its validation IoU | **0.6307** |
| the other nine validation IoUs | `NOT RECORDED` |
| that scheme on test, argmax | **IoU 0.7034** |
| that scheme on test, threshold 0.30 | **IoU 0.7273** |

### Why this is not a reproduction — three reasons, none of them soft

1. **The winning scheme needs the DEM channel zeroed.** A model genuinely trained on DEM would not
   prefer having it removed. So the DEM handling is wrong or unknown — and a 16-channel model fed
   zeros in channel 15 **is not the model that was evaluated.** Whatever 0.7034 measures, it is not
   this checkpoint as its author ran it.
2. **The delivered 0.30 threshold does not transfer.** Under every scheme tried here, argmax and
   threshold 0.30 land in the same place: 0.5403 vs 0.5402 for `raw`, per-scene 0.3557 vs 0.3556.
   The delivery reports a genuine difference (IoU 0.6292 → 0.6211, precision 0.787 → 0.722, recall
   0.758 → 0.816). Different threshold behaviour means different probability calibration, so the
   0.30 threshold is provably not transferable. `configs/models.yaml` leaves `threshold: null`
   for exactly this reason.
3. **Scoring 0.703 ABOVE the reported 0.629 is evidence against us, not for us.** On a different
   scene set under a preprocessing the authors did not use, a higher number only confirms we are
   running a different experiment. A number obtained under the wrong configuration is not a better
   result; quoting it would be the single most dishonest thing available in this document.

### Subset attempts — no subset of the 90 reproduces 0.6292 either

If the 67-scene "multimodal eligible" subset were recoverable by a filter, some subset of the 90
official test scenes under the best raw-value preprocessing should land on 0.6292. None does.
Re-scored here from `flood_per_scene.json` (no model re-run needed) and matching Q-041 §5 exactly:

| subset | scenes | global IoU | per-scene IoU | precision | recall |
|---|---|---|---|---|---|
| all 90, argmax | 90 | 0.5403 | 0.3557 | 0.5695 | 0.9133 |
| all 90, threshold 0.30 | 90 | 0.5402 | 0.3556 | 0.5694 | 0.9133 |
| no label nodata | 16 | 0.5407 | 0.3277 | 0.5733 | 0.9047 |
| has some flood ground truth | 83 | 0.5443 | 0.3728 | 0.5740 | 0.9133 |
| no all-zero S2 pixels | 86 | 0.5479 | 0.3702 | 0.5701 | 0.9335 |
| `s2_min > 0` | 86 | 0.5479 | 0.3702 | 0.5701 | 0.9335 |
| no nodata AND flood ground truth | 14 | 0.5407 | 0.3512 | 0.5733 | 0.9047 |
| *target: delivered, 67 scenes* | *67* | *0.6292* | *0.4075* | *0.7873* | *0.7580* |

The last row of the table is the target and nothing comes near it. Note also that **no candidate
filter yields 67 scenes** — the closest are 83 and 86 — so the sender's subset is not any of these
conditions. The seventh row is in the probe script's candidate list but is not quoted in Q-041.

## Head-to-head — none exists, and none is possible yet

**No comparison against the live Grounding DINO + V4 + SAM 2 path exists for flood.** It could not
be run meaningfully: this model needs 16 co-registered channels that the pipeline never has, and the
model's own predictions are not trustworthy under unknown normalisation. The Q-025t/Q-026t-style
head-to-heads that justified routing roads and buildings have no analogue here.

## What would unblock this

One message to the sender. The missing information is small and specific:

1. **The per-channel normalisation constants** — per-channel mean and std, or the equivalent
   scaling, as applied at training time. Or simply the training script, which has all of the below.
2. **S1 clipping and scaling** — was VV/VH clipped (e.g. to [−30, 0] dB or [−50, 1]) and then
   rescaled, or fed as raw dB, or standardised?
3. **S2 scaling** — divided by 10000 (L1C reflectance convention), percentile-stretched, or raw DN?
4. **DEM handling** — raw metres, divided by a constant, standardised per scene, or dropped? This is
   the channel the recovery search wanted zeroed, so it is the most suspicious one.
5. **How label −1 became `ignore_index` 255** — Sen1Floods11 hand labels use −1 for no-data and the
   config declares `ignore_index: 255`, so a remap happened somewhere and it affects which pixels
   are scored.
6. Secondary but useful: the 67-scene **`test_multimodal_eligible_scenes.csv` manifest**, so the
   reported numbers can be reproduced on the same scenes rather than on the official 90.

With (1)–(5) this becomes a measurable capability in an afternoon: the checkpoint loads, the
architecture is proven, the imagery is on disk (`datasets/raw/sen1floods11`, 1.9 GB — kept
deliberately, do not let it be reclaimed). Without them, everything is guesswork.

## The frontend already advertises this capability

`frontend/src/components/query/QueryBar.tsx:18` ships an example chip

```
{ icon: "🌊", label: "Flood extent", query: "Detect flood extent in the eastern district" },
```

which **routes nowhere**. `frontend/FRONTEND_POLISH.md:153` (item L30) already flags it, alongside
the "Vehicle count" chip, with the instruction to check each chip against the router and replace
any that route to `unsupported`. Until the normalisation lands, that chip either needs wiring to an
explicit refusal or removing — as it stands it implies a capability that does not exist.

## Caveats recorded in the transcript

The training-time normalisation was never documented and was not recovered, so this model does not
serve and is registered `NOT_CONFIGURED` (Q-041 §5). The architecture is proven by a 118-entry
`strict=True` load, but the ChangeFormer precedent shows that parameter-name agreement is not
numerical agreement, and the numerical check could not be completed. The delivered 0.30 threshold
is provably not transferable. Our measurements use the official 90-scene test split; the delivery
uses a 67-scene subset whose manifest was not delivered, so the two are not comparable. The best
recovered scheme scores 0.7034 on test — **above** the reported 0.6292 — which is evidence of a
different experiment, not a better model, and must never be quoted as our result. The delivery's own
per-scene mean IoU (0.4075) is 0.22 below its pooled IoU (0.6292), and its reported test IoU is 0.19
above the same checkpoint's recorded validation IoU (0.4358) with no explanation of the difference
in reduction. Nothing in the serving path depends on any of this: no mask is ever returned.
