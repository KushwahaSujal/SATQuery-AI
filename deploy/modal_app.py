"""
SatQuery AI on Modal (Q-022): the unchanged FastAPI backend on a cloud GPU.
  modal deploy deploy/modal_app.py              # deploy / update
  modal run deploy/modal_app.py::warm_hf_cache  # one-off: download HF models into the volume
Env at deploy time: SATQUERY_MODAL_GPU (default T4), SATQUERY_MIN_CONTAINERS (default 0; 1 keeps it warm).
"""
import os
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
REMOTE = "/root/isro"
GPU = os.environ.get("SATQUERY_MODAL_GPU", "T4")
MIN_CONTAINERS = int(os.environ.get("SATQUERY_MIN_CONTAINERS", "0"))

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0", "ffmpeg")
    .env({"SAM2_BUILD_CUDA": "0"})
    # cu128 wheels still target Turing (T4, sm_75); record the installed torch version in Q-022.
    .pip_install("torch", "torchvision", index_url="https://download.pytorch.org/whl/cu128")
    .pip_install_from_requirements(str(REPO / "backend" / "requirements.txt"))
    .env({"HF_HOME": "/models/hf", "SATQUERY_RESULTS_DIR": "/results", "PYTHONPATH": REMOTE,
          "SATQUERY_ANSWER_WRITER": "on", "SATQUERY_RESULTS_RETENTION_DAYS": "7"})
    .run_commands(f"mkdir -p {REMOTE}", f"ln -s /models/checkpoints {REMOTE}/checkpoints")
    .add_local_dir(str(REPO / "backend"), f"{REMOTE}/backend", ignore=["**/__pycache__", "**/*.pyc"])
    .add_local_dir(str(REPO / "configs"), f"{REMOTE}/configs")
)

app = modal.App("satquery-ai")
models = modal.Volume.from_name("satquery-models", create_if_missing=True)
results = modal.Volume.from_name("satquery-results", create_if_missing=True)
secrets = [modal.Secret.from_dotenv(str(REPO / "deploy"), filename=".env.modal")]


@app.function(image=image, gpu=GPU, volumes={"/models": models, "/results": results}, secrets=secrets,
              scaledown_window=300, timeout=900, min_containers=MIN_CONTAINERS, max_containers=1)
@modal.concurrent(max_inputs=4)
@modal.asgi_app()
def api():
    os.chdir(REMOTE)
    from backend.app.main import app as fastapi_app
    return fastapi_app


@app.function(image=image, volumes={"/models": models}, timeout=3600)
def warm_hf_cache():
    from huggingface_hub import snapshot_download
    for repo in ("IDEA-Research/grounding-dino-base", "facebook/sam2.1-hiera-small"):
        print(repo, "->", snapshot_download(repo))
    models.commit()
