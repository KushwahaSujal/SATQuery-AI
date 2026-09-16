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
