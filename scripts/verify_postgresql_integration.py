#!/usr/bin/env python3
"""
SATQUERY AI — End-to-End PostgreSQL Integration Verification
Tests and validates:
1. PostgreSQL connectivity & table schemas.
2. Real file upload and uploaded_files persistence.
3. Real analysis execution with AgentController.
4. Persistence of analysis_jobs, execution_steps, model_runs, analysis_results, and artifacts.
5. Retrieval via /api/jobs/{id} and /api/results/{id}.
"""
import sys
import os
import uuid
import asyncio
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from backend.app.main import app
from backend.app.db.session import (
    check_database_connection,
    get_session_maker,
    dispose_db_engine,
)
from backend.app.db.repositories.job_repository import JobRepository
from backend.app.logging import logger


async def run_verification():
    print("================================================================================")
    print("SATQUERY AI -- STEP 18: POSTGRESQL DATABASE INTEGRATION VERIFICATION")
    print("================================================================================")

    # 1. Connectivity check
    print("\n1. Testing PostgreSQL connection...")
    db_ok = await check_database_connection()
    if not db_ok:
        print("[ERROR] PostgreSQL is not reachable!", file=sys.stderr)
        sys.exit(1)
    print("   [OK] PostgreSQL connection verified (SQLAlchemy 2.x + asyncpg).")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        # 2. Health endpoint check
        print("\n2. Testing /api/health endpoint...")
        h_resp = await client.get("/api/health")
        assert h_resp.status_code == 200, f"Health failed: {h_resp.text}"
        h_data = h_resp.json()
        print(f"   [OK] Health: status={h_data['status']}, database_connected={h_data.get('database_connected')}")

        # 3. File upload and uploaded_files persistence
        print("\n3. Testing file upload and uploaded_files persistence in PostgreSQL...")
        sample_img = PROJECT_ROOT / "datasets/samples/real_pair/real_image_b.png"
        if not sample_img.is_file():
            print(f"[ERROR] Sample image not found at {sample_img}", file=sys.stderr)
            sys.exit(1)

        req_id = f"pg_verify_{uuid.uuid4().hex[:8]}"
        with open(sample_img, "rb") as f:
            upload_resp = await client.post(
                "/api/upload",
                files={"files": ("real_image_b.png", f, "image/png")},
                data={"request_id": req_id}
            )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        up_data = upload_resp.json()
        print(f"   [OK] Uploaded file: {up_data['uploaded_files']}, request_id: {req_id}")

        # Verify uploaded_files in DB
        session_factory = get_session_maker()
        async with session_factory() as session:
            job_db = await JobRepository.get_job(session, req_id)
            assert job_db is not None, "Job record not found in PostgreSQL!"
            assert job_db.status == "CREATED", f"Expected status CREATED, got {job_db.status}"
            assert len(job_db.uploaded_files) == 1, "Uploaded file record not found in PostgreSQL!"
            f_rec = job_db.uploaded_files[0]
            print(f"   [OK] DB uploaded_files row: filename='{f_rec.original_filename}', {f_rec.width}x{f_rec.height}, {f_rec.band_count} bands, CRS='{f_rec.crs}'")

        # 4. Run real analysis via /api/analyze
        print("\n4. Running production analysis via /api/analyze...")
        query_text = "The small dark-colored vehicle located at the top-right corner of the image."
        print(f"   Query: \"{query_text}\"")

        analyze_resp = await client.post(
            "/api/analyze",
            json={
                "request_id": req_id,
                "query": query_text,
                "image_filenames": ["real_image_b.png"]
            }
        )
        assert analyze_resp.status_code == 200, f"Analyze failed: {analyze_resp.text}"
        an_data = analyze_resp.json()
        print(f"   [OK] Analysis completed: status={an_data['status']}, task={an_data['task']}")
        print(f"        Answer: {an_data.get('answer')}")

        # 5. Verify PostgreSQL records
        print("\n5. Verifying complete persistence hierarchy in PostgreSQL...")
        async with session_factory() as session:
            full_job = await JobRepository.get_job(session, req_id)
            assert full_job is not None
            assert full_job.status == "COMPLETED"
            print(f"   - analysis_jobs: status={full_job.status}, task={full_job.task_type}, created_at={full_job.created_at}")
            print(f"   - uploaded_files: {len(full_job.uploaded_files)} record(s)")
            print(f"   - model_runs: {len(full_job.model_runs)} record(s)")
            for mr in full_job.model_runs:
                print(f"       * ModelRun: {mr.model_name} (status={mr.status})")
            print(f"   - execution_steps: {len(full_job.execution_steps)} record(s)")
            for es in full_job.execution_steps:
                print(f"       * Step: {es.step_name} [{es.status}]")
            print(f"   - analysis_results: {len(full_job.analysis_results)} record(s)")
            if full_job.analysis_results:
                res_rec = full_job.analysis_results[0]
                print(f"       * Result: answer='{res_rec.answer[:60]}...', confidence={res_rec.confidence}")
            print(f"   - artifacts: {len(full_job.artifacts)} record(s)")
            for art in full_job.artifacts:
                print(f"       * Artifact: {art.artifact_type} -> {art.filesystem_path}")

        # 6. Test GET /api/jobs/{id}
        print("\n6. Testing GET /api/jobs/{request_id} retrieval from PostgreSQL...")
        job_get_resp = await client.get(f"/api/jobs/{req_id}")
        assert job_get_resp.status_code == 200, f"GET /api/jobs failed: {job_get_resp.text}"
        job_get_data = job_get_resp.json()
        assert job_get_data["job_id"] == req_id
        assert job_get_data["status"] == "COMPLETED"
        assert job_get_data["result_available"] is True
        assert len(job_get_data["execution_steps"]) > 0
        assert len(job_get_data["artifacts"]) > 0
        print(f"   [OK] Retrieved job details from PostgreSQL: {len(job_get_data['execution_steps'])} steps, {len(job_get_data['artifacts'])} artifacts.")

        # 7. Test GET /api/results/{id}
        print("\n7. Testing GET /api/results/{request_id} retrieval from PostgreSQL...")
        res_get_resp = await client.get(f"/api/results/{req_id}")
        assert res_get_resp.status_code == 200, f"GET /api/results failed: {res_get_resp.text}"
        res_get_data = res_get_resp.json()
        assert res_get_data["request_id"] == req_id
        assert res_get_data["answer"] == an_data["answer"]
        print(f"   [OK] Retrieved full analysis result from PostgreSQL successfully.")

    await dispose_db_engine()
    print("\n================================================================================")
    print("SUCCESS: FULL POSTGRESQL INTEGRATION VERIFIED END-TO-END!")
    print("================================================================================")


if __name__ == "__main__":
    asyncio.run(run_verification())
