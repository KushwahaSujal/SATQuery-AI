# Request to Ayushman — 2026-09-20

Two of the three models you delivered today are integrated or integrable. Two need something from
you before they can ship. This is written to be sent as-is.

Context for whoever forwards this: the measured basis for every claim below is `project/qna.md`
Q-041 and `project/handoff/ayushman-delivery-2026-09-20.md`.

---

## First — the EuroSAT model is excellent and it closes a mandatory requirement

Land-cover classifier, EfficientNet-B0, 98.32% accuracy over 4050 held-out samples. It is wired in.

It also does something none of our other models did: it gives us a **measured remote-sensing
adaptation score on a held-out split**, which is mandatory requirement #1 and had been open against
BigEarthNet since 2026-09-14. This closes it.

Two things you did that made it immediately usable, and that I want to ask you to keep doing:

1. You shipped the **per-sample predictions** (`y_true.npy`, `y_pred.npy`, `y_prob.npy`). That let us
   recompute your accuracy and balanced accuracy independently — they matched to 10 decimal places,
   the probability rows sum to 1, and `argmax(y_prob) == y_pred` on all 4050 rows. That is the
   difference between a number we can defend and a number we have to trust.
2. You shipped `inference_config.json` with the exact image size and normalisation constants, so the
   serving preprocessing could be made to match training exactly.

---

## 1. Flood model — BLOCKED, and it is a small fix

**What works:** the checkpoint is real. We reconstructed the architecture from the 118 state_dict
entries and it loads with `strict=True` — encoder 16/32/64/128, bottleneck 256, transposed-conv
decoder, `output_layer` 1x1 to 2 classes, the 18 `DoubleConv` 3x3 convolutions bias-free and the
four transposed convs plus `output_layer` with bias. Both checkpoint hashes match your
`SHA256SUMS.json`.

**What blocks it:** the delivery documents the 16-channel order but **never states the training-time
normalisation**, and it is not in `training_config.json`, `model_metadata.json`, or the `config` dict
embedded in `best.pt`. On a BatchNorm network a wrong input scale does not raise an error — it just
predicts badly and silently.

We tried to recover it. 17 preprocessing/threshold combinations, scored on the **official**
Sen1Floods11 splits (89 validation, 90 test scenes — all four modalities present and verified).
Candidates were selected on validation and scored once on test, so these are not test-tuned numbers.

| scheme | test global IoU | per-scene IoU | precision | recall |
|---|---|---|---|---|
| raw values, no normalisation | 0.5403 | 0.3557 | 0.5695 | 0.9133 |
| per-scene min-max | 0.4528 | 0.3327 | 0.9742 | 0.4583 |
| S2 / 10000 | 0.3043 | 0.1228 | 0.4279 | 0.5130 |
| best on validation: S1 clip [-30,0]→[0,1], S2/10000, **DEM zeroed** | **0.7034** | 0.3923 | 0.9408 | 0.7359 |
| **your report (67 scenes)** | **0.6292** | 0.4075 | 0.7873 | 0.7580 |

Nothing reproduced your 0.6292. Note the last row of the sweep scores *higher* than your report —
that is not good news, and here is why we are not claiming it:

- It only wins with the **DEM channel replaced by zeros**. A model genuinely trained on DEM would not
  prefer having it removed, so whatever we are doing to DEM is wrong.
- Under every scheme we tried, **argmax and threshold 0.30 land in the same place** (0.5403 vs 0.5402
  for raw). Your report shows a real difference between them (0.6292 → 0.6211, precision 0.787 →
  0.722, recall 0.758 → 0.816). Different threshold behaviour means the probability calibration
  differs, so **your 0.30 threshold does not transfer to our inference path.**
- A better number obtained under a configuration you did not use is a different experiment, not a
  better result.

Right now the model is registered but returns `NOT_CONFIGURED` and refuses to report flood extent.
It stays that way until this is resolved.

### What we need — five things, all small

1. **The per-channel normalisation.** Exact means and standard deviations in the model's channel
   order, or whatever transform you actually applied. If you normalised per scene rather than with
   dataset constants, say that instead.
2. **S1 handling specifically.** The GeoTIFFs are gamma0 in dB (we measure roughly -38 to -0.3). Did
   you clip (to what range?), rescale, convert out of dB to linear power, or feed the dB values
   straight in?
3. **S2 handling.** Files are int16 DN (we measure 10 to ~5400 on the scene we checked). Divided by
   10000 to reflectance? By something else? Clipped?
4. **DEM handling.** This is the one we are most confident we have wrong. Metres as stored? Scaled?
   Per-scene centred? How did you treat DEM nodata?
5. **The label mapping.** `LabelHand` is -1 / 0 / 1 on disk, but your metadata says
   `ignore_index: 255`. Where did -1 become 255, and was that done before or after the loss?

**Best possible answer: just send `train_flood.py` and the Dataset class.** That settles all five at
once and is less work for you than writing them out.

### Also worth sending if it is cheap

6. **`test_multimodal_eligible_scenes.csv`** (and the train/validation ones). You report **67** test
   scenes; the official Sen1Floods11 test split is **90**, and all 90 are complete on our disk. We
   could not work out which 23 you excluded or why — we tried filtering on label nodata (16 scenes
   remain), scenes with any flood ground truth (83), and scenes with no all-zero S2 pixels (86), and
   none gave 67. Without that manifest we cannot compare against your number on the same data, only
   on a different set.

### One methodological note

Your global flood IoU is 0.629 but your **per-scene mean is 0.407** (and validation records 0.4358).
That gap means the pooled number is dominated by a few large-flood scenes. Both are legitimate, but
they answer different questions, so please always report which one a figure is — pooled or per-scene.
We will quote both.

---

## 2. Burn-scar model — two things to fix in the evidence, one decision pending

The checkpoint is genuine and internally consistent with your `model_config.yaml`: PL 2.6.6,
`terratorch.tasks.SemanticSegmentationTask`, `EncoderDecoderFactory`, `prithvi_eo_v2_300` (ViT-L, 24
blocks, width 1024, Conv3d patch embed, `pos_embed` 197 → 224x224), the three necks, `UNetDecoder`
512/256/128/64, 355 tensors, ~324.4M params. The hash matches your manifest.

We have **not** run it. It needs `terratorch`, `lightning` and `einops`, none of which are installed,
and this environment is on `torch 2.14.0+cu130` — terratorch pins tightly enough that installing it
risks downgrading torch and torchvision underneath the eight adapters that currently work. That is a
decision for the team, not something to do quietly. (`timm` 1.0.29 and
`segmentation_models_pytorch` 0.5.0 are already present, and smp's `UnetDecoder` produces exactly
your decoder's parameter names, so the gap is smaller than it looks.)

**Question for you:** what exact `terratorch`, `lightning` and `torch` versions did you train with?
`pip freeze` from that environment would let us decide between a separate venv and vendoring the
architecture. Your README says Python 3.12; we are on 3.11.

### Two things that need correcting before any burn-scar number goes in the paper or the deck

**(a) Two of your metric files disagree for the same claimed test set.** Both say 264 scenes and
68,627,952 valid pixels:

| file | precision | recall | F1 | confusion matrix |
|---|---|---|---|---|
| `final_test_metrics.json` | 0.8246 | 0.7601 | 0.7910 | `[[61248239, 1027123], [1524085, 4828505]]` |
| `final_test_metrics_threshold_040.json` | 0.7857 | 0.8000 | 0.7928 | `[[60889458, 1385904], [1270670, 5081920]]` |

Our guess is that the first is an argmax (0.5) run that got labelled as the 0.40 run, not that
anything was fabricated — but we can only quote one. **Which is the threshold-0.40 result?** Please
confirm and re-issue the file, since your `model_manifest.json` embeds the second set.

**(b) The model was trained from scratch, so it is not foundation-model adaptation.**
`backbone_pretrained: false` and `freeze_backbone: false` — a Prithvi-EO-2.0 300M ViT-L trained from
scratch on 432 scenes. That is a legitimate segmentation result (IoU 0.6567, ROC-AUC 0.9775) and an
illegitimate transfer-learning claim, and the pretrained geospatial backbone is the entire reason
anyone uses Prithvi. This is the first thing a reviewer will go for.

So: **was training from scratch deliberate?** If you have the pretrained-backbone run, or can do it,
the fine-tuned version is a much stronger result *and* would genuinely evidence foundation-model
adaptation. If from-scratch was deliberate, tell us why and we will document the reasoning — but we
will not describe it as adaptation either way.

**(c) A per-scene failure mode your pooled IoU hides.** From your full
`per_scene_metrics_threshold_040.csv`: **10 of the 264 test scenes sit at burn IoU exactly 0.0**. Six
of them — 193, 198, 203, 223, 224, 234 — predict **literally zero burn pixels** on scenes that are
1.438%-5.194% burned. The other four (211, 236, 260, 261) predict only false positives. Credit for
shipping the failure analysis; most people would not have. **Any idea what those ten have in common?**
If it is a band-scaling or nodata issue it may be cheap to fix, and it would move the per-scene numbers
a lot — your mean per-scene burn IoU is 0.5634 against a pooled 0.6567.

Two smaller notes on that evidence: `failure_analysis/failure_panel_index.csv` has broken pixel
columns (scene 248 reports `valid_pixels = 2`) and disagrees with `lowest_recall_summary.csv`, so we
are taking all per-scene numbers from `per_scene_metrics_threshold_040.csv`. And please don't quote
`val/mIoU` 0.8308 as the model's accuracy anywhere — it is the 2-class mean dominated by "Not burned";
the burn-scar IoU is 0.7128 on internal validation and 0.6567 on test.

---

## 3. Two small process requests

1. **Please don't ship nested archives.** `eurosat_efficientnet_b0.zip` was inside
   `drive-download-...003.zip`, so unpacking the obvious top-level archives misses an entire model.
   We nearly lost the one that closes a mandatory requirement. Also, ~10 GB of what you sent was
   exact duplicates (two copies each of the 3.6 GB checkpoint, the 6.2 GB LocateAnything archive, and
   the ChangeFormer package).
2. **Keep shipping what you shipped with EuroSAT.** A `SHA256SUMS.json`, an `inference_config.json`
   with the real preprocessing, and the raw per-sample predictions. Do that for the flood model and
   it would already be serving. The ChangeFormer and LocateAnything packages were re-deliveries of
   things already in the repo, which is harmless but cost ~13 GB of transfer.

---

## Summary

| Model | State | Needs |
|---|---|---|
| EuroSAT land cover | **integrated**, closes mandatory req #1 | nothing |
| Flood segmentation | loads, refuses to serve | items 1-5 above (or `train_flood.py`) |
| Burn scars | not runnable here | version list; metric-file fix; the from-scratch decision |
