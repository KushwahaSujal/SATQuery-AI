# TODO — 2026-09-16 onward (demo 2026-09-20)

Execution: **subagent-driven** (`superpowers:subagent-driven-development`), one fresh agent per task, review
between tasks. Plan: `docs/superpowers/plans/2026-09-15-cloud-gpu-and-answers.md`.
Your manual steps: `project/manual-tasks.md`.

## Day 1–2 (16–17 Sep): Sub-project 1 — cloud GPU + written answers

| # | Task | Needs from you | Status |
|---|---|---|---|
| 1 | API-key middleware + `SATQUERY_CORS_ORIGINS` | — | [ ] |
| 2 | `GET /api/video/{id}` from `result.json` when DB has no record | — | [ ] |
| 3 | Answer writer: Gemini → NVIDIA → template, number guard | — | [ ] |
| 4 | `answer_source` / `answer_facts` in responses + UI label | — | [ ] |
| 5 | BLIP baseline on VRSBench (200 VQA + 200 captions) | local backend stopped | [ ] |
| 6 | Qwen3-VL-4B scene model; keep only if it beats BLIP | local backend stopped | [ ] |
| 6b | **Results retention** on the cloud (see below) | confirm 7 days | [ ] |
| 7 | Modal deployment, weights upload, smoke check | Modal login, `deploy/.env.modal` | [ ] |
| 8 | Frontend backend-connection panel (URL + key) | — | [ ] |
| 9 | Cloud end-to-end run, Q-020/Q-021 in `project/qna.md`, push | — | [ ] |

### 6b. Results retention (added after plan review)

Why the results volume exists: Modal containers have no permanent disk. A job's masks, overlays, video,
PDF and `result.json` are written during the request, and the browser fetches them **afterwards** (overlay
image, video stream, *Download Results* zip, reopening a job). The container shuts down 5 minutes after the last
request and its disk is wiped, so without a volume every link to an older job would break. It is **not** for
training — training data stays on your machine.

To stop it growing forever: a startup-time cleanup on the cloud deletes `results/<job>/` folders older than
**7 days** (env `SATQUERY_RESULTS_RETENTION_DAYS`, default 7 in the cloud, unset = keep forever locally).
Measured job sizes: masking 1.5 MB, video 3.4 MB, change detection 15.6 MB.
Implement as a small task before Task 7: function `purge_old_results(results_dir, days)` in
`backend/app/artifacts/manager.py`, called from the app lifespan when the env var is set; unit test with
folders whose mtime is set to 8 and 6 days ago.

## Day 3–4 (18–19 Sep): Sub-project 2 — GeoTIFF mask and change accuracy

- [ ] Your answer: which GeoTIFFs and which classes to mask (see `project/manual-tasks.md`).
- [ ] Brainstorm → spec → plan (same process as sub-project 1).
- [ ] Baseline measurements on held-out labelled GeoTIFFs before any training.
- [ ] Fine-tuning runs on your RTX 3070; upload new weights to the Modal volume (`deploy/README.md` §4).
- [ ] Before/after numbers recorded in `project/qna.md`.

## Day 5 (20 Sep): Demo

- [ ] Full rehearsal from a laptop with the GPU hidden, against the cloud.
- [ ] Keep-warm deploy, usage check, fallback to local backend ready.

## Deferred (after the demo)

- PWA / mobile app.
- Supabase Storage for result files instead of the Modal volume (only if multiple backends are needed).
