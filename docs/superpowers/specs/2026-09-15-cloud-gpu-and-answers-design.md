# Cloud GPU + Better Replies — Design

**Date:** 2026-09-15 · **Branch:** `prototype` · **Deadline:** demo on 2026-09-20 · **Status:** approved in chat

Sub-project 1 of 2 for the demo. Sub-project 2 (GeoTIFF mask and change accuracy) has its own spec.
The PWA is out of scope until after the demo.

## Goal

Run every model on a free cloud GPU reached over HTTPS with an API key, so the tool works from a
laptop with only an integrated GPU. Replace one- or two-word replies with grounded, readable answers.

## Measured starting point

- Scene VQA and captions: `checkpoints/general_rs_vlm` is **BLIP-VQA** (`BlipForQuestionAnswering`); answers are
  one or two words ("Football field.").
- Models run only on the machine that serves the backend (RTX 3070, 8 GB).
- Supabase Postgres (`DATABASE_URL`, pooler `:6543`) stores jobs, results and video flags. Artifact files
  (masks, overlays, videos, PDFs) are on local disk under `results/`.

## Decisions

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| D1 | Whole FastAPI backend runs on **Modal** (Starter plan, $30/month free credit), GPU **T4 (16 GB)** | Backend on device, one remote call per model | One network boundary; no model code changes; video tracking would otherwise send ~40 frames per event over the network |
| D2 | Weights and Hugging Face cache on a Modal **Volume** `satquery-models`; result files on Volume `satquery-results` | Download at every cold start | Cold start stays under about a minute; volumes are free up to 1 TiB/month |
| D3 | Cloud backend uses the **same Supabase database** | New database | Already in use and verified with the pooler (D-113) |
| D4 | App-level keys: `SATQUERY_API_KEYS`; `Authorization: Bearer`, `X-API-Key`, or `?key=` | Modal proxy-auth tokens | `<video src>` and download links cannot send headers; per-teammate revocable keys |
| D5 | Scene model: **Qwen3-VL-4B-Instruct**, 4-bit NF4 (bitsandbytes), saved pre-quantized | GeoChat-7B | Apache-2.0, stronger general reasoning, ~3 GB; switched only if it beats BLIP on the VRSBench sample |
| D6 | Answer writer: **Gemini (free) → NVIDIA NIM (free) → current template answer** | OpenRouter / Ollama as further fallbacks | User decision: two remote providers plus the existing template is enough |
| D7 | The writer receives measured evidence as JSON plus the scene model's text, never the image | Send the image to the LLM | Gemini free tier may use inputs for training; keeps answers tied to measurements |
| D8 | **Number guard:** every number in a written answer must appear in the evidence (±0.05 absolute or ±0.5% for rounding; ratio×100 allowed) or the answer is rejected | Trust the LLM | Measurable, defensible guard against invented figures |
| D9 | Writer is off unless `SATQUERY_ANSWER_WRITER=on` | On by default | Tests and offline runs never call the network |

## Storage on the cloud volume

| Item | Size | Needed |
|---|---|---|
| `changeformer_v6_levir_levircd256_epoch20_best.pt` | 470 MB | yes |
| `cdvqa_satquery.pt` | 54 MB | yes |
| `RemoteCLIP-ViT-B-32.pt` | 578 MB | yes |
| DOFA (527 MB) + optical-SAR fusion (29 MB) + BigEarthNet (91 MB) | 647 MB | optional (optical-SAR refusal path, health listing) |
| HF cache: `IDEA-Research/grounding-dino-base` + `facebook/sam2.1-hiera-small` | 1.07 GB | yes |
| Qwen3-VL-4B-Instruct, pre-quantized 4-bit | ~3 GB (estimate; measured when saved) | yes |
| **Total** | **~5.2 GB (5.8 GB with optional)** | |

Not uploaded: BLIP (1.5 GB, replaced), `satquery_changeformer_best.pt` (470 MB, unused duplicate).

## Components

1. `backend/app/api/auth.py` — API-key middleware; `main.py` adds it inside CORS so 401s carry CORS headers.
   `SATQUERY_CORS_ORIGINS` (comma list) overrides allowed origins.
2. `backend/app/api/v1/endpoints/video.py` — `GET /api/video/{id}` falls back to `result.json` when the database
   has no record or is unreachable.
3. `backend/app/answers/writer.py` — providers, prompt, number guard, fallback chain → `WrittenAnswer(text, source, attempts)`.
4. `backend/app/agent/controller.py` — calls the writer after the pipeline (off the event loop); `AnalyzeResponse`
   gains `answer_source` (default `"template"`) and `answer_facts` (the template answer).
5. `backend/app/ml/adapters/scene_vlm.py` + registry key `scene_vlm` — Qwen3-VL; `run_vqa`/`run_caption` use it when
   available, BLIP otherwise.
6. `scripts/eval_scene_vlm_vrsbench.py` — VQA accuracy and caption ROUGE-L on a fixed 200-sample VRSBench subset.
7. `deploy/modal_app.py`, `scripts/modal_prepare_models.py`, `deploy/README.md` — deployment and manual.
8. Frontend `src/lib/connection.ts` — API URL + key in `localStorage`; every request and media URL uses it;
   connection panel on `/system`; "Waking GPU" state; answer-source badge on results.

## Error handling

- Provider timeout 8 s each; errors and rejections are recorded in the trace, never shown as the answer.
- Missing keys → provider skipped. All providers fail → template answer, `answer_source: "template"`.
- Cloud unreachable → frontend shows "Backend unreachable" with the configured URL.
- Cold start → health request > 3 s shows "Waking GPU (~60 s)".

## Testing and measurement

- Unit: auth (none configured / header / query / wrong key / health open / CORS on 401); video fallback; writer
  chain with mocked HTTP; number guard; controller wiring with the writer stubbed; scene-VLM selection.
- Measurement before switching: BLIP vs Qwen3-VL on 200 VRSBench VQA + 200 captions (same seed).
- End-to-end: this laptop with `CUDA_VISIBLE_DEVICES=""` running only the frontend against the Modal URL —
  masking, change, video, export; cold and warm latency recorded.
- Recorded in `project/qna.md` (Q-020 onward) with measured numbers.

## Risks

- T4 has no native bfloat16: any model path using bf16 autocast must fall back to fp16; verified in the cloud
  smoke test. Fallback GPU: L4 (24 GB, supports bf16), within the free credit for demo hours.
- Free-tier LLM limits or model renames: model names are env-configurable (`GEMINI_MODEL`, `NVIDIA_MODEL`).
- $30 credit: keep-warm only during demo hours.
