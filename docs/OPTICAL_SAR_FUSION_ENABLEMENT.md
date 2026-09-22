# Enabling Optical-SAR Fusion — current state and the work to fix it

**Status: deliberately disabled. Not a bug, not a deployment gap.**
Written 2026-09-22, after the hosted deployment. For whoever picks this up after the mentor demo.

---

## 0. Read this first

Two things need a decision before any code is written.

1. **`docs/models/OPTICAL_SAR_FUSION.md` says `Current Status: IMPLEMENTED & VERIFIED`.**
   That is false. The checkpoint holds random weights and the adapter refuses to run. If a judge
   reads that dossier and then asks for a demonstration, the contradiction is the thing they will
   remember. Correct that line before the dossier is shown to anyone outside the team.
2. **The home page advertises the capability** (`frontend-v2/src/app/page.tsx:59`, card
   "Optical + SAR Fusion") and it is one of four sample queries (`page.tsx:375`). A mentor can
   click it. Either accept that and prepare the answer in §7, or hide the card until §5 lands.

---

## 1. What happens today

Upload an optical + SAR pair, ask anything, and the job completes with:

```
status : COMPLETED   task: optical_sar_analysis
models : ['dofa', 'satquery_optical_sar_fusion']
answer : Optical-SAR analysis NOT_CONFIGURED: Optical-SAR fusion model is currently
         NOT_CONFIGURED on this deployment. The fusion head weights are uncalibrated
         and no validated fusion method is configured.
errors : []
```

Measured against the deployed backend on 2026-09-22 with
`demo_resources/3_optical_sar/{optical_sentinel2,sentinel1_sar_cband}.png`.

Note the job **succeeds**. It does not error, it refuses. That is the intended behaviour.

### A trap in the health endpoint

`/api/health` reports `satquery_optical_sar_fusion: true`. Availability only checks that the
adapter can be constructed and its weights load — not that they mean anything. So the model counts
toward the "AI Ready · 18/20" pill while refusing every request. Do not use that pill as evidence
the capability works.

---

## 2. Why it refuses — the mechanism

`backend/app/ml/adapters/fusion/adapter.py`

```python
31:  self.is_configured: bool = False          # hard-coded in __init__
64:  if not self.is_configured:                # predict() returns the refusal
```

`is_configured` is assigned `False` once and **nothing anywhere in the repo ever sets it to
`True`**. This is a kill switch, not a runtime capability check. `backend/app/ml/registry.py:82`
(`_probe_is_configured`) reads the same flag so `serving_state` reports the refusal honestly
instead of advertising a model that will not answer.

---

## 3. Why it was switched off

Recorded as **D-102** in `project/decisions.md:438`, "The Optical-SAR fusion head is untrained —
**BLOCKER**". In summary:

- `docs/SATQUERY_AI_MODEL_DATA_SETUP.md` §F creates `checkpoints/optical_sar/satquery_fusion.pth`
  by saving a **freshly constructed** `CrossAttentionFusionNet` — random initialisation.
- It references `scripts/train_optical_sar_fusion.py`, **which does not exist in the repo**
  (verified absent again on 2026-09-22).
- Therefore the 19 land-cover classes, `surface_roughness` and `builtup_index` that
  `run_optical_sar` would report are **noise formatted as findings**.

That directly contradicts the zero-fabrication commitment (D-010), which is the project's main
defensive claim. Returning `NOT_CONFIGURED` was chosen over shipping numbers nobody can justify.

### Checkpoint facts (measured)

| Property | Value |
|---|---|
| Path | `checkpoints/optical_sar/satquery_fusion.pth` |
| Size | 29,962,729 bytes (~29 MB) |
| Tensors | 30 (`opt_proj.weight`, `opt_proj.bias`, `sar_proj.weight`, …) |
| Architecture | `CrossAttentionFusionNet(embed_dim=768, num_heads=8, num_classes=19)` |
| Provenance | Random init, per D-102. Never trained. |

The file loads cleanly with `strict=True`. **A checkpoint that loads is not a checkpoint that
works** — this is the single most important thing to understand about this task.

---

## 4. The three options

D-102 laid these out. They are still the options.

| # | Option | Effort | Defensible to a judge? |
|---|---|---|---|
| A | Deterministic heuristic, labelled `HEURISTIC_ANALYSIS` | ~2–4 days | Yes, if labelled honestly |
| B | Train the head on co-registered S1+S2 | ~2–4 weeks | Yes, strongest |
| C | Leave as `NOT_CONFIGURED` | 0 | Yes — refusing is defensible |

**Recommended: A now, B if the timeline allows.** A gets a working capability with numbers that can
be explained from first principles. B is the real answer but is gated on data you do not have yet
(§6).

Do **not** consider a fourth option of flipping `is_configured = True` against the current
checkpoint. That ships random weights as findings and is the exact failure D-102 exists to prevent.

---

## 5. Option A — deterministic heuristic (recommended first step)

Replace the learned head with an explicit, documented computation. No training, no new data, and
every number traceable to an equation.

### What to compute

From the SAR image (Sentinel-1 dual-pol VV/VH, dB):
- **Surface roughness proxy** — VV/VH ratio and local variance. Smooth water is very low
  backscatter; urban is high with strong VV.
- **Built-up indicator** — high VV with high local variance, the classic double-bounce signature.

From the optical image (Sentinel-2):
- **NDWI** `(G − NIR)/(G + NIR)` for water.
- **NDBI** `(SWIR − NIR)/(SWIR + NIR)` for built-up.

Then report **agreement between the two sensors**, which is the honest product of a fusion step:
where optical and SAR agree on water/built-up, and where they disagree (cloud over optical, layover
or shadow in SAR). Disagreement is a finding, not a failure.

`backend/app/visualization/indices.py` already has index machinery — reuse it rather than writing
new NDWI/NDBI code.

### Steps

1. Add a `HEURISTIC_ANALYSIS` status alongside `NOT_CONFIGURED` in the fusion `ModelResult`, so the
   label travels with the answer into the UI and the report.
2. Implement the computation in a new module (suggested `backend/app/ml/adapters/fusion/heuristic.py`).
   Keep it pure: arrays in, numbers out, no model registry access.
3. In `adapter.py:predict`, branch on config: heuristic path when enabled, `NOT_CONFIGURED` when not.
   Keep the refusal branch — it is the fallback when inputs are not a valid pair.
4. Gate it on an explicit setting (`SATQUERY_FUSION_MODE=heuristic|off`), defaulting to `off`, so
   turning it on is a deliberate act that shows up in a diff.
5. Make the answer writer state the method in words: which thresholds, which bands, what the
   agreement percentage means. If it cannot be explained in one sentence, it is not ready.
6. Write the thresholds and their sources into `docs/models/OPTICAL_SAR_FUSION.md`, and correct the
   status line there (§0).

### Acceptance

- Two known scenes with an obvious answer (a water body, a dense urban block) return the expected
  class with the agreement figure.
- The answer names the method and cites the thresholds.
- Nothing in the output is presented as a learned prediction.

---

## 6. Option B — train the head properly

### Data: not currently on disk

`checkpoints/bigearthnet/` holds a Hugging Face classifier (`config.json`, `model.safetensors`) —
**not** co-registered S1+S2 training pairs. Checked `datasets/raw` (303 GB) on 2026-09-22:

| Present | Relevant? |
|---|---|
| `lae_1m` 88G, `isprs_potsdam_vaihingen` 43G, `spacenet3_roads` 35G, `inria_aerial` 26G, `spacenet7_multitemporal` 23G, `cloud95_landsat8` 18G, `openearthmap` 12G, `massachusetts_roads` 9.9G | No — all optical |
| `sen1floods11` 1.9G | **The only SAR data in the repo.** S1 + hand-labelled flood masks. |

BigEarthNet-MM (the prescribed set: co-registered S1 + S2, 19 Corine classes, matching the
network's `num_classes=19`) is **not downloaded**. That is the first task, and it is large — budget
disk and time before writing any training code. Check `datasets/manifests/` for whether an ingest
manifest already exists.

`sen1floods11` is not a substitute: it is flood/water binary labels, not 19-class land cover. It
could support a narrower, genuinely defensible capability ("SAR-based flood/water extent") if
BigEarthNet proves too heavy — worth considering as a scope cut rather than a compromise.

### Steps

1. Ingest BigEarthNet-MM; record counts and the split in `datasets/manifests/`.
2. Write `scripts/train_optical_sar_fusion.py` — the file D-102 says is referenced but missing.
   Follow the existing trainer conventions in `training/segmentation/` so the serving adapter can
   import from it the way the segmenters do.
3. Extract 768-d DOFA embeddings for both modalities; confirm the encoder is frozen and record
   which DOFA checkpoint produced them.
4. Train, then **validate on a held-out split and write the measured metrics into the dossier.**
   Per-class accuracy, not just a headline number. Unflattering numbers go in as measured.
5. Replace the checkpoint, set `is_configured` from a real check, delete the kill switch.
6. File a QNA entry that supersedes D-102 in both directions.

### Acceptance

- Held-out metrics exist, are written down, and were produced by a script in the repo.
- Somebody who did not train it can re-run the validation from the repo and get the same numbers.
- "How was this trained?" has a one-paragraph answer with a dataset, a split and a date.

---

## 7. What to say at the demo, before this is fixed

If the mentor clicks Optical + SAR Fusion and gets the refusal, say this:

> The fusion head was never trained — the checkpoint in the repo is a random initialisation. We
> found that during review and chose to have the model refuse rather than emit 19 class
> probabilities that are noise. The capability is wired end to end; what is missing is calibrated
> weights and the training data, which is BigEarthNet-MM.

That is a stronger position than a working-looking demo built on random weights, **provided you say
it first**. Being caught is what costs marks; disclosing is what earns them.

---

## 8. Deploying after the fix

The backend runs on Modal, the frontend on Vercel. Neither needs changing for this work beyond the
normal deploy.

```bash
# backend — picks up the code and configs/ from the working tree
.venv/bin/modal deploy deploy/modal_app.py

# if Option B replaces the checkpoint, push it to the volume first
.venv/bin/modal volume put satquery-models \
  checkpoints/optical_sar/satquery_fusion.pth \
  checkpoints/optical_sar/satquery_fusion.pth
.venv/bin/modal deploy deploy/modal_app.py    # new containers pick up the new volume snapshot
```

**A running container holds a stale volume snapshot.** Uploading weights alone changes nothing
until the containers cycle — redeploy after any `volume put`, or you will spend an hour debugging a
model that is already fixed. (Learned the hard way; see Q-057.)

Frontend, only if the UI changes:

```bash
cd frontend-v2 && vercel deploy --prod
```

Verify on the deployed stack, not localhost:

```bash
curl -s "$MODAL_URL/api/health" | python3 -c "import json,sys; \
  print(json.load(sys.stdin)['models_available']['satquery_optical_sar_fusion'])"
# then run a real pair through /api/upload + /api/analyze and read the answer
```

---

## 9. Related open items

These sit next to this work and are worth reading before starting.

- **D-104** — `sar_analysis` and `multispectral_analysis` are matched by `CapabilityMatcher` but
  have no branch in `build_dag_for_capability()`, so they fall back to a trivial
  `inspect_raster → generate_report` plan. The startup log lists them under "Capabilities with no
  DAG branch … produce no real output". Fusion is routed through `optical_sar_analysis`, which
  *does* have a workflow (`workflow_optical_sar`), so it is unaffected — but the neighbouring SAR
  capability is not.
- **D-105** — capability `required_tools` are never verified against `TOOL_REGISTRY`, so a
  capability can declare tools that do not exist and nothing complains at boot.
- **D-103** — previously reported `get_model`/`torch.randn` fabricated features in
  `backend/app/evidence/fusion.py`. Re-checked 2026-09-22: neither call is present; the file is now
  an evidence packager only. Appears resolved, but confirm before relying on it.

---

## 10. Touchpoints

| File | Line | What |
|---|---|---|
| `backend/app/ml/adapters/fusion/adapter.py` | 31 | `is_configured = False` — the kill switch |
| `backend/app/ml/adapters/fusion/adapter.py` | 64–82 | the `NOT_CONFIGURED` refusal |
| `backend/app/ml/adapters/fusion/network.py` | 45 | `CrossAttentionFusionNet` signature |
| `backend/app/ml/registry.py` | 82 | `_probe_is_configured` |
| `configs/models.yaml` | 136 | model entry, `checkpoint_path` |
| `backend/app/orchestration/capability_registry.py` | 75–86 | capability, required models and tools |
| `project/decisions.md` | 438 | D-102, the blocker |
| `docs/models/OPTICAL_SAR_FUSION.md` | 14 | the status line that needs correcting |
| `frontend-v2/src/app/page.tsx` | 59, 375 | where the UI advertises it |
