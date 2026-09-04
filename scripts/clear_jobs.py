#!/usr/bin/env python3
"""
SatQuery AI — Clear All Demo Jobs Script
Cleans up demo job records in PostgreSQL database and removes workspace job artifact folders.
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete
from backend.app.db.session import get_session_maker
from backend.app.db.models.job import AnalysisJob
from backend.app.db.models.file import UploadedFile
from backend.app.db.models.model_run import ModelRun
from backend.app.db.models.step import ExecutionStep
from backend.app.db.models.result import AnalysisResult
from backend.app.db.models.artifact import Artifact
from backend.app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

async def clear_database_jobs():
    print("============================================================")
    print("SATQUERY AI — CLEAR DEMO JOBS")
    print("============================================================")
    
    session_factory = get_session_maker()
    async with session_factory() as session:
        print("[1/2] Deleting job database records...")
        await session.execute(delete(Artifact))
        await session.execute(delete(AnalysisResult))
        await session.execute(delete(ExecutionStep))
        await session.execute(delete(ModelRun))
        await session.execute(delete(UploadedFile))
        await session.execute(delete(AnalysisJob))
        await session.commit()
        print("[OK] Database tables cleared.")

def clear_workspace_jobs():
    print("[2/2] Cleaning up workspace job directories...")
    jobs_dir = PROJECT_ROOT / "workspace" / "jobs"
    if jobs_dir.exists():
        for item in jobs_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                print(f" Removed job folder: {item.name}")
    print("[OK] Workspace jobs directory cleaned.")
    print("============================================================")

async def main():
    await clear_database_jobs()
    clear_workspace_jobs()

if __name__ == "__main__":
    asyncio.run(main())
