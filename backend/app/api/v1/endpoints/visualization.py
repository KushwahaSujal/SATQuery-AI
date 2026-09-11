"""
SatQuery AI — Visual analytics layers, legends, pixel inspection, histograms and exports.

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

from backend.app.geo.rendering import create_change_overlay
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
from backend.app.ml.registry import model_registry
from backend.app.ml.device import get_device
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


class PixelInspectRequest(BaseModel):
    col: Optional[int] = None
    row: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None


@router.get("/analysis/{job_id}/layers", response_model=List[LayerMetadata])
async def get_analysis_layers(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns all scientifically available visual analytics layers for the specified job.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"

    input_files = []
    if input_dir.exists():
        input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")])

    if not input_files:
        job = await JobRepository.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    meta_list = []
    for f in input_files:
        try:
            m = RasterInspector.inspect(f)
            meta_list.append(m)
        except Exception as e:
            logger.debug(f"Could not inspect input file {f}: {e}")

    model_res = artifact_manager.load_result_json(job_id) or {}
    layers = VisualizationRegistry.discover_available_layers(meta_list, model_res)

    for layer in layers:
        layer.artifact_url = f"/api/analysis/{job_id}/visualizations/{layer.layer_id}"
        if layer.layer_type in [
            VisualizationType.SINGLE_BAND,
            VisualizationType.SPECTRAL_INDEX,
            VisualizationType.SAR_POLARIZATION,
            VisualizationType.PROBABILITY_HEATMAP
        ]:
            layer.legend_url = f"/api/analysis/{job_id}/visualizations/{layer.layer_id}/legend"

    return layers


@router.get("/analysis/{job_id}/visualizations/{layer_id}")
async def get_visualization_image(job_id: str, layer_id: str, db: AsyncSession = Depends(get_db)):
    """
    Renders or serves the cached visualization PNG for a specific layer.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    vis_dir = job_dir / "visualizations"
    vis_dir.mkdir(parents=True, exist_ok=True)
    out_file = vis_dir / f"{layer_id}.png"
    legend_file = vis_dir / f"{layer_id}_legend.png"

    if out_file.exists():
        return FileResponse(path=str(out_file), media_type="image/png")

    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message=f"No input imagery found for job '{job_id}'.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])
    img: Optional[Image.Image] = None
    legend_img: Optional[Image.Image] = None

    if layer_id == "true_color":
        img, _ = CompositeRenderer.render_true_color(arr, meta)
    elif layer_id == "temporal_image_a":
        img, _ = CompositeRenderer.render_true_color(arr, meta)
    elif layer_id == "temporal_image_b":
        if len(input_files) >= 2:
            arr2, meta2 = RasterInspector.read_as_array(input_files[1])
            img, _ = CompositeRenderer.render_true_color(arr2, meta2)
        else:
            img, _ = CompositeRenderer.render_true_color(arr, meta)
    elif layer_id == "grayscale":
        norm, _, _, _ = _apply_percentile_stretch(arr[0] if arr.ndim == 3 else arr)
        img = Image.fromarray(norm, "L")
    elif layer_id.startswith("band_"):
        b_idx = int(layer_id.split("_")[1]) - 1
        img, legend_img, _ = CompositeRenderer.render_single_band(arr, b_idx, meta)
    elif layer_id == "false_color_nir":
        img, _ = CompositeRenderer.render_false_color(arr, meta)
    elif layer_id == "ndvi":
        res = SpectralIndexEngine.compute_ndvi(arr, meta)
        if not res.available:
            raise IndexNotAvailableError(index_name="ndvi", message=res.unavailability_reason, details={"job_id": job_id})
        img, legend_img = res.image, res.legend
    elif layer_id == "ndwi":
        res = SpectralIndexEngine.compute_ndwi(arr, meta)
        if not res.available:
            raise IndexNotAvailableError(index_name="ndwi", message=res.unavailability_reason, details={"job_id": job_id})
        img, legend_img = res.image, res.legend
    elif layer_id == "sar_vv":
        img, legend_img, _ = SARVisualizationEngine.render_polarization_layer(arr, "VV", meta)
    elif layer_id == "sar_vh":
        img, legend_img, _ = SARVisualizationEngine.render_polarization_layer(arr, "VH", meta)
    elif layer_id == "sar_dual_pol":
        img, _ = SARVisualizationEngine.render_dual_pol_composite(arr, meta)
    elif layer_id == "change_probability_heatmap":
        prob_arr = None
        prob_path = job_dir / "masks" / "change_probability.npy"
        if prob_path.exists():
            prob_arr = np.load(str(prob_path))
        else:
            mask_files = list((job_dir / "masks").glob("*.png"))
            if mask_files:
                m_img = Image.open(mask_files[0]).convert("L")
                prob_arr = (np.array(m_img) / 255.0).astype(np.float32)
            else:
                prob_arr = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.float32)
        base_preview = Image.fromarray(arr[0] if arr.ndim == 3 else arr).convert("RGB")
        img, legend_img, _ = HeatmapEngine.render_probability_heatmap(prob_arr, base_preview)
    elif layer_id == "change_raw_mask":
        raw_file = job_dir / "masks" / "change_raw_mask.png"
        if raw_file.exists():
            return FileResponse(path=str(raw_file), media_type="image/png")
        mask_files = list((job_dir / "masks").glob("*.png"))
        if mask_files:
            return FileResponse(path=str(mask_files[0]), media_type="image/png")
        bin_mask = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.uint8)
        img, _ = HeatmapEngine.render_binary_prediction_mask(bin_mask)
    elif layer_id in ["change_filtered_mask", "change_binary_mask"]:
        filt_file = job_dir / "masks" / "change_filtered_mask.png"
        if filt_file.exists():
            return FileResponse(path=str(filt_file), media_type="image/png")
        mask_file = job_dir / "masks" / "change_mask.png"
        if mask_file.exists():
            return FileResponse(path=str(mask_file), media_type="image/png")
        bin_mask = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.uint8)
        img, _ = HeatmapEngine.render_binary_prediction_mask(bin_mask)
    elif layer_id == "change_overlay":
        overlay_file = job_dir / "overlays" / "change_overlay.png"
        if overlay_file.exists():
            return FileResponse(path=str(overlay_file), media_type="image/png")
        filt_file = job_dir / "masks" / "change_filtered_mask.png"
        if not filt_file.exists():
            filt_file = job_dir / "masks" / "change_mask.png"
        if filt_file.exists():
            m_arr = (np.array(Image.open(filt_file).convert("L")) > 0).astype(np.uint8)
            base_pil = Image.fromarray(arr[0] if arr.ndim == 3 else arr).convert("RGB")
            img = create_change_overlay(base_pil, m_arr, color=(239, 68, 68), alpha=0.45)
        else:
            raise VisualizationNotAvailableError(layer_id=layer_id, message="Change overlay not found.", details={"job_id": job_id})
    elif layer_id == "change_regions":
        import cv2
        filt_file = job_dir / "masks" / "change_filtered_mask.png"
        if not filt_file.exists():
            filt_file = job_dir / "masks" / "change_mask.png"
        if filt_file.exists():
            m_arr = (np.array(Image.open(filt_file).convert("L")) > 0).astype(np.uint8)
        else:
            m_arr = np.zeros((arr.shape[1], arr.shape[2]), dtype=np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(m_arr, connectivity=8)
        np.random.seed(42)
        colors = np.random.randint(60, 255, size=(max(num_labels, 1), 3), dtype=np.uint8)
        colors[0] = [15, 23, 42]
        colored = colors[labels]
        img = Image.fromarray(colored, "RGB")
    elif layer_id in ["grounding_bboxes", "grounding_overlay"]:
        overlay_file = job_dir / "overlays" / "grounding_overlay.png"
        if overlay_file.exists():
            return FileResponse(path=str(overlay_file), media_type="image/png")
        overlay_files = list((job_dir / "overlays").glob("*.png"))
        if overlay_files:
            return FileResponse(path=str(overlay_files[0]), media_type="image/png")
        raise VisualizationNotAvailableError(layer_id=layer_id, message="Grounding overlay not found.", details={"job_id": job_id})
    elif layer_id == "sam2_segmentation_overlay":
        sam2_mask = job_dir / "masks" / "segmentation_mask.png"
        if sam2_mask.exists():
            return FileResponse(path=str(sam2_mask), media_type="image/png")
        overlay_files = list((job_dir / "overlays").glob("*.png"))
        if overlay_files:
            return FileResponse(path=str(overlay_files[0]), media_type="image/png")
        raise VisualizationNotAvailableError(layer_id=layer_id, message="SAM 2 overlay not found.", details={"job_id": job_id})
    else:
        raise VisualizationNotAvailableError(layer_id=layer_id, message=f"Unknown or unsupported layer ID '{layer_id}'.", details={"job_id": job_id})

    if img is not None:
        img.save(str(out_file), format="PNG", optimize=True)
    if legend_img is not None:
        legend_img.save(str(legend_file), format="PNG", optimize=True)

    return FileResponse(path=str(out_file), media_type="image/png")


@router.get("/analysis/{job_id}/visualizations/{layer_id}/legend")
async def get_visualization_legend(job_id: str, layer_id: str):
    """
    Serves the colorbar legend PNG for a layer.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    vis_dir = job_dir / "visualizations"
    legend_file = vis_dir / f"{layer_id}_legend.png"

    if not legend_file.exists():
        input_dir = job_dir / "input"
        input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
        if input_files:
            arr, meta = RasterInspector.read_as_array(input_files[0])
            if layer_id == "ndvi":
                res = SpectralIndexEngine.compute_ndvi(arr, meta)
                if res.available and res.legend:
                    res.legend.save(str(legend_file), format="PNG")
            elif layer_id == "ndwi":
                res = SpectralIndexEngine.compute_ndwi(arr, meta)
                if res.available and res.legend:
                    res.legend.save(str(legend_file), format="PNG")
            elif layer_id.startswith("band_"):
                b_idx = int(layer_id.split("_")[1]) - 1
                _, leg, _ = CompositeRenderer.render_single_band(arr, b_idx, meta)
                leg.save(str(legend_file), format="PNG")
            elif layer_id.startswith("sar_"):
                pol = "VV" if "vv" in layer_id else "VH"
                _, leg, _ = SARVisualizationEngine.render_polarization_layer(arr, pol, meta)
                leg.save(str(legend_file), format="PNG")
            elif "probability" in layer_id:
                leg = HeatmapEngine._generate_probability_legend()
                leg.save(str(legend_file), format="PNG")

    if legend_file.exists():
        return FileResponse(path=str(legend_file), media_type="image/png")

    raise VisualizationNotAvailableError(layer_id=layer_id, message=f"Legend not available for layer '{layer_id}'.", details={"job_id": job_id})


@router.post("/analysis/{job_id}/inspect-pixel")
async def inspect_pixel_at(
    job_id: str,
    body: PixelInspectRequest
):
    """
    Inspects scientific band DNs, geographic coordinates, derived index values, and model state for pixel (col, row).
    """
    col = body.col if body.col is not None else body.x
    row = body.row if body.row is not None else body.y
    if col is None or row is None:
        raise InvalidRequestError("Must provide 'col' and 'row' (or 'x' and 'y').", details={"job_id": job_id})

    job_dir = artifact_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message="No input imagery found for job.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])

    derived_indices = {}
    mapping = SpectralIndexEngine.resolve_band_indices(arr, meta)
    if mapping.get("nir") is not None and mapping.get("red") is not None:
        if 0 <= row < arr.shape[1] and 0 <= col < arr.shape[2]:
            nir_val = float(arr[mapping["nir"], row, col])
            red_val = float(arr[mapping["red"], row, col])
            if (nir_val + red_val) != 0:
                derived_indices["NDVI"] = round((nir_val - red_val) / (nir_val + red_val), 4)

    prob_map = None
    prob_path = job_dir / "masks" / "change_probability.npy"
    if prob_path.exists():
        prob_map = np.load(str(prob_path))

    bin_mask = None
    mask_files = list((job_dir / "masks").glob("*.png"))
    if mask_files:
        m_img = Image.open(mask_files[0]).convert("L")
        bin_mask = (np.array(m_img) > 0).astype(np.uint8)

    try:
        inspection = InspectorEngine.inspect_pixel(
            arr=arr,
            col=col,
            row=row,
            metadata=meta,
            prob_map=prob_map,
            bin_mask=bin_mask,
            derived_indices=derived_indices
        )
        return inspection
    except ValueError as e:
        raise InvalidRequestError(str(e), details={"job_id": job_id})


@router.get("/analysis/{job_id}/histogram/{layer_id}")
async def get_layer_histogram(job_id: str, layer_id: str):
    """
    Returns 50-bin distribution histogram and percentiles for the layer.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message="No input imagery found.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])

    data_2d = None
    units = "DN"

    if layer_id.startswith("band_"):
        b_idx = int(layer_id.split("_")[1]) - 1
        if b_idx < arr.shape[0]:
            data_2d = arr[b_idx]
    elif layer_id == "temporal_image_b" and len(input_files) >= 2:
        arr2, _ = RasterInspector.read_as_array(input_files[1])
        data_2d = arr2[0] if arr2.ndim == 3 else arr2
    elif layer_id == "ndvi":
        res = SpectralIndexEngine.compute_ndvi(arr, meta)
        if res.available and res.raw_array is not None:
            data_2d = res.raw_array
            units = "Index [-1, 1]"
    elif layer_id == "ndwi":
        res = SpectralIndexEngine.compute_ndwi(arr, meta)
        if res.available and res.raw_array is not None:
            data_2d = res.raw_array
            units = "Index [-1, 1]"
    elif layer_id == "change_probability_heatmap":
        prob_path = job_dir / "masks" / "change_probability.npy"
        if prob_path.exists():
            data_2d = np.load(str(prob_path))
            units = "Probability [0.0 - 1.0]"
    elif layer_id in ["change_raw_mask", "change_filtered_mask", "change_binary_mask"]:
        fname = "change_filtered_mask.png" if "filtered" in layer_id else ("change_raw_mask.png" if "raw" in layer_id else "change_mask.png")
        mask_file = job_dir / "masks" / fname
        if not mask_file.exists():
            mask_file = job_dir / "masks" / "change_mask.png"
        if mask_file.exists():
            data_2d = (np.array(Image.open(mask_file).convert("L")) > 0).astype(np.float32)
            units = "Discrete Binary State"

    if data_2d is None:
        data_2d = arr[0] if arr.ndim == 3 else arr

    hist = InspectorEngine.compute_histogram(data_2d, num_bins=50, units=units)
    return hist


@router.get("/analysis/{job_id}/export/{layer_id}")
async def export_layer(job_id: str, layer_id: str, format: str = "png"):
    """
    Exports visualization layer in PNG (with legend), GeoTIFF, or GeoJSON.
    """
    job_dir = artifact_manager.get_job_dir(job_id)
    vis_dir = job_dir / "visualizations"
    vis_dir.mkdir(parents=True, exist_ok=True)

    input_dir = job_dir / "input"
    input_files = sorted([f for f in input_dir.iterdir() if f.is_file() and not f.name.endswith(".json")]) if input_dir.exists() else []
    if not input_files:
        raise ArtifactNotFoundError("input_imagery", message="No input imagery found for export.", details={"job_id": job_id})

    arr, meta = RasterInspector.read_as_array(input_files[0])

    if format.lower() == "png":
        layer_png = vis_dir / f"{layer_id}.png"
        legend_png = vis_dir / f"{layer_id}_legend.png"
        export_out = vis_dir / f"{job_id}_{layer_id}_export.png"

        if not layer_png.exists():
            await get_visualization_image(job_id, layer_id)

        layer_img = Image.open(layer_png)
        legend_img = Image.open(legend_png) if legend_png.exists() else None

        layer_meta = LayerMetadata(
            layer_id=layer_id,
            layer_type=VisualizationType.SINGLE_BAND,
            title=f"SatQuery Export — {layer_id.upper()}",
            provenance=LayerProvenance.DERIVED_INDEX if "nd" in layer_id else LayerProvenance.SOURCE_DATA,
            units="Scientific Units"
        )
        out_path = ExportEngine.export_png_with_legend(layer_img, layer_meta, legend_img, export_out)
        return FileResponse(
            path=str(out_path),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{job_id}_{layer_id}.png"'}
        )

    elif format.lower() in ["tif", "tiff", "geotiff"]:
        export_out = vis_dir / f"{job_id}_{layer_id}.tif"
        data_to_export = arr[0] if arr.ndim == 3 else arr
        if layer_id == "ndvi":
            res = SpectralIndexEngine.compute_ndvi(arr, meta)
            if res.available and res.raw_array is not None:
                data_to_export = res.raw_array
        out_path = ExportEngine.export_geotiff(data_to_export, meta, export_out)
        return FileResponse(
            path=str(out_path),
            media_type="image/tiff",
            headers={"Content-Disposition": f'attachment; filename="{job_id}_{layer_id}.tif"'}
        )

    elif format.lower() in ["geojson", "json"]:
        export_out = vis_dir / f"{job_id}_{layer_id}.geojson"
        mask_files = list((job_dir / "masks").glob("*.png"))
        if not mask_files:
            raise VisualizationNotAvailableError(layer_id=layer_id, message="GeoJSON export requires segmented polygon mask.", details={"job_id": job_id})
        m_img = Image.open(mask_files[0]).convert("L")
        bin_mask = (np.array(m_img) > 0).astype(np.uint8)
        out_path = ExportEngine.export_geojson_mask(bin_mask, meta, export_out)
        return FileResponse(
            path=str(out_path),
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="{job_id}_{layer_id}.geojson"'}
        )
    else:
        raise InvalidRequestError(f"Unsupported export format '{format}'. Use 'png', 'geotiff', or 'geojson'.", details={"job_id": job_id})
