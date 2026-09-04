# Phases — Development Plan

Ordered by **what fails the evaluation first**, not by what is most interesting to build.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

---

## Reality check

The platform is **broad and largely built** — orchestration, grounding, change detection, change-VQA,
visual analytics, video, evidence, persistence, API, UI. What is missing is not features. It is
**the two mandatory requirements that are currently faked or absent**, and **measurement**.

A judge asking three questions — *"where is the remote-sensing adaptation?"*, *"how was the fusion
model trained?"*, *"what's your VRSBench number?"* — currently gets three bad answers. Phases P0–P2
exist to change that. Everything else is secondary.

---

## P0 · Ground truth & environment (blocking everything)
**Goal:** be able to run the thing and trust what the docs say.

- [ ] Set up local env: venv, `pip install -r backend/requirements.txt`, Postgres via docker-compose
- [ ] Fetch all checkpoints per `docs/SATQUERY_AI_MODEL_DATA_SETUP.md` into `checkpoints/`
- [ ] Run the full suite: `pytest -v`. Record the **actual** pass/fail count (docs claim 104; there
      are 120 test functions — reconcile)
- [ ] Run every `scripts/smoke_test_*.py` and record which models genuinely execute
- [ ] Produce an honest capability matrix: per model — checkpoint present? loads? forward pass? measured metric?
- [ ] Reconcile `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md` against the code (D-100): GeoChat wiring,
      `temporal_vqa.py` vs `temporal_change.py`, checkpoint sizes, test counts
- [ ] Fix config inconsistencies (D-107): SAM2 base-plus vs hiera-small; DOFA base vs large

**Exit:** a table of what actually works on real hardware, and docs that don't contradict the source.

---

## P1 · Close the two mandatory-requirement blockers
**Goal:** stop failing requirement #1 and requirement #5.

### P1a · Remote-sensing adaptation (D-101) — **highest priority in the project**
- [ ] Decide the approach (quiz-gated; see `rules.md` §6). Recommendation: LoRA fine-tune the BLIP
      VQA head on RSVQA + BigEarthNet-derived Q/A for the deadline
- [ ] Build the adaptation dataset (BigEarthNet S1+S2 with label→question templating; RSVQA train split)
- [ ] Write `training/vlm/` mirroring the existing `training/vqa/` layout
- [ ] Train, checkpoint to `checkpoints/rs_vlm_adapted/`, wire into `GeneralRSVLMAdapter`
- [ ] **Measure adapted vs base on RSVQA test** — this delta is the paper's headline adaptation result
- [ ] Update `configs/models.yaml`, model dossier, and the capability description

### P1b · Optical-SAR cross-modal analysis (D-102) — **currently random weights**
- [ ] Decide: train on BigEarthNet · replace with documented deterministic analysis · or disable
- [ ] If training: write the missing `scripts/train_optical_sar_fusion.py`, train on BigEarthNet
      S1+S2 pairs (19-class multi-label), report real accuracy
- [ ] If deterministic: implement explicit SAR-backscatter + NDWI/NDBI agreement analysis, tag
      `HEURISTIC_ANALYSIS`, remove the fake class probabilities
- [ ] Fix `fusion.py` `get_model` → `get_adapter` (D-103)
- [ ] **Remove the `torch.randn` feature fallback entirely** — raise instead
- [ ] Wire the orphaned `bigearthnet` adapter into the optical-SAR capability (D-106)

**Exit:** both mandatory requirements are satisfied by something we can explain and defend.

---

## P2 · Measurement & benchmarks
**Goal:** every number we say out loud has a results file behind it.

- [ ] **V4 grounding IoU on VRSBench** — currently unmeasured while being the production default (D-013)
- [ ] Extend `scripts/evaluate_grounding_vrsbench.py` to a full prescribed test split, not a sample
- [ ] Build the **RSVQA** evaluation harness (does not exist)
- [ ] Build the **VRSBench captioning** evaluation harness (does not exist)
- [ ] Re-verify CDVQA on the official test split; confirm OA 69.50 / AA 60.36 reproduces
- [ ] **Router accuracy experiment** — hand-label ~200 queries across the five task types, measure
      classification accuracy and failure modes. *This is the core evidence for the paper's claim.*
- [ ] Baseline comparison: monolithic VLM vs our routed pipeline on the same queries
- [ ] Latency + memory profile per capability, CPU and GPU
- [ ] Write everything to `results/evaluations/` as JSON — no numbers live only in a chat log

**Exit:** a results directory that can be dropped into a paper's tables section.

---

## P3 · Routing completeness & robustness
- [ ] Add DAG branches + tools for `multispectral_analysis` and `sar_analysis` (D-104):
      `compute_spectral_indices`, `render_composites`, `render_sar_polarization`
- [ ] Map both to real `TaskType`s in `to_legacy_workflow_plan`
- [ ] Validate `capability.required_tools` at registry construction; fail loudly at boot (D-105)
- [ ] Router robustness: paraphrases, Indian-English phrasing, multi-intent queries, typos
- [ ] Handle the ambiguity path end-to-end — surface `suggested_clarification` in the UI
- [ ] Decide whether to actually execute DAG stages concurrently, or drop the parallelism claim (D-003)

---

## P4 · ISRO/SAC evaluation-set readiness
**Goal:** survive Cartosat-2S + RISAT, which we have never tested against.

- [ ] Ingest genuine multi-band GeoTIFF (not PNG) end-to-end: 12/16-bit, >3 bands, real CRS
- [ ] Verify co-registration checks against genuinely georeferenced pairs
- [ ] RISAT SAR specifics: polarisation tag conventions, calibration, speckle
- [ ] Cartosat-2S: panchromatic + multispectral resolutions, radiometry
- [ ] Confirm outputs are emitted in the exact formats the benchmarks expect (box coords, mask encoding, answer vocabulary)
- [ ] Domain-shift honesty check: measure degradation vs the tuning datasets and report it

---

## P5 · Hardening & delivery
- [ ] Path traversal, MIME + magic-byte validation, upload size caps — audit, don't assume
- [ ] Rate limiting / concurrent job caps
- [ ] `results/` retention and cleanup (nothing exists today)
- [ ] `docker-compose up` from a clean clone, documented and actually tested
- [ ] Demo script: five queries covering all five mandatory capabilities
- [ ] Downloadable PDF report polish — it is explicitly listed as an expected deliverable
- [ ] Frontend integration checkpoint with the other half of the team

---

## P6 · Conference paper
- [ ] Fix the framing: the contribution is **deterministic capability routing with pre-execution
      dependency verification and provenance-linked evidence**, not "we used five models"
- [ ] Related work: GeoChat, RSGPT, EarthGPT, LHRS-Bot, agentic-VLM systems
- [ ] Tables from P2; ablations: V1–V4, adapted vs base VLM, router on/off
- [ ] Honest limitations section: heuristic scoring, sequential DAG, best-effort persistence, domain shift
- [ ] Target venue + deadline — **decide early**, it changes how much of P2 is mandatory

---

## Parallelisation between the two of us

| natsu | Ayushman |
|---|---|
| P0 environment + capability matrix | P0 doc/config reconciliation |
| P1a RS adaptation (the blocker) | P1b optical-SAR decision + fix |
| P2 router accuracy + baseline | P2 benchmark harnesses (RSVQA, VRSBench) |
| P3 routing completeness | P4 GeoTIFF / SAR ingestion realism |

Both: keep `decisions.md`, `flow.md` and `memory.md` current. Neither merges an orchestration
change without the other reviewing it.
