# Model Dossier: LocateAnything-3B

---

# 1. Model Identity
- **Model Name**: LocateAnything-3B
- **Model Family**: NVIDIA Eagle "Embodied" vision-language grounding models
- **Architecture**: MoonViT-SO-400M vision tower + 2-layer MLP connector + Qwen2.5-3B decoder with a
  multi-token-prediction (MTP) head
- **Task**: Open-vocabulary detection / phrase grounding by generating coordinate tokens
- **Modality**: RGB image + natural-language query
- **SatQuery Role**: Fallback detector in `workflows/grounding.py` when Grounding DINO returns no
  boxes and `grounding_model="auto"`; selectable directly as `grounding_model="locate_anything"`.
- **Current Status**: IMPLEMENTED, runs on RTX 3070. **Less accurate than Grounding DINO on our
  airport tile** (§5), so it is used only as the fallback (2026-09-16, `project/qna.md` Q-021)

---

# 2. Official Source
- **Model Hub**: [`nvidia/LocateAnything-3B`](https://huggingface.co/nvidia/LocateAnything-3B),
  pinned revision `c32291ca5e996f5a7a485845b4f57a233936bba0`
- **Reference code**: https://github.com/NVlabs/Eagle/tree/main/Embodied
- **Licence**: NVIDIA research, non-commercial. Fetch from the Hub; do not re-host the weights.

---

# 3. Setup

```bash
pip install -r backend/requirements.txt          # adds bitsandbytes, peft, accelerate, decord, lmdb, requests
python scripts/setup_locate_anything.py           # download @ pinned revision, apply patches, verify
python scripts/setup_locate_anything.py --check --hash-weights
```

Weights: 2 safetensors shards, 7.66 GB bf16, into `checkpoints/locate_anything_3b/` (gitignored).
The vendor code needs local patches to run on transformers 5.x; they are tracked in
`third_party/locate_anything/` — see `UPSTREAM.md` there for every hunk and why.

---

# 4. How SatQuery calls it

`LocateAnythingAdapter.predict(image, "airplane")` builds the vendor `ground_multi` prompt

```
Locate all the instances that match the following description: airplane.
```

and the model answers with coordinate tokens normalised to 0–1000, `x1 y1 x2 y2` order:

```
<ref>airplane</ref><box><0><96><188><443></box>…<|im_end|>
```

`parse_boxes()` maps them to pixel coordinates of the original image, drops zero-area and duplicate
boxes, and returns the same candidate dicts as Grounding DINO (`xyxy`, `bbox`, `box_2d`, `score`,
`label`). A query with no match returns `<box>None</box>` and an empty list.

Settings (`configs/models.yaml → models.locate_anything`):

| Key | Default | Why |
|---|---|---|
| `quantization` | `4bit` | fits beside Grounding DINO + SAM 2 on 8 GB; see §5. `8bit` = exact but slow; `none` for ≥ 16 GB GPUs |
| `generation_mode` | `slow` | vendor `hybrid` runs away (boxes along the image edge until the token cap) |
| `temperature` | `0.0` | vendor sampler samples iff `temperature > 0` and ignores `do_sample` |
| `repetition_penalty` | `1.0` | no gain on small tiles; 1.1 made dense quantized queries run longer |
| `max_new_tokens` | `1024` | dense 1024 px queries hit any cap; bounds worst-case latency (~40 s at 4-bit) |

The vision tower, connector and `lm_head` are never quantized. Result metadata records
`quantization`, `generation_mode`, `truncated` (no `<|im_end|>` before the cap), `raw_box_count`,
`dropped_degenerate`, `dropped_duplicate` and the full `raw_answer`.

---

# 5. Measured performance (RTX 3070 8 GB, 2026-09-16)

Greedy, slow decoding. Reference = bf16 with part of the model offloaded to CPU. A box matches when
IoU ≥ 0.5. "Small tiles" = 6 image/query pairs on 512 px tiles, each at repetition penalty 1.0 and 1.1.

| Precision | Recall vs bf16 | Precision vs bf16 | Peak VRAM | Airport tile |
|---|---|---|---|---|
| bf16 (offload) | — | — | 6.03 GiB | 18.2 s |
| 8-bit, skip vision/head | 26/26 | 26/26 | 5.98 GiB | 6.8 s |
| **4-bit, skip vision/head (default)** | **22/26** | **22/22** | **4.74 GiB** | **2.1 s** |
| 4-bit, all quantized (old adapter) | 19/26 | 19/22 | 4.15 GiB | 2.4 s |

Load: ~7–12 s. Allocated after load at 4-bit: 3.31 GiB.

**The precision table measures agreement with bf16, not correctness.** It shows how much
quantization changes the answer, not whether the answer is right.

**Correctness vs Grounding DINO on our imagery (2026-09-16, same API path, airport tile):**

| Detector | Prompt | Proposed | Masked | Top-ranked |
|---|---|---|---|---|
| Grounding DINO | "mask the airplanes" | 4 | 3 | the airliner (0.73) |
| LocateAnything | "mask the airplanes" | 16 | 16 | a jet bridge |
| LocateAnything | "mask the airplane" | 5 | 5 | a jet bridge |

The tile has one aircraft. LocateAnything labels jet bridges and service vehicles as
"airplane", and over-proposes badly on the plural prompt. Its fixed 0.5 score passes
`box_threshold`, and it leaves the V4 reasoner nothing to rank with, so the false positives
reach the masks. **It does not beat Grounding DINO here.** Keep it as the fallback only (the default
`auto`); `SATQUERY_GROUNDING_MODEL=locate_anything` is for comparisons.

**Roads ("mark all roads", 1024 px, via the API):** on the rural image its single box covered
the whole frame and was dropped; on the suburb it proposed the street grid (which Grounding DINO
misses) but as neighbourhood-sized boxes, so SAM 2 masked the lawns too (317,021 px vs Grounding
DINO's 39,433 px). A box detector is the wrong tool for roads at any size (Q-020, Q-022).

**Memory:** on a 1024 px input MoonViT attention allocates ~822 MiB extra. With Grounding DINO and
RemoteCLIP still loaded this runs out of memory; the executor then releases models and retries.

**Known weakness — dense scenes.** On `satquery_change_after.png` (1024 px), `building` reached the
token cap in every precision including bf16 (4-bit: 97 boxes, 41 s), and `road` returned 4 boxes at
4-bit and 7 at bf16. This does not resolve Q-020's road under-masking.

---

# 6. Limitations
- **No calibrated confidence.** Every box has `score = 0.5`; `box_threshold` does not filter it.
- **Resolution ceiling.** The processor caps input at 25 600 patches (≈ 5 MP at 14 px patches) and
  rejects sides ≥ 7168 px; larger scenes are downsampled internally.
- **Hybrid/fast decoding** are unreliable in our stack; only `slow` is tested.
- **No flash/magi attention kernels** installed; the code falls back to PyTorch SDPA.

---

# 7. Tests
- `tests/unit/test_locate_anything_parsing.py` — box parsing, no weights
- `tests/unit/test_grounding_locate_anything_fallback.py` — workflow fallback wiring, mocks
- `tests/models/test_locate_anything.py` — real weights + CUDA; skips cleanly otherwise
- Fixtures: `tests/data/grounding/airport_apron.png` (one airliner, plus jet bridges and service vehicles),
  `tests/data/grounding/05933_0000.png` (tennis courts; negative for "airplane")
