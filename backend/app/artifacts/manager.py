import os
import re
import json
import shutil
import time
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

    def save_progress_json(self, request_id: str, progress: Dict[str, Any]) -> Path:
        """Publish live pipeline progress for a running job.

        Execution steps are only written to the database once the pipeline finishes, so
        while a job runs there is nothing for a client to poll. This file is rewritten at
        each checkpoint so the UI can show which tool is executing, which model it is
        using and what has already completed, instead of an indefinite spinner.

        Written atomically: a poller reading the file while it is rewritten would
        otherwise see a truncated document.
        """
        job_dir = self.get_job_dir(request_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        out_path = job_dir / "progress.json"
        tmp_path = job_dir / "progress.json.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, default=str)
        os.replace(tmp_path, out_path)
        return out_path

    def load_progress_json(self, request_id: str) -> Optional[Dict[str, Any]]:
        job_dir = self.get_job_dir(request_id)
        path = job_dir / "progress.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                # A half-written file is not an error worth failing the poll over.
                return None
        return None

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


def _is_job_workspace(entry: Path) -> bool:
    """
    A job workspace is what ArtifactManager.save_result_json / init_job_workspace create:
    a `result.json` file or an `input` subdirectory directly inside the job folder. Matching
    `_JOB_ID` alone isn't enough — e.g. results/evaluations/ (scripts/eval_*.py) matches the
    name pattern but is not a job folder and must never be swept up. Neither marker is
    followed if it is itself a symlink.
    """
    result_json = entry / "result.json"
    input_dir = entry / "input"
    if not result_json.is_symlink() and result_json.is_file():
        return True
    if not input_dir.is_symlink() and input_dir.is_dir():
        return True
    return False


def purge_old_results(results_dir: Path, days: float, now: Optional[float] = None) -> List[str]:
    """
    Delete direct child directories of `results_dir` that look like job workspaces (see
    `_is_job_workspace`), whose name matches `_JOB_ID`, and whose mtime is older than
    `now - days * 86400`. Symlinks and plain files are skipped. Never raises: an unreadable
    `results_dir` or a directory that fails to delete/inspect is logged with `logger.warning`
    and skipped. Returns the sorted list of deleted directory names.
    """
    if now is None:
        now = time.time()
    cutoff = now - days * 86400
    removed: List[str] = []

    if not results_dir.is_dir():
        return removed

    try:
        entries = list(results_dir.iterdir())
    except OSError as exc:
        logger.warning(f"Results retention: could not list '{results_dir}': {exc}")
        return removed

    for entry in entries:
        if entry.is_symlink():
            continue
        if not entry.is_dir():
            continue
        if not _JOB_ID.fullmatch(entry.name):
            continue
        try:
            if not _is_job_workspace(entry):
                continue
            if entry.stat().st_mtime >= cutoff:
                continue
        except OSError as exc:
            logger.warning(f"Results retention: could not stat '{entry}': {exc}")
            continue
        try:
            shutil.rmtree(entry)
            removed.append(entry.name)
        except OSError as exc:
            logger.warning(f"Results retention: failed to remove '{entry}': {exc}")

    return sorted(removed)


def retention_days_from_env() -> Optional[float]:
    """
    Reads SATQUERY_RESULTS_RETENTION_DAYS. Unset/empty -> None. Non-numeric or
    <= 0 -> logs a warning and returns None.
    """
    raw = os.environ.get("SATQUERY_RESULTS_RETENTION_DAYS")
    if raw is None or raw.strip() == "":
        return None
    try:
        value = float(raw)
    except ValueError:
        logger.warning(f"Results retention: invalid SATQUERY_RESULTS_RETENTION_DAYS value '{raw}'.")
        return None
    if value <= 0:
        logger.warning(f"Results retention: SATQUERY_RESULTS_RETENTION_DAYS must be > 0, got '{raw}'.")
        return None
    return value


artifact_manager = ArtifactManager()
