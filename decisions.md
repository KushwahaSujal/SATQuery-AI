# Decisions — Reasoning Log

*(This is the file referred to as `theory.md` elsewhere. Same purpose: the **why** behind the code.)*

Every non-trivial change gets an entry. The rule is simple: **if someone reading the diff in three
months would ask "why did they do it like that?", the answer belongs here.**

**Entry template**

```
### D-NNN · <short title>
Date · Author · Files touched
**Decision:** what we did, in one sentence.
**Why:** the reasoning, the constraint, the thing that forced it.
**Alternatives rejected:** and why each lost.
**How it works:** what the function/library actually does, for a reader who doesn't know it.
**Consequences:** what this now makes easy, and what it makes hard.
```

---

## 1. Decisions inherited from the existing codebase

These were made before this log existed. Reconstructed from the source and recorded so they are
defensible in a demo, a viva, or a paper.

### D-001 · Decoupled specialist models instead of one large VLM
Files: `orchestration/capability_registry.py`, `models/registry.py`
**Decision:** run five task-specific networks behind a router rather than a single monolithic VLM.
**Why:** generalist VLMs (GPT-4V, LLaVA) have no multispectral or SAR pretraining, hallucinate
coordinates, cannot emit pixel-precise masks or true metric areas, and cannot do Siamese
bi-temporal differencing. The problem statement itself says a generic VLM will not satisfy the
requirements.
**Alternatives rejected:** fine-tuning one VLM for everything — a single point of failure; every new
task needs full retraining; spatial precision stays poor.
**Consequences:** better per-task accuracy and honest failure modes; the cost is orchestration
complexity and a much larger surface area to keep coherent. That orchestration is our actual
research contribution, so this is a good trade.

### D-002 · Deterministic (regex + rules) intent classification, not an LLM router
Files: `orchestration/intent_classifier.py`, `orchestration/matcher.py`
**Decision:** classify intent with lexical pattern lists and explicit priority rules.
**Why:** the evaluation grades the *observable* execution trace. A deterministic router is
reproducible, auditable, zero-cost, has no API dependency, and cannot hallucinate a task. It also
means the same query always routes the same way during a live demo.
**How it works:** `extract_entities()` runs ordered regex families (object, colour, size, position,
relation, ordering, temporal, change) over the lowercased query and fills an
`ExtractedQueryEntities` record. `classify_intent()` then branches on input count and modality
first, query semantics second, and returns a `routing_confidence` float computed from how many
facets matched. If a grounding verb appears with no object and no spatial anchor, it flags
`is_ambiguous` and drops confidence to 0.50 with a suggested clarification.
**Alternatives rejected:** LLM-based routing (non-deterministic, adds latency and a dependency,
and the internal reasoning is explicitly not evaluated); a trained classifier (no labelled routing
data, and it would be a black box in exactly the layer we want to be transparent).
**Consequences:** brittle to phrasings outside the pattern lists. Mitigation: the fallback
noun-phrase extractor after a grounding verb, plus `single_image_vqa` as the terminal default.
**Open risk:** the ISRO/SAC evaluation queries are undisclosed. Router recall on unseen phrasing is
untested — this needs a router-accuracy experiment (see `phases.md` P2).

### D-003 · Two-layer plan: rich DAG flattened to linear steps
Files: `orchestration/planner.py`, `orchestration/dependency_graph.py`, `agent/controller.py`
**Decision:** build a full DAG with dependencies and topological stages, then flatten it to a
linear step list for execution via `to_legacy_workflow_plan()`.
**Why:** the DAG gives us the auditable artefact the problem statement asks for (task, tools,
parameters, dependencies) and computes which nodes *could* run in parallel; the linear list keeps
the existing `SafeToolExecutor` working without a rewrite.
**How it works:** `compute_execution_stages()` repeatedly emits the set of nodes whose dependencies
are all already completed — a Kahn-style wave decomposition — and raises `WorkflowError` on a cycle
or an unsatisfiable dependency.
**Consequences:** we report parallelism we do not exploit. Honest framing in the paper: the DAG is
a *planning and audit* structure; concurrent execution is future work. Do not claim parallel
speedups we don't measure.

### D-004 · Lazy model loading with filesystem-existence availability checks
Files: `models/base.py`, `models/registry.py`
**Decision:** adapters are constructed eagerly, weights are loaded on first `predict()`, and
`is_available()` is nothing more than "does the configured checkpoint path exist".
**Why:** the API must boot in ~180 MB on a machine with no GPU and no checkpoints, and must report
truthful `NOT_CONFIGURED` states rather than pretending. It also keeps VRAM free until a query
actually needs a given model.
**How it works:** `BaseModelAdapter.__init__` only resolves config + device. `checkpoint_path`
resolves relative paths against the project root. `ensure_available()` raises a structured
`ModelUnavailableError` naming the expected path — which is what surfaces in the UI.
**Consequences:** availability is a weak signal — a corrupt or wrong-architecture checkpoint reads
as "available" until load fails. `validation_status` (`PENDING_VERIFICATION` vs `VERIFIED`) exists
to cover this but is only set by `mark_verified()`, which nothing calls automatically.

### D-005 · Database failures are non-fatal
Files: `agent/controller.py:40` `_safe_db_op`
**Decision:** wrap every persistence call so a Postgres outage logs a warning and the pipeline
continues.
**Why:** a demo must not die because a container is down. The answer and the on-disk artifacts are
the product; the DB is the audit index.
**Consequences:** silent audit-trail loss. Acceptable for a hackathon, **not** acceptable for the
"full traceability" claim in the paper — there we must state that persistence is best-effort.

### D-006 · Filesystem-first artifacts, database as index
Files: `artifacts/manager.py`, `db/models/artifact.py`
**Decision:** `results/{job_id}/{input,masks,overlays,vectors,reports}/` holds the real bytes;
Postgres stores paths and metadata.
**Why:** rasters, GeoTIFFs and PDFs are large and binary; serving them from disk is trivial and
they stay inspectable by hand and by QGIS. UUID-per-job directories also give free tenant isolation.
**Consequences:** DB and disk can drift (deleting a results dir orphans rows). No cleanup job exists.

### D-007 · Postgres + asyncpg over SQLite/Mongo
Files: `db/session.py`, `configs/app.yaml`
**Why:** concurrent async writes from a FastAPI worker (SQLite serialises writers), plus JSONB for
the unstructured trace/result payloads alongside real foreign keys for the audit chain — which
Mongo would not enforce.

### D-008 · OpenCV `VideoCapture` for decoding, not PyAV/Decord
Files: `video/decoder.py`
**Why:** `iter_frames()` is a generator, so memory stays O(1) regardless of video length; OpenCV
ships prebuilt wheels on Windows/Linux with no C compilation, which matters because the team
develops on Windows.
**Consequences:** less precise seeking than PyAV. Acceptable — we sample at ~1 fps anyway.

### D-009 · Heuristic video event score, explicitly labelled as a heuristic
Files: `video/flagger.py`, `configs/app.yaml`
**Decision:** `score = 0.4·detector + 0.3·V4 + 0.2·SAM2 + 0.1·persistence`, weights configurable and
validated to sum to 1.0 at config load.
**Why:** we have no labelled video event data, so there is nothing to calibrate against. Publishing
it as an uncalibrated composite is the honest option; calling it "AI confidence" would not be.
**Consequences:** must never be presented as a probability. Keep the `HEURISTIC_ANALYSIS`
provenance tag on it everywhere.

### D-010 · Zero-fabrication rule for spectral indices
Files: `visualization/indices.py`, `visualization/provenance.py`
**Decision:** refuse to compute NDVI/NDWI/NDBI when the required physical bands are absent; return
`INDEX_NOT_AVAILABLE` with an explanation instead of synthesising NIR.
**Why:** it is the project's central credibility claim, and a fabricated index in a disaster-response
context is actively dangerous.
**Bug fixed historically:** single-character band matching (`"r" in "green"`) misidentified green as
red; replaced with tokenised word-boundary matching.
**Note:** this rule is currently **violated elsewhere** — see D-102.

### D-011 · ChangeFormer preprocessing must match its training contract
Files: `models/changeformer.py`
**Decision:** normalise to `[-1, 1]`, not ImageNet mean/std.
**Why:** using ImageNet statistics produced oversaturated, wrong change masks on LEVIR-CD. The
published ChangeFormer training pipeline rescales to `[-1, 1]`; a preprocessing mismatch silently
destroys accuracy without throwing.
**Lesson to generalise:** for every pretrained checkpoint, copy the *original* preprocessing
verbatim and write a smoke test that asserts output sanity, not just "it didn't crash".

### D-012 · CDVQA does not replace ChangeFormer — both run
Files: `orchestration/dependency_graph.py` (`temporal_change_vqa`), `agent/registry.py`
**Decision:** on a bi-temporal question, execute ChangeFormer *and* CDVQA and merge the outputs.
**Why:** they answer different questions. ChangeFormer answers *where* (pixel mask, area in m²);
CDVQA answers *what* (19-class semantic label). Neither alone satisfies "what changed, and where".
**How it works:** the DAG marks `run_change_vqa`, `calculate_statistics` and `generate_overlay` as
siblings depending only on `run_change_detection`; `generate_report` joins all three.
**Consequences:** two model loads for one query (~3.2 GB). Also a graceful path: if the CDVQA
checkpoint is missing, `run_change_vqa` composes a factual sentence from ChangeFormer statistics
instead of failing — and records a warning saying exactly that.

### D-013 · V1→V4 are scoring strategies, not four models
Files: `workflows/grounding_reasoner.py`
**Decision:** implement four candidate-ranking policies over the same Grounding DINO box set.
**Why:** DINO returns many plausible boxes for a referring expression; picking `argmax(score)` (V1)
ignores everything the phrase actually said. V2 adds token-level semantic match, V3 adds area/centre
priors, V4 parses attributes and spatial relations and scores them explicitly.
**Measured (VRSBench sample):** V1 mIoU 0.1832 / R@0.5 0.22 · V2 **0.2371 / 0.26** · V3 0.2238 / 0.24.
V4 is the production default on qualitative multi-object improvement but **has no published IoU
number** — that gap must be closed before any paper claim. See `phases.md` P2.

### D-014 · Vendor GeoChat, ship BLIP — and say so
Files: `third_party/GeoChat/`, `models/general_rs_vlm.py`
**Decision (inherited):** GeoChat-7B was vendored but never wired in; `general_rs_vlm` loads
`Salesforce/blip-vqa-base`.
**Why it happened:** GeoChat shard 1 is ~10 GB and the target drive was FAT32 (4 GB file cap), so
the weights could not be downloaded. BLIP-VQA (~1.5 GB) was substituted to keep the VQA endpoint
functional.
**Status: this is now our single biggest liability.** BLIP has no remote-sensing adaptation, which
the problem statement explicitly disqualifies. See D-101.

---

## 2. Decisions made in this session

### D-100 · Document the code, not the master PDF
Date 2026-09-04 · Session 1 · Files: all root `*.md`
**Decision:** where `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md` and the source disagree, these docs
describe the source and flag the divergence.
**Why:** the master doc describes `backend/app/models/geochat.py`, a `temporal_vqa.py` workflow, a
492 MB ChangeFormer checkpoint and "104/104 tests". The repo has no `geochat.py`, the workflow is
`temporal_change.py`, the setup doc says the checkpoint is 164 MB, and there are 120 test functions.
Planning against a document that does not match the code produces work that does not compile.
**Consequences:** the master doc needs a reconciliation pass before it is used for the paper or
shown to judges. Tracked in `phases.md` P0.

---

### D-110 · Restructure the repo into layered/feature-sliced packages
Date 2026-09-04 · Session 2 · Files: `restructure.md`
**Decision:** adopt a staged restructure (S0–S6) documented in `restructure.md`. Approved
sequencing: **P0 baseline → S0 dead-code removal**, then the P1 model blockers, then S1–S4.
**Why:** measured, not asserted — the backend carries three overlapping planning layers of which
two are dead; three unrelated concepts are all named "registry"; `routes.py` is 1186 lines across
six domains with no service layer; `tests/` is 38 flat files with no markers, so there is no way to
run only the fast checkpoint-free tests. On the frontend, the design tokens defined in
`tailwind.config.js` are ~6% adopted (24 token usages vs ~400 raw colour utilities) and four files
hold 1,847 of 2,688 lines.
**The load-bearing argument** is not tidiness. Adding a capability today requires four edits in the
right order across four files, and skipping one fails **silently** — which is exactly how
`multispectral_analysis` and `sar_analysis` ended up routing to a dead-end DAG (D-104/D-105). A
decorator-registered tool registry plus one-file-per-capability with a boot-time assertion makes
that class of bug impossible rather than merely fixed.
**Alternatives rejected:** big-bang rewrite (unreviewable, and there is no green baseline to protect
it); leave as-is until after the deadline (P3 adds two more capabilities, so the four-edit trap gets
paid twice more and then migrated anyway).
**Consequences:** S2 causes large import churn across ~223 modules. Mitigated by keeping S0–S2
strictly behaviour-preserving and one stage per PR.

### D-111 · Frontend gets structural reorganisation only; component code untouched
Date 2026-09-04 · Session 2
**Decision:** for the frontend, do `git mv` into feature slices plus additive scaffolding
(`design-system/`, `lib/api/`, `types/`) and nothing else. No component internals rewritten. Not
executed until the frontend owners agree.
**Why:** the author works backend only and another group owns the frontend; their in-flight work
must not be disturbed. Moves plus import-path updates are reviewable in seconds and cannot change
rendering; rewriting 591-line panels cannot.
**Consequences:** the duplication (three near-identical card treatments, `flex items-center
space-x-2` ×19) stays until that team chooses to migrate onto the primitives. Acceptable — the
scaffolding is opt-in and the slices already give them a consistent home per feature.
**Carve-out worth raising independently:** `API_BASE` is declared twice with **different fallbacks**
(`""` in `page.tsx:16` vs `"http://localhost:8000"` in `VisualizationPanel.tsx:21`). That is a
latent environment-dependent bug, is a two-line fix, and needs no restructure.

### D-112 · Pin Python 3.11.16 via pyenv for the baseline
Date 2026-09-04 · Session 2
**Decision:** build 3.11.16 with pyenv and create `.venv` from it.
**Why:** the machine ships only Python 3.14.4, while the project requires 3.10/3.11
(`docs/…DEPLOYMENT`, `README`). Several pinned dependencies have no 3.14 wheels yet. A baseline
measured on an unsupported interpreter would not be a baseline.
**Note:** the machine has an RTX 3070 (8 GB VRAM), so CUDA wheels are appropriate — but 8 GB will
not hold GeoChat-7B (~14 GB), which independently supports the D-101 recommendation to adapt a
small VLM rather than revive GeoChat.

### D-113 · Disable asyncpg's prepared-statement cache behind transaction poolers
Date 2026-09-04 · Session 2 · Files: `backend/app/db/session.py`
**Decision:** detect a transaction-mode pooler in the database URL and pass
`connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}`.
**Why — measured, not assumed.** The team's `.env` points `DATABASE_URL` at
`…pooler.supabase.com:6543`, which is Supabase's **transaction-mode** pooler (pgBouncer). asyncpg
creates server-side prepared statements by default; transaction pooling rebinds each transaction to
an arbitrary backend, so those names collide. A three-way probe against the live database gave:

| Configuration | Result |
|---|---|
| A · as-shipped (`:6543`, no `connect_args`) | **FAIL** — `asyncpg.exceptions.DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_1__" already exists` |
| B · `:6543` + `statement_cache_size=0` | PASS |
| C · `:5432` session mode, as-shipped settings | PASS |

Postgres returns its own HINT naming pgbouncer transaction mode as the cause.
**The dangerous part:** in configuration A the *first* query (`SELECT version()`) succeeds. A health
check passes, the app reports healthy, and it fails later under real query load — an intermittent
production failure rather than a startup error.
**How it works:** `statement_cache_size=0` tells asyncpg to send each query unprepared;
`prepared_statement_cache_size=0` disables SQLAlchemy's dialect-level cache. Cost is a small
per-query planning overhead, which is irrelevant at our request volume.
**Scope of the heuristic:** matches `:6543` or `pgbouncer` in the host only — deliberately **not**
`pooler.` on its own, because configuration C proved the same pooler host on `:5432` (session mode)
supports prepared statements normally, and disabling the cache there would cost performance for no
benefit. `SATQUERY_DB_POOLER=1|0` overrides when the heuristic guesses wrong.
**Verified:** through `get_async_engine()` — the app's own factory, not a hand-rolled engine —
with 10 parameterised queries on fresh connections, 30 distinct statements on one connection, and
16 concurrent pooled queries. All pass.
**Alternative rejected:** switching `.env` to `:5432`. It works (configuration C) and needs no code,
but it silently breaks again the moment anyone pastes the pooler URL Supabase shows by default. The
code fix is robust to either port.

---

## 3. Open findings that need a decision (not yet decided)

### D-115 · The published "VRSBench" grounding numbers were not measured on VRSBench — **do not cite them**
Date 2026-09-04 · Session 2 · Evidence: `datasets/samples/vrsbench_sample_records.json`,
`tests/test_vrsbench_eval.py:47`, real `VRSBench_EVAL_referring.json`

`SATQUERY_AI_MASTER_DOCUMENTATION.md` §19 reports V1 mIoU 0.1832 / V2 0.2371 / V3 0.2238
"Evaluated on VRSBench sample setup". What that sample actually contains:

- **2 records**, both with `image_id: "real_image_b"` — which is a **LEVIR-CD change-detection
  crop**, not a VRSBench image. `tests/test_vrsbench_eval.py:47` hard-asserts this
  (`assert "real_image_b" in resolved.name`).
- **Record 1's query is verbatim from real VRSBench** — "The small dark-colored vehicle located at
  the top-right corner of the image." In the official split that query belongs to `P0003_0002.png`
  with ground truth `{<87><29><92><36>}`. Here it was re-pointed at a LEVIR-CD crop with an
  invented box `[245, 48, 256, 65]`.
- **Record 2's query has no match anywhere in the 16,159 real records** — it was written by hand,
  and it reuses record 1's box **identically**.

So three IoU figures were computed over two records, on the wrong imagery, against hand-drawn
boxes, one of which is duplicated. **These are not benchmark results and must never appear in the
paper or a slide as VRSBench numbers.** This is most likely an honest drift — a smoke-test fixture
that got promoted to "results" when the docs were written — but the effect on credibility if a
reviewer checks is severe.

**Second problem:** `scripts/evaluate_grounding_vrsbench.py` **cannot read real VRSBench.** It looks
for `rec["bbox"]` (line 226) and `rec["query"]`; the official file uses `ground_truth` as the string
`{<x1><y1><x2><y2>}` in **percentage** coordinates and `question` for the text. `normalize_gt_box`
handles xyxy/xywh/normalized floats only. The harness needs a VRSBench adapter before it can
produce a real number.

**Action:** real data is now on disk (`datasets/raw/`): LEVIR-CD test 2,048 pairs + val, and
VRSBench 16,159 referring / VQA / captioning eval records. Delete the fake sample from the docs'
results section, adapt the harness, re-measure, and only then publish numbers. Tracked in
`phases.md` P2.

### D-116 · Router accuracy measured at 74.9% — declarative referring expressions misroute
Date 2026-09-04 · Session 2 · Evidence: `results/evaluations/`, `PPT_RESULTS.md` §3
All 16,159 VRSBench referring queries are grounding queries by construction, which makes them a
clean test of `IntentClassifier`. Result: **12,101 correct (74.9%), 4,058 misrouted to
`single_image_vqa` (25.1%)**.
**Root cause:** grounding intent is detected via an imperative verb ("find", "locate", "where is")
*or* a noun from the hardcoded `OBJECT_PATTERNS` list. VRSBench phrases referring expressions
declaratively — "The baseball diamond **is located** in the left portion of the image" — which has
no imperative verb, and `baseball diamond`, `stadium`, `windmill`, `ground-track-field` are all
absent from the noun list. The query falls through to the terminal `single_image_vqa` default.
**Fix (not yet applied):** extend `OBJECT_PATTERNS` to the DOTA/VRSBench class vocabulary and add
declarative patterns (`is located`, `is positioned`, `is situated`, `is placed`). Should recover
most of the 25%. Must be re-measured after, not assumed.
**Why this matters beyond accuracy:** a misrouted grounding query goes to the VQA model, which is
the unadapted BLIP (D-101) — so it returns prose instead of a box, and the evaluation scores zero
for that record. Router accuracy multiplies directly into grounding score.

### D-114 · Dependencies are unpinned, and `transformers` resolved to a major version the code has never seen
`backend/requirements.txt` uses `>=` with **no upper bounds**. On a clean install today that
resolves `transformers>=4.41.0` to **5.16.1** — a major release with breaking API changes — plus
`torch 2.14.0+cu130`. The adapters were written against transformers 4.x. Any adapter using
`BlipProcessor`, `AutoModel` loading conventions, or generation kwargs may break on 5.x, and the
failure will look like a model bug rather than a dependency bug.
This is the same class of problem as D-108 (`aiosqlite` missing): the requirements file does not
describe an environment anyone has actually tested. Fix: pin the whole set with `==` (or a lockfile)
from a known-green run — but do that **after** the baseline, so we pin what works rather than what
we hope works.

### D-108 · `aiosqlite` is missing from `requirements.txt` — reproducibility gap
`db/session.py:34` returns `sqlite+aiosqlite:///results/satquery_test.db` whenever the test
environment is detected, so **the entire test suite depends on `aiosqlite`** — and it is not in
`backend/requirements.txt` (which lists only `asyncpg` and `psycopg2-binary`). A clean
`pip install -r backend/requirements.txt` therefore cannot run the tests. This means the
"104/104 passing" figure was produced in an environment with packages not captured by the
requirements file. Fix: add `aiosqlite` (and verify `greenlet`, which SQLAlchemy async needs) —
but do it as an explicit commit, since it changes the reproducibility story in the docs.

### D-109 · `EvidenceAdjudicator` is dead but tested — duplicate of `ConsistencyChecker`
`evidence/adjudicator.py` (244 lines) has its own model dossier
(`docs/models/EVIDENCE_ADJUDICATOR.md`) and 3 passing tests, but **nothing in the pipeline calls
it**. `AgentController` uses `ConsistencyChecker.check_change_consistency` instead
(`controller.py:167`). Two parallel implementations of "does the text answer agree with the spatial
evidence?", one of which never runs.
Options: wire the adjudicator in and retire `ConsistencyChecker` (it looks like the more developed
design and it is already documented as a contribution); or delete the adjudicator and keep the
simple checker. **Do not leave both** — a reviewer who reads the dossier and then greps for the call
site will find nothing, which is worse than either choice. This is a design call, so it is *not*
part of S0's mechanical deletion.

### Dead-code sweep result
A full unreferenced-module scan across `backend/app` found **no other orphaned modules** beyond the
S0 set (the only two hits, `db/migrations/env.py` and `versions/001_initial_schema.py`, are invoked
by Alembic rather than imported). The dead weight is concentrated exactly in the planner/router and
`*Workflow` class layers, which confirms the S0 scope is both correct and complete.

These are recorded here rather than acted on, because they are architecture-level calls that the
team — not the AI — should make. See `rules.md` §5 for the authority protocol.

### D-101 · The RS-adaptation requirement is currently unmet — **BLOCKER**
`models/general_rs_vlm.py` loads `Salesforce/blip-vqa-base`, a generic VQA model. The problem
statement says: *"A generic LLM or VLM without remote-sensing adaptation will not satisfy the
requirements."* Requirement #1 is mandatory. Options to weigh:
- **(a)** LoRA fine-tune BLIP on RSVQA / BigEarthNet captions — cheapest, uses the vendored stack,
  directly satisfies "fine-tuned or otherwise adapted using BigEarthNet or other open source data".
- **(b)** Swap to RemoteCLIP-conditioned VQA — the adapter and checkpoint already exist and
  RemoteCLIP *is* RS-adapted, but it is a retrieval/similarity model, not generative.
- **(c)** Get GeoChat-7B actually running — highest fidelity, needs ~14 GB VRAM and a non-FAT32 disk.
- **(d)** Fine-tune a small VLM head on BigEarthNet-derived Q/A pairs — most defensible for a paper
  because we then own the adaptation and can ablate it.
Recommendation: **(a) now for the deadline, (d) for the paper.**

### D-102 · The Optical-SAR fusion head is untrained — **BLOCKER**
`docs/SATQUERY_AI_MODEL_DATA_SETUP.md` §F creates `checkpoints/optical_sar/satquery_fusion.pth` by
saving a freshly constructed `CrossAttentionFusionNet` — i.e. **random weights**. It references
`scripts/train_optical_sar_fusion.py`, which **does not exist in the repo**. Consequence: the 19
land-cover classes, `surface_roughness` and `builtup_index` reported by `run_optical_sar` are noise
formatted as findings. This directly contradicts the zero-fabrication claim (D-010) and would not
survive a judge asking "how was this trained?".
Options: train the head on BigEarthNet (which is co-registered S1+S2 and is the prescribed dataset —
this also helps D-101); **or** replace the learned head with an explicit, documented deterministic
analysis (backscatter thresholds + NDWI/NDBI agreement) labelled `HEURISTIC_ANALYSIS`; **or** disable
the capability and return `NOT_CONFIGURED`. Anything is better than shipping random weights.

### D-103 · `fusion.py` calls a method that does not exist
`fusion.py:141` and `:155` call `model_registry.get_model("dofa")`. `ModelRegistry` defines
`get_adapter`, not `get_model` → `AttributeError` on that branch. Worse, lines 146/160 fall back to
`torch.randn(1, 768)` — fabricated features. Straightforward fix, but it should land together with
the D-102 decision so we don't polish a path we may delete.

### D-104 · Two capabilities route to nowhere
`multispectral_analysis` and `sar_analysis` are matched by `CapabilityMatcher` but have no branch in
`build_dag_for_capability()` → fallback DAG (`inspect_raster → generate_report`) and
`TaskType.UNSUPPORTED`. A user asking "compute NDVI for this scene" gets a report with no index.
The `visualization/indices.py` engine that would answer it is only reachable through the separate
`/api/analysis/...` endpoints. Fix: add DAG branches plus the missing tools
(`compute_spectral_indices`, `render_composites`, `render_sar_polarization`).

### D-105 · Capability `required_tools` are never verified
`DependencyChecker.verify_plan_dependencies` iterates **DAG nodes**, not `capability.required_tools`.
So capability definitions list tools that do not exist in `TOOL_REGISTRY` and nothing complains.
Fix: validate `required_tools` at registry construction time and fail loudly at boot.

### D-106 · BigEarthNet adapter is orphaned
Registered in `ModelRegistry.ADAPTER_CLASSES`, referenced by no capability, invoked by no DAG.
Given that BigEarthNet is the *prescribed adaptation dataset*, leaving it unused is both a
functional and a rhetorical loss.

### D-107 · Config inconsistencies to reconcile
- `configs/models.yaml` sam2: `checkpoint_path: sam2_hiera_base_plus.pt`, `config_path: sam2_hiera_b+.yaml`,
  `version: "Hiera-Base"` — but `model_id: facebook/sam2.1-hiera-small` and every doc says Hiera-Small.
- `models.yaml` dofa: `DOFA_ViT_base_e100.pth`; `models/registry.py` metadata says `DOFA_ViT_large_e100.pth`.
Pick one truth per model and make the YAML authoritative.
