"""
SatQuery AI — JobRepository
Encapsulates all database operations for analysis jobs, uploaded files, model runs,
execution steps, results, and artifacts.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.job import AnalysisJob
from backend.app.db.models.file import UploadedFile
from backend.app.db.models.model_run import ModelRun
from backend.app.db.models.step import ExecutionStep
from backend.app.db.models.result import AnalysisResult
from backend.app.db.models.artifact import Artifact
from backend.app.logging import logger


def _parse_datetime(val: Any) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    return None


class JobRepository:
    """Repository pattern for managing persistent analysis jobs and their associated metadata."""

    @staticmethod
    async def create_or_get_job(
        session: AsyncSession,
        job_id: str,
        task_type: Optional[str] = None,
        query: Optional[str] = None,
        status: str = "CREATED"
    ) -> AnalysisJob:
        """Creates a new analysis_job or returns existing one."""
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if job is None:
            job = AnalysisJob(
                id=job_id,
                status=status,
                task_type=task_type,
                query=query
            )
            session.add(job)
            await session.flush()
        else:
            if task_type:
                job.task_type = task_type
            if query:
                job.query = query
            if status:
                job.status = status
            job.updated_at = datetime.now(timezone.utc)
            await session.flush()

        return job

    @staticmethod
    async def update_job_status(
        session: AsyncSession,
        job_id: str,
        status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> Optional[AnalysisJob]:
        """Updates the status and optional error metadata of an analysis_job."""
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        res = await session.execute(stmt)
        job = res.scalar_one_or_none()
        if job:
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            if error_code is not None:
                job.error_code = error_code
            if error_message is not None:
                job.error_message = error_message
            if task_type is not None:
                job.task_type = task_type
            await session.flush()
        return job

    @staticmethod
    async def save_uploaded_files(
        session: AsyncSession,
        job_id: str,
        files_data: List[Dict[str, Any]]
    ) -> List[UploadedFile]:
        """Persists uploaded raster file metadata associated with an analysis_job."""
        records = []
        for item in files_data:
            rec = UploadedFile(
                job_id=job_id,
                original_filename=item.get("original_filename") or item.get("filename", "unknown"),
                stored_path=item.get("stored_path", ""),
                mime_type=item.get("mime_type"),
                file_size=item.get("file_size"),
                width=item.get("width"),
                height=item.get("height"),
                band_count=item.get("band_count") or item.get("bands"),
                crs=item.get("crs"),
                bounds=item.get("bounds"),
            )
            session.add(rec)
            records.append(rec)
        await session.flush()
        return records

    @staticmethod
    async def save_model_runs(
        session: AsyncSession,
        job_id: str,
        model_runs_data: List[Dict[str, Any]]
    ) -> List[ModelRun]:
        """Persists executed model runs."""
        records = []
        for run in model_runs_data:
            rec = ModelRun(
                job_id=job_id,
                model_name=run.get("model_name", "unknown"),
                model_version=run.get("model_version"),
                status=run.get("status", "SUCCESS"),
                device=run.get("device"),
                started_at=_parse_datetime(run.get("started_at")) or datetime.now(timezone.utc),
                finished_at=_parse_datetime(run.get("finished_at")) or datetime.now(timezone.utc),
                duration_seconds=run.get("duration_seconds"),
                error_code=run.get("error_code")
            )
            session.add(rec)
            records.append(rec)
        await session.flush()
        return records

    @staticmethod
    async def save_execution_steps(
        session: AsyncSession,
        job_id: str,
        steps_data: List[Dict[str, Any]]
    ) -> List[ExecutionStep]:
        """Persists observable execution trace steps (never hidden chain-of-thought)."""
        records = []
        for s in steps_data:
            rec = ExecutionStep(
                job_id=job_id,
                step_name=s.get("step_name") or s.get("step", "unknown_step"),
                status=s.get("status", "SUCCESS"),
                model_name=s.get("model_name"),
                started_at=_parse_datetime(s.get("started_at") or s.get("timestamp")) or datetime.now(timezone.utc),
                finished_at=_parse_datetime(s.get("finished_at")),
                duration_seconds=s.get("duration_seconds") or (s.get("duration_ms", 0.0) / 1000.0 if s.get("duration_ms") else None),
                metadata_json=s.get("metadata_json") or s.get("details_json") or ({"details": s.get("details")} if s.get("details") else None)
            )
            session.add(rec)
            records.append(rec)
        await session.flush()
        return records

    @staticmethod
    async def save_analysis_result(
        session: AsyncSession,
        job_id: str,
        answer: Optional[str],
        confidence: Optional[float],
        result_json: Dict[str, Any]
    ) -> AnalysisResult:
        """Persists final analysis result JSON and summary."""
        rec = AnalysisResult(
            job_id=job_id,
            answer=answer,
            confidence=confidence,
            result_json=result_json
        )
        session.add(rec)
        await session.flush()
        return rec

    @staticmethod
    async def save_artifacts(
        session: AsyncSession,
        job_id: str,
        artifacts_data: List[Dict[str, Any]]
    ) -> List[Artifact]:
        """Persists generated artifact references with filesystem paths."""
        records = []
        for art in artifacts_data:
            rec = Artifact(
                job_id=job_id,
                artifact_type=art.get("artifact_type") or art.get("type", "unknown"),
                filesystem_path=art.get("filesystem_path") or art.get("path", ""),
                mime_type=art.get("mime_type")
            )
            session.add(rec)
            records.append(rec)
        await session.flush()
        return records

    @staticmethod
    async def get_job(session: AsyncSession, job_id: str) -> Optional[AnalysisJob]:
        """Retrieves a full AnalysisJob with all eager child relationships."""
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .options(
                selectinload(AnalysisJob.uploaded_files),
                selectinload(AnalysisJob.model_runs),
                selectinload(AnalysisJob.execution_steps),
                selectinload(AnalysisJob.analysis_results),
                selectinload(AnalysisJob.artifacts),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_analysis_result(session: AsyncSession, job_id: str) -> Optional[AnalysisResult]:
        """Retrieves the latest AnalysisResult record for a job."""
        stmt = (
            select(AnalysisResult)
            .where(AnalysisResult.job_id == job_id)
            .order_by(AnalysisResult.created_at.desc())
        )
        res = await session.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_artifact(session: AsyncSession, job_id: str, artifact_type: str, filename: str) -> Optional[Artifact]:
        """Retrieves a specific artifact record by job_id, type, and filename match."""
        stmt = (
            select(Artifact)
            .where(
                Artifact.job_id == job_id,
                Artifact.artifact_type == artifact_type
            )
        )
        res = await session.execute(stmt)
        for art in res.scalars():
            if art.filesystem_path.endswith(filename) or filename in art.filesystem_path:
                return art
        return None
