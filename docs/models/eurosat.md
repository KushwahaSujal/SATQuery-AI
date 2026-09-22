# EuroSAT scene classification — the remote-sensing adaptation evidence

`eurosat_classifier` is an EfficientNet-B0 trained on EuroSAT RGB, 10 classes, delivered
2026-09-20 (project/qna.md Q-041). It is **registered and callable, and deliberately not routed**
from the grounding pipeline: that pipeline's response contract is a mask or a box, and a
scene-level classifier produces neither. Same reasoning as the crater detector (Q-028t) and land
cover (Q-037). **This model closes mandatory requirement #1** — see the section below.

All numbers below are copied from the delivered evaluation artefacts under `docs/models/eurosat/`
and from project/qna.md Q-041 §4, with Q-042 §7 and Q-043 §2 refining the `y_prob` claim. Nothing here is estimated. Anything unmeasured says `NOT MEASURED`.

| Registry key | Checkpoint | Architecture | Routed? | QNA |
|---|---|---|---|---|
| `eurosat_classifier` | `checkpoints/eurosat_efficientnet_b0/best_model.pt` | torchvision EfficientNet-B0, 10 classes | no | Q-041 §2, §4 |

Adapter: `backend/app/ml/adapters/eurosat.py` (`EuroSatLandCoverAdapter`).
Config: `configs/models.yaml`, key `eurosat_classifier`.

## Provenance and integrity

| | |
|---|---|
| Checkpoint | `checkpoints/eurosat_efficientnet_b0/best_model.pt` |
| Size | 47 MB — 48,724,792 bytes exactly |
| sha256 | `dbbfa69d48baa47ee813ae0465ce46e72c412159a5564e8e26d6d5044f012347` |
| Manifest | **none was supplied with the delivery.** This hash was computed here, not matched |
| Delivered evidence | `docs/models/eurosat/` — README, `inference_config.json`, metrics, 4 figures, per-sample predictions |
| Report generated | 2026-09-20T17:26:59 (delivery README) |

The other three checkpoints in the same delivery did ship manifests and all matched (Q-041 §1).
EuroSAT's did not, so the hash above establishes *what we have*, not *that we have what was
measured*. Treat it as a fixpoint for future comparison rather than as verification of the sender.

## Architecture

`torchvision.models.efficientnet_b0`, with `classifier[1]` replaced by `Linear(1280, 10)`. The
adapter loads `ckpt["model_state_dict"]` with **`strict=True`**, so a single wrong tensor name or
width fails loudly instead of serving wrong labels.

Read off the checkpoint itself (not from the README):

| | |
|---|---|
| `model_state_dict` entries | 360 |
| head | `classifier.1.weight` (10, 1280), `classifier.1.bias` (10,) |
| `epoch` | 9 |
| `best_val_accuracy` | 0.9891358024691358 |
| `image_size` | 224 |
| `class_names` | the 10 below, in this order |

Class names, training image size, epoch and best validation accuracy are read *from the checkpoint*
by the adapter, not hard-coded, and the load refuses if the head's output width disagrees with
`len(class_names)` — that mismatch would silently mislabel every prediction (Q-041 §2).

## Classes — checkpoint index order

| idx | class |
|---|---|
| 0 | `AnnualCrop` |
| 1 | `Forest` |
| 2 | `HerbaceousVegetation` |
| 3 | `Highway` |
| 4 | `Industrial` |
| 5 | `Pasture` |
| 6 | `PermanentCrop` |
| 7 | `Residential` |
| 8 | `River` |
| 9 | `SeaLake` |

## Preprocessing — from the delivery, not invented

From `docs/models/eurosat/inference_config.json`:

| step | value |
|---|---|
| resize | 224 x 224, bilinear |
| normalise mean | `[0.485, 0.456, 0.406]` |
| normalise std | `[0.229, 0.224, 0.225]` |
| input | 3-channel RGB |

These are the ImageNet constants, which is what an ImageNet-initialised EfficientNet-B0 expects.
Unlike the flood model in `docs/models/flood.md`, the preprocessing here **was** documented by the
sender, which is the single reason this model serves and that one does not.

### What the adapter refuses, and why it matters for a demo

`backend/app/ml/adapters/eurosat.py` rejects input rather than coercing it (commit `53c93a7`,
project/qna.md Q-043 §3). This is the most demo-relevant property of the adapter, because the obvious
thing to feed a 10 m Sentinel-2 model is 16-bit reflectance — and that used to fail silently:

| input | before `53c93a7` | now |
|---|---|---|
| 16-bit / reflectance (e.g. S2 L1C 0-10000) | clipped to 255 -> a **white tile**, answered `SeaLake` @ 0.9930 | `InvalidInputError` telling the caller to scale its own pixels |
| array containing NaN or inf | NaN cast to 0 -> a **black tile**, answered `SeaLake` @ 0.9906 | `InvalidInputError` |
| negative values | clipped to 0 | `InvalidInputError` |
| empty array | bare `ValueError` from numpy | `InvalidInputError` |
| float in [0, 1] | scaled by 255 | unchanged — still accepted |
| `top_k` = 0, -3, 2.9, `"x"`, `True` | positional path skipped validation; `-3` returned **seven** classes and `"x"` escaped as an HTTP 500 | `InvalidInputError` on every path |

A confident label on a blank tile is worse than an error, which is why these are refusals rather than
best-effort conversions. Accepted input is 8-bit RGB, or floats in [0, 1].

## Measured metrics — 4050 held-out test samples

From `docs/models/eurosat/evaluation/evaluation_metrics.json`:

| Metric | Value |
|---|---|
| test samples | 4050 |
| accuracy | 0.9832098765432099 |
| balanced accuracy | 0.9824222222222222 |
| ROC-AUC OvR, macro | 0.9995958032249936 |
| ROC-AUC OvR, weighted | 0.9996152613308699 |
| PR-AUC, macro | 0.9967362499341972 |
| PR-AUC, weighted | 0.9968799110618954 |

Per class, from `docs/models/eurosat/evaluation/classification_report.csv` (rounded to 6 dp here;
that file carries full precision):

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| `AnnualCrop` | 0.969027 | 0.973333 | 0.971175 | 450 |
| `Forest` | 0.997768 | 0.993333 | 0.995546 | 450 |
| `HerbaceousVegetation` | 0.958425 | 0.973333 | 0.965821 | 450 |
| `Highway` | 0.989390 | 0.994667 | 0.992021 | 375 |
| `Industrial` | 0.986772 | 0.994667 | 0.990704 | 375 |
| `Pasture` | 0.966102 | 0.950000 | 0.957983 | 300 |
| `PermanentCrop` | 0.970509 | 0.965333 | 0.967914 | 375 |
| `Residential` | 0.997748 | 0.984444 | 0.991051 | 450 |
| `River` | 0.992042 | 0.997333 | 0.994681 | 375 |
| `SeaLake` | 1.000000 | 0.997778 | 0.998888 | 450 |
| macro avg | 0.982778 | 0.982422 | 0.982578 | 4050 |
| weighted avg | 0.983255 | 0.983210 | 0.983212 | 4050 |

Weakest classes: `Pasture` (recall 0.950) and `HerbaceousVegetation` (precision 0.958) —
both vegetation classes that EuroSAT's own class definitions overlap on. `SeaLake` is the only
class with perfect precision. Support is unbalanced (300 for `Pasture` against 450 for five
classes), which is why balanced accuracy is quoted alongside accuracy.

Figures for the same run: `docs/models/eurosat/evaluation/figures/` — confusion matrix, ROC
curves, precision-recall curves, calibration curve.

## This closes mandatory requirement #1

`project/memory.md` §0 listed **"RS adaptation evidence (BigEarthNet) — mandatory req #1"** as
open. EuroSAT closes it: a remote-sensing-specific classifier with a measured score on a held-out
split, 0.9832 accuracy over 4050 samples. It closes it more cleanly than BigEarthNet would have,
because BigEarthNet is multi-label with no single headline accuracy on a split we hold.

## Verification — what was actually checked here

Independently recomputed from the delivered per-sample predictions
(`docs/models/eurosat/evaluation/predictions/y_true.npy`, `y_pred.npy`, `y_prob.npy`; 4050 rows):

| Check | Result |
|---|---|
| accuracy | 0.9832098765432099 — matches the delivered value to 16 dp |
| balanced accuracy | 0.9824222222222222 — matches to 16 dp |
| `y_prob` rows sum to 1 | to within 2.2e-07 (max deviation 2.1043325660e-07). The file is stored **float64**, carrying values that are exactly float32-representable — so they were computed in float32, but nothing is widened on read |
| `argmax(y_prob) == y_pred` | true for all 4050 rows |
| support per class | 450, 450, 450, 375, 375, 300, 375, 450, 375, 450 — matches the report |
| `strict=True` load | passes into `efficientnet_b0` with `Linear(1280, 10)`; forward gives `(1, 10)` |

So the report is internally consistent and was not written by hand. Q-041 §4 records the same two
recomputations to 10 dp; the full-precision agreement above is the stronger form of that check.

## The limit — recomputation, not re-measurement

**The EuroSAT imagery is not in this repository.** `datasets/raw/` contains no `eurosat`. Every
number above is therefore either copied from the delivered report or recomputed **from the
delivered predictions** — it is **not** a re-measurement from pixels through our own code path.
If the delivered `y_pred.npy` were produced by a different checkpoint than the one on disk, nothing
above would catch it. The `strict=True` load plus the matching hash are the only ties between the
predictions and the weights we hold.

## Scene-level only, and why it is not routed

One label per tile, no localisation. `run_grounding_pipeline` returns a `segmentation_mask` or a
box, and every consumer treats the mask as binary foreground
(`backend/app/evidence/fusion.py::build_grounding_evidence`). A class index for the whole scene
cannot be expressed in that contract without inventing a localisation the model cannot do, so the
model is registered and callable but nothing auto-selects it. This is the same decision, for the
same reason, as land cover and the two ISPRS models in `docs/models/trained_segmenters.md`.

## Resolution — 10 m/px, and what that means

EuroSAT tiles are Sentinel-2 at **10 m/px**, 64 x 64 px, upsampled to 224 x 224 for the network.
`configs/models.yaml` records `trained_gsd_m: 10.0` so the answer text cannot claim 0.5 m.

**Accuracy on sub-metre aerial photography is `NOT MEASURED`.** A 224 px input derived from a
64 px Sentinel-2 tile and a 224 px crop of a 0.5 m aerial photo cover 640 m and 112 m of ground
respectively; nothing in Q-041 measures the second case. A caller with high-resolution imagery
should treat this model as untested.

## Head-to-head — none exists

**There is no head-to-head against the live pipeline.** There is nothing to compare against: the
Grounding DINO + V4 + SAM 2 path has no scene-classification capability, and `bigearthnet`
produces multi-label tags over a different taxonomy on 12-channel Sentinel-2, not a single label
over these 10 classes. The Q-025t/Q-026t-style comparisons that justified routing roads and
buildings were never run for this model and cannot be.

## Caveats recorded in the transcript

No manifest shipped with this checkpoint, so its hash is recorded rather than matched (Q-041 §1);
the EuroSAT imagery is absent from the repo, so the score is recomputed from delivered predictions
and **not** re-measured from pixels (Q-041 §4); the model is scene-level with no localisation and
is deliberately unrouted (Q-041 §3); the tiles are 10 m Sentinel-2 upsampled 3.5x, and behaviour on
sub-metre imagery is `NOT MEASURED`; the delivery arrived nested inside
`drive-download-20260920T125749Z-1-003.zip`, so extracting only top-level archives misses this
model entirely (Q-041 §1); and the validation accuracy in the checkpoint (0.9891358024691358) is
higher than the test accuracy, which is the expected direction but has not been re-measured here.
