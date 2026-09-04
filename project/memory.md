# Memory — Live Project State

**Updated:** 2026-09-04 (Session 2)
**Read this first at the start of every session. Update it at the end of every session.**

---

## 1. Where we are

| | |
|---|---|
| Local path | `/home/natsu/dev/isro` |
| Remote | `github.com/KushwahaSujal/SATQuery-AI` (branch `main`) |
| HEAD | `360857f` — "Add comprehensive AI/ML model technical documentation dossiers…" |
| Commits so far | 2, both by KushwahaSujal (2026-09-03, 2026-09-04) |
| Size | 348 files · 223 Python modules · ~29k LOC (~14.4k in `backend/app`) |
| Our scope | **Backend** (natsu + Ayushman). Frontend/deck owned by the rest of the team. |
| Deadline | SIH 2026 (TBD) → then conference paper |

**Local environment is NOT set up.** No `.venv`, `torch` is not installed, `checkpoints/` does not
exist (gitignored — must be fetched per `docs/SATQUERY_AI_MODEL_DATA_SETUP.md`). Nothing has been
executed on this machine yet; every finding below comes from reading the source.

---

## 1b. Restructure progress (see [restructure.md](restructure.md))

| Stage | State | Result |
|---|---|---|
| **S0** dead-code removal | ✅ done | `agent/` 7→5 modules, `workflows/` 8→3; 493 deletions, 0 behaviour change |
| **Docs off root** | ✅ done | 13 root `.md` files → 1 (`README.md`); rest under `project/` |
| **S1** split `routes.py` | ✅ done | 1246 lines → 6 domain modules under `api/v1/endpoints/` + shim; all 27 routes intact |
| **S2** `models/` → `ml/` | ✅ done | per-model packages; `changeformer.py` 722 → `network.py` 418 + `adapter.py` 329; 45 import sites rewritten |
| **S3** decorator tool registry + per-capability files | ⬜ next | fixes D-104/D-105 structurally |
| **S4** test tiering (`unit`/`integration`/`smoke`) | ⬜ | no markers today; can't run "fast tests only" |
| **S5/S6** frontend | ⬜ blocked | **frontend was deleted upstream** in `f0a8c7b` — see below |

Verification after each stage: **104 passed / 7 failed / 1 skipped**, failure list unchanged
(all 7 are missing checkpoints). The improvement from the 100/11 baseline came from installing
`sam2`, not from any refactor.

⚠️ **Upstream deleted the entire `frontend/` directory** in commit `f0a8c7b` (4,941 deletions,
all 13 components). Merged in. If unintended, the team needs to know before rebuilding.

## 2. Currently working on

**`phases.md` P0 — baseline**, then `restructure.md` **S0** (dead-code removal). Approved
sequencing from the author: P0 → S0 → P1 blockers → S1–S4.

Environment progress this session:
- Machine has **Python 3.14.4 only**; project needs 3.10/3.11 → built **3.11.16 via pyenv** ✅
- `.venv` created from 3.11.16 ✅
- `pip install -r backend/requirements.txt` — **in progress** (CUDA torch, large download)
- GPU present: **RTX 3070, 8 GB VRAM** (note: too small for GeoChat-7B's ~14 GB — reinforces D-101)
- `checkpoints/` still absent; must be fetched before any model smoke test

### ✅ VERIFIED BASELINE — 2026-09-04, commit `360857f` + D-113 fix

```
108 passed · 11 failed · 1 skipped · 120 total · 111.82s
Python 3.11.16 · torch 2.14.0+cu130 (CUDA available, RTX 3070) · transformers 5.16.1 · SQLAlchemy 2.0.52
```

**All 11 failures are missing model artifacts or undeclared dependencies — zero logic failures.**

| Failing test | Cause |
|---|---|
| `test_changeformer_smoke.py::test_changeformer_smoke_real_images` | missing `checkpoints/changeformer/satquery_changeformer_best.pt` |
| `test_dofa.py` ×2 | missing `checkpoints/dofa/` |
| `test_vlm_and_fusion.py` ×4 | missing `checkpoints/general_rs_vlm`, `checkpoints/optical_sar/satquery_fusion.pth` |
| `test_model_registry.py` ×2 | asserts adapter availability → depends on the above |
| `test_sam2.py` ×2 | **`ModuleNotFoundError: No module named 'sam2'`** — undeclared dependency |

**Nothing in the orchestration, agent, workflow, API, DB, evidence or visualization layers fails.**
The docs' "104/104 passing" claim is wrong on both numbers: there are 120 tests, and 108 pass on a
clean machine with no checkpoints.

**Next action:** execute the S0 manifest in `restructure.md` §4b. Expected after S0:
**112 total · 100 passed · 11 failed · 1 skipped** (the 8 removed tests all currently pass, and none
of them are in the failing set).

---

## 3. Phase progress

| Phase | Status | Note |
|---|---|---|
| P0 Ground truth & environment | `[ ]` | **next up** — nothing runs locally yet |
| P1a RS adaptation | `[!]` | blocker; approach not yet decided (D-101) |
| P1b Optical-SAR fusion | `[!]` | blocker; currently random weights (D-102) |
| P2 Measurement & benchmarks | `[ ]` | V4 IoU, RSVQA, VRSBench captioning all unmeasured |
| P3 Routing completeness | `[ ]` | two capabilities route to a dead-end DAG |
| P4 ISRO/SAC readiness | `[ ]` | Cartosat/RISAT never tested |
| P5 Hardening & delivery | `[ ]` | |
| P6 Paper | `[ ]` | venue not chosen |

---

## 4. What is built vs what is missing

### Built and verified present in source
Agentic orchestration (intent classifier → capability matcher → DAG planner → dependency checker →
resource manager → whitelist validator → tool executor) · 13 capabilities · 14 tools · 9 model
adapters · Grounding DINO → V1–V4 reasoner → SAM 2.1 pipeline · ChangeFormerV6 · CDVQA (19 classes)
· evidence engine (boxes/masks/polygons/area/GeoJSON/PDF) · visual analytics (composites, NDVI/NDWI/
NDBI, SAR dual-pol, heatmaps, pixel inspector, 50-bin histogram, exports) · streaming video +
heuristic flagger · Postgres (10 tables) + Alembic · ~25 REST endpoints · Next.js 14 UI (11
components) · 38 test files / 120 test functions · Docker compose.

### Missing, broken, or dishonest — ranked

1. **[BLOCKER] No remote-sensing adaptation.** `general_rs_vlm` = `Salesforce/blip-vqa-base`,
   a generic VQA model. The problem statement explicitly disqualifies this. (`decisions.md` D-101)
2. **[BLOCKER] Optical-SAR fusion head is randomly initialised.** The setup doc creates the
   checkpoint by saving an untrained `CrossAttentionFusionNet`; `scripts/train_optical_sar_fusion.py`
   is referenced but absent. Its 19-class output, `surface_roughness` and `builtup_index` are noise.
   (D-102)
3. **[BUG] `fusion.py:141,155` call `model_registry.get_model()`** — no such method (`get_adapter`).
   Lines 146/160 fall back to `torch.randn(1,768)` — fabricated features. (D-103)
4. **[GAP] `multispectral_analysis` / `sar_analysis` route to a dead-end DAG** — no branch in
   `build_dag_for_capability`, unmapped in `to_legacy_workflow_plan`. "Compute NDVI" silently
   returns nothing. (D-104)
5. **[GAP] Capability `required_tools` are never validated** — several named tools don't exist in
   `TOOL_REGISTRY`; `DependencyChecker` only checks DAG nodes. (D-105)
6. **[GAP] `bigearthnet` adapter is orphaned** — the *prescribed adaptation dataset* is unused. (D-106)
7. **[GAP] V4 has no measured IoU** despite being the production default. V2 is the best measured
   (mIoU 0.2371, R@0.5 0.26) — and these numbers are weak overall. (D-013)
8. **[GAP] No RSVQA and no VRSBench-captioning evaluation harness.**
9. **[DOC] Master documentation contradicts the code** — describes `models/geochat.py` (absent),
   `temporal_vqa.py` (actually `temporal_change.py`), a 492 MB ChangeFormer (setup doc says 164 MB),
   "104/104 tests" (120 test functions exist). (D-100)
10. **[CONFIG] SAM2 yaml says hiera-base-plus, model_id says hiera-small; DOFA yaml says ViT_base,
    registry metadata says ViT_large.** (D-107)
11. `third_party/GeoChat/` is vendored but wired into nothing.
12. DAG parallel stages are computed but execution is sequential.
13. No `results/` retention or cleanup job.

---

## 4b. Build reality — the honest scorecard

Two different questions get confused constantly. Separate them:

### Is the software built? Largely yes.

| Subsystem | State | Evidence |
|---|---|---|
| Agentic orchestration (intent → capability → DAG → dependency check → execute) | **Working** | tests pass, no checkpoints needed |
| Evidence engine (boxes, masks, polygons, area, GeoJSON, PDF) | **Working** | tests pass |
| Visual analytics (composites, NDVI/NDWI/NDBI, SAR, heatmaps, inspector, exports) | **Working** | 18 tests pass |
| Video pipeline (decode, sample, flag) | **Working** | 12 tests pass |
| REST API (~25 endpoints) + PostgreSQL (10 tables) | **Working** | tests pass; Supabase verified after D-113 |
| Next.js UI (11 components) | Built, unverified here | not run this session |

**108 of 120 tests pass on a clean machine with zero model weights, and not one failure is a logic
failure.** The plumbing is real and it is decent.

### Does it satisfy the problem statement? Roughly half.

| # | Mandatory requirement | Status | Why |
|---|---|---|---|
| 1 | Remote-sensing adaptation | ❌ **NOT MET** | `general_rs_vlm` is `Salesforce/blip-vqa-base` — a generic VLM. The PS explicitly disqualifies this. |
| 2 | Single-image VQA | ⚠️ Runs, doesn't count | Works mechanically, but on the unadapted model from #1 |
| 3 | One more single-image task (grounding) | ✅ Code complete | Best measured mIoU 0.2371 / R@0.5 0.26 — weak, and V4 (the production default) is **unmeasured** |
| 4 | Bi-temporal change analysis | ✅ Code complete | ChangeFormer + CDVQA; checkpoints not verified on this machine |
| 5 | Cross-modal optical–SAR | ❌ **NOT MET** | Fusion head ships **randomly initialised**; outputs are noise |
| 6 | Agentic orchestration | ✅ **Strongest part** | Genuinely the differentiator, and it works |

**Realistic score: 3 of 6 met, 1 hollow, 2 hard blockers.**

### The one-line version

> The engineering is ~85% done. The *machine learning* — the part actually being graded — is closer
> to 40%. Two capabilities are presented as working while being a generic model and a random-weight
> network respectively. Fixing those two matters more than every other item on the roadmap combined.

Nothing above is new information; it is `prd.md` §4.2 and §4 of this file consolidated into one
table because the split kept causing the question "so how much is actually built?"

---

## 5. Verification record

Lives in **[`QNA.md`](QNA.md)** — written question-and-answer entries per `rules.md` §6, replacing
the old interactive quiz. A major change does not merge while its entry is *Pending review*.

| Entry | Change | Status |
|---|---|---|
| Q-001 | S0 — removal of dead planner/router/workflow-class layers | Pending review |
| Q-002 | D-113 — asyncpg prepared-statement cache behind Supabase's pooler | Pending review |

---

## 6. Open questions for the team

1. **D-101** — which RS-adaptation route? (LoRA-BLIP on RSVQA/BigEarthNet · RemoteCLIP-conditioned ·
   revive GeoChat-7B · train our own head). Deadline pressure favours LoRA-BLIP; the paper favours
   owning the adaptation.
2. **D-102** — train the fusion head, replace it with an honest deterministic analysis, or disable
   the capability? Shipping random weights is not an option.
3. Who owns reconciling `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md`? It is the team's public artifact
   and it currently overstates the build.
4. Conference venue and deadline — this determines how much of P2 is mandatory.
5. Is there GPU access for P1 training, and how much VRAM?

---

## 7. Session history

### Session 1 — 2026-09-04 · documentation bootstrap
Cloned the repo into an empty `/home/natsu/dev/isro`. Surveyed the full codebase (file tree, LOC,
tests, configs, frontend). Read the orchestration layer, agent controller, tool registry, model
registry, base adapter, general RS-VLM, fusion model, rendering, config, `configs/models.yaml`, the
model/data setup doc, and the frontend theme files.

Created at repo root: `prd.md`, `architecture.md`, `flow.md`, `decisions.md`, `rules.md`,
`phases.md`, `design.md`, `memory.md`.

**No application code was changed.** No tests were run (dependencies absent). Every claim in these
documents is sourced from reading the code; where the master documentation and the source disagree,
the documents follow the source and flag the divergence.

**Headline finding:** the platform is far more built-out than it is *correct*. Two of the six
mandatory requirements — remote-sensing adaptation and optical-SAR analysis — are currently
satisfied by a generic model and a randomly-initialised network respectively. Fixing those two
matters more than any new feature.
