# Pre-Demo Plan — what is left

Ordered by **what fails the evaluation first**, same principle as `phases.md`.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

**Baseline measured 2026-09-07**, not quoted from docs. Every number below was run on this machine.

---

## 0. Verified baseline

| Check | Result |
|---|---|
| Test suite | **132 passed, 0 failed, 0 xfail** in 56.3s | *(117 at plan time)*
| Backend boot | clean · device `cuda` · PostgreSQL connected · 14 tools registered |
| Frontend | `npm ci` + `tsc --noEmit` + `next build` all pass · 7 routes |
| Models reporting available | 9 / 9 (but see §1.4 — this check is a lie) |
| Capabilities agent-executable | **6 / 13** |
| MP4 end-to-end | HTTP 200, decodes correctly, **0 events found** |

### What is genuinely working

- Agent DAG branches: `single_image_vqa`, `single_image_caption`, `single_image_grounding`,
  `temporal_change_detection`, `temporal_change_vqa`, `optical_sar_analysis`
- Grounding DINO + SAM 2.1 on still imagery
- CDVQA — trained in-repo, **69.50% OA** on 2,000 SECOND-CDVQA test samples, artifacts on disk
- Visual grounding — **mIoU 0.3532, R@0.5 0.398** over 299 official VRSBench referring records
- PostgreSQL persistence, execution trace capture, artifact workspaces
- Video decode, task routing, and the `/api/video/*` endpoint surface

---

## 1. Blockers — these fail a mandatory requirement

### 1.1 `[ ]` Optical–SAR fusion is random weights · **mandatory req #5**
`checkpoints/optical_sar/satquery_fusion.pth` is an untrained `CrossAttentionFusionNet`.
Proven statistically: linear weights bounded to exactly ±1/√768, attention biases identically zero,
LayerNorm 1.0/0.0, zero optimizer state. `scripts/train_optical_sar_fusion.py` never existed.
Ayushman confirmed in writing: *"Straight answer: NO. It was NEVER trained."*

Currently emits noise dressed as land-cover predictions — which also violates the **zero fabrication**
non-functional requirement in `prd.md` §5.

Two options, his framing:
- **A · rule-based** — NDVI/NDWI from Sentinel-2 optical + calibrated VH/VV backscatter ratio from
  Sentinel-1 SAR to separate water / urban / bare soil / vegetation. Deterministic, defensible,
  no black-box weights. *Recommended.*
- **B · trainable** — linear probe on DOFA multimodal embeddings using BigEarthNet-MM or SEN1-2.

**Decision 2026-09-07: Option A.** Rule-based fusion is the chosen path.
Estimate: **1–2 days.**

### 1.2 `[ ]` Remote-sensing adaptation is unevidenced · **mandatory req #1**
The headline criterion. A generic VLM explicitly does *not* satisfy it.

- `general_rs_vlm` is stock `Salesforce/blip-vqa-base` — zero RS adaptation
- `bigearthnet` — the *prescribed* adaptation dataset — is registered in `ModelRegistry` but called
  by **no tool and no DAG branch** (D-106). Verified: `get_adapter("bigearthnet")` appears nowhere.
- `remoteclip` is likewise called by no tool

**The strongest honest answer we already own is CDVQA** — genuinely trained in this repo by
`training/vqa/train_cdvqa.py` on SECOND-CDVQA, a remote-sensing dataset, with reproducible
artifacts. That should become the headline adaptation story rather than an afterthought.

Minimum viable fix: wire BigEarthNet into a real capability + DAG branch so the prescribed dataset
is demonstrably used, and lead the narrative with CDVQA. Estimate: **1–2 days.**

### 1.3 `[ ]` ChangeFormer inference is broken · **mandatory req #4 (change map)**
Change *description* works via CDVQA; the spatial change **map** does not.

Measured today, 100 LEVIR-CD test pairs at 256px `[-1,1]`:

| | identical image T1==T2 | IoU | precision | recall |
|---|---|---|---|---|
| upstream `wgcban/ChangeFormer` | **0.00% changed** | 0.0737 | 0.4556 | 0.0808 |
| repo `network.py` | **61.65% changed** | 0.0530 | 0.0548 | 0.6097 |

Upstream loads the checkpoint `strict=True`, 373/373 tensors, 0 missing / 0 unexpected. The repo
reimplementation cannot distinguish an image from itself. Best upstream IoU is **0.1586 @ thr 0.05**
— still 4× below the checkpoint's self-reported 0.687.

So swapping the architecture is **necessary but not sufficient**. Open question for Ayushman: which
validation set produced 0.687? Estimate: vendor + rewire ≈ **half a day**; closing the remaining gap
is unbounded until he answers.

### 1.4 `[~]` `/api/health` reports models as ready that would crash on use
`is_available()` is a bare file-existence check, so `/api/models` shows all 9 green regardless of
whether the weights load. This is the exact false-positive `scripts/setup_checkpoints.py` was
flagged for.

**Design revised 2026-09-07 after reading the code.** The original plan here — "replace
`is_available()` with load-and-verify" — was wrong. Loading 1.5 GB BLIP plus 605 MB RemoteCLIP on
every health check is unacceptable, and it would change the contract in `ml/base.py` plus four
adapter overrides.

The slot for this already exists and is simply unwired:

- `ml/registry.py:152` defines `mark_verified()` — **called by nothing**
- `ml/registry.py:179` reads `_verified_models` into a `validation_status` field
- `schemas/models.py:29` documents `PENDING_VERIFICATION | VERIFIED | FAILED`

So every model reports `PENDING_VERIFICATION` forever. The fix is wiring, not redesign:

1. Leave `is_available()` alone — "the file is present" stays a cheap, honest answer to its own
   question
2. At startup, run the placeholder detection `scripts/verify_checkpoints.py` already implements
   (it only `torch.load`s files under 100 KB, so it is fast) and feed the result to `mark_verified()`
3. `validation_status` becomes meaningful, so `/api/models` can distinguish "file exists" from
   "genuine weights"

Files: `ml/registry.py`, one startup hook in `main.py`, plus tests. The five `is_available()`
implementations stay untouched — materially smaller blast radius than originally planned.

**Also:** delete `scripts/setup_checkpoints.py` — both teams agreed. Estimate: **half a day.**

**Status: blocked on the `rules.md` §6 quiz** (model-registry change).

---

## 2. Demo-critical — will be visible on stage

### 2.1 `[x]` MP4 pipeline finds nothing — **root-caused and fixed 2026-09-07**

Not a threshold problem. The trace said `Candidate detections found on 0 sampled frames`, so nothing
ever reached the flagger — its "did not satisfy persistence and event score thresholds" message was
misleading.

**Root cause:** `backend/app/workflows/video_analysis.py:141` read
`gd_res.metadata.get("boxes", [])`. The Grounding DINO adapter returns `GroundingResult` with
`boxes` as a **top-level field**; its `metadata` holds only `prompt`, `normalized_prompt`,
`box_threshold`, `text_threshold`, `image_dimensions`, `candidate_count`, `device`. So the read was
unconditionally `[]` for every frame, every prompt, every threshold. **The video pipeline had never
produced a single detection.**

Proven directly on `real_aerial_footage.mp4`: `result.boxes` = 2, 2, 1, 1 across four sampled
frames while `metadata["boxes"]` = 0, 0, 0, 0. Sweeping `box_threshold` down to 0.05 and trying five
prompt phrasings all returned 0 — consistent with a field bug, not a tuning one.

**Second bug, hidden behind the first:** with real boxes flowing, `backend/app/video/flagger.py:203`
crashed the workflow with `TypeError: expected string or buffer`. It wrapped
`create_change_overlay(...)` in `Image.fromarray()`, but that helper already returns a PIL Image —
every other call site uses it directly. That path had never executed.

**Result:** detections on 4/4 frames, SAM 2.1 now engages, flags produced with event scores.
Suite **120 passed, 1 xfailed** at the time.

Two fixes, one line each. Three further problems this uncovered are tracked below.

### 2.1a `[x]` Absent targets now report NOT_APPLICABLE — **FIXED 2026-09-07**

Grounding DINO is open-vocabulary: it ranks the best-matching region and has no "nothing here"
output, so it returned a confident flag for a car that was not in the footage.

**Two approaches were tried and measured to fail first:**
- **A · RemoteCLIP verification** — on a blank white image "a cat" scored 0.677; on a LEVIR-CD scene
  "a purple flying saucer" (0.430) outscored "buildings" (0.207). Reverted. (Adapter work kept — 2.1d.)
- **B · discriminative `reasoning_score`** — a real bug, fixed and kept, but for modifier-free queries
  the weights normalise to detector-only, so it made the gap *worse*: real 0.6802 -> 0.4972,
  nonsense 0.7445 -> 0.6134.

**What actually works: the photometric colour score already in the repo.** Detector confidence
cannot separate present from absent; pixel colour can. Measured over 32 frames of
`real_aerial_footage.mp4`:

| colour | in clip? | max colour score | max detector score |
|---|---|---|---|
| red | **yes** | **1.000** | 0.895 |
| white | **yes** | **0.969** | 0.916 |
| yellow | no | 0.230 | 0.827 |
| blue | no | 0.260 | 0.906 |
| green | no | 0.209 | 0.892 |

Detector score is useless (0.83-0.92 for all five). Colour score gives a **4x gap** with nothing in
between, so `min_colour_score = 0.45` sits in clear air.

**Implementation:** `color_score()` in `grounding_reasoner.py` already existed but was used only as a
0.15 *ranking* weight — which cannot reject, because ranking one candidate always yields that
candidate. It is now also a **gate**: when the query names a colour, a candidate whose pixels fail
the check is dropped. If every candidate is dropped, the run reports
`NOT_APPLICABLE: no <colour> <object> found in this footage`.

This is deterministic pixel statistics — mean RGB inside the box — not a black-box score. That
matters for defending it to a mentor.

**Also fixed so the result is visible:** `GET /api/video/{job_id}` rebuilt the response from the
database and overwrote the reason with "Retrieved 0 persisted event flags". The analysis result is
not persisted, only the flags — so the endpoint now re-derives the conclusion from the stored query
(the colour gate being deterministic makes that sound). And the UI showed a bare "No events
detected"; it now distinguishes **Not applicable** (amber) from **Detection failed** (red) from a
plain empty result, and prints the explanation.

### Verified in the browser via Playwright
| query | result |
|---|---|
| `spot a red car` | **1 event** — `0:15.4 — red car`, confidence 0.89 |
| `spot white cars` | **4 events** — 0:00.0 (0.92), 0:13.0 (0.85), 0:20.2 (0.54), 0:25.0 (0.91) |
| `spot a yellow car` | **0 events** — "**Not applicable** · no yellow car found in this footage. Candidate regions were detected but none are yellow." |

Suite **131 passed, 1 xfailed**. Covered by `test_absent_colour_reports_not_applicable` and
`test_present_colour_still_detected`.

### Scope limit — worth stating plainly
This rejects **wrong-colour** targets. It does **not** reject a wrong *object class*: asking for a
"purple flying saucer" still parses no colour our scorer knows and falls through
(`test_video_workflow_no_events_found` remains `xfail`). Class-level open-set rejection is unsolved
and A/B are measured dead ends for it. The colour gate covers the attribute case, which is the one
a judge is most likely to try.

### 2.1b `[x]` Per-frame failures are silently swallowed — **fixed 2026-09-07**
`video_analysis.py` caught every per-frame exception into a bare
`logger.warning(f"Grounding failed on frame {frame_idx}: {e}")` and continued, so the trace reported
`Candidate detections found on 0 sampled frames` and the result read `NO_RELEVANT_EVENTS_FOUND` —
**indistinguishable from the target genuinely being absent.**

Not hypothetical: running the suite while the dev server held 2.6 GB of a 7.65 GiB GPU produced CUDA
OOM on every frame and a clean-looking zero result. On a demo laptop with a busy GPU this fails
silently on stage. It is also how the field bug in 2.1 stayed invisible.

**Fix:** count per-frame failures instead of only logging them, and separate the two outcomes:
- some frames failed -> trace step marked `warning`, count and first failure shown, and the
  `NO_RELEVANT_EVENTS_FOUND` reason now appends `(N frame(s) also failed during detection.)`
- **every** frame failed and nothing was detected -> new `DETECTION_FAILED` reason and an `error`
  trace step, because we never actually looked and must not claim a negative we did not measure

`frame_errors` is declared beside `detections` rather than inside the grounding branch, so
non-grounding video tasks cannot `NameError` on it.

Covered by `test_video_workflow_reports_frame_failures_distinctly`, which monkeypatches the adapter
to raise `CUDA out of memory` and asserts the result is `DETECTION_FAILED`, not a clean negative.
Suite **121 passed, 1 xfailed** at the time.

### 2.1c `[x]` SAM 2.1 video propagation index error — **fixed 2026-09-07**
`SAM2VideoPredictor` indexes its frame directory **positionally** (0..N-1 over the sorted files),
but the workflow passed the original video frame number as `prompt_frame_idx`. With 6 sampled frames
and an anchor at frame 60 this raised `index 60 is out of bounds for dimension 0 with size 6`, was
caught, and fell back to per-image prediction.

The fallback was not empty, but close enough to be useless: **9 nonzero pixels out of 331,776**
(fraction 2.7e-05) on a box covering roughly 6% of the frame. Flags carried a bounding box and a
correct annotated overlay, but no usable segmentation.

**Fix:** build `pos_by_frame` / `frame_by_pos` maps from `sampled_frames`, pass the positional index
into `predict_video`, and map the positionally-keyed results back onto original frame numbers.

**Result: mask nonzero fraction 2.7e-05 -> 0.045** (4.5% of frame). Real segmentation.

Covered by `test_video_flag_mask_is_not_empty`. Note the first version of that test asserted
`frac > 0.0` and passed against the 9-pixel fallback — the threshold is now 0.001.
Suite **125 passed, 1 xfailed**.

---

## 3. Presentation — the seven asks

| # | Ask | State | Estimate |
|---|---|---|---|
| 1 | Frontend well designed | Builds and runs; Sandipan's `src/lib` restored. Needs a design pass, not a rebuild. D-111 says structural-only without frontend-owner agreement. | 2–3 days |
| 2 | MP4 pipeline works | §2.1 + §2.2 | 2–3 days |
| 3 | Prove orchestration is real | Trace is captured and persisted. Needs to be *shown*: per-step model, tool, duration, status, and the routing decision with its alternatives. Same artifact as #4. | 2 days |
| 4 | Audit report with useful detail | Trace data exists; the report generator is thin. Fold into #3 — an execution trace **is** the audit evidence. | shared with #3 |
| 5 | Responses user-friendly and detailed | Currently raw JSON. Needs a response composer that narrates what ran, what was found, and with what confidence. | 2 days |
| 6 | USP / 3D interactive | Nothing exists. Cheapest real option: terrain-relief or temporal change surface over an existing result. Only worth it once §1 and §2 produce real output to render. | 3–5 days |
| 7 | Security compliance | Not started. `.env` handling, CORS, upload validation and size limits, no secrets in logs, SQL injection surface. Mostly hardening, largely independent. | 1–2 days |

---

### 3a `[ ]` Header shows a false DEGRADED badge — **demo-critical, cheap**
Found 2026-09-07 running the app. `frontend/src/components/layout/AppHeader.tsx` reads three health
fields the backend does not return, so the first thing anyone sees is a red DEGRADED pill and a
fabricated model count, while the backend is genuinely healthy.

| Header reads | Backend returns | Result |
|---|---|---|
| `health.data.api === "online"` (L42) | `status: "ok"` — no `api` key | always `DEGRADED` |
| `health.data.models_ready` (L44) | `models_available` (a dict) | hardcoded fallback `5` |
| `health.data.models_total` (L45) | *(absent)* | hardcoded fallback `6` |

`models_ready` / `models_total` appear nowhere in the backend. CORS is correctly configured and the
call succeeds — this is purely a field-contract mismatch.

Fix either by aligning the frontend to the real payload, or by adding `api`, `models_ready` and
`models_total` to `/api/health`. The second keeps `D-111` (no frontend component rewrites without
the frontend owners) intact and is a few lines. **Recommend the backend side.** Estimate: **1 hour.**

---

## 3b. Prototype readiness — the two demo flows

Verified end-to-end against the running stack on 2026-09-07.

### `[x]` Two comparison images -> output — **works**
```
POST /api/upload   files=real_image_a.png, real_image_b.png
POST /api/analyze  {request_id, query, image_filenames:[a,b]}   ->  HTTP 200 in 6.8s
```
Routed through the **agent DAG** to `workflow_temporal_change_vqa`, executing 7 tools in order:
`inspect_raster -> validate_temporal_pair -> run_change_detection -> calculate_statistics ->
run_change_vqa -> generate_overlay -> generate_report`. Models used: `changeformer`, `cdvqa`.
Answer: *"10% to 20% change."* Artifacts on disk: 3 overlays, 5 masks, 1 vector, 1 report,
plus `trace.json` and `result.json`.

**Caveats:** the answer is terse (see §3 item 5 — response quality), and the change mask comes from
the broken ChangeFormer path (§1.3), so the map is unreliable even though the pipeline runs.

**Note the API contract:** `/api/analyze` requires `image_filenames`; omitting it returns 422. The
frontend must send it.

### `[~]` MP4 -> output — **runs, but segmentation is empty**
```
POST /api/video/analyze  file=real_aerial_footage.mp4, query="find all vehicles"  ->  HTTP 200 in 10.1s
```
Task `video_grounding`, 1 flag at 0.00-4.80s labelled `vehicles`, score 0.8038, models
`grounding_dino` + `sam2`. Both artifacts are served: annotated overlay (129,652 B, real image with
the box drawn) and mask (411 B).

**The mask is entirely zero** — `nonzero fraction 0.0` across 432x768. SAM 2.1 yields no usable
pixels, so a flag carries a bounding box and an overlay but no segmentation. Root cause is §2.1c:
video propagation errors on a frame-index mismatch, falls back to per-image prediction, and that
returns empty too. **Fixed — see §2.1c. Mask is now 4.5% of frame.**

**Reminder:** this path bypasses the agent DAG entirely (§2.2), so "is the orchestration real?"
currently has a different answer for video than for imagery.

---

## 3c. Dataset validation — do the outputs hold up on the real benchmarks?

Run 2026-09-07 on the datasets actually on disk.

### LEVIR-CD (bi-temporal change) — **output is WRONG**
`scripts/evaluate_changeformer_levircd.py --limit 100`, real LEVIR-CD test split through the
production adapter:

| metric | measured | checkpoint's own |
|---|---|---|
| IoU (aggregate) | **0.0376** | 0.6867 |
| IoU (mean/pair) | 0.0318 | — |
| F1 | 0.0725 | 0.8143 |
| precision / recall | 0.0431 / 0.2293 | 0.857 / 0.776 |

Delta **-0.6491**. The script's own verdict: *"the inference path is wrong."* The two-image flow
**runs** end-to-end and produces overlays, masks and a report, but the change map it draws is not
correct. This is §1.3, still quiz-gated.

### VRSBench (visual grounding) — **works, and there are two scripts**
There is no VRSBench *video* — the dataset is referring / VQA / captioning over still images
(16,159 referring records, 9,350 val images on disk).

**Trap:** `scripts/evaluate_grounding_vrsbench.py` reads `query` / `bbox` / `box` / `gt_box`, but
real VRSBench records use **`question`** and **`ground_truth`**. Pointed at the official file it
errors on every record — *"Grounding workflow requires a non-empty natural-language query"* — and
reports **mIoU 0.0000**. It only ever worked against the hand-written 2-record fixture in
`datasets/samples/vrsbench_sample_records.json`. This is the same field-name-mismatch class as
2.1 and Option B; it looks like a catastrophic result and is actually a schema bug.

**Use `scripts/evaluate_vrsbench_real.py`** — it reads the real schema. Re-run 2026-09-07:
**100 records, 0 errors, mIoU 0.2755, median 0.081, R@0.5 0.29, detection rate 0.86.**

The pipeline genuinely works on the official split. But note the headline number depends heavily on
the subset:

| run | n | subset | seed | mIoU | R@0.5 |
|---|---|---|---|---|---|
| 2026-09-04 | 299 | **unique-only** | 7 | 0.3532 | 0.398 |
| 2026-09-07 | 100 | **all** | 42 | 0.2755 | 0.290 |

`unique-only` keeps records whose target is unambiguous, so it is the easier subset. **Quoting
0.3532 without saying "unique-only subset" would not survive a careful judge.** State the subset
alongside the number everywhere it appears.

Full detail of the 299-record run (`results/evaluations/vrsbench_real_20260904T122102Z.json`):

| metric | value |
|---|---|
| mean IoU | 0.3532 |
| median IoU | 0.1957 |
| Recall@0.25 / @0.5 / @0.75 | 0.4816 / 0.3980 / 0.2341 |
| detection rate | 0.8428 |
| mean latency | 314 ms |

Per-category best-to-worst: airplane 0.632, ship 0.398, ground-track-field 0.391,
baseball-diamond 0.332, overpass 0.236, vehicle 0.192, bridge 0.135. Small objects are weakest —
worth knowing before a judge picks a query.

**Action:** either fix the field mapping in `evaluate_grounding_vrsbench.py` or delete it. Leaving
two grounding evaluators where the obvious one silently reports 0.0000 is a trap for whoever runs it
next. Estimate: **1 hour.**

---

### 2.1e `[ ]` Propagation covers only the anchor frame — **the temporal claim is not delivered**
Verified 2026-09-07 by instrumenting the flagger. On `real_aerial_footage.mp4`, 6 frames sampled,
6 detections reach the flagger, and **only 1 carries a mask**:

```
frame   0  mask=no   frac=0.0000  seg_score=0.0
frame  12  mask=no   frac=0.0000  seg_score=0.0
frame  24  mask=no   frac=0.0000  seg_score=0.0
frame  36  mask=no   frac=0.0000  seg_score=0.0
frame  48  mask=no   frac=0.0000  seg_score=0.0
frame  60  mask=YES  frac=0.0450  seg_score=0.88
```

SAM 2.1 logs `propagate in video: 1/1`. The anchor is chosen as the highest-confidence detection
(`detector*0.6 + reasoning*0.4`), which here is frame 60 — the **last** sampled frame — and
`propagate_in_video` runs forward from the prompt frame, so there is nothing after it to propagate
to.

The mask that does exist is excellent: 14,941 px, 100% inside the detection box, correct car
silhouette down to the wing mirror. But "SAM 2.1 video mask propagation" across the timeline is not
actually happening — it is single-frame segmentation with a propagation call that covers one frame.

**Fix:** run propagation in both directions (SAM2 supports a reverse pass), or anchor on the
earliest strong detection instead of the highest-scoring one. Estimate: **half a day.**
Do this before claiming temporal tracking to a judge.

### 2.1f `[ ]` Second sample video finds no vehicles
`derived_patrol.mp4` + `"find all vehicles"` -> 0 flags, `NO_RELEVANT_EVENTS_FOUND`, only
`grounding_dino` in `models_used`. The same video *does* return a confident flag for
`"purple flying saucer"` (detector 0.563), which is 2.1a from the other direction: the detector
responds to the nonsense prompt but not the real one. **Demo on `real_aerial_footage.mp4`.**

---

## 3d. Browser UI walkthrough — driven with Playwright 2026-09-07

Uploaded `datasets/samples/real_pair/real_image_a.png` + `real_image_b.png` through the real
dropzone, typed a query, clicked Run. **The UI works end to end.**

Upload registered "2 assets" with modality auto-detected `optical` and a live preview. The run
issued `POST /api/analyze` -> 200, then `/api/jobs/{id}`, `/api/results/{id}` and
`/api/analysis/{id}/visualizations/change_overlay`, and routed to `/analysis/{job_id}` showing
`COMPLETED`, `routing: agent intent controller`, `task: bi_temporal_change_vqa`.

**The Trace panel is the strongest asset in the product** — every tool with its own duration
(`run_change_detection` 1017ms, `run_change_vqa` 217ms, `generate_overlay` 29ms, `generate_report`
16ms, 1279ms total). That is the answer to "is the orchestration real?" and it already exists.

### `[ ]` 3d-i · Statistics panel reads a key that does not exist — **demo-critical**
The UI shows **Regions 0, Pixels Changed 0, Area 0 m²** while the answer claims "10% to 20% change".
`frontend/src/app/analysis/[jobId]/page.tsx:170-171` reads `data.metrics?.regions` and
`data.metrics?.changed_pixels`. **The response has no `metrics` key at all.** The real values live at
`evidence.spatial.statistics`:

| UI reads | actual path | actual value |
|---|---|---|
| `metrics.regions` | `evidence.spatial.statistics.region_count` | **171** |
| `metrics.changed_pixels` | `evidence.spatial.statistics.changed_pixels` | **15,542** |
| *(nothing)* | `evidence.spatial.statistics.change_ratio` | 0.237 |

Note `regions` vs `region_count` is a second mismatch inside the first. Fifth field-name mismatch
found this session, after 2.1, Option B, VRSBench records, and the health payload.

### `[ ]` 3d-ii · The backend's own quality warning is never shown — **honesty risk**
The API returned:
```
"quality_status":  "REVIEW_REQUIRED"
"quality_warning": "Excessive change detected (61.6%). Widespread radiometric or seasonal
                    variation between T1 and T2 may cause false positives."
"diagnostic_flags": ["EXCESSIVE_CHANGE"]
```
**None of this reaches the screen.** The UI presents a clean answer at 56.9% confidence while the
backend is flagging the result as unreliable — which is exactly the broken ChangeFormer path (§1.3,
measured IoU 0.0376) being hidden from view. Surfacing this costs almost nothing and directly serves
§3 item 4 (audit report) and the `prd.md` §5 "zero fabrication" requirement.

### `[ ]` 3d-iii · Query echoes as empty
The analysis page shows `QUERY ""`. `/api/results/{id}` does not return the query at all — the
response has no `query` key. Add it backend-side.

### `[ ]` 3d-iv · Evidence panel says "No evidence registered"
It reads only `evidence.spatial.boxes`, which is `[]` for change detection. But
`has_mask: true` with a real `mask_path`, `geojson_path` and `overlay_path` are all present.

All four are frontend/API contract fixes, no model work. Together: **half a day**, and they
transform what a judge sees.

---

## 3e. `[x]` Video in the browser — **FIXED 2026-09-07**

Was: upload worked, backend returned HTTP 200 with a correct flag, and the page showed
`NO_DATA / 0 events`. Took **four** separate fixes, each hidden behind the previous one. Every
API-level test passed throughout, because they read the POST response directly — **only driving the
browser exposed any of this.**

### 1. Four tables were never migrated
`GET /api/video/{job_id}` returned HTTP 500: `relation "videos" does not exist`. The database held
7 tables; `videos`, `video_frames`, `video_flags` and `visualization_layers` were defined in
`backend/app/db/models/` but had no migration — only `001_initial_schema` and `002_enable_rls`
existed, both predating those models.

Fixed by `f1b7463d221d_add_video_and_visualization_tables.py`, generated with
`alembic revision --autogenerate` so the DDL derives from the models rather than being hand-written.
Autogenerate detected exactly the 4 tables and their indexes and **no changes to the existing 7**.
Added `_enable_rls()` to match `002_enable_rls`, since this is Supabase and those four would
otherwise have been the only tables without row-level security.

Verified: all 11 tables present, `RLS=True` on every one.

### 2. `NameError: VideoFlag is not defined`
`api/v1/endpoints/video.py` used `VideoFlag` at lines 275/277 without importing it. The missing
tables had been masking it.

### 3. `NameError: TaskType is not defined`
Same file, line 302. Fixed, then swept the whole backend with `pyflakes`, which found **two more
latent NameErrors in code that has never run**:
- `api/v1/endpoints/visualization.py:238` — `create_change_overlay` used, never imported
  (the fallback branch when a pre-rendered overlay is missing)
- `workflows/grounding_reasoner.py:444` — `Path` used in an `isinstance` check, never imported

Both fixed. `pyflakes backend/` is now clean of real undefined names.

### 4. The UI read a field the API never emitted
`frontend/src/app/video/[jobId]/page.tsx` read `results.events`; the API returns **`flags`**. And it
was not just a rename — `VideoEvent` (`id`, `timestamp_sec`, `score`) and `VideoFlag` (`flag_id`,
`start_timestamp`, `event_score`) have entirely different shapes. The frontend was written against
an imagined API.

Fixed with a contained mapping in the page so the renderer is untouched, plus `flags` /
`video_metadata` added to `VideoJobResult` in `lib/types.ts`. Also replaced the hardcoded
`totalSec = 45.2` with the real decoded `video_metadata.duration_sec`.

**Sixth field-name mismatch this session**, after 2.1, Option B, VRSBench records, the health
payload, and the statistics panel.

### Verified working in the browser
```
status            COMPLETED
Event Timeline    0:00 → 0:30.2      (real duration, was hardcoded 45.2)
timeline marker   0:00.0 — vehicles
Detected Events   1 events
event card        0:00.0 · vehicles · confidence score 0.86
Models Executed   grounding_dino, sam2
```
Suite **125 passed, 1 xfailed**. Frontend `tsc --noEmit` clean.

**Still cosmetic:** the page shows `QUERY ""` — `/api/video/{id}` does not return the query
(same as 3d-iii). Tell Sandipan about fix 4; it is his file.

---

## 3f. `[x]` Colour queries — **FIXED 2026-09-07**

### Before
All three queries boxed the same white car at the same frame; red and yellow returned the identical
detector score (0.879). `parse_v4_query` extracted the colour and then dropped it, so
`'spot a red car'` and `'spot a yellow car'` produced the **byte-identical** prompt `'spot car.'`.
`"spot"` was also missing from the verb stoplist, so the detector was asked for a nonexistent
`"spot car"` class (`"find"` was in the list, which is why `find all vehicles` worked and hid this).

### After — measured on the full 30s video (32 frames @ 1fps)
| query | prompt | flags | key result |
|---|---|---|---|
| `spot a red car` | `red car.` | 5 | **14.40-18.24s @ 0.881** — raw frame 228 is a red car |
| `spot white cars` | `white cars.` | 5 | 0.00-8.64s @ 0.916, 24.96-29.76s @ 0.909 |
| `spot a yellow car` | `yellow car.` | 6 | still flags at 0.79 — **see 2.1a** |

Ground truth: white/silver cars ~5.0s, 7.4s, 14.9s, 17.4s; one red car ~17.4s; no yellow car.
**Red and white are now correct in both object and timestamp.**

*(The earlier run that seemed to miss the red car used `max_frames=12`, which covers only the first
~9.6s — the red car at 17.4s was never sampled. Sampling coverage matters when judging timestamps.)*

### Fixes
1. `grounding_reasoner.py` — added `spot, track, count, look, search, where, give, me, any` to the
   verb stoplist.
2. `grounding_reasoner.py` — `clean_prompt` now keeps the colour: `f"{color} {category}."`.
   The reasoner's 0.15 `color` weight cannot substitute, because it only re-orders existing
   candidates and there is one candidate per frame.
3. `flagger.py` — **overlay was recolouring the whole frame.** It passed a numpy array to
   `create_change_overlay`, which routes arrays through `render_display_rgb`, a 2-98 percentile
   stretch for satellite rasters. On video it turned a red car green. Now passes the PIL image.

### Verification
- Suite **129 passed, 1 xfailed** (was 125).
- **VRSBench re-measured, no regression:** mIoU 0.2755 -> **0.2834**, R@0.5 0.29 -> **0.31**,
  detection rate 0.86 unchanged, 0 errors — same seed 42, same "all" subset, 100 records.
- Two pre-existing tests asserted the old prompt; updated as **deliberate contract changes** with
  the reason named in a comment, not quietly relaxed.
- Written up in `project/qna.md` **Q-004** per `rules.md` §6.

### Still open
`spot a yellow car` returns a confident flag for a car that is not there (0.79). That is **2.1a**,
not this fix: Grounding DINO ranks the best-matching region and has no "nothing here" output. The
colour fix makes the *right* answer right; it does not make the *absent* answer safe.

Also worth a decision: the SAM 2.1 mask paints the target green (`(0, 230, 150)` @ alpha 0.45), so
in a colour demo the car's actual colour is hidden by the highlight.

---

## 3g. `[x]` Event timestamps were wrong — **FIXED 2026-09-07**

Reported: white-car timestamps a few seconds off, and events that did not correspond to actual
appearances. Ground truth (author, confirmed by dense 4 fps sampling): white cars visible
**4-8s, 14-18s, 25-27s**.

### Four separate causes

**1. Clustering ignored its own frame criterion.** `flagger.py:103` read
`frame_gap <= max_gap_frames or time_gap <= max_gap_seconds`. Frames are sampled with a stride, so
consecutive detections sit ~12 frame indices apart and `frame_gap <= 2` is essentially never true —
the **OR** meant only the time test ever fired, and event boundaries were set by wherever the coarse
sampling happened to land. Now clusters on time, with the frame test kept only as an extra
allowance for densely-sampled runs.

**2. The persistence filter could not filter.** `if frame_span < min_frames and duration <
min_seconds: continue` — an **AND**, so a 2-frame 0.24s blip passed on frame count alone and became
an "event". Now an OR: a cluster must satisfy both.

**3. Low-quality detections were accepted.** At `box_threshold=0.25` the detector also returned, on
empty asphalt at t=0: a **99.8%-area full-frame box** (score 0.282) and a **24x43px white
parking-line marking** (score 0.284). Real vehicles score **0.67-0.89**. Those artefacts produced
the spurious 0-4s events. Added `min_detector_score` (0.35) and `max_box_area_ratio` (0.90).

**4. Sampling was too coarse.** `sample_fps` defaulted to 1.0, quantising every boundary to ±1s.
Raised to 2.0.

### Result — matches the reported truth

| reported | measured |
|---|---|
| 4 → 8s | **4.80 – 8.16s** (3.4s) |
| 14 → 18s | **14.88 – 18.24s** (3.4s) |
| 25 → 27s | **25.44 – 27.36s** (1.9s) |

Three discrete segments, not one 4-27s span. `spot a red car` → a single segment 15.36-18.72s.
`spot a yellow car` → NOT_APPLICABLE.

### UI now shows ranges
The event card and timeline tooltip previously showed only the start. Both now show the visible
range and its duration: `0:04.8 → 0:08.2 (3.4s)`. Verified in the browser.

### Suite is fully green for the first time: **132 passed, 0 xfail**
The detector-quality gate also closed the last open case — `spot the purple flying saucer` on
`derived_patrol.mp4` is now rejected, so `test_video_workflow_no_events_found` went from `xfail` to
passing and the marker was removed.

**Correction:** an earlier draft of this section said the saucer was rejected on confidence
(0.563 vs 0.67-0.89). That is wrong. Its confidence *passes* the 0.35 floor. It is rejected by
`max_box_area_ratio`: the detector returns a **99.9%-of-frame** box on all three sampled frames.
That distinction matters, because the area rule is a principled one (a box covering the whole frame
is not an object detection) rather than a threshold fitted to this clip — so it is the part of this
change most likely to generalise, and the claim of "class-level open-set rejection" rests on it
being a degenerate-box rejection, not a semantic one.

Two pre-existing tests were sampling only the first ~3-4s of a 30s clip — a window containing no
vehicle — and had been passing on the 0.28 artefacts. Their sampling windows were widened to reach
the real car at 4.8-8.2s rather than the assertions being relaxed.

---

## 3h. Is the green suite overfitted? — honest audit 2026-09-07

Asked directly: are the thresholds hardcoded to `real_aerial_footage.mp4`? **No timestamps or
video-specific constants exist in the code**, but two thresholds *were derived from measurements on
that single clip*, and that is a real overfitting risk worth stating.

### Tuned on one video — treat as provisional
| constant | value | derived from |
|---|---|---|
| `min_colour_score` | 0.45 | present colours 0.97-1.00 vs absent 0.21-0.26, **one clip** |
| `min_detector_score` | 0.35 | real vehicles 0.67-0.89 vs artefacts 0.28, **one clip** |

### Principled — not fitted to data
| change | why it generalises |
|---|---|
| `max_box_area_ratio` 0.90 | a box covering ~all of the frame is not an object detection |
| `sample_fps` 2.0 | finer boundaries; no data dependence |
| cluster on time | fixes an OR whose frame test could never fire under strided sampling |
| persistence AND -> OR | the filter previously could not reject anything on duration |

**The flying-saucer rejection rests on the area rule, not the tuned score** — see the correction in
3g. That is the more generalisable half.

### Evidence it holds beyond the tuning clip
- **VRSBench, 9,350 images, completely different data.** After the prompt change: mIoU
  0.2755 -> **0.2834**, R@0.5 0.29 -> **0.31**, 0 errors. A real held-out benchmark, no regression.
- **Colours never used in tuning.** `blue` -> NOT_APPLICABLE (correct). `silver` -> the same three
  segments as `white` (correct — the cars are white/silver, and the scorer treats them alike).
- **Held-out video** `derived_patrol.mp4` (trees and dirt, **no vehicles**): `white cars`,
  `red car` and `find all vehicles` all return **0 flags**. No false positives on unseen content.

### Known weaknesses — do not oversell these numbers
1. **`spot a black car` returns 0 flags** and a dark vehicle does appear around 7.4s. 31 candidates
   were rejected as low-quality and 14 by colour; the single survivor was dropped by the persistence
   filter. **Likely a false negative.**
2. **Only one video in the repo contains vehicles.** There is no true held-out *detection* test —
   `derived_patrol.mp4` proves absence of false positives, not presence of true positives.
3. **The brightness-based scorers are exposure-sensitive.** `white = brightness/200` and
   `black = 1 - brightness/100` are absolute, so a brighter or darker clip will shift them. These
   should be normalised against per-frame statistics rather than fixed constants before anyone
   claims robustness.
4. **Two test fixtures were widened** to reach the vehicle at 4.8-8.2s. Legitimate — they were
   previously passing on 0.28 artefacts — but it is still fitting the tests to this clip.

### What would actually establish robustness
Two or three more real aerial clips with known contents, and replacing the absolute
brightness thresholds with per-frame normalised ones. Until then: the **logic fixes** are sound and
general; the **two thresholds** are calibrated to one clip and one lighting condition.

---

## 4. Ordering

Foundation first, per the decision on 2026-09-07.

1. ~~§2.4 boot validation~~ — **done 2026-09-07**, 120/120 green
2. §1.4 real availability check — half a day
3. §1.3 vendor upstream ChangeFormer — half a day *(quiz-gated)*
4. ~~§2.1 diagnose video zero-detections~~ — **done 2026-09-07**; spawned §2.1a/b/c, ~1 day remaining
5. §1.1 optical–SAR build — 1–2 days *(**Option A** chosen 2026-09-07)*
6. §1.2 wire BigEarthNet, lead with CDVQA — 1–2 days
7. §2.3 + §2.2 wire the dead capabilities — 3–5 days
8. §3 items 3/4/5 — trace, audit report, response composer — 4 days
9. §3 items 1/7 — frontend pass, security — 3–5 days
10. §3 item 6 — 3D, only if time remains

**Blockers 1–7 ≈ 8–12 working days. Everything ≈ 18–25.**

Estimates assume one person and no new training runs. §1.1 Option B and any ChangeFormer retraining
fall outside them.

---

## 4b. Open quiz gates (`rules.md` §6)

Both are changes the author must be able to defend; neither is answered yet.

- `[ ]` **§1.3 ChangeFormer** — vendor upstream `wgcban/ChangeFormer`, repoint the adapter,
  switch preprocessing to 256/`[-1,1]`, retire `network.py`. ~5 files.
- `[ ]` **§1.4 model-registry verification** — wire `mark_verified()` as above.

---

## 5. Waiting on Ayushman

1. Which validation set produced ChangeFormer IoU 0.687 — blocks closing §1.3
2. The real training notebook (`handoff/changeformer/TRAINING_SCRIPT.py` is a reconstruction)
3. A working `pip freeze` from the Kaggle/Colab environment — he sent version *ranges* that
   contradict our working install (transformers 5.16.1, torch 2.14.0, 117/0 passing)
4. ~~Optical–SAR: Option A or B~~ — **Option A chosen**; tell him so he does not build B

## 6. Explicitly not before the demo

Multi-user auth/RBAC · STAC harvesting · edge/ONNX packaging · retraining any foundation model ·
the `models/` → `ml/adapters/` migration beyond what is already merged.
