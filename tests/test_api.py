import pytest
import uuid
import httpx
from backend.app.main import app
from backend.app.db.session import get_session_maker
from backend.app.db.repositories.job_repository import JobRepository
from backend.app.db.models.job import AnalysisJob
from sqlalchemy import delete


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "models_available" in data
    assert "database_connected" in data
    assert data["database_connected"] is True


@pytest.mark.asyncio
async def test_models_list_endpoint(async_client):
    response = await async_client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) >= 5


@pytest.mark.asyncio
async def test_analyze_missing_image(async_client):
    response = await async_client.post("/api/analyze", json={
        "query": "What is in this image?",
        "image_filenames": ["non_existent_file.png"]
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_job_status_from_db(async_client):
    test_id = f"api_test_job_{uuid.uuid4().hex[:8]}"
    session_factory = get_session_maker()

    # Pre-seed a job in PostgreSQL
    async with session_factory() as session:
        await JobRepository.create_or_get_job(
            session=session,
            job_id=test_id,
            task_type="grounding",
            query="Test query for API",
            status="COMPLETED"
        )
        await JobRepository.save_execution_steps(session, test_id, [
            {"step_name": "step_1", "status": "SUCCESS"}
        ])
        mock_result = {
            "request_id": test_id,
            "status": "COMPLETED",
            "task": "single_image_grounding",
            "workflow_id": "workflow_grounding",
            "workflow_reason": "Grounding query",
            "answer": "Test Answer",
            "confidence": 0.95,
            "models_used": ["grounding_dino"],
            "parameters": {},
            "evidence": {},
            "execution_trace": [],
            "warnings": [],
            "errors": [],
            "artifacts": {}
        }
        await JobRepository.save_analysis_result(
            session, test_id, "Test Answer", 0.95, mock_result
        )
        await session.commit()

    # Query via API
    response = await async_client.get(f"/api/jobs/{test_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == test_id
    assert data["status"] == "COMPLETED"
    assert data["task"] == "grounding"
    assert data["result_available"] is True
    assert len(data["execution_steps"]) == 1

    # Query via /api/jobs/{test_id}/status
    status_resp = await async_client.get(f"/api/jobs/{test_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "COMPLETED"

    # Query via frontend alias without /api: /jobs/{test_id}/status
    alias_status_resp = await async_client.get(f"/jobs/{test_id}/status")
    assert alias_status_resp.status_code == 200
    assert alias_status_resp.json()["status"] == "COMPLETED"

    # Query result via /api/results/{test_id}
    res_resp = await async_client.get(f"/api/results/{test_id}")
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["answer"] == "Test Answer"
    assert res_data["confidence"] == 0.95

    # Query result via frontend alias without /api: /results/{test_id}
    alias_res_resp = await async_client.get(f"/results/{test_id}")
    assert alias_res_resp.status_code == 200
    assert alias_res_resp.json()["answer"] == "Test Answer"

    # Query trace via /api/trace/{test_id}
    trace_resp = await async_client.get(f"/api/trace/{test_id}")
    assert trace_resp.status_code == 200
    assert len(trace_resp.json()["execution_steps"]) == 1

    # Query trace via frontend alias without /api: /trace/{test_id}
    alias_trace_resp = await async_client.get(f"/trace/{test_id}")
    assert alias_trace_resp.status_code == 200
    assert len(alias_trace_resp.json()["execution_steps"]) == 1

    # Cleanup
    async with session_factory() as session:
        await session.execute(delete(AnalysisJob).where(AnalysisJob.id == test_id))
        await session.commit()
