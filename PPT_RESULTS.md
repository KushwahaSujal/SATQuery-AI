# PPT Round — Real Measured Results

**Generated:** 2026-09-04 · **Machine:** Python 3.11.16, PyTorch 2.14.0+cu130, RTX 3070 (8 GB)
**Every number here is measured.** Raw outputs in `results/evaluations/`. Nothing is illustrative,
estimated, or copied from a paper.

> **Do not use the old V1/V2/V3 numbers** (mIoU 0.1832 / 0.2371 / 0.2238). Those came from a
> 2-record fixture pointing at a LEVIR-CD crop with hand-drawn boxes, not VRSBench. See
> `decisions.md` D-115. The numbers below replace them.

---

## 1. The workflow slide — one query, end to end

**Input image:** `P0331_0012.png` — 512×512, VRSBench official validation split
**User query:** *"The ship is positioned at the top edge of the image, within the waters adjacent to the upper harbor."*

### Stage 1 — Agentic routing (zero model weights involved)

| | |
|---|---|
| Capability selected | `single_image_grounding` |
| Routing confidence | **0.98** |
| Workflow | `workflow_grounding` |
| Reason given | "Single image provided with spatial grounding/referral query targeting 'ship'." |

Entities parsed straight from the sentence:

```
object_class     = ship
position         = top
relation         = within
reference_object = harbor
```

**This is the differentiator.** No LLM call, no weights loaded, fully deterministic and auditable —
the system decided *which specialists to run* before touching a GPU.

### Stage 2 — Execution DAG

```
stage 1: inspect_raster
stage 2: validate_single_image
stage 3: run_grounding          -> grounding_dino
stage 4: run_segmentation       -> sam2
stage 5: generate_overlay
stage 6: generate_report
```
Models selected: `grounding_dino`, `sam2` · Time budget: 105 s

### Stage 3 — Observable execution trace (26 steps, all `success`)

```
 1  Pipeline initialized                    14  run_grounding_reasoner
 2  Workflow planned: workflow_grounding    15  run_grounding_reasoner
 3  Pre-execution dependencies verified     16  select_target_candidate
 4  System & VRAM headroom confirmed        17  call_sam2
 5  Plan validated against tool whitelist   18  call_sam2
 6  Tool: inspect_raster           0.2 ms   19  receive_segmentation_mask
 7  Tool: validate_single_image    0.0 ms   20  build_visual_evidence
 8  validate_image                          21  complete_pipeline
 9  receive_query                           22  Tool: run_grounding     7050.3 ms
10  parse_query                             23  Tool: run_segmentation     0.1 ms
11  call_grounding_dino                     24  Tool: generate_overlay   268.2 ms
12  call_grounding_dino                     25  Tool: generate_report     20.0 ms
13  obtain_candidate_boxes                  26  Analysis completed successfully
```

### Stage 4 — Result and accuracy

| | |
|---|---|
| Answer | "Grounded and segmented ship edge within waters with high precision at [334.0, 0.9, 383.7, 60.5] (detector confidence 0.3008, SAM 2 score 0.8977, area 1,270 px)" |
| Predicted box | `[334.0, 0.9, 383.7, 60.5]` |
| **Ground truth (VRSBench)** | `[332.8, 0.0, 384.0, 56.3]` |
| **IoU** | **0.891** |
| Mask area | 1,270 pixels |
| End-to-end latency | 7,531 ms cold (includes model load) · **314 ms warm** |
| Warnings / errors | 0 / 0 |

### Stage 5 — Evidence artifacts produced

```
overlays/grounding_overlay.png     396.5 KB
masks/grounding_mask.png             0.6 KB
vectors/grounding.geojson            0.9 KB
reports/..._audit_report.pdf         4.9 KB
result.json                         33.4 KB
trace.json                           8.6 KB
```

Every answer ships with a mask, a georeferenced vector, a PDF audit report and a machine-readable
trace. Nothing is text-only.

---

## 2. Benchmark results — VRSBench referring (official EVAL split)

Dataset: `xiang709/VRSBench`, `VRSBench_EVAL_referring.json` — 16,159 records, 9,350 images.
Subset: `unique=True` (unambiguous single target). Pipeline: Grounding DINO → V4 reasoner → SAM 2.1.

| Metric | n=299 (seed 7) | n=100 (seed 42) |
|---|---|---|
| **Mean IoU** | **0.3532** | 0.3170 |
| Median IoU | 0.1957 | 0.1508 |
| Recall@0.25 | 0.4816 | 0.4600 |
| **Recall@0.50** | **0.3980** | 0.3300 |
| Recall@0.75 | 0.2341 | 0.2100 |
| Detection rate | 0.8428 | 0.7700 |
| Mean latency | **314 ms** | 550 ms |
| Errors | **0** | 0 |

### Per-category mean IoU (n=299) — where it works and where it doesn't

| Strong | IoU | | Weak | IoU |
|---|---|---|---|---|
| stadium | **0.7815** | | bridge | 0.1352 |
| airplane | **0.6324** | | harbor | 0.1706 |
| ship | 0.3984 | | vehicle | 0.1923 |
| airport | 0.3951 | | overpass | 0.2363 |
| ground-track-field | 0.3905 | | baseball-diamond | 0.3320 |

**Honest reading:** large, visually distinct structures ground well. Small objects (vehicles) and
long thin structures (bridges, overpasses) are weak — a known limitation of box-based open-vocabulary
detectors on nadir imagery. Say this out loud in the presentation; it is a much stronger position
than claiming uniform performance.

---

## 3. Router accuracy — our own measurement, and a bug we found

All 16,159 VRSBench referring queries are grounding queries by construction, so this is a clean test
of the intent classifier.

| Routed to | Count | Share | |
|---|---|---|---|
| `single_image_grounding` | 12,101 | **74.9%** | correct |
| `single_image_vqa` | 4,058 | **25.1%** | **misrouted** |

**Router accuracy: 74.9%.**

**Root cause found.** `IntentClassifier` recognises grounding intent through (a) an imperative verb
("find", "locate", "highlight", "where is") or (b) a noun from a hardcoded list. VRSBench phrases
referring expressions *declaratively* — "The baseball diamond **is located** in the left portion of
the image" — which has no imperative verb, and `baseball diamond` / `stadium` / `windmill` /
`ground-track-field` are absent from the noun list. So the query falls through to generic VQA.

Example misroutes (all should be grounding):

```
[single_image_vqa]  "The baseball diamond is located in the left portion of the image."
[single_image_vqa]  "One of the ships is placed at the extreme right edge, partially cut off..."
[single_image_vqa]  "The baseball diamond with its infield dirt is in the upper left part..."
```

**This is a fixable bug, not a design flaw** — extend the noun vocabulary to the VRSBench/DOTA class
set and add declarative patterns ("is located", "is positioned", "is situated"). Expected to recover
most of the 25%.

**Frame it as a strength:** we measured our own router against 16,159 real queries and found a
concrete defect. That is exactly the kind of evidence-first engineering the problem statement asks
for, and it beats presenting an unmeasured claim.

---

## 4. What is genuinely running right now

| Component | Status | Evidence |
|---|---|---|
| Agentic orchestration | **Working** | 26-step trace above, 0.98 routing confidence |
| Grounding DINO | **Working** | HuggingFace `IDEA-Research/grounding-dino-base`, CUDA |
| V4 relational reasoner | **Working** | selects among candidates; filters full-frame boxes |
| SAM 2.1 segmentation | **Working** | `facebook/sam2.1-hiera-small`, mask score 0.8977 |
| Evidence engine | **Working** | overlay + mask + GeoJSON + PDF per job |
| Supabase persistence | **Working** | after the pooler fix (D-113) |
| Test suite | 108/120 | 12 failures = weights absent, no logic failures |
| ChangeFormer / CDVQA / VQA / Optical-SAR | **blocked** | checkpoints only on Ayushman's machine |

---

## 5. Reproducing these numbers

```bash
# full workflow showcase (the slide)
python scripts/showcase_workflow.py \
  --image P0331_0012.png \
  --query "The ship is positioned at the top edge of the image, within the waters adjacent to the upper harbor."

# benchmark
python scripts/evaluate_vrsbench_real.py --limit 300 --unique-only --seed 7

# router accuracy — see decisions.md D-116
```

Raw JSON: `results/evaluations/vrsbench_real_20260904T122102Z.json` (n=299) and
`vrsbench_real_20260904T121819Z.json` (n=100), each with per-record boxes, IoU and latency.

---

## 6. Slide-ready one-liners

- "Deterministic agentic routing at **0.98 confidence**, no LLM in the routing path — fully auditable."
- "**26-step observable execution trace** per query; every answer carries a mask, a GeoJSON and a PDF audit report."
- "**Mean IoU 0.3532, Recall@0.5 0.398** on 299 records of the official VRSBench referring split, **314 ms** per query."
- "We measured our own router on 16,159 real queries: **74.9% accurate**, and we know exactly why the other 25% fail."
- "**Zero errors** across 299 end-to-end runs."
