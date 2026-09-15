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
