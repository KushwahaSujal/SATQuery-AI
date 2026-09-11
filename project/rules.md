# Rules — Working Agreement

Binding for AI-assisted work on this repo. Human instructions override these; these override
default AI behaviour.

**Scope note:** natsu and Ayushman own the **backend**. Frontend, deck, and video are owned by the
rest of the team. Do not refactor `frontend/` unless asked — coordinate instead.

---

## 1. Non-negotiables

1. **Never fabricate a number.** No invented accuracies, latencies, parameter counts, or dataset
   sizes — in code, in docs, in the deck. If a metric is not in a results file or a run log, it does
   not get written down. Write `NOT MEASURED` instead.
2. **Never fabricate data.** No synthesised spectral bands, no `torch.randn` standing in for real
   features, no placeholder predictions rendered as findings. If an input is missing, return a
   structured `*_NOT_AVAILABLE` / `NOT_CONFIGURED` error explaining why.
3. **A random-weight model is not a model.** Never ship or describe an untrained network as
   producing predictions. (This rule exists because we currently violate it — see `decisions.md` D-102.)
4. **Every claim in a doc must be traceable** to a file path, a line, or a results artifact.
5. **No secrets in git.** Credentials live in `.env` only. `.env.example` stays credential-free.
6. **No heavy binaries in git.** Checkpoints, datasets, `node_modules`, `results/` stay ignored.

---

## 2. Libraries

### Use
`fastapi` · `pydantic` v2 · `sqlalchemy[asyncio]` + `asyncpg` · `alembic` · `torch` / `torchvision` ·
`transformers` · `timm` · `safetensors` · `open-clip-torch` · `numpy` · `scipy` · `pillow` ·
`tifffile` · `pyproj` · `shapely` · `opencv-python-headless` · `matplotlib` · `reportlab` · `pyyaml` ·
`psutil` · `pytest` + `pytest-asyncio`.

### Ask before adding
Anything requiring a system-level binary (**rasterio/GDAL**, `geopandas`) — the code deliberately
carries pure-Python fallbacks so the project installs on a fresh Windows laptop. Anything that pulls
a second deep-learning framework. Anything with a non-permissive licence (this goes to ISRO).

### Avoid
- **`opencv-python`** (non-headless) in backend — use `opencv-python-headless`; the GUI variant
  breaks in containers.
- **Hosted LLM APIs in the request path.** The router is deterministic by design (`decisions.md`
  D-002) and the judged environment may be offline.
- **`requests`** for new code — `httpx` is already a dependency and is async-capable.
- **Pandas** unless there is a genuine tabular workload; numpy covers what we do.
- **New state stores** (Redis, Celery). The in-process cache and background tasks are sufficient
  at this scale; adding infra costs more demo reliability than it buys.

---

## 3. Code conventions

- **Adapters:** every model subclasses `BaseModelAdapter` and implements `load_model`,
  `validate_inputs`, `predict`. `predict` returns a `ModelResult` — never a bare dict, never a
  fabricated result. Weights load lazily inside `load_model`, never in `__init__`.
- **Tools:** every entry in `TOOL_REGISTRY` is `Callable[[AgentState], None]` and mutates state in
  place. A new tool must be (a) added to `TOOL_REGISTRY`, (b) referenced by a DAG node, **and**
  (c) listed in the owning capability's `required_tools`. All three, or it is invisible or dead.
- **Capabilities:** adding one means touching four files —
  `capability_registry.py` (definition) → `matcher.py` (routing rule) →
  `dependency_graph.py` (DAG branch) → `planner.py::to_legacy_workflow_plan` (TaskType mapping).
  Skipping any of the four produces the silent-fallback bug in `decisions.md` D-104.
- **Config:** no magic numbers in code. Thresholds, weights and paths go in `configs/*.yaml` and are
  read through `settings`. Env vars override in `Config._apply_env_overrides`.
- **Preprocessing:** replicate each checkpoint's *original training* preprocessing exactly, and
  write a test asserting output sanity — not merely that it didn't crash (`decisions.md` D-011).
- **Paths:** `pathlib.Path`, resolved against `settings.root_dir`. Never `os.path` string joins.
- **Logging:** `from backend.app.logging import logger`. Never `print` in `backend/app/`.
- **Typing:** annotate public functions. Pydantic models for anything crossing the API boundary.

---

## 4. Error handling

- Raise from the `SatQueryException` hierarchy in `backend/app/exceptions.py`
  (`InvalidInputError`, `ModelUnavailableError`, `InferenceError`, `WorkflowError`,
  `CapabilityRequirementError`). Each carries `code`, `message`, `details`, `status_code` and is
  rendered by the handlers in `main.py` as `{"error": {...}}`.
- **Fail fast before execution, degrade gracefully during it.** Missing checkpoints, wrong input
  counts and unregistered tools must be caught by `DependencyChecker` *before* any model loads. Once
  running, a missing optional model should append a `warning` and continue (as `run_change_vqa`
  does), not abort.
- **Never swallow an exception silently.** `_safe_db_op` is the one sanctioned exception and it logs
  a warning. Do not copy that pattern into the model or evidence paths.
- Every user-facing error names **what** failed, **why**, and **what to do**. `ModelUnavailableError`
  printing the exact expected checkpoint path is the standard to match.

---

## 5. AI harnessing boundaries

### The AI may do without asking
Read anything. Run tests, linters, smoke scripts. Write docs and comments. Add tests. Fix an
obvious, localised bug **with a `decisions.md` entry**. Draft a plan or a diff for review.

### The AI must ask first
- Any change to `agent/`, `orchestration/`, or `models/registry.py` — the orchestration layer is the
  research contribution; it does not get silently rewritten.
- Adding, removing, or swapping a model or a dataset.
- Schema or migration changes.
- Anything in `frontend/` (another team owns it).
- Adding a dependency.
- `git push`, PRs, force-anything, deleting files, rewriting history.
- Editing `docs/SATQUERY_AI_MASTER_DOCUMENTATION.md` (the team's public artifact).

### The AI must never
Commit secrets or weights · invent benchmark numbers · mark something "verified" that has not been
run · delete uncommitted work without `git status` first · claim a test passed without showing the
output.

### Definition of done
Code compiles → relevant tests pass **with output shown** → `decisions.md` entry written →
`flow.md` session log updated → `memory.md` refreshed. Nothing is "done" until all five hold.

---

## 6. The change transcript — `qna.md` is a record, not a gate

> `qna.md` is a **stenographic transcript** of every major change: the questions a reviewer would
> ask, and the answers, written down as the change is made. It records. It does not approve.

**Revised 2026-09-11.** The previous version of this section held a change in **Pending review**
until the author signed off, and blocked the merge until they did. **That gate is retired.** There
is no pending state, no sign-off, no held merge, no gated push. Entries are recorded and the work
continues.

**Recorded:** anything in the "must ask first" list above, plus any change spanning >3 files,
touching the routing/capability logic, altering a model contract, or changing anything that will be
claimed in the paper or on stage.

**Not recorded:** typos, comments, docs, formatting, single-file localised fixes, added tests.

**Procedure**

1. The AI writes the entry at the time of the change — 4–6 questions with answers, covering:
   - *Mechanism* — what does this code actually do, step by step?
   - *Rationale* — why this approach over the alternative that was rejected?
   - *Blast radius* — what else breaks if this is wrong?
   - *Verification* — how do we know it worked? What specific check proves it?
   - *Defence* — how do you answer a mentor or reviewer who challenges this?
2. Answers must be specific: file paths, line numbers, commands, measured numbers. "It works
   because it's cleaner" is not an answer.
3. The change proceeds. Recording the entry never blocks a commit, merge or push.
4. The author reads entries whenever they like. If one contradicts their understanding, that is
   still worth catching — it just happens on their schedule now, not the merge's.

**The four properties that make it a transcript**

- **Contemporaneous** — written as the change happens, not reconstructed later.
- **Append-only** — a past entry is never edited or deleted. If it turns out wrong, file a new entry
  that supersedes it and cross-link both ways. The mistake stays in the record; that is the point.
- **Non-blocking** — see above. The record has no veto.
- **Verbatim on the facts** — measured numbers as measured, including the unflattering ones. A
  transcript that launders results is worthless as a defence, and this project's credibility rests
  on `pre-demo.md` being honest.

**Requesting an official copy.** Ask for "an official copy of the transcript" and you get a clean
standalone extract — by entry ID, date range, topic, or the whole record — with each entry's date
and the commit it describes. Extracted, not re-argued; anything missing is stated plainly.

**Why written rather than interactive:** a live quiz evaporates once answered. `qna.md` survives —
it can be read the night before a viva, onboards teammates without a meeting, and becomes the
defence section of the paper.

Underlying rationale is unchanged: this gets defended live in front of ISRO mentors and later
submitted as a paper. Code the author cannot explain is a liability regardless of whether it works.
The record exists so the explanation exists — not so that someone has to sign a form first.

---

## 7. Git

- Branch per unit of work: `feat/`, `fix/`, `docs/`, `exp/`. Never commit straight to `main`.
- Commit messages state **what changed and why**, imperative mood.
- `git status` before any destructive command; stash or commit untracked work first.
- Review what a broad `git add` staged before committing.
- Never push without being asked.
