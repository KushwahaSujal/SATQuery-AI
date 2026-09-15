# SatQuery AI — Cloud GPU Setup Manual

How to run the SatQuery AI backend on a free Modal cloud GPU so the app works from any laptop, even one
with only an integrated GPU. Written for branch `prototype`. Plan:
`docs/superpowers/plans/2026-09-15-cloud-gpu-and-answers.md`.

```
 Laptop (browser + Next.js frontend)  ──HTTPS + API key──►  Modal: FastAPI backend on a T4 GPU
                                                                ├─ Volume satquery-models  (weights, HF cache)
                                                                ├─ Volume satquery-results (masks, overlays, zips)
                                                                ├─ Supabase Postgres       (jobs, video flags)
                                                                └─ Gemini → NVIDIA NIM     (answer wording)
```

## What it costs

| Item | Free allowance | Our use |
|---|---|---|
| Modal compute (Starter plan) | $30 of credit per month, no card | T4 ≈ $0.59/h. Free while idle (shuts down after 5 min). |
| Modal volumes | 1 TiB per month | ~5.2 GB (see below) |
| Supabase | existing project | unchanged |
| Gemini API (Google AI Studio) | free tier, no card | one short request per answer |
| NVIDIA NIM (build.nvidia.com) | 1,000 credits on signup | only when Gemini fails |

### What goes on the cloud volume

| Item | Size |
|---|---|
| ChangeFormer v6 (LEVIR) | 470 MB |
| CDVQA | 54 MB |
| RemoteCLIP | 578 MB |
| DOFA + optical-SAR fusion + BigEarthNet (optional) | 647 MB |
| Hugging Face cache: Grounding DINO base + SAM 2.1 small | 1.07 GB |
| Qwen3-VL-4B scene model, 4-bit | ~3 GB (measured at step 2) |
| **Total** | **~5.2 GB (5.8 GB with the optional models)** |

Not uploaded: BLIP (1.5 GB, replaced by Qwen3-VL) and `satquery_changeformer_best.pt` (470 MB, unused copy).
Of the local 3.6 GB `checkpoints/`, 1.1 GB is required and 0.65 GB optional.

---

## 1. Accounts and keys (once)

1. **Modal** — sign up at <https://modal.com> (GitHub login works). Then, in the repo:
   ```bash
   .venv/bin/pip install modal
   .venv/bin/modal token new        # opens the browser, saves ~/.modal.toml
   ```
2. **Google AI Studio** — <https://aistudio.google.com> → *Get API key* → create key.
3. **NVIDIA** — <https://build.nvidia.com> → sign in → any model page → *Get API Key*.
4. **Pick an API key for SatQuery** — any long random string, one per teammate:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## 2. Prepare the scene model (once, on the RTX 3070 machine)

Stop the local backend first (it needs the GPU).

```bash
.venv/bin/pip install "bitsandbytes>=0.45.0" "accelerate>=1.0.0"
PYTHONPATH=. .venv/bin/python scripts/prepare_scene_vlm.py
```

Downloads Qwen3-VL-4B-Instruct (~9 GB, once), saves the 4-bit copy to `checkpoints/scene_vlm_qwen3vl4b_nf4`
and prints its size.

## 3. Cloud secrets file

```bash
cp deploy/.env.modal.example deploy/.env.modal     # gitignored — never commit it
```

Fill in:

| Variable | Value |
|---|---|
| `SATQUERY_API_KEYS` | the key(s) from step 1.4, comma-separated |
| `DATABASE_URL` | same as in the repo's `.env` (Supabase pooler URL) |
| `GEMINI_API_KEY` | from step 1.2 |
| `NVIDIA_API_KEY` | from step 1.3 |
| `SATQUERY_CORS_ORIGINS` | where the frontend runs, e.g. `http://localhost:3000,http://127.0.0.1:3000` |

## 4. Upload weights (once, and after retraining)

```bash
.venv/bin/modal volume put satquery-models checkpoints/changeformer/changeformer_v6_levir_levircd256_epoch20_best.pt /checkpoints/changeformer/
.venv/bin/modal volume put satquery-models checkpoints/cdvqa /checkpoints/cdvqa
.venv/bin/modal volume put satquery-models checkpoints/remoteclip /checkpoints/remoteclip
.venv/bin/modal volume put satquery-models checkpoints/dofa /checkpoints/dofa
.venv/bin/modal volume put satquery-models checkpoints/optical_sar /checkpoints/optical_sar
.venv/bin/modal volume put satquery-models checkpoints/bigearthnet /checkpoints/bigearthnet
.venv/bin/modal volume put satquery-models checkpoints/scene_vlm_qwen3vl4b_nf4 /checkpoints/scene_vlm_qwen3vl4b_nf4
.venv/bin/modal run deploy/modal_app.py::warm_hf_cache
.venv/bin/modal volume ls satquery-models /checkpoints
```

After retraining a model, re-run only its `volume put` line with `--force`, then redeploy (step 5).

## 5. Deploy

```bash
.venv/bin/modal deploy deploy/modal_app.py
```

It prints a URL like `https://<workspace>--satquery-ai-api.modal.run`. Check it:

```bash
URL=https://<workspace>--satquery-ai-api.modal.run
KEY=<your SatQuery key>
curl -s "$URL/api/health"                                                       # first call wakes the GPU
curl -s -o /dev/null -w "%{http_code}\n" "$URL/api/results/none"                 # 401 (no key)
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $KEY" "$URL/api/results/none"   # 404 (key OK)
```

If a model fails on the T4 with a bfloat16 error, use an L4 instead:
`SATQUERY_MODAL_GPU=L4 .venv/bin/modal deploy deploy/modal_app.py`

## 6. Use it from any laptop

1. Only the frontend runs locally (no GPU needed):
   ```bash
   cd frontend && npm ci && npm run build && npx next start -p 3000
   ```
2. Open <http://localhost:3000/system> → **Backend connection** → paste the Modal URL and your SatQuery key →
   **Save & test**. "Waking GPU (~60 s)" is normal after 5 minutes idle.
3. Use the app as usual. Answers show "Written by gemini:… from measured evidence" or "Measured answer".

Switch back to a local GPU backend by entering `http://localhost:8000` with an empty key.

## 7. Demo day

- **Keep it warm** for the demo (uses credit only while running):
  ```bash
  SATQUERY_MIN_CONTAINERS=1 .venv/bin/modal deploy deploy/modal_app.py
  ```
  Afterwards scale back to zero: `.venv/bin/modal deploy deploy/modal_app.py`
- Run one "mask airplanes" request 5 minutes before starting.
- Watch credit at <https://modal.com/settings/usage>.
- Stop everything: `.venv/bin/modal app stop satquery-ai`

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| "API key rejected" | key in `deploy/.env.modal` `SATQUERY_API_KEYS` matches the one entered; redeploy after editing |
| "Backend unreachable" | `curl $URL/api/health`; `modal app logs satquery-ai` |
| First request very slow | cold start; see measured times below |
| Answers always "Measured answer" | `GEMINI_API_KEY`/`NVIDIA_API_KEY` set? Trace step "Answer written from measured evidence" shows each provider's status |
| Video/images don't load, zip gives 401 | frontend must be the version with the connection panel (adds `?key=` to media) |
| Out of credit | Modal stops serving; use the local backend (`http://localhost:8000`) until the monthly reset |

## Measured

| Measurement | Value |
|---|---|
| Scene model folder size | _filled in during Task 6_ |
| Volume total (`modal volume ls`) | _filled in during Task 7_ |
| Cold start (health, after idle) | _filled in during Task 9_ |
| Warm: mask airplanes / change question / find red car | _filled in during Task 9_ |
