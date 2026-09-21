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
| [Q-011](#q-011--geotiff-georeferencing-without-rasterio-and-geojson-area-of-interest-input) | GeoTIFF georeferencing without rasterio; GeoJSON area-of-interest input | 2026-09-14 | Recorded · numbers corrected by Q-014 |
| [Q-012](#q-012--change-detection-two-agents-changeformer-vs-cdvqa-adjudication) | Change detection two agents: ChangeFormer vs CDVQA adjudication | 2026-09-14 | Recorded |
| [Q-013](#q-013--routing-scene-description-and-honest-refusal-for-unsupported-analyses) | Routing: scene description, and honest refusal for unsupported analyses | 2026-09-14 | Recorded |
| [Q-014](#q-014--demo-rehearsal-over-http-and-a-correction-to-q-011s-numbers) | Demo rehearsal over HTTP, and a correction to Q-011's numbers | 2026-09-15 | Recorded |
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

> **Corrected by [Q-014](#q-014--demo-rehearsal-over-http-and-a-correction-to-q-011s-numbers).** The live
> AOI figures below (14,101 changed px, 3,525.25 m², 114,001 full scene) came from a run that silently
> fell back to 512-px windows after GPU out-of-memory. At native resolution the same AOI has **13,902 px /
> 3,475.5 m²** (full scene 118,997). The equality checks — pipeline count = independent count, area =
> pixels × 0.25 — held in both runs and still stand.

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

---

## Q-012 · Change detection two agents: ChangeFormer vs CDVQA adjudication

**Recorded** 2026-09-14, atop `3043c72`. Ushnik's item 1 in `split-ushnik-ayushman.md`.

**Headline finding, measured before building:** on LEVIR-CD imagery, **CDVQA's change answers carry
essentially no information**. It says "yes, changes are observed" for 57.8% of pairs with building
change, 59.1% without, and **53.9% of identical image pairs**. The adjudicator is built around that fact
rather than around the assumption that two models are two independent good witnesses.

### 1. Mechanism

`backend/app/evidence/adjudicator.py::EvidenceAdjudicator.adjudicate_change_vqa`, called from
`run_change_vqa` after CDVQA answers. It is deterministic; rules are applied in order.

1. **Identical inputs** (`np.array_equal` on the two rasters) → `INPUTS_IDENTICAL`, the answer is "No
   change". A conflict is recorded if either model claimed change.
2. **Counterfactual probe:** CDVQA is asked the same question with the first image twice. If it returns
   the same change-claiming answer (anything except `no`/`0`), its answer does not depend on what changed
   → `CDVQA_UNINFORMATIVE`; the answer comes from ChangeFormer only.
3. **Answer-type check:** the question is classified into SECOND-CDVQA's types (change_or_not,
   increase/decrease_or_not, change_ratio(_types), change_to_what, largest/smallest_change) and must get
   the matching answer type (yes/no · ratio bucket · land-cover class). Otherwise
   `CDVQA_ANSWER_TYPE_MISMATCH`, answered from ChangeFormer where a building mask can answer it
   ("did it change?"). For increase/decrease it gives no answer, because a building mask has no direction.
4. **Comparable claims only.** ChangeFormer measures *building* change (LEVIR-CD); CDVQA *all*
   land-cover change (SECOND-CDVQA). Building change is a subset of all change, so:

   | CDVQA says | ChangeFormer building change | verdict |
   |---|---|---|
   | no | ≥ 1.0% | CONFLICT |
   | yes, general question | < 0.1% | CONSISTENT_WITH_CAVEAT (change is not buildings) |
   | yes, building question | < 0.1% | CONFLICT |
   | ratio bucket [lo, hi] | ratio × precision 0.8656 > hi (for "0%": ≥ 1.0%) | CONFLICT |
   | ratio bucket, building question | ratio outside bucket | CONFLICT |
   | "buildings" (class) | < 0.1% | CONFLICT |
   | other class | — | NOT_COMPARABLE |
   | otherwise | — | CONSISTENT |

- **Confidence:** CDVQA's own softmax score when CONSISTENT / CONSISTENT_WITH_CAVEAT / NOT_COMPARABLE;
  `None` for every other status. `AgentState.confidence_final` stops the controller from overwriting it.
- **Output:** `evidence.metadata.change_adjudication` — both models' outputs, question type, probe
  answer, thresholds, CDVQA's measured accuracy for that question type, rule, conflict details. Plus a
  trace step. Disagreements add a warning and set `quality_status = REVIEW_REQUIRED`.
- **Config:** `configs/app.yaml` `change_adjudication`.

### 2. Rationale — what was measured, and why the design changed twice

- **The old adjudicator was never called**, returned constant confidences (0.88, 0.35, `or 0.5`), and
  read `masks[0]["changed_pixels"]` / `["change_ratio"]`, keys ChangeFormer never produces. Its three
  tests asserted those invented values. It was replaced, not patched.
- **Thresholds** from LEVIR-CD-256 test, 1,113 pairs with no building change (`scratchpad/perpair.json`,
  production adapter): predicted ratio exceeds 1.0% on **2.1%** of them and 0.1% on 5.9%; 1.7% of
  real-change pairs have a true ratio below 0.1%. A conflict claim uses the stricter 1.0%.
- **CDVQA on LEVIR-CD** (`results/evaluations/cdvqa_on_levircd_test_20260914.json`, all 2,048 pairs):

  | question → answers | yes-rate / distribution |
  |---|---|
  | "are there any changes?" — pairs with building change (935) | yes 57.8% |
  | same — pairs with no building change (1,113) | yes 59.1% |
  | same — **identical pairs** (1,113) | **yes 53.9%** |
  | "what percentage of the area changed?" — all | "10–20%" 82.3% (1,686 / 2,048) |

- **Probe measurement** (`cdvqa_counterfactual_probe_levircd_20260914.json`): it flags **45.95%** of yes/no
  answers and **74.80%** of ratio answers as identical to the no-change answer. Yes/no agreement with
  building ground truth: 48.58% overall, 44.95% on flagged, **51.67% on the 1,107 kept**. The probe
  removes the least informative answers, but what remains is still near chance on this imagery.
- **First design iteration (before the probe),** run live on LEVIR 1024 scenes 100/101 and an identical
  pair: identical pairs came out "AGREE" (CDVQA "40–50%" vs 0 building px is not refuted by the subset
  rule). That, plus the measurement above, led to rules 1–2, and to renaming AGREE → **CONSISTENT**
  ("not refuted", not "confirmed").
- **Confidence overwrite, found live:** the controller averaged every model's confidence after the tools
  ran, mixing ChangeFormer's mean pixel probability with CDVQA's softmax. TYPE_MISMATCH showed 0.5163
  instead of None. The same averaging is why single-image grounding has always returned
  `confidence=None` (no model results to average). Grounding is deliberately **not** changed here.

### 3. Blast radius

- **On LEVIR-like imagery, nearly every change answer now comes from ChangeFormer alone.** Live, 9 of 12
  queries were UNINFORMATIVE or INPUTS_IDENTICAL; the 3 CONSISTENT ones (scene 101) passed the probe
  but, per the measurement, CDVQA is still ~chance there. **Do not present CDVQA as a second witness on
  this imagery.** The honest demo claim is the opposite: the system detects that CDVQA isn't answering.
- **CDVQA's measured accuracy is on SECOND-CDVQA only** (docs/models/CDVQA.md §18; the raw metrics JSON
  is not on this machine). Answers say so explicitly.
- **No ground truth for the adjudicator's own accuracy.** LEVIR-CD labels only buildings and has no
  questions; SECOND-CDVQA is not on this machine. **Adjudication accuracy is NOT MEASURED.**
- The probe costs one extra CDVQA forward pass per question (latency not measured separately).
- The question classifier is keyword rules. Phrasings outside them classify as `unknown`, which skips
  the type check (rules 1, 2 and 4 still apply).
- `AdjudicationResult.confidence` is now `Optional`; its only consumer is this module.

### 4. Verification

- `tests/unit/test_adjudicator.py`, 26 tests. Nine question classifications; answer types; the audit
  case (ratio answer to "has any new building been constructed?"); no direction guess for
  increase/decrease; each CONFLICT rule; the non-building caveat; a small false-positive area not
  triggering conflict; the 0% bucket needing ≥1.0%; the AOI pixel count as denominator; the measured
  accuracy note; identical inputs; probe flags; probe passes; probe on ratio.
- Live through the agent controller (`results/evaluations/change_adjudication_live_levir1024_20260914.json`),
  4 questions × {scene 100, scene 101, identical pair}. Identical pair: 4/4 `INPUTS_IDENTICAL`, confidence
  None. Scene 100: 4/4 `CDVQA_UNINFORMATIVE`, e.g. "Yes — building change is detected … 11.35% …
  CDVQA's answer '60% to 70% change.' was set aside". Scene 101: 1 UNINFORMATIVE, 3 CONSISTENT with
  CDVQA's own confidence (0.531 / 0.228 / 0.170).
- `pytest -q` → **203 passed, 0 failed**.

### 5. Defence — "You have two change models. Why does the answer only use one?"

"Because we measured whether the second one was answering the question, and on this imagery it isn't.
CDVQA says 'yes, changes are observed' for more than half of image pairs that are literally the same
image twice. So before trusting any CDVQA answer, the system asks it again with nothing changed. If it
gives the same answer, that answer can't be about the change, and we say so and answer from ChangeFormer,
whose building-change accuracy we did measure: IoU 0.74. When CDVQA's answer does pass that check, we
only call it 'consistent', because building change can bound total change from below but can't confirm
it. The point of two agents is not to average them; it's to catch the one that's wrong."

The caveat to volunteer: we cannot yet measure the adjudicator's accuracy end to end. No dataset here
has both building masks and change questions.

---

## Q-013 · Routing: scene description, and honest refusal for unsupported analyses

**Recorded** 2026-09-14, atop `23d105d`. Ushnik's item 2 in `split-ushnik-ayushman.md`.

### 1. Mechanism

- **Caption wording** (`orchestration/intent_classifier.py`): a single image now routes to
  `single_image_caption` for "describe … image/scene/picture/area/this", "description of", "what does
  this image show/contain/depict", "what do you see", "summarise". Before, only "caption", "summarize",
  "overview of scene" and "brief description" did. Grounding is still checked first, so "describe the red
  car at the bottom" stays grounding.
- **New capability `unsupported_analysis`** — definition, DAG branch
  (`inspect_raster → explain_unsupported_request → generate_report`), `KNOWN_CAPABILITIES`,
  `TaskType.UNSUPPORTED` mapping, and a tool whitelist entry.
- **Matcher:** when intent is `multispectral_analysis` or `sar_analysis` and either the input modality
  is wrong or the capability has no executable branch (`DependencyGraph.has_branch_for`), route to
  `unsupported_analysis`. The routing reason says which case applied.
- **Tool `explain_unsupported_request`** (`agent/tools/unsupported.py`) answers from raster metadata.
  - For an index request it names the bands the index needs. On ≤3 bands: "cannot be computed from this
    image". Otherwise: "not implemented in this version".
  - For SAR polarimetry: "not implemented".
  - Confidence `None` (`confidence_final`), plus a warning.

### 2. Rationale

Measured in tonight's audit (`scratchpad/audit_queries.py`): "compute NDVI for this scene" on an RGB PNG
routed to `single_image_vqa`, and BLIP answered **"No."** with confidence 0.5962. The intent classifier
had already identified `multispectral_analysis`; the matcher only honoured it for >3-band rasters, and
that capability has no DAG branch anyway, so the query fell through to generic VQA. An unrelated
model's answer with a confidence is worse than a refusal: it looks like a result. The refusal is the
honest output until spectral indices exist, and it separates "impossible on this input" from "not built
yet". "describe this image" also routed to VQA, not captioning.

### 3. Blast radius

- Queries matching the spectral/SAR patterns on single images no longer reach VQA at all. A query that
  mentions "infrared" or "NIR" conversationally now gets the refusal.
- **Caption quality is unchanged**: `run_caption` still prompts BLIP-VQA (`Salesforce/blip-vqa-base`)
  for a caption, so answers are one or two words ("Football field." on `05945_0000.png`). Only the routing
  was wrong here; captioning with a VQA model is `pre-demo.md` §1.2's problem.
- **Found on the way:** `agent/validator.py::PlanValidator.PERMITTED_TOOLS` is a separate hand-kept
  whitelist. The first live run failed with "Security violation: Proposed step
  'explain_unsupported_request' is not in the authorized tool whitelist". `rules.md` §3 listed four files
  for a new capability; it now lists five, and a test asserts every DAG tool is registered and
  whitelisted.
- `tests/integration/test_pipeline_end_to_end.py` hard-codes the tool count: 14 → 15.

### 4. Verification

- Live, through the agent controller (`scratchpad/routing_e2e.py`):

  | query | input | result |
  |---|---|---|
  | "describe this image" | RGB PNG | `single_image_caption`, run_caption |
  | "compute NDVI for this scene" | RGB PNG | `unsupported_analysis`: "NDVI needs red and near-infrared (NIR) bands, and this image has 3 band(s) (PNG) … cannot be computed from this image" |
  | "compute NDVI for this scene" | 4-band uint16 GeoTIFF | "… This image has 4 band(s), but spectral-index computation is not implemented" |
  | "show SAR backscatter in dB" | RGB PNG | "SAR polarimetric analysis … is not implemented" |
  | "how many buildings are in this image?" | RGB PNG | unchanged: `single_image_vqa` |

- `tests/unit/test_routing_unsupported.py`, 11 tests: 7 intent wordings, including grounding priority;
  RGB spectral/SAR → unsupported; multispectral → unsupported while unimplemented; explanation text for
  the RGB / multispectral / SAR cases; every tool in every executable DAG is registered and whitelisted.
- `pytest -q` → **214 passed, 0 failed**.

### 5. Defence — "Your system can't compute NDVI. Isn't a refusal a failure?"

"It's a missing feature, and the system now says so precisely: NDVI needs a near-infrared band, and an
RGB photo doesn't have one. Before this change the same question got 'No.' from a generic VQA model with
59.6% confidence. That's the real failure, because it looks like an analysis result. We'd rather show
what we can't do than dress up an unrelated model's output as a spectral index."

---

## Q-014 · Demo rehearsal over HTTP, and a correction to Q-011's numbers

**Recorded** 2026-09-15, atop `ca6f893`. Ushnik's item 3 in `split-ushnik-ayushman.md`. **Corrects the
live AOI figures in [Q-011](#q-011--geotiff-georeferencing-without-rasterio-and-geojson-area-of-interest-input).**

### 1. Mechanism — what was run, and what changed

**Rehearsal.** A real uvicorn server on port 8010 (`backend.app.main:app`, PostgreSQL connected, CUDA)
and an `httpx` client (`scratchpad/rehearsal.py`), in demo order, in one server process so models
accumulate as they will on stage. Responses are saved in `results/evaluations/demo_rehearsal_20260915/`.

| # | request | HTTP | result | s |
|---|---|---|---|---|
| 01 | VQA "how many buildings" (05945) | 200/200 | "3.", conf 0.3668 | 7.9 |
| 02 | "describe this image" | 200/200 | caption "Football field." | 7.4 |
| 03 | "find the vehicle" (VRSBench 05865) | 200/200 | accepted_verified — **wrong box** (see §3) | 15.5 |
| 04 | "find the airplane" (05865) | 200/200 | not_found, 2 contradicted | 7.4 |
| 05 | "segment the largest building" (05945) | 200/200 | DISPUTED (ground track field) | 7.8 |
| 06 | "compute NDVI" (RGB) | 200/200 | refusal naming missing NIR band | 6.9 |
| 07 | change + AOI upload (UTM GeoTIFF pair) | 200/200 | 13,902 px, 3,475.5 m², AOI applied | 10.0 |
| 08 | "has any new building been constructed?" | 200/200 | CDVQA_UNINFORMATIVE → "Yes — building change … 11.35%" | 9.2 |
| 09 | video "find all vehicles" | 200/200 | events 14.88–18.72s (2/3 verified), 25.44–27.36s (1/3) | 33.4 |
| 10 | video "find the airplane" | 200/200 | 0 events, 3 dropped with warnings | 25.7 |

Every overlay and PDF report URL returned 200. The server log shows one out-of-memory recovery
(`Released GPU memory held by: ['general_rs_vlm', 'grounding_dino', 'sam2', 'remoteclip']`).

**Code change.** `run_change_detection` now puts `inference_mode`, `oom_recovery` and `max_native_side` in
`evidence.metadata.change_inference`. It warns when an out-of-memory fallback ran in windows (accuracy
traded), and notes when other models were released (no accuracy cost). Before, the mode was only in
the ChangeFormer `ModelResult` metadata, which the API response does not include.

### 2. Rationale — the discrepancy that led here

Item 07 reported 13,902 changed px in the AOI; Q-011 recorded 14,101 for the same pair and AOI. Reproduced
on a clean GPU after stopping the server (`nvidia-smi` 1,346 MiB used):

| max_native_side | mode | full scene px | AOI (west half) px | IoU vs ground truth |
|---|---|---|---|---|
| 1024 | native | **118,997** | **13,902** | **0.8086** |
| 512 | windowed | 114,001 | 14,101 | 0.7997 |
| 256 | windowed | 111,556 | 13,014 | 0.7872 |

Q-011's figures match the 512-window row exactly. That run happened in a process with other models
resident, so ChangeFormer ran out of memory, released models, still could not fit, and fell back to 512 px —
**with nothing in the response to say so**. A first attempt to reproduce ran while the rehearsal server
still held GPU memory, and it too fell back to 512 px; that is how the mechanism was confirmed. The
rehearsal's 13,902 is the native result.

### 3. Blast radius

- **Q-011's absolute live numbers are wrong for native inference; its checks are not.** "Pipeline count
  equals independent count" and "area = pixels × 0.25" were computed on the same mask in both runs. The
  HTTP test (`test_aoi_http.py`) asserts only those relations, so it passes in either mode.
- **Window fallback moves results by ~4% of changed pixels on this scene** and costs 0.009 (512) / 0.021
  (256) IoU. It stays available as a last resort, now visible.
- **Do not demo** `VRSBench 05865 "find the vehicle"`: the plain-category rule backtracks from the true red
  vehicle (IoU 0.704) to a box with IoU 0.0 and calls it verified (Q-008 §3). Use a verified-correct image.
- Captions remain one or two words (Q-013).
- Ayushman's real GeoTIFF inputs were not ready; this rehearsal used LEVIR scene 100 georeferenced by us.

### 4. Verification

- `tests/unit/test_gpu_oom_recovery.py::test_change_tool_reports_inference_mode_and_warns_on_windowed_fallback`:
  a simulated OOM at 1024 px resolves at 512 windows, and `change_inference` plus the warning appear on the state.
- The rehearsal table above: 10/10 requests COMPLETED over HTTP.
- `pytest -q` → **215 passed, 0 failed**.

### 5. Defence — "Your own record had the wrong number. Why trust the rest?"

"Because the record caught it. The rehearsal produced a different count from the one we'd written down, so
we reproduced both on a clean GPU and found the earlier run had silently fallen back to smaller windows
after running out of memory. That's also a real bug: the API didn't say which mode ran. It does now, and
the old entry carries a correction pointing here, rather than being quietly edited. The consistency checks
in that entry held in both modes; only the headline figure depended on a hidden condition."

---

## Q-015 · `prototype` branch: repairing the 15 Sep merge, and "mask trees" returning text or one mask

**Recorded** 2026-09-15, atop `origin/main` `d5e59eb`, on branch `prototype`. Reported symptom: "when I
ask to mask trees it sometimes barely masks one or two or doesn't mask at all — just a textual answer."

### 1. Mechanism — what was wrong, and what changed

All four remote branches (`main`, `checkpoints`, `refactor/s0-remove-dead-layers`,
`feat/ayushman-demo-model-handoff`) were already ancestors of `origin/main`; no commits were missing.
**Content** was: merge `7efb6f2` resolved its two conflicts (`agent/tools/inference.py`,
`workflows/grounding.py`) to the *merge-base* blobs (`664813f`, `ae99446` = `977587d`), which dropped
**both** sides — Ushnik's two-agent verification, relaxed re-evaluation, AOI clipping, ChangeFormer
inference-mode reporting and CDVQA adjudication (Q-008/011/012/014), *and* Sandipan's LocateAnything
fallback and `ModelResult` confidence fix (`e1be13b`). On `origin/main` 13 tests failed; 12 of them passed
on `refactor/s0-remove-dead-layers`. Repair: `git merge-file` 3-way on those two files (ours `3e35ea2`,
base `977587d`, theirs `a431b02`), four hunks resolved by hand keeping both sides.

Four independent causes of the symptom, each measured on the real server:

1. **Routing** — `IntentClassifier.GROUNDING_VERB_PATTERNS` had no `mask`/`mark`, and `OBJECT_PATTERNS`
   matched only singular nouns. `"mask trees"`, `"mask all the trees"`, `"mask the buildings"` →
   `single_image_vqa` (text only). Added `mask|masks|masking|mark|delineate` and a plural suffix
   (`group(1)` stays singular). A plural noun alone does not imply grounding, so
   `"how many buildings are in this image?"` stays VQA (Q-013's test).
2. **Detector prompt** — `parse_v4_query` kept the verb: `"mask trees"` → prompt `"mask trees."`.
   Added `mask`, `every`, `each`, `how`, `many`, `are`, `there`, … to its stop words → `"trees."`.
3. **One box only** — the pipeline sent only `selected_box` to SAM 2. New step 9b
   (`segment_all_instances`): when `_wants_all_instances` (quantifier, `mask` verb, or plural noun; not
   size/position/ordinal/"the largest"), every reasoner candidate not NMS-overlapping a kept box
   (IoU > `iou_nms_threshold`) and not contradicted by the verifier is segmented and OR-ed into one mask,
   capped at 50. For relational plurals (`"trees near houses"`) a candidate must satisfy
   `_satisfies_relation`: edge-to-edge gap ≤ 8% of the image diagonal (41 px at 512²) and not the
   reference object itself (IoU > 0.5). `relation_score` (centre distance, used for ranking) is unchanged.
   Each instance box is added to `evidence.spatial.boxes`. SAM 2 now skips `set_image` when the pixel
   content hash (blake2b) matches the previous call, so N boxes cost one image encode.
4. **Cache replay** — `controller.py` cached only `{answer, confidence}`; a repeat of the same query on the
   same image (the frontend uploads a new job each time) returned the text with an **empty evidence
   package**: `has_mask: false`, `overlay_path: null`, `boxes: []` (measured, request `0bc265af`). Results
   carrying a mask, boxes or overlay are no longer cached.

Also: trace step renamed by the merge (`call_grounding`) restored to `call_grounding_dino` /
`call_locate_anything`; LocateAnything fallback was dead because `grounding_dino` is always in
`selected_models` — now `auto` unless LocateAnything is explicitly selected; the relational target is the
object before the relation phrase (`"trees near houses"` reported `targeting 'house'`); the rasterio demo
test uses `pytest.importorskip`; `package-lock.json` synced to `package.json` (`@mui/x-charts` was missing,
2 `tsc` errors).

### 2. Rationale — why this over the alternatives

- **3-way merge, not "take ours".** Taking `refactor/…` would drop Sandipan's LocateAnything wiring and
  confidence fix a second time; taking `main` keeps the regression.
- **Union mask, not per-instance masks.** Overlay, statistics, GeoJSON and the frontend all consume one
  binary mask; a union needs no schema change. Instances stay separable via `evidence.instances` and
  `region_count`.
- **Verification on the top instance only.** RemoteCLIP per box would add ~N crops per request; the trace
  says so explicitly (`note` in `segment_all_instances`).
- **Don't cache spatial results rather than cache the files.** Artifacts live under the old job id and
  the frontend fetches by job id; a replay would need copying. A re-run took 5.9–6.5 s warm.

### 3. Blast radius

- **Detector recall is the ceiling.** On VRSBench `P0725_0005.png`, `"mask houses"` masked 4 houses; the
  grey houses left and right of the orange-roofed one were not proposed by Grounding DINO at
  `box_threshold 0.25`, and the jetty in the water was masked as a house (plain query). This change does
  not improve the detector.
- Extra instances are **unverified** detector boxes; a false positive there (the jetty) is reported.
- `"how many cars"`-style questions are unaffected (still VQA). Queries with `mask`/`mark` + a noun now
  route to grounding where they previously went to VQA.
- Answer text changes to `"Segmented N instances of X (… px in total …). Top-ranked instance: …"` when N > 1.

### 4. Verification

- `tests/unit/test_mask_all_instances.py` (25 cases): routing, prompt, instance decision, relational
  target/reference, edge-gap relation, 3 mock trees → union of exactly 400+1600+400 px, "the largest tree" → 1.
- `pytest -q tests` → **243 passed, 1 skipped** (rasterio). The 3 `test_changeformer_accuracy` cases OOM'd
  while the demo server held VRAM (8 GB RTX 3070) and passed 9/9 after stopping it.
- `npx tsc --noEmit` exit 0; `next build` exit 0.
- Live HTTP, real models, `P0725_0005.png` (512²), all `workflow_grounding`, models `grounding_dino, sam2`,
  decision `accepted_verified`, overlay produced:

| query | instances | px | regions | refs | dropped by relation | s |
|---|---|---|---|---|---|---|
| mask houses | 4 | 38,335 | 11 | – | – | 13.6 |
| mask houses (repeat) | 4 | 38,335 | 11 | – | – | 5.9 |
| mask houses near cars | 3 | 36,912 | 10 | 11 cars | 1 (the jetty) | 6.1 |
| mark trees near houses | 9 | 17,294 | 7 | 5 houses | 0 | 6.5 |
| mark houses near trees | 4 | 38,335 | 11 | 9 trees | 0 | 6.1 |
| mask trees | 8 | 16,311 | 6 | – | – | 5.9 |

- Frontend (`next start`, Playwright): upload → "mark trees near houses" → analysis page shows 9 green tree
  masks on the image, 9 evidence rows, confidence 87.7%, regions 7.

### 5. Defence — "It found 4 houses in an image with at least 8. Is that 'working'?"

"The bug was that it found zero or one, or answered in text. Routing, the detector prompt, the single-box
limit and the cache replay were four separate causes, each measured, each with a test. What's left is
detector recall: Grounding DINO at our threshold didn't propose the grey houses, and the pipeline can only
segment what the detector proposes. The table shows the raw counts — including the jetty it wrongly
called a house, which the relational query then correctly dropped."

---

## Q-016 · Colour-qualified masking ("white houses", "cars near the red house"), and `demo_resources/`

**Recorded** 2026-09-15, atop `prototype` `d4c2c2d`. **Extends [Q-015](#q-015--prototype-branch-repairing-the-15-sep-merge-and-mask-trees-returning-text-or-one-mask)**:
Q-015's instance step filtered on relation only; its colour behaviour described there is superseded here.

### 1. Mechanism

Q-015's step 9b added every ranked candidate regardless of colour, and the reference object's colour
(`reference_category = "red house"`) was never checked. Measured on `P0897_0048.png` before this change:
`mask white houses` → **26** instances (every roof); on `P0725_0005.png`, `find cars near red house` → 4, one on
a grey rooftop.

Now, in multi-instance mode (`workflows/grounding.py`):
- **Target colour** (`parsed["color"]`): each instance, *the top-ranked one included*, is scored with the
  reasoner's unchanged `color_score` formulas applied to the **median RGB of its SAM 2 mask pixels**
  (`_mask_color_score`), not the box mean. Kept if ≥ `COLOR_MATCH_THRESHOLD` (white/bright 0.8, black/dark 0.3,
  others 0.6).
- **Reference colour** (a colour word inside `reference_category`): each reference box is segmented and kept
  only if its mask passes the same test. If none survive, no target is "near" one.
- If nothing passes: the top-ranked candidate is returned with the answer prefixed
  *"No instance satisfied every condition of '…'"*. If the top fails but others pass, it is excluded and the
  answer says so; `selected_box` becomes the first kept instance.
- `evidence.instance_filters` records `dropped_by_color`, `references_dropped_by_color`, `dropped_by_relation`,
  `top_instance_failed_filters`.

### 2. Rationale

- **Median over mask, not mean over box.** With the filter disabled, per-house scores on `P0897_0048` using
  the *mean* put the white house at [205,234,254,311] at 0.558 (shadow and lawn in the mask) — inseparable from
  grey roofs (0.55–0.63). With the **median**, the five white roofs score 0.92–1.00 and the next is 0.698; dark
  roofs 0.33–0.52. 0.8 sits in that gap.
- **Filter the top instance too.** The detector ranks by "houses" confidence, not whiteness; the top box was a
  dark roof in the mock test and can be in real scenes.
- **Reuse `color_score`.** Ranking (and the VRSBench numbers behind Q-008) stays untouched.

### 3. Blast radius

- Thresholds were set on **one image** (`P0897_0048`), 26 houses. The orange-tile roof on `P0725_0005` scores
  0.66 for `red` (threshold 0.6): close. Treat colours other than white/red as untested.
- **White cars fail**: 0.47–0.58 on `P0897_0048` (tiny masks with shadow) → "no instance satisfied".
- Colour only filters what the detector proposed: the two red cars beside the white house are not proposed for
  `cars.`, so `mask cars near white houses` omits them.
- Single-instance queries (`find the red car`) are unchanged: still the reasoner's ranking.

### 4. Verification

- `tests/unit/test_mask_all_instances.py` +2: a scene with two white and two dark boxes where the detector
  ranks dark first → exactly the two white boxes, 3,200 px, `dropped_by_color == 2`; and all-dark → top kept
  with the "No instance satisfied" answer. File: 27 passed.
- `pytest -q tests` → **245 passed, 1 skipped**, server stopped.
- Live HTTP on `prototype`:

| image | prompt | before (Q-015) | after |
|---|---|---|---|
| P0897_0048 | mask white houses | 26 | **5** (the white roofs) |
| P0897_0048 | mask cars near white houses | 15 | 5 |
| P0897_0048 | mask red cars | 2 | 2 |
| P0725_0005 | find cars near red house | 4 (1 on a rooftop) | 3 (street cars by the tile house; top box excluded) |
| P0725_0005 | mask cars near white houses | 11 | 1 + "No instance satisfied every condition" |

- Regression re-runs on `prototype`, same server: change detection LEVIR 100 → 118,997 px (= Q-014 native);
  CDVQA question → `CDVQA_UNINFORMATIVE` adjudication; `real_pair` → 16,685 px; video `real_aerial_footage.mp4`
  → events 14.88–18.72 s and 25.44–27.36 s (= Q-014); `derived_patrol.mp4` → 0; optical-SAR → honest
  `NOT_CONFIGURED`. Sentinel-2 demo pair → **0 px** with AOI applied (7,588 px AOI) — model domain, not a code
  path; recorded so nobody demos change detection on it.

**`demo_resources/`** collects every input used above, 8 more "known weak" images with their failure
modes (tennis courts → grass field; pools → roofs; dark parking lot → kerb; 2/8 storage tanks), and the
overlays produced, with a README of prompts and measured results.

### 5. Defence — "You tuned a threshold on one picture."

"Yes, and the entry says so. The threshold sits in a measured gap on that image — white roofs at 0.92 and up,
the next roof at 0.70 — and the check reuses the same colour formula the reasoner already used; what changed
is which pixels feed it: the object's mask instead of its box. White cars fail, and we recorded that instead
of lowering the bar until they passed."

---

## Q-017 · Merging Sandipan's results export (`d81e049`): path traversal, in-memory ZIP, video JSON

**Recorded** 2026-09-15, merge `45e4efd` of `origin/main` `d81e049` into `prototype` `7c6025b` (no conflicts).
`d81e049` adds `GET /api/results/{request_id}/download` (ZIP of `results/<id>/`) and "Download Results ↓"
buttons on the analysis page and results panel.

### 1. Mechanism — defects found and fixed

1. **Path traversal (security).** `ArtifactManager.get_job_dir` sanitised with `Path(request_id).name`, which
   returns `.` and `..` unchanged; `results/..` is the repository root. `GET /api/results/%2E%2E/download`
   (curl `--path-as-is`) began zipping the 20 GB checkout — `.env` (database credentials), `checkpoints/`,
   `datasets/raw/` — into memory: the server's RSS reached **5.9 GB after 3 min 19 s** before it was killed.
   The same helper backs 28 call sites, including uploads that accept a client `request_id`. Fix: the id
   must match `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}` and resolve to a direct child of `results/`, else
   `InvalidInputError` (`INVALID_JOB_ID`, 400); the download endpoint maps it to 404.
2. **ZIP built in RAM on the event loop.** `async def` + `io.BytesIO`: a large job blocks every other request
   while it is compressed and holds the whole archive in memory. Now a plain `def` (threadpool), written to a
   `NamedTemporaryFile`, returned as `FileResponse`, deleted by a `BackgroundTask`; symlinks are skipped.
3. **Video exports had no JSON.** Image jobs write `result.json`/`trace.json` in `agent/controller.py`; the video
   endpoint never did, so a video ZIP held frames and the MP4 only. `POST /api/video/analyze` now saves both.
4. **No download button on the video page.** Added, same styling as the analysis page.

Not a defect: one video flag has no `mask_frame_*.png` — the flagger only writes a mask when SAM 2 produced one
for the peak frame (`video/flagger.py`).

### 2. Rationale

- **Fix in `get_job_dir`, not only the new endpoint** — every job-scoped path goes through it.
- **Allow-list, not deny-list** — existing ids (`uuid4`, `oom-mode`, `test_geo_req`, `showcase-3096b285`) all match.

### 3. Blast radius

- Any caller passing a job id with spaces or other characters now gets 400. No such id exists in `results/`
  (`ls results`) or in the tests.
- Exports include `input/` — uploaded imagery and videos are in the ZIP by design.
- The repo is **public**; model weights were not pushed (see `DEMO_SETUP.md`).

### 4. Verification

- `tests/unit/test_results_download.py` (17): 8 bad ids rejected, 4 existing id styles accepted, 4 traversal/missing
  URLs → 404, a real ZIP with `masks/…png` and `result.json`.
- `pytest -q tests` → **262 passed, 1 skipped**.
- Live, fixed server: `%2E%2E`, `%2e`, `.`, `..`, `..%2F..%2Fetc` → 404 in ≤ 26 ms, server RSS 0.89 GB.
- Live exports: masking job 8 files 1.52 MB (input, mask, overlay, preview, PDF, result.json, trace.json, GeoJSON);
  LEVIR change job 14 files 15.6 MB (before/after, 4 masks + GeoTIFF + probability, 3 overlays, PDF, JSON, GeoJSON);
  video job 8 files incl. `result.json` whose flags are 14.88–18.72 s and 25.44–27.36 s.
- Playwright on the rebuilt frontend: "Download Results ↓" on `/analysis/636537d3…` and `/video/a6bd7563…`
  each downloaded `SatQuery_Results_<id>.zip`; the PDF inside starts `%PDF-1.4`.

### 5. Defence — "Nobody would type `..` into a job id."

"They wouldn't have to type it into the UI — it's one GET request to a public route, and the response was the
repository with its `.env`. Before it finished, it would have taken the demo machine's memory. The fix is an
allow-list in the one function every job path goes through, with tests for the exact URLs that worked."

---

## Q-018 · Video: auto-play the detected event's time range, pause at its end, highlight the playhead

**Recorded** 2026-09-15, atop `prototype` `152b38c`. Also fixes a regression introduced by Q-017.

### 1. Mechanism

- `frontend/src/hooks/useSegmentPlayer.ts` (new): `playSegment({start, end})` seeks the `<video>` to `start`, plays,
  and pauses at `end`, setting `currentTime = end` exactly. `timeupdate` fires ~4×/s (up to 250 ms overshoot), so
  the end is checked on every `requestAnimationFrame` while a segment plays. If unmuted autoplay is refused, it
  retries muted; if that fails too, status `blocked` ("Click an event to play"). A manual seek > 0.25 s outside the
  segment releases it. Zero-length events play 1 s.
- `frontend/src/app/video/[jobId]/page.tsx`: when results arrive, the first event auto-plays once. Timeline shows
  events as start→end bars (were start-only dots) and a playhead at `currentTime`; the playhead is highlighted
  (amber, glow; pulsing once stopped) while inside the active event. Event bars and event cards play their segment.
  Status badge on the player: "Playing event / Paused in event / Stopped at event end · start → end".
  Timeline length uses the video's real duration (was a hard-coded 45.2 s fallback); the "Stream: …" placeholder
  box, previously always drawn over the player, now appears only if the stream fails.
- **Regression from Q-017:** video jobs now write `result.json` in `VideoAnalysisResponse` shape; `GET
  /api/results/{id}` parsed it as `AnalyzeResponse` → pydantic `request_id Field required` → **500 with no CORS
  header**, which the home page's `useAnalysisResult` retried ~1×/s (20 CORS errors in the console during the test).
  It now returns 404 "is a video job; its results are at /api/video/{id}".

### 2. Rationale

- **rAF, not `timeupdate`**, for the pause: the requirement is "pause at 21", and a 250 ms overshoot is visible.
- **Custom playhead** on our timeline: the native `<video controls>` scrubber cannot be styled or highlighted.
- **HTTP Range** was already served by `/api/video/{id}/stream` (`206 Partial Content`), so seeking needed no backend work.

### 3. Blast radius

- Only the first event auto-plays; others play on click.
- Browsers that block autoplay entirely show the "Click an event to play" state instead of playing.

### 4. Verification

- API: `find red car` on `real_aerial_footage.mp4` (30.16 s) → one event 15.36–18.72 s, score 0.893; the raw keyframe
  (frame 228) shows a red sedan. `find white car` → 4.80–8.16, 14.88–18.24, 25.44–27.36 s.
- Playwright, built frontend, real flow (upload on home page → "find red car" → redirected to `/video/12fdfcb3…`):
  status "Stopped at event end · 0:15.4 → 0:18.7"; `video.currentTime = 18.72`, `paused = true`, `muted = false`;
  playhead `left = 62.069%` (= 18.72 / 30.16), `data-highlighted = true`.
- Clicking "▶ play this event", sampled every 250 ms: 15.38, 15.60, 15.85 … 18.35, 18.60, then 18.72 paused ×6 —
  real-time playback, stop at exactly 18.72.
- After the 404 fix: reload video page → auto-plays and stops again; home page 10 s → **0 console errors**.
- `tsc --noEmit` 0, `eslint` 0, `next build` 0; `pytest -q tests` → **263 passed, 1 skipped** (+1 regression test).

### 5. Defence — "Does it really stop at the end or just near it?"

"We read the element's own clock: 18.60 while playing, then 18.72 and paused, every sample after. The end is checked
every frame, not on the browser's quarter-second time event, and the position is then set to the end exactly."

---

## Q-019 · Video only: a box that follows the object while the event plays; outlines instead of colour-hiding masks

**Recorded** 2026-09-15, atop `prototype` `a462c4a`. Image masking and its overlays are unchanged.

### 1. Mechanism

Problem: the only visual evidence was one keyframe with a 45% green mask fill — a red car rendered green, so the
requested colour could not be checked — and detections existed only on coarse samples (8 frames over 3.36 s,
~2 fps), too sparse to draw a moving box.

- `backend/app/video/tracker.py` (new) `track_event`: for each flagged event, re-reads frames from `start_frame` to
  `end_frame` at ~10 fps (stride `round(fps/10)`, ≤ 90 frames, the peak frame always included), prompts SAM 2.1
  video propagation with the event's confirmed box at the peak frame, and propagates **forwards and backwards**
  (`SAM2Adapter.predict_video(bidirectional=True)`, a second `propagate_in_video(reverse=True)` pass). Each mask →
  normalised box; masks < 0.02% of the frame are "object not visible" and omitted. Per point it stores the median
  RGB of the object's saturated mask pixels (saturation > 0.3), or of all mask pixels when fewer than 20% are
  saturated (white/grey/black objects). Stored as `flag.metadata["track"]`, so it is persisted with the flag
  (`metadata_json`) and returned by both `POST /video/analyze` and `GET /video/{id}`.
- `backend/app/workflows/video_analysis.py` step 6b calls it for every flag; failure is a per-event warning.
- `backend/app/video/flagger.py`: the annotated keyframe draws the SAM 2 mask **boundary** (2 px, `draw_mask_outline`)
  instead of `create_change_overlay(..., alpha=0.45)`.
- `frontend/src/components/video/TrackOverlay.tsx` (new): positioned over the `<video>`'s letterboxed content area,
  it interpolates each track linearly between points by `video.currentTime` (rAF while playing), hides across gaps
  > 0.5 s, and draws a 2 px cyan outline with no fill, a label (`red car · 0.89`) and a swatch of the measured colour.

### 2. Rationale

- **SAM 2 video propagation over re-running Grounding DINO per frame:** it follows the one object the event was
  confirmed on, instead of re-choosing among candidates on each frame (which can hop between two cars).
- **Bidirectional:** the confirmed (peak) frame is usually mid-event; forward-only propagation left the start blank.
- **Saturated-pixel median:** measured on frame 228's mask (12,385 px): all pixels [148, 96, 111] (reads pink —
  windows and shadow), saturation > 0.2 → [123, 45, 59], > 0.3 → [120, 39, 53] (67% of pixels), > 0.4 → [106, 24, 36] (49%).

### 3. Blast radius

- Adds ~10 s per video request on this clip (red car 35.9 s → 44.8 s; white car, 3 events, 33.3 s → 57.1 s).
- The swatch is a median, not a classifier: the white car's swatch reads light grey rgb(155,157,159) at 6.2 s (a large
  black rear window); the red car's first point [236,124,149] is pink from glare at the frame edge.
- Tracks cover the event window only (the playback segment), not the whole video.

### 4. Verification

- `tests/unit/test_video_tracker.py` (4): normalised box from a mask; a synthetic red square moving 1 px/frame is
  tracked with `bidirectional=True`, 21 frames at stride 2, an empty-mask frame omitted, boxes move right, colour
  red, temp frames removed; saturated median ignores grey glass but keeps a white car white; keyframe outline
  leaves object pixels unchanged. `pytest -q tests` → **267 passed, 1 skipped**.
- Live, `real_aerial_footage.mp4`: `find red car` → event 15.36–18.72 s, **43 track points**, also returned by
  `GET /video/{id}` (43); `find white car` → 43, 43 and 25 points for its three events, colours in
  [148–251] grey/white range.
- Playwright on the built frontend, replaying the red-car event and sampling every 0.22 s: a box on every sample,
  moving y = 77.9% → 0% as the car drives off, colour swatch present; paused at 18.72 with the final box. Seeked to
  16.2 s: the outline encloses the red car and the car's paint is visible (screenshot); white car at 6.2 s likewise.
- Annotated keyframe `flag_b6c230f9_annotated_frame_228.png`: red car with a green outline, no fill.

### 5. Defence — "How do you know it's the red car and not just any car?"

"Watch it: the box follows one car through the clip and nothing covers it, so the paint you see is the answer. The
swatch beside the label is the median colour of that car's own pixels on that frame, measured, not predicted — and
where the median is fooled by a black window or glare, the record above says so."

---

## Q-020 · "mark the roads" masks 5 short segments, not the street grid — detector recall, not undertraining

**Recorded** 2026-09-15, atop `prototype`, job `a181e7bd-d363-496f-966d-fd9624840860`, input
`satquery_change_after.png` (1024×1024, a residential subdivision next to open rural land, not georeferenced).
User's question: is this because "our model isn't trained enough, need more training?"

### 1. Mechanism

`grounding_dino` is **not a model we trained** — it's IDEA-Research's pretrained open-vocabulary box detector,
used zero-shot. "Roads" is fundamentally a bad fit for that architecture: a box detector proposes a rectangle
around one compact object; a street grid is a connected linear network with dozens of near-identical parallel
and perpendicular segments, none individually "compact."

Measured from `trace.json`:
1. First pass, prompt `"roads."`, `box_threshold 0.25`: **1 raw detection**, score 0.259, box
   `[409, 59, 1020, 1019]` — roughly the whole right half of the image. RemoteCLIP (the verification agent)
   scored that crop 76.6% "roundabout", 16.0% "golffield", **0.44% "road"** → `contradicted`. The pipeline's own
   backtrack logic (Q-008) correctly discarded it and lowered `box_threshold` to 0.15.
2. Second pass at 0.15: **12 raw detections**, scores 0.157–0.259 — every one below what real objects scored in
   earlier measurements (cars/houses/planes: 0.5–0.9, Q-015/Q-016). The top-ranked survivor, box
   `[0, 10.6, 114, 162]` (the diagonal rural road, top-left), was accepted with detector confidence 0.237 —
   but RemoteCLIP's own read of that same crop is 84.7% **"trees"**, 3.1% "building", and only **3.7% "road"**.
   It was accepted only because it ranked 2nd among 11 weak candidates, not because either agent was confident
   it is a road.
3. `segment_all_instances` (Q-015) took the 11 candidates, dropped ones overlapping already-kept boxes
   (NMS `iou > iou_nms_threshold`) or contradicted by the verifier, and segmented what was left: **5 disjoint
   boxes**, 39,433 px, covering the rural diagonal road and one edge of the street grid. The other ~10+ visibly
   paved streets in the grid never appeared as a candidate at *any* threshold tried (0.25 or 0.15) — this is a
   detector recall gap, not a filter in our code discarding them.

### 2. Why "more training" is the wrong frame

We have never trained Grounding DINO; there is no checkpoint of ours to make "more trained." The three real
options are architecturally different:
- **Fine-tune Grounding DINO on a road-labelled dataset** (DeepGlobe Road Extraction, Massachusetts Roads,
  SpaceNet Roads) — this is training, but it is *adding* a capability we don't have, not correcting
  undertraining of an existing one.
- **Swap to a semantic road-segmentation model** (e.g. a U-Net/D-LinkNet-style linear-network extractor) for
  road-type queries — a better architectural fit than box-detect-then-mask for a connected network.
- **Same-day mitigation, no training:** per-tile detection on large images, alternate prompts ("street",
  "paved road", "asphalt"), and a lower default `box_threshold` specifically for linear-network categories
  (roads, rivers, canals) — cheap to try, unlikely to close the gap fully.

### 3. Blast radius

- This is a **new, previously unmeasured** failure mode. Q-015/Q-016 measured compact objects (houses, cars,
  trees, planes) and found detector misses/false positives there too, but never tested "roads" specifically.
- Any query for a linear-network category (roads, rivers, paths, canals, pipelines) should be expected to
  under-mask the same way until one of the §2 fixes lands.
- Not a regression: no prior code change touched this; it's the first measurement of this category.

### 4. Verification

Read directly from `results/a181e7bd-d363-496f-966d-fd9624840860/{trace.json,result.json}` — every number above
is from that file, not re-run.

### 5. Defence — "Couldn't you just lower the threshold further?"

"We already did, automatically — the pipeline's own backtrack step took it from 0.25 to 0.15 and still got only
11 weak candidates for a grid with dozens of visible streets, and the verification agent independently rated the
best of those only 3.7% confident it's a road. Lowering it further would mask trees and rooftops as roads, not
find more of them — the fix is a road-shaped detector, not a lower bar."

## Q-021 · LocateAnything-3B actually runs: four silent bugs, a vendored patch set, 4-bit by measurement

**Recorded** 2026-09-16, atop `prototype` `0c8b74d`, working tree not yet committed. Weights:
`nvidia/LocateAnything-3B` @ `c32291ca5e99`, sha256 of both shards verified against the Hub etags.
Hardware: RTX 3070 8 GB, transformers 5.16.1, torch 2.14.0+cu130.

### 1. Mechanism

The adapter (`backend/app/ml/adapters/locate_anything.py`, merged in `c2d62ab`) had never produced a
detection on any machine. Four independent faults sat in the load → decode path; each alone was enough:

1. **Missing packages.** The only load path needed `bitsandbytes`; the vendor code also hard-imports
   `peft`, `decord`, `lmdb`, `requests`. None were installed. `load_model()` raised, the error became
   `ModelUnavailableError`, and `workflows/grounding.py` recorded
   `fallback_to_locate_anything → skipped (model_not_available)` and carried on. No crash, no visible failure.
2. **RoPE tables zero / NaN.** transformers 5.x builds models on the meta device; the vendor
   `Qwen2RotaryEmbedding` computes `inv_freq`, `cos_cached`, `sin_cached` as non-persistent buffers in
   `__init__`, which are never recomputed. After load, cos/sin were 0 and `inv_freq` NaN in all 36 layers,
   so q·cos + rot(q)·sin = 0: uniform attention. Output was `<|im_end|>` instantly (hybrid) or endless
   `<null>` (slow, 2.5 min). Fixed by building the tables lazily as plain attributes.
3. **Wrong RoPE base.** Sandipan's compat patch read `getattr(config, "rope_theta", 10000.0)`; 5.x moved
   the value to `config.rope_parameters`, so the model ran with 1e4 instead of the trained 1e6. Fixed to
   read `rope_parameters`, raise if absent.
4. **Never deterministic.** NVIDIA's `sample_tokens` ignores `do_sample` and samples iff
   `temperature > 0`; the adapter passed 0.7. Now `temperature=0.0`.

Also: the vendor `hybrid` (multi-token) decoder runs away on our tiles — after ~15 real boxes it keeps
emitting boxes along the right image edge until `max_new_tokens` (airport tile: 341 boxes / 2050 tokens,
identical at 4-bit and 8-bit, with and without repetition penalty). The block's top token really is
`<box>` (p 0.82–0.90), so it is model behaviour in our stack, not the stop check. Default is now
`generation_mode="slow"`.

Sandipan's seven compat hunks plus fixes 2–3 now live in `third_party/locate_anything/patches/` and are
applied/verified by `scripts/setup_locate_anything.py` (git blob hashes; `modeling_qwen2.py` patched blob
`5a95084c`). Previously they existed only inside the gitignored `checkpoints/` directory of one machine.

### 2. Rationale

- **Slow over hybrid:** hybrid is a speed optimisation; on 512 px tiles slow takes 0.5–2.1 s at 4-bit,
  and terminated on all 12 small-tile runs; hybrid was only exercised on the airport tile, where it ran away.
- **4-bit over 8-bit, measured** (12 greedy runs on 512 px tiles vs a bf16 reference partly offloaded to
  CPU; box match = IoU ≥ 0.5): 4-bit recall 22/26, precision 22/22, peak 4.74 GiB; 8-bit 26/26, 26/26,
  peak 5.98 GiB but 2–10× slower per call (bnb int8). Plain 4-bit with the vision tower also quantized (the old
  adapter config): 19/26, 19/22. 8-bit is exact but leaves no VRAM for Grounding DINO + SAM 2 on 8 GB.
- **Vendored patches over a fork/re-upload:** the licence is NVIDIA non-commercial research; we fetch the
  canonical weights and keep only our diffs.

### 3. Blast radius

- Any bf16 load of this model under transformers ≥ 5 without fix 2 produces garbage with no error.
- If `transformers` changes again, `scripts/setup_locate_anything.py --check` catches file drift but not
  new API breakage — re-run `tests/models/test_locate_anything.py`.
- **Dense 1024 px queries are weak in every precision, bf16 included**: `building` hit the token cap
  everywhere (4-bit: 97 boxes/1024 tokens/41 s); `road` gave 4 boxes at 4-bit (ended, 3.7 s) and 7 at bf16
  (hit the 384-token cap). This does **not** close Q-020's road gap; no claim of that should be made.
  `max_new_tokens` is now 1024 (~40 s worst case in the fallback path) and truncation is flagged in
  result metadata (`truncated`).
- Scores are still a constant 0.5; V4 ranking of LocateAnything candidates carries no model confidence.

### 4. Verification

- `scripts/setup_locate_anything.py --check --hash-weights` → exit 0; fresh `--skip-weights` install into an
  empty dir → patches apply, hashes match; rerun is a no-op; a tampered file is restored.
- Pristine upstream + both patches → `git hash-object` identical to the working checkpoint files.
- `tests/unit/test_locate_anything_parsing.py` 17 passed; `tests/unit/test_grounding_locate_anything_fallback.py`
  3 passed (fallback fires / is skipped when unavailable / not used when a detector is named);
  `tests/models/test_locate_anything.py` 2 passed on the 3070 in 14 s (airport tile: ≥3 in-bounds boxes,
  one with IoU ≥ 0.5 to the airliner, two calls byte-identical; tennis-court tile: `<box>None</box>`).
- Through the real registry: load 6.7 s, 3.31 GiB allocated, 2.2 s then 1.5 s per call, identical outputs.

### 5. Defence — "Was this model ever part of your pipeline before today?"

"Wired in, yes; running, no. Until 2026-09-16 every call ended in `model_not_available` and the pipeline
logged the fallback as skipped. Even once it loaded, its position encoding was zeroed by a library upgrade,
so its first outputs were empty. Every number we quote for it was measured after those fixes, against a
full-precision reference, and we quote its weakness on dense scenes alongside its strength on small tiles."

### Correction, same day, before commit — the airport result was misread

The claims above that the airport tile shows "an airliner plus gate aircraft" (in the session) and the model test's
`>= 3 boxes` requirement were wrong: the tile has **one** aircraft; the long white shapes are jet bridges. The
"recall/precision vs bf16" numbers in §2 measure agreement between precisions, not correctness. Measured through the
real API path afterwards, with a new opt-in switch (`parameters.grounding_model` / `SATQUERY_GROUNDING_MODEL`):

| Detector | Prompt | Proposed | Masked | Top-ranked |
|---|---|---|---|---|
| Grounding DINO | "mask the airplanes" | 4 | 3 | airliner, confidence 0.732 |
| LocateAnything | "mask the airplanes" | 16 | 16 | jet bridge (fixed 0.5 score) |
| LocateAnything | "mask the airplane" | 5 | 5 | jet bridge |
| auto (default) | "mask the airplanes" | Grounding DINO ran | 3 | airliner |

**LocateAnything is worse than Grounding DINO on this tile.** It stays fallback-only, and the default is unchanged.
The model test now asserts only that the airliner is found and that the output is deterministic. Two reporting
bugs found in the same run are fixed: `models_used` said `grounding_dino` when LocateAnything ran, and the
deliberation's detector label was hard-coded to Grounding DINO.

## Q-022 · "mark all roads": LocateAnything is not better than Grounding DINO; OOM retry freed nothing

**Recorded** 2026-09-16, atop `prototype` `0c8b74d`, same uncommitted working tree as Q-021. Inputs:
`satquery_change_before.png` (rural) and `satquery_change_after.png` (rural + suburb), both 1024×1024.
User's question: a 3B model "is supposed to be more powerful" — shouldn't it beat Grounding DINO on roads?

### 1. Mechanism

Both images were sent through `POST /api/analyze` with `parameters.grounding_model` set per run:

| Image | Detector | Proposed | Kept after filters | Result |
|---|---|---|---|---|
| rural | Grounding DINO | 2, then 5 relaxed | — | "No roads found": verifier contradicted all (helicopter, roundabout, storage tank) |
| rural | LocateAnything | 1, then 1 relaxed | 0 | "No roads detected": its one box covered nearly the whole frame and was dropped by the full-frame filter |
| suburb | Grounding DINO | 1, then 12 relaxed | 5 masked, 39,433 px | rural track + one street + two non-road patches (as in Q-020) |
| suburb | LocateAnything | 6 | 4 masked, 317,021 px | rural track + the street grid, but each grid box is SAM-segmented as a block, so lawns between streets are masked too (~30 % of the image) |

LocateAnything proposes the street grid, which Grounding DINO never did. But it proposes it as a few very large
boxes, and box → SAM 2 turns each one into a neighbourhood-sized blob.

### 2. Rationale — why a 3B generalist does not win here

- **Output format.** Both detectors return axis-aligned boxes. A road is a thin connected line, and its box is a
  large area. On the rural image the road's box was the whole frame, so it was rejected. Parameter count cannot
  fix that; roads need a pixel-level (segmentation) model, as Q-020 §2 already concluded.
- **Training data.** LocateAnything's published strengths are natural images, GUI, documents and pointing. Nothing
  in its card targets overhead imagery, and on our airport tile it labelled jet bridges as airplanes (Q-021
  correction). Its 3B parameters are mostly a language decoder, not overhead-image recognition.
- **No confidence.** Every box scores 0.5, so neither the threshold nor the V4 reasoner can separate good boxes
  from bad ones.

### 3. Blast radius — the OOM retry bug

The LocateAnything run on the rural image first **failed**. MoonViT attention on a 1024 px input requests
822 MiB. That ran out of memory because Grounding DINO and RemoteCLIP were still loaded from the previous
request. `SafeToolExecutor` then released every model and retried **inside the `except` block**. The live
traceback still referenced the failed call's frames and the model, so 3.94 GiB stayed allocated and the reload
was refused. This affected every tool that hits OOM, not just LocateAnything. The retry now runs after the
`except` block, with `gc.collect()` and `torch.cuda.empty_cache()`. The same pattern was fixed in the
LocateAnything adapter's own load retry. A related bug: the not-found result had no `detector` key, so
`models_used` still said `grounding_dino`.

### 4. Verification

Re-ran Grounding DINO then LocateAnything on the rural image: the log shows the OOM, the release, and a
**completed** retry. `tests/unit/test_gpu_oom_recovery.py` still passes (7 with `test_agent.py`). Jobs
`f047ea6f…`, `231d4875…`, `99631e54…`, `5261dbe7…` hold the traces and overlays behind the table.

### 5. Defence — "Why not just use the bigger model?"

"We measured it. On roads it either returns one frame-sized box, which we reject, or a few neighbourhood-sized
boxes that mask the lawns along with the streets. Grounding DINO under-detects the same roads. Neither is a road
extractor. The fix is a segmentation model for linear features, not a larger box detector."

## Q-023 · LocateAnything-3B removed; the working integration stays in history

**Recorded** 2026-09-16, atop `prototype` `528662d` (the commit that holds the working integration).
Decision: the user, deciding on Sandipan's behalf (he owns the integration and delegated the call).

### 1. Mechanism

Removed: the adapter, its registry entry and metadata, the grounding workflow's automatic fallback
(`fallback_to_locate_anything`), the capability's optional-model entry, the validator allowlist entry, the
`run_grounding` detector switch (`parameters.grounding_model` / `SATQUERY_GROUNDING_MODEL`, added and removed the
same day), the `locate_anything` config block and its `ModelSpec` fields, the six packages it needed
(`bitsandbytes`, `peft`, `accelerate`, `decord`, `lmdb`, `requests`), `third_party/locate_anything`,
`scripts/setup_locate_anything.py`, its tests and model doc, and the VRS-Bench script's `--model locate_anything`.

Kept, because they are independent of the model: the executor's OOM retry outside the `except` block, the
`detector` key on grounding results (including the not-found path), the ChangeFormer reports in
`docs/models/changeformer/`, the Grounding DINO test tiles in `tests/data/grounding/`, and Q-021/Q-022.
The 7.2 GB weights in `checkpoints/locate_anything_3b/` are gitignored and left on disk; the packages are
still installed in this machine's `.venv`.

### 2. Rationale

Q-021 and Q-022 measured it through the real API. It did no better than Grounding DINO on any prompt we
compared: airport, jet bridges labelled airplanes; roads, a frame-sized box or neighbourhood-sized masks. It
emits no confidence, so its errors cannot be filtered. Its costs were concrete: a 7.7 GB download per machine,
six extra packages, patches to vendor code that break on transformers upgrades, and 3.3 GiB of an 8 GB GPU,
which caused an OOM. "Keep it switched off" was rejected: git history keeps it just as well, and switched-off
code still carries the packages, the patches and the confusion.

### 3. Blast radius

- Grounding requests where Grounding DINO finds nothing now end in "not found" directly. Before today the
  fallback was always silently skipped (Q-021), so for anyone on an older checkout nothing changes.
- `parameters.grounding_model` is no longer read. It never shipped, and the UI never sent it.
- Machines that installed from the Q-021 requirements keep the six packages until the venv is rebuilt;
  nothing imports them.

### 4. Verification

The full `tests/unit` suite plus `tests/models/test_grounding_workflow.py` pass after removal (counts are in the
commit that adds this entry). `grep -rn locate_anything` over backend, configs, scripts, tests and frontend
finds only the removal note in `scripts/evaluate_grounding_vrsbench.py`. The browser check of "mask the
airplanes" on the airport tile runs on Grounding DINO.

### 5. Defence — "You spent a day on it and then deleted it?"

"We spent a day finding out whether it helps, and we have numbers that say it doesn't on our imagery. The four
bugs we fixed and the OOM fix it exposed are real gains, and one `git revert` restores the integration if a
bigger GPU or a road use case changes the answer."

## Q-024 · Hard-prompt sweep: change detection, small objects, video; two video bugs fixed

**Recorded** 2026-09-16, atop `prototype` `a56eaeb`. Every case went through the live HTTP API on the RTX 3070.
The inputs are `demo_resources/` plus `satquery_airplane.png` and `satquery_white_cars.mp4`. The README
baselines are from 2026-09-15.

### 1. Mechanism — what was run and what came back

**Change detection (ChangeFormer, masks scored against the dataset ground truth):**

| Pair | Prompt | Result | vs GT |
|---|---|---|---|
| levir_100 | detect building changes | 118,997 px, 11.35 %, same as baseline | P 0.894 · R 0.895 · F1 0.894 · IoU 0.809 |
| levir_101 | detect building changes | 44,311 px, 4.23 % | P 0.816 · R 0.733 · F1 0.772 · IoU 0.629 |
| levir_105 | detect building changes | 52,726 px, 5.03 % | P 0.885 · R 0.882 · F1 0.883 · IoU 0.791 |
| real_pair | detect changes | 16,685 px, same as baseline | — |
| levir_100 before twice | detect building changes | **0 px**, no false change | — |
| sentinel2 | detect changes | 0 px, same as baseline | — |
| levir_100 | has any new building been constructed? | "Yes", with CDVQA set aside | — |
| levir_105 | were any buildings demolished? | reports 5.03 % change but **never answers yes or no** | — |
| satquery before/after (= levir_100, same md5) | how many new houses were built and where? | reports 11.35 % and 181 regions; **no house count** | — |

**Small objects (Grounding DINO + SAM 2):** `mask airplanes` gave 9 masks, same as baseline, covering all ~7
planes, so a few planes are double-masked. `mask the airplane` on the airport-apron tile masked only the
airliner; the plural prompt also picks up two jet bridges. `mask red cars` gave 2 and `mask white houses` 5, both
the same as baseline. `find the red car parked next to the big white house` found the right car.
`find cars near red house` gave 3, same as baseline. `mask the ships` on the tennis tile correctly returned
nothing. `segment the largest airplane` picked the twin-engine plane, which is plausible, with verifier
confidence 0.39. `how many airplanes are parked here?` was routed to the VQA model, which answered 7
(plausible). **`mask tennis courts` failed:** it masked the grass field plus the whole court complex (51 % of
the image). That is the README's known weakness, reproduced on a different tile.

**Video:** `find all vehicles` gave the same 2 events as the baseline (14.88–18.72 s, 25.44–27.36 s). The
patrol clip gave 0 events, and `find airplanes` gave 0. `when does a red car appear?` gave 1 event
(15.36–18.72 s), verified in 3 of 3 frames, and it is the red car. `find the white car` gave 3 events.

### 2. Two bugs found and fixed

1. **The keyframe box and outline pointed at different cars.** SAM 2 video propagation tracks one anchor
   object. `video_analysis.py` then attached that object's mask to every detection in any propagated frame. In
   keyframe 198 the box was on the silver car and the outline on the red car, and the event score used the red
   car's SAM score. Now a propagated mask is attached only when it lies inside the detection's box
   (≥ 50 % of mask pixels inside and bounding-box IoU ≥ 0.3, `_mask_fits_box`). Any other detection is
   segmented on its own box with SAM 2 image mode, which is the fallback already used for the anchor. A trace
   step records how many detections this applied to.
2. **Question words became the class.** `parse_v4_query` had no stop words for question or video phrasing, so
   "when does a red car appear?" became the Grounding DINO prompt `red when does car appear.`, and that text was
   drawn on the keyframe. Added: when, what, which, does, do, did, appear(s/ed/ing), shown, seen, time, moment,
   video, clip, footage. The prompt is now `red car.`.

### 3. Blast radius

- Event timings are unchanged. Event scores shift slightly because they now use the correct object's mask
  (real footage, first vehicles event: 0.6403 → 0.7524).
- More SAM 2 image calls per video, one per unmatched detection. The white-cars clip still finishes in about
  a minute.
- The stop words also apply to image prompts. "time", "video" and "clip" can no longer be requested as object
  classes.
- **Still weak, not fixed:** tennis courts / large flat areas; count questions about change ("how many new
  houses") answered as a percentage; demolition questions not answered yes/no, since ChangeFormer cannot tell
  construction from demolition and CDVQA is set aside; plural "airplanes" picking up jet bridges.

### 4. Verification

- `tests/unit/test_video_mask_match_and_question_words.py`: 8 tests, including frame 198's geometry and four
  query phrasings.
- Full `tests/unit` plus the grounding-workflow and model-registry tests: 229 passed, 1 skipped. An earlier run
  with the backend still holding the GPU failed two video tests; they pass once the GPU is free, as the README
  warns.
- Re-run on the fixed backend: the red-car event is labelled `red car`; keyframe 198 no longer outlines the red
  car; real-footage events are unchanged.

### 5. Defence — "Your video demo showed the wrong car outlined"

"It did, and we traced why: one tracked mask was being reused for every event. Each event now gets a mask of its
own object, checked against its box, and there's a test built from the exact frame that showed the bug."

---

## Q-025 · Hosted-backend groundwork: API keys, DB-less video results, and answers written from measured evidence

**Recorded** 2026-09-16, branch `cloud-gpu` (worktree off `prototype` `0c8b74d`), commits `e8b402b`, `9688a48`,
`a95c9b0`, `22c329a`. Plan: `docs/superpowers/plans/2026-09-15-cloud-gpu-and-answers.md` Tasks 1–4.
15 files, +455/−1. Not yet merged into `prototype`; not yet exercised against a live LLM provider.

### 1. Mechanism

1. **API keys** — `backend/app/api/auth.py:26` `ApiKeyMiddleware.dispatch` reads `SATQUERY_API_KEYS` on every
   request (comma list). Empty → request passes (local runs unchanged). Otherwise the key is taken from
   `Authorization: Bearer`, `X-API-Key`, or `?key=` (`auth.py:17`) and compared with `hmac.compare_digest`.
   `OPTIONS` and `OPEN_PATHS` (`auth.py:10`: `/api/health`, `/docs`, `/redoc`, `/openapi.json`) are always open.
   Failure → 401 `{"error": {"code": "UNAUTHORIZED", ...}}`. Registered at `backend/app/main.py:43`, *before*
   `CORSMiddleware`; Starlette wraps later-added middleware outside, so CORS is outermost and the 401 still carries
   `access-control-allow-origin`. `SATQUERY_CORS_ORIGINS` overrides the origin list (`config.py:263`).
2. **Video results without a DB row** — `GET /api/video/{id}` (`endpoints/video.py:266–282`) wraps the repository
   lookup in try/except; on no row or DB error it loads `result.json` (`video.py:273`, written by
   `POST /api/video/analyze`, Q-017) and returns it if it has `flags` and `video_metadata`; otherwise 404 as before.
3. **Answer writer** — `backend/app/answers/writer.py`. After a non-FAILED pipeline, `controller.py:233–235` calls
   `apply_answer_writer(state)` (`writer.py:148`). If `SATQUERY_ANSWER_WRITER` is not `on`, nothing happens.
   Otherwise `evidence_for_writer` (`writer.py:130`) builds a JSON of task, models, confidence, area statistics,
   detection labels+scores (≤50), whitelisted metadata (`instance_count`, `instance_filters`,
   `agent_deliberation`, `aoi`, `change_inference`), the scene model's text answer, and warnings — **no image**.
   `write_answer` (`writer.py:81`) posts it, off the event loop (`asyncio.to_thread`), to Gemini
   (`gemini-2.5-flash`) then NVIDIA NIM (`meta/llama-3.3-70b-instruct`) via the OpenAI-compatible
   `/chat/completions`, 8 s timeout, temperature 0.2, max 300 tokens. The first non-empty reply that passes
   `numbers_grounded` (`writer.py:64`) becomes `state.answer`; missing key → provider skipped; HTTP error, empty
   reply, or ungrounded number → next provider; all fail → template answer kept. A trace step
   "Answer written from measured evidence" records `source` and every attempt's status.
4. **Response + UI** — `AnalyzeResponse` gains `answer_source` (default `"template"`, else `"<provider>:<model>"`)
   and `answer_facts` (the template answer the text was based on) (`schemas/responses.py:59–60`). The results
   panel shows "Written by <source> from measured evidence" or "Measured answer", with the facts as hover text.

### 2. Rationale

- **App-level keys, not Modal proxy tokens** — `<video src>` and download links cannot send headers, so the key
  must also work as `?key=`; one key per teammate can be revoked by editing one env var (design D4).
- **Rephrase, don't generate** — the template answer is computed from measurements; the LLM only rewords it for
  the question. Sending the image was rejected: Gemini's free tier may use inputs for training, and an LLM that
  sees the image can "see" things the measurements do not support (D7).
- **Number guard over trusting the model** — every number in the reply is parsed (`_NUMBER` regex, commas
  stripped) and must match a number in the evidence text within ±0.05 absolute or ±0.5 % relative, or equal a
  ≤1 ratio ×100 (so `0.1135` permits "11.35 %"/"11.4 %"). Measurable and explainable on stage (D8).
- **Off by default** (D9) — `tests/conftest.py` forces `SATQUERY_ANSWER_WRITER=off`, so no test touches the network.

### 3. Blast radius

- Wrong middleware order → browser shows a CORS error instead of "API key rejected"; guarded by
  `test_missing_or_wrong_key_is_401_with_cors_header`. The task reviewer also checked video Range/206 seeking still
  works through `BaseHTTPMiddleware` (Starlette 1.6.0: `206`, `content-range: bytes 100-199/10000`).
- With `SATQUERY_API_KEYS` unset, behaviour is identical to before — local runs and the existing suite unaffected.
- Writer failure modes all degrade to the template answer; they cannot fail the job. **Known weakness (open):**
  the user's own question is part of the evidence text (`writer.py:111`), so a number typed in the question
  counts as grounded — "were 42 buildings built?" would let "42 buildings were built" through the guard.
  Logged for the branch's final review; not yet fixed.
- Guard tolerance literal is `0.051`, not `0.05` (float slack) — a 0.001 widening of D8.
- An old-schema video `result.json` that fails `VideoAnalysisResponse(**saved)` gives a 500, not a 404.

### 4. Verification (as run, GPU hidden, `CUDA_VISIBLE_DEVICES=""`)

- `tests/unit/test_api_key_auth.py` — RED 1 failed / 5 passed (the 401 case returned 404); GREEN **6 passed**.
- `tests/unit/test_video_result_fallback.py` — RED 1 failed / 1 passed; GREEN **2 passed**; `test_video_api.py` 3 passed.
- `tests/unit/test_answer_writer.py` — **7 passed** (plan said 8: miscount, the file has 7 tests); HTTP is
  `httpx.MockTransport`, asserting host, Bearer header, and that the body contains no `data:image`.
- `tests/unit/test_answer_writer_wiring.py` — RED `AttributeError` (no `apply_answer_writer` in controller);
  GREEN; combined with the writer tests **8 passed**. A real `POST /api/upload` + `POST /api/analyze`
  ("compute NDVI for this scene" on a 64×64 PNG, COMPLETED via the unsupported-request path) returns
  `answer_source` and a non-empty `answer_facts`.
- Frontend: `npx tsc --noEmit` exit 0; eslint exit 0 (1 pre-existing unused-import warning in `ResultsPanel.tsx:3`).
- Each test run printed 2 pre-existing warnings (`StarletteDeprecationWarning`: httpx with TestClient).
- **Not yet verified:** a real Gemini/NVIDIA reply; the full `tests/` tier on this branch (≈30 min on CPU for
  `tests/unit` alone; pending).

### 5. Defence — "How do you know the LLM didn't make up the numbers?"

"It isn't allowed to. It only gets the measurements as JSON, never the image, and every number in its reply is
checked against that JSON — within rounding — before we show it. If one doesn't match, we throw the reply away
and try the next provider, and if none pass we show the plain measured answer. The response says which one you
got: `answer_source` is `template` or the provider and model, and `answer_facts` carries the measured sentence
it was written from. The one gap we know about: a number you type in your own question also counts as allowed,
which we're closing next."

---

## Q-026 · Qwen3-VL scene model (unmeasured), VRSBench scorer, Modal deployment, results retention, frontend connection

**Recorded** 2026-09-16, branch `cloud-gpu`, commits `35cbd93`, `644f553`, `912bb69`, `c85c2c8`, `3ae4e41`,
`b17c4e9`, `21221a3`, `5664a74` (plus `77bd612`, see §0). Plan Tasks 5–8 and 6b. Not merged into `prototype`;
nothing here has run on a GPU or on Modal yet.

**Numbering note (merge, 2026-09-17).** Written on branch `cloud-gpu` as Q-021/Q-023/Q-024 while `prototype`
independently recorded its own Q-021–Q-024. On merging `prototype` into `cloud-gpu` the branch entries were
renumbered Q-025/Q-026/Q-027; only IDs and cross-references changed.

### 0. Correction to this branch's Q-025 (hosted-backend groundwork)

That entry said writer failures "all degrade to the template answer; they cannot fail the job". That was **wrong
when written**: only per-provider network errors were caught. An exception in `evidence_for_writer` or elsewhere in
`write_answer` propagated out of `run_pipeline` and turned a completed analysis into a 500. Found by the Task 4
review; fixed in `77bd612` — `apply_answer_writer` now catches any exception, logs it, records a `warning` trace
step `source=template; writer error: <Type>`, and returns the template answer
(test `test_apply_answer_writer_degrades_to_template_on_exception`). The Q-025 text stays as written.

### 1. Mechanism

1. **Scene model** — `backend/app/ml/adapters/scene_vlm.py`, registry key `scene_vlm`, adapter name `SceneVLM`
   (the name `evidence_for_writer` looks for). `is_available()` (`scene_vlm.py:23`) is true only if enabled **and**
   CUDA is present **and** `checkpoints/scene_vlm_qwen3vl4b_nf4` exists — it never downloads at request time.
   `load_model` (`:30`) loads the pre-quantized NF4 weights in fp16 (no bf16: T4 has no native bf16). `predict`
   (`:50`) thumbnails to ≤1024 px, prompts "answer only from what is visible … one to three sentences", greedy
   decode, ≤200 new tokens. `run_vqa`/`run_caption` (`agent/tools/inference.py:58,66`) now share
   `_run_scene_model` (`:39`), which takes `scene_vlm` if available, else `general_rs_vlm` (BLIP), else a
   NOT_CONFIGURED answer. Side effect: `run_caption` now also copies the model's warnings into the job (it did not
   before). `scripts/prepare_scene_vlm.py` downloads Qwen/Qwen3-VL-4B-Instruct and saves the NF4 copy — **not run yet**.
2. **VRSBench scorer** — `scripts/eval_scene_vlm_vrsbench.py --adapter {general_rs_vlm,scene_vlm} --n 200 --seed 0`.
   Same `random.Random(seed)` sample for both adapters (sampling does not depend on `--adapter`). VQA correct = the
   normalised ground truth equals, or appears as a whole word in, the normalised prediction; captions scored by
   ROUGE-L F1. A sample that throws is recorded with its error and scored wrong / 0.0 (`644f553`), and
   `vqa_errors`/`caption_errors` are reported, so a crash cannot silently favour either model.
3. **Results retention** — `purge_old_results` (`artifacts/manager.py:156`) runs from `lifespan` (`main.py:28–31`)
   only when `SATQUERY_RESULTS_RETENTION_DAYS` is set (`retention_days_from_env`, `:202`; the Modal image sets 7).
   It deletes a direct child of the results dir only if: name matches `_JOB_ID`, not a symlink, is a directory,
   contains `result.json` or `input/` (`_is_job_workspace`, `:139`), and mtime is older than the cutoff. Listing
   errors → warning, `[]`; per-folder errors → warning, skipped. Never raises.
4. **Modal** — `deploy/modal_app.py`: debian-slim py3.11 + cu128 torch + `backend/requirements.txt`; `backend/` and
   `configs/` copied in; `/root/isro/checkpoints` → volume `satquery-models`; `HF_HOME=/models/hf`; results on volume
   `satquery-results`; secrets from `deploy/.env.modal` (gitignored; template `.env.modal.example`).
   `gpu=T4` (env `SATQUERY_MODAL_GPU`), `scaledown_window=300`, `max_containers=1`, 4 concurrent inputs,
   `min_containers` from `SATQUERY_MIN_CONTAINERS`. `warm_hf_cache` pre-downloads Grounding DINO base and SAM 2.1 small.
5. **Frontend connection** — `frontend/src/lib/connection.ts`: base URL + key in `localStorage`; `http()` sends
   `Authorization: Bearer`; `mediaUrl()` prefixes `/…` paths with the base and appends `?key=` to http(s) URLs only
   (never `blob:`/`data:`, never twice). `useConnection()` (`:85`, `useSyncExternalStore`) makes every component that
   renders a backend URL re-render once the stored values are known after hydration. `/system` has a
   "Backend connection" panel: Save & test → `GET /api/results/connection-check` (404 = reachable and authorised,
   401 = "API key rejected", network error = "backend unreachable at <url>", >3 s = "Waking GPU (~60 s)…"); a base
   without `http://`/`https://` is refused.

### 2. Rationale

- **Qwen3-VL-4B NF4 over BLIP** — BLIP-VQA answers in one or two words ("Football field."), which the answer writer
  cannot turn into a grounded sentence. Qwen3-VL-4B is Apache-2.0 and ~3 GB at 4-bit (estimate). GeoChat-7B was
  rejected in the design (size, licence). **The switch is conditional**: keep `scene_vlm` only if, on the same 200+200
  VRSBench samples, its VQA accuracy ≥ BLIP's and caption ROUGE-L > BLIP's. `enabled: true` is committed now only
  because availability also requires the checkpoint, which does not exist yet — so today BLIP is still what runs.
- **Retention markers over name-only matching** — the first version (`c85c2c8`) matched folder names only; the
  review showed `results/evaluations/` matches and would be deleted, and that an unreadable volume would crash
  startup. Fixed in `3ae4e41`. Cost: an old folder with neither marker (upload aborted before `input/` existed) is
  kept forever — harmless.
- **`useSyncExternalStore` over reading `localStorage` in render** — the first frontend version (`21221a3`) read the
  key during render; the server-rendered HTML then carries `http://localhost:8000` with no key, and React 19 does not
  repair mismatched `src`/`href` on hydration, so cloud images/video could stay broken. Fixed in `5664a74`.

### 3. Blast radius

- Scene model: with no checkpoint (today) behaviour equals BLIP's; if the Qwen path fails at load, `InferenceError`
  surfaces for VQA/caption jobs — no fallback to BLIP after a failed Qwen load (not implemented).
- `max_containers=1`: all teammates share one GPU container; concurrent heavy jobs queue (4 inputs at a time).
- **Open risk (not changed here):** LocateAnything is the grounding fallback when DINO finds nothing
  (`workflows/grounding.py:218`) and reports itself available whenever `transformers` imports. In the cloud image its
  weights and gitignored vendored code are absent, so that fallback would try a 7.2 GB Hugging Face download mid-request.
  Owned by the parallel LocateAnything work; decision pending with the user.
- Retention deletes user results on the cloud volume after 7 days (user asked to confirm 7).
- `?key=` in media URLs appears in browser history and server access logs — inherent to design D4.

### 4. Verification (as run, GPU hidden)

- `tests/unit/test_eval_scene_vlm_metrics.py` — RED import error → **2 passed**.
- `tests/unit/test_scene_vlm_selection.py` — RED (VQA got the BLIP answer) → **3 passed**; related files
  (`test_video_workflow`, `test_gpu_oom_recovery`, `test_agent`, `test_optical_sar_safety`) **17 passed** in 21 min 34 s
  on CPU. `model_registry.get_adapter('scene_vlm')` → `SceneVLM False` (no CUDA, no checkpoint).
- `tests/unit/test_results_retention.py` — first version 7 passed; fix round RED **2 failed / 7 passed**
  (PermissionError propagated; `evaluations/` deleted) → GREEN **9 passed**; with `test_results_download.py` 27 passed.
- Full `tests/unit` at `3ae4e41`, `CUDA_VISIBLE_DEVICES=""`: **248 passed, 1 skipped, 12 warnings, 946 s**.
- `deploy/modal_app.py`: `py_compile` only (no `modal` package locally). Task reviewer checked every Modal call used
  (`Secret.from_dotenv`, `@modal.concurrent`, `@modal.asgi_app`, `scaledown_window`, `min_containers`) against the
  current Modal docs: current.
- Frontend at `5664a74`: `tsc --noEmit` clean; eslint on changed files: 1 error + 6 warnings, all pre-existing
  (`MapViewer.tsx:71` set-state-in-effect); `next build --webpack` succeeds (Turbopack refuses the worktree's
  symlinked `node_modules` — environment, not code).
- **Not yet verified:** any Qwen3-VL or BLIP score; checkpoint size; a real `modal deploy`; cold/warm latency;
  the connection panel in a browser; hydration behaviour at runtime.

### 5. Defence — "Why should we believe Qwen is better than BLIP?"

"You shouldn't yet, and the code doesn't assume it. Both models get scored on the same 200 VRSBench questions and
200 captions with the same seed, failures counted as wrong, and Qwen is only kept if it's at least as accurate on
questions and strictly better on captions. Until that run happens the deployed system still answers with BLIP —
Qwen only switches on when its weights are present, and those weights are only uploaded after it wins."

---

## Q-027 · Final-review fixes on `cloud-gpu`, and corrections to this branch's Q-025/Q-026

**Recorded** 2026-09-16, branch `cloud-gpu`, commit `960bdb0` (on `f7320e5`). Source: final whole-branch review of
`0c8b74d..f7320e5` ("ready to merge with fixes"), one fix wave, one scoped re-review ("all findings addressed").
(Written as Q-024 on the branch; renumbered at merge — see the note in Q-026.)

### 1. Mechanism — what changed

1. **Guard no longer counts the question as evidence** — `write_answer` (`backend/app/answers/writer.py:96–105`)
   builds two texts: the prompt text (still contains the query) and `guard_text` (no `query`), which the number check
   uses (`writer.py:130`). `guard_text` still contains the measured template answer.
2. **Sign-insensitive matching** — `numbers_grounded` (`writer.py:64–79`) compares absolute values, so evidence
   `-3.2` grounds "decreased by 3.2 %".
3. **`confidence` is not guard evidence** — excluded from `guard_text` (`writer.py:99`), still sent to the model; so
   `confidence: 0.85` no longer grounds "85 ships" through the ×100 rule. Real ratios (`change_ratio`) still work.
4. **Non-ASCII API key → 401** — `auth.py:31` compares bytes; `hmac.compare_digest` on non-ASCII `str` raised
   `TypeError` → 500 (measured by the reviewer: `?key=é` → 500 before, 401 after).
5. **Old-schema video `result.json` → 404** — `video.py:207–211` catches pydantic `ValidationError`.
6. **`scene_vlm` permitted by the plan validator** (`agent/validator.py:36`). Deliberately *not* added to the
   capability registry's `required_models`: the planner copies that list into `selected_models`, and
   `dependency_checker.py:65–73` returns 503 for any required model that is not on disk (only `general_rs_vlm` is
   exempt), so every VQA/caption request would fail on a deployment missing either scene model, and `models_used`
   would name a model that never ran. `_run_scene_model` already records the model it actually used.
7. **`transformers>=4.57.0`** in `backend/requirements.txt` (Qwen3-VL and the `dtype=` keyword need it; 5.16.1 installed).
8. **Strict VQA metric** — `scripts/eval_scene_vlm_vrsbench.py:26–40` adds `vqa_strict_correct` (normalised exact
   match, or first token equals a one-word ground truth) and reports `vqa_accuracy_strict` next to the lenient
   `vqa_accuracy`; the VQA loop appends " Answer with a single word or short phrase." to the question for **both**
   adapters. The lenient metric gave credit for "There are 2 or 3 buildings" (gt "2") and "not yellow" (gt "yellow"),
   which favours the model that writes sentences (Qwen) over the one-word model (BLIP). **The Qwen keep/drop decision
   will be taken on `vqa_accuracy_strict`.**
9. **Connection check** — `ConnectionPanel.tsx:67–90`: `GET /api/health` first (unreachable → "backend unreachable
   at <url>"), then the protected probe: 401 → "API key rejected"; 404/400 → "Connected"; anything else →
   "unexpected status <code>". Previously any non-401 (500, 502, Modal's 404 for a wrong subdomain) read as
   "Connected".

### 2. Corrections to earlier entries on this branch (they stay as written)

- **Q-025 §3** cites the query weakness at `writer.py:111`; the query was added at `writer.py:89` (line 111 was the
  reply-text line). The weakness itself is now fixed (item 1).
- **Q-025 §5 defence** ("It only gets the measurements as JSON") overstated: the evidence also carries the scene
  model's free-text answer (`scene_model_answer`), whose numbers are the VLM's words, not measurements, and they
  **do** pass the guard. Still true after `960bdb0`.
- **Q-026 §1.5** said "404 = reachable and authorised"; the code at `f7320e5` treated every non-401 as connected.
  Fixed by item 9.

### 3. Blast radius — what is still open (measured or confirmed, not fixed)

- **Wrong direction passes the guard.** With absolute-value matching, "increased by 3.2 %" for evidence `-3.2`
  passes, as does the correct "decreased". The guard checks that numbers are present, not what they mean. Before
  `960bdb0` both sentences were rejected.
- **`detections[].score` (≤1) can still ground a count via ×100**, like `confidence` did (`writer.py:152`).
- **LocateAnything cloud fallback (R10)** — unchanged; must be decided before `modal deploy` (see Q-026 §3).
- `test_orchestration_capabilities.py` fails to collect when run alone (circular import
  `capability_registry → agent/__init__ → controller → planner → capability_registry`); reported by the fix agent as
  reproducing on unmodified `f7320e5`; passes inside the full suite.

### 4. Verification (as run, GPU hidden)

- Touched test files + `test_answer_writer_wiring.py`, `test_agent.py`, `test_orchestration_capabilities.py`,
  `test_routing_unsupported.py`: **56 passed** (fix agent); re-reviewer re-ran them independently: all pass
  (`test_answer_writer.py` 13/13, `test_api_key_auth.py` 7/7, `test_video_result_fallback.py` 3/3,
  `test_eval_scene_vlm_metrics.py` 7/7, orchestration/agent files 25/25).
- RED evidence: items 4, 5, 8 by temporarily reverting each fix (fix agent); items 1–3 by the re-reviewer against a
  copy of the pre-fix `writer.py` — "42 buildings" reply accepted, "decreased by 3.2 %" rejected, "85 ships" with
  `confidence 0.85` accepted — all as the findings described.
- Frontend: `tsc --noEmit` clean, eslint clean on the changed file, `next build --webpack` succeeds.
- Full `tests/unit` last ran at `3ae4e41` (248 passed, 1 skipped); not re-run after `960bdb0`.

### 5. Defence — "Your guard would let 'increased by 3.2 %' through when it actually decreased."

"Yes — the guard is a check that every number the model writes was measured, not a check of the sentence's meaning;
we say so in the record. What stops a wrong direction is the prompt, which gives the model the measured sentence
('decreased by 3.2 %') to rephrase, and the response carries that measured sentence in `answer_facts` next to the
written one, so anyone can compare them. Sign-aware checking is the next step; we chose to accept correct
restatements of negative changes rather than throw all of them away."

---

## Q-028 · Merge into `prototype`; Qwen3-VL beats BLIP on VRSBench (measured); answer-writer models replaced

**Recorded** 2026-09-17. Merge commit `69290bd` (`prototype` 55f76b3 merged into `cloud-gpu`, then `prototype`
fast-forwarded to it). Measurements on the RTX 3070 (8 GB), branch at `69290bd`. The writer model choice is
configuration (`.env`, `deploy/.env.modal`), not a commit.

### 1. Mechanism

1. **Merge.** Only `project/qna.md` conflicted: `prototype` had recorded its own Q-021–Q-024 (LocateAnything
   bring-up and removal, hard-prompt sweep). Those stay; the `cloud-gpu` entries became Q-025–Q-027 (IDs and
   cross-references only — note inside Q-026). `a56eaeb` removed LocateAnything, which closes the cloud-fallback risk
   Q-026 §3 left open (R10).
2. **Scene-model decision (plan Task 6 step 6).** `scripts/eval_scene_vlm_vrsbench.py --n 200 --seed 0` for both
   adapters; the script verified identical VQA questions and caption images across the two runs.
   Rule fixed before measuring (Q-027 §1.8): keep `scene_vlm` only if strict VQA accuracy ≥ BLIP's **and** caption
   ROUGE-L > BLIP's. Both met → `scene_vlm` stays enabled; with its checkpoint present it now answers VQA/captions
   (locally already, since `checkpoints/` is shared).
3. **Qwen checkpoint.** `scripts/prepare_scene_vlm.py`: Qwen/Qwen3-VL-4B-Instruct (8.3 GB HF snapshot) →
   `checkpoints/scene_vlm_qwen3vl4b_nf4`, **2.7 GB** (`model.safetensors` 2,874,045,174 bytes), 24 s, peak RSS 5.1 GB.
4. **Answer-writer models.** Live probes with the team's keys: `gemini-2.5-flash` → 404 "no longer available to new
   users"; `meta/llama-3.3-70b-instruct` → 410 "end of life 2026-08-26". Most other NIM chat models on this account
   → 404 (not available) or 503 (overloaded). Chosen, via env: `GEMINI_MODEL=gemini-3.5-flash-lite`,
   `NVIDIA_MODEL=openai/gpt-oss-20b`. The code defaults in `writer.py` still name the dead models — anyone running
   without these env vars gets the template answer.

### 2. Measured (verbatim)

| Same 200 VQA + 200 captions, seed 0 | BLIP (`general_rs_vlm`) | Qwen3-VL-4B NF4 (`scene_vlm`) |
|---|---|---|
| VQA accuracy, lenient | 0.240 | 0.420 |
| VQA accuracy, strict (decision metric) | 0.235 | **0.420** |
| Caption ROUGE-L | 0.0140 | **0.1882** |
| Caption mean words | 1.145 | 64.33 |
| Seconds per sample | 0.102 | 2.217 |
| Errors (VQA / caption) | 0 / 0 | 0 / 0 |
| Wall time / peak RSS | 52 s / 1.95 GB | 14 min 56 s / 3.7 GB |

Strict VQA correct by question type (n): existence 37 → BLIP 13, Qwen 26; colour 29 → 10, 15; category 27 → 4, 9;
position 25 → 3, 9; scene type 20 → 3, 9; **quantity 39 → BLIP 9, Qwen 5**; shape 7 → 0, 3; reasoning 4 → 0, 2.

Answer-writer probes (real `write_answer`, 8 s timeout):
- `gemini-3.5-flash-lite`: 1.0–1.4 s; "has any new building been constructed?" → written answer accepted;
  "mask airplanes" → "Detected 3 airplane instances with masks covering 7.75% of the image." accepted;
  "Were more than 50 new buildings built here?" → reply repeated "50" → **rejected → template** (Q-027 item 1 working).
- `openai/gpt-oss-20b`: 5.3–8.1 s; one call exceeded 8 s (`error`); others accepted.
- `gemini-3.6-flash`: 13.3 s — would exceed the 8 s timeout; not used.

### 3. Blast radius

- **Qwen is weaker at counting than BLIP on this sample** (5 vs 9 of 39). Part of it is the scorer: Qwen answers
  "One"/"Five" and the strict metric compares against "1"/"5", so number words score wrong. Not corrected here; the
  counts are reported as measured. Counting questions on stage should go through detection (Grounding DINO + SAM 2
  instance counts), not the scene model.
- Qwen is 22× slower per sample on the 3070 (2.2 s vs 0.10 s) and writes 64-word captions.
- **Rejected prompt change (recorded because it is a guard weakness):** adding "never repeat a number from the
  QUESTION… refer to it in words" made `gemini-3.5-flash-lite` answer "change detection confirmed that more than that
  many new structures were built" (the evidence says nothing about a building count) and spell numbers as words
  ("zero point eight one", "over one hundred thousand"), which the digit-only guard cannot check. Not adopted. The
  guard remains blind to numbers written in words.
- The NVIDIA fallback sits near its timeout; if Gemini is down, some answers will fall back to the template.
- **Local environment change, not from this branch:** `rasterio` 1.4.4 appeared in the shared `.venv` on
  2026-09-17 10:12 IST (installed with the segmentation-training packages). `backend/app/geo/raster.py` prefers
  rasterio when importable, and 3 tests in `tests/unit/test_geotiff_georeferencing.py` then fail (nodata tag,
  user-defined CRS, GeoJSON polygon in WGS84). Full `tests/unit` on the merged tree: **267 passed, 3 failed, 878 s**;
  the same tests passed at `3ae4e41` before the install, and no geo code changed. The Modal image does not install
  rasterio. Open.

### 4. Verification

- Result files: `results/evaluations/scene_vlm_vrsbench_general_rs_vlm_20260917.json`,
  `…_scene_vlm_20260917.json` (gitignored); sample identity asserted when comparing.
- Merge: `git merge-base --is-ancestor prototype cloud-gpu` true; `git merge --ff-only` in the main checkout left its
  uncommitted `project/manual-tasks.md` and untracked training files untouched.

### 5. Defence — "Your VLM can't even count."

"On our 200-question sample it counted worse than BLIP — 5 against 9 of 39 — and we say so. Part of that is our
scorer marking 'Five' wrong against '5', but we haven't corrected for it. Everywhere else it was better — 42 % against
23.5 % overall, and captions went from one word to real descriptions. Counting in our pipeline is done by the
detector and segmenter, which give an instance count with a mask per object; the scene model is for describing the
scene, not for counting."

---

## Q-029 · SatQuery AI runs on a Modal T4: deployment, key check, and the five demo prompts end to end

**Recorded** 2026-09-17, `prototype`/`cloud-gpu` at `a4f863e` (`scripts/cloud_smoke.py`), app
`https://ushnik1p2h3d--satquery-ai-api.modal.run` (Modal workspace `ushnik1p2h3d`, app `satquery-ai`).
All requests sent from the RTX 3070 machine with `CUDA_VISIBLE_DEVICES=""` — nothing ran on the local GPU.

### 1. Mechanism

1. Weights uploaded to volume `satquery-models` (`modal volume put`, 333 s for Qwen + BigEarthNet; the rest earlier).
   An upload interrupted by the 11:02 machine freeze was re-sent with `--force` for the folder in flight
   (BigEarthNet); Qwen had not started. Afterwards, sizes of all 29 files on the volume were compared with the local
   copies (Modal reports rounded sizes; local sizes rounded the same way): 0 mismatches.
2. `modal run deploy/modal_app.py::warm_hf_cache` downloaded Grounding DINO base and SAM 2.1 small into the volume's
   HF cache. Two failed attempts first: local `python-dotenv` missing (needed by `Secret.from_dotenv`), then a
   Modal-side "image build terminated due to external shut-down"; the third succeeded.
3. `modal deploy deploy/modal_app.py` (5 s once the image existed). Secrets from `deploy/.env.modal` (gitignored):
   six per-person `SATQUERY_API_KEYS`, Supabase `DATABASE_URL`, Gemini/NVIDIA keys and model names, `HF_TOKEN`, CORS.
4. `scripts/cloud_smoke.py <url> <key>` uploads the demo files and runs: mask airplanes, mask white houses, "what is in
   this image?", "has any new building been constructed?" (LEVIR pair), "find red car" (video); downloads each
   result zip.

### 2. Measured (verbatim)

- `/api/health` first call after deploy: **200 in 23.6 s**, `device: cuda`, `database_connected: true`,
  models available: all except `general_rs_vlm` (BLIP, not uploaded since Qwen won — Q-028); `scene_vlm: true`.
- Auth: no key **401**, wrong key **401**, `?key=é` **401**, valid key → **404** for a non-existent job (2.4 s).
- Demo prompts (seconds, all `COMPLETED`, all zips HTTP 200):

| Case | first model use | warm | answer source | zip |
|---|---|---|---|---|
| mask airplanes | 47.1 | 22.8 | gemini:gemini-3.5-flash-lite | 1.26 MB |
| mask white houses | 32.4 | 24.3 | gemini:gemini-3.5-flash-lite | 1.64 MB |
| what is in this image? | 49.2 | 20.9 | gemini:gemini-3.5-flash-lite | 0.98 MB |
| has any new building been constructed? | 115.0 | 91.7 | gemini:gemini-3.5-flash-lite | 15.6 MB |
| find red car (video) | 105.4 | 110.4 | — (video path has no writer) | 2.44 MB |

- Answers: airplanes — 9 instances, 13,795 px, mean SAM 2 score 0.876; white houses — 5 instances, 7,599 px, mean
  0.942; scene — "aerial view of a residential neighborhood featuring houses, streets, and parked cars…"; change —
  "Yes, building change is detected in the analysed area across 181 regions, covering 11.35% of the area.";
  video — one flag 15.36–18.72 s (the expected event).
- Warm `/api/health`: 2.2–2.4 s.

### 3. Blast radius

- **Slow for a live demo on a T4:** change 92 s and video 110 s warm. The times include the upload from India and
  the result download (change zip 15.6 MB); the split between network and GPU time was not measured. An L4
  (`SATQUERY_MODAL_GPU=L4`) was not tried.
- Cold start after 5 idle minutes needs ~24 s before the first request, plus 30–70 s per model on first use —
  demo day should use `SATQUERY_MIN_CONTAINERS=1` and one warm-up run of each prompt.
- `max_containers=1`: all six people share one GPU container.
- The five prompts are the only end-to-end cloud evidence so far; the browser UI against the cloud (plan Task 9
  step 3) has **not** been run yet.
- Local machine: the 11:02 hard freeze and a later kernel OOM kill (11:08:28, a 300 MB training process) happened
  while a parallel session trained a road-segmentation model (≈5 GB RAM with 4 loader workers) on a 15 GB machine.
  The Modal upload held 1.2 GB during the Qwen file. No cause for the freeze was logged.

### 4. Verification

- Result files: `results/evaluations/cloud_smoke_20260917_1123.json` (first use), `…_1128.json` (warm).
- Modal run log: `https://modal.com/apps/ushnik1p2h3d/main/deployed/satquery-ai`.

### 5. Defence — "Does this really run without a GPU on the laptop?"

"Yes — every number here was measured from a machine with its GPU hidden from Python. The laptop only uploads the
image and draws the result; detection, segmentation, change detection and the scene model run on a T4 in Modal. The
honest cost is time: about 20–25 seconds for a mask or a scene question once warm, and a minute and a half to two
minutes for change detection and video."

---

## Q-025 · First trained road segmenter: IoU 0.031 → 0.540 (DeepGlobe) and 0.021 → 0.606 (Massachusetts) against the live pipeline

**Recorded** 2026-09-17, atop `prototype` `55f76b3`. The work is uncommitted at the time of writing. It
follows up Q-020, where "mark the roads" was traced to low detector recall rather than too little training.
All numbers were measured on the RTX 3070 (8 GB) with 14.7 GB RAM.

### 1. Mechanism — what was built and run

- **Data** (`datasets/manifests/training_sources.yaml`, `scripts/download_training_data.py`): 14 sources from
  Kaggle, the Hugging Face Hub and the SpaceNet S3 bucket, fetched into `datasets/raw/<name>/` (gitignored).
  Downloads resume, and a `.complete` marker is written per dataset. The HF mirror
  `micahter/spacenet-road-dataset` was **rejected**: it holds vector road graphs only, with no masks. SpaceNet 3
  comes from the official bucket instead: PS-RGB tiles plus speed geojson for all four cities, about 28 GB. The
  full tarballs would have been larger and would have added MS, PAN and PS-MS imagery that we do not use.
- **Loader** (`training/segmentation/datasets.py`): each tile carries its ground sampling distance (DeepGlobe
  0.5 m, Massachusetts 1.0 m, SpaceNet and WHU 0.3 m). Everything is resampled to **0.5 m**, so a road has the
  same width in pixels whichever dataset it comes from. For training, a random window is cut from the *original*
  tile and only that window is resized (`read_crop`). The first version resized whole 1500² Massachusetts tiles
  to 3000² before cropping. That made data loading the bottleneck: 220 s per epoch, with the GPU idle between
  batches, against 74 s after the fix. Pure-white pixels mark no-data in the Massachusetts tiles and are
  excluded from both the loss and the metrics.
- **Splits.** Massachusetts uses its official split (1108/14/49 tiles). DeepGlobe publishes masks only for its
  train set, so its tiles are divided 90/5/5 by a SHA-1 hash of the tile id (5609/320/297). **The DeepGlobe
  test split is therefore not the standard DeepGlobe benchmark**, and our numbers are not directly comparable
  to published DeepGlobe leaderboards.
- **Model and training** (`training/segmentation/train_seg.py`): smp U-Net with an ImageNet ResNet-34 encoder.
  Loss is BCE + Dice with the no-data mask applied; fp16; AdamW 3e-4 with 500-step warm-up and cosine decay.
  Each epoch is 4000 random 512² crops, with the two sources sampled equally; batch 8, 40 epochs. Each epoch is
  scored on up to 300 validation tiles, sampled once with seed 0 from the 334 available. The checkpoint and
  decision threshold (from a 0.20–0.75 grid) are picked by validation IoU. The test split is scored **once**,
  with that threshold frozen.
- **Head-to-head** (`scripts/eval_road_baseline.py`): the same seeded tiles go through
  `run_grounding_pipeline(image, "mark all roads")` with its defaults (Grounding DINO + V4 reasoning + SAM 2)
  and through the trained checkpoint. Pixel TP/FP/FN are summed over all tiles for each method. Ground truth
  is used only for scoring.

### 2. Measured results

**Run `roads_dg_ma`** (DeepGlobe + Massachusetts): best epoch 38; threshold 0.30 frozen on validation; peak GPU
memory 2.06 GB; about 74–82 s per epoch.

| Split | IoU | F1 | Precision | Recall |
|---|---|---|---|---|
| val at best epoch (≤300 tiles) | 0.570 | 0.726 | 0.721 | 0.731 |
| test, both sources pooled (346 tiles) | 0.584 | 0.738 | 0.722 | 0.754 |
| test, DeepGlobe (297, hash split) | 0.547 | 0.707 | 0.697 | 0.718 |
| test, Massachusetts (49, official) | 0.606 | 0.755 | 0.736 | 0.775 |

**Head-to-head on the same tiles** (`results/training/road_h2h_*.json`):

| Tiles | Pipeline IoU | Trained IoU | Pipeline tiles at IoU 0 | Trained tiles at IoU 0 | Tiles where trained < pipeline |
|---|---|---|---|---|---|
| DeepGlobe, 100 of the test split (seed 0) | 0.0314 | **0.5402** | 58 | 1 | 5 |
| Massachusetts, all 49 test tiles | 0.0211 | **0.6063** | 37 | 0 | 0 |

The pipeline took 0.57 s per DeepGlobe tile and 0.98 s per Massachusetts tile. The baseline IoU was measured
twice and was identical both times (0.0314). An earlier progress report in the session said 61 of the 100
DeepGlobe tiles scored 0. That count came from console output rounded to 3 decimals; the exact count from the
JSON is 58.

**Validation is noisy until the learning rate falls.** Up to about epoch 20, validation IoU moved between
0.41 and 0.54, and the best threshold jumped between 0.20 and 0.65. From epoch 29 it rose steadily from 0.558
to 0.570, with loss falling from 0.47 to 0.44. The first, DeepGlobe-only run (`roads_deepglobe`) crashed at
epoch 15. Its best was val IoU 0.532 at epoch 4, and it never beat that before the crash
(`results/training/roads_deepglobe_run1_crashed.log`).

### 3. Blast radius

- **Nothing in the serving path changed yet.** The trained model is not in `configs/models.yaml` and does not
  receive road prompts. Until it does, "mark the roads" still runs the 0.03-IoU path from Q-020. The claim is
  "we trained a road segmenter that scores 0.54–0.61 IoU on held-out tiles where the current pipeline scores
  0.02–0.03", **not** "the product now segments roads well."
- **Resolution assumption.** The model was trained at 0.5 m. Imagery much coarser (Sentinel-2 at 10 m) or much
  finer (drone imagery) is outside its training range, and nothing here measures how it does there.
- **Resources.** On 2026-09-17 at 11:02 the PC froze hard with no log trail. At the time, training (6 workers),
  three download lanes and another session's GPU evaluation were running together; RAM exhaustion is the most
  likely cause but is not proven. Since then every job runs in `satquery.slice` (MemoryMax 13.7 G, no swap).
  `satquery-mem-guard` (`scripts/mem_guard.sh`) stops the largest job in that slice when available RAM falls
  below 1 GB. It was tested once against a dummy process, and its log marks that entry as a test.
  `results/training/sysmon.log` records RAM, swap and GPU every 30 s and syncs each line to disk.

### 4. Verification

- `cat checkpoints/roads_dg_ma_seg/report.json` gives the test table above. The threshold was chosen on
  validation, and test was scored once.
- `.venv/bin/python scripts/eval_road_baseline.py --source deepglobe_roads --n 100 --checkpoint
  checkpoints/roads_dg_ma_seg/best.pt` reproduces the head-to-head (seeded).
- SpaceNet mask quality was checked visually by overlaying rasterised masks on three random Vegas and Paris
  tiles; the masks follow the carriageways. It has not been checked numerically.
- After the crash, all 24,214 downloaded images were test-opened (cv2 / rasterio) and none failed. The partial
  downloads (45 S3 temporary files, 8 HF `.incomplete` files, one Kaggle zip) were deleted and fetched again.

### 5. Defence — "Isn't 0.03 → 0.54 just comparing a detector with a segmenter?"

"Yes, and that is the point Q-020 made. A box detector is the wrong tool for a road network, and the fix is a
tool built for the job, not more tuning of the detector. The comparison is fair on its own terms: the same
tiles, the same pixel metric, the pipeline as users run it today, and a threshold frozen before test. What
we do not claim: parity with published DeepGlobe results (our DeepGlobe test split is our own), accuracy on
imagery far from 0.5 m, or that the product already uses this model. Wiring it in is the next change, and it
gets its own entry."

## Q-026 · Trained building segmenter: WHU IoU 0.635 → 0.831, Massachusetts 0.191 → 0.686 against the live pipeline

**Recorded** 2026-09-17, atop `prototype` `55f76b3`. The work is uncommitted, and it uses the same trainer,
loader and head-to-head script as Q-025.

### 1. Mechanism

Run `buildings_whu_ma`: U-Net / ResNet-34 trained on WHU Building (official split, 5732/1228/1228 tiles,
0.3 m) and Massachusetts Buildings (official split, 137/4/10, 1.0 m), both resampled to 0.5 m. Training used
**256² crops**, not 512²: a 512-px WHU tile shrinks to 307 px at 0.5 m, so a 512² crop would be mostly
padding. Other settings: batch 16, 6000 crops per epoch, 30 epochs, everything else as in Q-025. Checkpoint and
threshold were picked on validation, which is mostly WHU because Massachusetts has only 4 validation tiles.
Test was scored once.

### 2. Measured results

Best epoch 28; threshold 0.40; peak GPU memory 1.24 GB; about 26 s per epoch.

| Test split | IoU | F1 | Precision | Recall |
|---|---|---|---|---|
| pooled (1238 tiles) | 0.753 | 0.859 | 0.843 | 0.876 |
| WHU (1228) | 0.823 | 0.903 | 0.902 | 0.904 |
| Massachusetts (10) | 0.686 | 0.814 | 0.785 | 0.846 |

Head-to-head against `run_grounding_pipeline("mark all buildings")` on the same tiles
(`results/training/building_h2h_*.json`):

| Tiles | Pipeline IoU | Trained IoU | Trained worse on | Pipeline s/tile |
|---|---|---|---|---|
| WHU, 100 test tiles (seed 0) | 0.635 | **0.831** | 5 of 100 | 0.55 |
| Massachusetts, all 10 test tiles | 0.191 | **0.686** | 0 of 10 | 2.03 |

Both methods score IoU 0 on 27 of the 100 WHU tiles. For 26 of those, the ground truth contains no buildings,
and per-tile IoU is defined as 0 when prediction and truth are both empty. On the 74 tiles that do contain
buildings, each method has exactly one tile at 0.

### 3. Blast radius

- **The pipeline is not bad at buildings.** 0.635 IoU on WHU is a real result: buildings are compact objects,
  which a box detector handles well, unlike roads (Q-020, Q-025). The gap opens on the dense 1 m Massachusetts
  scenes (0.191).
- As in Q-025, nothing in the serving path changed. The building checkpoint is not wired to any prompt.
- The model's context is 256 px at 0.5 m (128 m). Very large buildings, such as warehouses and airport
  terminals, were rare in training and have not been measured.

### 4. Verification

`checkpoints/buildings_whu_ma_seg/report.json`; `.venv/bin/python scripts/eval_road_baseline.py --source
whu_building --n 100 --query "mark all buildings" --checkpoint checkpoints/buildings_whu_ma_seg/best.pt`. The
empty-tile count came from reading each zero-IoU tile's ground-truth mask (`max() == 0`).

### 5. Defence — "Your pipeline already did 0.64 on WHU; is 0.83 worth a second model?"

"On WHU-like imagery, the gain is +0.20 IoU: fewer merged and missed buildings. On the denser 1 m
Massachusetts scenes, the pipeline drops to 0.19 and the trained model holds at 0.69. The larger gain is on the
kind of scene the pipeline struggles with. The WHU test score is not a state-of-the-art claim: we score at
0.5 m, not WHU's native 0.3 m."

## Q-027 · Adding SpaceNet 3 (Vegas + Paris) to the road model: better on all three test sets

**Recorded** 2026-09-17, atop `prototype` `55f76b3`; uncommitted. This follows Q-025, whose model
(`roads_dg_ma`) this one is compared with.

### 1. Mechanism

Run `roads_dg_ma_sn3`: the Q-025 recipe, unchanged (U-Net / ResNet-34, 512² crops at 0.5 m, batch 8, 40
epochs, 4000 crops per epoch), plus a third source, `spacenet3_roads`. That source is 1238 tiles from Vegas
and Paris, hash-split 1123/65/50. Shanghai and Khartoum were still downloading and are **not** included.
`prepare_spacenet3.py` converts the 16-bit PS-RGB tiles to 8-bit, using a 2–98 % stretch per band and per
tile. It draws each road centreline as a band 1.75 m × lane count to either side (default 2 lanes), at the
0.3 m GSD. The three sources are sampled equally, so SpaceNet makes up a third of the crops in each epoch.
The DeepGlobe and Massachusetts test tiles are the same as in Q-025, because the hash split does not depend
on which other sources are present.

### 2. Measured results

Best epoch 38; threshold 0.40 frozen on validation (Q-025: 0.30); val IoU 0.586; peak GPU 2.06 GB.

| Test split | Q-025 model IoU | This model IoU |
|---|---|---|
| DeepGlobe (297) | 0.547 | **0.557** |
| Massachusetts (49) | 0.606 | **0.613** |
| SpaceNet Vegas + Paris (50) | not trained on SpaceNet; not scored | 0.633 |
| pooled | 0.584 (2 sources) | 0.596 (3 sources; not comparable) |

Head-to-head against `run_grounding_pipeline("mark all roads")` (`results/training/road_h2h_*_sn3model.json`):

| Tiles | Pipeline IoU | This model IoU | Tiles where this model is worse |
|---|---|---|---|
| DeepGlobe, 100 (seed 0) | 0.031 | 0.552 | 1 |
| Massachusetts, 49 | 0.021 | 0.613 | 0 |
| SpaceNet, 50 | 0.129 | 0.633 | 1 |

### 3. Blast radius

- The gains on DeepGlobe (+0.010) and Massachusetts (+0.007) are small, and each comes from a single training
  run (seed 0). No variance was measured, so they may be within seed noise. The claim is "adding SpaceNet did
  not hurt and probably helped," not a significant improvement.
- The SpaceNet labels are drawn from centrelines with an assumed width, not traced by hand. A SpaceNet score is
  partly a measure of agreement with that width rule.
- The OpenCV "unknown TIFF tag" warnings that swelled this run's log to 34 MB are now silenced in
  `datasets.py`. The metrics are unaffected.

### 4. Verification

`checkpoints/roads_dg_ma_sn3_seg/report.json`; `.venv/bin/python scripts/eval_road_baseline.py --source
spacenet3_roads --n 50 --checkpoint checkpoints/roads_dg_ma_sn3_seg/best.pt`.

### 5. Defence — "Is +0.01 IoU real?"

"We don't know yet, and we say so. It is one seed. What we can say: adding a third city-scale source did not
cost accuracy on the first two, and the same model reaches 0.63 IoU on SpaceNet. The next check is two more
seeds of both configurations."

## Q-028 · Crater detector (YOLO11s): lunar AP50 0.963 vs 0.024 for zero-shot Grounding DINO

**Recorded** 2026-09-17, atop `prototype` `55f76b3`; uncommitted. This is the first planetary ("space")
capability. Nothing in the serving path uses it yet.

### 1. Mechanism

- **Data** (`training/detection/train_craters.py`): LU3M6TGT (Moon, 416² tiles, YOLO labels; 8756 train,
  1545 valid) plus the Kaggle Mars/Lunar crater set (640² tiles; 98/26/19). LU3M6TGT ships only train and
  valid, so its valid split is divided 50/50 by a SHA-1 hash of the filename into our val (752) and test
  (793). **No LU3M6TGT training tile is in our test set.** The Mars/Lunar set keeps its own splits. Totals:
  8854 / 778 / 812.
- **Why these settings:** LU3M6TGT craters are tiny (median box ≈ 9 px at 416 px; 109 boxes per tile on
  average, up to 506), so training runs at **832 px** with `max_det=1000`.
- **Model:** ultralytics YOLO11s from COCO weights; 60 epochs; batch 8; 2 data-loader workers. With 4 workers,
  the dataloaders held about 1.6 GB each and pushed available RAM down to 1.35 GB. Best weights are chosen by
  ultralytics' validation fitness. Test was scored once with `best.pt`.
- **Licence and install:** ultralytics is AGPL-3.0 (user's decision, 2026-09-17). It is installed `--no-deps`,
  so its `opencv-python` requirement does not clash with the backend's `opencv-python-headless`
  (`training/requirements.txt`).
- **Head-to-head** (`scripts/eval_crater_baseline.py`): one AP50 implementation (COCO 101-point, greedy
  matching at IoU ≥ 0.5) scores both the Grounding DINO adapter prompted with `"crater."` and the YOLO model,
  on the same seeded tiles: 150 of the LU3M6TGT test tiles and all 19 Mars/Lunar test tiles.

### 2. Measured results

Ultralytics test metrics (`checkpoints/craters_yolo_seg/report.json`):

| Test split | mAP50 | mAP50-95 | P | R |
|---|---|---|---|---|
| LU3M6TGT (793) | 0.965 | 0.870 | 0.912 | 0.892 |
| Mars/Lunar (19) | 0.648 | 0.345 | 0.657 | 0.596 |

Validation at epoch 60 (the last epoch was also the best): mAP50 0.965, mAP50-95 0.849. About 123 s per epoch
at 832 px, with 4.6 GB of GPU memory in use.

Head-to-head, AP50 from our own code (`results/training/crater_h2h_thr*.json`):

| Tiles | GD @ box/text thr 0.05 | GD @ 0.01 | YOLO |
|---|---|---|---|
| LU3M6TGT, 150 (16,969 craters) | 0.012 (max recall 0.038) | **0.024** (max recall 0.150) | **0.963** (max recall 0.993) |
| Mars/Lunar, 19 (151 craters) | 0.337 (max recall 0.596) | **0.377** (max recall 0.801) | **0.642** (max recall 0.921) |

Our AP code gives 0.963 for YOLO on the 150-tile LU sample, against ultralytics' 0.965 on all 793 tiles.
The two implementations agree.

**Grounding DINO's detection count is a threshold effect, not a cap.** At 0.05 it returned about 20 boxes per
LU tile (8–15 on the four tiles probed); at 0.01 it returned 281–457 on the same four tiles, which have
78–291 true craters. The 0.01 row is the fairer baseline, because AP can use the low-score detections.

### 3. Blast radius

- **The Mars/Lunar set is small** (98 training tiles, 19 test tiles), and its 0.65 mAP50 is correspondingly
  uncertain. The model mostly learned LU3M6TGT's lunar imagery. Mars performance on anything but these tiles
  has not been measured.
- LU3M6TGT's labels come from a catalogue (the dataset ships `dilatation_offsets`). Very small or degraded
  craters may be missing from the labels, and those count against precision.
- AGPL-3.0: serving this model from the backend over a network may carry source-disclosure obligations. The
  user accepted this knowingly.
- Not wired into any prompt or tool.

### 4. Verification

`checkpoints/craters_yolo_seg/report.json`; `.venv/bin/python scripts/eval_crater_baseline.py --n 150
--box-threshold 0.01`; the splits are in `datasets/processed/craters/{train,val,test}.txt`, which are
regenerated deterministically.

### 5. Defence — "Grounding DINO was never meant for craters. Is this comparison fair?"

"It is the comparison that matters for the product, because without this model a crater question goes to
Grounding DINO. We gave it the most favourable setting we measured (threshold 0.01, where it returns hundreds
of boxes per tile), and we scored both methods with the same code. The YOLO number is not a planetary-science
benchmark claim. It is 0.96 AP50 on held-out tiles from LU3M6TGT's own validation split, and 0.64 on a small
Mars/Lunar set."

## Q-029 · Land-cover segmenter (7 shared classes): mIoU 0.68 DeepGlobe, 0.60 OpenEarthMap, 0.43 LoveDA

**Recorded** 2026-09-17, atop `prototype` `55f76b3`; uncommitted. **There is no head-to-head.** The live
system has no pixel-level land-cover capability to compare against: BigEarthNet gives scene-level multi-label
tags on Sentinel-2.

### 1. Mechanism

- **Classes** (`training/segmentation/datasets.py`): other, built_up, agriculture, rangeland, forest, water,
  barren; 255 means ignore. The mapping is lossy and deliberate. LoveDA's building and road both become
  built_up, as do OpenEarthMap's developed space, road and building. DeepGlobe's "unknown", LoveDA's "ignore"
  and OpenEarthMap's "unknown" become ignore. Only LoveDA has a background class, so "other" is scored only
  there, and LoveDA has no rangeland.
- **Splits:** DeepGlobe publishes masks only for its train set, so it is hash-split (714/51/38).
  LoveDA's and OpenEarthMap's official val sets are **our test sets** (1669 and 500 tiles), and their official
  train sets are hash-split into train and val. **The HF LoveDA mirror (`chloechia/loveda`) has 1366 train
  tiles, not the official 2522.** The mirror itself is short, and the download is complete relative to it.
  OpenEarthMap was unpacked from parquet (`prepare_openearthmap.py`, 3500 tiles) and assumed to be at 0.5 m;
  its true GSD varies from 0.25 to 0.5 m.
- **Model** (`training/segmentation/train_landcover.py`): U-Net / ResNet-34 with a 7-channel head;
  cross-entropy (ignore 255) plus soft Dice; 512² crops at 0.5 m; batch 8; 40 epochs; 3 workers. Best
  checkpoint by validation mIoU over the classes present; test scored once.

### 2. Measured results

Best epoch 32; val mIoU 0.706; peak GPU 2.36 GB.

| Test split | mIoU | pixel acc | built_up | agriculture | rangeland | forest | water | barren | other |
|---|---|---|---|---|---|---|---|---|---|
| DeepGlobe (38) | **0.682** | 0.881 | 0.647 | 0.885 | 0.265 | 0.807 | 0.793 | 0.698 | — |
| OpenEarthMap (500) | **0.600** | 0.805 | 0.823 | 0.684 | 0.498 | 0.654 | 0.654 | 0.286 | — |
| LoveDA (1669) | **0.428** | 0.601 | 0.433 | 0.568 | — | 0.321 | 0.590 | 0.287 | 0.367 |

### 3. Blast radius

- **Not comparable to published leaderboards.** The classes are merged (for example, building + road), our
  LoveDA test is the official val set, and we trained on about half of LoveDA's official train set.
- **Weak classes:** rangeland (0.27 on DeepGlobe) and barren (0.29 on both OpenEarthMap and LoveDA). LoveDA
  overall is weak, and its "other" class (0.37) absorbs everything LoveDA calls background.
- The DeepGlobe test split has only 38 tiles (large 2448² tiles, though). Its mIoU has wide uncertainty.
- Not wired into any prompt.

### 4. Verification

`checkpoints/landcover_dg_lv_oem_seg/report.json` (per-class IoU for every split, and the per-epoch
history).

### 5. Defence — "Why is LoveDA so much lower?"

"Three measured reasons. We had half its official training data. Its test set is 1669 tiles from different
cities than the train set (urban and rural, official split). And its 'background' class has no counterpart in
the other two datasets, so the model sees it only in LoveDA crops. Getting the full LoveDA train set from
Zenodo is the first thing to try if land cover needs to improve."

## Q-030 · Road model on all four SpaceNet cities (`roads_all`): Shanghai 0.32 → 0.50, Khartoum 0.39 → 0.53

**Recorded** 2026-09-17, atop `prototype` `55f76b3`; uncommitted. This follows Q-027 (`roads_dg_ma_sn3`,
trained on Vegas and Paris only).

### 1. Mechanism

Same recipe as Q-025 and Q-027. SpaceNet now covers all four cities once Shanghai and Khartoum finished
downloading: 2549 tiles with road labels out of 2780 (231 PS-RGB tiles have no geojson and are skipped),
hash-split 2283/144/122. The 50 Vegas + Paris test tiles from Q-027 are among the 122. The DeepGlobe and
Massachusetts test tiles are unchanged.

### 2. Measured results

`roads_all`: best epoch 37; threshold 0.35; test IoU DeepGlobe 0.554, Massachusetts 0.610, SpaceNet (all
122) 0.558; pooled 0.583.

**Q-027's model against this one on the same 122 SpaceNet test tiles** (`results/training/spacenet_bycity.json`):

| City (test tiles) | `roads_dg_ma_sn3` (Vegas + Paris only) | `roads_all` |
|---|---|---|
| Vegas (36) | 0.642 | 0.631 |
| Paris (14) | 0.572 | 0.549 |
| Shanghai (55) | 0.317 | **0.500** |
| Khartoum (17) | 0.393 | **0.532** |
| all 122 | 0.472 | **0.558** |

On DeepGlobe and Massachusetts the two models are equal to within 0.003 (0.557 against 0.554, and 0.613
against 0.610).

### 3. Blast radius

- **The main gain is geographic coverage.** Cities the earlier model never saw improve by +0.14 to +0.18. The
  cities it did see drop by 0.01 to 0.02, a cost of splitting the SpaceNet third of each epoch across four
  cities. As before, these are single-seed runs.
- **`roads_all` is the recommended road checkpoint** for integration (`checkpoints/roads_all_seg/best.pt`).
  It has not been wired in yet.
- The Q-027 claim of "0.633 on SpaceNet" referred to the 50 Vegas + Paris tiles only. It must not be quoted
  as a SpaceNet-wide number: on all four cities, that model scores 0.472.

### 4. Verification

`checkpoints/roads_all_seg/report.json`; the per-city numbers come from a one-off script that reuses
`scripts/eval_road_baseline.py`'s `load_checkpoint`, `predict` and `score` over
`SOURCES['spacenet3_roads']('test')`, pooling TP/FP/FN per city.

### 5. Defence — "Your Vegas score went down. Why ship this one?"

"By 0.011 on 36 tiles, while Shanghai went up by 0.183 on 55 tiles and Khartoum by 0.139 on 17. A road
model for ISRO will mostly see cities that look nothing like Las Vegas, so the model that has seen more
kinds of city is the one to ship."

## Q-031 · Capability roadmap: what the new training unlocks, and what is still needed before users see it

**Recorded** 2026-09-17, atop `prototype` `55f76b3`; uncommitted. **This is a plan, not a result.** Measured
numbers are quoted only from Q-025 to Q-030. Every other row is marked *planned*, and each needs its own entry
with measurements before it is claimed anywhere. At the time of writing, the ResNet-50 road run
(`roads_all_r50`) is at epoch 9 of 60, with val IoU 0.471. The LoveDA-full, FAIR1M and Kaggle phase-2
downloads are paused or held by the user while the ISPRS data (access approved for SIH development)
downloads.

### 1. Mechanism: what exists, what is planned, and what "unlocked" means

A capability counts as **unlocked** only when all four of these are true: (a) a checkpoint exists with a
measured test score; (b) it is registered in `configs/models.yaml` with an adapter in `backend/app/ml/adapters/`;
(c) the router and agent send the matching prompts to it; (d) an end-to-end test drives a prompt through the
API and checks the output. **Today, none of the new models meets (b), (c) or (d).**

| Capability (what a user could ask) | Model / data | State | Measured so far |
|---|---|---|---|
| "mark all roads": a pixel road network, not boxes | U-Net R34 `roads_all` (DeepGlobe, Massachusetts, SpaceNet ×4) | **trained** | IoU 0.554 / 0.610 / 0.558; live pipeline 0.031 / 0.021 / 0.129 (Q-025, Q-030) |
| "mark all buildings": footprint masks in dense scenes | U-Net R34 `buildings_whu_ma` | **trained** | IoU 0.831 WHU / 0.686 Massachusetts; live 0.635 / 0.191 (Q-026) |
| "find craters" on Moon / Mars imagery (first planetary capability) | YOLO11s `craters_yolo` | **trained** | AP50 0.963 lunar / 0.642 Mars-Lunar; Grounding DINO 0.024 / 0.377 (Q-028) |
| "show land cover / what is this area used for": a 7-class map (built-up, agriculture, rangeland, forest, water, barren, other) plus area percentages | U-Net R34 `landcover_dg_lv_oem` | **trained** | mIoU 0.682 DeepGlobe / 0.600 OEM / 0.428 LoveDA; no live equivalent (Q-029) |
| the same four, more accurate | ResNet-50 encoders, 4-flip TTA, full LoveDA | *planned (running)* | roads R50 in progress; buildings and land cover queued |
| very-high-resolution urban mapping (buildings, impervious surfaces, trees, low vegetation, cars, clutter at 5–9 cm) | ISPRS Potsdam + Vaihingen | *planned* | data downloading; package contents not yet inspected |
| "find all water bodies" / flood extent | Sentinel-2 water bodies (Kaggle) + Sen1Floods11 (already downloaded, SAR) | *planned* | data held / not yet trained |
| "is this scene cloudy? mask the clouds" (a preprocessing gate for optical analysis) | 95-Cloud, Landsat 8 | *planned* | data held |
| "find ships" in port or at sea | MASATI-v2 | *planned* | data held |
| "what new buildings appeared between these dates?" at building level, over time series | SpaceNet 7 multitemporal | *planned*; would complement ChangeFormer (LEVIR-CD) | data held |
| sharper instance masks for 15 object classes (planes, ships, vehicles, storage tanks, …) | iSAID masks, for SAM 2 refinement | *planned* | data held |
| open-vocabulary detection that knows remote-sensing classes ("find storage tanks / helipads / roundabouts") | Grounding DINO fine-tuned on LAE-1M (1M instances, 80+ classes) | *planned*; Swin-T may fit the 3070, Swin-B needs the cloud GPU | LAE-1M 37.2 of 42.2 GB of its last file |

### 2. Rationale: why these, in this order

- **Roads, buildings, craters, land cover first**, because each fixes a measured failure or adds a capability
  the problem statement asks for, and all of their data was already downloaded.
- **Accuracy pushes before new capabilities**, because they reuse downloaded data and the evaluation harness,
  and every gain is measured on the same test tiles as before.
- **Water, cloud, ships and multitemporal change next**, because they are common ISRO-style questions that
  currently route to generic models or have no model at all. Cloud masking is also a quality gate for every
  other optical capability.
- **Grounding DINO fine-tuning last**, because it is the largest job, it changes a model already in the
  serving path (a higher regression risk than adding new models), and the base model does not fit the local
  GPU for training.

### 3. Blast radius

- **Routing is the risk, not the models.** Sending "roads" to a segmenter instead of Grounding DINO changes
  the output type (a mask, not boxes plus masks) and the answer text. Every change to the router or agent
  needs its own QNA entry and end-to-end tests.
- **Resolution mismatch.** Our segmenters are trained at 0.5 m. Water bodies and clouds are 10–30 m data.
  ISPRS is 5–9 cm. Each needs its own GSD handling, or a documented refusal for inputs outside its range.
- **Planetary imagery** must not be routed to Earth models, or the reverse. This needs an explicit
  body/sensor hint or a classifier. None exists yet.
- **Licences to honour.** ultralytics is AGPL-3.0 (Q-028). iSAID, SpaceNet 7 and water bodies are
  non-commercial. ISPRS access was approved for SIH development and requires the Cramer (2010) + DGPF
  acknowledgement in papers.

### 4. Verification: the gate each row must pass before it is called "unlocked"

1. `checkpoints/<task>_seg/report.json` with a test split that was scored once, with the threshold frozen on
   val.
2. A head-to-head against whatever the live system does today for that prompt, on the same tiles, when a live
   equivalent exists.
3. A unit test for the adapter, and an end-to-end test that sends the prompt through the HTTP API and checks
   the artefact.
4. A QNA entry with the measured numbers, including the weak classes and tiles.

### 5. Defence: "You list twelve capabilities. How many actually work?"

"Four models are trained and measured, and they beat the current pipeline on the same tiles by large
margins, or add something it cannot do. None of them answers a user prompt yet; wiring them in is the next
change. Everything else in the table is planned, with data downloaded or queued, and nothing planned is
presented as done."

## Q-032 · ResNet-50 encoders and 4-flip TTA: +0.012 to +0.017 IoU on every road and building test set

**Recorded** 2026-09-17, atop `prototype` `55f76b3`; uncommitted. This follows Q-026 (buildings) and Q-030
(roads). Same test tiles, and each test split scored once.

### 1. Mechanism

- **What changed from Q-026 and Q-030:** the encoder is `resnet50` instead of `resnet34`; the road run is 60
  epochs instead of 40. `train_seg.py` now also reports `test_per_source_tta`, which averages the identity,
  horizontal, vertical and double flips at the same frozen threshold. TTA is never used to pick the
  checkpoint or the threshold.
- **Resilience added to the trainer:**
  - it saves `last.pt` after every epoch (model, optimizer, schedule, scaler, history), and `--resume` loads it;
  - `best.pt` and `last.pt` are written to a temporary file and then renamed, so a power cut cannot leave a
    torn file;
  - the queue is an enabled systemd user service (`satquery-train-queue`, `datasets/raw/_jobs/train_queue.sh`)
    that resumes after a reboot.
- **Interruption (disclosed):** a power cut at about 19:13 killed `roads_all_r50` during epoch 38. The run
  predated `last.pt`, so it was continued with `--warm-start` from the epoch-37 `best.pt` (val IoU 0.5685).
  The LR schedule was advanced to epoch 37 (LR 9.91e-5), but **AdamW's moment estimates restarted from zero**.
  Epochs 38–60 are therefore not identical to an uninterrupted run. The pre-cut checkpoint is kept as
  `best_epoch37_precut.pt`. The buildings run was not interrupted.

### 2. Measured results (test IoU)

| Test split | R34 (Q-026 / Q-030) | R50 | R50 + TTA |
|---|---|---|---|
| Roads, DeepGlobe (297) | 0.554 | 0.557 | **0.569** |
| Roads, Massachusetts (49) | 0.610 | 0.616 | **0.622** |
| Roads, SpaceNet, 4 cities (122) | 0.558 | 0.565 | **0.571** |
| Buildings, WHU (1228) | 0.823 | 0.834 | **0.840** |
| Buildings, Massachusetts (10) | 0.686 | 0.695 | **0.700** |

`roads_all_r50`: best epoch 54, threshold 0.35, val IoU 0.583 at epoch 60.
`buildings_whu_ma_r50`: best epoch 37, threshold 0.45, val IoU 0.832 at epoch 40.

### 3. Blast radius

- **The attribution is incomplete.** The R34 checkpoints were never scored with TTA, so the "+TTA" column
  combines two changes. Running TTA on the R34 checkpoints would separate them. That has not been done.
- The encoder gains (+0.003 to +0.011) come from single seeds and are of the same size as the unmeasured run
  to run noise (Q-027). Only the direction is consistent: all five sets improved.
- **Cost:** R50 peaks at about 3.35 GB of GPU memory in training (R34: 2.06 GB). TTA makes inference 4× slower.
- **Recommended checkpoints for integration:** `checkpoints/roads_all_r50_seg/best.pt` and
  `checkpoints/buildings_whu_ma_r50_seg/best.pt`, served with TTA if latency allows.
- Land cover (`landcover_full_r50`) is queued behind the full LoveDA download, which is paused at the
  user's request.

### 4. Verification

`checkpoints/{roads_all_r50,buildings_whu_ma_r50}_seg/report.json` (`test_per_source` and
`test_per_source_tta`); `results/training/train_queue.log`; the interruption is marked in
`results/training/roads_all_r50.log` and `sysmon.log`. Resume was tested with a smoke run: 2 epochs, stop,
then `--resume --epochs 3` continued at epoch 3.

### 5. Defence — "Was the interrupted run trained properly?"

"It was interrupted once, and we say how: weights and LR schedule were carried over, optimizer moments were
not. Its result is the best of any road model on all three test sets, and the uninterrupted buildings run
shows the same direction of gain. If a reviewer needs a clean run, the trainer now resumes exactly from
`last.pt`, so a re-run costs 1.5 GPU hours and nothing else."

## Q-033 · Numbering collision: two different Q-025 to Q-029 series exist in this file

**Recorded** 2026-09-18, atop `prototype` `541b0f2`. This entry only records a fact; it changes no code.

### 1. Mechanism: what happened

Two sessions appended to `project/qna.md` in parallel. The cloud-GPU session committed Q-025 to Q-029 (hosted
backend, Qwen3-VL, Modal deployment; commits up to `541b0f2`). The training session, working uncommitted in
the main checkout, wrote its own Q-025 to Q-032 after them (trained segmenters, craters, land cover,
roadmap, R50 + TTA). Each session numbered from the last entry it had seen, so **Q-025, Q-026, Q-027,
Q-028 and Q-029 each appear twice** in this file, with different content. Q-030 to Q-032 appear once.

The record is append-only (global rule: past entries are never edited or deleted), so neither series is
renumbered. Both series stay exactly as written.

### 2. How to cite them unambiguously

| Cite as | Entry |
|---|---|
| **Q-025c … Q-029c** | the cloud-GPU series (hosted backend, Qwen3-VL, Modal T4), the entries **before** the heading "Q-025 · First trained road segmenter" |
| **Q-025t … Q-032t** | the training series, starting with "Q-025 · First trained road segmenter" |

Every earlier cross-reference inside the training series (for example "Q-020", "follows Q-025") points to
entries in its own series or to the shared history before Q-025, and reads correctly with the "t" suffix.

### 3. Blast radius

Anyone citing "Q-026" in a paper, demo or review without a suffix is ambiguous from this point on. The
cloud-GPU session's queued entry must take **Q-034 or later**. The next number free for both sessions is
Q-034.

### 4. Verification

`grep -n '^## Q-0' project/qna.md` lists both series in file order: Q-025 to Q-029 (cloud), then Q-025 to Q-032
(training), then this Q-033.

### 5. Defence: "Why not just renumber?"

"Because this file is a transcript. Renumbering would rewrite entries after the fact, and the rule
forbids it. The collision is itself part of the record: two teams worked in parallel. An alias table fixes
the ambiguity without changing a single past entry."

## Q-035 · Water and cloud masking: two new capabilities (water pooled test IoU 0.47/mean per-tile 0.77, cloud pooled 0.70)

**Recorded** 2026-09-18, atop `prototype` 541b0f2; uncommitted. Next free number after Q-034 (the cloud-GPU
session's entry, held on its own branch per Q-033's alias table).

### 1. Mechanism

- **Water:** Kaggle "Water Bodies Dataset" (Sentinel-2, ~10 m GSD), 2560/129/131 tiles, hash-split (no
  official split). `train_seg.py` gained `--target-gsd`, so each source trains at its own native resolution
  instead of being forced to the road/building default of 0.5 m — critical here, since upsampling 10 m water
  tiles to 0.5 m would inflate them ~400x in pixel count. U-Net/ResNet-34, 40 epochs, `--target-gsd 10 --crop
  192`. Checkpoint `checkpoints/water_seg`.
- **Cloud:** 95-Cloud (Landsat 8), 13768/856/1723 patches. The Kaggle mirror holds only the "95-Cloud
  additional to 38-Cloud" half — the 38-Cloud training patches and the official 38-Cloud/95-Cloud **test**
  imagery were never downloaded, only 20 `*_MTL.txt` metadata files. So the official train/test separation
  is unusable; the split is instead by Landsat **scene id** (51/3/6 scenes) so neighbouring patches from the
  same scene cannot leak across splits. 16-bit bands are mapped to 8-bit with a fixed `>>8` capped at 254 (not
  a per-patch percentile stretch, which would leak the label — an overcast patch and a clear one would end up
  with the same histogram after stretching). The 254 cap matters because the loader treats pure white as
  no-data; an uncapped bright cloud would have been masked out of the loss. `--target-gsd 30 --crop 256`, 30
  epochs. Checkpoint `checkpoints/cloud_seg`.
- Both sources default to landcover's usual behaviour when no `--target-gsd` is passed (regression-tested:
  12/12 arrays identical before/after the change for one `deepglobe_roads` and one `whu_building` tile).

### 2. Measured results

| Model | Best epoch | Threshold | Val IoU (pooled) | Test IoU (pooled) | Val→test precision/recall |
|---|---|---|---|---|---|
| Water | 21 | 0.20 | 0.800 | **0.475** | P 0.93→0.89, R 0.85→0.50 |
| Cloud | 9 | 0.50 | 0.830 | **0.703** | P 0.88→0.93, R 0.93→0.74 |

**Water's pooled test score is misleading on its own** — investigated in detail below. Per-tile (one IoU per
tile, then averaged/medianed — "macro"), the model does much better:

| Water split | tiles | per-tile median IoU | per-tile mean IoU | tiles scoring <0.05 IoU |
|---|---|---|---|---|
| val | 129 | 0.857 | 0.792 | 0 |
| test | 131 | 0.866 | 0.772 | 1 |

A script (`scripts/_debug_water.py`, not committed — see §3) reproduced the official pooled numbers exactly
(val 0.8000, test 0.4749, matching `report.json` to the last digit — confirms the trainer's own `evaluate()`
has no bug here) and then broke the same pooled total down per tile. The cause: this Kaggle set has no
official split and extreme tile-size variance — 84×84 px up to 5292×6767 px, a ~4000x range in area. Pooled
IoU sums raw pixels across all tiles, so it is a pixel-weighted average, not a per-tile one. On the test
split, 7 of 131 tiles exceed 4 million pixels; one of them (3155×2457, a single large water body, IoU 0.182,
recall the main shortfall) alone carries tens of millions of raw pixels and numerically dominates the pooled
total, even though 130 of the 131 tiles score well. The val split's 3 large tiles average a much higher 0.827,
which is why val's pooled score (0.800) doesn't show the same effect — an accident of the random hash split,
not a difference in the model.

Cloud's val→test recall drop (0.93→0.74) was not investigated to the same depth; noted as an open question,
not explained.

### 3. An incident during this work: a diagnostic script crashed the PC

While investigating the water gap, an ad-hoc diagnostic script was run directly (not wrapped in
`systemd-run --slice=satquery.slice` with a memory cap, breaking the standing rule that heavy jobs run
memory-guarded — see `local-training-memory-guard` in the assistant's memory). The script called `read_pair`
without passing `target_gsd`, so it silently used the *land-cover* default (0.5 m) instead of water's native
10 m — the loader tried to upsample a 10 m tile to 0.5 m, a 20x/axis (~400x pixel count) blow-up. For the
largest water tile (5292×6767) this would attempt to allocate roughly 14 billion pixels. Run uncapped, this
exhausted system RAM and swap; the kernel OOM-killer fired (`Killed process ... python ... anon-rss:11321648kB`)
and the desktop froze, requiring a hard reboot (new boot `c6cd240...` at 17:08, 2026-09-18).

**No data or checkpoint was damaged.** Every `checkpoints/*_seg/report.json` was re-verified as valid JSON
after the reboot; all persistent services (`satquery-mem-guard`, `satquery-sysmon`, `satquery-ingest-isprs`)
restarted automatically, confirming the systemd-based design from the earlier 2026-09-17 crash held up. The
training queue had already finished before the crash, so no training was lost. The corrected, capped rerun
(`MemoryMax=3G`, `--slice=satquery.slice`) produced the per-tile numbers in §2 without incident.

### 4. Blast radius

- Neither model is wired into the app. `configs/models.yaml` and routing are untouched.
- Water's pooled test score (0.475) will look bad if quoted alone; §2's per-tile breakdown must go with it, or
  it understates the model.
- The cloud test set is not ISRO's or the community's standard 38-Cloud/95-Cloud test set (§1); "cloud IoU
  0.70" is not comparable to published 95-Cloud leaderboard numbers.

### 5. Verification

`checkpoints/{water,cloud}_seg/report.json`. The per-tile/pooled reconciliation is reproducible: any script
that calls `read_pair(..., target_gsd=WATER_GSD_M)` (not the default) and sums per-tile tp/fp/fn will recover
the exact pooled numbers above.

### 6. Defence — "Is water masking actually good, or is 0.47 the real number?"

"Both statements are true, for different things. 0.47 is the honest pixel-weighted score on this exact test
set, and we do not hide it. But it's driven almost entirely by one large, hard tile. On 130 of 131 test
tiles — including every tile a typical query would touch — the model's IoU is 0.77 to 1.0, median 0.87. We
show the reviewer both numbers and explain the gap, rather than picking whichever one is more flattering."

## Q-036 · ISPRS Potsdam and Vaihingen: very-high-resolution urban segmentation (mIoU 0.700 / 0.729), a new 0.1 m capability

**Recorded** 2026-09-18, atop `prototype` 541b0f2; uncommitted.

### 1. Mechanism

Data obtained by the user directly from ISPRS (access request approved for SIH development,
2026-09-17) — Potsdam (5 cm GSD, RGB + RGBIR) and Vaihingen (9 cm GSD, IRRG — infrared/red/green, not RGB).
6 classes, `255 = IGNORE`: impervious, building, low_vegetation, tree, car, clutter. This is a **separate
taxonomy** (`isprs_urban` in `training/segmentation/datasets.py`'s `SEG_TASKS`) from the 7-class land-cover
one — ISPRS has no equivalent of the "car" class and does not merge impervious/building the way land-cover
merges everything into "built_up".

Two decisions, each with measurements behind them (full detail in `docs/models/isprs_urban.md`):
- **Two models, not one, per city.** Per-class mean band value on channel 0: Potsdam RGB gives
  tree/building = 72.7/111.4 = 0.65 (vegetation darker than roofs); Vaihingen IRRG gives 140.3/113.9 = 1.23
  (vegetation brighter). A shared first conv layer cannot learn opposite signs for the same channel on the
  same discriminative cue, so each city trains separately.
- **0.1 m resolution**, not the land-cover 0.5 m default. Measured car bounding boxes: median 2.45×4.20 m
  (Potsdam), 3.06×4.14 m (Vaihingen). At 0.5 m a car is 5×8 px, gone by a /32 encoder bottleneck; at 0.1 m it
  is 25×42 px. ISPRS's own eroded-boundary protocol erodes 3 px at native GSD (0.15 m Potsdam / 0.27 m
  Vaihingen), so 0.1 m does not exceed the labels' own precision.

Two Potsdam label tiles were found off-palette during decoding: `top_potsdam_4_12_label.tif` is a lossy
re-encode (24,850 distinct colours instead of 6 — exact-match decoding would read 0% of its 36M pixels as
labelled), and `top_potsdam_6_7_label.tif` codes most cars as an off-yellow (252,255,0) rather than the exact
palette colour (37x more car pixels recovered by threshold decoding vs exact match). The decoder
(`decode_isprs_label`) thresholds each channel at 127 instead of exact-matching, verified against all 71
label tiles: 0 unknown pixels, 0 pixels within 40 DN of the threshold.

Own splits (`hash_split`, 70/15/15, not ISPRS's official benchmark split — we hold the complete ground truth,
which the official ISPRS test protocol withholds from participants; same caveat as DeepGlobe in Q-025t):
Potsdam 29/5/4 tiles, Vaihingen 22/5/6. `train_landcover.py` gained `--taxonomy` and per-taxonomy
`--target-gsd`; regression-tested against unchanged `deepglobe_landcover` loading (index counts and pixel
sums identical before/after).

### 2. Measured results

`train_landcover.py --taxonomy isprs_urban`, U-Net/ResNet-34, crop 512, 40 epochs, `--max-val-tiles 5`
(both cities have only 5 val tiles, so this is not a subsample).

| City | Best epoch | mIoU | pixel acc | impervious | building | low_veg | tree | car | clutter |
|---|---|---|---|---|---|---|---|---|---|
| Potsdam (4 test tiles) | 25 | **0.700** | 0.885 | 0.811 | 0.907 | 0.763 | 0.695 | 0.821 | 0.201 |
| Vaihingen (6 test tiles) | 25 | **0.729** | 0.878 | 0.811 | 0.891 | 0.671 | 0.784 | 0.683 | 0.532 |

Clutter is the weakest Potsdam class (0.201) and one of the strongest relative gaps in Vaihingen (0.532) — a
city-specific effect, not a bug: Vaihingen's "clutter" pixels carry visible IR structure, Potsdam's are closer
to a near-empty catch-all bucket of whatever the other 5 classes don't cover.

### 3. Blast radius

- **Test sets are 4 and 6 tiles.** These mIoU numbers carry wide uncertainty and are not directly comparable
  to the ISPRS leaderboard, which scores on the eroded boundary set and excludes clutter from its headline
  5-class mean; we score all 6 classes on the full (non-eroded) labels.
- **Not wired into the app.** No adapter, no `configs/models.yaml` entry, no routing.
- **Licence/citation:** ISPRS access was approved for SIH development use. Papers using this data should cite
  Cramer (2010) and carry the DGPF acknowledgement (`datasets/raw/isprs_potsdam_vaihingen/docs/`). Potsdam's
  own conditions-of-use text was not found locally — the shipped PDF (`complexscenes_revision_v4.pdf`) is
  revision v4 and covers Vaihingen/Toronto only; "Potsdam" does not appear in it.
- The unofficial mirror `Potsdam/Toronto.zip` (3.2 GB) was deleted after inspection: it contains only
  `Reference_3d_reconstruction/*.dxf` (3D roof models for the ISPRS 3D-reconstruction task), no 2D semantic
  labels, so it cannot train or test any SatQuery model. Its file list is kept
  (`_Toronto_contents.txt`) and it can be re-fetched with the same access if needed.

### 4. Verification

`checkpoints/isprs_{potsdam,vaihingen}_seg/report.json` (full per-class breakdown); 17 CPU-only unit tests in
`tests/unit/test_isprs_dataset.py` (label decoding, split disjointness, crop shapes); `docs/models/isprs_urban.md`.

### 5. Defence — "Why isn't this one 6-class model?"

"Because the evidence says the two cities disagree on their most useful cue. Vaihingen's near-infrared band
makes vegetation brighter than buildings; Potsdam's visible-only RGB makes it darker. A single first layer
would have to learn opposite responses to the same input channel for the same class — we measured the
mismatch (0.65 vs 1.23) rather than assume it, and split the models instead of forcing a bad averaged
network on both cities to save one entry in `configs/models.yaml`."

## Q-037 · Land-cover retrained on the full LoveDA (2522 train tiles) plus ResNet-50: LoveDA mIoU 0.428 → 0.488

**Recorded** 2026-09-18, atop `prototype` 541b0f2; uncommitted. Follows Q-029t (7-class land cover,
ResNet-34, partial LoveDA) and Q-032 (ResNet-50 + TTA on roads/buildings).

### 1. Mechanism

Q-029t's LoveDA mirror (`chloechia/loveda`, Hugging Face) held only 1366 of LoveDA's 2522 official train
tiles — Rural only, missing all 1156 Urban ones. The official Zenodo release throttles to ~17 kB/s per
connection; a byte-identical re-upload was not found (an initial HF re-upload of `Train.zip` had the same
size but a different md5 than Zenodo's — re-archived, not identical — and was rejected by the download
script's checksum check rather than silently accepted). The full set was obtained instead as 8382 individual
files (`ahsennazir/loveDA`, official folder layout, `images_png`/`masks_png`), verified by file count rather
than an archive checksum. This gives 2273/249/1669 train/val/test tiles (the 1669 val tiles are unchanged —
they were already complete in the old mirror).

Same recipe as land cover's first run (Q-029t) but ResNet-50 instead of ResNet-34, matching the road/building
upgrade in Q-032.

### 2. Measured results

Best epoch 34; peak GPU 3.65 GB.

| Test split | Q-029t (ResNet-34, partial LoveDA) | This run (ResNet-50, full LoveDA) |
|---|---|---|
| DeepGlobe | 0.682 | 0.698 |
| OpenEarthMap | 0.600 | 0.603 |
| LoveDA | 0.428 | **0.488** |

DeepGlobe and OpenEarthMap did not use the LoveDA fix and their small gains (+0.016, +0.003) are attributable
to the ResNet-50 encoder change alone, consistent in size with Q-032's road/building gains. LoveDA's larger
gain (+0.060) is consistent with training on the correct, complete dataset rather than a rural-only subset.

### 3. Blast radius

- Two changes (encoder + full LoveDA) landed in one run; their individual contributions to the LoveDA gain
  are not separated.
- Not wired into the app.

### 4. Verification

`checkpoints/landcover_full_r50_seg/report.json`.

---

## Q-034 · L4 vs T4 measured; first real-browser end-to-end run against the cloud

**Recorded** 2026-09-18, app `satquery-ai` redeployed with `SATQUERY_MODAL_GPU=L4`
(`~/.venvs/modal/bin/modal deploy deploy/modal_app.py`, same image and weights as Q-029). All requests sent
from the RTX 3070 machine; the browser check used the real Next.js frontend (`npx next start -p 3000`,
no local backend) driven by Playwright, not the smoke script.

### 1. Mechanism

1. Redeploy with `SATQUERY_MODAL_GPU=L4` took the same code path as T4 (`deploy/modal_app.py`) — no changes
   needed; the GPU type is only a deploy-time env var. GPU identity verified directly, not inferred: the
   running container's PyTorch reported `torch.cuda.get_device_name(0)` → `"NVIDIA L4"`,
   `total_memory` → `22.0 GiB`, via `modal container exec <id> -- python -c "..."`.
2. Two `scripts/cloud_smoke.py` passes (first, warm) run under `systemd-run --user --slice=satquery.slice`
   (the mem-guard's cgroup) so the run stays supervised while a parallel training job used the local GPU.
   First attempt used the wrong working directory (`systemd-run`'s default, `$HOME`) and every file-based
   case failed with `FileNotFoundError`; the stray output file it wrote outside the repo
   (`~/results/evaluations/cloud_smoke_20260918_1135.json`) was deleted, and the rerun passed
   `--property=WorkingDirectory=<repo>`.
3. Browser check: Playwright against `localhost:3000`, connected to the cloud on `/system` with the
   `ushnik` key, then the real Command Center flow — drag-and-drop upload of
   `demo_resources/4_video/real_aerial_footage.mp4`, typed query "find red car", clicked Run, followed the
   redirect to `/video/{job_id}`, read the rendered event card, and inspected `browser_network_requests` for
   every `/api/` call's status and query string.

### 2. Measured (verbatim)

Cold start after redeploy: **28.2 s** (`/api/health`, 200).

| Prompt | L4 first | L4 warm | T4 warm (Q-029) |
|---|---|---|---|
| mask airplanes | 37.9 s | 26.9 s | 22.8 s |
| mask white houses | 26.4 s | 27.3 s | 24.3 s |
| what is in this image? | 82.0 s | 22.9 s | 20.9 s |
| has any new building been constructed? | 55.4 s | 45.4 s | 91.7 s |
| find red car (video) | 56.1 s | 59.7 s | 110.4 s |

All non-video answers on both L4 passes: `gemini:gemini-3.5-flash-lite`. Video result both passes:
`flags: [[15.36, 18.72]]` — identical to every prior run of this prompt (Q-029, and now the browser run).

Browser run: upload → registered (30.2 s, 12.5 fps, 377 frames, 768×432, h264) → job completed → event card
shows "red car", score **0.89**, **0:15.4 → 0:18.7**, playback auto-stopped at the event's end. Every
`/api/*` network request returned 200 except the video stream (**206**, Range request, correctly keyed) and
a benign generic-results poller hitting a video job id (**404**, repeated — see §3).

### 3. Blast radius

- **L4 is faster where it matters, not everywhere.** Change detection and video are the two GPU-bound,
  multi-model jobs; L4 warm beat T4 warm there by roughly 2× (45.4 s vs 91.7 s; 59.7 s vs 110.4 s — though
  video's L4 number came from the browser-adjacent smoke run, not a clean isolated pass, see below). On the
  lighter single-model jobs (masking, scene question) the two GPUs are within a few seconds of each other —
  those times are dominated by uploading the file and downloading the result zip over this connection, not
  by compute. This branch has not isolated network time from GPU time; the L4-vs-T4 gap on light jobs could
  be entirely network variance.
- **The L4 "first" pass is not a clean cold-model measurement.** It ran concurrently with the Playwright
  browser session's own upload/analyze/download traffic on the same connection and against the same warm
  container (`max_containers=1`), so its numbers (e.g. 82.0 s for the scene question) reflect contention,
  not first-load cost in isolation.
- **Confirmed harmless, found only by driving the real UI:** the video results page
  (`frontend/src/app/video/[jobId]/page.tsx` or the hook it uses) polls the generic per-image results
  endpoint (`GET /api/results/{id}`) on an interval even for a video job id, producing a 404 roughly every
  2.5 s until the poll is presumably cancelled elsewhere. Confirmed via `browser_network_requests` and the
  console log (10 identical 404 lines, ~2.5 s apart). Purely cosmetic — the video-specific data source
  (`GET /api/video/{id}`) is what the page actually renders from, and it was correct throughout. Not fixed
  in this entry.
- **First genuine confirmation of the D4 media-key path in a browser**, not just via `httpx`/curl: the video
  `<video>` element's stream request carried `?key=...` and received `206 Partial Content`, and the
  Download Results link's `href` carried the same key. This is what Q-027's `useConnection()`/`mediaUrl()`
  fix (hydration-safety) was written to guarantee; this run is its first real-browser evidence.
- Operational note, not a code defect: `systemd-run` without an explicit `WorkingDirectory` silently broke
  every relative-path case in the smoke script and wrote its (gitignored, still real) output file into
  `~/results/evaluations/` outside the repo. Deleted after diagnosis, per the standing disk-hygiene rule.

### 4. Verification

- Result files (gitignored): `results/evaluations/cloud_smoke_20260918_1141.json` (L4 first),
  `…_1144.json` (L4 warm).
- Browser artifacts saved to `~/Downloads/satquery_cloud_results_2026-09-17/browser_check/`:
  `1_system_connected.png`, `2_video_result_red_car.png`, and the full job output
  (`job_4c310c8a/{result.json,trace.json,video/…}`) pulled from the Modal results volume with
  `modal volume get`.
- GPU identity: `modal container exec <container-id> -- python -c "import torch; print(torch.cuda.get_device_name(0), ...)"`
  → `NVIDIA L4 22.0 GiB` (not inferred from `/api/health`, which only reports `device: cuda`).

### 5. Defence — "How do you know this ran on an L4 and not a T4 left over from before?"

"We didn't take Modal's word for the deploy config — we asked the running container directly. `modal
container exec` into it and asked PyTorch what GPU it sees; it answered 'NVIDIA L4', 22 GB, which is the L4's
real VRAM size and not the T4's 16 GB. That's the same container that served every request in this table."

## Q-038 · Trained road/building segmenters wired into the live query path — the first capability actually reaching users

**Recorded** 2026-09-18, atop `prototype` 5e0d965. This is the change Q-031's "what unlocked means" gate
was written for: until now every trained model in Q-025t..Q-037 existed only as a checkpoint plus an
adapter, with nothing routing to it. This entry covers roads and buildings only.

### 1. Mechanism

`run_grounding_pipeline` (`backend/app/workflows/grounding.py`) funnels every mask/box query through
Grounding DINO → V4 reasoning → SAM 2. A dispatch check now sits between query parsing and detector
invocation:

- `classify_trained_segmenter_target` (new module `backend/app/workflows/trained_segmenter.py`) returns
  `roads_segmenter` / `buildings_segmenter` / `None`. It routes to a trained segmenter **only** when all
  hold: the routing flag is on; `_wants_all_instances(...)` is True (the pipeline's own existing
  category-vs-single-target signal — deliberately reused, not reimplemented, so the two can't drift);
  no relational or colour qualifier in the parsed query; and the parsed category matches exactly one of
  the road/building vocabularies.
- Everything else falls through to the existing path **byte-unchanged**: single-target ("the largest
  building"), ordinal, size/position, relational ("the road near the school"), colour ("red buildings"),
  multi-class ("roads and buildings"), and every class without a trained segmenter (cars, ships, planes,
  tanks, tennis courts...).
- If the target class matches but the checkpoint or trainer module is unavailable, a
  `trained_segmenter_unavailable` trace step is recorded and the query falls back to the detector path
  rather than erroring.
- `run_trained_segmenter_path` returns the same response shape callers already consume, with a distinct
  `strategy` (`trained_segmenter_roads` / `trained_segmenter_buildings`) so this path is never confusable
  with a V4 result in logs or evidence, and an `evidence.trained_segmenter` block carrying checkpoint,
  threshold, threshold source, coverage and encoder.
- Toggle: `configs/app.yaml` `trained_segmenter_routing.enabled` (default **true**), env override
  `SATQUERY_TRAINED_SEGMENTERS_ENABLED`.

**Resolution caveat, deliberately not papered over.** The segmenters were trained at 0.5 m/px
(Q-025t/Q-026t/Q-032). `run_grounding_pipeline` has no GSD metadata for an arbitrary uploaded image, so
this path runs the model at the image's **native resolution** and says so in the answer text. No
resampling step was invented, because none was validated. A caller that knows its GSD should resample to
0.5 m before calling.

### 2. What this changes for a user

| Query | Before | After |
|---|---|---|
| "mark all roads" | Grounding DINO + SAM 2, IoU 0.031 DeepGlobe / 0.021 Massachusetts (Q-025t) | trained U-Net, IoU 0.557 / 0.616 (Q-032) |
| "segment buildings" | IoU 0.635 WHU / 0.191 Massachusetts (Q-026t) | 0.834 / 0.695 (Q-032) |
| "mark the largest building", "find the road near the school", "mask red cars", "mask airplanes" | unchanged | unchanged |

The accuracy figures are carried over from the training entries — this change routes to those
checkpoints, it does not re-measure them.

### 3. Blast radius

- **This is the highest-risk change of the session:** it sits inside the function every object-class
  query, and video frame grounding, passes through. Mitigations: narrow dispatch conditions, reuse of the
  existing all-instances signal, a kill switch, unavailable-checkpoint fallback, and the regression run
  in §4.
- Roads/buildings answers now have `selected_box: None` and an empty `instance_boxes` — a class mask has
  no single selected instance. Downstream consumers were checked for None handling; anything new that
  assumes a box must handle it.
- Only roads and buildings are wired. Craters, land cover, water, cloud and ISPRS remain checkpoint-only
  (Q-031's gate not yet passed for them).
- Not re-validated at non-0.5 m resolutions (see §1).

### 4. Verification

Independently re-run in this session, not taken from the subagent's report:
- `tests/unit/test_trained_segmenter_dispatch.py` — **20 passed** (dispatch decisions, no weights needed:
  segmenter for "mark all roads"/"segment buildings"; fallback for ordinal, relational, colour, wrong
  class, and flag-disabled).
- `tests/models/test_grounding_trained_segmenter.py` — **1 passed**, real end-to-end: logs confirm it
  loaded `checkpoints/roads_all_r50_seg/best.pt` (unet/resnet50, epoch 54, threshold 0.35) and ran real
  inference through `run_grounding_pipeline`.
- Full suite `tests/unit tests/models -m "not models"`: **326 passed, 3 failed** — the same three
  pre-existing `test_geotiff_georeferencing.py` GDAL/rasterio failures that fail on 541b0f2 without any
  of this work. Count rose from 306 (Q-035..Q-037 baseline) by the 20 new dispatch tests.
- API assumptions spot-checked directly against source: `parsed["category"]`,
  `model_registry.is_model_available`, the adapter's `class_name`/`checkpoint_path`, and `ModelResult`'s
  `masks`/`confidence`/`metadata`.

### 5. Defence — "You changed the function everything depends on. How do you know you didn't break it?"

"Because the fallback is the old code path, untouched, and we proved it still runs: 326 tests pass, the
only failures are three that already failed before this work existed. The new path is entered only when
four independent conditions all agree, it reuses the pipeline's own category signal rather than a second
opinion that could drift, and it can be switched off in config with no code change. A reviewer who
distrusts it can set `trained_segmenter_routing.enabled: false` and get the exact previous behaviour."

## Q-039 · Water and cloud routed (measured 4.2x and 16x over the detector path); land cover and ISPRS deliberately not routed

**Recorded** 2026-09-20, atop `prototype` 74e65c2. Extends Q-038, which wired the first two classes
(roads, buildings). Also records a third system crash and the safety hole that allowed it.

### 1. What now routes, and the measurement behind it

Q-038's dispatch gained `water_segmenter` and `cloud_segmenter`. Unlike roads/buildings — which were
justified by Q-025t/Q-026t before wiring — these were initially routed on a *structural* argument only
(a whole-image region class suits a class segmenter better than an open-vocabulary box detector). That
gap is now closed; both were measured on held-out test tiles, same script, same tiles, both methods:

| Query | Detector path (GroundingDINO + V4 + SAM 2) | Trained segmenter | Tiles |
|---|---|---|---|
| "mask all water" (`water_bodies`, 10 m) | IoU **0.0942** (P 0.588 / R 0.101, 1.0 s/tile) | IoU **0.3944** (P 0.975 / R 0.398) | 60 |
| "mask all clouds" (`cloud95`, 30 m) | IoU **0.0404** (P 0.720 / R 0.041, 0.6 s/tile) | IoU **0.6424** (P 0.874 / R 0.708) | 60 |

Water's 0.394 is the pixel-weighted pooled metric whose behaviour Q-035 explains (per-tile median is
0.866); both columns are computed identically, so the comparison is fair even where the absolute
number understates the model.

Vocabulary needed a **compound-noun exclusion list**: bare `water`/`cloud` must be in the vocabulary,
but measured against the real parser `mask all water tanks` → category "water tanks", `mask the water
tower` → "water tower", `mask the cloud shadows` → "cloud shadow" would all have been captured by the
class segmenter. `waterfront`/`watershed`/`cloudy` need no entry (word boundaries handle them).

Cloud reachability was **measured, not assumed**: `mask the clouds` / `mask all clouds` / `segment
clouds` reach `single_image_grounding` via the router's fallback noun-phrase extractor, while the
quality phrasings that should *not* segment (`is this scene cloudy`, `how cloudy is this image`,
`remove the clouds`) classify as `single_image_vqa` and never reach the dispatch. No router change was
needed.

### 2. Deliberately NOT routed, with reasons

- **Land cover (7-class)** — the response contract genuinely cannot carry it, verified in source:
  `backend/app/evidence/fusion.py` does `(segmentation_mask > 0).astype(np.uint8) * 255` and passes the
  result to `mask_to_geojson(binary_mask=...)`. A 7-class index map would be silently reinterpreted as
  "class 0 background, classes 1-6 one single object" — wrong area statistics and wrong polygons, not
  merely unhelpful output. Reachability is near-nil anyway: "show land cover", "what is this area used
  for", "land use map" all classify as VQA.
- **ISPRS Potsdam / Vaihingen** — registered and callable, not auto-routed. ISPRS answers the *same*
  "buildings"/"roads" questions as the 0.5 m models but at 5-9 cm, and no GSD (nor band composition,
  which would distinguish Potsdam RGB from Vaihingen IRRG, Q-036) reaches the dispatch function. There
  is no basis to auto-select even a city. No resolution guesser was invented.

### 3. Two bugs found while wiring, both user-facing

1. **A 20x/60x false accuracy claim.** `BinarySegmenterAdapter` hard-coded the trainer's
   `TARGET_GSD_M` (0.5 m) as `trained_gsd_m` for *every* checkpoint, and that value is interpolated
   into the answer text ("Trained and validated at {x} m/px"). Water is 10 m and cloud 30 m, so routing
   them unchanged would have told users a resolution 20x/60x wrong. Fixed with a `trained_gsd_m`
   ModelSpec field (the binary trainer writes `--target-gsd` to `report.json` only, never into the
   checkpoint dict); multi-class checkpoints do store `target_gsd` and it takes precedence. Asserted in
   the end-to-end test.
2. **The evaluation script had started comparing the trained model against itself.** After Q-038 wired
   roads/buildings, `eval_road_baseline.py`'s "baseline" call to `run_grounding_pipeline` was itself
   routed to the trained model for any routed class. The first cloud run returned *identical* IoU to 4
   decimal places for both columns at 0.03 s/tile (versus ~1.0 s/tile for a real detector run) — the
   tell that caught it. The script now forces `settings.trained_segmenter_routing.enabled = False` for
   the baseline. **The water numbers in §1 predate the merge and are unaffected**; the cloud numbers in
   §1 are from the corrected run. Any future head-to-head on a routed class must use the fixed script.

`LandCoverSegmenterAdapter` also hard-rejected any class count ≠ 7, which excluded the 6-class ISPRS
checkpoints; the comment justifying it was factually wrong (`infer_logits` reads K from the model the
adapter builds, not from the trainer). Now a non-empty check.

`configs/models.yaml` `landcover_segmenter` repointed from `landcover_dg_lv_oem_seg` (ResNet-34) to
`landcover_full_r50_seg` — better on all three splits, no measured downside (Q-037).

### 4. Third system crash, and the safety hole behind it

The desktop froze again on 2026-09-20, requiring a hard reboot. No OOM record and a 19-minute gap in
`sysmon.log` — the same signature as 2026-09-17. Unproven trigger; the last sample before the gap shows
6.9 GB available with 3.8 GB of swap already in use, after which an agent downloaded two ~700 MB
checkpoints (HF's Xet backend was measured holding 4.7 GB for one download earlier in this project).

The **structural** cause is certain even though the trigger is not: `satquery.slice` had
`MemoryMax=14056M` on a 14 GB machine — an aggregate limit that permitted essentially all RAM. Three
individually-capped jobs (a 5 GB eval plus two agents) summed past physical memory. Per-job caps never
bounded the total. Fixed:

| | Before | After |
|---|---|---|
| `satquery.slice` aggregate | 13.7 G (no real limit) | **`MemoryMax=8G`, `MemoryHigh=6G`** |
| `satquery-mem-guard` fires at | 1 GB available | **2.5 GB available** |
| HF transfer backend | Xet (measured 4.7 GB for one file) | **disabled** (`HF_HUB_DISABLE_XET=1`) |

Subagent shell commands do not inherit the slice, so an agent's own `pip install` / `hf download` is
unguarded — which is why *concurrency*, not any single job's size, was the real hazard. Operating rule
now: one heavy job at a time.

### 5. Verification

Full capped suite **352 passed, 3 failed** (up from 326 in Q-038; +26 are the new dispatch tests). The
3 are the same pre-existing `test_geotiff_georeferencing.py` GDAL failures and remain the only
failures. End-to-end on a held-out tile: `run_grounding_pipeline(img, "mask all water")` →
`trained_segmenter_water`, threshold 0.20 from the checkpoint, `trained_gsd_m` 10.0, "Sentinel-2" in
the answer, no `call_grounding_dino`/`call_sam2` steps, IoU 0.840 against truth. Head-to-head JSONs in
`results/training/{water,cloud}_h2h.json`.

### 6. Defence — "You routed water and cloud before measuring them. Why should we trust the rest?"

"The subagent that wired them said so in its own report rather than hiding it, and the routing was not
accepted until both were measured — 4.2x and 16x, on held-out tiles, with the same script scoring both
sides. The same review caught two user-facing bugs: an answer string that would have claimed the wrong
resolution by a factor of 20 to 60, and an evaluation script that had quietly started grading the model
against itself. Neither was in the brief; both were found by re-running the work rather than reading
the summary."

## Q-040 · LAE-DINO checkpoints are MMDetection-format: adopting them is not a quick win, and neither is the LAE-1M fine-tune

**Recorded** 2026-09-20, atop `prototype` 196e017. Closes the open question from Q-031's roadmap:
"Grounding DINO fine-tuned on LAE-1M — needs the cloud GPU". **Recommendation: do neither, for now.**

### 1. What was checked

Q-031 listed a LAE-1M fine-tune of Grounding DINO as the largest remaining planned capability and the
only one needing a cloud GPU. Before paying for that, the authors' own released weights were examined,
on the theory that their checkpoint might already be what we would have trained.

Two checkpoints were downloaded (kept at `checkpoints/lae_dino/`, ~694 MB each):
- `lae_dino_swint_lae1m-28ca3a15.pth` — **trained on LAE-1M itself**, i.e. precisely the target of the
  planned fine-tune. Its existence was not previously known to this project; it was found while
  surveying the HF repos.
- `lae_dino_swint_fintune_dior-e612b298.pth` — the DIOR-fine-tuned variant.

### 2. Finding: wrong framework, not merely a different file layout

Both are **bare MMDetection state dicts**, not HF `transformers` checkpoints. Evidence (key names):

```
level_embed
backbone.patch_embed.projection.weight
backbone.stages.0.blocks.0.attn.w_msa.relative_position_bias_table
```

`stages.N.blocks.N.attn.w_msa` and `patch_embed.projection` are open-mmlab `SwinTransformer` naming;
`level_embed` is the MMDet DINO head. HF's `GroundingDinoForObjectDetection` uses an entirely different
module tree (`model.backbone.conv_encoder...`, `model.encoder.layers.N.self_attn...`). 1004 and 1053
tensors respectively, with **no `meta` key** — so no embedded config either; their repo's config file
would also be required.

Consequences:
- Running them needs `mmdet` + `mmcv` + `mmengine`. `mmcv`'s compiled ops track specific PyTorch
  versions; this project is on torch 2.14 with CUDA 13. That is an isolated-environment build with a
  real chance of not resolving, and it was not attempted here (two prior attempts at this task were
  killed — one by an API rate limit, one by the machine freeze in Q-039).
- The alternative, writing an MMDet→HF key-mapping converter, is not a rename job: the two
  implementations differ structurally, and a wrong mapping produces plausible-looking garbage rather
  than an error, so it would need its own validation against published numbers.
- Either way the product would carry a second inference stack, or a converted model nobody upstream
  validates.

### 3. Why this also argues against our own LAE-1M fine-tune

The planned cloud fine-tune would produce approximately what `lae_dino_swint_lae1m` already is. If
their artefact is impractical to serve here, ours would face the same problem from the other
direction: we would either train inside their MMDet codebase (inheriting the same stack) or implement
Grounding DINO fine-tuning against HF transformers ourselves — more work than the GPU time it would
have bought. The cloud GPU was never the bottleneck; the serving stack is.

### 4. What we give up, stated plainly

LAE-DINO addresses **open-vocabulary** detection — arbitrary phrases like "storage tanks", "helipads",
"roundabouts" — which is a different capability from the class-specific segmenters now shipping. The
measured wins to date (Q-038, Q-039: roads, buildings, water, cloud at 4x to 20x over the detector
path) came from small task-specific models, not from better open-vocabulary detection. Queries outside
the trained classes still fall through to zero-shot Grounding DINO with its known weakness (Q-028:
AP50 0.024 on craters).

**Not measured:** whether either LAE-DINO checkpoint actually beats zero-shot Grounding DINO on our
data. The format finding blocked the comparison; no accuracy claim is made here in either direction.

### 5. Recommendation

1. **No cloud GPU for training.** Every model now shipping was trained on the local RTX 3070.
2. **Keep both checkpoints** (1.4 GB, `checkpoints/lae_dino/`) rather than re-download later; the
   LAE-1M one is the relevant artefact if this is ever revisited.
3. **Revisit only if** open-vocabulary detection becomes a demo requirement, and then budget it as an
   environment/integration task, not a training task.

### 6. Defence — "You planned a fine-tune and then didn't do it. Was that a reversal?"

"It was the result of checking before spending. The plan assumed the blocker was GPU hours. Inspecting
the authors' released weights showed the blocker is the serving framework: their artefacts are
MMDetection, ours is HF transformers on torch 2.14, and that gap costs the same whether we train the
model ourselves or download theirs. We also found they had already published a LAE-1M-trained
checkpoint, which is what our fine-tune would have reproduced. The honest conclusion is that the cloud
GPU would not have bought the capability we wanted."

---

## Q-041 · Ayushman's 2026-09-20 delivery: EuroSAT verified and wireable, flood preprocessing unrecoverable, burn scars blocked on terratorch

**Recorded** 2026-09-20, working tree on `prototype` (not yet rebased onto `d0daed7`). Work was paused
mid-task at the user's request; nothing is committed. Full state and the resume list:
[`project/handoff/ayushman-delivery-2026-09-20.md`](handoff/ayushman-delivery-2026-09-20.md).

### 1. What was delivered, and what of it is new

`~/Downloads/ayushman/` held ~22 GB of archives containing **three new models** plus two already in
the repo. `checkpoints/locate_anything_3b/` and `checkpoints/changeformer/` already carried the
delivered LocateAnything and ChangeFormer artefacts (the ChangeFormer checkpoint byte-size matches at
492,691,833, and its reports are already at `docs/models/changeformer/`), so those are re-deliveries.

**EuroSAT was nested inside another archive.** `drive-download-20260920T125749Z-1-003.zip` (1 GB) is a
superset bundle containing `eurosat_efficientnet_b0.zip`. Extracting only the top-level archives
misses an entire model — worth knowing for the next hand-off.

All four delivered checkpoints were hashed and matched their manifests:
`burnscars … bb1ce3b5…a8dc8` ✅, `flood best.pt … 5d6a26b6…274f6` ✅, `flood last.pt … 281c86c4…92554` ✅.
The EuroSAT checkpoint shipped with no manifest; its hash is recorded as
`dbbfa69d48baa47ee813ae0465ce46e72c412159a5564e8e26d6d5044f012347`.

### 2. Mechanism — what the code does, step by step

Two modules were written, neither yet registered:

- `backend/app/ml/adapters/eurosat.py` — `EuroSatLandCoverAdapter`. Builds
  `torchvision.efficientnet_b0`, replaces `classifier[1]` with `Linear(1280, len(class_names))`, and
  loads `ckpt["model_state_dict"]` with **`strict=True`**. Class names, training image size, epoch and
  best validation accuracy are read from the checkpoint, not hard-coded, and the load refuses if the
  head's output width disagrees with the length of `class_names` (that mismatch would silently mislabel
  every prediction). `confidence` is the real softmax probability of the winning class; the full
  distribution and the ranked top-k go in `metadata`.
- `backend/app/ml/adapters/flood_unet.py` — `UNetFromScratch`, reconstructed from the checkpoint's 118
  state_dict entries because the training script was not delivered: encoder 16→32→64→128, bottleneck
  256, `ConvTranspose2d` decoder, `output_layer` 1×1 → 2 classes, every conv `bias=False`, ReLUs at
  `block` indices 2 and 5 so the stored `block.0/1/3/4` line up. `strict=True` is what proves the
  reconstruction, and it passes.

  > **SUPERSEDED in part by Q-043 §3.** "every conv `bias=False`" is wrong: 18 of the 23 conv/deconv
  > tensors are bias-free (the `DoubleConv` 3x3 convolutions), while the four `ConvTranspose2d`
  > upsamplers `up4`..`up1` and `output_layer` each carry a bias. The code was always correct; this
  > sentence over-generalised it.

### 3. Rationale — why this over the rejected alternative

**EuroSAT is registered but deliberately not routed.** The grounding pipeline's response contract is a
mask or a box; a scene-level classifier produces neither, so routing it there would mean inventing a
localisation it cannot do. Same reasoning the crater detector is unrouted (Q-028) and agreed with the
local-GPU session for flood and burn scars.

**`terratorch` was not installed for the burn-scar model.** This venv is `torch 2.14.0+cu130`;
terratorch pins tightly and a plain install risks downgrading torch/torchvision under the eight working
adapters. Trading eight working models for one unverified one is not a call to make unilaterally.

> **SUPERSEDED by Q-045 §1.** The premise is wrong. `torch 2.14.0+cu130` is PyPI's own default build
> string for torch 2.14.0, not a custom CUDA-13 pin — the installed wheel has no `direct_url.json` and
> is a plain `manylinux_2_28_x86_64` wheel from an index. A resolve-only probe shows terratorch pulls
> **the identical torch 2.14.0 / torchvision 0.29.0 / timm 1.0.29 / smp 0.5.0 / numpy 2.4.6**, so it
> cannot disturb the eight adapters. The decision not to adopt it still stands, but on different and
> better grounds — see Q-045.

### 4. EuroSAT — verification, and why it closes mandatory requirement #1

`memory.md` §0 lists "RS adaptation evidence (BigEarthNet) — mandatory req #1" as open. EuroSAT closes
it with a measured score on a held-out split.

Recomputed independently from the delivered per-sample predictions
(`docs/models/eurosat/evaluation/predictions/y_{true,pred,prob}.npy`, 4050 samples):

| Metric | Delivered | Recomputed |
|---|---|---|
| accuracy | 0.9832098765432099 | 0.9832098765 |
| balanced accuracy | 0.9824222222222222 | 0.9824222222 |

Also verified: `y_prob` rows sum to 1, and `argmax(y_prob) == y_pred` for all 4050 rows. The report is
internally consistent and was not written by hand.

**The limit, stated plainly:** the EuroSAT images are not in this repository, so this is a recomputation
of the delivered predictions, **not** a re-measurement from pixels. Tiles are Sentinel-2 at 10 m/px,
64×64, upsampled to 224. Accuracy on sub-metre aerial photography is **NOT MEASURED**.

### 5. Flood — the preprocessing could not be recovered, and the delivered threshold is not transferable

The delivery fixes the 16-channel order (S1 VV/VH, 13 S2 bands, DEM) but **never states the training-time
normalisation**; `training_config.json`, `model_metadata.json` and the checkpoint's embedded `config` all
omit it. On a BatchNorm network a wrong input scale does not crash, it just predicts badly.

Measured on the **official** Sen1Floods11 test split (90 scenes, all four modalities verified present).
Ayushman's report uses a 67-scene "multimodal eligible" subset whose manifest is on his Windows machine,
so the sets are not identical. Scripts: `scripts/flood_preproc_recovery/`; per-scene confusion counts at
both thresholds: `results/evaluations/flood_preproc_recovery_20260920/flood_per_scene.json`.

Sweep 1, seven schemes scored on test:

| scheme | global IoU | per-scene IoU | precision | recall |
|---|---|---|---|---|
| raw, no normalisation | **0.5403** | 0.3557 | 0.5695 | 0.9133 |
| per-scene min-max | 0.4528 | 0.3327 | 0.9742 | 0.4583 |
| S2 ÷ 10000 | 0.3043 | 0.1228 | 0.4279 | 0.5130 |
| *delivered (67 scenes)* | *0.6292* | *0.4075* | *0.7873* | *0.7580* |

Sweep 2, ten schemes selected on **validation** (89 scenes) then scored once on test — selecting on test
and quoting that number would be selection on the test set:

- Best on validation: `s1clip30_s2/10k_dem0` (S1 clipped to [−30, 0] dB → [0, 1], S2 ÷ 10000, **DEM
  replaced with zeros**), validation IoU 0.6307.
- That scheme on test: **IoU 0.7034 argmax, 0.7273 at threshold 0.30.**

**Three reasons this is not a reproduction:**

1. The winning scheme needs the **DEM channel zeroed**. A model genuinely trained on DEM would not
   prefer it removed, so the DEM handling is wrong or unknown — and a 16-channel model fed zeros in
   channel 15 is not the model that was evaluated.
2. Under every scheme tried here, argmax and threshold 0.30 land in the same place (0.5403 vs 0.5402 for
   raw). The delivery reports a genuine difference (0.6292 → 0.6211, precision 0.787 → 0.722, recall
   0.758 → 0.816). Different threshold behaviour means different probability calibration, so **the
   delivered 0.30 threshold does not transfer.**
3. Scoring *above* the report (0.703 vs 0.629) is not good news. On a different scene set under a
   different preprocessing it only confirms we are not running the delivered configuration.

No subset of the 90 scenes reproduced 0.6292 either — tried no-label-nodata (16 scenes, 0.5407),
has-flood-GT (83, 0.5443), no-all-zero-S2 (86, 0.5479), s2_min>0 (86, 0.5479).

**Disposition: do not ship as a working capability.** Ask Ayushman for the normalisation constants (or
the training script) — one message unblocks a real capability, everything else is guesswork.

> **SUPERSEDED by Q-044.** The normalisation *was* recoverable, without the author: it is encoded in
> the checkpoint's own 18 BatchNorm layers, which store the statistics of their training-time inputs.
> Per-scene 2/98 percentile clipping into [0, 1], selected label-free on the train split, scores IoU
> 0.6244 / F1 0.7684 on the official 90-scene test split against the delivered 0.6292 / 0.7724, and
> reproduces the delivered threshold response. This section's search also had a bug: 6 of the 90 test
> scenes carry NaN in S1 and were not sanitised, which poisoned every per-scene candidate and
> flattered `raw` — itself refuted by a factor of ~3000 against the stored statistics. Serving remains
> gated off by default because a recovery is not the author's confirmation. Note also
that `frontend/src/components/query/QueryBar.tsx:18` already advertises a "Flood extent" chip that
routes nowhere, which `FRONTEND_POLISH.md:153` had already flagged.

### 6. Burn scars — genuine checkpoint, three problems in the evidence

The checkpoint is real and fully consistent with the delivered `model_config.yaml`: PL 2.6.6,
`terratorch.tasks.SemanticSegmentationTask`, `EncoderDecoderFactory`, backbone `prithvi_eo_v2_300`
(ViT-L: 24 blocks, width 1024, `patch_embed` a **Conv3d** `(1024, 6, 1, 16, 16)`, `pos_embed` 197 → 224×224),
necks `SelectIndices[5,11,17,23]` → `ReshapeTokensToImage` → `LearnedInterpolateToPyramidal`, decoder
`UNetDecoder` 512/256/128/64, head 1×1 → 2 classes. 355 tensors, ~324.4 M params. Missing from `.venv`:
`terratorch`, `lightning`, `einops`.

Three things that must be settled before any burn-scar number is claimed:

1. **Two delivered metric files disagree for the same claimed test set.** Both state 264 scenes and
   68,627,952 valid pixels. `final_test_metrics.json`: precision 0.8246 / recall 0.7601 / F1 0.7910,
   matrix `[[61248239, 1027123], [1524085, 4828505]]`. `final_test_metrics_threshold_040.json` (the one
   the manifest embeds): precision 0.7857 / recall 0.8000 / F1 0.7928 / IoU 0.6567, a different matrix.
   Most likely the first is the argmax/0.5 run mislabelled rather than fabricated — but quote one and
   say which.
2. **It was trained from scratch** (`backbone_pretrained: false`). A Prithvi-EO-2.0 300M ViT-L trained
   from scratch on 432 scenes is **not** evidence of geospatial-foundation-model adaptation — the
   pretrained backbone is the whole point of Prithvi. Do not describe it as foundation-model transfer.
3. **The pooled IoU hides per-scene collapse.** In `failure_analysis/lowest_recall_summary.csv`, 15 test
   scenes have burn IoU ≈ 0 and **7 predict literally zero burn pixels** against 1.2–5.2% ground-truth
   burn fraction (193, 198, 203, 223, 224, 234, and 261/260/236 below 0.05%).

   > **SUPERSEDED by Q-042 (2026-09-20).** Every count in the paragraph above is wrong: it was read
   > off `lowest_recall_summary.csv` (15 rows = the 15 *lowest-recall* scenes, not a count of
   > IoU≈0) instead of the full 264-row `per_scene_metrics_threshold_040.csv`. The correct figures,
   > recomputed from all 264 rows, are in **Q-042 §1**. The qualitative claim — that the pooled IoU
   > hides whole scenes the model misses entirely — holds and is if anything understated.

### 7. Blast radius — what breaks if this is wrong

Nothing in the serving path yet: neither new adapter is registered, `configs/models.yaml`,
`registry.py`, `intent_classifier.py` and `trained_segmenter.py` are untouched, so the 352-passing
suite and every existing capability are unaffected.

> **SUPERSEDED in part by Q-043 §1.** Two errors here. (a) "the 352-passing suite" was never
> reproducible from a clean checkout — 352 depended on an untracked `tests/__init__.py`; the real
> pre-work baseline was **394 passed, 3 failed**. (b) "neither new adapter is registered … untouched"
> was true when written but stopped being true the same day: `eurosat_classifier` and
> `flood_segmenter` were registered in `dce3ac3`, and `configs/models.yaml` and `registry.py` were
> both edited. Current suite: **430 passed, 3 failed**. The staged checkpoints sit under gitignored
`checkpoints/`. The risk is **documentary**: if the flood or burn-scar numbers were quoted as ours, the
flood threshold would be wrong and the burn-scar model would be misdescribed as foundation-model
adaptation. That is what §5 and §6 exist to prevent.

### 8. Verification — the specific checks that were run

- `sha256sum` on all four checkpoints against the delivered manifests (§1).
- EuroSAT: `strict=True` load into `torchvision.efficientnet_b0` + a real forward pass to `(1, 10)`;
  accuracy and balanced accuracy recomputed from the delivered `.npy` predictions and matching to 10 dp;
  `y_prob` rows sum to 1; `argmax(y_prob) == y_pred` on all 4050 rows.
- Flood: `strict=True` load of the reconstructed `UNetFromScratch`; 17 preprocessing/threshold
  evaluations over 90 test and 89 validation scenes on real Sen1Floods11 imagery and hand labels.
- Burn scars: checkpoint inspected with `mmap=True, weights_only=True` (no 3.6 GB ever resident);
  `hyper_parameters` cross-checked against the delivered yaml; prefix census of the 355 tensors.

### 9. Defence — answering a challenging reviewer

*"You measured the flood model higher than its own report — why not claim that?"* Because it is not the
same measurement. Different scene set, and a preprocessing that only wins with the DEM channel zeroed,
which cannot be what a 16-channel DEM-trained model did. A higher number obtained under a configuration
the authors did not use is not a better result, it is a different experiment. The delivered threshold
provably does not transfer, since argmax and 0.30 coincide here and diverge in their report.

*"Then why keep the checkpoint at all?"* The architecture is proven exact by a `strict=True` load of a
118-entry state_dict, and the hashes match. What is missing is four numbers' worth of normalisation
metadata, which the author can supply.

*"Is the burn-scar model foundation-model adaptation?"* No. `backbone_pretrained: false` — it is a
Prithvi-shaped ViT-L trained from scratch on 432 scenes. It is a legitimate segmentation result and an
illegitimate transfer-learning claim, and the transcript says so before anyone asks.

---

## Q-042 · Correcting Q-041 §6.3, and four further findings in Ayushman's delivered evidence

**Recorded** 2026-09-20, same session as Q-041, before either was committed. **This entry supersedes
Q-041 §6.3**, which is annotated in place and left standing. Nothing else in Q-041 changes.

The error was caught while writing `docs/models/burnscars.md` from the delivered CSVs, by reading the
full 264-row `per_scene_metrics_threshold_040.csv` rather than the 15-row
`failure_analysis/lowest_recall_summary.csv` that Q-041 had used.

### 1. The corrected per-scene failure counts

Q-041 §6.3 made three mistakes at once: it treated the row count of a *lowest-recall* extract as a
count of IoU≈0 scenes, conflated "predicted no burn pixels" with "got no true positives", and quoted
a ground-truth range belonging to the wrong group.

| claim | Q-041 §6.3 said | actually (all 264 rows) |
|---|---|---|
| scenes at burn IoU exactly 0.0 | "15 … ≈ 0" | **10** |
| scenes predicting **zero** burn pixels | "7" | **6** — 193, 198, 203, 223, 224, 234 |
| scenes with **zero true positives** | conflated with the above | **10** — the six above plus 211, 236, 260, 261 |
| GT burn fraction of the zero-prediction scenes | "1.2–5.2%" | **1.438% – 5.194%** |
| "261/260/236 below 0.05%" predicted | three scenes | only **260 (0.047%)** and **261 (0.034%)**; **236 is 0.154%**, ~3x that, and 211 is 0.795% |

Verified by recomputation from `docs/models/burnscars/per_scene_metrics_threshold_040.csv`:
`predicted_burn_pixels == 0` → 6 scenes; `true_positive == 0` → 10 scenes; `burn_iou == 0.0` → 10.
Distribution of per-scene burn IoU: 11 below 0.01, 23 below 0.05, 30 below 0.10.

**Not delivered, computed here:** mean per-scene burn IoU **0.5634**, median **0.6584**, against the
pooled **0.6567**. So for burn scars the pooled and per-scene figures happen to agree closely — unlike
the flood model, where they diverge sharply (0.629 vs 0.407). The correct criticism of the burn-scar
number is therefore not that the average is inflated, but that **10 of 264 scenes are complete
misses**, 6 of them predicting no burn at all on scenes that are 1.4–5.2% burned.

### 2. `val/mIoU` 0.8308 is not a burn-scar IoU and must never be quoted as one

The `ModelCheckpoint` callback state inside the checkpoint selected epoch 08 on `val/mIoU = 0.8308`
(epoch 06 was 0.8276). That is the **2-class mean** IoU, averaged over "Not burned" and "Burn scar",
and it is dominated by the background class, which is ~88% of pixels. The burn-scar IoU at threshold
0.40 is **0.7128** on internal validation and **0.6567** on the held-out test set. Anyone quoting
0.83 as the model's segmentation accuracy would be overstating it by ~0.17 IoU.

### 3. Stronger evidence on which of the two conflicting metric files is the threshold-0.40 run

Q-041 §6.1 recorded the conflict and guessed that `final_test_metrics.json` is a mislabelled
argmax/0.5 run. Two pieces of evidence now settle it:

- Its **ROC-AUC is byte-identical** to the 0.40 file's (0.9774894441090206). ROC-AUC is
  threshold-independent, so both files describe the **same model and the same scenes**, differing only
  in the operating point — which rules out a different evaluation run or a different split.
- Its precision is higher and recall lower than the 0.40 file (0.8246/0.7601 vs 0.7857/0.8000), which
  is exactly the direction a **higher** threshold moves them.

Also: `final_test_metrics.json` reports no IoU and no pixel accuracy at all, while
`final_test_metrics_threshold_040.json` does and is the one `model_manifest.json` embeds. **Quote the
0.40 file.** Ayushman should still confirm, but the delivery is now self-consistent rather than
contradictory.

### 4. The delivered burn-scar `model_config.yaml` is a config, not a run log

It disagrees with the manifest in four places, so it must not be cited as a record of what ran:
`max_epochs: 50` with EarlyStopping patience 15 against the manifest's 10 epochs; `seed_everything: 2`
against `split_seed: 42`; and the checkpoint's task hparam `lr` is 1e-3 while the yaml optimiser block
says 1e-4 (the scheduler's `_last_lr` confirms 1e-4 was actually in force). Independent confirmation
of the split size: `global_step` 3888 = 9 epochs x 432 scenes at batch size 1.

Separately, `failure_analysis/failure_panel_index.csv` has **broken pixel columns** (scene 248 shows
`valid_pixels = 2`) and disagrees with `lowest_recall_summary.csv`. Do not take numbers from it; use
`per_scene_metrics_threshold_040.csv`.

### 5. A new flood attack surface: the delivered test IoU exceeds its own validation IoU

The delivered test global flood IoU is **0.6292**, but the same checkpoint's own recorded
**validation** flood IoU at the same epoch is **0.4358** (`best.pt["metrics"]`, the only place it
appears — it is in no delivered JSON). Test scoring 0.19 higher than validation is not impossible, but
it is unexplained by the delivery and is the kind of gap a reviewer will ask about.

The likely explanation is a **reduction mismatch, not a real generalisation gain**: 0.4358 sits right
next to the test **per-scene mean** of 0.4075, not the test **global** 0.6292 — even though the
validation metric is named `global_validation_flood_iou`. If the "global" validation metric is in fact
a per-scene average, the two numbers are not comparable at all. This is recorded as **NOT
ESTABLISHED**; neither figure should be quoted without naming its reduction.

### 6. Q-041's flood sweep tables were partial, and the gaps are now marked

Q-041 §5 quotes 3 of the 7 sweep-1 rows and 1 of the 10 sweep-2 validation IoUs. The remaining scheme
*names* are recoverable from `scripts/flood_preproc_recovery/`, but four sweep-1 numbers were never
written down (`s2/10k+dem/1k`, `s1shift+s2/10k+dem/1k`, `per_scene_z`, `s2/10k+z(s1,dem)`).
`docs/models/flood.md` lists every scheme and marks those cells `NOT RECORDED` rather than inventing
them. The seven subset scores in Q-041 were re-derived from
`results/evaluations/flood_preproc_recovery_20260920/flood_per_scene.json` and **reproduce exactly**
(0.5403 / 0.5402 / 0.5407 / 0.5443 / 0.5479 / 0.5479), plus one Q-041 omitted: "no nodata AND flood
GT", 14 scenes, IoU 0.5407.

### 7. EuroSAT held up, with one wording correction

Every EuroSAT number in Q-041 §4 matched the delivered sources. The recomputation is in fact tighter
than claimed — accuracy and balanced accuracy agree to **16 decimal places**, not 10. One correction:
Q-041 says the `y_prob` rows "sum to 1"; they sum to 1 **within 2.1e-07** (float32 probabilities
widened to float64). The claim stands, the wording was loose.

> **SUPERSEDED by Q-043 §2.** Both halves of this are wrong: the measured maximum deviation is
> 2.1043325660e-07, which *exceeds* the stated 2.1e-07 bound, and `y_prob.npy` is stored as
> **float64** (carrying exactly-float32-representable values), so nothing is widened on read. The
> underlying claim — the rows sum to 1 to float32 precision — stands.

### 8. Why this matters more than the arithmetic

Three of the errors in Q-041 §6.3 all pushed the same way: they made the burn-scar failure sound
*worse and more specific* than the data supports ("15 scenes", "7 predict zero", a tidy "1.2–5.2%").
A transcript that overstates a weakness is as bad as one that launders a strength — both mean the
numbers cannot be trusted, and a reviewer who checks the CSV finds the record wrong. The cause was
reading a 15-row summary extract instead of the 264-row source. **Rule going forward: quote per-scene
statistics only from `per_scene_metrics_*.csv`, never from a `*_summary.csv` extract.**

---

## Q-043 · Two independent audits of Q-041/Q-042 and the new model docs: what they found

**Recorded** 2026-09-21, atop `prototype` `53c93a7`. **Supersedes Q-041 §7 and Q-042 §7 in part**, both
annotated in place and left standing. Two read-only audits were run over the delivery work: a numeric
fact-check recomputing every figure from the primary artefacts, and a link/path integrity audit. Both
found real errors. This entry records them, because a record that only contains the findings and not
the corrections is not a transcript.

### 1. Q-041 §7 was wrong about the test baseline, and went stale on registration

"the 352-passing suite" was never reproducible from a clean checkout: 352 depended on an **untracked**
`tests/__init__.py`, without which collection aborts entirely. The real pre-work baseline was **394
passed, 3 failed**; after the delivery work it is **430 passed, 3 failed** (the 3 are the long-standing
GDAL failures in `tests/unit/test_geotiff_georeferencing.py`). The same sentence's claim that "neither
new adapter is registered … `configs/models.yaml`, `registry.py` … are untouched" was true at the
moment of writing and false by the end of the day: both were registered in `dce3ac3`.

### 2. Q-042 §7's tightening of the `y_prob` claim was itself wrong, in both halves

It said the rows sum to 1 "within 2.1e-07 (float32 probabilities widened to float64)". Measured maximum
deviation is **2.1043325660e-07**, which *exceeds* that bound, and `y_prob.npy` is stored as
**float64** whose values are exactly float32-representable — so they were computed in float32, but
nothing is widened on read. Correct statement: within **2.2e-07**, stored float64 carrying float32
precision. The underlying claim is unharmed; a section written specifically to tighten loose wording
introduced two new inaccuracies, which is worth noticing about this failure mode.

### 3. Three factual errors in the new model docs, all now corrected

- **`flood.md` claimed "every convolution `bias=False`".** False, and it sat five lines above the
  document's own "`strict=True` is what proves the reconstruction … a spurious bias makes the load fail
  loudly" — i.e. inside the proof argument, about the exact property the argument turns on. Measured:
  of 23 conv/deconv weight tensors, **18 are bias-free** (the `DoubleConv` 3x3 convolutions) and **5
  carry a bias** — the four `ConvTranspose2d` upsamplers `up4`..`up1` and `output_layer`, which take
  PyTorch's default `bias=True`. The code was always right (`flood_unet.py` passes `bias=False` inside
  `DoubleConv` only); the prose generalised it. The same wrong claim was propagated into Q-041 §2, the
  handoff doc, the request to Ayushman and the `dce3ac3` commit message; the first is annotated here and
  the rest are fixed.
- **`burnscars.md` said "~262,144 valid pixels each"**, sourced to the file that refutes it: 102 of the
  264 scenes carry nodata, the smallest having **159,741** valid pixels (61% of the tile), for
  **68,627,952** in total rather than 264 x 262,144 = 69,206,016. That is the pixel base for every
  pooled metric in the document.
- **`burnscars.md` attributed a 9%-foreground figure to the internal-validation split.** 9.26% is the
  *held-out test* split's burn fraction; the internal-validation split is **11.96%** (derived two
  independent ways from all 17 rows of the threshold sweep, identical to 6 dp on every row). Q-042 §2's
  mirror figure — background "~88% of pixels" — is correct, since 1 − 0.1196 = 88.04%. So the pair was
  right in the transcript and wrong in the doc.

### 4. `CHECKPOINT_INVENTORY.md` asserted that two absent checkpoints were verified on disk

The highest-severity finding, and **pre-existing** rather than introduced by this work.
`grounding_dino` and `sam2` were both listed `Verified on Disk? YES` with timed real inference (1.408 s
/ 1.105 s) and status **AVAILABLE**. Neither directory exists; `find / -xdev` over the whole machine
finds no `*groundingdino*` or `*sam2_hiera*` above 10 MB. They are HuggingFace-backed —
`scripts/verify_checkpoints.py:38` lists both in `HUGGINGFACE_BACKED` and reports them `HF-backed`
rather than `MISSING` — so they download at first use. That is fine; asserting they are on disk and
timed is not, in the one document whose entire purpose is checkpoint provenance, and it is exactly the
kind of claim a mentor falsifies with one `ls`.

Three sizes in the same table were also wrong, re-measured 2026-09-21: `changeformer` **493 MB**
(492,593,071 B) not 164 MB; `cdvqa` **56.5 MB** (56,460,598 B) not 46 MB; `optical_sar` **30.0 MB**
(29,962,729 B) not 18.8 MB. Consequently the "3.896 GB for the ten original files" subtotal is the sum
of the table's own claimed sizes, **not a measurement**, despite sitting under a heading that says
measured — and it describes a fully warmed HF cache, not the current tree. The row count was also
wrong (11, actually 13 rows / 14 files), and "Combined Disk Footprint 7.884 GB" invited a
factor-of-two misreading: `du -sh checkpoints` is **15 GB** across ~40 weight files, because this table
documents 14 and silently omits the locally trained segmenters, `lae_dino` (1.45 GB) and
`scene_vlm_qwen3vl4b_nf4` (2.87 GB). All corrected, with the coverage boundary now stated.

Also corrected there: the `Real Inference Tested?` column, renamed to `Inference actually run? (what,
exactly)`, because it was misleading in opposite directions for the two new rows. EuroSAT's "YES" sat
in a column whose every other YES carries a wall-clock latency on real imagery, when what ran was a
load plus a forward — no accuracy was re-measured from pixels here. Flood's "LOADS ONLY" was right
about serving and wrong about inference: 17 real GPU sweeps over 179 scenes were run on that exact
checkpoint.

### 5. `flood.md` described the opposite of what the adapter does

It said the adapter "loads the real checkpoint, validates 16-channel input and returns a structured
refusal". `FloodSegmenterAdapter.predict` does none of the first two: the refusal is **unconditional**,
by design, because the blocker is the missing normalisation rather than anything the caller did, and
demanding a valid 16-band stack before refusing would imply the request is fixable. `load_model()` and
`validate_inputs()` do behave as described, but they are not on the serving path. The document also
never named `flood_segmenter.py` at all, only the architecture module.

### 6. What the audits confirmed — including the thing that was wrong last time

Q-042 §1's per-scene burn-scar statistics, which existed *because* Q-041 §6.3 got them wrong, are now
**completely correct**: `burn_iou == 0.0` → 10 scenes, `predicted_burn_pixels == 0` → 6
{193,198,203,223,224,234}, `true_positive == 0` → 10, zero-prediction GT range 1.4378%–5.1937%, counts
below IoU 0.01/0.05/0.10 → 11/23/30, mean 0.5634, median 0.6584. Every one of the 264 rows is
internally self-consistent (TP+FP+FN+TN = valid_pixels, TP+FN = burn_pixels, recomputed IoU matches to
<1e-9). Not a single per-scene number disagrees with the source.

Independently confirmed as well: all four checkpoint hashes and byte sizes; all six EuroSAT metrics
(accuracy and balanced accuracy **bit-identical**, the four AUCs to ≤2.3e-16, recomputed without
sklearn since it is not installed); all 52 cells of the EuroSAT per-class table; all 17x6 cells of the
burn-scar threshold sweep, with burn IoU and F1 both peaking at 0.40; both burn-scar metric files
recomputing bit-exactly from their own confusion matrices, with **identical** ROC-AUC (0.9774894441090206)
and identical GT-positive totals (6,352,590) — which strengthens Q-042 §3's argument that the two files
are the same model and scenes at different operating points; the 264-row CSV summing exactly to the
0.40 file's confusion matrix; all seven flood subset IoUs re-deriving exactly; the flood checkpoint's
`validation_flood_iou` 0.4358341431549679 appearing in no delivered JSON (Q-042 §5 confirmed); and
every burn-scar architecture claim including 355 tensors, **324,411,275** parameters and the
`val/mIoU` 0.8308090567588806 callback state at epoch 08.

The link audit confirmed every markdown link in ten documents resolves, `QueryBar.tsx:18` really is
the unrouted "Flood extent" chip, and `FRONTEND_POLISH.md:153` really does flag it.

### 7. Blast radius

Documentation only. No serving code changed in this entry's work; the suite is unchanged at 430 passed
/ 3 pre-existing failures. The risk being closed is reputational rather than functional: four of these
errors (§3's bias claim, §4's two absent checkpoints, §1's test count) are the kind a reviewer
falsifies in one command, and three of them sat inside the arguments they were meant to support.

### 8. Defence — what these audits say about the record

*"How much of your documentation is wrong?"* Two audits recomputed every number in five documents from
the primary artefacts. They found one false architecture fact, two wrong pixel/foreground figures, one
stale test count, one code-contradicting description, and a pre-existing inventory that vouched for two
checkpoints that are not on disk. Everything else — several hundred figures, including every per-scene
statistic, every hash, every metric recomputation and every architecture claim — reproduced exactly.
All six are corrected above and in the documents.

*"Why should we trust the corrections more than the originals?"* Because the corrections are
recomputations from the delivered artefacts with the commands recorded, not re-readings of prose. The
pattern worth noting is that **the errors clustered in summary prose, not in tables**: generalising
"`DoubleConv` convolutions have no bias" into "every convolution", rounding "at most 262,144" into
"~262,144 each", carrying a test count from a peer's message without reproducing it. The tables, which
were transcribed from the source files, were right. Q-042 §8's rule (quote per-scene statistics only
from the 264-row source, never a summary extract) generalises: **prose that summarises a table is a
claim and needs checking against the table.**

---

## Q-044 · The flood preprocessing was recovered from the model's own BatchNorm statistics — we were not blocked on the author

**Recorded** 2026-09-21, atop `prototype` `087190f`. **Supersedes Q-041 §5's conclusion** that the
training-time normalisation could not be recovered, and corrects a bug in that search. Prompted by the
question "can't we proceed without Ayushman returning the doc?" — the answer turned out to be no, we
could not, only because the search had been looking in the wrong place.

### 1. Mechanism — the checkpoint contains its own preprocessing

Q-041 §5 searched by scoring candidate normalisations **against labels**, which was the wrong
instrument: many wrong preprocessings produce plausible IoUs, and the best-scoring one needed the DEM
channel zeroed, which cannot be what a DEM-trained model did.

Every BatchNorm layer stores `running_mean` and `running_var` estimated **during training, from its own
input**. Those statistics are therefore a fingerprint of the training-time input distribution, and they
are in the checkpoint. Reading them requires no labels at all.

Two rounds:

- **First layer only** (`scripts/flood_preproc_recovery/flood_recover_from_bn_stats.py`).
  `encoder1.block.1` stores means of order 0.05–0.91 and stds 0.07–0.36. Raw Sentinel-2 digital numbers
  are of order 1000, so raw input would drive the first convolution's output into the thousands.
  Measured discrepancy for the `raw` scheme: **2^11.6, a factor of ~3000**. So `raw` — the scheme that
  scored *best* against labels in Q-041 §5 at IoU 0.5403 — is **decisively refuted**. Per-scene scaling
  into [0, 1] matched on all 16 channels in sign and magnitude. Also: DEM ranks 5th of 16 in first-conv
  weight energy, so it is genuinely used, confirming that zeroing it was wrong.
- **All 18 layers** (`flood_bn_fingerprint_all_layers.py`). First-layer agreement proved necessary but
  not sufficient: per-scene min-max scaled by a fitted 1.2078 matched layer one well and then collapsed
  to IoU 0.41, because a global input scale propagates and mismatches every later layer differently.
  Scoring against all 18 BatchNorms over a percentile grid selects **per-scene percentile clipping at
  2/98, scaled to [0, 1]** (median |log2(std ratio)| 0.119 and median mean offset 0.120 across the
  stack; p=0 gives 0.444, p=5 gives 0.199).

Selection used the **TRAIN** split — the split the running statistics were estimated on — and no
labels, so there is nothing to overfit and no test leakage even in principle.

### 2. A bug in the Q-041 §5 search, which is why it failed

**6 of the 90 official test scenes carry NaN in the Sentinel-1 bands, one of them entirely NaN**
(524,288 NaN pixels = both S1 bands). The Q-041 §5 sweep did not sanitise them. For any *per-scene*
normalisation, `np.percentile`/`np.min` over a channel containing a single NaN returns NaN, which
propagates to the whole channel and then the whole scene. So several of the schemes in that sweep were
scored on poisoned inputs, and `raw` — which has no division and so only spread NaN locally through the
convolutions — was flattered by comparison.

Concretely: per-scene min-max scored 0.4528 in Q-041 §5 and scores **0.5206** under the same threshold
once percentiles are nan-aware. Q-041 §5's conclusion "no scheme reproduced 0.6292" was reached with a
partly broken harness. That is the honest reason the recovery took two attempts, and it is recorded
rather than quietly fixed.

### 3. Verification — the recovered preprocessing reproduces the delivered scores

Measured once on the official 90-scene Sen1Floods11 test split, with the preprocessing chosen
label-free beforehand:

| | recovered, 90 official scenes | delivered, his 67-scene subset |
|---|---|---|
| global flood IoU, argmax | **0.6244** | 0.6292 |
| F1, argmax | **0.7684** | 0.7724 |
| pixel accuracy, argmax | 0.9472 | 0.9557 |
| precision, argmax → 0.30 | 0.8505 → 0.7937 (**−0.057**) | 0.7873 → 0.7220 (**−0.065**) |
| recall, argmax → 0.30 | 0.7014 → 0.7446 (**+0.043**) | 0.7580 → 0.8164 (**+0.058**) |
| global IoU, 0.30 | 0.6238 | 0.6211 |

IoU agrees to 0.005 and F1 to 0.004, on a **different and larger** scene set. More telling than the
point values: the **threshold response now matches in direction and magnitude**. Under every scheme in
Q-041 §5 argmax and 0.30 coincided, which was the evidence that the calibration was wrong; the delivery
reports IoU roughly flat between the two while precision falls ~0.065 and recall rises ~0.058, and the
recovered preprocessing reproduces exactly that shape. That is a reproduction.

Artefacts: `results/evaluations/flood_preproc_recovery_20260920/bn_fingerprint.json`,
`bn_fingerprint_all_layers.json`, `bn_recovered_test_scores.json`.

### 4. What was built, and why serving is still gated off by default

`normalise_flood_input` in `backend/app/ml/adapters/flood_unet.py` implements the recovered
normalisation (nan-aware percentiles, non-finite pixels replaced after scaling).
`FloodSegmenterAdapter` gained a gate: `configs/models.yaml`'s new `preprocessing` key is `null` by
default and the adapter keeps refusing exactly as before; set to `"bn_recovered_p2p98"` it serves, and
every response then carries `preprocessing_provenance: "recovered_not_supplied"`, the measured
recovered-versus-delivered numbers, and a warning, with the caveat stated in the answer text itself.
Only that exact string opens the gate — a unit test asserts that `"true"`, `"p2p98"` and the uppercase
form all keep it shut.

**Why default off.** This is an *inference about what training did*, not a statement from the author.
It is very likely right — a label-free method picking a preprocessing that then reproduces two
independent statistics and a threshold response is strong evidence — but "very likely right" is a
different claim from "confirmed", and flipping a model from *refuses* to *serves* changes what the
system asserts at a demo. That is the user's call, not a side effect of a documentation commit.

The delivered 0.30 threshold is offered but not imposed: under the recovered preprocessing it trades
precision for recall at essentially unchanged IoU (0.6238 against 0.6244), so argmax is the default.

### 5. Blast radius

None by default: the gate ships closed, `predict()` refuses as before, and the suite went 430 → **434
passed** with the same 3 pre-existing GDAL failures. If the gate is opened, the risk is that the
recovered preprocessing is close but not identical to training, in which case served masks would be
slightly worse than the delivered scores suggest — which is why the provenance travels with every
response rather than living only in a document.

### 6. What this means for the three "blocked on Ayushman" items

- **Flood normalisation** — no longer blocking. Recovered and reproduced. His confirmation would
  upgrade this from "recovered" to "confirmed", and remains worth asking for.
- **Which burn-scar metric file is the 0.40 run** — was never blocking: Q-042 §3 settles it from the
  byte-identical ROC-AUC.
- **`terratorch` versions** — not blocking; an isolated venv against current releases can be tried.
- **Why burn-scar training was from scratch** — genuinely needs him. It is a rationale, not a fact, and
  no amount of inspection recovers it.

### 7. Defence — answering a challenging reviewer

*"You recovered a preprocessing the author never gave you. Why is that not just tuning until the number
looked right?"* Because the selection never saw a label or a test scene. The preprocessing was chosen by
matching 18 BatchNorm layers' stored statistics on the training split, then scored once on test. If the
choice had been tuned to the score, the threshold response would not also have come out right — that is
a second, independent statistic we did not fit.

*"Then why is it not switched on?"* Because reproducing a number is evidence, not confirmation. The
author can still say we guessed wrong about a detail that happens not to matter much on this split. Until
he does, the capability ships off, and when it is on, every response says the preprocessing was
recovered rather than supplied.

*"Q-041 §5 said this was impossible. Which of you is wrong?"* Q-041 §5 is wrong, for two reasons now
recorded: it searched with labels instead of the model's own statistics, and its harness silently
poisoned every per-scene candidate on the six NaN-bearing scenes.

---

## Q-045 · The terratorch objection was wrong, and the burn-scar checkpoint's BatchNorm statistics were never populated

**Recorded** 2026-09-21, atop `prototype` `7d209db`. **Supersedes Q-041 §3 and §6's rationale** for not
installing `terratorch`, annotated in place. Reproducer: `scripts/verify_burnscars_terratorch.py`, run
from an isolated venv at `~/.venvs/terratorch-probe`.

### 1. The dependency objection was based on misreading a build string

Q-041 §3 justified not installing `terratorch` on the grounds that it "pins tightly and a plain install
risks downgrading torch/torchvision under the eight working adapters". **That was wrong.**

`torch 2.14.0+cu130` is **PyPI's own default build string** for torch 2.14.0, not a custom CUDA-13 pin.
Evidence: `.venv/lib/python3.11/site-packages/torch-2.14.0.dist-info/` has **no `direct_url.json`** (so
it was installed from an index, not a pinned wheel URL) and its `WHEEL` tag is the plain
`cp311-cp311-manylinux_2_28_x86_64`. A probe venv built purely from PyPI reports the identical
`2.14.0+cu130`.

A resolve-only `pip install terratorch --dry-run` on Python 3.11 succeeds and would pull:

| package | resolved | main `.venv` today |
|---|---|---|
| torch | **2.14.0** | 2.14.0 — identical |
| torchvision | **0.29.0** | 0.29.0 — identical |
| timm | 1.0.29 | 1.0.29 — identical |
| segmentation_models_pytorch | 0.5.0 | 0.5.0 — identical |
| numpy | 2.4.6 | 2.4.6 — identical |
| lightning / pytorch-lightning | 2.6.6 | absent (the ckpt was written by PL **2.6.6** — exact match) |
| terratorch | 1.2.11 | absent |
| torchgeo / einops / jsonargparse | 0.8.1 / 0.8.2 / 4.52.0 | absent |

terratorch declares only `torch>2.0`, unpinned `torchvision`, `numpy>=2.2`, `timm>=1.0.15`,
`smp>=0.5.0`, `lightning>=2.6.0`. **Nothing it declares can force a torch change.** The stated reason
for the decision was therefore false, and it had been propagated into `memory.md`, both handoff docs,
`docs/models/burnscars.md` and the `dce3ac3` commit message. All corrected.

A genuine constraint did emerge: **Python 3.11 caps us at terratorch 1.2.11**, because 1.2.12+ require
`torchgeo>=0.9`, which requires Python >=3.12. Both venvs here are 3.11.16, and the delivery README says
training used 3.12. Which terratorch version Ayushman trained with is **NOT RECORDED** — the checkpoint
stores only `pytorch-lightning_version: 2.6.6` and `hyper_parameters._class_path`.

### 2. The checkpoint is architecturally exactly what the config declares

Built from the delivered `docs/models/burnscars/model_config.yaml` through
`terratorch.tasks.SemanticSegmentationTask` / `EncoderDecoderFactory`, the checkpoint loads
**`strict=True` with zero missing keys, zero unexpected keys and zero shape mismatches** across all 355
tensors. The parameter count reconciles exactly: 324,204,674 parameters + 206,601 buffers =
**324,411,275**, matching the census in Q-041 §6 (which counted params+buffers). A CPU forward pass on
one synthetic 6-band 224x224 tile returns logits of shape `(1, 2, 224, 224)`.

Per the ChangeFormer scar (`network.py:14-16` — 373 names matched, `strict=True` passed, IoU 0.019 vs
0.726 because `num_heads` differed) **a clean strict load is not evidence the metrics are right**, and a
ViT's `num_heads` changes no tensor shape so `strict=True` provably cannot detect it. The mitigating
difference here is that the encoder is not a reimplementation: it is terratorch's own registered
`prithvi_eo_v2_300` (`num_heads=16`, the standard ViT-L value), from the library named in the
checkpoint's own `_class_path`. Residual risk: a silent config change between the unknown training
version and 1.2.11.

### 3. New defect the delivery does not record: all 9 BatchNorm layers are at initialisation

Read straight out of the raw checkpoint, independently confirmed here:

```
BatchNorm layers found: 9
num_batches_tracked distinct values: [0]
layers with running_mean == 0 AND running_var == 1: 9 of 9
affine weight of model.decoder.decoder.blocks.0.conv1.1:
    min 0.9878  max 0.9974  mean 0.9940   -> trained, not at the 1.0 init
```

All 9 (the 8 in `UNetDecoder` plus `model.neck.2.fpn1.1` in `LearnedInterpolateToPyramidal`) have
`running_mean` 0, `running_var` 1 and `num_batches_tracked` **0** — untouched from initialisation —
while their affine weights have clearly trained. So gradients flowed, but **no running statistics were
ever accumulated**.

Consequence: in `.eval()` mode every one of those BatchNorms degenerates to
`y = weight * x / sqrt(1 + eps) + bias`, a pure affine map that does not normalise anything. The
decoder effectively has no normalisation at inference.

**Mechanism: NOT ESTABLISHED.** The observed state — buffers present but never updated, affine weights
trained — is exactly what you get if the BatchNorms were held in **eval mode throughout training**. If
that is what happened, our eval-mode inference is *faithful* to training and the delivered metrics are
reproducible in principle. The alternative, that they were in train mode using batch statistics, cannot
be ruled out from the checkpoint alone; at batch size 1 (`global_step` 3888 = 9 x 432) train-mode BN
degenerates to instance normalisation over a single tile, which would make eval-mode inference
**not** equivalent and the reported numbers batch-size dependent. One question to Ayushman settles it.

This is also a plausible contributor to the per-scene collapse already documented (Q-042 §1: 10 of 264
scenes at burn IoU 0.0, 6 predicting no burn pixels at all) — a decoder with no working normalisation is
exactly the kind of thing that fails catastrophically on out-of-distribution scenes rather than
gracefully.

**Contrast, and why this matters beyond burn scars.** The flood model's BatchNorm statistics *are*
populated (`encoder1.block.1.num_batches_tracked = 2773`), which is what made Q-044's label-free
preprocessing recovery possible. The burn-scar checkpoint carries **no such information**, so the same
trick cannot be used on it: its preprocessing cannot be recovered from its own weights. Fortunately it
does not need to be — the delivered `model_config.yaml` states the per-band means and stds explicitly.

### 4. Why terratorch still is not being adopted — the reasons have changed

The dependency objection is withdrawn. The remaining ones:

1. **The metric cannot be reproduced here regardless.** The HLS Burn Scars imagery is absent from this
   machine — `find datasets/ -iname '*burn*' -o -iname '*hls*'` returns 0 hits and
   `datasets/manifests/training_sources.yaml` has no entry. So installing terratorch could establish
   only that the checkpoint instantiates, which §2 has now established *without* adopting it.
2. **Cost and untested interactions.** ~100 packages absent today (lightning, torchgeo, kornia,
   diffusers, geopandas, xarray, h5py, hydra-core, …), ~3.4 GB of wheels / 6.8 GB installed, and it
   would upgrade `huggingface_hub 1.30.0 -> 1.32.0` and `matplotlib 3.11.1 -> 3.11.2`. This venv runs
   `transformers 5.16.1` and terratorch pulls `diffusers 0.40.0`; that interaction is **NOT TESTED**.
3. **§3 is the real blocker.** Paying ~7 GB to register a model whose decoder BatchNorms never
   normalise, whose headline metric is unreproducible here, and whose eval/train equivalence is
   unestablished, is the wrong order of operations.

Cheaper path if it is wanted later: vendor the `PrithviViT` + `UNetDecoder` pair against the smp 0.5.0
already installed, whose `UnetDecoder` parameter names already match. The ChangeFormer lesson applies —
any such port must be verified numerically, not by a clean load.

### 5. Blast radius

Nothing in the serving path. No repo code changed; `scripts/verify_burnscars_terratorch.py` was added as
the reproducer. The main `.venv` is untouched and verified still on torch 2.14.0+cu130 / torchvision
0.29.0+cu130 with an unchanged 155-package `pip freeze`; all installation happened in
`~/.venvs/terratorch-probe` (6.8 GB, deletable). The correction in §1 is documentary but matters: a
false technical reason was recorded as the basis of a decision, and anyone re-deciding later would have
inherited it.

### 6. Defence

*"You refused to install a library for a reason that was wrong. What else is wrong?"* The reason was
checkable in one command and nobody checked it, including me — that is the lesson, and it is why the
correction names every document that carried it. The decision it supported happens to survive on other
grounds, which is luck, not diligence.

*"Is the burn-scar model usable?"* Architecturally it is exactly what its config says, and it runs. But
its decoder BatchNorms never accumulated statistics, so at inference they do not normalise; whether that
matches how it was trained is unestablished, its headline IoU cannot be reproduced without imagery we do
not have, and 10 of its 264 test scenes are complete misses. It should not be presented as a working
capability.

---

## Q-046 · Verifier crops fabricated black pixels at image edges; fixing it moved two Q-009 numbers the wrong way

**Recorded** 2026-09-21, atop `prototype` `e9b7f70`. Closes the owner's post-demo item #3 ("Verifier
crop at image edges"). Evidence:
`results/evaluations/{verifier_edge_crops,disputed_edge_boxes_05945,grounding_verdicts_crop_geometry}_20260921.json`;
reproducers `scripts/eval_verifier_edge_crops.py`, `eval_disputed_edge_boxes.py`,
`eval_grounding_verdicts_vrsbench.py`.

### 1. Mechanism

`DetectionVerifier.crop` built a square window of `2x` the box's longer side (floor 96 px) around the
box centre and passed it straight to `PIL.Image.crop`, which **fills out-of-frame coordinates with
zeros**. Verified rather than assumed: cropping `(-20,-20,20,20)` from a solid `(200,100,50)` 64x64
image returns a 40x40 image that is **exactly 75.0% pure black**. So RemoteCLIP was being handed a
black L-shape and scoring it as image content.

This was not an edge case. On the 973-crop probe (all frames 512x512), **711 crops (73.1%) left the
frame**, and among those the fabricated area averaged **45.5%** (median 46.5%, max 93.2%); 306 crops
were more than half fabricated. Two causes: 308 where the doubled side alone exceeded 512 px, and 403
where the side fitted but the window sat off-frame.

`crop()` now returns the legacy box untouched when it is already inside the frame — so no non-edge
measurement can move — and otherwise caps the side at `min(width, height)` and translates the window
back inside. `crop_mode` is selectable (`inset` default, `clamp`, `pad`) so the old behaviour is one
argument away.

### 2. Verified independently here, and one overstated claim corrected

The implementation is correct, but its comment claimed "the box always stays inside the window". That
is false in one case, and the claim was tightened. Property test over 576 synthetic boxes across
512x512, 400x300 and 97x640 frames: `pad` fabricates black in **466** crops, `inset` in **0**. `inset`
failed to contain the whole box in **48** cases — and all 48 are boxes longer than the frame's short
side, where **no** square in-frame window can contain the box. **Real defects: 0.** The comment now
states the containment guarantee with its actual precondition.

### 3. The two DISPUTED answers on `05945_0000.png`

| geometry | query | decision | verdict | crop box | out of frame |
|---|---|---|---|---|---|
| pad (before) | segment the largest building | `accepted_disputed` | contradicted | `[102,-241,648,304]` | yes |
| pad (before) | find the white car at the bottom left | `accepted_disputed` | contradicted | `[-53,278,82,413]` | yes |
| **inset (after)** | segment the largest building | `accepted_unconfirmed` | unverified | `[0,0,512,512]` | no |
| **inset (after)** | find the white car at the bottom left | `accepted_unconfirmed` | unverified | `[0,279,135,414]` | no |

The before-state reproduces Q-009 §3 **exactly** — top matches "ground track field" and "roundabout" —
so the baseline is the one Q-009 describes. Boxes are unchanged (these are attribute queries, label
only). **Neither becomes `verified`:** the false *contradiction* is gone and the label drops DISPUTED →
UNCONFIRMED, but the verifier still cannot positively confirm either. `clamp` was measured and rejected
because it repairs only one of the two and separates true from wrong less well (AUC 0.9725 vs 0.9755).

### 4. Two Q-009 numbers moved the wrong way — stated plainly

**In favour:** contrastive AUC 0.9626 → **0.9755**; true-label accept 0.820 → **0.870**; false
contradiction on true labels 0.1336 → **0.0976**; across 300 present VRSBench queries DISPUTED answers
fall **75 → 53** (22 of 75, 29%, stop being falsely disputed) while R@0.5 rises 0.330 → 0.337 and mIoU
0.3086 → 0.3176.

**Against:**
- **`absent_returned_a_box` 0.2833 → 0.3400 (+5.7 pts)** — the number Q-009 headlines as 28.0%. The
  extra boxes are all `accepted_unconfirmed` (57 → 75); `accepted_verified` on absent queries is flat
  (28 → 27), so **nothing newly claims to have found an absent object**, but more absent queries return
  a box at all.
- **On vehicles — the demo's main class** — `vehicle_crop_as_vehicle` verified falls 0.555 → 0.465 and
  `nonvehicle_as_vehicle` rises 0.164 → 0.273.

Mechanism of the regression: black padding was destroying the surrounding scene context, and context
labels (road, parking lot, grass field, trees) are the verifier's main competitors. Removing the
padding restores that context, which makes the verifier less pessimistic — good for true positives, bad
for rejecting absent objects. **The old 28.0% was partly bought with fabricated pixels.**

Shipped anyway. Handing an encoder zero-fill and scoring it as image content is not defensible under
questioning at any accuracy, and the absent-object protection Q-009 actually relies on is the *label*,
which still holds. The lever that would restore 28.0% is `top_k` (3 → 2), not the padding —
**NOT MEASURED**, and `configs/app.yaml` was deliberately left alone because changing it reopens
Q-009's measured rule. Reversible in one argument: `DetectionVerifier(crop_mode="pad")`.

### 5. Q-009's recorded numbers are not exactly reproducible by anyone, independent of this change

The scripts behind the Q-009 evaluation files and the per-query cache they replayed were **never
committed** — confirmed against full git history, no such file has ever existed. There was no cached
harness to run, so it was rebuilt from the same source data under a stated deterministic rule.

Evidence the reconstruction is the right sample: it yields **n = 973** exactly (first 40 records per
`obj_cls` over 26 classes, two classes short of 40) and the 200-crop vehicle rows reproduce Q-009
**digit for digit** (`vehicle_crop_as_vehicle` 0.555, `vehicle_crop_as_airplane` 0.035). The remaining
973-crop rows sit ~1.3 points off the recorded ones, and the 300/300 deliberation sample is
demonstrably a different draw (272/28 attribute/plain versus Q-009's 206/94), which is why present
recall sits lower in absolute terms. Before/after comparisons here are like-for-like because every
geometry was measured on one sample in one process; **absolute comparisons against 2026-09-14 are
not.** Wrong-label pairing is seeded (`SEED=20260914`) because the original pairing was not recorded.

This is a process failure worth fixing beyond this entry: a measured claim whose harness is not
committed cannot be defended, only asserted. The three new scripts are committed for exactly that
reason.

### 6. Blast radius

The 262 probe crops already inside the frame are **bit-identical across all three geometries**, so no
non-edge number can move; all movement is on the 711 edge crops. `backend/app/video/flagger.py:211`
calls `verifier.verify()` and therefore inherits the change, so **Q-008's video event counts (3 events
→ 0 on road footage, one dropped real white car) are NOT MEASURED** under the new geometry — the most
likely place a demo number has shifted without being looked at. `crop_box` is otherwise only echoed
into evidence metadata, and `remoteclip.py` is untouched (it only runs open_clip's Resize+CenterCrop).

### 7. Verification

20 new unit tests in `tests/unit/test_verifier_edge_crops.py`: every edge, every corner, a box larger
than the image, a 1-px box, a 1-px corner box, a box entirely outside on each side, a non-square frame,
and an 11x11 x 3-size position sweep. Each builds an image with **no pure-black pixel** (`randint(1,256)`)
and asserts the crop is `array_equal` to the source region it names — so "no fabricated pixels" is proved
by identity with the source, not by a colour heuristic. One test pins the old `pad` defect so the
before/after comparison cannot silently rot, and one `models`-marked test asserts pad → contradicted
and inset → not contradicted on the real image. Suite: **549 passed, 3 failed** (the pre-existing GDAL
failures), up from 530 by exactly the 19 new non-models tests.

### 8. Defence

*"You made your headline absent-object number worse."* Yes, from 28.0% to 34.0%, and it is in the
record. The 28.0% was measured while 73% of verification crops contained fabricated black pixels
averaging 45% of their area; suppressing the context labels the verifier competes against is what
bought part of that number. A figure obtained through a bug is not a figure we can defend, and the
protection the pipeline actually relies on — refusing to label an absent object `verified` — is
unchanged at 28 versus 27 queries.

*"Then why not keep the old behaviour and the old number?"* Because it would mean knowingly feeding a
vision encoder zero-fill and scoring it as if it were imagery, having measured that this happens on
73% of crops. The fix is also what removes the false contradiction from both DISPUTED demo answers,
which is the defect we set out to fix.
