# SatQuery AI: Frontend Polish Handoff

**Audited:** 2026-09-14 · branch `refactor/s0-remove-dead-layers` · every file under `frontend/src/` (29 files, ~4,400 lines)
**Checked against:** the actual FastAPI handlers and Pydantic schemas in `backend/app/` (not the older contract doc)
**Tooling baseline:** `npx tsc --noEmit` passes · `npx eslint src` gives **25 errors, 10 warnings**

All paths below are relative to `frontend/`. Line numbers match the branch state above.

---

## 0. Ground rule for this pass: no fabricated data

The UI must never show a number, name, status or picture the backend did not send. This is a demo and paper
project, and one invented "43 regions" on screen can sink the credibility of every real result.

When a value is missing, do this:

| Situation | Show |
|---|---|
| Field absent or `null` | `—`, or hide the row |
| Request still loading | A skeleton or "Loading…" |
| Request failed | The backend error message (`error.message` or `detail`), shown in red |
| Feature not supported for this job | Say so plainly, e.g. "NDVI unavailable: no NIR band" (the backend sends this reason) |

**Banned patterns:** `?? <literal number>`, `|| "<made-up string>"`, a `catch {}` that swaps in fake objects,
and hardcoded model names, latencies, durations or coordinates.

Search to find them again after fixing: `rg -n '\?\? [0-9"]|\|\| "[A-Z]|\|\| [0-9]|catch \{' src`

---

## 1. P0: Fake or wrong data shown to users (fix first)

### 1.1 Mock data inventory (every hardcoded fallback)

| ID | File:line | What is faked | Replace with |
|---|---|---|---|
| M1 | `src/components/results/ResultsPanel.tsx:200` | Regions `?? 43` | `evidence.spatial.statistics.region_count`, else `—` |
| M2 | `src/components/results/ResultsPanel.tsx:204` | Changed area fallback `"152.4k m²"` | `evidence.spatial.statistics.estimated_area_sq_m`, else `—` |
| M3 | `src/components/results/ResultsPanel.tsx:263` | Detections tab: `?? 43 regions detected` | Real count or `evidence.spatial.boxes.length` |
| M4 | `src/components/results/ResultsPanel.tsx:274-277` | Metadata tab: task `"CHANGE"`, model `"satquery-v2-large"`, latency `"1.34s"` | `result.task`, `result.models_used`, sum of trace `duration_ms` |
| M5 | `src/components/results/ResultsPanel.tsx:14-18, 105-107` | Pipeline tracker is static: steps 0–1 always "✓ completed", step 2 always "running" | Remove it, or drive it from `GET /api/jobs/{id}` `execution_steps` |
| M6 | `src/app/page.tsx:31-35, 55-59, 89-93` | Trace bar with invented durations (38, 112, 85, 94, 650 ms) and fake step names (`sam2_grounding`, `model_execution`) | Delete. `POST /api/analyze` is synchronous and returns the real `execution_trace`, so render that |
| M7 | `src/app/page.tsx:83-85` | Local job saved as `status: "COMPLETED"` and `task: "CHANGE"` when AUTO, whatever actually happened | Use `status` and `task` from the analyze response |
| M8 | `src/components/upload/UploadPanel.tsx:42-46` | **Upload failure is swallowed.** It adds a fake raster (1024×1024, 3 bands, `EPSG:32636`, "Optical RGB", green ✓) | Show the error. Never add a raster the server did not accept |
| M9 | `src/components/upload/UploadPanel.tsx:53` | Video upload failure adds a fake video (45.2 s, 30 fps, 1356 frames, H264) | Show the error |
| M10 | `src/lib/api.ts:94` | Missing `request_id` becomes a random UUID | Throw. The backend always returns `request_id` |
| M11 | `src/lib/api.ts:109-121` | Raster defaults: width/height `1024`, bands `3`, dtype `uint8`, **crs `"EPSG:4326"`**, modality `"Optical"`, `valid_raster: true` | Keep `undefined`. A plain PNG has no CRS, but the HUD currently claims EPSG:4326 |
| M12 | `src/lib/api.ts:139-147` | Video defaults: fps `30`, 1920×1080, codec `h264`, random id | Keep `undefined` |
| M13 | `src/lib/api.ts:73` | Model task fallback `"Remote Sensing"` | Backend `task` is a required field, so use it directly |
| M14 | `src/components/layout/AppHeader.tsx:44-45` | Header shows **`5/6 MDL`** when health fails or is loading | Show `—/— MDL` in grey while loading, and red on error |
| M15 | `src/components/layout/AppHeader.tsx:122` | Version `"v0.9-alpha"` | `health.data.version` |
| M16 | `src/lib/api.ts:54` | `storage: "available"` is hardcoded | Remove it. The backend does not report storage |
| M17 | `src/app/system/page.tsx:20-30` | Offline fallback: device `"CPU"`, version `"1.0.0"`, environment `"development"` | `—` plus an "API unreachable" banner |
| M18 | `src/app/system/page.tsx:48, 54` | `d.device \|\| "CPU"` shown with **ok** status, and `environment \|\| "development"` | `—` |
| M19 | `src/components/terminal/TerminalConsole.tsx:39` | `models.length \|\| 9` | Real count |
| M20 | `src/components/terminal/TerminalConsole.tsx:57` | "…additional registered neural adapters **active in memory**". False: the models are lazy-loaded | "+N more registered" |
| M21 | `src/components/terminal/TerminalConsole.tsx:64` | "Connecting to SatQuery neural pipeline gateway..." stays up forever when the backend is down | Show an error on `modelsQuery.isError` |
| M22 | `src/components/terminal/TerminalConsole.tsx:131` | Job line fallbacks `"ANALYSIS"`, `"Geospatial query"`, `"COMPLETED"` | `—` |
| M23 | `src/app/jobs/page.tsx:44-47` | Job fallbacks: task `"ANALYSIS"`, query `"Geospatial Execution Job"`, status `"COMPLETED"`, created_at **now** | `—`, or skip the row |
| M24 | `src/app/analysis/[jobId]/page.tsx:14` | `status ?? "COMPLETED"`, so an unknown or failed job lookup displays as COMPLETED | `"UNKNOWN"` |
| M25 | `src/app/analysis/[jobId]/page.tsx:17-30` | When there is no result, builds a fake one: query `"Satellite intelligence spatial query"`, answer "Analysis execution completed…", **confidence `0.0`** (renders "0.0%") | Render a "result not available" state |
| M26 | `src/app/analysis/[jobId]/page.tsx:170-172` | Metrics show **`0`** / `"0 m²"` for every job, because `metrics` does not exist on the response (see C2) | Read `evidence.spatial.statistics`, else `—` |
| M27 | `src/app/analysis/[jobId]/page.tsx:211` | Empty models list shows `"SatQuery Execution Engine"` | "No models recorded" |
| M28 | `src/app/analysis/[jobId]/page.tsx:123` | `"routing: agent intent controller"` is hardcoded | `result.workflow` / `result.workflow_reason` |
| M29 | `src/app/video/[jobId]/page.tsx:25-32` | Fallback `models_used: ["SAM 2.1", "Grounding DINO"]`, query `"Video Tracking & Intelligence"` | Error state |
| M30 | `src/app/video/[jobId]/page.tsx:48` | Duration `?? 45.2` | Hide the timeline until metadata arrives |
| M31 | `src/app/video/[jobId]/page.tsx:78` | `"H264 Stream · Realtime SAM2 / ByteTrack"`. ByteTrack is not in the pipeline and nothing runs in realtime | `video_metadata.codec` only |
| M32 | `src/app/video/[jobId]/page.tsx:63` | `status \|\| "COMPLETED"`, always green, including `"NO_DATA"` | Colour by status |
| M33 | `src/app/visual-analytics/[jobId]/page.tsx:44-52` | **Pixel Telemetry shows invented values before any click**: col 412/row 650, coords `35.52184, 33.90112`, NDVI `0.4125`, probability `89.42%`, "Changed" | Show "Click the image to inspect a pixel" |
| M34 | `src/app/visual-analytics/[jobId]/page.tsx:243-246` | Histogram fallbacks: max `0.998`, mean `0.314`, σ `0.341` | Loading or error state |
| M35 | `src/app/visual-analytics/[jobId]/page.tsx:140-160` | When a layer image fails, draws **fake SVG blobs** (green ellipses for NDVI, red gradient for change, blue wave for NDWI) | Show the backend error. It returns the reason, e.g. `IndexNotAvailableError` "no NIR band" |
| M36 | `src/app/jobs/page.tsx:34-35` + `src/lib/localJobs.ts` | Jobs list merges in `localStorage` records. They carry fake statuses (M7) and reappear after a server clear | Use `GET /api/jobs` as the only source. Delete `localJobs.ts` |

### 1.2 Backend-contract mismatches (UI reads fields that do not exist)

| ID | File:line | Frontend expects | Backend actually sends |
|---|---|---|---|
| C1 | `src/lib/types.ts:126-142` (`AnalysisResult`) | `evidence: EvidenceItem[]` | `evidence: EvidencePackage` **object**: `{ spatial: { boxes[], statistics{}, overlay_path, … }, consistency[], summary, metadata }` (`backend/app/schemas/evidence.py:55`). The analysis page's Evidence section therefore **always** reads "No evidence registered." |
| C2 | same | `metrics: SpatialMetrics` | **No `metrics` field.** Use `evidence.spatial.statistics`: `region_count`, `changed_pixels`, `change_ratio`, `estimated_area_sq_m`, `estimated_area_sq_km`, `quality_status`, `quality_warning` |
| C3 | same | `task` ∈ `VQA \| GROUNDING \| CHANGE …` | Lowercase enum: `single_image_vqa`, `single_image_caption`, `single_image_grounding`, `bi_temporal_change`, `bi_temporal_change_vqa`, `optical_sar_analysis`, `video_grounding`, `video_grounding_tracking`, `video_vqa`, `video_change`, `unsupported` |
| C4 | same | *(not typed)* | Also sent and never shown: `status`, `workflow_reason`, `warnings[]`, `errors[]`, `artifacts{}`, `orchestration`. **`answer` can be `null`.** Surface `warnings` and `errors`: that is where the backend explains weak results |
| C5 | `src/lib/types.ts:1-6` (`JobStatus`) | `PENDING \| RUNNING \| COMPLETED \| FAILED \| CANCELED` | Enum `QUEUED, VALIDATING, PLANNING, RUNNING, GENERATING_EVIDENCE, COMPLETED, FAILED`. The DB also writes `CREATED` (upload) and `UPLOADED` (video upload). `PENDING` and `CANCELED` never occur |
| C6 | `src/lib/types.ts:99-104` (`TraceStep`) + `src/components/trace/ExecutionTrace.tsx:74` | `{ name, status: success\|running\|failed\|skipped }` | Result trace items are `{ step, status: success\|warning\|error\|running, model, tool, duration_ms, details }` (`schemas/agent.py:30`). The job endpoint's `execution_steps` use `step_name` and `duration_seconds` instead. `ExecutionTrace` calls `step.name.replace(...)`, which **throws** if given a raw result trace item |
| C7 | `src/lib/types.ts:171-182` (`PixelInspectionResponse`) | `bands{}`, `model.probability`, `model.prediction` | `band_values{}`, top-level `probability`, `prediction` (int class), `model_prediction.status` ("Changed"/"Unchanged"), `geographic_coordinates{x_coord,y_coord,crs}` (`visualization/inspector.py:94`). As written, probability and prediction **never render from real data** |
| C8 | `src/lib/types.ts:184-199` (`HistogramResponse`) | `bins: number[]`, `percentiles{}` | `counts: number[]`, `bins: [{range_start, range_end, count}]`, `units`, `total_pixels`, no `percentiles` |
| C9 | `src/lib/api.ts:215` + `types.ts:157` (`LegendResponse`) | JSON `{min, max, ticks…}` | The legend endpoint returns a **PNG image**. `api.legend()` would fail on `response.json()`. Use `layer.legend_url` in an `<img>` |
| C10 | `src/lib/api.ts:69-78` (models) | status is AVAILABLE or NOT_CONFIGURED only | Backend has `load_state`/`status` ∈ `NOT_CONFIGURED\|AVAILABLE\|LOADED\|FAILED`, plus `last_error`, `validation_status`, `checkpoint`, `device`. `loaded` is set to `isAvailable` (bug, line 76), and `isLoaded` is computed then ignored (line 70) |
| C11 | `src/lib/api.ts:162` + `src/components/query/QueryBar.tsx:6-14` | Task selector sends `override_task` | `override_task` is declared in `schemas/requests.py:9` and **read nowhere in the backend**. Its values (`VQA`, `CHANGE`) also do not match the task enum. See D1 |
| C12 | `src/lib/api.ts:201-211` (layers) | `category` from `layer_type`, description built from `units` | Fine, but the useful fields (`colormap`, `units`, `min/max`, `valid_pixel_pct`, `display_stretch`, `crs`, `source_model`) are dropped |

**Suggested fix for C1–C12:** rewrite `src/lib/types.ts` to mirror `backend/app/schemas/*.py` exactly. Delete every
`any` in `api.ts`: the 13 lint errors there are these mismatches. Once the types are right, TypeScript will point
at most of section 1.1.

---

## 2. Dead or redundant controls (look clickable, do nothing)

| ID | File:line | Control | Action |
|---|---|---|---|
| D1 | `src/components/query/QueryBar.tsx:176-298` | **Task type dropdown** (AUTO/VQA/GROUNDING/CHANGE/TEMPORAL_VQA/VIS. ANALYTICS/VIDEO). The backend ignores it (C11) | Remove it, or disable it with a "routing is automatic" tooltip until the backend honours `override_task` |
| D2 | `src/components/map/MapViewer.tsx:34-54` | **RGB / NDVI / SAR** layer toggles: no `onClick`, RGB permanently "active" | Remove. Layers live on the Visual Analytics page |
| D3 | `src/components/map/MapViewer.tsx:160-187` | **Zoom `+` `−` `⊡`** buttons: no handlers | Implement pan/zoom or remove |
| D4 | `src/app/video/[jobId]/page.tsx:106-120` | Timeline event dots have `cursor-pointer` and a hover-scale but no click handler | On click, seek the `<video>` (`videoRef.current.currentTime = ev.timestamp_sec`) |
| D5 | `src/app/video/[jobId]/page.tsx:134-164` | Event list rows have hover styles, no action | Same seek behaviour. Show `keyframe_url` thumbnails |
| D6 | `src/components/terminal/TerminalConsole.tsx:165-167` | macOS "traffic light" dots with a hover effect, non-functional | Remove the hover, or remove the dots |
| D7 | `src/components/terminal/TerminalConsole.tsx:99` | `status` and `models` commands print the same output | Make `status` print `/api/health`, or drop it |
| D8 | `src/components/results/ResultsPanel.tsx` (whole panel) | On Command Center, `page.tsx:94` redirects to `/analysis/{id}` after 700 ms, so the result tabs and buttons are essentially never seen | Pick one: stay on Command Center and show the result, or redirect with no fake intermediate state |
| D9 | `src/components/layout/AppHeader.tsx:214-243` | Breadcrumb always offers `analysis · vis-analytics · video` for every job. `video` on a raster job, or `analysis` on a video job, opens a 404 or empty page | Only show links valid for the job's task |
| D10 | `src/app/visual-analytics/[jobId]/page.tsx:261-272` | Export PNG / GEOTIFF / GEOJSON always shown. GeoJSON 4xx's when no mask exists. Downloads open in a new tab and a JSON error page lands there | Enable per layer. Use `fetch` and show errors inline |
| D11 | `src/app/visual-analytics/[jobId]/page.tsx:264` | `href="#"` branch is unreachable (`activeId` is never empty) | Remove |
| D12 | `src/components/layout/AppHeader.tsx:285-301` | "Session timer" counts from page load and resets on refresh, so it carries no information | Remove, or replace with the running job's elapsed time |
| D13 | `src/app/jobs/page.tsx:194-211` | Table rows highlight on hover but are not clickable | Make the row open the job |
| D14 | `src/components/upload/UploadPanel.tsx:243-256` | "clear" only clears rasters. A registered video can **never** be removed | Clear everything, and add a per-file remove button |
| D15 | Unused code | `src/components/layout/EmptyState.tsx`, `src/components/layout/StatusBadge.tsx`, `endpoints.artifacts`, `api.legend`, `api.videoResults`, `CommandItem.shortcut` | Delete, or use them |

---

## 3. Logic errors

| ID | File:line | Bug | Effect |
|---|---|---|---|
| L1 | `src/app/analysis/[jobId]/page.tsx:36` | `s.duration_ms ?? s.duration_seconds ? Math.round(s.duration_seconds * 1000) : undefined`. Precedence is `(a ?? b) ? … : …` | A step that has `duration_ms` but no `duration_seconds` gets **`NaN ms`** |
| L2 | `src/app/analysis/[jobId]/page.tsx:34, 40` | Maps `step_name \|\| name` but not `step`. Also `job.data.execution_steps` is `[]` (truthy) when the DB has none, so it never falls back to `result.execution_trace` | Trace shows "unknown", or nothing |
| L3 | `src/components/trace/ExecutionTrace.tsx:27-30` | Only lowercase `success/failed/running/skipped` handled | Backend `error`, `warning`, and DB `SUCCESS` render with no icon, looking identical to skipped |
| L4 | `src/components/upload/UploadPanel.tsx:36-38` + `src/app/page.tsx:66-71` | Each drop makes a new upload with a new `request_id`. Analyze then refuses with "upload all images together" | Pass the existing `request_id` as a form field on the second upload (the backend accepts `request_id` in `POST /api/upload`) |
| L5 | `src/components/upload/UploadPanel.tsx:29` | No 1–2 raster limit client-side. The backend returns 400 for 3+ files, which triggers M8's fake rasters | Validate the count before upload |
| L6 | `src/app/page.tsx:25, 39` | Raster(s) **and** video can both be registered; video silently wins | Make modes exclusive, or ask the user |
| L7 | `src/app/page.tsx:43-44` | Hardcodes `sample_fps: 2`, `min_event_score: 0.4`. That **overrides the backend's tuned default of 0.20** (`schemas/video.py:31`) | Don't send these unless the user sets them |
| L8 | `src/lib/api.ts:179-180` | `if (payload.sampling_fps)` drops a legitimate `0` | Use `!= null` |
| L9 | `src/app/visual-analytics/[jobId]/page.tsx:21, 32, 54` | `activeId` defaults to `"true_color"`. If that layer doesn't exist, the image shows `layers[0]` while the highlight, histogram and export all use `"true_color"` | Initialise from `layers[0].id` once loaded |
| L10 | `src/app/visual-analytics/[jobId]/page.tsx:39-40` | Pixel col/row assume a **1024×1024** image and ignore `object-contain` letterboxing | Wrong pixel, or out-of-bounds 4xx. Use the image's `naturalWidth/Height` and its rendered rect |
| L11 | `src/app/visual-analytics/[jobId]/page.tsx:27, 41` | `pixelInspector` errors and loading are never shown | A failed click silently leaves the mock values up (M33) |
| L12 | `src/app/visual-analytics/[jobId]/page.tsx:204` | Labelled **"lat/lng"**, but `coordinates` are `[x, y]` in the raster CRS (metres for UTM, lon/lat order for 4326) | Label "x, y (CRS)" and show `crs` |
| L13 | `src/app/visual-analytics/[jobId]/page.tsx:128` | Opacity slider fades the whole canvas, not an overlay on a base layer | Either render base plus overlay, or remove the slider |
| L14 | `src/app/video/[jobId]/page.tsx:153-160` | Labels `event_score` "confidence score", colour-graded at 0.9/0.75. The backend says it is a "heuristic event-ranking score; **not calibrated model probability**" | Rename to "event score" and drop the confidence colouring |
| L15 | `src/app/video/[jobId]/page.tsx:19-23` | Query errors (404) aren't handled | Shows "NO_DATA" in green and "No events detected" instead of "job not found" |
| L16 | `src/components/layout/AppHeader.tsx:42, 261` | A health **fetch failure** shows "DEGRADED". The backend always returns `status:"ok"`, so "degraded" is never real | "OFFLINE" on error, grey while loading |
| L17 | `src/components/layout/AppHeader.tsx:141` | `pathname === href`, so no nav item is active on `/analysis/*`, `/video/*`, `/visual-analytics/*` | Prefix match. Treat job pages as Jobs |
| L18 | `src/app/models/page.tsx:23, 33` | Counts `status === "LOADED"`, which never happens (C10), so it always shows "0 loaded". NOT_CONFIGURED gets a **red** dot like a failure | Fix the mapping. Use red only for FAILED |
| L19 | `src/app/models/page.tsx:14` | `isLoading` and `isError` ignored | Backend down looks like "0 registered" |
| L20 | `src/app/jobs/page.tsx:53, 64-70` + `src/lib/api.ts:249-256` | `listJobs` swallows errors and returns `[]`. `clearJobs` error is swallowed, then local state is cleared anyway | Backend down looks like "no jobs". A failed delete **looks successful** |
| L21 | `src/app/jobs/page.tsx:115-129` | **"Clear All Jobs" has no confirmation.** It calls `DELETE /api/jobs`, which wipes every job, file record and workspace folder on the server | Add a confirm dialog naming the count. Consider hiding it outside dev |
| L22 | `src/app/jobs/page.tsx:17-24, 262, 292` | `TASK_COLORS` and the `task === "VIDEO"` routing use frontend task names. Real tasks are lowercase (C3), so every task is grey and **video jobs open the raster analysis page** | Route on `task.startsWith("video_")` |
| L23 | `src/app/jobs/page.tsx:135` | "RUNNING" filter misses `QUEUED/VALIDATING/PLANNING/GENERATING_EVIDENCE/CREATED/UPLOADED` | Group them into an "In progress" filter |
| L24 | `src/components/terminal/TerminalConsole.tsx:116-118` | `jobs` concatenates live and local without de-duplication | Duplicate rows |
| L25 | `src/components/terminal/TerminalConsole.tsx:33-69` | The effect resets the user's typed history every time `modelsQuery.data` changes (30 s refetch) | Seed only once |
| L26 | `src/components/results/ResultsPanel.tsx:59-63` | "Done" pill shows for any result, including `status: FAILED` | Colour by `result.status` |
| L27 | `src/components/results/ResultsPanel.tsx:202-205` | "Changed Area" shown for VQA and grounding tasks | Show metrics relevant to the task |
| L28 | `src/components/upload/UploadPanel.tsx:175` | File `<input>` value is never reset | Re-selecting the same file does nothing |
| L29 | `src/components/upload/UploadPanel.tsx:105-127` | Drop zone stays active during upload | Concurrent uploads race |
| L30 | `src/components/query/QueryBar.tsx:16-21` | Example chips "Flood extent in the eastern district" and "Count the number of vehicles in the parking lot" may not map to a supported workflow | Check each chip against the router. Replace any that route to `unsupported` |

---

## 4. Technical errors

| ID | Where | Issue |
|---|---|---|
| T1 | `npx eslint src` | **25 errors, 10 warnings.** 16× `no-explicit-any` (`api.ts`, analysis page), 3× `react-hooks/set-state-in-effect` (`CommandPalette.tsx:71`, `jobs/page.tsx:61`, `TerminalConsole.tsx:68`), 6× unescaped `"` (`analysis/[jobId]/page.tsx:120`, `video/[jobId]/page.tsx:69`, `CommandPalette.tsx:154`), plus unused vars (`dotColor`, `isLoaded`, `title`, `loading`, `useModels` import, etc.). Target: `eslint` clean |
| T2 | `src/components/trace/ExecutionTrace.tsx:74` | `step.name.replace(/_/g, "_")` does nothing, and crashes on an undefined `name` |
| T3 | `src/components/trace/ExecutionTrace.tsx:80` | Backend `duration_ms` is a float, rendered raw (e.g. `123.456789ms`). Round it |
| T4 | `src/app/visual-analytics/[jobId]/page.tsx:30` | `layers ?? []` makes a new array each render, so the `useMemo` dependency changes every time (lint warning) |
| T5 | `src/components/terminal/TerminalConsole.tsx:1` | No `"use client"` directive. It works only because the importer is a client page |
| T6 | `src/components/ui/CommandPalette.tsx` + `CommandPaletteContext.tsx` | Two global `keydown` listeners both handle Escape. Enter handler re-binds on every render (`filtered` is a new array) |
| T7 | `src/app/page.tsx:60, 94` | `setTimeout` redirects are never cleared on unmount |
| T8 | `src/components/layout/AppHeader.tsx:319` | Shows `⌘ K` on Linux and Windows, where the shortcut is Ctrl+K |
| T9 | Error handling | Each page handles loading and error differently, or not at all. Add one `<QueryState>` component (loading / error with message / empty) and use it everywhere |
| T10 | `src/lib/localJobs.ts` | `localStorage` job cache disagrees with the server (M7, M36, L20). Remove it |
| T11 | Testing | No tests exist, yet `frontend/CLAUDE.md` requires Vitest and Playwright. At minimum add unit tests for the response mappers in `api.ts` (the C-series bugs) |

---

## 5. Visual errors

| ID | Where | Issue |
|---|---|---|
| V1 | Analysis, Video, Visual Analytics, Models, System pages | **Two styling systems.** Command Center and Jobs use CSS variables (`var(--s1)`, `var(--t2)`); the other pages use hardcoded hex Tailwind classes (`text-[#404040]`, `bg-[#0a0a0a]`). The pages look different. Move everything to the tokens in `globals.css` |
| V2 | Many | **Unreadable contrast**: `text-[#2a2a2a]`, `#333`, `#1e1e1e` on `#080808`/`#0a0a0a` backgrounds (roughly 1.3:1, WCAG needs 4.5:1). Examples: `video/[jobId]/page.tsx:153` "confidence score", `visual-analytics/[jobId]/page.tsx:106` "← analysis workspace", `:270` export arrow `#1e1e1e`, `analysis/[jobId]/page.tsx:86, 123, 190`, `models/page.tsx:47, 51` |
| V3 | Page heights | Header is 48 px + main padding 14 px = 62 px. Pages use `calc(100vh - 62px)` (`page.tsx:108`), `64px` (`jobs/page.tsx:88`), `80px` (analysis, video, visual-analytics, models). The result is gaps or clipped bottoms. Use a flex layout instead of magic numbers |
| V4 | `src/app/video/[jobId]/page.tsx:93-96` | Debug box "Stream Endpoint: /api/video/{id}/stream…" sits beside the player permanently. Remove it |
| V5 | `src/app/jobs/page.tsx:345-347` | Footer dev note "local store · GET /api/jobs for live data" is visible to users |
| V6 | `src/app/analysis/[jobId]/page.tsx:150-154` | Debug overlay "Target Job ID / Status / Layer" drawn over the image |
| V7 | `src/app/analysis/[jobId]/page.tsx:144-146` | Failed overlay image is just hidden: a blank black panel with no message |
| V8 | Fixed widths | Command Center 268 + 288 px side columns; Visual Analytics 220 + 220 px. **Nothing is responsive**, and the layout breaks below about 1100 px |
| V9 | `src/app/visual-analytics/[jobId]/page.tsx` | Legend images exist (`layer.legend_url`) but are never displayed. Without a colourbar, NDVI and probability layers can't be interpreted |
| V10 | `src/components/query/QueryBar.tsx:17-20` | Emoji icons (🏗🌊🌿🚗) clash with the SVG icon set |
| V11 | `src/components/query/QueryBar.tsx:323` | Hover colour `hsl(222, 88%, 68%)` hardcoded instead of a token |
| V12 | `src/app/jobs/page.tsx:123` | "Clear All Jobs" uses raw `#ef4444`, not `var(--red)` |
| V13 | `src/components/upload/UploadPanel.tsx:124-125` | `onDragLeave` fires when the cursor passes over child elements, so the drop zone flickers |
| V14 | `src/components/map/MapViewer.tsx:154-155` | `{active.width && …}` renders a literal `0` when width is 0 |
| V15 | `src/components/map/MapViewer.tsx:11` | Only the **last** raster is previewed. For a T1/T2 change pair, the user cannot see image A |
| V16 | `src/components/upload/UploadPanel.tsx:210, 334` | Every raster row shows a green ✓ "valid", hardcoded, including fake rasters from M8 |
| V17 | `src/components/layout/AppHeader.tsx:325-339` | "Running-job accent" gradient shows on every job page, running or not |
| V18 | `src/components/layout/EmptyState.tsx` | Uses `slate-*` Tailwind colours from a different palette (also unused, see D15) |

---

## 6. Backend features with no UI (not bugs; for planning)

| Endpoint | What it gives | UI status |
|---|---|---|
| `POST /api/upload/aoi` + `aoi_filename` / `aoi_geojson` on `/api/analyze` | GeoJSON area-of-interest clipping | **No UI** |
| `GET /api/reports/{request_id}` | Report download | No UI |
| `GET /api/trace/{job_id}` | Full agent trace | No UI |
| `GET /api/video/{job_id}/keyframes` | Keyframe list | No UI |
| `AnalyzeResponse.warnings / errors / workflow_reason / orchestration` | Why a result is weak, verification and backtracking info | Not displayed |
| `evidence.spatial.boxes` (+ `geo_bounds`) | Grounding boxes | Not drawn |
| `evidence.consistency[]`, `evidence.summary` | Cross-model agreement | Not displayed |

**Backend note, not the frontend team's:** `GET /api/video/{id}` sets `keyframe_url` from `keyframe_path`, which is
likely a filesystem path, not a URL. Confirm before building thumbnails (D5).

---

## 7. Suggested split and order

1. **Types and API layer** (unblocks the rest): C1–C12, T1 (`any`), M10–M13, M16. One person.
2. **Remove all fabrication**: the rest of section 1.1. Add the shared `<QueryState>` (T9). Grep the banned patterns until clean.
3. **Command Center and upload flow**: L4–L8, L28–L29, D1–D3, D8, D14, M5–M9.
4. **Result pages** (Analysis, Visual Analytics, Video): L1–L3, L9–L15, D4–D5, D10–D11, V4, V6–V7, V9.
5. **Shell and status pages** (Header, Jobs, Models, System, Terminal): L16–L27, D6–D7, D9, D12–D13, M14–M23.
6. **Visual consistency**: V1–V3, V8, and the remaining V items. Do this last so it isn't redone.

**Definition of done for this pass:**
- `npx eslint src` has 0 errors and `npx tsc --noEmit` passes
- With the backend **stopped**, every page shows an explicit offline or error state and no numbers
- The banned-pattern grep in section 0 returns no fabricated fallbacks
- One real raster change job and one real video job display only values that match the API JSON (check in the browser Network tab)
