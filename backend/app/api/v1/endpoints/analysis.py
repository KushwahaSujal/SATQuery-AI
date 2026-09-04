"""
SatQuery AI — Analysis submission, job lifecycle, results, trace and PDF report.

Split out of the former monolithic api/routes.py (1246 lines).
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.requests import AnalyzeRequest
from backend.app.schemas.responses import (
    UploadResponse,
    AnalyzeResponse,
    HealthResponse,
    ModelsListResponse,
    RasterMetadataResponse,
)
from backend.app.schemas.agent import JobStatus
from backend.app.geo.raster import RasterInspector
from backend.app.geo.modality import ModalityDetector
from backend.app.geo.display import save_display_preview
from backend.app.agent.state import AgentState
from backend.app.agent.controller import agent_controller
from backend.app.models.registry import model_registry
from backend.app.models.device import get_device
from backend.app.artifacts.manager import artifact_manager
from backend.app.config import settings
from backend.app.exceptions import (
    SatQueryException,
    InvalidInputError,
    InvalidRequestError,
    UnsupportedFormatError,
    UnsupportedMediaError,
    PairValidationError,
    InvalidTemporalPairError,
    TemporalAlignmentRequiredError,
    ModelUnavailableError,
    ModelNotConfiguredError,
    InferenceError,
    ModelInferenceError,
    IndexNotAvailableError,
    VisualizationNotAvailableError,
    ArtifactNotFoundError,
    NoRelevantEventsFoundError,
    JobNotFoundError,
    DatabaseUnavailableError,
)
from backend.app.logging import logger
from backend.app.db.session import get_db, check_database_connection
from backend.app.db.repositories.job_repository import JobRepository
from backend.app.db.repositories.video_repository import VideoRepository
from backend.app.schemas.video import (
    VideoAnalysisRequest,
    VideoAnalysisResponse,
    VideoMetadata,
    VideoSamplingConfig,
    VideoFlagConfig,
)
from backend.app.workflows.video_analysis import VideoAnalysisWorkflow
from backend.app.video.decoder import VideoDecoder
from backend.app.visualization import (
    VisualizationRegistry,
    CompositeRenderer,
    SpectralIndexEngine,
    SARVisualizationEngine,
    HeatmapEngine,
    ComparisonEngine,
    InspectorEngine,
    ExportEngine,
    LayerProvenance,
    VisualizationType,
    LayerMetadata,
)
from backend.app.visualization.composites import _apply_percentile_stretch
from backend.app.db.repositories.visualization_repository import VisualizationRepository
from pydantic import BaseModel
from PIL import Image
import numpy as np

router = APIRouter(prefix="/api", tags=["SatQuery AI"])

router = APIRouter(tags=["SatQuery AI"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_query(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """
    Primary analysis endpoint.
    Accepts user natural-language query and list of uploaded image filenames.
    Orchestrates deterministic routing, agent planning, tool execution, evidence fusion,
    visualization layer discovery, and PostgreSQL persistence.
    """
    req_id = request.request_id or str(uuid.uuid4())
    job_dir = artifact_manager.get_job_dir(req_id)
    input_dir = job_dir / "input"

    image_paths: List[str] = []
    for fname in request.image_filenames:
        clean_name = Path(fname).name
        fpath = input_dir / clean_name
        if not fpath.exists():
            raise ArtifactNotFoundError(
                artifact_name=clean_name,
                message=f"Image file '{clean_name}' not found in workspace for request '{req_id}'. Please upload it first.",
                details={"job_id": req_id, "missing_file": clean_name}
            )
        image_paths.append(str(fpath))

    state = AgentState(
        request_id=req_id,
        query=request.query,
        image_paths=image_paths,
        parameters=request.parameters
    )

    response = await agent_controller.run_pipeline(state)

    # Attach discovered visualization layers
    try:
        available_layers = VisualizationRegistry.discover_available_layers(
            request_id=req_id,
            input_paths=image_paths,
            metadata_list=state.metadata,
            models_used=state.selected_models,
            task=state.task.value if state.task else "unknown",
            evidence=state.evidence
        )
        response.visualizations = [l.model_dump() if hasattr(l, "model_dump") else l for l in available_layers]
    except Exception as e:
        logger.warning(f"Could not attach visualization layers: {e}")

    return response


@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """Retrieves list of all analysis jobs from PostgreSQL."""
    try:
        from sqlalchemy import select
        from backend.app.db.models.job import AnalysisJob
        stmt = select(AnalysisJob).order_by(AnalysisJob.created_at.desc())
        res = await db.execute(stmt)
        jobs = res.scalars().all()
        return [
            {
                "id": j.id,
                "job_id": j.id,
                "task": j.task_type or "unknown",
                "query": j.query or "",
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            }
            for j in jobs
        ]
    except Exception as e:
        logger.warning(f"Failed to list jobs: {e}")
        return []


@router.delete("/jobs")
async def delete_all_jobs(db: AsyncSession = Depends(get_db)):
    """Clears all jobs from PostgreSQL database and workspace folders."""
    try:
        from sqlalchemy import delete
        from backend.app.db.models.job import AnalysisJob
        from backend.app.db.models.file import UploadedFile
        from backend.app.db.models.model_run import ModelRun
        from backend.app.db.models.step import ExecutionStep
        from backend.app.db.models.result import AnalysisResult
        from backend.app.db.models.artifact import Artifact
        import shutil

        await db.execute(delete(Artifact))
        await db.execute(delete(AnalysisResult))
        await db.execute(delete(ExecutionStep))
        await db.execute(delete(ModelRun))
        await db.execute(delete(UploadedFile))
        await db.execute(delete(AnalysisJob))
        await db.commit()

        # Clean workspace jobs dir
        jobs_dir = artifact_manager.workspace_root / "jobs"
        if jobs_dir.exists():
            for item in jobs_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)

        return {"status": "ok", "message": "All jobs cleared successfully."}
    except Exception as e:
        logger.error(f"Failed to clear jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves current job status, execution steps, models used, and artifacts from PostgreSQL.
    Falls back to filesystem trace if database record is not yet present.
    """
    try:
        job = await JobRepository.get_job(db, job_id)
        if job:
            return {
                "request_id": job.id,
                "job_id": job.id,
                "status": job.status,
                "task": job.task_type,
                "query": job.query,
                "error_code": job.error_code,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "execution_steps": [
                    {
                        "id": s.id,
                        "step_name": s.step_name,
                        "status": s.status,
                        "model_name": s.model_name,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                        "duration_seconds": s.duration_seconds,
                        "metadata": s.metadata_json
                    }
                    for s in job.execution_steps
                ],
                "models_used": [m.model_name for m in job.model_runs],
                "result_available": len(job.analysis_results) > 0,
                "artifacts": [
                    {
                        "id": a.id,
                        "type": a.artifact_type,
                        "path": a.filesystem_path,
                        "created_at": a.created_at.isoformat() if a.created_at else None
                    }
                    for a in job.artifacts
                ]
            }
    except Exception as e:
        logger.warning(f"Database query failed for get_job_status: {e}")

    # Fallback to filesystem artifact manager if DB was unavailable or job not in DB
    trace = artifact_manager.load_trace_json(job_id)
    result = artifact_manager.load_result_json(job_id)

    if result:
        return {
            "request_id": job_id,
            "job_id": job_id,
            "status": result.get("status", JobStatus.COMPLETED.value),
            "trace": trace,
            "result_available": True,
            "result": result
        }
    if trace:
        return {
            "request_id": job_id,
            "job_id": job_id,
            "status": JobStatus.RUNNING.value,
            "trace": trace,
            "result_available": False
        }

    raise JobNotFoundError(job_id=job_id, details={"job_id": job_id})


@router.get("/results/{request_id}", response_model=AnalyzeResponse)
@router.get("/jobs/{request_id}/results", response_model=AnalyzeResponse)
async def get_job_results(request_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves full analysis result JSON from PostgreSQL.
    Falls back to filesystem result JSON if necessary.
    """
    try:
        res_rec = await JobRepository.get_analysis_result(db, request_id)
        if res_rec and res_rec.result_json:
            return AnalyzeResponse(**res_rec.result_json)
    except Exception as e:
        logger.warning(f"Database query failed for get_job_results: {e}")

    # Filesystem fallback
    data = artifact_manager.load_result_json(request_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No results found for request ID '{request_id}'."
        )
    return AnalyzeResponse(**data)


@router.get("/reports/{request_id}")
async def download_pdf_report(request_id: str, db: AsyncSession = Depends(get_db)):
    """
    Downloads the generated ReportLab PDF audit report using database-recorded path
    or filesystem resolution.
    """
    pdf_path = None

    # Check database-recorded artifact
    try:
        art = await JobRepository.get_artifact(db, request_id, "reports", ".pdf")
        if art and Path(art.filesystem_path).exists():
            pdf_path = Path(art.filesystem_path)
    except Exception as e:
        logger.debug(f"DB lookup for report artifact: {e}")

    # Filesystem fallback
    if not pdf_path or not pdf_path.exists():
        job_dir = artifact_manager.get_job_dir(request_id)
        fallback_path = job_dir / "reports" / f"{request_id}_audit_report.pdf"
        if fallback_path.exists():
            pdf_path = fallback_path

    if not pdf_path or not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF report not found for request ID '{request_id}'."
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"SatQuery_Report_{request_id}.pdf"
    )


@router.get("/trace/{job_id}")
async def get_job_trace(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves execution trace for a job from database or filesystem."""
    try:
        job = await JobRepository.get_job(db, job_id)
        if job and job.execution_steps:
            return {
                "job_id": job_id,
                "status": job.status,
                "execution_steps": [
                    {
                        "step_name": s.step_name,
                        "status": s.status,
                        "model_name": s.model_name,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                        "duration_seconds": s.duration_seconds,
                        "metadata": s.metadata_json
                    }
                    for s in job.execution_steps
                ]
            }
    except Exception as e:
        logger.warning(f"Database lookup for trace failed: {e}")

    trace = artifact_manager.load_trace_json(job_id)
    if trace is not None:
        return {"job_id": job_id, "execution_steps": trace}
    raise JobNotFoundError(job_id=job_id, details={"job_id": job_id})
