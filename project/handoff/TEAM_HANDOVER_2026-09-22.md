# Team handover — 2026-09-22

Everything you need to run, deploy, and continue SatQuery AI. Written after the app was deployed
and driven end to end against the cloud GPU.

Branch: `prototype` at `b0cc3ab`, pushed. `main` is **not** current — see §6.

---

## 1. What is live right now

| | URL | Runs on |
|---|---|---|
| Frontend | https://satquery-ai-smoky.vercel.app | Vercel (free tier) |
| Backend | https://ushnik1p2h3d--satquery-ai-api.modal.run | Modal, T4 GPU |
| Database | Supabase pooler | (unchanged) |

**Nobody's laptop needs to be on.** Open the URL from any machine. The GPU container sleeps after
5 minutes idle and wakes on the next request (~60 s cold start).

Verified working on the deployed stack on 2026-09-22:

| Capability | Result |
|---|---|
| Image masking / grounding | COMPLETED, 82%, trained building segmenter, 7 regions / 1,437 px |
| Bi-temporal change detection | COMPLETED, ChangeFormer + CDVQA, 11.35% building change, 181 regions |
| Video tracking | COMPLETED in 137 s, 2 events, grounding_dino + sam2 + remoteclip |
| Optical + SAR fusion | **refuses** with `NOT_CONFIGURED` — by design, see §7 |

Models available in the cloud: **18 of 20**. Missing: `crater_detector` (ultralytics is AGPL and
pulls `opencv-python`, which clashes with the backend's `opencv-python-headless`) and
`general_rs_vlm` (BLIP, intentionally replaced by Qwen3-VL `scene_vlm`). Do not demo crater
detection.

Tests: `pytest -m "not models" -q` → **561 passed, 3 failed** (2026-09-22). The 3 are pre-existing
GDAL failures in `tests/unit/test_geotiff_georeferencing.py`, unrelated to anything recent.

---

## 2. The hosting model — read this before touching deployment

The two halves are deployed separately and by different tools. Confusing them is the main way to
waste an afternoon.

```
Browser ──HTTPS──> Vercel (Next.js, frontend-v2/)   static + SSR, no GPU
   │
   └────HTTPS + X-API-Key──> Modal (FastAPI, backend/)   T4 GPU, model weights
                                  ├── volume satquery-models   (weights, HF cache)
                                  ├── volume satquery-results  (masks, overlays, zips)
                                  └── Supabase Postgres        (jobs, video flags)
```

**The backend cannot go on Vercel.** It needs CUDA, PyTorch and ~6 GB of weights, and runs jobs for
tens of seconds. Vercel is for `frontend-v2/` only, forever.

### How the frontend finds the backend

Two build-time variables, set in the Vercel dashboard (Production **and** Preview):

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | the Modal URL |
| `NEXT_PUBLIC_API_KEY` | one of the keys in `SATQUERY_API_KEYS` |

`NEXT_PUBLIC_*` values are **compiled into the bundle**. Changing either needs a redeploy, not a
restart. There is no runtime connection panel in `frontend-v2` — that was the old `frontend/`.

### How auth works

`backend/app/api/auth.py` rejects everything except `/api/health`, `/docs`, `/redoc` and
`/openapi.json` once `SATQUERY_API_KEYS` is set. The client sends `X-API-Key`; `<img>`, `<video>`
and download links cannot set headers, so those URLs carry `?key=` instead. Both helpers live in
`frontend-v2/src/lib/endpoints.ts` (`authHeaders()`, `withKey()`) — **use them, do not write a
fourth copy.** Three separate call sites each forgot the key and returned 401 in production while
working locally (Q-058).

> **Why local testing cannot catch auth bugs:** no key is configured locally, so `authHeaders()`
> returns `{}` and every path behaves identically. Anything touching backend calls must be tested
> against the deployed backend or it is unverified.

### CORS

`backend/app/config.py` defaults to `localhost:3000` only. Two overrides, both set in
`deploy/.env.modal`:

```
SATQUERY_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SATQUERY_CORS_ORIGIN_REGEX=https://satquery[a-z0-9-]*\.vercel\.app
```

The regex exists because Vercel names every deployment `satquery-<hash>-<scope>.vercel.app` — it
truncates the project name, so anchoring on `satquery-ai` blocks every preview build. It is scoped
rather than `.*\.vercel\.app` because `allow_credentials=True` is on.

**Symptom to recognise:** the site shows "AI Ready" but nothing works. `/api/health` is an open
path, so the pill goes green while every real request fails on CORS or 401.

---

## 3. Running it locally

```bash
# backend (repo root, venv already has everything)
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# frontend — note: frontend-v2, NOT frontend/
cd frontend-v2 && npm run dev
```

`frontend/` is the **old** UI, last touched 2026-09-16. All current work is in `frontend-v2/`. If
the UI looks wrong, check which directory you started. Port 3000 matters — CORS allows only that.

No local Postgres needed; `DATABASE_URL` points at Supabase.

---

## 4. Deploying

### Backend (Modal)

```bash
.venv/bin/modal deploy deploy/modal_app.py
```

Takes ~5 s when the image is cached. It ships `backend/`, `configs/` and `training/` from your
working tree — **uncommitted changes deploy too**, so check `git status` first.

Pushing new weights:

```bash
.venv/bin/modal volume put satquery-models checkpoints/<dir>/<file> checkpoints/<dir>/<file>
.venv/bin/modal deploy deploy/modal_app.py     # REQUIRED, see below
```

> **A running container holds a stale volume snapshot.** Uploading weights alone changes nothing
> until containers cycle. Redeploy after every `volume put` or you will debug a model that is
> already fixed (Q-057).

### Frontend (Vercel)

```bash
cd frontend-v2 && vercel deploy --prod
```

Deploys are **manual** — see §6 for why, and the two settings that must change before Git is
connected.

### Demo day

```bash
SATQUERY_MIN_CONTAINERS=1 .venv/bin/modal deploy deploy/modal_app.py   # keep GPU warm, costs credit
.venv/bin/modal deploy deploy/modal_app.py                             # scale back to zero after
```

Run one real query ~5 minutes before starting. Watch credit at https://modal.com/settings/usage.

---

## 5. Why the trained segmenters work in the cloud

Worth knowing because it will bite again. The segmenter adapters build their network through
`training.segmentation.train_seg`, so the Modal image must ship `training/` plus
`segmentation-models-pytorch`, `albumentations` and `rasterio`. Without them,
`binary_segmenter.trainer_importable()` returns False and **nine** models — including the buildings
segmenter the main demo uses — report unavailable in the cloud while working perfectly on your
laptop. Already fixed in `deploy/modal_app.py`; do not "tidy" those lines away.

Also: only the checkpoint files named in `configs/models.yaml` are on the volume (840 MB), not the
whole `checkpoints/` tree (4.6 GB). The directories hold `last.pt` and training artifacts nobody
serves. If you add a model, upload **its** file and redeploy.

---

## 6. TODO

### P0 — before or around the demo

| # | Item | Why | Owner |
|---|---|---|---|
| 1 | Correct `docs/models/OPTICAL_SAR_FUSION.md:14` — it says `IMPLEMENTED & VERIFIED` | The code hard-disables the model. A judge reading both sees a contradiction, and it undercuts the zero-fabrication claim (D-010) | |
| 2 | Decide: hide the "Optical + SAR Fusion" home card, or prepare the answer in §7 | A mentor can click it (`frontend-v2/src/app/page.tsx:59`, and sample query at `:375`) | |
| 3 | Rehearse the three working capabilities on the **deployed** URL, not localhost | Auth and CORS bugs only exist in production | |

### P1 — right after the demo

| # | Item | Notes |
|---|---|---|
| 4 | Reconcile `main` and `prototype` | They differ across **95 files**. `main` has 18 commits by Sandipan (`frontend-v2: initial build`, `rebuild all pages…`, DS v2.0 tokens) — a parallel rebuild of the same frontend. Needs Sandipan; do not merge unilaterally |
| 5 | Connect the repo to Vercel for auto-deploy | Blocked: `vercel git connect` fails because the Vercel account has **push but not admin** on `KushwahaSujal/SATQuery-AI`. Sujal must do it, or grant admin |
| 6 | **When connecting Git**, change two settings in the same sitting | (a) Root Directory `.` → `frontend-v2`, else Git builds clone the repo root where there is no `package.json`; (b) Production Branch defaults to `main` → set to `prototype`, else the first webhook build deploys a branch 92 commits behind and wipes the live site |
| 7 | Optical-SAR fusion | Full plan in [`docs/OPTICAL_SAR_FUSION_ENABLEMENT.md`](../../docs/OPTICAL_SAR_FUSION_ENABLEMENT.md). Recommended: deterministic heuristic (~2–4 days) before training (~2–4 weeks) |
| 8 | Reclaim orphaned result workspaces | **892 directories in local `results/`** (measured 2026-09-22) against 16 jobs in the database. Neither delete route can reach them — both derive their target set from the database, deliberately, so a stale directory is never guessed at. Needs a separate sweep that reports what it would delete before deleting. Note the cloud has its own `satquery-results` volume with a 7-day retention job; this is the local tree |

### P2 — backlog, tracked in `project/decisions.md`

| # | Item | Ref |
|---|---|---|
| 9 | RS-adaptation requirement — **verify current status** | D-101. Filed against BLIP; Qwen3-VL `scene_vlm` has since replaced it. Qwen3-VL is still a *generic* VLM, so the mandatory requirement may remain unmet. Confirm before claiming otherwise |
| 10 | `sar_analysis` and `multispectral_analysis` route to a trivial fallback DAG | D-104. Startup logs them under "Capabilities with no DAG branch … produce no real output" |
| 11 | Capability `required_tools` never verified against `TOOL_REGISTRY` | D-105. A capability can declare tools that do not exist and nothing complains at boot |
| 12 | BigEarthNet adapter is orphaned — registered, used by nothing | D-106 |
| 13 | Router accuracy 74.9%; declarative referring expressions misroute | D-116. Fix is known and not applied: extend `OBJECT_PATTERNS`, add `is located` / `is positioned` patterns |
| 14 | Capability health: **8 of 15** fully agent-executable | Printed at every backend start. Read the warnings; they are accurate |
| 15 | `frontend-v2/src/components/analysis/ResultsCanvas.tsx` | Dead code — imported nowhere. Builds `/api/v1/jobs/…/layers/…/visualization` (wrong path) and reads `NEXT_PUBLIC_API_URL` (wrong variable). Harmless today, a trap for whoever wires it up. Fix or delete |
| 16 | `export_layer` calls `get_visualization_image` directly | Its `db: AsyncSession = Depends(get_db)` receives the `Depends` object, not a session. Works only because that path never touches `db`. Should become a shared helper |
| 17 | `NEXT_PUBLIC_API_KEY` is readable by anyone who opens the site | Acceptable for a credit-capped demo backend. The AWS move needs a server-side proxy holding the key |
| 18 | Uncommitted work not ours: `backend/app/ml/adapters/sam2.py`, `scripts/measure_video_mask_coverage.py`, `tests/unit/test_video_mask_propagation.py` | Predate 2026-09-22. Whoever owns them should commit or discard |

---

## 7. Gaps you must be able to explain

Do not get caught by these. Saying them first is a strength; being caught is not.

**Optical-SAR fusion refuses.** The checkpoint is a freshly constructed network saved at random
initialisation, and the training script it was meant to come from does not exist in the repo
(D-102). Rather than emit 19 class probabilities that are noise, the model returns
`NOT_CONFIGURED`. Full detail and the fix plan: `docs/OPTICAL_SAR_FUSION_ENABLEMENT.md`.

**`/api/health` says the fusion model is available.** Availability only checks that weights load,
not that they mean anything, so it counts toward "18/20" while refusing every request. Do not cite
that pill as evidence a capability works.

**Change detection reports low confidence** (0.126 measured) even when the answer is correct and
detailed. Know which number appears on screen.

---

## 8. Where the records are

| File | What |
|---|---|
| `project/qna.md` | The transcript. Append-only, contemporaneous, never edited. Today's work is **Q-052 … Q-059** |
| `project/decisions.md` | D-numbered decisions, including the open blockers above |
| `project/memory.md` §0 | Live project state — read at session start, update at session end |
| `deploy/README.md` | Cloud GPU setup manual; **§9** covers Vercel + PWA |
| `docs/OPTICAL_SAR_FUSION_ENABLEMENT.md` | The fusion gap and how to close it |

`qna.md` entries cover mechanism, rationale, blast radius, verification and defence, with file
paths, line numbers and measured numbers. If you change something worth defending, add an entry —
do not edit an old one; supersede it and say so in both directions.

---

## 9. Time-wasters we already hit, so you do not have to

1. **Editing `frontend/` instead of `frontend-v2/`.** The old UI still runs and looks plausible.
2. **Testing auth locally.** Impossible — no key is configured, so every path passes. Use the
   deployed backend.
3. **Uploading weights without redeploying.** Running containers hold a stale volume snapshot.
4. **Assuming a checkpoint that loads is a checkpoint that works.** The fusion weights load cleanly
   with `strict=True` and are random.
5. **Trusting the model-count pill.** 18/20 counts models that will refuse.
6. **Reading `docs/models/*.md` as current.** At least one dossier claims a status the code
   contradicts (P0 item 1).
