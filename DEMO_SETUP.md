# Running the SatQuery AI demo from a fresh clone

Branch: `prototype`. Tested on Ubuntu, Python 3.11, Node 24, NVIDIA RTX 3070 (8 GB).

## 1. Clone

```bash
git clone -b prototype https://github.com/KushwahaSujal/SATQuery-AI.git
cd SATQuery-AI
```

## 2. Model weights — not in git

`checkpoints/` (3.6 GB) is gitignored: ChangeFormer alone is 940 MB, over GitHub's 100 MB file limit.
Copy it from a machine that has it (the team's dev box):

```bash
# on the machine that has the weights
tar -cf satquery_checkpoints.tar checkpoints/
# on the demo machine, from the repo root
tar -xf satquery_checkpoints.tar
```

Expected layout: `checkpoints/{bigearthnet,cdvqa,changeformer,dofa,general_rs_vlm,optical_sar,remoteclip}/`.

| Feature | Needs | Without it |
|---|---|---|
| Masking ("mask trees", "cars near red house") | Grounding DINO, SAM 2 | — downloaded automatically from Hugging Face on first request (~1.1 GB, needs internet) |
| Verification agent (confirms the top detection) | `checkpoints/remoteclip` | Masking still works; answers say "verification agent unavailable" |
| Change detection | `checkpoints/changeformer` | Change requests fail |
| Change questions ("has a building been built?") | `checkpoints/cdvqa` + changeformer | Fail |
| Captions / VQA | `checkpoints/general_rs_vlm` | Honest NOT_CONFIGURED message |
| Optical + SAR | `checkpoints/dofa`, `optical_sar` | Honest NOT_CONFIGURED message (it refuses even with them) |

## 3. Backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env        # defaults are fine for a demo
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

PostgreSQL is optional for the demo: if it is unreachable the server logs a warning at startup and keeps
running; results are still written to `results/<job_id>/` and exports work. For job history, start one:
`docker run -d --name satquery-pg -e POSTGRES_USER=satquery -e POSTGRES_PASSWORD=satquery -e POSTGRES_DB=satquery -p 5432:5432 postgres:15`
and set `POSTGRES_HOST=localhost` / `DATABASE_URL=postgresql+asyncpg://satquery:satquery@localhost:5432/satquery` in `.env`.

Check: `curl localhost:8000/api/health` → `"status":"ok"` and `models_available`.

## 4. Frontend

```bash
cd frontend
npm ci
npm run build && npx next start -p 3000     # or: npm run dev
```

Open http://localhost:3000. The UI calls the API at `http://localhost:8000` (override with
`NEXT_PUBLIC_API_BASE_URL` at build time).

## 5. Demo

Inputs, prompts and the expected overlays are in [`demo_resources/README.md`](demo_resources/README.md).
Every result page (image and video) has **Download Results ↓**: a ZIP of the job folder — inputs, masks,
overlays, video keyframes/annotated frames, the PDF audit report, `result.json` and `trace.json`.

Before going on stage:
- Run one masking request first so the Hugging Face models are downloaded and loaded (first call ~15 s,
  then ~6 s).
- Don't run `pytest` while the server is up — both need the GPU.
- `pytest -q tests` needs the checkpoints; expected: 262 passed, 1 skipped (`rasterio` not installed).
