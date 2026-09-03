from typing import Any, Dict, List, Optional
from pathlib import Path
import numpy as np
from PIL import Image

from backend.app.schemas.evidence import (
    EvidencePackage,
    SpatialEvidence,
    BoundingBoxEvidence,
    AreaStatistics,
    ConsistencySignal,
)
from backend.app.geo.metadata import RasterMetadata
from backend.app.evidence.boxes import normalize_box
from backend.app.evidence.masks import save_mask_as_geotiff
from backend.app.geo.vectors import mask_to_geojson, save_geojson
from backend.app.evidence.statistics import calculate_area_statistics
from backend.app.artifacts.manager import artifact_manager


class EvidenceFusionEngine:
    """
    Fuses multi-source spatial, statistical, and consistency evidence into a single structured EvidencePackage.
    """
    @staticmethod
    def package(
        boxes: Optional[List[BoundingBoxEvidence]] = None,
        has_mask: bool = False,
        mask_path: Optional[str] = None,
        geojson_path: Optional[str] = None,
        overlay_path: Optional[str] = None,
        statistics: Optional[AreaStatistics] = None,
        geojson_data: Optional[Dict[str, Any]] = None,
        consistency_signals: Optional[List[ConsistencySignal]] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        candidate_boxes: Optional[List[List[float]]] = None,
        candidate_scores: Optional[List[float]] = None,
        selected_box: Optional[List[float]] = None,
        reasoning_strategy: Optional[str] = None,
        reasoning_score: Optional[float] = None,
        sam2_artifact: Optional[str] = None,
        sam2_score: Optional[float] = None
    ) -> EvidencePackage:
        spatial = SpatialEvidence(
            boxes=boxes or [],
            has_mask=has_mask,
            mask_path=mask_path,
            geojson_path=geojson_path,
            overlay_path=overlay_path,
            statistics=statistics,
            geojson_data=geojson_data,
            candidate_boxes=candidate_boxes or [],
            candidate_scores=candidate_scores or [],
            selected_box=selected_box,
            reasoning_strategy=reasoning_strategy,
            reasoning_score=reasoning_score,
            sam2_artifact=sam2_artifact,
            sam2_score=sam2_score
        )

        return EvidencePackage(
            spatial=spatial,
            consistency=consistency_signals or [],
            summary=summary,
            metadata=metadata or {}
        )

    @classmethod
    def build_grounding_evidence(
        cls,
        selected_box: Optional[List[float]],
        segmentation_mask: Optional[np.ndarray],
        metadata: Optional[RasterMetadata],
        request_id: Optional[str] = None,
        target_category: str = "detected_object",
        grounding_score: Optional[float] = None,
        sam2_score: Optional[float] = None,
        summary: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> EvidencePackage:
        """
        Connects grounding workflow output to the evidence engine:
        - For georeferenced imagery:
          * transforms image-space bounding box into map coordinates (EPSG:4326);
          * transforms segmentation mask into geospatial polygons in EPSG:4326;
          * produces GeoJSON with EPSG:4326 coordinates and preserves source CRS metadata;
          * never assumes pixel coordinates are geographic coordinates.
        - For non-georeferenced benchmark PNG/JPEG:
          * keeps evidence strictly in image coordinates;
          * sets geo_bounds to None;
          * sets coordinate_space to 'image_coordinates';
          * never assumes pixel coordinates are geographic coordinates.
        """
        is_geo = bool(metadata and metadata.is_georeferenced)
        boxes: List[BoundingBoxEvidence] = []

        # 1. Bounding Boxes
        if selected_box:
            img_w = metadata.width if (metadata and metadata.width) else 256
            img_h = metadata.height if (metadata and metadata.height) else 256
            norm_box = normalize_box(
                box=selected_box,
                img_width=img_w,
                img_height=img_h,
                label=target_category,
                score=grounding_score,
                metadata=metadata
            )
            boxes.append(norm_box)

        # 2. Segmentation Mask, Geospatial Polygons & Statistics
        has_mask = False
        mask_path: Optional[str] = None
        geojson_path: Optional[str] = None
        geojson_data: Optional[Dict[str, Any]] = None
        stats: Optional[AreaStatistics] = None

        if segmentation_mask is not None:
            has_mask = True
            stats = calculate_area_statistics(segmentation_mask, metadata=metadata)
            geojson_data = mask_to_geojson(
                binary_mask=segmentation_mask,
                metadata=metadata,
                target_crs="EPSG:4326"
            )

            # Persist artifacts if a job request_id is provided
            if request_id:
                dirs = artifact_manager.init_job_workspace(request_id)
                if is_geo:
                    m_path = dirs["masks"] / "grounding_mask.tif"
                    save_mask_as_geotiff(segmentation_mask, m_path, metadata=metadata)
                else:
                    m_path = dirs["masks"] / "grounding_mask.png"
                    uint8_mask = (segmentation_mask > 0).astype(np.uint8) * 255
                    Image.fromarray(uint8_mask).save(m_path)
                mask_path = str(m_path)

                gj_path = dirs["vectors"] / "grounding.geojson"
                save_geojson(geojson_data, gj_path)
                geojson_path = str(gj_path)

        meta_dict = extra_metadata.copy() if extra_metadata else {}
        meta_dict.update({
            "is_georeferenced": is_geo,
            "source_crs": metadata.crs if is_geo else None,
            "target_crs": "EPSG:4326" if is_geo else "image_coordinates",
            "coordinate_space": "geographic" if is_geo else "image_coordinates",
            "grounding_score": grounding_score,
            "sam2_score": sam2_score,
            "selected_box": selected_box,
            "sam2_artifact": mask_path
        })

        cand_boxes = meta_dict.get("candidate_boxes", [])
        cand_scores = meta_dict.get("candidate_scores", [])
        strat = meta_dict.get("strategy")
        r_score = meta_dict.get("reasoning_score")

        return cls.package(
            boxes=boxes,
            has_mask=has_mask,
            mask_path=mask_path,
            geojson_path=geojson_path,
            statistics=stats,
            geojson_data=geojson_data,
            summary=summary,
            metadata=meta_dict,
            candidate_boxes=cand_boxes,
            candidate_scores=cand_scores,
            selected_box=selected_box,
            reasoning_strategy=strat,
            reasoning_score=r_score,
            sam2_artifact=mask_path,
            sam2_score=sam2_score
        )
