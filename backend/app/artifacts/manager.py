import os
import re
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.config import settings
from backend.app.logging import logger
from backend.app.exceptions import InvalidInputError

# A job directory name: starts alphanumeric, so "." and ".." can never match.
_JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


class ArtifactManager:
    """
    Manages all filesystem operations for job artifacts:
    results/<request_id>/
      input/
      overlays/
      masks/
      vectors/
      reports/
      result.json
      trace.json
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.storage.results_dir)
        if not self.base_dir.is_absolute():
            self.base_dir = settings.root_dir / self.base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, request_id: str, create: bool = False) -> Path:
        # Path(request_id).name alone let "." and ".." through: results/.. is the repo root, so
        # GET /api/results/../download zipped the whole 20 GB checkout, .env included (Q-017).
        clean_id = Path(str(request_id)).name
        if not _JOB_ID.fullmatch(clean_id):
            raise InvalidInputError(f"Invalid job id '{request_id}'.", code="INVALID_JOB_ID")
        job_dir = self.base_dir / clean_id
        if job_dir.resolve().parent != self.base_dir.resolve():
            raise InvalidInputError(f"Invalid job id '{request_id}'.", code="INVALID_JOB_ID")
        if create:
            job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def init_job_workspace(self, request_id: str) -> Dict[str, Path]:
        job_dir = self.get_job_dir(request_id)
        dirs = {
            "root": job_dir,
            "input": job_dir / "input",
            "overlays": job_dir / "overlays",
            "masks": job_dir / "masks",
            "vectors": job_dir / "vectors",
            "reports": job_dir / "reports",
            "visualizations": job_dir / "visualizations",
        }
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return dirs

    def get_input_path(self, request_id: str, filename: str) -> Path:
        dirs = self.init_job_workspace(request_id)
        clean_name = Path(filename).name
        return dirs["input"] / clean_name

    def save_result_json(self, request_id: str, data: Dict[str, Any]) -> Path:
        job_dir = self.get_job_dir(request_id)
        out_path = job_dir / "result.json"
        # A pipeline that fails before any tool creates the workspace must still record its result.
        job_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return out_path

    def load_result_json(self, request_id: str) -> Optional[Dict[str, Any]]:
        job_dir = self.get_job_dir(request_id)
        path = job_dir / "result.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save_trace_json(self, request_id: str, trace_data: List[Dict[str, Any]]) -> Path:
        job_dir = self.get_job_dir(request_id)
        out_path = job_dir / "trace.json"
        # A pipeline that fails before any tool creates the workspace must still record its result.
        job_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2, default=str)
        return out_path

    def load_trace_json(self, request_id: str) -> Optional[List[Dict[str, Any]]]:
        job_dir = self.get_job_dir(request_id)
        path = job_dir / "trace.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_artifact_path(self, request_id: str, artifact_type: str, filename: str) -> Optional[Path]:
        job_dir = self.get_job_dir(request_id)
        clean_name = Path(filename).name
        target = job_dir / artifact_type / clean_name
        if target.exists():
            return target
        # Fallback check directly in job_dir
        target_root = job_dir / clean_name
        if target_root.exists():
            return target_root
        return None

    def list_artifacts(self, request_id: str) -> Dict[str, List[str]]:
        job_dir = self.get_job_dir(request_id)
        artifacts: Dict[str, List[str]] = {
            "inputs": [],
            "overlays": [],
            "masks": [],
            "vectors": [],
            "reports": [],
            "data": []
        }
        if not job_dir.exists():
            return artifacts

        for sub in ["input", "overlays", "masks", "vectors", "reports"]:
            d = job_dir / sub
            if d.exists():
                artifacts[sub] = [f.name for f in d.iterdir() if f.is_file()]

        if (job_dir / "result.json").exists():
            artifacts["data"].append("result.json")
        if (job_dir / "trace.json").exists():
            artifacts["data"].append("trace.json")

        return artifacts


artifact_manager = ArtifactManager()
