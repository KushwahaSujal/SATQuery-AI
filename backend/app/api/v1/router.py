"""
SatQuery AI — API v1 aggregate router.

Combines the endpoint modules that replaced the former monolithic
`api/routes.py`. Route paths and behaviour are unchanged; only the file
layout differs.
"""
from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    analysis,
    artifacts,
    system,
    uploads,
    video,
    visualization,
)

router = APIRouter(prefix="/api", tags=["SatQuery AI"])

# Order matters: more specific prefixes are registered before the generic
# job routes so that e.g. /api/analysis/{job_id}/... is not shadowed.
router.include_router(system.router)
router.include_router(uploads.router)
router.include_router(video.router)
router.include_router(visualization.router)
router.include_router(artifacts.router)
router.include_router(analysis.router)

__all__ = ["router"]
