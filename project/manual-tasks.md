# Your Manual Tasks — Cloud GPU Setup

Things only you can do (accounts, logins, secrets, clicking in a browser). Everything else is in
`project/todo-tomorrow.md`. Details for each step: `deploy/README.md` (the setup manual).

Tick each box when done. Estimated times in brackets.

## Before the agents start (tomorrow morning)

- [ ] **Stop the local backend** before the agents begin (tasks 5 and 6 use the 8 GB GPU). *[1 min]*
- [ ] **Modal account**: sign up at <https://modal.com> with GitHub. Free Starter plan, no card. *[3 min]*
- [ ] **Modal login on this machine**: in the Claude session type
  `! cd ~/dev/isro && .venv/bin/pip install modal && .venv/bin/modal token new`
  and finish the login in the browser tab it opens. *[2 min]*
- [ ] **Google AI Studio key**: <https://aistudio.google.com> → *Get API key* → *Create API key*. Copy it. *[3 min]*
- [ ] **NVIDIA key**: <https://build.nvidia.com> → sign in → open any model → *Get API Key*. Copy it. *[3 min]*

Do NOT paste keys into chat. They go only into the file in the next section.

## Needed before Task 7 (deployment)

- [ ] **Create the cloud secrets file**:
  `cp deploy/.env.modal.example deploy/.env.modal` (Task 7 creates the example file), then open
  `deploy/.env.modal` in an editor and fill in:
  - `SATQUERY_API_KEYS` — generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`;
    one per teammate, comma-separated. Keep a copy somewhere safe (password manager).
  - `DATABASE_URL` — copy the line from `~/dev/isro/.env` (the Supabase pooler URL).
  - `GEMINI_API_KEY`, `NVIDIA_API_KEY` — from above.
  - `SATQUERY_CORS_ORIGINS` — leave `http://localhost:3000,http://127.0.0.1:3000` unless the frontend runs elsewhere.
  *[5 min]*
- [ ] **Local `.env` for testing the writer** (optional): add `GEMINI_API_KEY=`, `NVIDIA_API_KEY=` and
  `SATQUERY_ANSWER_WRITER=on` to `~/dev/isro/.env` if you want written answers locally too. *[1 min]*

## After the agents deploy (Task 7–9)

- [ ] **Check Modal usage** once at <https://modal.com/settings/usage> — confirm credit used is small. *[1 min]*
- [ ] **Send each teammate** the Modal URL and their own key, plus §6 of `deploy/README.md`. *[5 min]*
- [ ] **Teammate laptops**: open `http://localhost:3000/system` → *Backend connection* → paste URL + key →
  *Save & test*. *[2 min each]*

## Decisions waiting for you

- [ ] **GeoTIFF accuracy (sub-project 2)**: which GeoTIFFs will you demo — Sentinel-2 (10 m), high-resolution
  aerial/drone (< 1 m), or something else? And for masks, which things must be masked (buildings, water,
  vegetation, roads…)? The design for sub-project 2 starts from this answer.
- [ ] **Results retention on the cloud** — confirm the default in `project/todo-tomorrow.md` (keep results 7 days).

## Demo day

- [ ] Morning: `SATQUERY_MIN_CONTAINERS=1 .venv/bin/modal deploy deploy/modal_app.py` (keeps the GPU warm). *[2 min]*
- [ ] 5 minutes before: run "mask airplanes" once from the UI.
- [ ] After: `.venv/bin/modal deploy deploy/modal_app.py` (back to free idle), check usage.
- [ ] Emergency: if the cloud fails, start the local backend and switch the connection to `http://localhost:8000`.

## Training data — manual steps (added 2026-09-17)

The automatic downloads (`scripts/download_training_data.py`, sources in
`datasets/manifests/training_sources.yaml`) need nothing more from you. The Kaggle token is already at
`~/.kaggle/access_token`. These are optional extras:

- [x] **Hugging Face token** (done 2026-09-17, logged in as DRAgNATSU66; optional; downloads work without one, but anonymous requests get lower rate
  limits): <https://huggingface.co/settings/tokens> → *Create new token* → type **Read**. Then type
  `! .venv/bin/hf auth login` in the Claude session and paste it at the prompt, not in chat. *[2 min]*

### Phase 2: additional downloads (only if accuracy stops improving)

Do these **after** the automatic ~145 GB set has been trained on and evaluated, and only for a
capability whose test score has stopped improving. Each one is worth fetching only if it targets a
measured weakness.

- [x] **LoveDA, full official set** (done 2026-09-18; the Zenodo zips were not byte-identical to any
  available re-upload, so this was fetched as 8382 individual files from `ahsennazir/loveDA` instead —
  see `project/qna.md` Q-037). Retrained: land-cover LoveDA mIoU 0.428 → 0.488.
- [x] **ISPRS Potsdam / Vaihingen** (access approved for SIH development and download started by you, 2026-09-17; Potsdam.zip 12.4 GB, Vaihingen.zip 14.9 GB, Toronto.zip 3.2 GB) (5 cm aerial imagery, 6 land-cover classes; the best
  high-resolution segmentation benchmark). Request access with the form at
  <https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/default.aspx>. Research use only. *[5 min + wait]*
- [ ] **PRADAN (ISRO, Chandrayaan-2 OHRC/TMC imagery)**: register at <https://pradan.issdc.gov.in>
  (Chandrayaan-2 section: <https://pradan.issdc.gov.in/ch2/>). The images have **no labels**; they are
  only useful after we label them (e.g. craters/boulders), or for testing the crater model. *[10 min]*
- [ ] **Bhoonidhi (ISRO/NRSC, Resourcesat/Cartosat/Sentinel scenes)**: register at
  <https://bhoonidhi.nrsc.gov.in>. Also **unlabelled**. Useful for Indian test scenes and demo imagery,
  not for training as-is. *[10 min]*
- [ ] *Not needed:* **xView** (<https://xviewdataset.org>) and **FAIR1M** (gaofen-challenge.com, which
  was unreachable on 2026-09-17) are both already inside LAE-1M, which is downloading automatically.
  The same goes for DOTA (<https://captain-whu.github.io/DOTA/>) and DIOR.
- [ ] **Licences.** DeepGlobe, Massachusetts, DIOR, DOTA, Inria and ISPRS are for research use.
  LoveDA and OpenEarthMap are CC-BY-NC-SA (no commercial use). WHU, SpaceNet and the Kaggle crater
  set are CC-BY. LAE-1M is MIT, but the underlying images keep their original licences. Fine for
  SIH and a paper; check again before any commercial use.

### Raw data retention (after training)

A trained checkpoint does not need its raw data to run, so most of `datasets/raw/` can be deleted once
a model is final. Keep these:
- **the val/test tiles** for every dataset a model claims a score on (a few GB): needed to re-run the
  evaluation for the paper or demo, and to compare the next model against the same tiles;
- **the manifest** (`datasets/manifests/training_sources.yaml`) and download script, which can fetch
  anything deleted again;
- **the train split** of any dataset still being trained on, or queued for the next run.

Delete the train splits only after the checkpoint has been scored on test, and the result recorded in
`project/qna.md`.

