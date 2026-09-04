# Flow — Codebase Execution Map

Tracks **where execution starts, what calls what, and what the AI touched each session.**
Update the "Session log" at the bottom every time code changes.

---

## 1. Entry points

| # | Entry point | File | Triggered by |
|---|---|---|---|
| 1 | ASGI app object | `backend/app/main.py:32` (`app = FastAPI(...)`) | `uvicorn backend.app.main:app` |
| 2 | Startup hook | `main.py:22` `lifespan()` → `init_db_engine()` | process boot |
| 3 | Shutdown hook | `lifespan()` → `dispose_db_engine()` | process stop |
| 4 | Config singleton | `backend/app/config.py:251` `settings = Config()` | **import time**, before anything else |
| 5 | Model registry singleton | `backend/app/models/registry.py:324` | import of `models.registry` |
| 6 | Capability registry singleton | `orchestration/capability_registry.py:207` | import — registers 13 capabilities |
| 7 | Agent controller singleton | `agent/controller.py:315` | import |
| 8 | Frontend root | `frontend/src/app/page.tsx` | browser at `:3000` |
| 9 | CLI/dev run | `main.py:183` `if __name__ == "__main__"` | `python -m backend.app.main` |

**Import-time side effects to be aware of:** `config.py` reads all three YAMLs and validates the
video scoring weights sum to 1.0 (raises at import if not). `capability_registry.py` builds all 13
capabilities. Neither loads model weights.

---

## 2. Primary call chain — `POST /api/analyze`

```
routes.analyze_query                                    api/routes.py:229
│
├─ AgentState(...)                                      agent/state.py
└─ agent_controller.run_pipeline(state)                 agent/controller.py:50
   │
   ├─ [1] _safe_db_op → JobRepository.create_or_get_job          db/repositories/job_repository.py
   │
   ├─ [2] AdvancedWorkflowPlanner.plan(state)           orchestration/planner.py:44
   │      ├─ InputAnalyzer.analyze(image_paths)         orchestration/input_analyzer.py
   │      │     └─ RasterInspector.inspect              geo/raster.py
   │      │     └─ ModalityDetector                     geo/modality.py
   │      ├─ IntentClassifier.classify_intent           orchestration/intent_classifier.py:168
   │      │     └─ .extract_entities                    intent_classifier.py:77  (regex facets)
   │      ├─ CapabilityMatcher.match                    orchestration/matcher.py:23
   │      │     └─ capability_registry.get / list_enabled
   │      └─ DependencyGraph.build_dag_for_capability   orchestration/dependency_graph.py:62
   │            └─ .compute_execution_stages            dependency_graph.py:22  (topological)
   │
   ├─ AdvancedWorkflowPlanner.to_legacy_workflow_plan   planner.py:82  (DAG → linear steps)
   │
   ├─ [3] DependencyChecker.verify_plan_dependencies    orchestration/dependency_checker.py:26
   ├─ [4] ResourceManager.verify_resource_availability  orchestration/resource_manager.py
   ├─ [5] PlanValidator.validate_plan                   agent/validator.py
   ├─ [6] orchestration_cache.compute_cache_key / .get  orchestration/cache.py
   │
   ├─ [7] for tool_name in plan.steps:
   │        SafeToolExecutor.execute_tool(name, state)  agent/executor.py
   │           └─ TOOL_REGISTRY[name](state)            agent/registry.py:422
   │
   ├─ [8] OutputQualityValidator.validate_changeformer_output  orchestration/output_validator.py
   ├─ [9] ConfidenceEvaluator.evaluate                  evidence/confidence.py
   │      ConsistencyChecker.check_change_consistency   evidence/consistency.py
   ├─ [10] ProvenanceBuilder.build_provenance_graph     orchestration/provenance.py
   ├─ [11] operational_health.record_workflow_execution orchestration/health.py
   │
   ├─ artifact_manager.save_result_json / save_trace_json   artifacts/manager.py
   └─ _safe_db_op(_persist_final_db_records)
        └─ JobRepository.{update_job_status, save_model_runs,
                          save_execution_steps, save_analysis_result, save_artifacts}
```

---

## 3. Tool fan-out — `TOOL_REGISTRY` (agent/registry.py:422)

| Tool | Calls into | Notes |
|---|---|---|
| `inspect_raster` | `RasterInspector.inspect` | populates `state.metadata` |
| `validate_single_image` | `geo/validation.validate_single_image` | |
| `validate_temporal_pair` | `geo/validation.validate_temporal_pair` | appends alignment warnings |
| `validate_optical_sar_pair` | `geo/validation.validate_optical_sar_pair` | |
| `run_vqa` | `model_registry.get_adapter("general_rs_vlm").predict` | graceful message if NOT_CONFIGURED |
| `run_caption` | same adapter, fixed caption prompt | |
| `run_grounding` | **`workflows/grounding.run_grounding_pipeline`** → `EvidenceFusionEngine.build_grounding_evidence` | the deep path, see §4 |
| `run_segmentation` | `sam2` adapter — **no-op if grounding already produced a mask** | |
| `run_change_detection` | `changeformer` adapter → saves `.npy` prob map, GeoTIFF + PNG masks, overlay, GeoJSON, area stats | heaviest tool |
| `run_change_vqa` | `cdvqa` adapter; **falls back to a ChangeFormer-derived sentence** if CDVQA missing | |
| `run_optical_sar` | `dofa.extract_features` → `fusion.predict` | ⚠ see gaps |
| `calculate_statistics` | `evidence/statistics.calculate_area_statistics` | also synthesises an answer if none |
| `generate_overlay` | `geo/rendering.create_change_overlay` + `save_image` | green for grounding, red for change |
| `generate_report` | `evidence/report.PDFReportGenerator.generate` | ReportLab |

---

## 4. Grounding sub-pipeline — `workflows/grounding.py:63`

```
run_grounding_pipeline(image, query)
├─ _validate_image                              grounding.py:26
├─ GroundingDINOAdapter.predict                 models/grounding_dino.py
│     → candidate boxes [x1,y1,x2,y2] + text-association scores
├─ run_v4_reasoning(...)                        workflows/grounding_reasoner.py:634
│     ├─ parse_v4_query                         :84   → head noun, colour, size, position, relation, ordinal
│     ├─ nms_candidates                         :307
│     ├─ position_score / size_score / color_score / relation_score   :199 :224 :253 :347
│     ├─ detect_reference / detect_reference_heuristic                :505 :424
│     ├─ rank_v4_candidates                     :568  → weighted multi-criteria score
│     └─ ordinal_select                         :388
├─ SAM2Adapter.predict(box prompt)              models/sam2.py
└─ returns {answer, selected_box, segmentation_mask, grounding_score, sam2_score, strategy, trace, evidence}
```

`V1/V2/V3/V4` are **scoring strategies inside this one file**, not four separate networks.

---

## 5. Video path (separate from the DAG)

```
POST /api/video/upload   → routes.upload_video (ext/size validation, saves file, DB row)
POST /api/video/analyze  → routes.analyze_video
     └─ VideoAnalysisWorkflow                    workflows/video_analysis.py:35
          ├─ VideoDecoder.iter_frames            video/decoder.py   (OpenCV streaming, O(1) memory)
          ├─ FrameSampler (coarse 1 fps → refine) video/sampler.py
          ├─ GroundingDINO + V4 per keyframe
          ├─ SAM 2.1 video memory propagation    models/sam2.py + video tracking
          └─ VideoEventFlagger                   video/flagger.py
                score = 0.4·det + 0.3·V4 + 0.2·SAM2 + 0.1·persistence  (weights from configs/app.yaml)
                → temporal clustering → persistence filter → video_flags rows
GET /api/video/{id}/{status,results,events,keyframes,stream}
```

---

## 6. Visual analytics path (on-demand, post-job)

```
GET /api/analysis/{job}/layers            → visualization/registry.py  (discovers valid modes)
GET .../visualizations/{layer}            → composites.py | indices.py | sar.py | heatmaps.py
GET .../visualizations/{layer}/legend     → matplotlib colorbar
POST .../inspect-pixel  {col,row}         → visualization/inspector.py  (affine → lat/lon, DN, indices)
GET .../histogram/{layer}                 → inspector.py  (50 bins + P2/P25/P50/P75/P98)
GET .../export/{layer}?format=png|geotiff|geojson → visualization/exports.py
```

---

## 7. Known dead ends / traps in the flow

1. **`multispectral_analysis` and `sar_analysis`** reach `CapabilityMatcher` but
   `DependencyGraph.build_dag_for_capability` has no branch → silent fallback DAG
   (`inspect_raster → generate_report`). Also unmapped in `to_legacy_workflow_plan` → `TaskType.UNSUPPORTED`.
2. **Capability `required_tools` are never validated.** `DependencyChecker` checks *DAG node* tools
   only. Names like `compute_spectral_indices`, `render_sar_polarization`, `inspect_pixel`,
   `sample_keyframes` appear in capability definitions but do not exist in `TOOL_REGISTRY`.
3. **`fusion.py:141` and `:155` call `model_registry.get_model(...)`** — that method does not exist
   (`get_adapter` does) → `AttributeError` on that branch.
4. **`fusion.py:146,160`** fall back to `torch.randn(1, 768)` when DOFA is unavailable — fabricated
   features feeding a real-looking classification.
5. **`bigearthnet` adapter is orphaned** — registered in `ModelRegistry`, referenced by no capability.
6. **`third_party/GeoChat/` is vendored but unreferenced** by `backend/`. There is no
   `backend/app/models/geochat.py`, despite the master documentation describing one.
7. **DAG parallel stages are computed but not used** — execution is a plain `for` loop over
   `plan.steps`.

---

## 8. Session log — what the AI changed

> Format: date · session summary · files created/modified · verification.

### 2026-09-04 — Session 1 (documentation bootstrap)
- **Changed:** no application code. Read-only survey of the repo.
- **Created:** `prd.md`, `architecture.md`, `flow.md`, `decisions.md`, `rules.md`,
  `phases.md`, `design.md`, `memory.md` at repo root.
- **Actions:** cloned `KushwahaSujal/SATQuery-AI` into `/home/natsu/dev/isro`; mapped
  348 files / 223 Python modules / ~29k LOC; read `main.py`, `agent/controller.py`,
  `agent/registry.py`, `orchestration/{planner,capability_registry,intent_classifier,matcher,dependency_graph,dependency_checker}.py`,
  `models/{registry,base,general_rs_vlm,fusion}.py`, `geo/rendering.py`, `config.py`,
  `configs/models.yaml`, `frontend/{package.json,tailwind.config.js,globals.css,layout.tsx}`,
  `docs/SATQUERY_AI_MODEL_DATA_SETUP.md`.
- **Verification:** none run — `torch` is not installed and `checkpoints/` is absent on this
  machine, so the test suite cannot execute yet. All findings are from source reading.
- **Findings logged:** see `decisions.md` §3 and `memory.md` §4.

### 2026-09-04 — Session 2 (P0 baseline + S0 dead-code removal)
Branch: `refactor/s0-remove-dead-layers` (not committed — awaiting review)

**Environment (P0):** built Python 3.11.16 via pyenv (machine had only 3.14.4); created `.venv`;
installed `backend/requirements.txt` + `aiosqlite`. torch 2.14.0+cu130 with CUDA on an RTX 3070.

**Baseline recorded:** `108 passed · 11 failed · 1 skipped · 120 total`. All 11 failures trace to
missing checkpoints or the undeclared `sam2` package — no logic failures anywhere in the
orchestration, agent, workflow, API, DB, evidence or visualization layers.

**Changed — DB fix (D-113):**
- `backend/app/db/session.py` — added `_is_transaction_pooler()` and pgBouncer-safe
  `connect_args` (`statement_cache_size=0`, `prepared_statement_cache_size=0`).
  Verified against the live Supabase instance through `get_async_engine()`.

**Changed — S0 dead-code removal:**
- Deleted: `agent/router.py`, `agent/planner.py`, `workflows/base.py`, `workflows/single_vqa.py`,
  `workflows/caption.py`, `workflows/temporal_change.py`, `workflows/optical_sar.py`,
  `tests/test_router.py`
- Edited: `agent/__init__.py`, `agent/controller.py` (dropped the never-read `self.planner`),
  `workflows/__init__.py`, `workflows/grounding.py` (removed the `GroundingWorkflow` class,
  kept `run_grounding_pipeline`), `tests/test_agent.py`, `tests/test_grounding_workflow.py`

**Verification:**
- `compileall backend/app` → exit 0
- grep for all 9 deleted symbols across `backend/`, `tests/`, `scripts/` → **none**
- `from backend.app.main import app` imports cleanly; 13 capabilities, 14 tools intact
- `pytest` → `100 passed · 11 failed · 1 skipped · 112 total`
- **Failure list byte-identical to baseline** (`diff` clean) — 8 tests removed, zero new failures,
  zero accidental fixes. Behaviour-preserving as required.

**Result:** `backend/app/agent/` 7 modules → 5; `backend/app/workflows/` 8 → 3.
