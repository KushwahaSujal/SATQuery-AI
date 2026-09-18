# frontend-v2 — End-to-End Demo Run

This document covers how to verify frontend-v2 actually talks to the backend.
The frontend wiring (api.ts / endpoints.ts / types.ts) is **byte-identical** to
the connected `frontend/` v1 in the parent repo. The chat history I added on
top is also wired to `api.analyze()` + polling, not mock data.

---

## TL;DR — three commands

```bash
# 1. backend (in the parent repo root, with venv activated)
cd ../ && source .venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2. backend smoke (proves backend works) — run from frontend-v2/
node scripts/smoke.mjs

# 3. frontend
npm run dev    # http://localhost:3000
```

---

## Step-by-step verification

### Step 1 — Backend health

```bash
curl http://localhost:8000/api/health
```

Expected:

```json
{
  "status": "ok",
  "database_connected": true,
  "models_available": {"changeformer": true, "grounding_dino": true, ...},
  ...
}
```

If `"status":"ok"` and `models_available` is non-empty → backend is up.

### Step 2 — End-to-end smoke test (no UI needed)

`scripts/smoke.mjs` exercises the **exact chain** the frontend-v2 chat uses:

1. `GET /api/health`
2. `GET /api/models`
3. `POST /api/upload` (one PNG from `demo_resources/1_masking/`)
4. `POST /api/analyze` with `query="Describe this scene in detail"`
5. Polls `GET /api/jobs/{jobId}` every 2s until terminal
6. `GET /api/results/{jobId}` → checks `answer`, `confidence`, `models_used`
7. `GET /api/analysis/{jobId}/layers` → checks ≥ 1 layer
8. `GET <artifact_url>` → checks PNG bytes

```bash
node scripts/smoke.mjs
```

Pass output (last lines):

```
PASS POST /api/upload — request_id=3fa85f64-...
PASS POST /api/analyze — status=COMPLETED task=single_image_caption ...
PASS job reached terminal state — final=COMPLETED
PASS result has answer — confidence=0.87 ...
PASS GET /api/analysis/{jobId}/layers — 3 layers
✓ ALL CHECKS PASSED
```

If the smoke test passes, the backend is fully wired and the frontend will
work — because frontend-v2's `api.ts` calls the exact same endpoints with the
exact same payloads.

### Step 3 — Frontend UI verification

```bash
npm run dev
# open http://localhost:3000
```

Then click **New Analysis** → drop any PNG from `demo_resources/1_masking/`
into the upload zone → type "Describe this scene" → send.

What you should see in the right-side chat:

| State | UI |
|---|---|
| Immediately after send | user bubble + a "thinking" assistant bubble with spinner + cyan pulse + `queued` pill |
| ~2s later | status pill becomes `running` |
| When pipeline completes | thinking bubble replaces with the real `result.answer` + `conf` chip + workflow chip + model pills (from `result.models_used`) + metrics grid (Regions / Changed px / Area) |
| Recent Chats list | cyan pulsing dot on the running session, green dot when complete |
| Bottom of assistant message | "Open full analysis →" link → `/analysis/{jobId}` (the layer viewer page) |

If you see the user bubble + a real answer + chips → the chat wiring works.

### Step 4 — Layer viewer verification

Click the "Open full analysis →" link. You should land on `/analysis/{jobId}`
which:

- Shows breadcrumb `analysis / {jobId}`
- Shows status pill (COMPLETED, green) + confidence badge
- Renders the **real** layer image from `artifact_url` returned by the backend
- Has a layer switcher in the toolbar that fetches real layers
- Has an Evidence / Trace / Metrics right panel populated from the real result

If the layer image is visible and you can switch between layers → the full
visualization path works.

---

## What to check if something fails

| Symptom | Likely cause | How to fix |
|---|---|---|
| `/api/health` returns 404 | Wrong API base | Check backend started on port 8000 |
| `models_available` is empty `{}` | Model checkpoints missing | See `DEMO_SETUP.md` in parent repo — needs `checkpoints/` dir |
| `upload` fails with `UNSUPPORTED_MEDIA` | Wrong file type | Use `.tif/.tiff/.png/.jpg/.jpeg/.geojson` |
| `analyze` returns `MODEL_NOT_CONFIGURED` | Specific model missing | Check `checkpoints/{changeformer,cdvqa,...}/` exists |
| `result.answer` is empty string | Pipeline ran but produced no text | Backend bug — check backend logs |
| Frontend says `Could not start analysis: fetch failed` | Backend not on port 8000 | `NEXT_PUBLIC_API_BASE_URL` in `.env.local` |
| Smoke test prints "models list non-empty FAIL" | Backend up but no models | Check `/api/models` directly; backend may have crashed during init |

---

## What's already wired (no changes needed)

| Piece | File | Status |
|---|---|---|
| API client | `src/lib/api.ts` | Identical to connected `frontend/` v1 |
| Endpoints | `src/lib/endpoints.ts` | Identical to connected `frontend/` v1 |
| Types | `src/lib/types.ts` | Mirror of backend Pydantic schemas |
| Chat send | `src/app/analysis/page.tsx` sendMessage() | Real `api.analyze()` call + polling |
| Chat resume | resumePolling() | Polls in-flight jobs on page load |
| Job page | `src/app/analysis/[jobId]/page.tsx` | Uses `useJob` / `useAnalysisResult` / `useLayers` hooks |
| Error handling | `src/lib/api.ts` http() | Parses `error.message` and `detail` |

---

## What's NOT wired yet (future work)

| Item | Why deferred |
|---|---|
| Pixel inspector UI | Backend supports it, no click handler wired yet on `/analysis/[jobId]` |
| Histogram chart | Backend supports it, MUI X Charts installed but unused |
| PDF report export | Backend supports `/api/reports/{id}`, no UI button yet |
| Video intelligence | `/api/video/*` endpoints not consumed in frontend-v2 |
| Auth | Backend has no auth, frontend has no login |

These are follow-on items, not blockers for the core demo.