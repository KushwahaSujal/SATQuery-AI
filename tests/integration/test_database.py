"""
SatQuery AI — PostgreSQL Database Tests
Tests connection, schema models, repository operations, lifecycle transitions,
cascade relationships, and job status retrieval.
"""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select, delete

from backend.app.db.session import (
    get_session_maker,
    check_database_connection,
)
from backend.app.db.models import (
    AnalysisJob,
    UploadedFile,
    ModelRun,
    ExecutionStep,
    AnalysisResult,
    Artifact,
)
from backend.app.db.repositories.job_repository import JobRepository


@pytest.mark.asyncio
async def test_database_connection():
    """Verify live asyncpg connectivity to PostgreSQL."""
    connected = await check_database_connection()
    assert connected is True, "Database connection failed"


@pytest.mark.asyncio
async def test_job_creation_and_lifecycle():
    """Verify AnalysisJob creation and status progression in PostgreSQL."""
    session_factory = get_session_maker()
    test_id = f"test_job_{uuid.uuid4().hex[:8]}"

    async with session_factory() as session:
        # 1. Create job
        job = await JobRepository.create_or_get_job(
            session=session,
            job_id=test_id,
            task_type="grounding",
            query="Find the vehicle near the road.",
            status="CREATED"
        )
        await session.commit()
        assert job.id == test_id
        assert job.status == "CREATED"
        assert job.task_type == "grounding"

    # 2. Transition through lifecycle
    async with session_factory() as session:
        job = await JobRepository.update_job_status(
            session=session,
            job_id=test_id,
            status="VALIDATING"
        )
        await session.commit()
        assert job.status == "VALIDATING"

    async with session_factory() as session:
        job = await JobRepository.update_job_status(
            session=session,
            job_id=test_id,
            status="PLANNING"
        )
        await session.commit()
        assert job.status == "PLANNING"

    async with session_factory() as session:
        job = await JobRepository.update_job_status(
            session=session,
            job_id=test_id,
            status="RUNNING"
        )
        await session.commit()
        assert job.status == "RUNNING"

    async with session_factory() as session:
        job = await JobRepository.update_job_status(
            session=session,
            job_id=test_id,
            status="COMPLETED"
        )
        await session.commit()
        assert job.status == "COMPLETED"

    # Cleanup
    async with session_factory() as session:
        await session.execute(delete(AnalysisJob).where(AnalysisJob.id == test_id))
        await session.commit()


@pytest.mark.asyncio
async def test_uploaded_files_persistence():
    """Verify UploadedFile metadata persistence with raster spatial properties."""
    session_factory = get_session_maker()
    test_id = f"test_files_{uuid.uuid4().hex[:8]}"

    async with session_factory() as session:
        await JobRepository.create_or_get_job(session, test_id, "vqa")
        files_data = [
            {
                "original_filename": "sample_optical.tif",
                "stored_path": f"/data/jobs/{test_id}/input/sample_optical.tif",
                "mime_type": "image/tiff",
                "file_size": 1048576,
                "width": 512,
                "height": 512,
                "band_count": 3,
                "crs": "EPSG:4326",
                "bounds": [10.0, 20.0, 10.5, 20.5]
            }
        ]
        records = await JobRepository.save_uploaded_files(session, test_id, files_data)
        await session.commit()

        assert len(records) == 1
        assert records[0].original_filename == "sample_optical.tif"
        assert records[0].width == 512
        assert records[0].band_count == 3
        assert records[0].crs == "EPSG:4326"

    # Cleanup
    async with session_factory() as session:
        await session.execute(delete(AnalysisJob).where(AnalysisJob.id == test_id))
        await session.commit()


@pytest.mark.asyncio
async def test_model_runs_and_execution_trace_persistence():
    """Verify ModelRun and ExecutionStep persistence with observable metadata."""
    session_factory = get_session_maker()
    test_id = f"test_runs_{uuid.uuid4().hex[:8]}"

    async with session_factory() as session:
        await JobRepository.create_or_get_job(session, test_id, "grounding")

        # Save model run
        runs = await JobRepository.save_model_runs(session, test_id, [
            {
                "model_name": "IDEA-Research/grounding-dino-base",
                "status": "SUCCESS",
                "device": "cpu",
                "duration_seconds": 1.45
            }
        ])
        assert len(runs) == 1
        assert runs[0].model_name == "IDEA-Research/grounding-dino-base"

        # Save execution steps
        steps = await JobRepository.save_execution_steps(session, test_id, [
            {
                "step_name": "candidate_generation",
                "status": "SUCCESS",
                "model_name": "grounding_dino",
                "duration_seconds": 1.45,
                "metadata_json": {"candidate_count": 5}
            },
            {
                "step_name": "v4_reasoning",
                "status": "SUCCESS",
                "model_name": None,
                "duration_seconds": 0.05,
                "metadata_json": {"strategy": "V4_RELATIONAL"}
            }
        ])
        assert len(steps) == 2
        assert steps[1].metadata_json["strategy"] == "V4_RELATIONAL"
        await session.commit()

    # Cleanup
    async with session_factory() as session:
        await session.execute(delete(AnalysisJob).where(AnalysisJob.id == test_id))
        await session.commit()


@pytest.mark.asyncio
async def test_result_and_artifacts_persistence():
    """Verify AnalysisResult and Artifacts persistence and retrieval."""
    session_factory = get_session_maker()
    test_id = f"test_res_{uuid.uuid4().hex[:8]}"

    async with session_factory() as session:
        await JobRepository.create_or_get_job(session, test_id, "grounding")

        # Save result
        result_record = await JobRepository.save_analysis_result(
            session=session,
            job_id=test_id,
            answer="Identified vehicle at top right.",
            confidence=0.88,
            result_json={"task": "grounding", "confidence": 0.88}
        )
        assert result_record.confidence == 0.88

        # Save artifacts
        artifacts = await JobRepository.save_artifacts(session, test_id, [
            {
                "artifact_type": "overlays",
                "filesystem_path": f"/results/{test_id}/overlays/grounding_overlay.png",
                "mime_type": "image/png"
            },
            {
                "artifact_type": "reports",
                "filesystem_path": f"/results/{test_id}/reports/{test_id}_audit_report.pdf",
                "mime_type": "application/pdf"
            }
        ])
        assert len(artifacts) == 2
        await session.commit()

    # Retrieve full job with relationships
    async with session_factory() as session:
        full_job = await JobRepository.get_job(session, test_id)
        assert full_job is not None
        assert len(full_job.analysis_results) == 1
        assert len(full_job.artifacts) == 2

        # Test get_artifact
        art = await JobRepository.get_artifact(session, test_id, "overlays", "grounding_overlay.png")
        assert art is not None
        assert "grounding_overlay.png" in art.filesystem_path

    # Cleanup
    async with session_factory() as session:
        await session.execute(delete(AnalysisJob).where(AnalysisJob.id == test_id))
        await session.commit()


@pytest.mark.asyncio
async def test_cascade_deletion():
    """Verify that deleting an AnalysisJob cascades to all child records."""
    session_factory = get_session_maker()
    test_id = f"test_cascade_{uuid.uuid4().hex[:8]}"

    async with session_factory() as session:
        await JobRepository.create_or_get_job(session, test_id, "grounding")
        await JobRepository.save_uploaded_files(session, test_id, [{
            "original_filename": "sample.png",
            "stored_path": "/tmp/sample.png"
        }])
        await JobRepository.save_model_runs(session, test_id, [{
            "model_name": "test_model",
            "status": "SUCCESS"
        }])
        await JobRepository.save_execution_steps(session, test_id, [{
            "step_name": "step1",
            "status": "SUCCESS"
        }])
        await JobRepository.save_analysis_result(session, test_id, "ans", 0.9, {"k": "v"})
        await JobRepository.save_artifacts(session, test_id, [{
            "artifact_type": "overlay",
            "filesystem_path": "/tmp/overlay.png"
        }])
        await session.commit()

    # Verify children exist
    async with session_factory() as session:
        files = (await session.execute(select(UploadedFile).where(UploadedFile.job_id == test_id))).scalars().all()
        assert len(files) == 1

    # Delete parent job
    async with session_factory() as session:
        await session.execute(delete(AnalysisJob).where(AnalysisJob.id == test_id))
        await session.commit()

    # Verify all children were cascade-deleted
    async with session_factory() as session:
        files = (await session.execute(select(UploadedFile).where(UploadedFile.job_id == test_id))).scalars().all()
        runs = (await session.execute(select(ModelRun).where(ModelRun.job_id == test_id))).scalars().all()
        steps = (await session.execute(select(ExecutionStep).where(ExecutionStep.job_id == test_id))).scalars().all()
        results = (await session.execute(select(AnalysisResult).where(AnalysisResult.job_id == test_id))).scalars().all()
        arts = (await session.execute(select(Artifact).where(Artifact.job_id == test_id))).scalars().all()

        assert len(files) == 0
        assert len(runs) == 0
        assert len(steps) == 0
        assert len(results) == 0
        assert len(arts) == 0
