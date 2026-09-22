# LocateAnything-3B — Bring-Up and Verification Plan

**Date:** 2026-09-16
**Branch:** `prototype`
**Owner of existing code:** Sandipan (wired in `c2d62ab`, merged via `e1be13b`)
**Status:** integration already exists — this plan is **bring-up and verification**, not integration.

---

## Outcome — removed, 2026-09-16

Bring-up succeeded, but measured through the real API LocateAnything was less accurate than
Grounding DINO on our imagery (airport: jet bridges and vehicles labelled "airplane"; roads: one
frame-sized box, or neighbourhood-sized masks) and it costs 3.3 GiB of GPU memory. It was removed
after the working integration was committed (`528662d`), so `git revert` of the removal commit
restores it. See `project/qna.md` Q-021, Q-022, Q-023. The sections below are the plan as written.

## Status — end of 2026-09-16

| Phase | State |
|---|---|
| 0 · reproducible patches | **Done.** `third_party/locate_anything/`, `scripts/setup_locate_anything.py` |
| 1 · make it load | **Done.** 4-bit (vision/connector/head kept bf16), 3.31 GiB |
| 2 · parity + determinism | **Done.** Greedy `slow`; parsing and model tests pass |
| 3 · pipeline wiring | **Partly.** Fallback covered by tests; calibrated scores (F5) not started |
| 4 · accuracy / Q-020 | **Measured, not solved.** Dense 1024 px queries hit the token cap |
| 5 · docs + record | **Done.** `docs/models/LOCATE_ANYTHING.md`, `project/qna.md` Q-021 |

What bring-up found beyond F1–F7 below, all recorded in Q-021:
- transformers 5.x left the vendor RoPE tables at zero/NaN, so every output was empty.
- Sandipan's `rope_theta` fallback silently used 1e4 instead of 1e6.
- `peft`, `decord`, `lmdb`, `requests`, `accelerate` were also missing.
- The vendor `hybrid` decoder runs away on our tiles.

**Correction to F4 below:** switching to `do_sample=False` would not have fixed it. NVIDIA's sampler
ignores `do_sample` and samples whenever `temperature > 0`. The fix that shipped is `temperature=0.0`.
F7's claim that the box mapping is correct was confirmed by the model tests.

---

## TL;DR

The LocateAnything-3B *integration* was already written and merged. What was missing was the
weights, and nobody has ever executed the code path. Today the weights landed
(`checkpoints/locate_anything_3b/`, 7.2 GB).

Verifying the local files against the vendor release turned up **one hard blocker, one serious
reproducibility risk, and one correctness bug** — plus confirmation that several things I had
assumed were broken are in fact correct.

| # | Finding | Severity | Phase |
|---|---|---|---|
| F1 | `bitsandbytes` is not installed; the adapter's only load path requires it | **Blocker** | 1 |
| F2 | Vendor model code is locally patched, undocumented, and in a **gitignored** directory | **Blocker (project risk)** | 0 |
| F3 | RTX 3070 has 7.7 GB VRAM; the model is 7.66 GB in bf16 — it does not fit | **Hardware constraint** | 1 |
| F4 | Adapter samples (`do_sample=True, temperature=0.7`) — boxes are non-deterministic | **Correctness** | 2 |
| F5 | Every box gets a hardcoded `score=0.5`, so the V4 reasoner ranks on no signal | Medium | 3 |
| F6 | Image processor caps at ~5.0 MP; full-res scenes get silently downsampled | Low today, matters for Q-020 | 4 |
| F7 | Coord scale, processor API, and prompt template are all **correct as written** | Verified OK | — |

---

## §0 — What landed on disk today

Source: `~/Downloads/locate_anything_3b.zip` (6.24 GB), an `hf download` snapshot of
`nvidia/LocateAnything-3B` at commit `c32291ca5e996f5a7a485845b4f57a233936bba0`.

Extracted to `checkpoints/locate_anything_3b/` — which is exactly the path
[`configs/models.yaml:79`](../../../configs/models.yaml#L79) already expects. `checkpoints/**` is
gitignored ([`.gitignore:43`](../../../.gitignore#L43)), so nothing here enters version control.

```
model-00001-of-00002.safetensors   4.96 GB
model-00002-of-00002.safetensors   2.70 GB   → 7.66 GB bf16, 770 tensors
modeling_locateanything.py         custom arch (LocateAnythingForConditionalGeneration)
modeling_qwen2.py                  patched Qwen2 (MTP / block decoding)
processing_locateanything.py       LocateAnythingProcessor
image_processing_locateanything.py MoonViT patchifier
generate_utils.py                  MTP hybrid generator + <box> pattern handling
batch_infer.py, batch_utils/       reference CLI — our ground truth for parity
kernel_utils/range_attention.py    "la_flash" custom attention kernel
```

Reference implementation for cross-checking: https://github.com/NVlabs/Eagle/tree/main/Embodied

---

## §1 — Findings, with evidence

### F1 — `bitsandbytes` missing (BLOCKER)

[`locate_anything.py:158-173`](../../../backend/app/ml/adapters/locate_anything.py#L158-L173) builds a
`BitsAndBytesConfig` and passes it to `from_pretrained`. That is the **only** load path — there is no
unquantized branch.

```
$ .venv/bin/python -c "import bitsandbytes"
ModuleNotFoundError: No module named 'bitsandbytes'
```

Every call therefore raises `ModuleNotFoundError` inside the `try`, which
[`locate_anything.py:177-193`](../../../backend/app/ml/adapters/locate_anything.py#L177-L193) converts
to `ModelUnavailableError`. In the pipeline that surfaces as
`fallback_to_locate_anything → skipped (model_not_available)`
([`grounding.py:264`](../../../backend/app/workflows/grounding.py#L264)) — a **silent** degradation.
The grounding request still returns, just with no fallback. This is why the gap was never noticed.

**Conclusion: this code path has never executed successfully on any machine.**

### F2 — Patched vendor code in a gitignored directory (BLOCKER, project risk)

Two files carry mtimes a day later than the rest of the snapshot. Verified against the git blob
hashes recorded in the snapshot's own `.cache/huggingface/download/*.metadata`:

| File | Upstream blob | Local blob | |
|---|---|---|---|
| `modeling_vit.py` | `cc6b383…` | `cc6b383…` | unmodified |
| `processing_locateanything.py` | `2be6905…` | `2be6905…` | unmodified |
| `modeling_locateanything.py` | `8e61b1d…` | `c035c3b…` | **modified** |
| `modeling_qwen2.py` | `e42a31e…` | `0250e78…` | **modified** |

I fetched the pristine upstream files at the pinned commit and diffed. The changes are
**transformers-version compatibility patches** — NVIDIA targets `transformers 4.51.0`
(`generation_config.json`), the venv has **5.16.1**:

- `_check_and_adjust_attn_implementation(..., allow_all_kernels=False)` — new parameter in 5.x (both files)
- `_tied_weights_keys` list → dict — 5.x changed the type (both files)
- `self.post_init()` added to `__init__` — required for correct loading in 5.x
- `DynamicCache` legacy-cache handling rewritten — `use_legacy_cache` removed in 5.x
- `rope_theta` defensive `getattr` fallback

These are plausible and probably correct. **The problem is not the patches, it is that they exist on
exactly one machine, with no record.** Anyone who re-downloads the weights, or sets up a second dev
box or the cloud GPU node, gets upstream code that fails against transformers 5.16.1 — with no hint
that seven hunks of patching are missing.

> **Checked and cleared:** `_tied_weights_keys = {}` looked dangerous, since `config.tie_word_embeddings`
> is `true` and clearing it could leave `lm_head` randomly initialised. It is safe here —
> `language_model.lm_head.weight` is explicitly present in `model.safetensors.index.json`, so it is
> loaded from disk rather than tied.

### F3 — The model does not fit in VRAM

```
GPU: NVIDIA GeForce RTX 3070, 7.7 GB
Model: 7.66 GB bf16
```

bf16 weights alone leave nothing for activations, KV cache, or the display. Quantisation or offload
is mandatory locally. This is presumably why Sandipan wrote the 4-bit path — but 4-bit was never
tested (F1), and it has to survive a custom MTP generator (`block_size: 6`) plus a custom `magi`
attention implementation (`config.json: "_attn_implementation": "magi"`). That combination is
unproven and is the main technical unknown in this plan.

### F4 — Non-deterministic detections

[`locate_anything.py:342-356`](../../../backend/app/ml/adapters/locate_anything.py#L342-L356) hardcodes
`do_sample=True, temperature=0.7, top_p=0.9, repetition_penalty=1.1`.

For a *detector*, sampling is the wrong default: the same image and query produce different boxes on
every call. That breaks benchmark reproducibility, A/B comparison against Grounding DINO, and any
number quoted in the paper or demo. The values mirror `batch_infer.py`'s CLI defaults, which are
generation defaults, not detection defaults.

### F5 — Constant confidence defeats ranking

[`locate_anything.py:81`](../../../backend/app/ml/adapters/locate_anything.py#L81) assigns every box
`score = 0.5`. The model emits coordinate tokens with no calibrated per-instance confidence, so the
adapter is being honest — but the consequence is that the V4 reasoner ranks LocateAnything candidates
on a flat signal, and downstream thresholds (`box_threshold: 0.35`,
[`configs/models.yaml:82`](../../../configs/models.yaml#L82)) are meaningless for this model.

A real score can be recovered from the decoder: mean token log-prob over each box's coordinate tokens
(`coord_start_token_id: 151677` … `coord_end_token_id: 152677`).

### F6 — Resolution ceiling

`preprocessor_config.json` sets `in_token_limit: 25600` (the class default of 4096 is overridden), at
`patch_size: 14` → **~5.0 MP**. Larger images are bicubic-downsampled in
[`image_processing_locateanything.py:52-55`](../../../checkpoints/locate_anything_3b/image_processing_locateanything.py).
A hard ceiling also raises `ValueError("Exceed pos emb")` if either side exceeds 7168 px.

Current demo assets are **under** the limit, so this is not a demo blocker:

| Asset | Size | Patches | vs 25600 |
|---|---|---|---|
| `satquery_change_after.png` | 1024×1024 | 5 329 | fine |
| `satquery_airplane.png` | 512×512 | 1 296 | fine |

It matters for real full-res scenes, and it is directly relevant to **Q-020** ("mark the roads"
under-masks — detector recall). Thin linear features like roads are exactly what gets destroyed by
downsampling, so any road evaluation must state the input resolution it ran at.

### F7 — Verified correct (no action)

Things worth recording as *checked*, because they were plausible failure modes:

- **`_COORD_SCALE = 1000.0` is right.** `config.json` gives `coord_start_token_id: 151677` and
  `coord_end_token_id: 152677` — exactly 1000 coordinate tokens.
- **`py_apply_chat_template` and `process_vision_info` exist.** Non-standard names, but real, at
  `processing_locateanything.py:599` and `:549`.
- **The prompt template matches the vendor's `ground_multi` exactly.** Adapter
  [`:246`](../../../backend/app/ml/adapters/locate_anything.py#L246) emits
  `"Locate all the instances that match the following description: {q}."`, identical to README
  line 507 and `processing_locateanything.py:411`.
- **Box coordinate mapping is correct.** I previously flagged the proportional-scaling map at
  [`:370-373`](../../../backend/app/ml/adapters/locate_anything.py#L370-L373) as a likely accuracy bug,
  on the assumption the processor pads or crops. It does not — `rescale()` performs a pure per-axis
  `resize()` to a patch multiple. Normalised coordinates are invariant under independent per-axis
  scaling, so `x_norm × orig_w` recovers the original pixel position exactly. **That earlier concern
  was wrong.**
- **`AutoModel` (not `AutoModelForCausalLM`) is correct**, per `config.json.auto_map`, as the
  adapter's comment already states.

---

## §2 — Plan

### Phase 0 — Make the patches reproducible *(do this first; it protects everything else)*

Nothing else is trustworthy while the only working copy of the model code is untracked.

1. Create `third_party/locate_anything/` (tracked) containing:
   - `modeling_locateanything.patch`, `modeling_qwen2.patch` — unified diffs vs upstream
   - `UPSTREAM.md` — pins commit `c32291ca5e996f5a7a485845b4f57a233936bba0`, records the four
     upstream blob hashes, and states the transformers version the patches target (5.16.1)
2. Add `scripts/setup_locate_anything.sh` — downloads the repo at the pinned commit, applies both
   patches, verifies resulting blob hashes.
3. Record the patch rationale in `docs/models/LOCATE_ANYTHING.md` (see Phase 5).

**Verification**
```bash
# from a clean re-download, the script must reproduce today's working tree byte-for-byte
scripts/setup_locate_anything.sh --dest /tmp/la_verify
cd /tmp/la_verify && git hash-object modeling_locateanything.py modeling_qwen2.py
# expect: c035c3b21d8d58aa700a0e44a355f7c742fa5821
#         0250e78ee0bd9fa778cf6601e8d0eaed5682640e
```

### Phase 1 — Make it load *(resolves F1, F3)*

Separate "does the model run" from "does our adapter run". Establish the reference first.

1. **Reference path, no adapter.** Run the vendor CLI on a demo image:
   ```bash
   cd checkpoints/locate_anything_3b
   python batch_infer.py --model . --attn sdpa \
     --image ~/Downloads/satquery_airplane.png --query "airplane" \
     --out /tmp/la_reference.jsonl
   ```
   Expect OOM on the 3070 in bf16 — that is itself a datapoint. Record peak VRAM either way.
   Note `--attn sdpa`, not the `magi` default in `config.json`: start on the stock kernel.

2. **Pick the local execution mode.** In preference order:
   - **(a) Cloud GPU** — the box from
     [`2026-09-15-cloud-gpu-and-answers.md`](2026-09-15-cloud-gpu-and-answers.md) runs bf16 unquantised
     with no accuracy question. **Recommended for any number we intend to quote.**
   - **(b) Local 4-bit** — `pip install bitsandbytes`, keep the existing adapter path. Dev-loop only,
     and only if (c) confirms the boxes match.
   - **(c) Local bf16 + CPU offload** — `device_map="auto"` with `max_memory`, no new dependency.
     Slow, but numerically faithful, which makes it the reference for judging (b).

3. **Add an unquantised branch to the adapter.** Today quantisation is unconditional. Gate it on
   config (`quantization: none | 4bit`) so the same adapter serves the cloud GPU and the 3070.

**Verification**
```bash
.venv/bin/python -c "
from backend.app.ml.registry import model_registry
a = model_registry.get_adapter('locate_anything')
print('available:', a.is_available()); a.load_model(); print('loaded:', a._loaded)
import torch; print('peak VRAM GB:', round(torch.cuda.max_memory_allocated()/1024**3, 2))
"
```
Gate: loads without exception, peak VRAM recorded, `is_available()` no longer masks a missing
dependency.

### Phase 2 — Adapter/reference parity *(resolves F4)*

1. Switch the adapter default to `do_sample=False` (greedy). Keep sampling reachable via kwargs for
   deliberate diversity, never as the default.
2. Run the vendor CLI and `LocateAnythingAdapter.predict()` on the **same image + query** and compare
   `raw_answer` strings. Under greedy decoding they must be identical — any divergence means our
   prompt assembly or preprocessing differs from the reference.
3. Assert boxes land in the right pixel space by overlaying on `satquery_airplane.png`.

**Verification** — new `tests/models/test_locate_anything.py`:
- `raw_answer` from adapter == `raw_response` from `batch_infer.py`, greedy, same image/query
- two consecutive greedy `predict()` calls return byte-identical boxes (pins F4 shut)
- `<box><x1><y1><x2><y2></box>` parsing: known string in → known pixel boxes out (no GPU needed)
- every returned box satisfies `0 ≤ x1 < x2 ≤ W`, `0 ≤ y1 < y2 ≤ H`

### Phase 3 — Pipeline wiring *(resolves F5)*

1. Confirm the fallback actually fires: force Grounding DINO to return nothing and assert
   `fallback_to_locate_anything → success` in the step record
   ([`grounding.py:246-264`](../../../backend/app/workflows/grounding.py#L246-L264)).
2. Replace the constant `0.5` with mean coordinate-token log-prob per box; keep `0.5` as the
   documented fallback when logprobs are unavailable. Record in metadata which one was used.
3. Re-check `box_threshold` semantics in [`configs/models.yaml:82`](../../../configs/models.yaml#L82)
   once scores are real — the current value is inherited from Grounding DINO and is not calibrated
   for this model.
4. Verify the agent-side selection logic at
   [`inference.py:92-94`](../../../backend/app/agent/tools/inference.py#L92-L94) still routes `auto`
   correctly now that the model genuinely loads.

### Phase 4 — Accuracy work, Q-020 roads *(resolves F6)*

Only after Phases 1–3. This is where the model earns its place.

1. Head-to-head on the Q-020 road query: Grounding DINO vs LocateAnything on
   `satquery_change_after.png`, same prompt, greedy, boxes + recall recorded.
2. If full-res scenes exceed 5.0 MP, implement tiling with overlap and cross-tile box merging.
   Do **not** rely on the silent internal downsample.
3. Log input resolution and whether downsampling occurred in result metadata — every road number we
   quote must carry the resolution it was measured at.

### Phase 5 — Documentation and record

1. `docs/models/LOCATE_ANYTHING.md` — matching the existing `GROUNDING_DINO.md` shape; must cover the
   patch set, the pinned upstream commit, the resolution ceiling, and the confidence caveat.
2. Update `docs/models/MODEL_COMPARISON_MATRIX.md` and `MODEL_RESOURCE_REQUIREMENTS.md` with measured
   VRAM and latency — measured, not estimated.
3. File `project/qna.md` **Q-021** covering this bring-up: the patched vendor files and why
   (mechanism), cloud-GPU-vs-4-bit (rationale), the silent `model_not_available` path that hid the
   gap for days (blast radius), the parity test (verification), and the honest answer to "was this
   model ever actually running?" — **no, not until today** (defence).

---

## §3 — Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 4-bit breaks the custom MTP generator or `magi` attention | Local dev path dead | Phase 1 tests bf16+offload first as the numerical reference |
| Patches are lost on any re-download or new machine | Model silently reverts to broken | Phase 0, before anything else |
| 4-bit degrades box quality subtly | Bad numbers quoted as good | Parity test in Phase 2 compares against unquantised output |
| transformers upgrades again | Patches rot | `UPSTREAM.md` pins the tested version; pin `transformers` in requirements |
| `ModelUnavailableError` keeps degrading silently | Failures invisible in demo | Promote to a visible warning in the step record when a *configured* model is unavailable |

---

## §4 — Decisions needed

1. **Primary execution target** — cloud GPU (clean bf16, recommended) or local 4-bit (fast loop,
   needs validation)? Phase 1 step 2 branches on this.
2. **Role in the pipeline** — stay the fallback behind Grounding DINO, or become the primary detector
   for free-form/relational queries where GDINO is weakest? Current wiring is fallback-only
   ([`grounding.py:218`](../../../backend/app/workflows/grounding.py#L218)).
3. **Licence** — registry records *"NVIDIA Research (non-commercial)"*
   ([`registry.py:60`](../../../backend/app/ml/registry.py#L60)). Confirm that is compatible with the
   SIH submission terms before it appears in the demo.
