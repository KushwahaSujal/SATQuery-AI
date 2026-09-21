# Prithvi-EO-2.0 300M burn scars — blocked, and not foundation-model transfer

A burn-scar semantic segmenter on six HLS reflectance bands, delivered 2026-09-20
(project/qna.md Q-041 §6). The checkpoint is genuine, its hash matches the delivered manifest, and
its architecture is fully consistent with the delivered `model_config.yaml`. **It is NOT registered,
it has NO adapter, and it cannot be loaded in this repository today** — `terratorch`, `lightning`
and `einops` are absent from `.venv` and were deliberately not installed.

**Three things a reviewer will attack, stated before anyone asks:** it was trained **from scratch**,
so it is not evidence of geospatial-foundation-model adaptation; **two delivered metric files
disagree** for the same claimed test set; and the pooled IoU **hides per-scene collapse** — six test
scenes predict literally zero burn pixels. Each has its own section below.

All numbers below are copied from the delivered artefacts under `docs/models/burnscars/`, read out of
the checkpoint itself, or from project/qna.md Q-041 §6. Nothing here is estimated. Anything
unmeasured says `NOT MEASURED`.

| Registry key | Checkpoint | Architecture | Loadable? | Routed? | QNA |
|---|---|---|---|---|---|
| *(none — not registered)* | `checkpoints/burnscars_seg/PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt` | ViT-L (`prithvi_eo_v2_300`) + `UNetDecoder`, 2 classes | **no** | no | Q-041 §6 |

## Provenance and integrity

| | |
|---|---|
| Checkpoint | `checkpoints/burnscars_seg/PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt` |
| Size | 3.7 GB — 3,891,715,165 bytes exactly (3.62 GiB) |
| sha256 | `bb1ce3b5a9901415cbc33076c785aa234b80e06e1dd54ad4f5c2bbcea18a8dc8` |
| Manifest | ✅ matches `docs/models/burnscars/model_manifest.json` (hash **and** byte size) |
| Format | PyTorch Lightning `.ckpt` (not a bare `state_dict`) |
| Delivered evidence | README, manifest, two metric files, per-scene CSV, threshold sweep, 15 failure panels, `train_val_split_seed42.pt` |

The checkpoint was inspected with `torch.load(..., mmap=True, weights_only=True)`, so none of the
3.6 GB was ever resident (Q-041 §8).

## Architecture — as recorded inside the checkpoint

Everything in this section was read from the checkpoint, and separately cross-checked against
`docs/models/burnscars/model_config.yaml`. The two agree on the model.

| | |
|---|---|
| framework | PyTorch Lightning **2.6.6** |
| task class | `terratorch.tasks.SemanticSegmentationTask` |
| factory | `EncoderDecoderFactory` |
| backbone | `prithvi_eo_v2_300` — ViT-L: 24 blocks, width 1024, MLP 4096 |
| `patch_embed.proj` | a **Conv3d**, weight shape `(1024, 6, 1, 16, 16)` + bias `(1024,)` |
| `pos_embed` | `(1, 197, 1024)` = 1 cls token + 14 x 14 patches → **trained at 224 x 224** |
| necks | `SelectIndices(indices=[5, 11, 17, 23])` → `ReshapeTokensToImage` → `LearnedInterpolateToPyramidal` |
| decoder | `UNetDecoder`, channels 512 / 256 / 128 / 64 |
| head | 1x1 `Conv2d(64 → 2)` |
| state_dict tensors | 355 — encoder 294, decoder 48, neck 11, head 2 |
| parameters | **324,411,275** |
| `epoch` | 8 (zero-indexed), `global_step` 3888 |

`global_step` 3888 = 9 epochs x 432 scenes at `batch_size: 1`, which independently confirms the
432-scene training split and the batch size from the yaml.

The decoder's stored names are `model.decoder.decoder.blocks.{0..3}.conv{1,2}.{0,1}` — Conv3x3
followed by BatchNorm per sub-block, block 0 taking 2048 input channels (1024 upsampled + 1024
skip). That is exactly `segmentation_models_pytorch`'s `UnetDecoder` naming, which matters for the
vendoring option discussed under "Runtime blocker".

### Checkpoint selection — on `val/mIoU`, not on burn IoU

From the `ModelCheckpoint` callback state inside the checkpoint:

| | |
|---|---|
| monitored metric | `val/mIoU`, mode `max` |
| best score | **0.8308** at `burnscars-rigorous-epoch=08.ckpt` |
| second best | 0.8276 at epoch 06 |

**`val/mIoU` is the mean IoU over both classes**, and class 0 (`Not burned`) dominates the pixels,
so 0.8308 is not a burn-scar IoU and must never be quoted as one. The burn-scar IoU on the held-out
test set is 0.6567 (see below); the burn-scar IoU on the internal validation split at threshold 0.40
is 0.7127750719799246 (from the threshold sweep).

### Training hyperparameters, and where the yaml and the run disagree

| | `model_config.yaml` | checkpoint |
|---|---|---|
| optimiser | `torch.optim.AdamW`, lr **1e-4** | task hparam `lr` = **1e-3**; scheduler `_last_lr` = **1e-4** |
| scheduler | `ReduceLROnPlateau`, factor 0.5, patience 4 | same, `last_epoch` 8, never reduced |
| max epochs | **50**, `EarlyStopping` on `val/loss` patience 15 | ran to epoch 8; manifest says 10 total |
| seed | `seed_everything: 2` | manifest reports `split_seed: 42` |
| precision | `bf16-mixed` | — |
| loss / ignore | `ce`, `ignore_index: -1` | `ce`, `ignore_index: -1` |
| batch size / workers | 1 / 2 | (consistent with `global_step` 3888) |
| train augmentation | `albumentations.D4` + `ToTensorV2` | — |
| no-data handling | `no_data_replace: 0`, `no_label_replace: -1` | — |

The delivered yaml is a **configuration, not a run log**: it allows 50 epochs where the manifest
reports 10, and its `seed_everything: 2` is a different thing from the manifest's `split_seed: 42`.
The Lightning CLI optimiser (lr 1e-4) overrides the task's default lr of 1e-3, and the scheduler's
`_last_lr` confirms 1e-4 was the lr in force through epoch 8. Do not quote the yaml as evidence of
what was run without these qualifications.

## Input bands and normalisation — six HLS bands

From `model_config.yaml` (`dataset_bands` == `output_bands`), `rgb_indices: [2, 1, 0]`:

| idx | band | mean | std |
|---|---|---|---|
| 0 | `BLUE` | 0.033349706741586264 | 0.02269135568823774 |
| 1 | `GREEN` | 0.05701185520536176 | 0.026807560223070237 |
| 2 | `RED` | 0.05889748132001316 | 0.04004109844362779 |
| 3 | `NIR_NARROW` | 0.2323245113436119 | 0.07791732423672691 |
| 4 | `SWIR_1` | 0.1972854853760658 | 0.08708738838140137 |
| 5 | `SWIR_2` | 0.11944914225186566 | 0.07241979477437814 |

Unlike the flood model (`docs/models/flood.md`), **the normalisation here was delivered** — these
are reflectance-scale constants, so inputs are HLS surface reflectance in [0, 1], not DN. Classes:
`0 = Not burned`, `1 = Burn scar`. Inference threshold **0.40**, selected on the internal
validation split.

## Splits

| split | scenes | note |
|---|---|---|
| train | 432 | from the original HLS Burn Scars *training* partition, seed 42 |
| internal validation | 108 | from the same partition; used for threshold selection |
| held-out test | 264 | **the dataset's original validation partition, reused as test** |

Split artefact: `docs/models/burnscars/train_val_split_seed42.pt` (3 KB). Scene tiles are 512 x 512
with **at most** 262,144 valid pixels each: 102 of the 264 scenes carry nodata, the smallest having
159,741 valid pixels (61% of the tile), for **68,627,952** valid pixels in total — not 264 x 262,144
= 69,206,016 (`per_scene_metrics_threshold_040.csv`).

**The HLS Burn Scars dataset provides no official independent test split.** The delivery is explicit
about this: the 264-scene original validation partition was treated as the held-out test set after
carving a new 432/108 split out of the original training partition. The 264 scenes were not used for
threshold selection, so the threshold is honest — but these are **not** benchmark-comparable numbers
and must not be quoted against published HLS Burn Scars leaderboards. This is the same class of
caveat as the DeepGlobe and ISPRS splits (Q-025t and Q-036, `docs/models/isprs_urban.md`).

## Problem 1 — it was trained from scratch

`backbone_pretrained: false`. `freeze_backbone: false`. Both in the delivered `model_config.yaml`
**and** in the checkpoint's own `hyper_parameters`, so this is not a documentation slip.

**A Prithvi-EO-2.0 300M ViT-L trained from scratch on 432 scenes is not evidence of
geospatial-foundation-model adaptation.** The pretrained backbone is the entire point of Prithvi:
what makes "we adapted a geospatial foundation model" a claim worth making is the pretraining on
large-scale HLS data, and none of it is present here. What was trained is a Prithvi-*shaped* ViT-L —
324 M parameters initialised randomly and fitted to 432 scenes.

**This must never be described as foundation-model transfer, fine-tuning, or adaptation**, in the
paper, the demo, the README or a slide. The honest description is: "a 324 M-parameter ViT-L +
U-Net-decoder segmenter trained from scratch on HLS Burn Scars".

It is a legitimate segmentation result and an illegitimate transfer-learning claim. Both halves of
that sentence are true and the second one is the one a reviewer will reach for first.

## Problem 2 — two delivered metric files disagree for the same claimed test set

Both files claim **264 test scenes** and **68,627,952 valid pixels**. Their confusion matrices are
different, and so are their precision and recall.

| | `final_test_metrics.json` | `final_test_metrics_threshold_040.json` |
|---|---|---|
| threshold stated | *none stated* | 0.4 |
| precision (burn scar) | 0.824592170131026 | 0.785723297356267 |
| recall (burn scar) | 0.7600844694841001 | 0.7999760727514289 |
| F1 (burn scar) | 0.7910253568538832 | 0.7927856307916421 |
| burn-scar IoU | *not reported* | 0.6567065891632144 |
| pixel accuracy | *not reported* | 0.9612902043179141 |
| ROC-AUC | 0.9774894441090206 | 0.9774894441090206 |
| TN | 61248239 | 60889458 |
| FP | 1027123 | 1385904 |
| FN | 1524085 | 1270670 |
| TP | 4828505 | 5081920 |

Both matrices sum to 68,627,952, so neither is malformed.

**Most likely the first file is an argmax / threshold-0.5 run that was mislabelled, not fabricated.**
Two pieces of evidence point that way: the ROC-AUC is **identical** in both files, and ROC-AUC is
threshold-independent — so both were almost certainly computed from the same probability maps; and
the first file's precision is *higher* and recall *lower* than the second's, which is exactly the
direction a higher decision threshold moves them. The threshold sweep confirms the magnitude: at
0.50 the sweep records precision 0.857 / recall 0.800, at 0.40 precision 0.824 / recall 0.841, on
the *internal validation* split.

**Only one of these may ever be quoted, and it is
`final_test_metrics_threshold_040.json`** — because it is the file whose numbers
`model_manifest.json` embeds verbatim, it is the only one that states its threshold, and it is the
only one that reports IoU and pixel accuracy at all. The canonical held-out test numbers are
therefore:

| Metric — **pooled/global over all 68,627,952 valid pixels** of the 264 held-out scenes, threshold 0.40 | Value |
|---|---|
| precision (burn scar) | 0.785723297356267 |
| recall (burn scar) | 0.7999760727514289 |
| F1 (burn scar) | 0.7927856307916421 |
| burn-scar IoU | 0.6567065891632144 |
| pixel accuracy | 0.9612902043179141 |
| ROC-AUC | 0.9774894441090206 |
| valid pixels | 68,627,952 |

`final_test_metrics.json` should be treated as unlabelled and not cited. It has not been
reconciled — that reconciliation needs the scoring script, which was not delivered.

## Problem 3 — the pooled IoU hides per-scene collapse

IoU 0.6567 is **pooled over 68.6 M pixels**. Per scene, from
`docs/models/burnscars/per_scene_metrics_threshold_040.csv` (all 264 rows, threshold 0.40):

| | |
|---|---|
| scenes with burn IoU **exactly 0.0** | **10** of 264 |
| scenes with burn IoU < 0.01 | 11 |
| scenes with burn IoU < 0.05 | 23 |
| scenes with burn IoU < 0.10 | 30 |
| scenes predicting **literally zero** burn pixels | **6** |
| scenes with zero true positives | 10 |
| mean per-scene burn IoU | 0.5634 (computed here from the CSV; **not** a delivered figure) |
| median per-scene burn IoU | 0.6584 (computed here; **not** a delivered figure) |
| scenes with no ground-truth burn at all | 0 — every test scene contains burn pixels |

The six scenes that predict **no burn pixels whatsoever**, against real burn scars covering 1.4 % to
5.2 % of the scene:

| scene | GT burn px | predicted burn px | GT burn fraction | burn IoU |
|---|---|---|---|---|
| 193 | 3,874 | **0** | 1.478 % | 0.0 |
| 198 | 11,873 | **0** | 4.529 % | 0.0 |
| 203 | 13,615 | **0** | 5.194 % | 0.0 |
| 223 | 3,769 | **0** | 1.438 % | 0.0 |
| 224 | 10,252 | **0** | 3.911 % | 0.0 |
| 234 | 5,888 | **0** | 2.246 % | 0.0 |

Four more scenes predict a handful of burn pixels, **none of which are correct** (zero true
positives), so their IoU is also exactly 0:

| scene | GT burn px | predicted burn px | true positives | predicted fraction |
|---|---|---|---|---|
| 211 | 3,086 | 2,083 | **0** | 0.795 % |
| 236 | 3,340 | 404 | **0** | 0.154 % |
| 260 | 3,219 | 122 | **0** | 0.047 % |
| 261 | 3,598 | 90 | **0** | 0.034 % |

And five more in the worst-15 list are effectively blind on large burns — these are the expensive
failures, because the burn is not small:

| scene | GT burn fraction | predicted fraction | burn recall | burn IoU |
|---|---|---|---|---|
| 222 | 13.567 % | 0.240 % | 0.0177 | 0.0177 |
| 248 | 7.805 % | 0.085 % | 0.0001 | 0.0001 |
| 45 | 7.565 % | 1.166 % | 0.0177 | 0.0156 |
| 254 | 6.468 % | 0.116 % | 0.0180 | 0.0180 |
| 252 | 2.328 % | 0.029 % | 0.0126 | 0.0126 |

Full rows for all fifteen: `docs/models/burnscars/failure_analysis/lowest_recall_summary.csv`, with
per-scene visual panels alongside it. **Note the failure mode: it is one-sided.** Where these
scenes go wrong the model under-predicts, and scenes 222, 252 and 254 have burn precision 1.0 with
recall under 0.02 — every pixel it called burn was burn, and it called almost none. 10 of 264
scenes (3.8 %) are missed entirely, which a pooled recall of 0.800 does not reveal.

`failure_analysis/failure_panel_index.csv` should not be used for numbers: its `valid_pixels`,
`ground_truth_burn_pixels` and confusion columns disagree with `lowest_recall_summary.csv` for the
same scenes (e.g. scene 248 shows `valid_pixels = 2`), so those columns are counting something else.
The panel PNG paths in it are fine.

## Internal-validation threshold sweep — where 0.40 comes from

From `docs/models/burnscars/internal_validation_thresholds.csv`, 108 internal-validation scenes.
This is a genuinely useful table: it shows burn IoU peaking at 0.40 and the precision/recall
trade-off either side of it.

| threshold | precision | recall | F1 | burn IoU | pixel acc | pred. burn frac |
|---|---|---|---|---|---|---|
| 0.10 | 0.672027 | 0.928165 | 0.779596 | 0.638802 | 0.937224 | 0.165207 |
| 0.15 | 0.709879 | 0.911135 | 0.798014 | 0.663912 | 0.944828 | 0.153529 |
| 0.20 | 0.738175 | 0.897472 | 0.810067 | 0.680767 | 0.949659 | 0.145430 |
| 0.25 | 0.762508 | 0.884955 | 0.819181 | 0.693739 | 0.953269 | 0.138825 |
| 0.30 | 0.784632 | 0.872221 | 0.826111 | 0.703739 | 0.956078 | 0.132969 |
| 0.35 | 0.804907 | 0.857879 | 0.830549 | 0.710205 | 0.958128 | 0.127489 |
| **0.40** | **0.823664** | **0.841128** | **0.832304** | **0.712775** | 0.959456 | 0.122153 |
| 0.45 | 0.841121 | 0.821583 | 0.831237 | 0.711211 | 0.960095 | 0.116838 |
| 0.50 | 0.857352 | 0.799610 | 0.827475 | 0.705720 | **0.960116** | 0.111560 |
| 0.55 | 0.872462 | 0.775348 | 0.821043 | 0.696415 | 0.959570 | 0.106302 |
| 0.60 | 0.886338 | 0.748779 | 0.811772 | 0.683178 | 0.958464 | 0.101052 |
| 0.65 | 0.899361 | 0.720123 | 0.799823 | 0.666421 | 0.956883 | 0.095778 |
| 0.70 | 0.911976 | 0.688893 | 0.784891 | 0.645944 | 0.954833 | 0.090357 |
| 0.75 | 0.923928 | 0.653921 | 0.765822 | 0.620511 | 0.952163 | 0.084660 |
| 0.80 | 0.936319 | 0.612899 | 0.740850 | 0.588373 | 0.948710 | 0.078299 |
| 0.85 | 0.950477 | 0.561648 | 0.706070 | 0.545679 | 0.944065 | 0.070683 |
| 0.90 | 0.966655 | 0.490035 | 0.650371 | 0.481889 | 0.936978 | 0.060638 |

Both F1 (0.832304) and burn IoU (0.712775) peak at 0.40, and the peak is flat: 0.35 and 0.45 are
within 0.003 IoU, so the choice is not over-tuned. Pixel accuracy peaks at 0.50 instead, which is
why it is the wrong metric to select on for a **11.96 %**-foreground class (that is this
internal-validation split's burn fraction, derived two independent ways from every row of the sweep;
9.26 % is the *held-out test* split's figure). Note that the internal-validation
IoU at 0.40 (0.7128) is **0.056 above** the held-out test IoU (0.6567) — the expected direction, and
a reminder that the threshold was chosen on the easier split.

## Runtime blocker — it cannot be loaded here

| package | status in `.venv` |
|---|---|
| `terratorch` | **MISSING** |
| `lightning` | **MISSING** |
| `pytorch_lightning` | **MISSING** |
| `einops` | **MISSING** |
| `timm` | present, 1.0.29 |
| `segmentation_models_pytorch` | present, 0.5.0 |
| `albumentations` | present, 2.0.8 |
| `torch` / `torchvision` | 2.14.0+cu130 / 0.29.0+cu130 |

**Why `terratorch` was not installed:** this venv is `torch 2.14.0+cu130`, `terratorch` pins
tightly — **but a resolve-only probe on 2026-09-21 disproved the concern** (Q-045): it resolves to the
same torch 2.14.0 / torchvision 0.29.0 wheels already installed, because `+cu130` is PyPI's default
build string rather than a custom pin. The superseded reasoning was that it would downgrade
torch/torchvision underneath the eight working
adapters. Trading eight verified models for one unverified one is not a unilateral call (Q-041 §3).

`smp` 0.5.0's `UnetDecoder` already produces the exact decoder parameter names the checkpoint
stores, so hand-vendoring a minimal Prithvi ViT + the three necks is a real option — following the
`changeformer/network.py` precedent. **But the ChangeFormer lesson applies in full force:** matching
parameter names is not matching computation (IoU 0.019 vs 0.726 there, from one differing
`num_heads`). Any vendoring must be verified numerically against
`docs/models/burnscars/per_scene_metrics_threshold_040.csv`, per scene, not merely load cleanly.

The three open options, unchanged from the handoff: install `terratorch` in a **separate** venv for
one offline verification run; vendor a minimal Prithvi ViT + necks and verify numerically; or shelve
the model and keep only the documented evidence. No decision has been made and the model stays
unregistered until one is.

## Checkpoint size — two thirds of it is optimiser state

| | |
|---|---|
| file | 3,891,715,165 bytes |
| weights | 324,411,275 parameters, i.e. ~1.30 GB at fp32 (1.21 GiB) |
| optimiser | one AdamW state, **327 parameter entries**, each with `step`, `exp_avg`, `exp_avg_sq` |

Two AdamW moments at fp32 over 324 M parameters is ~2.6 GB, which accounts for the remaining two
thirds of the file. **Stripping the checkpoint to `state_dict` alone gives roughly 1.2 GB, or about
650 MB at fp16.** Worth doing before this ever ships, and it costs nothing because the optimiser
state is only needed to resume training — which nothing here plans to do.

## Head-to-head — none exists

**No comparison against the live Grounding DINO + V4 + SAM 2 path exists, and none can be run
today** — the model cannot be loaded. The pipeline also has no burn-scar capability and no
six-band HLS input path, so there is no baseline to compare against even in principle. Every number
in this document is either the sender's measurement, re-read from the delivered artefacts, or was
derived here from those artefacts and labelled as such (the per-scene counts, the mean/median IoU, the
355-tensor census, the parameter count and the `val/mIoU` callback state). **Nothing here was measured
by running this model in this repository** — it cannot be run at all without `terratorch`.

## Caveats recorded in the transcript

Trained from scratch (`backbone_pretrained: false`, `freeze_backbone: false`) on 432 scenes, so it
is a Prithvi-shaped ViT-L and **not** foundation-model adaptation — a legitimate segmentation result
and an illegitimate transfer-learning claim (Q-041 §6.2, §9). Two delivered metric files disagree
for the same claimed 264-scene test set; only `final_test_metrics_threshold_040.json` may be quoted
(Q-041 §6.1). The pooled IoU 0.6567 hides 10 scenes at IoU 0.0, six of which predict no burn pixels
at all against 1.4–5.2 % ground-truth burn (Q-042 §1, superseding Q-041 §6.3). The dataset ships no official independent
test split, so the original 264-scene validation partition was reused as the held-out test set and
these numbers are not leaderboard-comparable. The checkpoint was selected on `val/mIoU` 0.8308, a
two-class mean dominated by the unburned class, not on burn IoU. The delivered `model_config.yaml`
is a configuration rather than a run log and disagrees with the manifest on epochs and seed. Nothing
in this document was measured by running the model here: `terratorch`, `lightning` and `einops` are
absent and were deliberately not installed, so the model is unregistered, adapterless and
unloadable, and nothing in the serving path depends on it.
