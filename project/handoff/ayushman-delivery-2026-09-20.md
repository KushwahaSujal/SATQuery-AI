# Ayushman delivery 2026-09-20 — state and TODO

**Status: integration complete, 2026-09-20.** Work was paused at ~19:40 for a reboot and resumed the
same day. Everything below the "DONE" heading near the end records what actually shipped; the analysis
above it is the original investigation and still stands except where Q-042 corrects it. Branch
`prototype`, committed locally, **not pushed**.

Source: `~/Downloads/ayushman/` (~22 GB of archives, with duplicates).

---

## What the delivery actually contained

Three **new** models, plus two that were already integrated.

| # | Model | New? | Runnable today? |
|---|---|---|---|
| 1 | EuroSAT EfficientNet-B0 land-cover classifier, 10 classes | **new** | **yes** |
| 2 | Sen1Floods11 flood U-Net, 16 channels (S1 VV/VH + 13 S2 + DEM) | **new** | **no — preprocessing unknown** |
| 3 | Prithvi-EO-2.0 300M burn-scar segmenter | **new** | **no — needs `terratorch`** |
| 4 | ChangeFormer v6 LEVIR checkpoint + reports | already in repo | yes (unchanged) |
| 5 | LocateAnything-3B (6.2 GB) | already in `checkpoints/` | n/a |

**EuroSAT was hidden.** `drive-download-…-003.zip` is a 1 GB superset bundle that contains a nested
`eurosat_efficientnet_b0.zip`. Unzipping only the obvious top-level archives misses it entirely.

### Checkpoint hashes — all verified against the delivered manifests

| File | SHA-256 | Manifest match |
|---|---|---|
| `checkpoints/burnscars_seg/PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt` | `bb1ce3b5…a8dc8` | ✅ |
| `checkpoints/flood_seg/best.pt` | `5d6a26b6…274f6` | ✅ |
| `checkpoints/flood_seg/last.pt` | `281c86c4…92554` | ✅ |
| `checkpoints/eurosat_efficientnet_b0/best_model.pt` | `dbbfa69d48baa47ee813ae0465ce46e72c412159a5564e8e26d6d5044f012347` | no manifest supplied — hash recorded here |

---

## Files already changed / added (uncommitted)

**Checkpoints** (gitignored, staged on disk):
- `checkpoints/flood_seg/{best.pt,last.pt}` — renamed from `best_model.pt`/`last_model.pt` to the
  repo's `best.pt`/`last.pt` convention.
- `checkpoints/burnscars_seg/PrithviEO2_300M_BurnScars_from_scratch_epoch08.ckpt` (3.7 GB).
- `checkpoints/eurosat_efficientnet_b0/best_model.pt` — kept the delivered filename, which the
  delivery README names explicitly.

**Evidence, committable:**
- `docs/models/flood/` — README, metadata, 3 evaluation reports, SHA256SUMS.
- `docs/models/burnscars/` — README, manifest, metrics, per-scene CSV, threshold sweep,
  15 failure panels (22 MB), `train_val_split_seed42.pt`.
- `docs/models/eurosat/` — README, inference config, metrics, classification report, 4 figures,
  per-sample predictions (`y_true/y_pred/y_prob.npy`).

**Code written:**
- `backend/app/ml/adapters/eurosat.py` — **complete, not yet registered or tested.**
- `backend/app/ml/adapters/flood_unet.py` — **complete.** The 16-channel `UNetFromScratch`
  architecture, reconstructed from the checkpoint's 118 state_dict entries; loads `strict=True`.

**Measurement artefacts rescued from tmpfs:**
- `scripts/flood_preproc_recovery/{flood_recover_preproc,flood_subset_probe,flood_preproc_val_search}.py`
- `results/evaluations/flood_preproc_recovery_20260920/flood_per_scene.json` — per-scene TP/FP/FN/TN
  at thresholds 0.5 and 0.30 for all 90 official test scenes, so subsets can be re-scored without
  re-running the model.

---

## 1. EuroSAT — works, and it is the mandatory-requirement-#1 evidence

`memory.md` lists "RS adaptation evidence (BigEarthNet) — mandatory req #1" as still open. **This
model closes it** with a real measured score, and does so more cleanly than BigEarthNet would have.

Delivered numbers, **independently recomputed** from the delivered per-sample predictions
(`docs/models/eurosat/evaluation/predictions/`) and matching to 10 decimal places:

| Metric | Delivered | Recomputed here |
|---|---|---|
| accuracy (4050 test samples) | 0.9832098765432099 | 0.9832098765 |
| balanced accuracy | 0.9824222222222222 | 0.9824222222 |

Also checked: `y_prob` rows sum to 1, and `argmax(y_prob) == y_pred` for all 4050 rows. So the
report is internally consistent and not hand-written.

Verified separately: `torchvision.efficientnet_b0` with `classifier[1] → Linear(1280, 10)` loads the
`model_state_dict` with **`strict=True`** and forwards to `(1, 10)`.

**Caveat to keep:** the EuroSAT images are not in this repo (`datasets/raw/` has no `eurosat`), so
the score has NOT been re-measured from pixels here — only recomputed from the delivered
predictions. Tiles are Sentinel-2 at 10 m/px, 64×64, upsampled to 224. Scene-level only: one label
per tile, no localisation. Do not route it from the grounding pipeline.

## 2. Flood — real checkpoint, but the preprocessing is NOT recovered. Do not ship as working.

The architecture is certain: `flood_unet.py` loads the 118-entry state_dict with `strict=True`
(encoder 16→32→64→128, bottleneck 256, transposed-conv decoder, `output_layer` 1×1 → 2 classes,
all convs `bias=False`).

**The problem:** the delivery documents the 16-channel order but **never states the training-time
normalisation**, and `training_config.json`, `model_metadata.json` and the checkpoint's embedded
`config` all omit it. Wrong normalisation on a BatchNorm network does not crash — it silently
predicts badly.

Measured on the **official** Sen1Floods11 test split (90 scenes; all four modalities present and
verified). Ayushman's report uses a 67-scene "multimodal eligible" subset whose manifest lives on
his Windows machine, so the sets are not identical.

Sweep 1 — seven schemes, scored on test (see `flood_recover_preproc.py`):

| scheme | global IoU | per-scene IoU | prec | rec |
|---|---|---|---|---|
| raw (no normalisation) | 0.5403 | 0.3557 | 0.5695 | 0.9133 |
| per-scene min-max | 0.4528 | 0.3327 | 0.9742 | 0.4583 |
| s2/10k | 0.3043 | 0.1228 | 0.4279 | 0.5130 |
| *(delivered, 67 scenes)* | *0.6292* | *0.4075* | *0.7873* | *0.7580* |

Sweep 2 — ten schemes selected on **validation** (89 scenes), then scored once on test, which is the
only defensible order (`flood_preproc_val_search.py`):

- Best on validation: **`s1clip30_s2/10k_dem0`** (S1 clipped to [−30, 0] dB → [0, 1],
  S2 ÷ 10000, **DEM replaced with zeros**) — validation IoU 0.6307.
- That scheme on the 90 test scenes: **IoU 0.7034 at argmax, 0.7273 at threshold 0.30.**

**Why this is not a reproduction, and why I stopped:**

1. The winner needs the **DEM channel zeroed out** to do best. A model genuinely trained on DEM
   would not prefer having it removed, so the DEM scaling is definitely wrong/unknown — and a
   16-channel model fed zeros in channel 15 is not the model that was evaluated.
2. Under my preprocessing, **argmax and threshold 0.30 give nearly identical results**
   (0.5403 vs 0.5402 for raw). The delivery reports a real difference (0.6292 → 0.6211, with
   precision moving 0.787 → 0.722 and recall 0.758 → 0.816). Different threshold behaviour means the
   probability calibration differs, so **the delivered 0.30 threshold is not transferable.**
3. Scores *above* the reported ones (0.703 vs 0.629) are not good news — on a different scene set
   with a different preprocessing, they just confirm we are not running the delivered configuration.

**Conclusion: the flood model must not ship as a verified capability.** No subset of the 90 test
scenes reproduced 0.6292 (tried: no-label-nodata, has-flood-GT, no-all-zero-S2, s2_min>0).

## 3. Burn scars — blocked on `terratorch`, and I deliberately did not install it

Checkpoint is genuine and fully consistent with the delivered `model_config.yaml`: PL 2.6.6,
`terratorch.tasks.SemanticSegmentationTask`, `EncoderDecoderFactory`, backbone
`prithvi_eo_v2_300` (ViT-L: 24 blocks, width 1024, `patch_embed` is a **Conv3d** `(1024, 6, 1, 16, 16)`,
`pos_embed` 197 → trained at 224×224), necks `SelectIndices[5,11,17,23]` → `ReshapeTokensToImage` →
`LearnedInterpolateToPyramidal`, decoder `UNetDecoder` 512/256/128/64, head 1×1 → 2 classes.
355 state_dict tensors, ~324.4 M params.

Missing from `.venv`: **`terratorch`, `lightning`, `einops`** (`timm` 1.0.29 and
`segmentation_models_pytorch` 0.5.0 are present, and smp's `UnetDecoder` already produces the exact
decoder parameter names).

**Why I did not install it:** this venv is `torch 2.14.0+cu130`. `terratorch` pins tightly and a
plain `pip install` risks downgrading torch/torchvision, which would break the eight working
adapters. That trade is the user's call, not mine.

Two honest problems in the delivered burn-scar evidence, which must be reconciled before anything is
quoted in the paper or demo:

1. **Two metric files disagree for the same claimed test set.** Both say 264 scenes and
   68,627,952 valid pixels, but `final_test_metrics.json` gives precision 0.8246 / recall 0.7601 /
   F1 0.7910 with confusion matrix `[[61248239, 1027123], [1524085, 4828505]]`, while
   `final_test_metrics_threshold_040.json` (the one the manifest embeds) gives precision 0.7857 /
   recall 0.8000 / F1 0.7928 / IoU 0.6567 with a different matrix. The first is most likely the
   argmax/0.5 run mislabelled, not fabricated — but **quote one, and say which.**
2. **Trained from scratch** (`backbone_pretrained: false`, `freeze_backbone: false`) on 432 scenes.
   A Prithvi-EO-2.0 300M ViT-L trained from scratch on 432 scenes is **not** evidence of
   geospatial-foundation-model adaptation — the pretrained backbone is the entire point of Prithvi.
   Do not describe it as foundation-model transfer anywhere. This is the single most likely thing a
   reviewer will attack.
3. **Per-scene collapse hidden by the global number.** Corrected in Q-042 §1 — recount from the
   full 264-row `per_scene_metrics_threshold_040.csv`: **10 scenes sit at burn IoU exactly 0.0**, of
   which **6 predict literally zero burn pixels** (193, 198, 203, 223, 224, 234) on scenes that are
   1.438%–5.194% burned; the other 4 (211, 236, 260, 261) predict only false positives. 11 scenes are
   below IoU 0.01, 23 below 0.05, 30 below 0.10. Mean per-scene burn IoU is 0.5634 and the median
   0.6584 against the pooled 0.6567, so here the pooled figure is *not* inflated — the real criticism
   is the 10 complete misses. Take per-scene numbers from `per_scene_metrics_threshold_040.csv`, never
   from `lowest_recall_summary.csv` (15 rows = lowest-recall extract) or from
   `failure_panel_index.csv` (its pixel columns are broken).

Also: the checkpoint is 3.6 GB of which ~2/3 is AdamW optimiser state. Stripping to `state_dict`
(optionally fp16) gives roughly 1.2 GB / 650 MB.

---

## Coordination already done

- `sen1floods11` (1.9 GB) was on the other session's delete list. **Asked them to keep it; they
  confirmed it is intact and removed it from the list permanently.** It is required for any further
  flood work — do not let it be deleted.
- Their revised 153 GB cleanup is agreed and is being held until this work is done.
- `prototype` has moved to `d0daed7` (their Q-038…Q-040 work). My working tree has not been rebased
  onto it yet — **do this before committing.**
- Agreed with them: burn-scar and flood get registered **without** routing, for the same reason
  crater detection is unrouted — nothing in the pipeline distinguishes sensor/domain, so a
  Sentinel-scale multispectral model must not auto-fire on an aerial RGB photo.

---

## DONE — integration completed 2026-09-20 (later the same day)

Tests: `pytest -m "not models" -q` → **430 passed, 3 failed** (the 3 are the pre-existing GDAL
failures in `tests/unit/test_geotiff_georeferencing.py`). Baseline before this work was 394 + the
same 3, so **+36 tests, no regressions**. `pytest tests/models/test_eurosat_adapter.py -q` → 2 passed
against the real checkpoint. `scripts/verify_checkpoints.py` → exit 0, both new models listed OK.

**Also fixed, pre-existing and unrelated:** `tests/__init__.py` had never been tracked in git, so
`tests/unit/test_mask_all_instances.py` could not import `tests.models` and **collection aborted
entirely** at `d0daed7`. Earlier "352 passed" runs relied on an untracked local file. The empty
`tests/__init__.py` is now committed; collection goes from 412+error to 439.

### 1. EuroSAT — DONE, shipped, closes mandatory requirement #1
- `configs/models.yaml` key `eurosat_classifier`; `registry.py` import + `ADAPTER_CLASSES` +
  `MODEL_METADATA`; adapter `backend/app/ml/adapters/eurosat.py`.
- Live round-trip verified: returns `Industrial` at 94.7% on `airport_airplanes__P0173_0003.png`,
  probabilities sum to 1.0, unloads clean. (That tile is 0.5 m aerial and the model is a 10 m
  Sentinel model, so the label is out-of-domain — the answer text states the GSD, which is the point.)
- Tests: `tests/models/test_eurosat_adapter.py`, plus coverage in `tests/unit/test_trained_adapters.py`.
- Docs: `docs/models/eurosat.md`.
- **Not routed**, deliberately: scene-level output satisfies neither the mask nor the box contract.

### 2. Flood — DONE as a refusal, per the decision in §2 above
- `backend/app/ml/adapters/flood_segmenter.py` + config + registry entries.
- `predict()` returns `status="NOT_CONFIGURED"`, `confidence=None`, `masks=[]`, and carries every
  measured number in `metadata`. The refusal is **unconditional** — it does not validate input or load
  weights first, because the blocker is the missing normalisation, not the caller's input. `load_model()`
  still works (verified: epoch 9, `strict=True`, forward `(1,16,64,64) → (1,2,64,64)`) for whoever
  recovers the preprocessing.
- `validate_inputs()` rejects 3-channel RGB naming the full 16-band order.
- Tests: `tests/unit/test_flood_segmenter.py` (16 tests, pass with checkpoints absent).
- Docs: `docs/models/flood.md`.
- Corrected in `flood_unet.py`: its docstring had claimed the reconstruction was "checked numerically
  against the delivered per-scene metrics". **It was not and cannot be** — that claim is now replaced
  with an explicit statement of the opposite.

### 3. Burn scars — document-only, decided with the user
`terratorch` was **not** installed (it would risk downgrading torch 2.14 under the eight working
adapters). Checkpoint staged, fully documented in `docs/models/burnscars.md`, **not registered**, no
adapter. Unchanged from the analysis above.

### 4. Record and tidy — DONE
- `qna.md` **Q-041** (the delivery) and **Q-042** (corrections + four further findings).
- `docs/models/{eurosat,flood,burnscars}.md` written; `CHECKPOINT_INVENTORY.md` rows + storage totals.
- `docs/notes/transformers5-custom-modeling-traps.md` + `locate_anything_qwen2_transformers5.diff` —
  see §5 below.
- `project/memory.md` §0 rewritten to current state; `split-ushnik-ayushman.md` updated (req #1 closed,
  flood/burn-scar items added against Ayushman).
- `project/handoff/request-to-ayushman-2026-09-20.md` — ready to send.
- `git add -f docs/models/burnscars/train_val_split_seed42.pt` (3 KB, `*.pt` is gitignored but it is the
  split reproducibility artefact).
- The 22 MB of burn-scar failure panels were **kept**. `docs/models/changeformer/` is already 7.2 MB of
  committed evidence PNGs, and these are the primary record of the per-scene failures.

### 5. Disk — DONE, ~25 GB reclaimed
`df /home` avail 351 G → 375 G.
- ~18.3 GB of redundant archives in `~/Downloads/ayushman/`, every deletion gated on SHA-256
  comparison against the extracted copy in the repo, not on filename or size.
- 7.2 GB `checkpoints/locate_anything_3b` + 123 MB of archive-only extras, deleted with the user's
  approval. Dead since Q-023; zero references in `backend/`, `configs/`, `scripts/`, `tests/`,
  `training/`.
- **Before deleting it, one thing was rescued.** That gitignored directory held the only copy of a local
  patch to `modeling_qwen2.py`, fixing two silent-failure bugs on transformers 5.x: non-persistent
  buffers computed in `__init__` come back as zeros/NaN under meta-device init (uniform attention,
  fluent output that ignores the image), and `rope_theta` moved into `config.rope_parameters` so the
  usual `getattr(config, "rope_theta", 10000.0)` silently applied 1e4 to a checkpoint trained at 1e6.
  Preserved as `docs/notes/locate_anything_qwen2_transformers5.diff` with the lesson written up in
  `docs/notes/transformers5-custom-modeling-traps.md`. Nothing in the repo currently reads `rope_theta`
  (grepped), so this is a trap list, not an open bug.
- `~/Downloads/ayushman/` now holds only `test-...zip` (12 MB), verified 100% redundant — all 12 files
  are byte-identical to repo copies, so it is safe to delete whenever.

---

## What remains — all of it waiting on someone else

1. **Ayushman: the flood preprocessing.** Five specific questions in
   `request-to-ayushman-2026-09-20.md`; the training script would answer all of them. Until then the
   model stays `NOT_CONFIGURED`. This is the only thing standing between us and a working flood
   capability.
2. **Ayushman: confirm which burn-scar metric file is the 0.40 run.** Q-042 §3 makes the case that
   `final_test_metrics.json` is a mislabelled argmax run (its ROC-AUC is byte-identical to the 0.40
   file's, and ROC-AUC is threshold-independent), so quote the 0.40 file — but he should confirm.
3. **Ayushman: was burn-scar training-from-scratch deliberate?** If a pretrained-backbone run is
   possible it would be both a stronger result and genuine foundation-model adaptation evidence.
4. **Team decision: burn scars beyond documentation.** Separate venv to verify, vendor the
   architecture, or leave it. Needs his version list first.
5. **Frontend: the "Flood extent" suggestion chip** (`QueryBar.tsx:18`) still routes nowhere. Either
   point it at the refusal or remove it. Sandipan owns that file.
6. **Not done, deliberately:** nothing was pushed. Commits are local on `prototype`.
