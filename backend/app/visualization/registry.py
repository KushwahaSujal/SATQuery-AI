"""
SatQuery AI — Visualization Registry & Layer Generator
Central registry determining supported visual analytics layers for a given job and its rasters/models.
Ensures zero-fabrication: only advertises layers that the source data or model execution actually supports.
"""
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np

from backend.app.geo.metadata import RasterMetadata
from backend.app.geo.raster import RasterInspector
from backend.app.visualization.provenance import LayerProvenance, VisualizationType, LayerMetadata
from backend.app.visualization.composites import CompositeRenderer
from backend.app.visualization.indices import SpectralIndexEngine
from backend.app.visualization.sar import SARVisualizationEngine
from backend.app.visualization.heatmaps import HeatmapEngine
from backend.app.visualization.comparison import ComparisonEngine
from backend.app.logging import logger


class VisualizationRegistry:
    """
    Discovers, generates, and serves visual analytics layers for SatQuery jobs.
    """

    @classmethod
    def discover_available_layers(
        cls,
        raster_metadata_list: Optional[List[RasterMetadata]] = None,
        model_results: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[LayerMetadata]:
        """
        Inspects input imagery metadata and model execution traces to determine
        all scientifically valid visualization layers.
        """
        if raster_metadata_list is None:
            raster_metadata_list = kwargs.get("metadata_list") or []

        request_id = kwargs.get("request_id")
        if model_results is None:
            ev = kwargs.get("evidence")
            ev_dict = ev.model_dump() if hasattr(ev, "model_dump") else (ev if isinstance(ev, dict) else {})
            model_results = {
                "models_used": kwargs.get("models_used", []),
                "task": kwargs.get("task", ""),
                "evidence": ev_dict
            }

        layers: List[LayerMetadata] = []

        if not raster_metadata_list:
            return layers

        primary_meta = raster_metadata_list[0]
        bands = primary_meta.bands

        # 1. True Color / RGB
        if bands >= 3:
            layers.append(LayerMetadata(
                layer_id="true_color",
                layer_type=VisualizationType.TRUE_COLOR,
                title="True Color / RGB",
                provenance=LayerProvenance.SOURCE_DATA,
                units="DN",
                crs=primary_meta.crs,
                bounds=primary_meta.bounds,
                resolution=primary_meta.resolution
            ))
        elif bands == 1:
            layers.append(LayerMetadata(
                layer_id="grayscale",
                layer_type=VisualizationType.GRAYSCALE,
                title="Panchromatic / Grayscale",
                provenance=LayerProvenance.SOURCE_DATA,
                units="DN",
                crs=primary_meta.crs,
                bounds=primary_meta.bounds
            ))

        # 2. Individual Bands
        for b_idx in range(bands):
            b_desc = primary_meta.band_descriptions[b_idx] if (primary_meta.band_descriptions and b_idx < len(primary_meta.band_descriptions)) else f"Band {b_idx + 1}"
            layers.append(LayerMetadata(
                layer_id=f"band_{b_idx + 1}",
                layer_type=VisualizationType.SINGLE_BAND,
                title=f"Single Band — {b_desc}",
                provenance=LayerProvenance.SOURCE_DATA,
                units="DN",
                colormap="viridis",
                crs=primary_meta.crs,
                bounds=primary_meta.bounds
            ))

        # 3. Multispectral False Color & Indices (Only if bands >= 4 or tagged)
        has_nir = False
        if primary_meta.band_descriptions:
            has_nir = any("nir" in d.lower() for d in primary_meta.band_descriptions)
        if bands >= 4 or has_nir:
            layers.append(LayerMetadata(
                layer_id="false_color_nir",
                layer_type=VisualizationType.FALSE_COLOR,
                title="False Color — NIR / Red / Green",
                provenance=LayerProvenance.DERIVED_INDEX,
                units="Composite Display",
                crs=primary_meta.crs,
                bounds=primary_meta.bounds
            ))
            layers.append(LayerMetadata(
                layer_id="ndvi",
                layer_type=VisualizationType.SPECTRAL_INDEX,
                title="NDVI — Normalized Difference Vegetation Index",
                provenance=LayerProvenance.DERIVED_INDEX,
                units="Index [-1.0, 1.0]",
                colormap="RdYlGn",
                crs=primary_meta.crs,
                bounds=primary_meta.bounds
            ))
            layers.append(LayerMetadata(
                layer_id="ndwi",
                layer_type=VisualizationType.SPECTRAL_INDEX,
                title="NDWI — Normalized Difference Water Index",
                provenance=LayerProvenance.DERIVED_INDEX,
                units="Index [-1.0, 1.0]",
                colormap="Blues",
                crs=primary_meta.crs,
                bounds=primary_meta.bounds
            ))

        # 4. SAR Polarizations
        if primary_meta.sensor and "SAR" in primary_meta.sensor.upper() or primary_meta.format in ["Sentinel-1", "SAR"]:
            layers.append(LayerMetadata(
                layer_id="sar_vv",
                layer_type=VisualizationType.SAR_POLARIZATION,
                title="SAR Backscatter — VV",
                provenance=LayerProvenance.SOURCE_DATA,
                units="Linear Intensity",
                colormap="gray"
            ))
            if bands >= 2:
                layers.append(LayerMetadata(
                    layer_id="sar_vh",
                    layer_type=VisualizationType.SAR_POLARIZATION,
                    title="SAR Backscatter — VH",
                    provenance=LayerProvenance.SOURCE_DATA,
                    units="Linear Intensity",
                    colormap="gray"
                ))
                layers.append(LayerMetadata(
                    layer_id="sar_dual_pol",
                    layer_type=VisualizationType.SAR_POLARIZATION,
                    title="SAR Dual-Pol Composite (VV / VH / Ratio)",
                    provenance=LayerProvenance.DERIVED_INDEX,
                    units="Composite Display"
                ))

        # 5. Multi-Image & Temporal Individual Epoch Layers
        if len(raster_metadata_list) >= 2:
            m1, m2 = raster_metadata_list[0], raster_metadata_list[1]
            layers.append(LayerMetadata(
                layer_id="temporal_image_a",
                layer_type=VisualizationType.TRUE_COLOR,
                title=f"Earlier Image A (T1) — {m1.filename}",
                provenance=LayerProvenance.SOURCE_DATA,
                units="DN",
                crs=m1.crs,
                bounds=m1.bounds,
                resolution=m1.resolution
            ))
            layers.append(LayerMetadata(
                layer_id="temporal_image_b",
                layer_type=VisualizationType.TRUE_COLOR,
                title=f"Later Image B (T2) — {m2.filename}",
                provenance=LayerProvenance.SOURCE_DATA,
                units="DN",
                crs=m2.crs,
                bounds=m2.bounds,
                resolution=m2.resolution
            ))

        # 6. Model Evidence Layers
        if model_results:
            models_used = [str(m).lower() for m in model_results.get("models_used", [])]
            task = str(model_results.get("task", "")).lower()
            ev_spatial = model_results.get("evidence", {}).get("spatial", {})
            has_mask = bool(ev_spatial.get("has_mask", False))
            boxes = ev_spatial.get("boxes", [])

            # Change detection layers (ChangeFormer)
            is_change_task = (
                "changeformer" in models_used or
                "changeformer" in model_results or
                "change_probability" in model_results or
                "change" in task or
                (has_mask and "change" in task)
            )
            if is_change_task:
                layers.append(LayerMetadata(
                    layer_id="change_probability_heatmap",
                    layer_type=VisualizationType.PROBABILITY_HEATMAP,
                    title="ChangeFormer — Change Probability Heatmap",
                    provenance=LayerProvenance.MODEL_PROBABILITY,
                    source_model="ChangeFormerV6",
                    units="Probability [0.0 - 1.0]",
                    colormap="turbo",
                    display_stretch="Continuous [0.0, 1.0]"
                ))
                layers.append(LayerMetadata(
                    layer_id="change_binary_mask",
                    layer_type=VisualizationType.BINARY_MASK,
                    title="ChangeFormer — Binary Change Mask",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="ChangeFormerV6",
                    units="Discrete State {0, 1}"
                ))
                layers.append(LayerMetadata(
                    layer_id="change_raw_mask",
                    layer_type=VisualizationType.BINARY_MASK,
                    title="ChangeFormer — Raw Binary Change Mask",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="ChangeFormerV6",
                    units="Discrete State {0, 1}"
                ))
                layers.append(LayerMetadata(
                    layer_id="change_filtered_mask",
                    layer_type=VisualizationType.BINARY_MASK,
                    title="ChangeFormer — Post-Processed Filtered Mask",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="ChangeFormerV6",
                    units="Discrete State {0, 1}"
                ))
                layers.append(LayerMetadata(
                    layer_id="change_overlay",
                    layer_type=VisualizationType.TEMPORAL_CHANGE_OVERLAY,
                    title="ChangeFormer — Temporal Change Overlay",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="ChangeFormerV6",
                    units="Alpha Overlay"
                ))
                layers.append(LayerMetadata(
                    layer_id="change_regions",
                    layer_type=VisualizationType.REGION_MAP,
                    title="ChangeFormer — Connected Change Regions Map",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="ChangeFormerV6",
                    units="Identified Component Polygons"
                ))

            # Grounding & Segmentation layers (Grounding DINO + V4 + SAM 2)
            is_grounding_task = (
                "grounding_dino" in models_used or
                "grounding_dino" in model_results or
                "boxes" in model_results or
                "sam2" in models_used or
                "sam2" in model_results or
                "grounding" in task or
                len(boxes) > 0
            )
            if is_grounding_task:
                layers.append(LayerMetadata(
                    layer_id="grounding_bboxes",
                    layer_type=VisualizationType.BBOX_OVERLAY,
                    title="Grounding DINO + V4 — Candidate & Target Boxes",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="Grounding DINO / V4 Reasoner",
                    units="Vector Coordinates [xyxy]"
                ))
                if "sam2" in models_used or has_mask:
                    layers.append(LayerMetadata(
                        layer_id="sam2_segmentation_overlay",
                        layer_type=VisualizationType.SEGMENTATION_OVERLAY,
                        title="SAM 2.1 — High-Resolution Segmentation Mask",
                        provenance=LayerProvenance.MODEL_OUTPUT,
                        source_model="SAM 2.1 Hiera",
                        units="Alpha Mask Overlay"
                    ))
                layers.append(LayerMetadata(
                    layer_id="grounding_overlay",
                    layer_type=VisualizationType.SEGMENTATION_OVERLAY,
                    title="Grounding Evidence Overlay",
                    provenance=LayerProvenance.MODEL_OUTPUT,
                    source_model="Grounding DINO + SAM 2.1",
                    units="Visual Evidence Overlay"
                ))

        # 7. Multi-Modal Comparison (if optical + SAR or T1 + T2)
        if len(raster_metadata_list) >= 2:
            m1, m2 = raster_metadata_list[0], raster_metadata_list[1]
            co_reg, reason = ComparisonEngine.verify_co_registration(m1, m2)
            layers.append(LayerMetadata(
                layer_id="comparison_split",
                layer_type=VisualizationType.OPTICAL_SAR_COMPARISON,
                title=f"Comparison: {m1.filename} vs {m2.filename}",
                provenance=LayerProvenance.SOURCE_DATA,
                co_registered=co_reg,
                raw_stats={"alignment_status": reason}
            ))

        if request_id:
            for layer in layers:
                layer.artifact_url = f"/api/analysis/{request_id}/visualizations/{layer.layer_id}"
                if layer.layer_type in [
                    VisualizationType.SINGLE_BAND,
                    VisualizationType.SPECTRAL_INDEX,
                    VisualizationType.SAR_POLARIZATION,
                    VisualizationType.PROBABILITY_HEATMAP
                ]:
                    layer.legend_url = f"/api/analysis/{request_id}/visualizations/{layer.layer_id}/legend"

        return layers
