# QNA — Change Verification Record

Replaces the interactive quiz gate. Every **major** change to this codebase gets an entry here:
the questions a reviewer (or an ISRO mentor, or a paper reviewer) would ask, and the answers,
written down.

**Why this format:** a live quiz is gone the moment it's answered. A written Q&A survives, can be
read the night before a viva, onboards Ayushman and the frontend team without a meeting, and turns
into the "defence" section of the paper. It also forces the answer to be *written*, which is a
harder test than recognising a correct option in a list.

**What counts as major** (same trigger as before): anything in `agent/`, `orchestration/`, or
`models/registry.py` · changes spanning more than 3 files · model or dataset swaps · schema or
migration changes · anything that will be claimed in the paper.
**Not major:** typos, comments, docs, formatting, single-file localised fixes, added tests.

**How to use it**
1. Before merging a major change, the AI writes the entry: 4–6 questions covering *mechanism,
   rationale, blast radius, verification, defence* — with answers.
2. You read it. Anything that doesn't match your understanding is a flag: either the change is
   wrong, or the explanation is, and both are worth catching before merge.
3. Mark the entry **Reviewed** with your initials and the date once you can restate it unaided.
   Until then it stays **Pending review** and the change does not merge.

---

## Index

| ID | Change | Date | Status |
|---|---|---|---|
| [Q-001](#q-001--s0-removal-of-the-dead-planner-router-and-workflow-class-layers) | S0 — removal of the dead planner, router and workflow-class layers | 2026-09-04 | Pending review |
| [Q-002](#q-002--d-113-disabling-asyncpgs-prepared-statement-cache-behind-supabases-pooler) | D-113 — asyncpg prepared-statement cache behind Supabase's pooler | 2026-09-04 | Pending review |

---

## Q-001 · S0 — removal of the dead planner, router and workflow-class layers

**Branch:** `refactor/s0-remove-dead-layers` · **Scope:** 8 files deleted, 6 edited, 493 deletions
**Result:** 120 → 112 tests; 108 → 100 passing; failure list byte-identical to baseline.

### 1. Mechanism — what was really doing the planning, and how do we know the old planner was unreachable?

`AgentController.__init__` assigned `self.planner = RuleBasedPlanner()`, and **`self.planner` was
never read again anywhere in the class.** The actual planning happens at `controller.py:71`, which
calls `AdvancedWorkflowPlanner.plan(state)` — a *classmethod* on
`orchestration/planner.py`, reached directly through the import, never through the instance
attribute.

Unreachability was established three ways, not by reading alone:
1. `grep -n "self.planner" backend/app/agent/controller.py` → **one hit, the assignment**. A value
   that is written once and never read is dead by definition.
2. A full import map of `backend.app.agent.*` across `backend/`, `tests/` and `scripts/` showed
   `planner.py` imported only by `controller.py` (that dead line), `agent/__init__.py`
   (a re-export), and `tests/test_agent.py`. `router.py` only by `planner.py`, `__init__.py`, and
   `tests/test_router.py`. Nothing outside that closed circle.
3. An unreferenced-module sweep over all of `backend/app` found no *other* orphaned modules, which
   told us the dead code was confined to this cluster rather than being the tip of something larger.

The distinction that matters: "rarely used" would still show a live call site somewhere in the
execution path. There was none — the only consumers were the module's own siblings and its own tests.

### 2. Rationale — why did deleting five `*Workflow` classes remove no capability?

Because **they were never the execution mechanism.** Work is executed by `TOOL_REGISTRY`
(`agent/registry.py:422`) — a dict of 14 named callables. The controller walks `plan.steps` and
calls `SafeToolExecutor.execute_tool(name, state)` for each. The DAG in
`dependency_graph.py` emits *tool names*, not workflow classes.

Four of the five classes were literally this:

```python
class SingleVQAWorkflow(BaseWorkflow):
    async def execute(self, state): return await agent_controller.run_pipeline(state)
```

A one-line delegation back to the controller that invoked them. Nothing constructed them —
`grep "Workflow()"` across `backend/app` returned nothing, and no `.execute()` call site existed.
They were an abstraction someone designed, wired the imports for, and then routed around.

### 3. Blast radius — why keep `run_grounding_pipeline` but delete `GroundingWorkflow`?

They lived in the same file, `workflows/grounding.py`, but only the class was dead.
`run_grounding_pipeline` is genuinely live with **two non-test callers**:

- `agent/registry.py:119` — the `run_grounding` tool, i.e. the real production path
- `scripts/evaluate_grounding_vrsbench.py:32` — the benchmark harness

Deleting the module would have broken the entire grounding capability *and* the only grounding
evaluation script we have — which matters doubly because V4's IoU is still unmeasured and that
script is how we'll measure it. So the edit truncated the file at line 329 (dropping the class and
its `BaseWorkflow` import) and kept everything above it. `GroundingWorkflow.run()` was itself just
`return run_grounding_pipeline(...)`, so nothing of substance was in the class.

### 4. Verification — why is 108 → 100 a pass, not a regression?

Because the count dropping is *expected* and the composition is unchanged. Eight tests were removed
by design: `test_router.py` (6, all on `DeterministicRouter`), one planner test in `test_agent.py`,
and one in `test_grounding_workflow.py` that exercised the deleted class. 108 − 8 = 100. Predicted
before running, matched after.

The check that would have caught a hidden regression is **diffing the failure lists**, not comparing
the totals:

```
grep "^FAILED" baseline.txt | sort > b.txt
grep "^FAILED" after_s0.txt | sort > a.txt
diff b.txt a.txt        # empty
```

A raw count can hide a swap — one test starts failing while another stops — and would still show
"100 passed". The empty diff proves the same 11 tests fail for the same reasons and no previously
passing test moved. Backed by `compileall` exit 0, a grep for all 9 deleted symbols returning
nothing, and an import smoke test confirming 13 capabilities and 14 tools still register.

### 5. Defence — "you deleted the routing layer from an agentic system"

We deleted a *dead* routing layer and kept the live one. The system has two: `DeterministicRouter`
(keyword matching, never invoked) and the `orchestration/` pipeline that actually runs —
`InputAnalyzer` → `IntentClassifier` → `CapabilityMatcher` → `DependencyGraph`. The second is
strictly more capable: it extracts structured query entities, emits a `routing_confidence`, detects
ambiguous queries and proposes clarifications, and produces a dependency DAG the problem statement
can be audited against.

Keeping both was the actual risk. A reader — or a reviewer — encountering `agent/planner.py` first
would reasonably conclude that keyword matching is our contribution, which undersells the system and
invites exactly the criticism the question implies. Removing it makes the real router unambiguous.
The proof it was dead is in the tests: the routing behaviour is unchanged, because the deleted code
never ran.

**Status: Pending review** — sign off here once you can restate answers 1, 2 and 4 unaided.

---

## Q-002 · D-113 — disabling asyncpg's prepared-statement cache behind Supabase's pooler

**File:** `backend/app/db/session.py` · **Scope:** 1 file, +42 lines

### 1. Mechanism — what actually failed?

`DATABASE_URL` points at `…pooler.supabase.com:6543`. Port 6543 is Supabase's **transaction-mode**
pooler (pgBouncer). asyncpg prepares every statement server-side under a generated name
(`__asyncpg_stmt_1__`, …). Transaction pooling rebinds each transaction to whichever backend
connection is free, so a name prepared by one client collides with another's on the same backend:

```
asyncpg.exceptions.DuplicatePreparedStatementError:
prepared statement "__asyncpg_stmt_1__" already exists
HINT: pgbouncer with pool_mode set to "transaction" or "statement"
      does not support prepared statements properly.
```

`statement_cache_size=0` makes asyncpg send each query unprepared;
`prepared_statement_cache_size=0` disables SQLAlchemy's own dialect-level cache. Cost is a little
per-query planning time, irrelevant at our volume.

### 2. Rationale — why fix the code instead of just editing `.env` to port 5432?

Port 5432 does work (proven — see below). But 6543 is the URL Supabase displays by default, so a
config-only fix breaks again the first time anyone copy-pastes from the dashboard. The code fix is
correct on either port.

### 3. Blast radius — why not just always disable the cache?

Because it would cost performance on direct/session-mode connections that don't need it. The
heuristic matches only `:6543` or `pgbouncer` in the host — deliberately **not** `pooler.` alone,
since the same pooler hostname on `:5432` is session mode and handles prepared statements fine
(configuration C below). `SATQUERY_DB_POOLER=1|0` overrides when the guess is wrong.

### 4. Verification — how do we know?

A three-way probe against the live database:

| Configuration | Result |
|---|---|
| A · as-shipped (`:6543`, no `connect_args`) | **FAIL** — `DuplicatePreparedStatementError` |
| B · `:6543` + `statement_cache_size=0` | PASS |
| C · `:5432` session mode, unchanged code | PASS |

Then re-verified through `get_async_engine()` — the app's own factory, not a hand-rolled engine —
with 10 parameterised queries on fresh connections, 30 distinct statements on one connection, and
16 concurrent pooled queries.

### 5. Defence — why did nobody notice this before?

**Because the first query succeeds.** In configuration A, `SELECT version()` returned PostgreSQL
17.6 before anything broke. `/api/health` would pass, the app would report healthy, and it would
fail later under real query load. That is the failure mode most likely to appear during a live demo
and least likely to appear during a smoke test — which is the argument for probing with repeated
and concurrent queries rather than a single connectivity check.

**Status: Pending review**
