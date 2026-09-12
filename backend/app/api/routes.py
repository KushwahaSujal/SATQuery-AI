"""
SatQuery AI — API compatibility shim.

The former 1246-line monolith was split into `backend/app/api/v1/endpoints/`
(system, uploads, analysis, artifacts, video, visualization). This module
re-exports the aggregate router and the handler functions that other modules
import directly, so existing import sites keep working unchanged:

    from backend.app.api.routes import router
    from backend.app.api.routes import get_job_status      # main.py alias routes

Prefer importing from `backend.app.api.v1` in new code.
"""
from backend.app.api.v1.router import router

from backend.app.api.v1.endpoints.system import get_health, list_models
from backend.app.api.v1.endpoints.uploads import upload_rasters
from backend.app.api.v1.endpoints.analysis import (
    analyze_query,
    delete_all_jobs,
    download_pdf_report,
    get_job_results,
    get_job_status,
    get_job_trace,
    list_jobs,
)
from backend.app.api.v1.endpoints.artifacts import get_artifact_file
from backend.app.api.v1.endpoints.video import (
    analyze_video,
    get_video_analysis_result,
    get_video_keyframes,
    stream_video,
    upload_video,
)
from backend.app.api.v1.endpoints.visualization import (
    export_layer,
    get_analysis_layers,
    get_layer_histogram,
    get_visualization_image,
    get_visualization_legend,
    inspect_pixel_at,
)

__all__ = [
    "router",
    # system
    "get_health", "list_models",
    # uploads
    "upload_rasters",
    # analysis
    "analyze_query", "list_jobs", "delete_all_jobs", "get_job_status",
    "get_job_results", "download_pdf_report", "get_job_trace",
    # artifacts
    "get_artifact_file",
    # video
    "upload_video", "analyze_video", "get_video_analysis_result",
    "get_video_keyframes", "stream_video",
    # visualization
    "get_analysis_layers", "get_visualization_image", "get_visualization_legend",
    "inspect_pixel_at", "get_layer_histogram", "export_layer",
]
