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
