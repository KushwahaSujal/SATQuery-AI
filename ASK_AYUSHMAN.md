# What I need from Ayushman

Forwardable as-is. Ordered by how much it blocks.

**Context:** I've got the backend running on a clean machine — Python 3.11, CUDA on a 3070,
108/120 tests passing. Every one of the 12 non-passing tests is "model weights not on disk",
because `checkpoints/` is gitignored and never left your machine. I've already pulled everything
that's public from HuggingFace. What's left is the stuff only you have, plus a few questions that
code can't answer.

---

## A. Files — only you have these

These three are SatQuery-specific, so I can't download them. Everything else I've handled.

| # | File | Goes in | Blocks |
|---|---|---|---|
| **A1** | `satquery_changeformer_best.pt` | `checkpoints/changeformer/` | **All change detection.** Also blocks the investigation into the bug you reported. This is the #1 item. |
| **A2** | `cdvqa_satquery.pt` | `checkpoints/cdvqa/` | Change-VQA — one of the mandatory SIH capabilities |
| **A3** | `satquery_fusion.pth` | `checkpoints/optical_sar/` | Optical–SAR analysis (also mandatory). See question B3 before sending — it may not be worth sending. |

Any transfer is fine — Drive, WeTransfer, USB. Please **don't** commit them to git; they're
correctly gitignored and should stay that way.

**Already sorted, don't bother:** Grounding DINO, SAM 2.1, BLIP (general_rs_vlm), DOFA, RemoteCLIP,
BigEarthNet — all public on HuggingFace, I'm pulling them directly.

---

## B. Questions — genuinely more important than the files

### B1. How was `satquery_changeformer_best.pt` produced? ⚠️ highest priority

There's no ChangeFormer training script anywhere in the repo, so I can't tell what the model
expects as input. Specifically:

- Did you **fine-tune** it yourself, or convert/rename a released checkpoint from
  `wgcban/ChangeFormer`?
- If you trained it: **what normalisation did your dataloader use?**
  - ImageNet stats — `mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]`, or
  - `[-1,1]` rescale — `mean=[0.5,0.5,0.5]`, `std=[0.5,0.5,0.5]`?
- What **input size** did you train at — 256×256 or 512×512?
- Can you send the **training script or notebook**? Even a rough one.

**Why this matters and why it's probably your bug.** Our two docs contradict each other:
`SATQUERY_AI_MASTER_DOCUMENTATION.md` §26 says training used `[-1,1]` and that ImageNet was the
bug that got fixed. `docs/models/CHANGEFORMER_V6.md` §10 says ImageNet is correct. **The code uses
ImageNet.** One of those documents is wrong.

If the checkpoint was trained on `[-1,1]` but we feed it ImageNet-normalised input, the tensors are
roughly twice the magnitude the model expects and per-channel skewed — which produces exactly what
you described: change masks that are blank, or saturated, or just not lining up with the real
difference. Your answer decides this in one line. I've already written the script that measures it
across all the candidate settings (`scripts/diagnose_changeformer_preprocessing.py`) — it just
needs A1 to run.

### B2. When you saw the bug, what were you feeding it?

- Which two images exactly? (LEVIR-CD pair, our `datasets/samples/real_pair/`, or your own?)
- **PNG/JPEG, or GeoTIFF?**
- What did you expect vs what you got — blank mask, everything marked as changed, or right shape
  but wrong place? A screenshot is ideal.

**Why:** I proved a separate real bug — any image deeper than 8-bit gets mangled. A 12-bit GeoTIFF
arrives at the model ~26× out of range, a 16-bit one ~430×. If you were on GeoTIFF, that alone
explains it and I can fix it today. If you were on PNG, it's the normalisation question above.
The two need different fixes, so I don't want to guess.

### B3. How was `satquery_fusion.pth` created?

`docs/SATQUERY_AI_MODEL_DATA_SETUP.md` §F says to generate it like this:

```python
net = CrossAttentionFusionNet()
torch.save(net.state_dict(), 'checkpoints/optical_sar/satquery_fusion.pth')
```

That's a **freshly constructed, untrained network** — random weights. It also references
`scripts/train_optical_sar_fusion.py`, which doesn't exist in the repo.

If that's really how it was made, then the land-cover classes, "surface roughness" and "built-up
index" it reports are random noise formatted to look like findings. That's one of the six mandatory
SIH requirements, and it's the kind of thing a mentor asks "how did you train this?" about.

**Just tell me straight — was it ever trained?** No blame either way; I need to know whether to
train it on BigEarthNet, replace it with an honest rule-based analysis, or disable it. Any of those
is fine. Shipping random weights isn't.

### B4. Where did the VRSBench grounding numbers come from?

The master doc reports V1 mIoU 0.1832 / V2 0.2371 / V3 0.2238 as VRSBench results. I checked
`datasets/samples/vrsbench_sample_records.json` against the real 16,159-record VRSBench eval split:

- There are **2 records**, and both point at `real_image_b` — which is a **LEVIR-CD** crop, not a
  VRSBench image.
- Record 1's question is **word-for-word from real VRSBench**, where it belongs to `P0003_0002.png`
  with a different ground-truth box. Here it's pointed at the LEVIR-CD crop with a hand-made box.
- Record 2's question doesn't exist anywhere in VRSBench, and it reuses record 1's box exactly.

I'm assuming this started as a smoke-test fixture and the numbers got written into the docs as
"results" later — easy drift, no drama. But we can't put those numbers in the PPT or the paper,
because if a judge checks, it looks like fabricated benchmarks.

**Was there ever a run against the real VRSBench split?** If yes, send the output JSON. If no, say
so and I'll produce real numbers — I've already downloaded the official split.

### B5. Any local changes not pushed?

`main` has only 2 commits and `checkpoints/`, `results/` and `datasets/` are all gitignored. If
you've got fixes, eval outputs, or training scripts sitting locally, they're invisible to me.
Anything in `results/` from previous runs is especially useful — that's where real measured numbers
would live.

---

## C. Heads-up on things I've already changed

So we don't collide:

- **Fixed a real database bug.** Our Supabase URL uses the transaction pooler on port 6543, which
  breaks asyncpg's prepared statements. Symptom is nasty: the health check passes and it fails
  later under load. Verified against the live DB and fixed in `backend/app/db/session.py`.
- **Deleted dead code** on branch `refactor/s0-remove-dead-layers`: `agent/planner.py`,
  `agent/router.py` and the five `*Workflow` classes were never called by anything —
  `AgentController` assigns `self.planner` and never reads it. Tests went 120 → 112 with an
  identical failure list, so nothing behavioural changed.
- **`requirements.txt` is missing two packages** that the code imports: `aiosqlite` (the whole test
  suite needs it) and `sam2`. Also everything is unpinned, so a clean install now pulls
  `transformers 5.16.1` — a major version the adapters were written before. Worth pinning from a
  known-good environment; if you have a working `pip freeze`, send it.
