# Task assignments — Jyotimoy · Sujal · Somdutta

Cut on 2026-09-11 against the measured state in [`pre-demo.md`](pre-demo.md).
Read `pre-demo.md` §0 first — it is the only honest baseline. Numbers in the other docs are older.

**Working agreement**

- Branch off `refactor/s0-remove-dead-layers`, not `main`. `main` is 15 commits stale.
- One branch per track: `feat/<name>-<topic>`. Do not push to `main`.
- `rules.md` §6: any change spanning >3 files, touching routing/capability logic, or altering a
  model contract gets recorded in `qna.md`. It is a transcript, not a gate — it never blocks your
  merge. None of the tasks below are meant to reach that size; if yours starts to, talk to Ushnik.
- Baseline to beat, every time, before you open a PR: `pytest -q` → **132 passed, 0 failed**.
- Do not touch: `ml/adapters/changeformer*`, `checkpoints/optical_sar/*`, the agent DAG routing, or
  `frontend/src/components/**` (D-111 — frontend components belong to Sandipan).

---

## Track A · Jyotimoy — the API contract, and what the judge actually sees

The system is more correct than it looks. Five separate field-name mismatches mean the UI shows
zeros, empty strings and a false error badge while the backend is returning real, correct data.
This track is the highest value-per-hour work left in the repo, and it is fully specified — every
item below has the exact file, line and real payload path already measured.

**Prefer fixing on the backend side**: add the field the frontend already reads. That keeps D-111
intact and is usually a few lines.

### A1 · False DEGRADED badge — 1 hour · `pre-demo.md` §3a
`frontend/src/components/layout/AppHeader.tsx:42-45` reads `api`, `models_ready`, `models_total`.
`/api/health` returns `status: "ok"` and `models_available` (a dict). So the first thing anyone sees
is a red DEGRADED pill and a fabricated model count, on a healthy backend.
**Do:** add `api`, `models_ready`, `models_total` to `/api/health`.
**Done when:** the header reads OPERATIONAL with a true count, and a test asserts the payload keys.

### A2 · Statistics panel reads a key that does not exist — `pre-demo.md` §3d-i
`frontend/src/app/analysis/[jobId]/page.tsx:170-171` reads `data.metrics?.regions` and
`data.metrics?.changed_pixels`. **There is no `metrics` key in the response.** Real values:

| UI reads | actual path | actual value |
|---|---|---|
| `metrics.regions` | `evidence.spatial.statistics.region_count` | 171 |
| `metrics.changed_pixels` | `evidence.spatial.statistics.changed_pixels` | 15,542 |
| *(nothing)* | `evidence.spatial.statistics.change_ratio` | 0.237 |

Note `regions` vs `region_count` — a second mismatch nested inside the first.
**Done when:** the panel shows 171 / 15,542 / 23.7% on the `real_pair` sample.

### A3 · The backend's own quality warning never reaches the screen — `pre-demo.md` §3d-ii
The API returns `quality_status: "REVIEW_REQUIRED"`, a `quality_warning` string and
`diagnostic_flags: ["EXCESSIVE_CHANGE"]`. The UI shows a clean answer at 56.9% confidence instead.
**This is the honesty item.** We are hiding our own reliability flag from a judge, which cuts
against the `prd.md` §5 zero-fabrication requirement. Surface it.
**Done when:** `REVIEW_REQUIRED` renders visibly wherever the answer renders.

### A4 · Query echoes as empty — `pre-demo.md` §3d-iii
The analysis page shows `QUERY ""`. `/api/results/{id}` has no `query` key at all. Add it.

### A5 · Evidence panel says "No evidence registered" — `pre-demo.md` §3d-iv
It reads only `evidence.spatial.boxes`, `[]` for change detection — while `has_mask: true` and a
real `mask_path`, `geojson_path` and `overlay_path` are all present. Read those too.

**A1–A5 together: about one day, and they change what a judge sees more than anything else left.**

### A6 · Then: the response composer — 2 days · `pre-demo.md` §3 item 5
Responses are raw JSON today. By the time you finish A1–A5 you will know the payload shape better
than anyone. Write the composer that narrates what ran, what it found, and with what confidence.
Talk to Ushnik before starting this one — it is the first task in this track with design latitude.

---

## Track B · Sujal — security hardening, and CI that proves the suite is green

Two jobs. The second one is urgent because of the first week of five people pushing at once.

### B1 · CI — do this first, half a day
There is **no `.github/workflows/`**. The suite is green on Ushnik's machine and nowhere else, and
we are about to have five people committing concurrently. That is the single highest-leverage thing
missing from the repo right now.
**Do:** GitHub Actions running `pytest -q -m "not models"` on every PR, plus `tsc --noEmit` and
`next build` for the frontend. Model-marked tests need weights that are not in git — exclude them
and say so in the workflow.
**Done when:** a PR shows a green check, and a deliberately broken test shows a red one.

### B2 · Security compliance — 1–2 days · `pre-demo.md` §3 item 7
Largely independent of everyone else's work. Touches no model code.

- **Upload size limit is not enforced.** `settings.storage.max_upload_size_mb` is defined at
  `backend/app/config.py:34` and env-overridable at `:230`, but `grep` finds **no read of it
  anywhere in the request path**. `backend/app/api/v1/endpoints/uploads.py:119-124` validates the
  extension and nothing else. Any size upload is currently accepted. Fix it and test it.
- **CORS** — `backend/app/main.py:44` uses `settings.app.cors_origins`. Verify it is not `["*"]`
  in any config path, and that the deployed value is explicit.
- **`.env` handling** — `.env` is correctly gitignored. Confirm no secret is read into a log line,
  an error response, or the `/api/health` payload.
- **SQL injection surface** — the repositories use SQLAlchemy; confirm no raw string-built SQL.
  If there is none, say so in writing. A verified negative is a real result.
- **No secrets in logs** — grep the logging calls for anything carrying a credential or a full path
  outside the workspace.

**Done when:** each of the five has either a fix plus a test, or a written verified-negative with
the command you ran.

### B3 · Delete `scripts/setup_checkpoints.py` — 15 minutes
Both teams agreed it goes (`pre-demo.md` §1.4). It reports checkpoints as ready when the files are
placeholders — the exact false positive we are trying to remove. Check nothing imports it first.

---

## Track C · Somdutta — evidence and robustness

The suite went green for the first time this week. `pre-demo.md` §3h is an honest audit of whether
that green is real, and the answer is *partly*. Your track is to find out. This is verification
work, not architecture — but it feeds the paper and decides what we are allowed to claim on stage.

### C1 · Are the video thresholds overfitted? — 1–2 days · `pre-demo.md` §3h
Two thresholds — `min_detector_score: 0.35` and `max_box_area_ratio: 0.90` (`backend/app/config.py`)
— were calibrated on **one clip, in one lighting condition**: `real_aerial_footage.mp4`. The logic
fixes around them are principled and general; these two numbers are not.

**Do:** source 2–3 more real aerial clips where you know the contents, run the video pipeline on
each, and report per-clip: detections found, false positives, missed objects, and whether the
existing thresholds hold. Do not tune anything yet — measure first, then bring Ushnik the numbers.
**Done when:** there is a table in `pre-demo.md` §3h with a row per clip.

### C2 · `derived_patrol.mp4` finds no vehicles — `pre-demo.md` §2.1f
`"find all vehicles"` → 0 flags, `NO_RELEVANT_EVENTS_FOUND`. The same clip returns a confident flag
for `"purple flying saucer"` at 0.563. The detector answers a nonsense prompt but not the real one.
This is a live, reproducible instance of exactly what C1 is looking for — start here, it is the
cheapest way into the pipeline.

### C3 · Two grounding evaluators, one silently reports 0.0000 — 1 hour · `pre-demo.md` §2.1d
`scripts/evaluate_grounding_vrsbench.py` has a field-mapping bug and reports a perfect zero;
`scripts/evaluate_vrsbench_real.py` is the one that works (mIoU 0.3532, R@0.5 0.398 over 299
official records). Leaving both is a trap for whoever runs the obvious-looking one next.
**Do:** fix the field mapping, or delete the file. Either is acceptable — decide and say why.

---

## What is NOT in these tracks, and why

| Item | Owner | Why not delegated |
|---|---|---|
| §1.1 optical–SAR rule-based fusion | Ushnik | Mandatory req #5, currently random weights |
| §1.3 ChangeFormer vendor + rewire | Ushnik | Blocked on Ayushman's validation set |
| §1.2 wire BigEarthNet, lead with CDVQA | Ushnik / Ayushman | Headline adaptation claim |
| §1.4 model-registry verification | Ushnik | Touches the registry contract |
| §2.1e SAM 2.1 bidirectional propagation | Ushnik | Model-level; the temporal claim depends on it |
| Frontend design pass (§3 item 1) | Sandipan | D-111 — his components |
| §3 items 3/4 trace + audit report | open | Pick up after Track A lands the payload work |

---

## First 48 hours

1. Everyone: clone, checkout `refactor/s0-remove-dead-layers`, get `pytest -q` to 132 passed
   locally. If it does not go green on your machine, that is the first bug and it outranks your
   track.
2. Sujal: B1 (CI) before anything else — it protects the other four.
3. Jyotimoy: A1, then A2. Both are measured and unambiguous.
4. Somdutta: C2, then C3. Both are small and teach you the pipeline.
5. Report back with numbers, not adjectives. Every claim in `pre-demo.md` has a command behind it;
   keep that standard.
