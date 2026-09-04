# Restructure Plan — Production-Grade Layout

**Status:** proposal, awaiting approval. No code moved yet.
**Measured:** 2026-09-04 against commit `360857f`.

Goal, in the author's words: *scalable structure · reusable UI design-system components for
consistency across tool pages · niche-specific backend components for better debugging, testing
and development.*

---

## 1. Diagnosis (measured, not asserted)

### 1.1 Backend — three overlapping layers, one of which is dead

| Layer | Files | Live? |
|---|---|---|
| `agent/planner.py` + `agent/router.py` (`RuleBasedPlanner`, `DeterministicRouter`) | 2 | **DEAD** |
| `orchestration/` (`AdvancedWorkflowPlanner`) | 14 | live |
| `workflows/*Workflow` classes + `workflows/base.py` | 6 | **DEAD** |

Evidence:
- `agent/controller.py:38` assigns `self.planner = RuleBasedPlanner()`. **`self.planner` is never
  read again** — `run_pipeline` calls `AdvancedWorkflowPlanner.plan()` directly (`controller.py:71`).
- `BaseWorkflow` has five subclasses. Nothing in `backend/app` ever instantiates or calls `.execute()`
  on any of them. The only external reference is one test.
- Live code in `workflows/` is three functions, not the class hierarchy:
  `run_grounding_pipeline`, `run_v4_reasoning`, `VideoAnalysisWorkflow`.

**Cost:** ~8 of the 120 tests (`test_router.py` ×6, `test_agent.py` ×2) exercise dead code, which
inflates the coverage story. A newcomer reading `agent/` learns a routing system that does not run.

### 1.2 Three different things are all called "registry"

`agent/registry.py` (tools) · `models/registry.py` (models) · `orchestration/capability_registry.py`
(capabilities). Same word, three unrelated concepts, three directories.

### 1.3 `api/routes.py` is 1186 lines spanning 6 domains

11 route prefixes, 34 imports in the first 80 lines, business logic inline in handlers. There is no
service layer — endpoints reach straight into the controller, repositories, artifact manager and
visualization engines.

### 1.4 `models/` mixes integration code with network definitions

`cdvqa.py` (adapter) sits beside `cdvqa_model.py` (the `nn.Module`); `fusion.py` contains both
`CrossAttentionFusionNet` and its adapter. Adapters and architectures have different reasons to
change and different test needs.

### 1.5 `tests/` is 38 files in one flat directory

No unit/integration/smoke separation, no pytest markers. You cannot run "the fast tests that need no
checkpoints" — which is exactly what you want while developing.

### 1.6 Frontend — no design system, despite tokens existing

| Finding | Number |
|---|---|
| Design tokens from `tailwind.config.js` actually used | **24 usages** |
| Raw `slate-*` / `cyan-*` / `emerald-*` etc. used instead | **~400 usages** |
| Token adoption | **~6%** |
| Distinct near-identical card treatments | 3 (`bg-slate-900 p-2.5 rounded border border-slate-800` and two variants) |
| `flex items-center space-x-2` repeated | 19× |
| Shared primitives (`Button`, `Card`, `Badge`, `Stat`) | **0** |
| Directories under `src/` | 2 (`app`, `components`) — no `lib`, `hooks`, `types`, `ui` |

**God components:** `VisualizationPanel.tsx` 591 lines · `ResultsPanel.tsx` 493 · `page.tsx` 421 ·
`VideoPlayerPanel.tsx` 342. That is 1,847 of 2,688 total frontend lines in four files.

**Live bug from the missing API layer:** `API_BASE` is declared twice with **different fallbacks** —
`page.tsx:16` falls back to `""`, `VisualizationPanel.tsx:21` falls back to
`"http://localhost:8000"`. In Docker, where `NEXT_PUBLIC_API_URL` is set, they agree; unset, they
silently diverge. Ten raw `fetch()` call sites, no shared error handling, no request types.

---

## 2. Target structure — backend

Principle: **layer by responsibility, slice by domain.** Pure logic must be importable and testable
without FastAPI, without a database, and without model weights.

```
backend/app/
├── main.py
├── core/                       # cross-cutting; zero domain knowledge
│   ├── config.py  logging.py  exceptions.py  device.py
├── api/
│   ├── deps.py                 # shared FastAPI dependencies (db session, job lookup)
│   └── v1/
│       ├── router.py           # aggregates the endpoint modules
│       └── endpoints/
│           ├── health.py  models.py  uploads.py
│           ├── analysis.py     # /analyze /jobs /results /trace /reports
│           ├── artifacts.py  visualization.py  video.py
├── domain/                     # PURE. no I/O, no FastAPI, no torch import at module level
│   ├── agent/       state.py  controller.py  executor.py  validator.py
│   ├── planning/
│   │   ├── input_analyzer.py  intent_classifier.py  matcher.py  dag.py  policy.py
│   │   └── capabilities/       # ← one file per capability, was a 207-line registry
│   │       ├── base.py  grounding.py  temporal_change.py  optical_sar.py
│   │       ├── vqa.py  spectral.py  video.py
│   ├── tools/                  # ← was agent/registry.py
│   │   ├── base.py             # Tool protocol + @register_tool decorator
│   │   ├── raster.py  validation.py  inference.py  evidence.py
│   │   └── registry.py         # auto-collected, no manual dict
│   └── evidence/
├── ml/                         # everything that touches weights
│   ├── base.py  registry.py  device.py  concurrency.py
│   └── adapters/
│       ├── grounding_dino/{adapter.py}
│       ├── sam2/{adapter.py}
│       ├── changeformer/{adapter.py, network.py}
│       ├── cdvqa/{adapter.py, network.py}      # cdvqa_model.py lands here
│       ├── fusion/{adapter.py, network.py}
│       ├── rs_vlm/  dofa/  remoteclip/  bigearthnet/
├── services/                   # composes domain + infra for the API
│   ├── analysis_service.py  video_service.py
│   ├── artifact_service.py   visualization_service.py
├── infra/
│   ├── db/{session.py, models/, repositories/, migrations/}
│   └── storage/artifact_store.py
├── geo/  visualization/  video/     # already cohesive — keep, move under domain later if useful
└── schemas/
```

### Why this serves the stated goals

**Debuggability.** A failure is now locatable by layer: routing bug → `domain/planning/`;
inference bug → `ml/adapters/<model>/`; persistence bug → `infra/db/`. Today a grounding bug could
live in `agent/`, `orchestration/`, `workflows/` or `models/`.

**Testability.** `domain/` imports no torch and no DB, so its tests run in milliseconds with no
checkpoints. That is the tier you run on every save.

**Scalability — this is the important one.** Adding a capability today requires editing **four
files in the right order**, and skipping any one produces a silent no-op (this is exactly bug D-104
in `decisions.md`: `multispectral_analysis` routes to a dead-end DAG because two of the four edits
were missed). After the change, a capability is **one file** in `capabilities/` declaring its own
tools, DAG and TaskType, self-registering — and a boot-time assertion fails loudly if a declared
tool is not registered (fixes D-105).

---

## 3. Target structure — frontend

```
frontend/src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # thin: composition only
│   └── (tools)/{grounding,change,optical-sar,video}/page.tsx
├── design-system/                  # ← the reusable layer that does not exist today
│   ├── tokens.ts                   # single source of truth; tailwind.config.js imports it
│   ├── primitives/
│   │   ├── Button.tsx  Card.tsx  Panel.tsx  Badge.tsx  Chip.tsx
│   │   ├── Stat.tsx  Field.tsx  Slider.tsx  Tabs.tsx  Modal.tsx
│   │   ├── Spinner.tsx  Tooltip.tsx  EmptyState.tsx
│   │   └── index.ts
│   └── patterns/                   # domain-aware but still reusable across tool pages
│       ├── ProvenanceBadge.tsx     # SOURCE_DATA / DERIVED_INDEX / MODEL_PROBABILITY / HEURISTIC
│       ├── StatusPill.tsx          # LOADED / AVAILABLE / NOT_CONFIGURED / FAILED
│       ├── ConfidenceMeter.tsx  LayerChip.tsx  MetricRow.tsx  LegendBar.tsx
├── features/                       # feature slices mirroring backend capabilities
│   ├── upload/         UploadPanel.tsx  useUpload.ts
│   ├── query/          QueryBar.tsx  useAnalyze.ts
│   ├── map/            MapViewer.tsx  useLayers.ts
│   ├── visualization/  VisualizationPanel.tsx  Histogram.tsx  PixelInspector.tsx  ExportMenu.tsx
│   ├── results/        ResultsPanel.tsx  AnswerCard.tsx  AreaStats.tsx
│   ├── trace/          TracePanel.tsx  WorkflowDecisionPanel.tsx
│   ├── video/          VideoPlayerPanel.tsx  Timeline.tsx  KeyframeCarousel.tsx
│   └── models/         ModelStatusPanel.tsx
├── lib/
│   ├── api/  client.ts (one API_BASE, typed errors, retry)  analysis.ts  video.ts  visualization.ts
│   ├── hooks/  useJobPolling.ts  useAsync.ts
│   └── utils/  cn.ts  format.ts
└── types/api.ts                    # generated from FastAPI /openapi.json
```

**Consistency mechanism.** The four god components each re-implement panel chrome, status colours
and metric rows in raw Tailwind. Extracting `<Card>`, `<Panel>`, `<Stat>`, `<StatusPill>` and
`<ProvenanceBadge>` means every tool page inherits the same treatment by construction, and the
`design.md` palette becomes enforced rather than aspirational (6% → ~100% token adoption).

**Contract safety.** Generating `types/api.ts` from the backend's own OpenAPI schema means a
response-shape change breaks the frontend build instead of failing silently at runtime — worth a lot
given the frontend is owned by different people.

---

## 4. Migration plan — staged, each stage independently shippable

| Stage | Work | Behaviour change | Risk |
|---|---|---|---|
| **S0** | Delete dead code: `agent/planner.py`, `agent/router.py`, `workflows/base.py` + 4 unused `*Workflow` classes, and their ~8 tests | none | very low |
| **S1** | Split `routes.py` → `api/v1/endpoints/*` + extract `services/` | none | low |
| **S2** | Package moves: `core/`, `domain/`, `ml/adapters/<model>/`, `infra/` | none (imports only) | medium — large import churn |
| **S3** | Decorator tool registry + per-capability files + boot-time validation | **fixes D-104, D-105** | medium |
| **S4** | Test tiers `unit/ integration/ smoke/ eval/` + pytest markers | none | low |
| **S5** | Frontend `design-system/` + `lib/api/client.ts` + OpenAPI type codegen | fixes the dual `API_BASE` bug | low |
| **S6** | Frontend feature slices; break up the four god components onto primitives | visual parity target | medium |

### Measured import churn (informs S2 scope)

531 import lines reference `backend.app.*` across `backend/`, `tests/` and `scripts/`:

| Would move to | Packages | Import lines touched |
|---|---|---|
| `domain/` | agent 30 · orchestration 35 · workflows 17 · evidence 18 | **100** |
| `ml/` | models 69 | **69** |
| `infra/` | db 54 · artifacts 6 | **60** |
| `core/` | logging 62 · exceptions 37 · config 15 | **114** |

**Refinement this changes:** `core/` is the *most* expensive move (114 lines) and the *least*
valuable — `config.py`, `logging.py` and `exceptions.py` are already flat, unambiguous, and nobody
is confused about where they live. `backend.app.logging` alone appears in 62 files.

**Revised S2:** move `domain/`, `ml/` and `infra/` (229 lines, high clarity gain); **leave
`config.py`, `logging.py`, `exceptions.py` at `backend/app/` root.** Same benefit, a third less
churn, a third less merge-conflict surface against Ayushman's and the frontend team's branches.
Revisit `core/` only if the root ever gets genuinely cluttered.

**Rules for the migration**
1. One stage per branch/PR. Never two in flight.
2. **S0–S2 must be behaviour-preserving.** Same tests, same pass count, no logic edits smuggled in.
3. Do not start S1 before `phases.md` **P0** — a green baseline is required, and there is none today
   (no venv, no torch, no checkpoints, suite never run on this machine). Refactoring without a
   baseline is how silent breakage happens.
4. Fix bugs in separate commits from moves, so `git log --follow` stays readable.
5. Frontend stages (S5, S6) need the frontend owners' agreement — that is their codebase.

---

## 4b. S0 — exact deletion manifest (verified safe)

Approved sequencing: **P0 baseline → S0**. Nothing below is executed until `pytest` runs green
and the true pass count is recorded.

Safety was established by grepping every import of `backend.app.agent.*` and
`backend.app.workflows.*` across `backend/`, `tests/` and `scripts/`. The only references to the
symbols below are (a) the dead modules referencing each other, (b) `__init__.py` re-exports, and
(c) three tests that exist solely to exercise them.

### Delete outright — 8 files

| File | Symbol | Sole consumers |
|---|---|---|
| `backend/app/agent/router.py` | `DeterministicRouter` | `agent/planner.py`, `agent/__init__.py`, `tests/test_router.py` |
| `backend/app/agent/planner.py` | `BasePlanner`, `RuleBasedPlanner`, `OptionalLLMPlanner` | `agent/controller.py` (dead assignment), `agent/__init__.py`, `tests/test_agent.py` |
| `backend/app/workflows/base.py` | `BaseWorkflow` | only the 5 subclasses |
| `backend/app/workflows/single_vqa.py` | `SingleVQAWorkflow` | `workflows/__init__.py` only |
| `backend/app/workflows/caption.py` | `CaptionWorkflow` | `workflows/__init__.py` only |
| `backend/app/workflows/temporal_change.py` | `TemporalChangeWorkflow` | `workflows/__init__.py` only |
| `backend/app/workflows/optical_sar.py` | `OpticalSARWorkflow` | `workflows/__init__.py` only |
| `tests/test_router.py` | 6 tests on `DeterministicRouter` | — |

Each of the four deleted `*Workflow` classes is a two-line passthrough:
`async def execute(state): return await agent_controller.run_pipeline(state)`.

### Edit — 6 files

| File | Change |
|---|---|
| `agent/controller.py` | drop `planner` import; drop `self.planner = RuleBasedPlanner()` (line 38, assigned and never read); simplify `__init__` to no args — the only construction site is `agent_controller = AgentController()` at line 315 |
| `agent/__init__.py` | remove `DeterministicRouter`, `BasePlanner`, `RuleBasedPlanner`, `OptionalLLMPlanner` from imports and `__all__` |
| `workflows/__init__.py` | remove `BaseWorkflow` + the 4 deleted classes; keep `GroundingWorkflow`→(removed), `VideoAnalysisWorkflow` |
| `workflows/grounding.py` | remove the `GroundingWorkflow` class (line 331→EOF) and the now-unused `BaseWorkflow` import. **Keep `run_grounding_pipeline`** — it is live, called by `agent/registry.py:119` and `scripts/evaluate_grounding_vrsbench.py` |
| `tests/test_agent.py` | remove `test_rule_based_planner`; **keep** `test_validator_rejects_unauthorized_tool` (`PlanValidator` is live) |
| `tests/test_grounding_workflow.py` | remove `test_grounding_workflow_class`; **keep** `test_grounding_pipeline_execution`, which already covers the same code path directly. `GroundingWorkflow.run()` was a one-line passthrough to `run_grounding_pipeline` |

### Expected effect

- 8 files deleted, 6 edited
- **8 tests removed** (6 router + 1 planner + 1 workflow-class) — expected count 120 → 112
- **Zero behaviour change.** No live code path is touched.
- `backend/app/workflows/` drops from 8 modules to 3 live ones:
  `grounding.py`, `grounding_reasoner.py`, `video_analysis.py`

### Acceptance gate

Baseline pass count minus exactly 8, no new failures, `python -m compileall backend/app` clean.
If any other test changes state, stop and investigate — that means something was not as dead as the
grep indicated.

---

## 4c. Frontend — structural reorganisation only

**Author's constraint (2026-09-04):** *"just restructure what they made — their work stays intact.
The codebase structure just gets organised by me. I don't make frontend code, I work backend only.
We'll be working on the existing frontend; we can revamp later if we want. I can only propose for now."*

So: **file moves and import-path updates only. No component internals rewritten. Nothing executed
until the frontend owners agree.**

### Move manifest — pure `git mv`, zero logic change

```
src/components/UploadPanel.tsx            → src/features/upload/UploadPanel.tsx
src/components/QueryBar.tsx               → src/features/query/QueryBar.tsx
src/components/MapViewer.tsx              → src/features/map/MapViewer.tsx
src/components/MetadataPanel.tsx          → src/features/metadata/MetadataPanel.tsx
src/components/ModelStatusPanel.tsx       → src/features/models/ModelStatusPanel.tsx
src/components/ResultsPanel.tsx           → src/features/results/ResultsPanel.tsx
src/components/TracePanel.tsx             → src/features/trace/TracePanel.tsx
src/components/WorkflowDecisionPanel.tsx  → src/features/trace/WorkflowDecisionPanel.tsx
src/components/VideoPlayerPanel.tsx       → src/features/video/VideoPlayerPanel.tsx
src/components/VisualizationPanel.tsx     → src/features/visualization/VisualizationPanel.tsx
src/components/Header.tsx                 → src/components/layout/Header.tsx
```

Only `src/app/page.tsx` import lines change. The slices deliberately mirror the backend
capabilities, so a feature has one home on both sides.

### Additive scaffolding — opt-in, nothing forced to adopt it

`src/design-system/` (`tokens.ts` + empty `primitives/`, `patterns/`), `src/lib/api/client.ts`,
`src/types/api.ts`. Existing components keep working untouched; the frontend team migrates onto
these at whatever pace they choose. Extracting `<Card>`, `<Panel>`, `<Stat>`, `<StatusPill>` and
`<ProvenanceBadge>` from the duplicated Tailwind clusters (§1.6) is **their** call, not a
prerequisite for the move.

### The one thing worth fixing regardless

`API_BASE` is declared twice with different fallbacks — `""` in `page.tsx:16`,
`"http://localhost:8000"` in `VisualizationPanel.tsx:21`. A single `lib/api/client.ts` export
removes the divergence. Two-line change, no restructure required. Worth raising with them
independently of everything else here.

---

## 5. Sequencing against the existing plan

The blockers in `phases.md` P1 (no remote-sensing adaptation; randomly-initialised fusion head) are
**evaluation-failing**; this restructure is **velocity-improving**. If the deadline is tight, the
honest ordering is:

```
P0 baseline → S0 (dead code, ~1h) → P1 blockers → S1–S4 → S5–S6
```

S0 is worth doing immediately regardless: it is an hour of deletion, it cannot break anything that
runs, and it removes the misleading `agent/` layer that anyone reading the repo hits first.

The counter-argument for doing S3 early: it *structurally prevents* the class of bug that D-104 and
D-105 already represent. If more capabilities are going to be added — and P3 adds two — doing S3
before them is cheaper than adding two more four-file edits and then migrating three.
