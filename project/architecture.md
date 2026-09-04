# Architecture — SatQuery AI

Describes the system **as the code actually is** (commit `360857f`), not as the marketing docs
describe it. Where `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md` disagrees with the source, the
source wins and the divergence is called out in `decisions.md`.

---

## 1. Tech stack

### Backend
| Layer | Choice | Version |
|---|---|---|
| Web framework | FastAPI + Uvicorn | ≥0.109 / ≥0.27 |
| Validation | Pydantic v2 | ≥2.5 |
| ORM / DB | SQLAlchemy 2.0 async + asyncpg + PostgreSQL 15 | ≥2.0 / ≥0.29 |
| Migrations | Alembic | ≥1.13 |
| ML runtime | PyTorch + torchvision + transformers + timm + safetensors + open-clip-torch | ≥2.0 / ≥4.41 |
| Geospatial | pyproj, shapely, tifffile, numpy, scipy (rasterio/geopandas optional — pure-Python fallbacks in code) | — |
| Imaging | Pillow, OpenCV (headless), matplotlib | — |
| Reports | ReportLab | ≥4.0 |
| Tests | pytest + pytest-asyncio | ≥7.4 |

### Frontend
Next.js 14 (App Router) · React 18 · TypeScript 5 · TailwindCSS 3.4 · maplibre-gl 4 · lucide-react · clsx + tailwind-merge

### Infra
Docker + docker-compose (postgres + backend + frontend). Checkpoints and datasets are
**host-mounted read-only volumes**, never baked into images and never committed to git.

---

## 2. Folder structure

```
satquery-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, exception handlers, alias routes
│   │   ├── config.py                # YAML + env → typed Pydantic settings singleton
│   │   ├── exceptions.py            # SatQueryException hierarchy
│   │   ├── logging.py
│   │   ├── api/routes.py            # ~25 REST endpoints (1186 lines — the largest file)
│   │   ├── agent/                   # legacy//execution layer
│   │   │   ├── controller.py        # AgentController.run_pipeline — the spine
│   │   │   ├── state.py             # AgentState (mutable job context passed to every tool)
│   │   │   ├── planner.py           # RuleBasedPlanner (legacy fallback)
│   │   │   ├── router.py            # legacy keyword router
│   │   │   ├── validator.py         # PlanValidator — tool whitelist
│   │   │   ├── executor.py          # SafeToolExecutor — per-tool try/except + timing
│   │   │   └── registry.py          # TOOL_REGISTRY: 14 named callables
│   │   ├── orchestration/           # the "agentic" layer (newer, richer)
│   │   │   ├── input_analyzer.py    # file → modality/band/geometry facts
│   │   │   ├── intent_classifier.py # regex entity extraction + intent + routing_confidence
│   │   │   ├── capability_registry.py # 13 CapabilityDefinitions
│   │   │   ├── matcher.py           # intent + facts → capability (priority rules)
│   │   │   ├── dependency_graph.py  # capability → DAG + topological stages
│   │   │   ├── planner.py           # AdvancedWorkflowPlanner → OrchestratedPlan
│   │   │   ├── dependency_checker.py# pre-flight tool/model/input verification
│   │   │   ├── resource_manager.py  # RAM/VRAM headroom check
│   │   │   ├── policy_engine.py
│   │   │   ├── output_validator.py  # post-hoc sanity on model outputs
│   │   │   ├── cache.py             # deterministic result cache
│   │   │   ├── provenance.py        # provenance graph builder
│   │   │   ├── health.py            # workflow success/latency counters
│   │   │   └── schemas.py           # Capability/DAG/Intent pydantic models
│   │   ├── models/                  # one adapter per neural model
│   │   │   ├── base.py              # BaseModelAdapter — lazy load, availability, unload
│   │   │   ├── registry.py          # ModelRegistry: 9 adapters + metadata
│   │   │   ├── device.py, concurrency.py
│   │   │   ├── grounding_dino.py  sam2.py  changeformer.py
│   │   │   ├── cdvqa.py  cdvqa_model.py
│   │   │   ├── general_rs_vlm.py    # ← currently BLIP-VQA (see gaps)
│   │   │   ├── dofa.py  fusion.py  remoteclip.py  bigearthnet.py
│   │   ├── workflows/               # multi-step pipelines invoked by tools
│   │   │   ├── grounding.py         # DINO → reasoner → SAM2 → evidence
│   │   │   ├── grounding_reasoner.py# V1/V2/V3/V4 candidate scoring (742 lines)
│   │   │   ├── temporal_change.py  single_vqa.py  caption.py  optical_sar.py
│   │   │   └── video_analysis.py
│   │   ├── geo/                     # raster IO, metadata, modality, alignment, rendering
│   │   ├── evidence/                # boxes, masks, polygons, stats, fusion, adjudicator, PDF
│   │   ├── visualization/           # composites, indices, sar, heatmaps, inspector, exports
│   │   ├── video/                   # decoder, sampler, flagger
│   │   ├── artifacts/manager.py     # results/{job_id}/ workspace layout
│   │   ├── db/                      # models(8 files), repositories(3), session, migrations
│   │   └── schemas/                 # request/response/evidence/agent/video pydantic contracts
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/src/
│   ├── app/{layout,page,globals.css}
│   └── components/  # Header, UploadPanel, QueryBar, MapViewer, VisualizationPanel,
│                    # ResultsPanel, TracePanel, VideoPlayerPanel, ModelStatusPanel,
│                    # MetadataPanel, WorkflowDecisionPanel
├── configs/{app,models,workflows}.yaml
├── training/vqa/                    # CDVQA training: dataset.py, model.py, train_cdvqa.py, extract_second.py
├── scripts/                         # smoke tests, evaluations, verification (16 scripts)
├── tests/                           # 38 files, 120 test functions
├── datasets/samples/                # small real fixtures committed for smoke tests
├── third_party/GeoChat/             # vendored, NOT wired into the backend
├── docs/                            # team docs incl. master documentation + 27 model dossiers
├── checkpoints/                     # gitignored, host-mounted, must be fetched
└── results/                         # gitignored job workspaces
```

---

## 3. Application flow

### 3.1 Request lifecycle (image analysis)

```
POST /api/upload  (multipart)
   └─ routes.upload_rasters → validate ext/MIME/magic → save under results/{job_id}/input/
                            → RasterInspector.inspect → return metadata + filenames

POST /api/analyze {query, image_filenames, task?}
   └─ routes.analyze_query
        └─ build AgentState(request_id, query, image_paths, parameters)
        └─ agent_controller.run_pipeline(state)          ← backend/app/agent/controller.py
             1  status=VALIDATING           → JobRepository.create_or_get_job
             2  status=PLANNING
                AdvancedWorkflowPlanner.plan(state):
                   InputAnalyzer.analyze()        → modalities, bands, file types, geometry
                   IntentClassifier.classify_intent() → task + entities + routing_confidence
                   CapabilityMatcher.match()      → CapabilityDefinition + human-readable reason
                   DependencyGraph.build_dag_for_capability() → nodes + topological stages
                to_legacy_workflow_plan()          → WorkflowPlan{task, steps[], models[]}
             3  DependencyChecker.verify_plan_dependencies()  (input count, tools, checkpoints)
             4  ResourceManager.verify_resource_availability() (RAM/VRAM headroom)
             5  PlanValidator.validate_plan()      (tool whitelist)
             6  orchestration_cache.get(key)       → short-circuit on exact repeat
             7  status=RUNNING
                for tool in plan.steps: SafeToolExecutor.execute_tool(tool, state)
                   (status flips to GENERATING_EVIDENCE at "generate_report")
             8  OutputQualityValidator → warnings, quality_status
             9  ConfidenceEvaluator + ConsistencyChecker
            10  ProvenanceBuilder.build_provenance_graph()
            11  operational_health.record_workflow_execution()
            12  status=COMPLETED | FAILED
        └─ persist: result JSON + trace JSON to disk; job/steps/model_runs/results/artifacts to Postgres
        └─ return AnalyzeResponse

GET /api/jobs/{id}[/status] · /api/results/{id} · /api/trace/{id} · /api/reports/{id}
GET /api/artifacts/{id}/{type}/{filename}
GET /api/analysis/{id}/layers | /visualizations/{layer} | /legend | /histogram | /export
POST /api/analysis/{id}/inspect-pixel
```

Video uses a **separate path**: `POST /api/video/upload` → `POST /api/video/analyze` →
`VideoAnalysisWorkflow` (not the AgentController DAG) → `GET /api/video/{id}/...`.

### 3.2 Routing decision table (as implemented)

| Inputs | Query signal | Capability | DAG tools |
|---|---|---|---|
| 1 image | grounding verb / object noun | `single_image_grounding` | inspect_raster → validate_single_image → run_grounding → run_segmentation → generate_overlay → generate_report |
| 1 image | caption/summarise keywords | `single_image_caption` | inspect → validate → run_caption → report |
| 1 image | anything else | `single_image_vqa` | inspect → validate → run_vqa → report |
| 1 multispectral raster | NDVI/NDWI/spectral words | `multispectral_analysis` | ⚠ **no DAG branch** → falls back to inspect → report |
| 1 SAR raster | SAR/polarisation words | `sar_analysis` | ⚠ **no DAG branch** → falls back to inspect → report |
| 2 images, optical+SAR | any | `optical_sar_analysis` | inspect → validate_optical_sar_pair → run_optical_sar → report |
| 2 images, question form | "what/has/did/…?" | `temporal_change_vqa` | inspect → validate_temporal_pair → run_change_detection → {calculate_statistics ∥ run_change_vqa ∥ generate_overlay} → report |
| 2 images, imperative | "show where…" | `temporal_change_detection` | same minus run_change_vqa |
| video | ordering/relation/"track" | `video_grounding_tracking` | separate video workflow |
| video | otherwise | `video_grounding` | separate video workflow |

### 3.3 Model → capability wiring

| Model key | Adapter | Used by capability |
|---|---|---|
| `grounding_dino` | `GroundingDINOAdapter` | single_image_grounding, video_* |
| `sam2` | `SAM2Adapter` | single_image_grounding, video_grounding_tracking |
| `changeformer` | `ChangeFormerAdapter` | temporal_change_detection, temporal_change_vqa |
| `cdvqa` | `CDVQAAdapter` | temporal_change_vqa |
| `general_rs_vlm` | `GeneralRSVLMAdapter` (BLIP-VQA) | single_image_vqa, single_image_caption |
| `dofa` | `DOFAAdapter` | optical_sar_analysis |
| `satquery_optical_sar_fusion` | `OpticalSARFusionModel` | optical_sar_analysis |
| `remoteclip` | `RemoteCLIPAdapter` | *optional* on grounding — never invoked |
| `bigearthnet` | `BigEarthNetMultimodalAdapter` | ⚠ **none** — registered but orphaned |

---

## 4. Key architectural properties

**Two-layer planning.** `orchestration/` produces a rich `OrchestratedPlan` (capability + intent +
DAG + confidence); it is then flattened to a legacy linear `WorkflowPlan` for `SafeToolExecutor`.
The DAG's parallel stages are computed and reported but **executed sequentially**. The DAG is
currently descriptive, not an execution engine.

**Lazy model loading.** `BaseModelAdapter.__init__` never touches weights. `is_available()` is a
filesystem existence check on the configured checkpoint path; `load_model()` happens on first
`predict()`. This is what lets the API boot and report honest `NOT_CONFIGURED` statuses on a
machine with no checkpoints.

**Database is non-fatal.** `AgentController._safe_db_op` swallows persistence errors with a
warning. The pipeline completes and returns results even with Postgres down; you lose the audit
trail, not the answer.

**Artifacts are filesystem-first, DB-indexed.** `results/{job_id}/{input,masks,overlays,vectors,reports}/`
is the source of truth; Postgres holds pointers plus the trace.

**State is a single mutable object.** Every tool takes `AgentState` and mutates it in place. Simple
and easy to trace; it also means tool ordering is load-bearing and tools are not independently
composable.

---

## 5. Database schema (10 tables)

`analysis_jobs` (root, UUID PK) → 1:N `uploaded_files`, `model_runs`, `execution_steps`,
`artifacts`, `visualization_layers`, `videos`; 1:1 `analysis_results`.
`videos` → 1:N `video_frames`, `video_flags`.

---

## 6. Deployment

```
Browser :3000 → Next.js server → (rewrite) → FastAPI :8000 → Postgres :5432
                                              ↓ native FS
                                     checkpoints/  datasets/  results/
```

Env config precedence: `configs/*.yaml` defaults → `.env` / environment overrides
(`DATABASE_URL`, `SATQUERY_DEVICE`, `*_CHECKPOINT`, …), applied in `Config._apply_env_overrides`.
