# QNA — Change Transcript

A **stenographic record** of every major change to this codebase: the questions a reviewer (or an
ISRO mentor, or a paper reviewer) would ask, and the answers, written down as the change is made.

It **records; it does not approve.** There is no pending state, no sign-off, and no change is ever
held waiting on this file.

> **Protocol change, 2026-09-11.** This file previously ran an approval gate: entries started as
> *Pending review* and the change did not merge until the author signed off. That gate is retired
> (`rules.md` §6). The five entries below were migrated from *Pending review* to *Recorded* on that
> date — their content is unchanged, only the retired status field was converted. Nothing about
> them was re-argued or rewritten.

**Why this format:** a live quiz is gone the moment it's answered. A written record survives, can be
read the night before a viva, onboards Ayushman and the frontend team without a meeting, and turns
into the "defence" section of the paper. It also forces the answer to be *written*, which is a
harder test than recognising a correct option in a list.

**What gets recorded:** anything in `agent/`, `orchestration/`, or `ml/registry.py` · changes
spanning more than 3 files · model or dataset swaps · schema or migration changes · anything that
will be claimed in the paper or on stage.
**Not recorded:** typos, comments, docs, formatting, single-file localised fixes, added tests.

**The rules of the record**

1. **Contemporaneous** — written as the change happens, not reconstructed afterwards.
2. **Append-only** — no entry is ever edited or deleted. If one turns out to be wrong, a new entry
   supersedes it and both are cross-linked. The mistake stays in the record; that is what makes
   this a transcript and not a brochure.
3. **Non-blocking** — recording an entry is never a reason to pause a commit, merge or push.
4. **Verbatim on the facts** — measured numbers as measured, including the unflattering ones.

**Requesting an official copy.** Ask for "an official copy of the transcript" and you get a clean
standalone extract — by entry ID, date range, topic, or the whole record — with each entry's date
and the commit it describes. Extracted, never re-litigated; anything missing is stated plainly.

---

## Index

| ID | Change | Date | Record |
|---|---|---|---|
| [Q-001](#q-001--s0-removal-of-the-dead-planner-router-and-workflow-class-layers) | S0 — removal of the dead planner, router and workflow-class layers | 2026-09-04 | Recorded |
| [Q-002](#q-002--d-113-disabling-asyncpgs-prepared-statement-cache-behind-supabases-pooler) | D-113 — asyncpg prepared-statement cache behind Supabase's pooler | 2026-09-04 | Recorded |
| [Q-003](#q-003--video-and-visualization-tables-migration) | Video & visualization tables migration (f1b7463d221d) | 2026-09-07 | Recorded |
| [Q-004](#q-004--colour-reaches-the-detector-prompt) | Colour reaches the detector prompt; verb stoplist; overlay colour fidelity | 2026-09-07 | Recorded |
| [Q-005](#q-005--absent-colours-report-not_applicable) | Absent colours report NOT_APPLICABLE (colour gate) | 2026-09-07 | Recorded |
| [Q-006](#q-006--retiring-the-approval-gate-qnamd-becomes-a-transcript) | Retiring the approval gate; `qna.md` becomes a transcript | 2026-09-11 | Recorded |
| [Q-007](#q-007--changeformer-ayushmans-epoch-20-checkpoint-on-vendored-upstream-architecture) | ChangeFormer — Ayushman's epoch-20 checkpoint on vendored upstream architecture | 2026-09-14 | Recorded |
| [Q-010](#q-010--gpu-out-of-memory-recovery-for-resident-models) | GPU out-of-memory recovery for resident models | 2026-09-14 | Recorded |
| [Q-011](#q-011--geotiff-georeferencing-without-rasterio-and-geojson-area-of-interest-input) | GeoTIFF georeferencing without rasterio; GeoJSON area-of-interest input | 2026-09-14 | Recorded |
| [Q-008](#q-008--two-agent-detection-verification-backtracking-and-re-evaluation) | Two-agent detection: verification, backtracking and re-evaluation (stills + video) | 2026-09-14 | Recorded · superseded in part by Q-009 |
| [Q-009](#q-009--two-agent-detection-attribute-queries-are-labelled-not-backtracked) | Two-agent detection: attribute queries are labelled, not backtracked (supersedes Q-008 rule) | 2026-09-14 | Recorded |

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

**Recorded** 2026-09-04. (Migrated from the retired *Pending review* gate on 2026-09-11.)

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

**Recorded** 2026-09-04. (Migrated from the retired *Pending review* gate on 2026-09-11.)


---

## Q-003 · Video and visualization tables migration

**Revision:** `f1b7463d221d_add_video_and_visualization_tables` · revises `002_enable_rls`
**Scope:** 1 migration file. Creates `videos`, `video_frames`, `video_flags`,
`visualization_layers`; enables RLS on all four.
**Result:** `GET /api/video/{job_id}` went from HTTP 500 to 200; browser shows `1 events`.

### 1. Mechanism — the POST returned 200 with a correct flag while the DB write failed. Where was the result lost?

`POST /api/video/analyze` computes the whole result in memory and returns it directly from
`VideoAnalysisWorkflow.execute()`. Persistence is wrapped in a `try/except` that logs a warning and
continues (`video.py`, "Database persistence for video job ... encountered error"), so a failed
write cannot fail the request. The response the caller receives is therefore correct and complete.

The loss happens at the *next* step. The frontend does not keep that response — it navigates to
`/video/{job_id}`, which calls `GET /api/video/{job_id}`, and that endpoint reads from the database.
With no `videos` table the read raised `UndefinedTableError` → HTTP 500 → the page fell back to its
default object, which hardcodes `status: "NO_DATA"` and `events: []`.

So the pipeline was correct end-to-end and the *handoff* was broken. Every API test in the session
passed because they read the POST response; only driving the browser exercised the GET.

### 2. Rationale — `ensure_db_tables()` already creates all ten tables. Why write a migration instead of calling it on startup?

`ensure_db_tables()` is `metadata.create_all()`. It creates what is missing and is fine for the
SQLite test database, which is disposable. Against the live Supabase database it is the wrong tool:

- It only ever *adds*. It cannot alter or drop, so the first time a column changes it silently does
  nothing and the schema diverges from the models with no error.
- It leaves no version record. `alembic_version` is how we know which schema a given deployment has;
  `create_all` writes nothing, so "which migration is this database on?" becomes unanswerable.
- It would run on every boot against production, which is a schema write executed by any process
  that happens to start — including a developer's laptop pointed at the shared database.

The migration also gave a safety property `create_all` cannot: `--autogenerate` **diffed the models
against the live database** and reported exactly four added tables and their indexes, with **no
changes to the existing seven**. That diff is the evidence the change is additive.

### 3. Blast radius — what breaks if the new tables go in without RLS, and what breaks if `downgrade()` runs later?

**Without RLS:** `002_enable_rls` enabled row-level security on all seven original tables, which on
Supabase is what stops the public `anon` key reading a table directly through PostgREST. Four tables
without it would have been the only openly readable ones in the database — and they hold job ids,
filenames and file paths. `_enable_rls()` in the migration closes that. Verified after applying:
all 11 tables report `rowsecurity = true`.

**If `downgrade()` runs:** it drops the four tables and every video job and visualization layer row
in them. The artifacts on disk under `results/` survive, so re-running an analysis regenerates the
records, but the history is gone. The FKs are `ondelete='CASCADE'` from `videos` to
`video_frames`/`video_flags`, so dropping in the generated order is safe; the risk is data loss, not
constraint failure.

### 4. Verification — what single check proves it worked, and why aren't the tests enough?

The check: `GET /api/video/{job_id}` returns **HTTP 200 with `flags` populated**, and the browser
page shows `Detected Events: 1 events`. Measured: `status COMPLETED`, one flag at 0.00–29.76s
labelled `vehicles`, score 0.8577.

The tests are not sufficient because `conftest.py` sets `SATQUERY_ENV=test`, which routes to
SQLite, and SQLite gets its schema from `ensure_db_tables()` — **so the test suite creates the
tables it needs and can never observe the missing migration.** The suite was 125 passed while the
production schema was broken. Any check that proves this class of bug has to run against Postgres.

### 5. Defence — why were four tables defined in code but never migrated, and does anything else have the same gap?

The models were added after `001_initial_schema` and no migration followed; `002_enable_rls` lists
its seven tables by hand, so it did not notice either. Nothing enforced the link, and the test suite
structurally could not (see 4).

How to check for recurrence: `alembic revision --autogenerate` and confirm it produces an **empty**
migration. A non-empty diff means the models and the database have drifted again. Run after applying
this one: the next autogenerate is clean. Making that a CI check is the durable fix.

---

## Q-004 · Colour reaches the detector prompt

**Scope:** `workflows/grounding_reasoner.py`, `video/flagger.py`, 3 test files.
**Result:** suite 125 → 129 passed. VRSBench mIoU 0.2755 → **0.2834**, R@0.5 0.29 → **0.31**
(same seed 42, same "all" subset, 100 records, 0 errors).

### 1. Mechanism — three colour queries returned the identical box. What exactly was thrown away?

`parse_v4_query` correctly extracted `color` for all three queries, then built the detector prompt
from `category` alone:

```
'spot a red car'    -> clean_prompt='spot car.'   color='red'
'spot a yellow car' -> clean_prompt='spot car.'   color='yellow'
```

Red and yellow produced a **byte-identical prompt**, so Grounding DINO received the same input and
returned the same box, at the same detector score (0.879 for both). Two separate defects:

1. `"spot"` was missing from the verb stoplist, so it survived into the category and the detector
   was asked for a nonexistent `"spot car"` class. `"find"` was in the list, which is why
   `find all vehicles` behaved correctly and masked the problem.
2. The colour was dropped from the prompt entirely.

### 2. Rationale — the reasoner already has a 0.15 `color` weight. Why change the prompt instead of relying on it?

Because that weight only *re-orders candidates that already exist*. `rank_v4_candidates` scores each
candidate and sorts; with one candidate per frame there is nothing to re-order, so the colour score
changes no outcome. It also cannot *reject* — the top-ranked candidate is selected regardless of how
poorly it scores.

Putting the colour in the prompt attacks it upstream, where Grounding DINO is genuinely
colour-conditioned. The measured difference: `"spot a red car"` now flags **14.40–18.24s**, and the
raw frame at index 228 is a red car. Previously it flagged 0.00–9.60s, boxing a white one.

### 3. Blast radius — this changes the prompt for every grounding query. What could regress?

Every query carrying a colour now sends a longer prompt, which is the main grounding path and is
scored on VRSBench — the number that goes in the paper. So it was re-measured on the same
seed/subset rather than assumed: **mIoU 0.2755 → 0.2834, R@0.5 0.29 → 0.31**, detection rate 0.86
unchanged, 0 errors. A small improvement, no regression.

Two existing tests asserted the old behaviour (`clean_prompt == "vehicle."` for a query containing
"white"). Those are **deliberate contract changes**, updated with a comment naming the reason rather
than quietly relaxed. The added stopwords (`spot, track, count, look, search, where, give, me, any`)
are a real risk if a target class is ever named by one of them; `ground-track-field` is safe because
it tokenises as a single hyphenated token.

### 4. Verification — what proves the colour is actually being used?

Three checks, in increasing strength:
1. `parse_v4_query('spot a red car')['clean_prompt'] == 'red car.'` and yellow differs — unit test
   `test_colour_reaches_the_detector_prompt`.
2. On the real video the three queries now return **different** flags and timestamps, where before
   all three returned 0.00–9.60s peaking at frame 60.
3. The decisive one: `"spot a red car"` peaks at frame 228, and the **raw decoded frame 228 is a red
   car**. Checked against the image, not the label.

### 5. Defence — a mentor asks "does it really understand colour?" What is the honest answer?

"It now conditions the detector on colour, and that is measurable: asking for a red car returns the
red car at 14.4–18.2s, asking for white returns the white ones. It is not a colour classifier — the
attribute is passed to an open-vocabulary detector that was trained to handle it."

And the limitation, unprompted: **asking for a yellow car — which is not in the footage — still
returns a confident flag at 0.79.** Grounding DINO ranks the best-matching region and has no "nothing
here" output. That is tracked as `pre-demo.md` §2.1a; RemoteCLIP verification was built for it and
measured unreliable, so open-set rejection remains open. The colour fix makes the *right* answer
right; it does not make the *absent* answer safe.

### 6. Why did the overlay show a red car as green?

`flagger.py` passed a numpy array into `create_change_overlay`, which routes arrays through
`render_display_rgb` — a 2–98 percentile per-band contrast stretch built for multi-band satellite
rasters. Applied to an ordinary video frame it recoloured the entire image. Passing the PIL image
takes the branch that skips the stretch. Guarded by `test_annotated_overlay_preserves_true_colour`,
which asserts a red region stays red when the mask is elsewhere.

The car still renders green *inside* the mask — that is the SAM 2.1 segmentation highlight,
`color_rgb=(0, 230, 150)` at alpha 0.45, working as designed. Worth reconsidering for colour demos,
since painting the target green hides the attribute being asked about.


---

## Q-005 · Absent colours report NOT_APPLICABLE

**Scope:** `schemas/video.py`, `workflows/video_analysis.py`, `api/v1/endpoints/video.py`,
`frontend/.../video/[jobId]/page.tsx`, `lib/types.ts`, 1 test file.
**Result:** suite 129 → **131 passed**. `spot a yellow car` on footage with no yellow car returns
0 flags and "Not applicable"; red and white still detect correctly.

### 1. Mechanism — the detector is confident about a car that isn't there. What actually separates present from absent?

Not confidence. Grounding DINO is open-vocabulary: it ranks the best-matching region in the frame
and has no "nothing here" output, so it always returns *something*. Measured over 32 frames of
`real_aerial_footage.mp4`, its score does not separate the two cases at all:

| colour | in clip? | max colour score | max detector score |
|---|---|---|---|
| red | yes | **1.000** | 0.895 |
| white | yes | **0.969** | 0.916 |
| yellow | no | 0.230 | 0.827 |
| blue | no | 0.260 | 0.906 |
| green | no | 0.209 | 0.892 |

Detector score spans 0.83–0.92 for present and absent alike. **Photometric colour score separates
them 4:1 with nothing in between**, so the threshold sits at 0.45, in clear air.

`color_score()` takes the mean RGB inside the candidate box and compares channels — for yellow,
`min(r,g) - b`. It already existed and was used only as a 0.15 *ranking* weight. Ranking cannot
reject: with one candidate, that candidate always wins regardless of score. The change makes it a
**gate** as well as a weight.

### 2. Rationale — RemoteCLIP verification was the obvious answer. Why pixel statistics instead?

RemoteCLIP was built first and measured unreliable: on a blank white image "a cat" scored 0.677, and
on a LEVIR-CD scene "a purple flying saucer" (0.430) outscored "buildings" (0.207). Both the
negation and distractor formulations failed in the same direction — out-of-distribution text lands
far from the remote-sensing cluster and softmax rewards it. It was reverted (`pre-demo.md` 2.1a).

Option B (making `reasoning_score` discriminative) was a genuine bug and is fixed, but for
modifier-free queries the weights normalise to detector-only, so it moved the gap the *wrong* way:
real 0.6802 → 0.4972 while nonsense only fell 0.7445 → 0.6134.

The pixel test wins on three counts: it is the only one that measurably separates the cases, it is
deterministic and inspectable (a mentor can be shown the mean RGB), and it reuses code already in
the repo rather than adding a model to the inference path.

### 3. Blast radius — what breaks if the threshold is wrong, and what does this NOT cover?

Too high and real detections are rejected — a dark red car under shadow could fall below 0.45.
`test_present_colour_still_detected` guards that with the red car at ~17.4s. Too low and it stops
rejecting. The measured margin (0.26 absent vs 0.97 present) means a mistake needs to be large;
`min_colour_score` is configurable per request if a clip needs it.

The gate only fires when the query names a colour the scorer knows (white, black, red, blue, green,
yellow, grey/silver). Every colourless query is untouched — `find all vehicles` behaves exactly as
before. **It does not do class-level rejection:** asking for a "purple flying saucer" parses no
known colour and still returns a flag, which is why `test_video_workflow_no_events_found` remains
`xfail`. That limit is stated in `pre-demo.md` rather than papered over.

### 4. Verification — what proves it, beyond the unit test?

Three layers:
1. `test_absent_colour_reports_not_applicable` — yellow on real footage → 0 flags,
   `NOT_APPLICABLE` in the reason.
2. `test_present_colour_still_detected` — red on the same footage still flags.
3. Driven through the browser with Playwright, which is the only layer that exercises persistence
   and rendering: red → `0:15.4 — red car` 0.89; white → 4 events; yellow → "**Not applicable** ·
   no yellow car found in this footage."

Layer 3 caught two things the tests could not: `GET /api/video/{job_id}` overwrote the reason with
"Retrieved 0 persisted event flags", and the UI printed a bare "No events detected". Both fixed.

### 5. Defence — a mentor asks how the system knows a colour is absent rather than just undetected.

"The detector proposes regions; it will propose one for any prompt. We then check the pixels inside
the proposed region against the requested colour — mean RGB, a fixed rule per colour, no model. On
this clip, colours that are present score 0.97–1.00 and colours that are absent score 0.21–0.26, so
we reject below 0.45 and report NOT_APPLICABLE with the reason. The detector's own confidence was
0.83–0.92 in both cases, which is exactly why we do not gate on it."

The honest caveat to volunteer: this covers colour attributes. A request for an object class that is
simply not present is still not rejected — that is open, and two approaches to it have already been
measured and rejected.

---

## Q-006 · Retiring the approval gate; `qna.md` becomes a transcript

**Recorded** 2026-09-11. First entry filed under the new protocol, and a record of the protocol
change itself.

### 1. Mechanism — what actually changed, file by file?

The *Pending review* state and the merge block are gone. Nine files:

- `~/.claude/CLAUDE.md` — **new**, global. Loads in every project, every session; defines transcript
  mode and declares it supersedes the old gate everywhere.
- `project/rules.md` §6 — rewritten from "The verification protocol" to "The change transcript".
  Step 3 used to read *"Entry starts as Pending review. The change does not merge while it is
  pending."* It now reads *"The change proceeds. Recording the entry never blocks a commit, merge
  or push."*
- `project/qna.md` — preamble rewritten; index column `Status` → `Record`; Q-001..Q-005 converted
  from `Pending review` to `Recorded` with their original dates.
- `project/memory.md` §5, `project/README.md:29`, `project/phases.md:42`, `project/tasks.md` — stale
  gate references updated; two "Quiz-gated" reasons dropped from the tasks ownership table.
- `project/pre-demo.md` — §1.4 changed from *"blocked on the `rules.md` §6 quiz"* to *"ready to
  start"*; §4b retitled from "Open quiz gates" to "Changes to record"; the `(quiz-gated)` marker
  removed from ordering step 3.
- `/home/natsu/dev/synth-veda/docs/rules.md` — the same cross-project rule, updated.

Claude's own memory files were updated to match: `feedback_major_change_gate.md` (global) rewritten,
`quiz-before-major-changes.md` deleted and replaced by `qna-transcript-mode.md`.

### 2. Rationale — why drop a gate that was working?

It was not working; it was queueing. Q-003, Q-004 and Q-005 were written on 2026-09-07 and still sat
*Pending review* on 2026-09-11, which meant a branch carrying a database migration, a working video
pipeline and the restored `frontend/src/lib` could not merge — while three new people were waiting
to start and the demo was days away. The gate's cost had become "a six-person team is blocked", and
its benefit — the author having a written explanation to defend — is fully preserved by the record
alone. The ceremony was separable from the value, so it was cut.

### 3. Blast radius — what is genuinely lost?

The pre-merge catch. Under the old rule, an entry whose explanation contradicted the code stopped
the merge, and that disagreement was the signal. Now a wrong change gets recorded and merged, and
the contradiction surfaces whenever someone reads the entry — which may be after it has shipped.

That is a real reduction in safety and is stated here rather than glossed. What offsets it: the
suite gates merges instead (132 passed, and Sujal's Track B1 puts that in CI so it gates on every
PR, not just on one machine), and the append-only rule means a wrong entry cannot be quietly tidied
up later — it stays in the record with its superseding entry beside it.

### 4. Verification — what proves the gate is actually gone?

`grep -rn -iE 'pending review|quiz' project/ backend/ README.md` returns two hits, both inside
sentences explaining why a *written* record beats a *live* quiz — the rationale that survived. No
hit asserts a pending state or a blocked merge. `project/qna.md` shows five entries marked
`Recorded`, none `Pending review`. The branch that the gate was blocking,
`refactor/s0-remove-dead-layers`, pushed at `a42b28e`.

### 5. Defence — a mentor asks whether you removed the check because it was inconvenient.

"Partly, and the inconvenience was the evidence. The check had two parts: writing down a defensible
explanation, and a sign-off ritual before merge. The first part is the one that makes the work
defensible, and we kept it in full — every major change still gets mechanism, rationale, blast
radius, verification and defence, written when the change is made, appended and never rewritten. The
second part was costing us a blocked branch and three idle engineers four days before a demo, and it
was never what made the explanation good. We also made the record strictly append-only at the same
time, so the trade is: we gave up a pre-merge stop, and in exchange the history can no longer be
edited after the fact. Test coverage now does the merge-gating, which is a better tool for it."

The caveat to volunteer: this only works if entries actually get written at the time. A transcript
nobody keeps is worse than a gate nobody passes.

---

## Q-007 · ChangeFormer — Ayushman's epoch-20 checkpoint on vendored upstream architecture

**Recorded** 2026-09-14. Uncommitted at time of recording — working tree on
`refactor/s0-remove-dead-layers` atop `977587d`. Closes `pre-demo.md` §1.3; resolves the finding in
commit `9620919`.

**Scope:** 5 files edited, 1 test file added · **Result:** LEVIR-CD test IoU **0.019 → 0.7385**
(all 2,048 pairs); suite 132 → **141 passed, 0 failed**.

### 1. Mechanism — what runs now, step by step?

1. **Checkpoint.** `checkpoints/changeformer/changeformer_v6_levir_levircd256_epoch20_best.pt`
   (492,691,833 bytes, sha256 `1d756d33…c63023f4b`), from Ayushman's
   `SatQuery_ChangeFormer_Package.zip`. The two zips he sent are byte-identical (all 11 files
   sha256-matched). Upstream trainer layout: `model_G_state_dict`, 373 tensors; 41,029,259 elements
   − 2,585 BatchNorm buffer elements = **41,026,674 parameters**, exactly his claim.
2. **Network.** `ml/adapters/changeformer/network.py` is replaced by the 15 definitions in
   `ChangeFormerV6`'s dependency closure, extracted by AST from `wgcban/ChangeFormer` @ `afd1b7ed`
   (MIT). Copied verbatim; the only change is `timm.models.layers` → `timm.layers`.
3. **Preprocessing** (`adapter.py::preprocess_changeformer_input`): RGB → [0,1] →
   `(x − 0.5) / 0.5`, the upstream `datasets/data_utils.py:18` contract. No resize.
4. **Forward** (`adapter.py::_forward_logits`): whole scene in one pass if both sides ≤
   `max_native_side` (1024, `configs/models.yaml`), else non-overlapping windows of that size.
   Each window is reflect-padded to a multiple of 32 and cropped back. Takes `outputs[-1]`, the
   full-resolution map of the 5 returned.
5. **Threshold** 0.435 from `configs/models.yaml`, frozen on the LEVIR-CD validation split per his
   `reports/frozen_validation_threshold.json`. Mask post-processing, quality flags and the
   `ModelResult` shape are unchanged, so downstream tools needed no edits.

### 2. Rationale — why vendor upstream instead of fixing the in-repo network, and why native resolution?

**Vendor, not fix:** the in-repo reimplementation loads all 373 tensors `strict=True` yet computes
something else. Head counts, for example, are `[1,2,5,8]` there vs `[1,2,4,8]` upstream, and head
count changes no tensor shape. Hunting for every such divergence would still leave a hand-written
network. Vendoring the exact source gives provable equivalence: max abs logit difference vs upstream
is **0.0 at all five output scales** on random input. Same checkpoint, 200 LEVIR-CD test pairs,
threshold 0.435 (`results/evaluations/changeformer_ab_upstream_vs_inrepo_levir200_20260914.json`):

| network / normalisation | IoU | F1 | AUC | identical-pair changed |
|---|---|---|---|---|
| upstream / [-1,1] | **0.7260** | **0.8413** | **0.9905** | **0.0%** |
| upstream / ImageNet | 0.3391 | 0.5065 | 0.9404 | ~0% |
| in-repo / [-1,1] | 0.0206 | 0.0403 | 0.6968 | 2.3% |
| in-repo / ImageNet *(old prod contract)* | 0.0189 | 0.0371 | 0.5093 | 3.2% |

**The checkpoint also mattered.** On 2026-09-07, upstream code with the *old* epoch-10 checkpoint
scored IoU 0.0737 (`pre-demo.md` §1.3). Neither the new weights alone nor the vendored network alone
would have fixed this.

**Native, not tiled or resized:** his contract says 256×256, but LEVIR-CD-256 is 1024 scenes cut
4×4, and the network has no positional embeddings. Measured on his 1024 scenes
(`…scale_strategy_levir1024_20260914.json`), raw-mask IoU:

| strategy | test_100 | test_101 | test_105 |
|---|---|---|---|
| native 1024 | **0.8075** | **0.6300** | **0.7913** |
| 256 tiles | 0.7883 | 0.5957 | 0.7671 |
| resize to 256 | 0.0891 | 0.0000 | 0.0000 |

Native wins on all three. Windowing is kept above 1024 because stage-4 attention (sr_ratio 1)
grows quadratically with area.

### 3. Blast radius — what breaks if this is wrong, and what does it not cover?

- **It is a building-change detector.** LEVIR-CD labels only building construction and demolition.
  On test_101 the largest false-positive cluster is bare construction ground: real change, but not a
  building. Claiming general land-cover change on stage would overstate it.
- **Out-of-domain accuracy is NOT MEASURED.** Every number here is LEVIR-CD: 0.5 m/px Google Earth
  RGB over Texas. Sentinel-2 at 10 m, multispectral, or seasonal pairs are untested.
- **Confidence is uncalibrated.** `ModelResult.confidence` is the mean change-probability over
  predicted pixels (0.875 on test_100). It comes from real logits, but it is not a calibrated
  probability of correctness.
- **Windowed path is less accurate than native:** 256 windows cost 0.02–0.03 IoU above. 1024 windows
  on >1024 scenes have seams and are NOT MEASURED against labels.
- **Precision/recall differ slightly from his report** with the adapter's morphological filter:
  P 0.8656 / R 0.8341 vs his 0.8608 / 0.8387, same IoU. Attributed to the filter, not isolated.
- Files: `network.py` (replaced), `adapter.py`, `config.py` (`ModelSpec.max_native_side`),
  `configs/models.yaml`, `ml/registry.py`. The old epoch-10 checkpoint stays on disk, unreferenced.

A latent bug found on the way: `models.yaml` already held `threshold: 0.5` and `input_size: 512`
*below* the new keys, and YAML keeps the last duplicate. The first comparison run silently used 0.5;
`AgentState` metadata exposed it. Both stale keys are removed.

### 4. Verification — what proves it?

- **Full LEVIR-CD test split through the production adapter:**
  `python scripts/evaluate_changeformer_levircd.py --limit 2048 --threshold 0.435` → IoU **0.7385**,
  F1 **0.8496**, 0.039 s/pair (`results/evaluations/changeformer_levircd_20260914T161054Z.json`).
  His report: IoU 0.7386, F1 0.8496.
- **His scenes, old vs new production path** (`…old_vs_new_levir1024_20260914.json`): IoU 0.1061 →
  0.8086, 0.0433 → 0.6289, 0.0546 → 0.7909 (filtered mask). The old path flagged ~68% of every scene
  as changed; ground truth is 5–11%.
- **Agent pipeline end-to-end** on test_100: `temporal_change_detection`, 6/6 tools succeed, 118,997
  px changed vs 118,843 ground truth, overlay + 5 masks + GeoJSON + report produced.
- **`tests/models/test_changeformer_accuracy.py`**, 9 tests: threshold is 0.435; IoU floor on 64
  LEVIR pairs; per-scene floors; identical pair → 0 changed px; windowed path; non-multiple-of-32
  sizes; mismatched sizes rejected. **Run against the old code with `git stash`: 8 of 9 fail.** The
  one that passes checks only shapes and finite values, the kind of test that let the broken
  network through before.
- `pytest -q` → 141 passed, 0 failed.

### 5. Defence — a reviewer asks: "it loaded strict=True before too. Why believe it now?"

"Because we stopped treating loading as evidence. Strict loading proves the parameter *names and
shapes* line up. It says nothing about the computation, and our old network proved that by loading
cleanly and scoring 0.019 IoU. What we trust now is three measurements. First, the vendored network
matches upstream's logits bit-for-bit. Second, the production adapter reproduces the checkpoint
author's held-out test score on all 2,048 LEVIR-CD pairs to four decimal places. Third, an identical
before/after pair produces exactly zero changed pixels. And we added tests that assert accuracy
rather than shapes, and confirmed they fail on the old code."

The caveat to volunteer: this is a building-change model, measured only on LEVIR-CD. Say that
before anyone asks what it does on Sentinel-2.

---

## Q-008 · Two-agent detection: verification, backtracking and re-evaluation

> **Superseded in part by [Q-009](#q-009--two-agent-detection-attribute-queries-are-labelled-not-backtracked)
> (same night, before commit).** The rule below (R3) backtracked on every query type; measured per
> query type it cost attribute queries 6.8 points of R@0.5. Q-009 keeps R3 for plain category queries
> and only labels attribute queries. The headline numbers in this entry are R3's and are replaced there.

**Recorded** 2026-09-14, written with the change on `refactor/s0-remove-dead-layers` atop `dee8e53`.
Plan: `project/plan-2026-09-14-agent-parity-geo.md` phases 1–2.

**Result, 300 present + 300 absent VRSBench queries:** absent-object queries that still return a box
**64.7% → 28.0%**; present-object R@0.5 **38.7% → 36.0%**, mIoU **0.349 → 0.327**. Road-footage
"find the airplane" **3 events → 0**, at the cost of **one real car event**.

### 1. Mechanism — what are the two agents, and what exactly decides?

- **Agent 1, detection:** Grounding DINO proposes boxes with a detector confidence; the existing V4
  reasoner ranks them by query attributes (position, size, colour, relations).
- **Agent 2, verification** (`backend/app/evidence/verifier.py`): RemoteCLIP (real weights: 302
  tensors, 0 missing) crops each candidate and scores it against the query label *and* a 32-label
  remote-sensing vocabulary. Synonym groups (car/vehicle/truck…) are collapsed by max before the
  softmax. Verdict: **verified** (query group in top 3) · **contradicted** (not top 3, best match is
  another object) · **unverified** (not top 3, best match is scene context: road, parking lot, trees…).
- **Deliberation** (`workflows/grounding.py`), walking the reasoner's order:
  - verified → **accept**;
  - contradicted → **backtrack** to the next candidate; the box is excluded from later passes;
  - unverified → hold the first one as a fallback and keep looking for a verified candidate;
  - nothing verified and nothing held → **re-evaluate**: rerun Grounding DINO at box threshold 0.15
    (from 0.25), and accept only a *verified* candidate from that pass;
  - still nothing → **NOT_FOUND**, no mask.
  Ordinal queries ("second from left") verify only the selected box, because another box would be a
  different answer.
- Every attempt is recorded in `evidence.metadata.agent_deliberation.attempts`, and in the trace as an
  `agent_deliberation` step. Each record holds both confidences, the verifier's rank and top match,
  and the decision. Answers name both agents' confidences; "with high precision" is gone.
- **Video** (`video/flagger.py`): after the persistence/score filters, up to 3 of an event's
  highest-detector-score frames are verified. The event is kept iff ≥1 frame is verified; that frame
  becomes the keyframe (preferring one with a SAM 2 mask). Dropped events are listed in `warnings`
  with detector score, frames confirmed and the verifier's best matches.
- Config: `configs/app.yaml` `agent_verification` (top_k 3, crop_pad 1.0, min_crop_side 96, relaxed
  threshold 0.15, 3 video frames, vocabulary, synonyms, context labels).

### 2. Rationale — why this rule and not a simpler one? What was tried and rejected?

Everything below was measured before it was wired in, and all files are in `results/evaluations/`.

1. **Raw similarity floor, rejected.** On 973 VRSBench ground-truth crops (40 per class), raw
   RemoteCLIP similarity separates true from wrong labels at AUC 0.928, but the scores sit in a narrow
   band (mean 0.278 true vs 0.207 wrong). Contrastive ranking gives AUC 0.955
   (`remoteclip_verifier_probe_20260914.json`).
2. **Hard top-k veto, rejected.** The implemented verifier accepts 78.3% of true labels and 5.5% of
   wrong ones. But it accepts only **42.5% of real vehicles**, the main demo class
   (`detection_verifier_vrsbench_20260914.json`). No crop/top-k setting fixes that: getting vehicles
   to 67% lets 27–35% of non-vehicles verify as "vehicle" (`detection_verifier_sweep_20260914.json`).
3. **Three verdicts instead of two.** A real vehicle that fails usually loses to *context*; a wrong
   label loses to *another object*. At pad 1.0 / min side 96
   (`detection_verifier_3way_20260914.json`):

   | crop vs label | verified | unverified | contradicted |
   |---|---|---|---|
   | true label | 80.7% | 6.2% | 13.2% |
   | wrong label | 6.3% | 9.6% | 84.2% |
   | real vehicle as "vehicle" | 55.5% | 25.5% | 19.0% |
   | real vehicle as "airplane" | 3.5% | 46.5% | 50.0% |

4. **The deliberation rule itself was chosen on 300 present + 300 absent queries**, with candidates
   and verdicts cached once and six rules simulated
   (`agent_deliberation_rules_vrsbench_20260914.json`). The first version (R1) also held unconfirmed
   candidates in the relaxed pass. It returned a box for 45.0% of absent queries; R3, the shipped rule,
   returns one for 28.0%, with identical present R@0.5. Stricter rules cut absent boxes further (R5:
   18.7%) but drop present R@0.5 to 32.7%.
5. **Simulation = implementation:** the real pipeline run on 40 cached records (80 queries) made the
   same decision and the same box as the R3 simulation **80/80**.

### 3. Blast radius — what does this cost, and what can go wrong?

- **Present-object recall drops:** R@0.5 38.7% → 36.0%, mIoU 0.349 → 0.327. The verifier sometimes
  contradicts the *correct* box. Worked example, VRSBench `05865_0000.png` "find the vehicle": the
  first candidate overlaps the ground-truth red vehicle at IoU 0.704, but RemoteCLIP ranked "vehicle"
  7th (best match "ship"). Under R1 it backtracked to a box with IoU 0.0. Under R3 the same case still
  backtracks: it is a genuine failure mode, not a fixed one.
- **12.7% of absent-object queries still return a box marked *verified*.** The second agent reduces
  hallucination; it does not eliminate it. A further 15.3% return a box explicitly marked UNCONFIRMED.
- **Video false rejection on the demo clip:** `real_aerial_footage.mp4` "find all vehicles" went from
  3 events to 2. The dropped 4.80–7.68s event is a **real white car** (checked visually on the
  single-agent keyframe `results/1de5e372…/video/flag_b034e517_annotated_frame_60.png`); RemoteCLIP
  read it as building/ship on 0/3 frames. Keeping the crop window inside the frame did not change that
  verdict. Most likely a domain gap: RemoteCLIP is satellite-nadir, and this is a low-altitude close-up.
- `tests/unit/test_video_workflow.py::test_video_flag_mask_is_not_empty` sampled only the first
  12s, whose only vehicle event is that car. Its window was widened to 40 frames (reaches the 14.9s
  event), with the reason written in the test.
- `tests/models/test_grounding_workflow.py::test_grounding_pipeline_execution` feeds a flat grey image
  through a mock detector claiming a vehicle. The real verifier correctly found no vehicle, so this
  plumbing test now injects a stub verifier.
- Latency: ~8.6 ms per verification (measured over 1,946 verifications); up to 5 per pass. GPU: adds
  RemoteCLIP ViT-B/32 to resident models; the change-detection OOM (plan phase 3) gets worse, not better.
- **Not calibrated:** `verifier_confidence` is a softmax over the vocabulary, a relative score.
- Found while checking masks, **not caused by this change:** with verification disabled, 64 sampled
  frames give SAM 2 masks on only 1 of 3 vehicle events. Propagation runs forward from one anchor
  (`pre-demo.md` §2.1e).

### 4. Verification — what proves it?

- `tests/unit/test_agent_deliberation.py`, 8 tests with scripted verdicts: accept first verified;
  backtrack past contradicted; prefer a later verified over an earlier unconfirmed; unconfirmed
  returned but labelled; re-evaluate when all contradicted (contradicted boxes not re-verified); relaxed
  pass rejects unconfirmed; NOT_FOUND; no verifier → single-agent behaviour.
- Live, VRSBench (`agent_deliberation_live_vrsbench_20260914.json`, run under R1): present objects
  4/4 verified (airplane, vehicle, ship, storage tank); absent 3/4 NOT_FOUND, the fourth UNCONFIRMED
  on a relaxed-pass box — the case that motivated R3.
- Live video after the change: "find the airplane" 0 flags, with three warnings naming detector scores
  0.71/0.52/0.73 and 0/3, 0/3, 0/2 frames confirmed; "find the red car" 1 flag (15.36–18.24s); "find
  all vehicles" 2 flags (verified 2/3 and 1/2 frames).
- `pytest -q` → 161 passed + the widened video test passing (7/7 in `test_video_workflow.py`).

### 5. Defence — a mentor asks: "RemoteCLIP isn't trained for this. Why should its opinion override the detector's?"

"It doesn't override it; it's a second, independent witness with a different failure pattern, and we
measured exactly how good a witness it is before we let it vote. Grounding DINO will always return
*something* for any prompt: on our set, it put a box on 64.7% of queries for objects that aren't in
the image. RemoteCLIP, asked whether a crop is the named category rather than 32 alternatives, confirms
a wrong label 6.3% of the time. So we only overrule the detector when the verifier positively says
it's a *different object*; when it only sees background, we keep the detection but mark it unconfirmed.
That cut hallucinated boxes to 28.0% and cost 2.7 points of recall, and every decision, with both
confidences, is in the trace."

The caveat to volunteer: it has a real blind spot on close-up, low-altitude footage. It rejected a
genuine white car in our own demo video. Say so before the demo does.

---

## Q-009 · Two-agent detection: attribute queries are labelled, not backtracked

**Recorded** 2026-09-14, same session as Q-008 and before either was committed. **Supersedes the
deliberation rule and headline numbers of Q-008**; Q-008's verifier design, measurements and video
behaviour stand.

**Result, same 300 present + 300 absent VRSBench queries:**

| | single agent | Q-008 rule (R3) | **this rule (R7)** |
|---|---|---|---|
| present R@0.5 | 38.7% | 36.0% | **40.7%** |
| present mIoU | 0.349 | 0.327 | **0.371** |
| absent queries that return a box | 64.7% | 28.0% | **28.0%** |

### 1. Mechanism — what changed from Q-008?

The deliberation now branches on the reasoner's strategy (`workflows/grounding.py::deliberate`).

- **Attribute queries** (`multi_attribute_ranking`, or `ordinal_*`: "the largest building", "white car
  at the bottom left", "second from left"): only the reasoner's selected box is verified, and it is
  always returned. The verifier sets the label — **verified**, **unconfirmed**, or **DISPUTED** when
  it contradicts. No backtrack, no relaxed re-evaluation.
- **Plain category queries** ("find the ship"): Q-008's R3 rule, unchanged — backtrack on
  contradiction, hold the first unconfirmed, relaxed re-evaluation accepts only verified, else
  NOT_FOUND.

`agent_deliberation.mode` records which branch ran; `decision` gains `accepted_disputed`; the tool adds
a warning for disputed answers.

### 2. Rationale — what showed Q-008's rule was wrong?

The verifier judges *category*, not *attributes*. For "the largest building", backtracking replaces the
largest box with a smaller building the verifier likes better, which answers a different question. The
visible symptom was the demo image `GR_DINO_TEST/05945_0000.png`: "segment the largest building"
backtracked past the two largest candidates and returned a 1,247 px box, and "find the white car at
the bottom left" backtracked away from the car the single agent had found.

Split by query type from the same cache (`agent_deliberation_rules_vrsbench_20260914_stdout.txt`):

| rule | attribute R@0.5 (n=206) | plain R@0.5 (n=94) |
|---|---|---|
| single agent | 48.1% | 18.1% |
| R3 — backtrack everywhere (Q-008) | 41.3% | 24.5% |
| R6 — attribute: no backtrack, contradicted → NOT_FOUND | 37.9% | 24.5% |
| **R7 — attribute: label only** | **48.1%** | **24.5%** |

Backtracking helps plain queries (+6.4 points) and hurts attribute queries (−6.8). R7 takes the better
branch for each, and beats the single agent on all three headline measures.

### 3. Blast radius — what does R7 give up?

- **Attribute queries for absent objects still return a box.** Measured on 220 absent attribute
  queries (VRSBench referring expressions with the object class replaced by one not in the image;
  `agent_verifier_absent_attribute_queries_20260914.json`): no candidates 26.4% · **DISPUTED 61.4%** ·
  unconfirmed 7.3% · **verified 5.0%**. So 73.6% return a box, and the protection is the label, not a
  refusal. A UI that ignores the label would show hallucinations again.
- Every absent query in the headline 300 is a plain "find the X", so the 28.0% figure describes
  category queries only.
- On the demo image both previously regressed queries now return the single agent's original boxes,
  **labelled DISPUTED** (verifier's best match "ground track field" and "roundabout"). Both boxes touch
  the image edge; the black-padded crop is the likely cause. Keeping crops inside the frame was tested
  on video frames only and did not change those verdicts, so it was not adopted.

### 4. Verification

- Implementation vs R7 simulation on 40 cached records (80 queries): **80/80** identical decision and
  box.
- `tests/unit/test_agent_deliberation.py` now 11 tests: the Q-008 eight, plus attribute query →
  DISPUTED with no backtrack and a single verification, attribute verified, and mode recorded.

### 5. Defence — "So when the agents disagree on 'the largest building', you just ignore the verifier?"

"We don't ignore it; we stop letting it answer a question it can't evaluate. The verifier knows whether
a crop looks like a building. It has no idea which building is largest. When it vetoed attribute
answers, accuracy on those queries fell from 48.1% to 41.3%, because it kept swapping the right answer
for a smaller building it liked better. So on attribute queries it tells the user it disagrees, and on
plain 'find the X' queries, where category is the whole question, it is allowed to backtrack. That split
is measured, not assumed, and it is better than one agent on every number we track."

---

## Q-010 · GPU out-of-memory recovery for resident models

**Recorded** 2026-09-14. Committed *before* Q-008/Q-009's verifier, because the verifier adds another
resident model and the suite is not reliably green without this.

### 1. Mechanism

- `ml/registry.py::release_gpu_memory(exclude)` — unloads every cached adapter except `exclude`
  **in place**: instances stay registered, because other objects hold references (the verifier caches
  its RemoteCLIP adapter), and they reload lazily. Besides `unload()`, it clears any attribute holding a
  `torch.nn.Module` or a SAM 2 predictor (DOFA keeps weights in `_dofa_model`, which the base `unload()`
  misses), then `gc.collect()` + `torch.cuda.empty_cache()`. Returns the released model keys.
- `ml/adapters/changeformer/adapter.py::_forward_logits_resilient` — on `torch.OutOfMemoryError`:
  release other models → retry native → 512 windows → 256 windows → raise. What happened is returned
  in `metadata.oom_recovery` (`released_models`, `resolved_by`), and `inference_mode` becomes
  `windowed_512`/`windowed_256` if accuracy was traded.
- `agent/executor.py` — heavy inference tools get one retry after any error whose cause chain is a CUDA
  OOM: release all models, add a warning trace step naming what was released, rerun the tool. Non-OOM
  errors are not retried.

### 2. Rationale

Measured, not hypothesised. The in-process audit ran every demo query type in sequence
(`scratchpad/audit_queries.py`). `temporal_change_vqa` failed both times with "CUDA out of memory. Tried
to allocate 1024.00 MiB … 33.75 MiB is free" after BLIP, Grounding DINO and SAM 2 loaded. The API server
keeps models resident across requests, so this is the demo configuration, not a test artefact.
Chrome (333 MiB) and the Claude desktop app (73 MiB) also held GPU memory (`nvidia-smi`).

Order of recovery is by accuracy cost. Releasing models costs a reload on the next query, but no
accuracy. Windows cost 0.02–0.03 IoU at 256 px (Q-007). Resize-to-fit was not used: it measured IoU
0.00–0.09 (Q-007).

### 3. Blast radius

- The first query after a release pays model load time again (not measured per model tonight).
- If ChangeFormer itself cannot fit, results silently would have been an error; now they may be
  `windowed_256`, which is visible in metadata but not yet surfaced in the answer text.
- `release_gpu_memory` clears attributes by type. An adapter that keeps GPU tensors in a plain dict or
  list would not be freed.
- Suite flakiness observed before the fix: with RemoteCLIP resident, the full run failed 5–7 ChangeFormer
  tests on OOM; after adding recovery but before isolating the accuracy fixture, one isolated run
  failed the three `test_1024_scene_native_iou` cases and an identical rerun passed 146/146. The cause
  of that one failure was not captured (a passing rerun leaves no assertion), most likely a windowed
  fallback when free memory dipped. `tests/models/test_changeformer_accuracy.py`'s fixture now releases
  other models before measuring accuracy.

### 4. Verification

- `tests/unit/test_gpu_oom_recovery.py`, 5 tests: recover by releasing; fall back to 512 windows when
  release is not enough; no recovery metadata when memory is fine; executor releases + retries a heavy
  tool once; executor does not retry non-OOM errors.
- Live, same audit script, all models in one process: both change queries now `COMPLETED`, log
  `Released GPU memory held by: ['general_rs_vlm', 'grounding_dino', 'sam2', 'remoteclip'] (kept:
  ['changeformer'])` and later `['cdvqa']`.
- Full suite with all of tonight's changes: 167 passed, 0 failed.

### 5. Defence — "Isn't evicting models just hiding that you're over budget?"

"We are over budget on an 8 GB card: nine models don't fit at once, and the demo server loads them
lazily as queries arrive. The honest options are a bigger GPU, or managing memory and saying when we do
it. We release models first, because that costs reload time and no accuracy. We only fall back to
smaller windows if the model alone still can't fit, and when that happens the result says so in its
metadata. The trace shows exactly which models were released for which query."

**Addendum (same session, before commit).** The video workflow does not run through the agent
executor, so it had no recovery: in an isolated suite run, Grounding DINO hit OOM on every sampled
frame ("Tried to allocate 328.00 MiB … 157.00 MiB free") after the ChangeFormer tests, each frame was
logged as a frame error, and 2–4 video tests failed. `workflows/video_analysis.py` now retries a frame
once after releasing every model except `grounding_dino`, `sam2` and `remoteclip`, with a warning trace
step. Isolated suite at the two-agent commit afterwards: 157 passed, 0 failed.

---

## Q-011 · GeoTIFF georeferencing without rasterio, and GeoJSON area-of-interest input

**Recorded** 2026-09-14, atop `9c7caf6`. Plan phases 4–5.

**Result:** a real UTM GeoTIFF now reads as `EPSG:32614` with its transform (before: `crs=None`,
`is_georeferenced=False`). Through HTTP, change detection with a WGS84 AOI over the western half of
LEVIR scene 100 reports **14,101 changed px = the independently counted 14,101**, **3,525.25 m² exact**,
change ratio relative to the AOI, and GeoJSON in lon/lat.

### 1. Mechanism

**GeoTIFF read** (`geo/raster.py::_georeference_from_tifffile`), because `rasterio` is not installed and
rules.md §2 keeps GDAL optional:
- CRS from `ProjectedCSTypeGeoKey` (3072), else `GeographicTypeGeoKey` (2048), as `EPSG:n`.
  User-defined (32767) → not georeferenced, rather than guessed.
- Transform from `ModelTransformation` (34264), else `ModelPixelScale` (33550) + `ModelTiepoint`
  (33922), in rasterio Affine order `[a, b, c, d, e, f]` so metadata is identical whichever reader
  ran. `RasterPixelIsPoint` is shifted half a pixel, as GDAL does.
- Bounds, resolution, nodata (`GDAL_NODATA` 42113).

**GeoTIFF write** (`evidence/masks.py::_geotiff_tags`): change and segmentation masks carry the source
CRS and transform; `run_change_detection` now passes `meta1`. Before, they were saved without it.

**GeoJSON output** (`geo/vectors.py` path B, the no-rasterio path): real contour polygons with holes
(`cv2.findContours` RETR_CCOMP → affine → pyproj). Before, every component became its **bounding
rectangle**.

**Non-8-bit pairs** (`geo/optical_preprocessing.py::joint_rgb8_pair`): uint16/float/multi-band input
is reduced to the first three bands and stretched with one set of 2–98% percentiles computed across
**both dates**, with a warning. Before, arrays went straight to ChangeFormer's `/255` scaling.

**AOI input** (`geo/aoi.py`):
- `load_aoi` accepts Polygon / MultiPolygon / Feature / FeatureCollection, as a dict, JSON string or
  file. CRS is RFC 7946 WGS84 unless a legacy `crs` member names another. Errors are structured
  `AOIError` (422): `AOI_INVALID`, `AOI_REQUIRES_GEOREFERENCED_RASTER`, `AOI_OUTSIDE_RASTER`.
- `rasterize_aoi` reprojects to the raster CRS, maps world→pixel through the inverse affine, and fills
  with an exact even-odd scanline at pixel centres (`_scanline_fill`). It reports AOI area, the area
  inside the raster, and coverage.
- Inputs: `AnalyzeRequest.aoi_geojson` (inline) or `aoi_filename` from the new `POST /api/upload/aoi`,
  which validates on upload.
- Applied in `inspect_raster` → `AgentState.aoi`, `evidence.metadata.aoi`, a trace step, and a warning
  if coverage < 100%.
  - **Change detection:** masks clipped to the AOI (full-scene masks kept as `*_full_scene`), answer
    and counts are AOI-relative, AOI outline drawn on the overlay.
  - **Statistics:** pixels outside the AOI are excluded from the valid area.
  - **Grounding:** candidates whose centre is outside the AOI are dropped (trace step
    `filter_area_of_interest`), and the SAM 2 mask is clipped.

### 2. Rationale — why these choices?

- **tifffile over adding rasterio:** a system GDAL binary is an "ask first" dependency, and the project
  deliberately installs on a fresh Windows laptop. The GeoKeys needed are four tags.
- **Joint stretch, not per-date:** per-date percentile stretching changes each date's radiometry
  independently. That difference is exactly what a change detector reports as change.
  `test_joint_stretch_does_not_invent_change_in_uint16` asserts unchanged pixels stay byte-identical
  across dates.
- **Scanline, not `cv2.fillPoly`:** fillPoly was implemented first and **the new tests caught it**. It
  fills every pixel an edge touches, so a 200×200-pixel AOI rasterised to 201×201 (40,401 px, +1.0%),
  and hole boundaries were removed too (30,200 instead of 30,000). The scanline is exact by
  construction. Speed: a 10,980×10,980 (Sentinel-2 tile) raster with a 5,001-vertex AOI rasterises in
  **0.25 s**, area error **−0.00004%**.
- **Fail, don't fall back, when an AOI can't be applied:** analysing the whole scene when the user
  asked about one area would return plausible, wrong numbers.

### 3. Blast radius — limits and what isn't covered

- **Only EPSG CRSs are read and written.** A WKT-defined or user-defined CRS (32767) is treated as not
  georeferenced, so AOI requests on such files fail with `AOI_REQUIRES_GEOREFERENCED_RASTER`.
- **Band selection is "first three bands".** Sentinel-2 stacks are usually B2,B3,B4… (blue first), so
  RGB order may be wrong for them. The stretch warns but does not reorder. ChangeFormer is also only
  measured on LEVIR-CD 8-bit RGB (Q-007); multispectral accuracy is **NOT MEASURED**.
- **GeoJSON polygons trace pixel centres**, ~half a pixel inside the true boundary (−0.8% polygon area
  on the 77,500 px test shape). Reported areas come from pixel counts, which are exact.
- **Grounding uses the box centre** for AOI membership; a box straddling the edge is kept or dropped
  whole. Its mask is clipped.
- AOI applies to the first raster's grid. Pairs are required to share dimensions (Q-007), and CRS
  equality between the two dates is not re-checked here.
- Found on the way and fixed: `artifact_manager.save_result_json` / `save_trace_json` did not create the
  job directory, so a pipeline that failed before any tool ran (e.g. an AOI error when the controller is
  called directly) raised a misleading `FileNotFoundError` instead of returning FAILED. The HTTP path
  was unaffected because upload creates the workspace.
- The upload endpoint's first version stringified the structured error inside a generic `HTTP_ERROR`;
  it now re-raises the `AOIError`, and the app's handler returns `{"error": {"code": "AOI_INVALID"}}`.

### 4. Verification

- `tests/unit/test_geotiff_georeferencing.py` (13): UTM scale+tiepoint; WGS84; ModelTransformation;
  tiepoint not at origin + PixelIsPoint; nodata; plain TIFF and user-defined CRS not georeferenced;
  channels-first read; metric area exact; GeoJSON real shape in lon/lat (Austin, TX) with pixel count
  77,500 and 1 hole; image coordinates without georef; saved mask GeoTIFF round-trips CRS + transform
  + bounds; joint stretch passes 8-bit through; joint stretch does not invent change.
- `tests/unit/test_aoi.py` (7): reprojected AOI hits exactly columns 100–299 / rows 200–399;
  FeatureCollection from dict, string and file (non-polygons ignored); legacy CRS member; holes; half
  outside → coverage 0.50; each structured error; request resolution and box helper.
- `tests/unit/test_aoi_http.py` (3): GeoTIFF upload reports CRS; AOI upload 200 / invalid 422
  `AOI_INVALID` / wrong extension 415; `/api/analyze` with `aoi_filename` and inline `aoi_geojson`
  both COMPLETED with valid pixels = 524,288 (the AOI), area = pixels × 0.25, and identical counts;
  AOI on a PNG → FAILED with `AOI_REQUIRES_GEOREFERENCED_RASTER` in the trace.
- Live HTTP run (`scratchpad/api_aoi.py`): 14,101 changed px in AOI vs 114,001 full scene; the
  independent count of the full mask's western 512 columns is 14,101; GeoJSON longitudes stay west of
  the AOI's east edge (−97.74977 vs −97.74976).
- `pytest -q` → **180 passed, 0 failed**.

### 5. Defence — "How do you know the area inside the polygon is right, and not just plausible?"

"Three independent checks that don't share code. The rasteriser is tested on an AOI defined in UTM
metres and sent in lon/lat: after reprojection it must land on exactly columns 100–299 and rows
200–399, and it does. We tried OpenCV's polygon fill first and that same test caught it filling one
pixel too many on each side. End to end, the pipeline's in-AOI change count equals a direct count of the
full-scene mask's western half, 14,101 both ways, and the area is that count times 0.25 m² exactly. And
at Sentinel-2 tile scale, a 5,000-vertex polygon's pixel area matches its analytic area to four parts in
ten million."

The caveat to volunteer: this is measured on RGB LEVIR scenes we georeferenced ourselves, to test the
geometry. Real multispectral GeoTIFFs will read and clip correctly, but which three bands feed the
model, and how accurate it is on them, is not measured.
