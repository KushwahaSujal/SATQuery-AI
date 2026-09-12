# What I need from Ayushman — v2

*Revised 2026-09-04 after receiving the checkpoints. Everything from v1 about sending files is
resolved — the zip had all of them and they are genuine. What's below is what the weights themselves
raised.*

Forwardable as-is.

---

## Status: files received, all real

The 3.1 GB zip is unpacked and verified. Nothing further needed on that front.

| model | size | verdict |
|---|---|---|
| changeformer | 492.6 MB | real weights, well trained (see below) |
| cdvqa | 56.5 MB | real |
| optical_sar fusion | 30.0 MB | real file — but see Q3 |
| dofa · general_rs_vlm · remoteclip · bigearthnet | 447 MB · 1.54 GB · 605 MB · 94.5 MB | real |

**Test suite went from 104 passed / 7 failed to 117 passed / 0 failed.** Thank you — that unblocked
a lot.

---

## Q1. ChangeFormer: where did the architecture code come from? ⚠️ blocking

**Your checkpoint is good.** It carries its own training metadata:

```
epoch 10 | precision 0.857  recall 0.776  f1 0.814  IoU 0.687
model_class: ChangeFormerV6   model_module: models.ChangeFormer   params: 41,026,674
```

**Our pipeline scores IoU 0.0306 on the real LEVIR-CD test split.** That is 22× worse than what your
own checkpoint reports. So the weights are fine and our inference is wrong.

It is **not** the preprocessing — I swept every candidate (ImageNet vs `[-1,1]` vs plain `[0,1]`, at
256 and 512, across all thresholds). Everything lands at IoU 0.066–0.071 and predicts 62–80% of the
scene as changed when ground truth is 7.2%.

Three measurements that pin it down:

- **AUC = 0.4801** across 2.6M pixels — below chance. The output has no signal in it at all.
- Best IoU across *every* threshold 0.05–0.95 is **0.0653**. Nothing to tune.
- **Feed the same image as both T1 and T2 → 61.61% flagged as "changed."** A real pair gives 62.13%.
  The model cannot tell an image from itself.

The cause is almost certainly that `backend/app/ml/adapters/changeformer/network.py` is a
**reimplementation** of ChangeFormerV6 written in this repo. All 373 parameter names match, so
`load_state_dict(strict=True)` succeeds — but matching names is not the same as matching
computation. Your checkpoint says `model_module: models.ChangeFormer`, i.e. the upstream
`wgcban/ChangeFormer` module, which is not what we run.

**What I need:**

1. **Which code did you train with?** The upstream `wgcban/ChangeFormer` repo, or the
   `network.py` in ours? If upstream — can you send or link the exact `models/ChangeFormer.py` you
   used? That single file resolves this.
2. **Did you ever run inference through *our* adapter and check it against ground truth?** Or was
   the 0.687 measured inside your training script? If the latter, that fully explains how this
   survived — the two paths were never compared.
3. Same question for **CDVQA**: was the 69.50% OA measured through
   `backend/app/ml/adapters/cdvqa/`, or in your training notebook? I'll verify it next and want to
   know which number I'm reproducing.

**Nothing is broken on your side.** The training worked. The gap is between your training code and
the repo's inference code, and it means change detection has never actually worked in the app.

---

## Q2. The 164 MB vs 492 MB confusion is resolved — docs need correcting

Both numbers were right about different things, and both docs are wrong about the parameter count:

- weights alone = **41.0M params × 4 bytes = 164 MB** ← what `SATQUERY_AI_MODEL_DATA_SETUP.md` cites
- the file is **492.6 MB** because it also contains the Adam optimiser state (exactly 3.00×)
- both docs claim **"~13.5 Million parameters"** — the real figure is **41,026,674**

Worth fixing before anyone quotes 13.5M to a judge. Also: the file being a full training checkpoint
rather than weights-only is *useful* — that's where the metadata came from — so please keep saving
them that way.

---

## Q3. Was `satquery_fusion.pth` ever trained? — still open

The file is real (30.0 MB, consistent with the architecture's ~7.3M params). But size cannot tell me
whether the weights are trained or random, and `docs/SATQUERY_AI_MODEL_DATA_SETUP.md` §F still says
to create it like this:

```python
net = CrossAttentionFusionNet()
torch.save(net.state_dict(), 'checkpoints/optical_sar/satquery_fusion.pth')
```

That's an untrained network. It also references `scripts/train_optical_sar_fusion.py`, which doesn't
exist in the repo.

**Just tell me straight — was it trained, and on what?** No blame either way. If it was, send the
training script and I'll verify it like ChangeFormer. If it wasn't, we need to decide between
training it on BigEarthNet, replacing it with an honest documented rule-based analysis, or disabling
the capability. Any of those is defensible. Reporting random-weight land-cover classes as findings
is not, and optical–SAR is one of the six mandatory SIH requirements.

Unlike ChangeFormer, this one **cannot be settled by measurement** — there's no ground truth to test
against — so your answer is the only way to know.

---

## Q4. VRSBench grounding numbers — still open

The master doc reports V1 mIoU 0.1832 / V2 0.2371 / V3 0.2238 as VRSBench results. The fixture those
came from (`datasets/samples/vrsbench_sample_records.json`) has **2 records, both pointing at
`real_image_b`** — a LEVIR-CD crop, not a VRSBench image. One question is copied verbatim from real
VRSBench (where it belongs to a different image with a different box); the other exists nowhere in
the 16,159-record official split and reuses the first one's box.

I've since run the real thing: **mean IoU 0.3532, R@0.5 0.398 over 299 records** of the official
referring split. Those numbers are in `project/handoff/ppt-results.md` and should replace the old
ones everywhere.

**Was there ever a run against the real split?** If yes, send the output JSON. If no, just say so —
I'll assume the fixture was a smoke test that drifted into the docs as "results", which is an easy
thing to happen and worth catching before a judge does.

---

## Q5. Things I changed that you should know about

- **Supabase pooler fix** — we both found this independently. Yours applies `connect_args`
  unconditionally; mine only when the URL is a transaction pooler (`:6543`/pgbouncer), because the
  same host on `:5432` is session mode and handles prepared statements fine. Merged, kept the
  conditional one.
- **`requirements.txt` is missing two packages the code imports**: `aiosqlite` (the whole test suite
  needs it) and `sam2`. Also everything is unpinned — a clean install now pulls `transformers 5.16.1`,
  a major version the adapters predate. If you have a working `pip freeze`, send it and I'll pin from it.
- **`scripts/setup_checkpoints.py` is actively dangerous** — it writes 1.5 KB placeholder dicts to
  every checkpoint path. Because `is_available()` is a bare file-existence check, that makes
  `/api/models` report all 9 models as configured while `load_model()` fails on 373 missing tensors.
  I've added `scripts/verify_checkpoints.py`, which creates nothing and detects placeholders by
  loading the file. Suggest we delete `setup_checkpoints.py`.
- **Restructure** on branch `refactor/s0-remove-dead-layers`: dead planner/router/workflow layers
  removed, `routes.py` split by domain, `models/` → `ml/adapters/<model>/`, tests tiered into
  unit/integration/models, tools now self-register via a decorator. All behaviour-preserving and
  verified at each step.
- **Heads up:** commit `f0a8c7b` on `main` deleted the entire `frontend/` directory — all 13
  components, 4,941 deletions. If that wasn't intended, someone should know.
