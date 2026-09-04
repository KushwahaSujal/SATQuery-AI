# SatQuery AI — Frontend API Contract Specification
**Document Version**: 2.0.0  
**Status**: Authoritative Reference  
**Last Updated**: September 2026  
**Backend Base URL**: `http://localhost:8000/api` (Development) / `/api` (Production Proxy)

---

## 1. Architectural Principles & Scientific Integrity

1. **Deterministic Dual-Key Compatibility**:
   - `job_id` and `request_id` are interchangeable aliases and always synchronized.
   - `workflow` and `workflow_id` are interchangeable aliases.
   - `trace` and `execution_trace` are interchangeable aliases.
2. **Scientific Grounding & Zero Fabrication**:
   - No fake bounding boxes, simulated masks, or synthetic predictions.
   - **V4 Reasoner** is a deterministic query-aware spatial/relational ranking and filtering algorithm, **never** represented as a neural network.
   - Grounding DINO detection confidence is reported as detection score, **not** grounding accuracy.
   - SAM 2.1 mask stability score is reported as SAM 2 score, **not** ground-truth IoU.
   - ChangeFormer continuous change probability maps ($0.0 \dots 1.0$) and discrete binary change masks are derived directly from model tensor outputs.
3. **Structured JSON-Only Errors**:
   - All HTTP error responses adhere strictly to the JSON schema:
     ```json
     {
       "error": {
         "code": "<EXPLICIT_ERROR_CODE>",
         "message": "<Human-readable diagnostic description>",
         "details": {},
         "job_id": "<UUID or null>"
       }
     }
     ```
   - No plain-text or raw HTML error responses are returned.

---

## 2. Model Lifecycle & Inventory

### `GET /api/models`
Retrieves live runtime availability and memory state of all models without force-loading heavy weights.

- **Method**: `GET`
- **Query Parameters**: None
- **Response Status**: `200 OK`
- **Lifecycle States**:
  - `NOT_CONFIGURED`: Checkpoint file or adapter missing on host.
  - `AVAILABLE`: Checkpoint verified on disk; model ready to load on demand.
  - `LOADED`: Model weights currently resident in GPU/CPU memory.
  - `FAILED`: Model initialization or weight loading failed.

#### Example Response
```json
{
  "models": [
    {
      "name": "GeoChat",
      "version": "7B-v1.5",
      "task": "single_image_vqa",
      "supported_tasks": ["vqa", "image_description", "scene_interpretation"],
      "supported_modalities": ["optical_rgb", "multispectral", "sar"],
      "input_count": 1,
      "input_relationship": "single",
      "checkpoint_path": "checkpoints/geochat/geochat_7b.pt",
      "available": true,
      "loaded": false,
      "device": "cuda:0",
      "precision": "float16",
      "model_id": "geochat_7b_v1_5",
      "status": "AVAILABLE"
    },
    {
      "name": "Grounding DINO",
      "version": "1.0",
      "task": "grounding",
      "supported_tasks": ["object_grounding", "zero_shot_detection"],
      "supported_modalities": ["optical_rgb"],
      "input_count": 1,
      "input_relationship": "single",
      "checkpoint_path": "checkpoints/grounding_dino/groundingdino_swint_ogc.pth",
      "available": true,
      "loaded": false,
      "device": "cuda:0",
      "precision": "float32",
      "model_id": "grounding_dino_swin_t",
      "status": "AVAILABLE"
    },
    {
      "name": "V4 reasoning",
      "version": "4.0",
      "task": "grounding_reasoning",
      "supported_tasks": ["spatial_grounding_reasoning", "referral_ranking", "relational_filtering"],
      "supported_modalities": ["optical_rgb"],
      "input_count": 1,
      "input_relationship": "single",
      "checkpoint_path": null,
      "available": true,
      "loaded": true,
      "device": "cpu",
      "precision": "float32",
      "model_id": "v4_spatial_reasoner",
      "status": "AVAILABLE"
    },
    {
      "name": "SAM 2.1",
      "version": "2.1",
      "task": "segmentation",
      "supported_tasks": ["promptable_segmentation", "box_to_mask"],
      "supported_modalities": ["optical_rgb"],
      "input_count": 1,
      "input_relationship": "single",
      "checkpoint_path": "checkpoints/sam2/sam2.1_hiera_large.pt",
      "available": true,
      "loaded": false,
      "device": "cuda:0",
      "precision": "float32",
      "model_id": "sam2_hiera_large",
      "status": "AVAILABLE"
    },
    {
      "name": "ChangeFormer",
      "version": "6.0",
      "task": "temporal_change_detection",
      "supported_tasks": ["bi_temporal_change", "damage_assessment"],
      "supported_modalities": ["optical_rgb"],
      "input_count": 2,
      "input_relationship": "temporal_pair",
      "checkpoint_path": "checkpoints/changeformer/changeformer_v6.pth",
      "available": true,
      "loaded": false,
      "device": "cuda:0",
      "precision": "float32",
      "model_id": "changeformer_v6",
      "status": "AVAILABLE"
    },
    {
      "name": "CDVQA",
      "version": "1.0",
      "task": "temporal_vqa",
      "supported_tasks": ["temporal_change_vqa", "bi_temporal_qa"],
      "supported_modalities": ["optical_rgb"],
      "input_count": 2,
      "input_relationship": "temporal_pair",
      "checkpoint_path": "checkpoints/cdvqa/cdvqa_v1.pth",
      "available": true,
      "loaded": false,
      "device": "cuda:0",
      "precision": "float32",
      "model_id": "cdvqa_v1",
      "status": "AVAILABLE"
    }
  ]
}
```

---

## 3. Ingestion & Analysis Workflows

### 3.1 Upload Files
#### `POST /api/upload`
Uploads raw satellite rasters (GeoTIFF, TIFF, PNG, JPEG) and inspects GDAL/rasterio metadata, modality, CRS, bounds, and resolution.

- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `files`: One or more binary raster files.
  - `request_id` (optional): Client-supplied job ID UUID string.
- **Response Status**: `200 OK`

```json
{
  "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "uploaded_files": ["t1_beirut_2020.tif", "t2_beirut_2020.tif"],
  "metadata": [
    {
      "filename": "t1_beirut_2020.tif",
      "format": "GeoTIFF",
      "width": 1024,
      "height": 1024,
      "bands": 3,
      "dtype": "uint8",
      "crs": "EPSG:32636",
      "bounds": [35.512, 33.895, 35.532, 33.915],
      "transform": [0.5, 0.0, 35.512, 0.0, -0.5, 33.915],
      "resolution": [0.5, 0.5],
      "nodata": null,
      "band_descriptions": ["Red", "Green", "Blue"],
      "tags": {},
      "detected_modality": "optical_rgb",
      "modality_confidence": 0.98,
      "modality_reason": "3 bands with standard RGB radiometric values.",
      "preview_url": "/api/artifacts/3fa85f64-5717-4562-b3fc-2c963f66afa6/previews/t1_beirut_2020_preview.png"
    }
  ]
}
```

---

### 3.2 Execute Analysis
#### `POST /api/analyze`
Dispatches the query through the Agent Orchestration Router into the dedicated workflow.

- **Method**: `POST`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "query": "Identify all buildings damaged between image A and image B",
    "image_filenames": ["t1_beirut_2020.tif", "t2_beirut_2020.tif"],
    "parameters": {
      "threshold": 0.5,
      "min_region_size": 25
    }
  }
  ```

- **Routing Logic Matrix**:
  | Input Modality / Count | Query Intent | Routed Workflow | Models Used |
  | :--- | :--- | :--- | :--- |
  | Single Image | Natural Language VQA / Description | Single-Image VQA | GeoChat 7B |
  | Single Image | Localization / Grounding ("locate", "box", "highlight") | Single-Image Grounding | Grounding DINO + V4 Reasoner + SAM 2.1 |
  | Bi-Temporal Pair | Change Analysis ("detect changes", "what changed") | Bi-Temporal Change Detection | ChangeFormerV6 |
  | Bi-Temporal Pair | Change VQA ("compare", "how many buildings were destroyed") | Bi-Temporal Change VQA | ChangeFormerV6 + CDVQA |

- **Response Body**:
```json
{
  "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "COMPLETED",
  "task": "bi_temporal_change_detection",
  "workflow_id": "workflow_change_detection",
  "workflow": "workflow_change_detection",
  "workflow_reason": "Bi-temporal image pair provided with change detection query.",
  "answer": "Detected 43 change clusters comprising 152,400 m² of modified structural surface area.",
  "confidence": 0.912,
  "models_used": ["changeformer"],
  "parameters": {
    "threshold": 0.5,
    "min_region_size": 25
  },
  "evidence": {
    "spatial": {
      "boxes": [],
      "has_mask": true,
      "mask_path": "masks/change_mask.png",
      "geojson_path": "vectors/change.geojson",
      "overlay_path": "overlays/change_overlay.png",
      "statistics": {
        "changed_pixels": 609600,
        "raw_changed_pixels": 612400,
        "total_valid_pixels": 1048576,
        "change_ratio": 0.5814,
        "threshold": 0.5,
        "region_count": 43,
        "quality_status": "PASS",
        "quality_warning": null,
        "estimated_area_sq_m": 152400.0,
        "estimated_area_sq_km": 0.1524,
        "area_unit": "sq_meters",
        "metric_crs": "EPSG:32636"
      },
      "candidate_boxes": [],
      "candidate_scores": [],
      "selected_box": null,
      "reasoning_strategy": null,
      "reasoning_score": null,
      "sam2_artifact": null,
      "sam2_score": null
    },
    "consistency": [
      {
        "signal_name": "spatial_continuity",
        "passed": true,
        "score": 0.94,
        "details": "Connected components show high morphological consistency."
      }
    ],
    "summary": "Detected 43 change clusters comprising 152,400 m² of modified structural surface area.",
    "metadata": {
      "is_georeferenced": true,
      "source_crs": "EPSG:32636",
      "target_crs": "EPSG:4326"
    }
  },
  "execution_trace": [
    {
      "step_name": "pair_registration_validation",
      "status": "SUCCESS",
      "model_name": null,
      "duration_seconds": 0.042,
      "metadata": {"alignment": "perfect", "crs_match": true}
    },
    {
      "step_name": "changeformer_inference",
      "status": "SUCCESS",
      "model_name": "ChangeFormerV6",
      "duration_seconds": 0.814,
      "metadata": {"input_size": [1024, 1024]}
    }
  ],
  "trace": [
    {
      "step_name": "pair_registration_validation",
      "status": "SUCCESS",
      "model_name": null,
      "duration_seconds": 0.042,
      "metadata": {"alignment": "perfect", "crs_match": true}
    },
    {
      "step_name": "changeformer_inference",
      "status": "SUCCESS",
      "model_name": "ChangeFormerV6",
      "duration_seconds": 0.814,
      "metadata": {"input_size": [1024, 1024]}
    }
  ],
  "warnings": [],
  "errors": [],
  "artifacts": {
    "masks": ["masks/change_mask.png", "masks/change_probability.npy"],
    "overlays": ["overlays/change_overlay.png"],
    "vectors": ["vectors/change.geojson"]
  },
  "visualizations": [
    {
      "layer_id": "true_color",
      "layer_type": "TRUE_COLOR",
      "title": "True Color / RGB",
      "provenance": "SOURCE_DATA",
      "available": true,
      "artifact_url": "/api/analysis/3fa85f64-5717-4562-b3fc-2c963f66afa6/visualizations/true_color",
      "mime_type": "image/png",
      "units": "DN"
    },
    {
      "layer_id": "change_probability_heatmap",
      "layer_type": "PROBABILITY_HEATMAP",
      "title": "ChangeFormer — Change Probability Heatmap",
      "provenance": "MODEL_PROBABILITY",
      "source_model": "ChangeFormerV6",
      "available": true,
      "artifact_url": "/api/analysis/3fa85f64-5717-4562-b3fc-2c963f66afa6/visualizations/change_probability_heatmap",
      "legend_url": "/api/analysis/3fa85f64-5717-4562-b3fc-2c963f66afa6/visualizations/change_probability_heatmap/legend",
      "mime_type": "image/png",
      "units": "Probability [0.0 - 1.0]"
    }
  ]
}
```

---

## 4. Visual Analytics & Scientific Inspection API

### 4.1 Discover Layers
#### `GET /api/analysis/{job_id}/layers`
Returns all verified visual analytics layers for the job.

- **Supported Layer Types (`VisualizationType`)**:
  1. `TRUE_COLOR`: Standard RGB composite using red, green, blue channels.
  2. `GRAYSCALE`: Panchromatic single-channel stretch.
  3. `FALSE_COLOR`: Near-Infrared multispectral composite (e.g. NIR/Red/Green).
  4. `SINGLE_BAND`: Individual spectral band visualized with colormap.
  5. `BAND_DIFFERENCE`: Spectral difference between channels or temporal epochs.
  6. `SPECTRAL_INDEX`: Normalized indices (`ndvi`, `ndwi`, `ndbi`).
  7. `PROBABILITY_HEATMAP`: Continuous model posterior probability ($0.0 \dots 1.0$) with turbo colormap.
  8. `BINARY_MASK`: Discrete classification mask ($0 / 1$).
  9. `CONFIDENCE_MAP`: Spatial model confidence distribution.
  10. `BBOX_OVERLAY`: Candidate and target bounding box geometry overlay.
  11. `SEGMENTATION_OVERLAY`: SAM 2.1 alpha mask overlay on source imagery.
  12. `TEMPORAL_CHANGE_OVERLAY`: ChangeFormer bi-temporal change highlights.
  13. `SAR_POLARIZATION`: Radar backscatter amplitude ($VV$, $VH$, $HH$, $HV$).
  14. `OPTICAL_SAR_COMPARISON`: Co-registered optical vs SAR split view.
  15. `VIDEO_FLAG_REGION`: Moment keyframe event flag highlight.
  16. `REGION_MAP`: Morphologically labeled connected component polygon map.

- **Provenance Categories (`LayerProvenance`)**:
  - `SOURCE_DATA`: Directly rendered from raw sensor DNs.
  - `DERIVED_INDEX`: Mathematically computed spectral index.
  - `MODEL_OUTPUT`: Discrete model prediction mask or bounding box.
  - `MODEL_PROBABILITY`: Continuous tensor probability map.
  - `HEURISTIC_ANALYSIS`: Post-processed spatial component reasoning.

---

### 4.2 Pixel Inspector
#### `POST /api/analysis/{job_id}/inspect-pixel`
Inspects authentic scientific band DNs, geographic coordinates, derived index values, and model state for a single pixel location.

- **Request Body**:
  ```json
  {
    "col": 412,
    "row": 650
  }
  ```
- **Response**:
  ```json
  {
    "row": 650,
    "col": 412,
    "coordinates": [35.52184, 33.90112],
    "CRS": "EPSG:4326",
    "crs": "EPSG:4326",
    "band_values": {
      "Band_1 (Red)": 142.0,
      "Band_2 (Green)": 118.0,
      "Band_3 (Blue)": 94.0
    },
    "indices": {
      "NDVI": 0.4125
    },
    "prediction": 1,
    "probability": 0.8942,
    "pixel": {
      "col": 412,
      "row": 650
    },
    "geographic_coordinates": {
      "x_coord": 35.52184,
      "y_coord": 33.90112,
      "crs": "EPSG:4326"
    },
    "derived_indices": {
      "NDVI": 0.4125
    },
    "model_prediction": {
      "probability": 0.8942,
      "prediction_class": 1,
      "status": "Changed"
    },
    "raw_values_preserved": true
  }
  ```

---

### 4.3 Distribution Histogram
#### `GET /api/analysis/{job_id}/histogram/{layer_id}`
Computes an authentic 50-bin distribution histogram and summary statistics over valid, non-null raster pixels.

- **Response**:
  ```json
  {
    "total_pixels": 1048576,
    "units": "Probability [0.0 - 1.0]",
    "counts": [480200, 12050, 8900, 4200, 3100, "...50 integer bin counts..."],
    "min": 0.0,
    "max": 0.9984,
    "mean": 0.3142,
    "median": 0.1250,
    "std": 0.3412,
    "p2": 0.0012,
    "p25": 0.0450,
    "p50": 0.1250,
    "p75": 0.7420,
    "p98": 0.9850,
    "percentiles": {
      "p2": 0.0012,
      "p25": 0.0450,
      "p50": 0.1250,
      "p75": 0.7420,
      "p98": 0.9850
    },
    "bins": [
      {"range_start": 0.0, "range_end": 0.02, "count": 480200},
      {"range_start": 0.02, "range_end": 0.04, "count": 12050}
    ]
  }
  ```

---

### 4.4 Data Export
#### `GET /api/analysis/{job_id}/export/{layer_id}?format={png|geotiff|geojson}`

- **Supported Formats**:
  - `format=png`: High-resolution PNG image with attached scientific legend and provenance metadata banner.
  - `format=geotiff` (or `tif`): Single-band or multi-band GeoTIFF preserving source CRS, affine geotransform, bounding box, dimensions, and NoData values.
  - `format=geojson`: GeoJSON FeatureCollection of segmented vector polygons in `EPSG:4326` coordinate reference system.

---

## 5. Video Intelligence API

### 5.1 Video Ingestion
#### `POST /api/video/upload`
Uploads video file (MP4, AVI, MOV, MKV) and extracts stream metadata.

- **Form Fields**: `file` (Video binary file)
- **Response**:
  ```json
  {
    "job_id": "video_job_8f21e",
    "filename": "surveillance_pass.mp4",
    "video_metadata": {
      "filename": "surveillance_pass.mp4",
      "duration_sec": 45.2,
      "fps": 30.0,
      "width": 1920,
      "height": 1080,
      "frame_count": 1356,
      "codec": "h264"
    }
  }
  ```

### 5.2 Video Query & Analysis
#### `POST /api/video/analyze`
Executes intelligent frame sampling, zero-shot Grounding DINO detection, SAM 2.1 mask segmentation, and temporal event aggregation.

- **Request Body**:
  ```json
  {
    "job_id": "video_job_8f21e",
    "video_filename": "surveillance_pass.mp4",
    "query": "Track all military transport vehicles moving across the runway",
    "sampling_fps": 2.0,
    "confidence_threshold": 0.4
  }
  ```

### 5.3 Video Results & Stream
- `GET /api/video/{job_id}` & `GET /api/video/{job_id}/results`: Retrieves aggregated event flags and keyframe overlays.
- `GET /api/video/{job_id}/stream`: Serves HTTP byte-range video streaming for browser playback.

---

## 6. Standardized Error Codes & Status Matrix

| HTTP Status | Error Code (`code`) | Diagnostic Condition |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_REQUEST` | Malformed JSON, missing mandatory query parameter, or pixel coordinate out of bounds. |
| `400 Bad Request` | `INDEX_NOT_AVAILABLE` | Requested spectral index (e.g. NDVI) cannot be computed due to missing spectral bands (e.g. NIR missing). |
| `404 Not Found` | `JOB_NOT_FOUND` | Queried `job_id` does not exist in database or filesystem. |
| `404 Not Found` | `ARTIFACT_NOT_FOUND` | Image, mask, vector GeoJSON, or preview file is missing from job workspace. |
| `404 Not Found` | `VISUALIZATION_NOT_AVAILABLE`| Requested visualization layer was not generated for this job modality/workflow. |
| `404 Not Found` | `NO_RELEVANT_EVENTS_FOUND` | Video analysis detected no motion or targets matching the query string. |
| `415 Unsupported Media` | `UNSUPPORTED_MEDIA` | Uploaded file is not a supported raster or video container format. |
| `422 Unprocessable` | `INVALID_TEMPORAL_PAIR` | Bi-temporal image pair has mismatched dimensions, unalignable sensor modalities, or invalid metadata. |
| `422 Unprocessable` | `TEMPORAL_ALIGNMENT_REQUIRED` | Image pair lacks spatial overlap or coordinate reference system alignment. |
| `500 Server Error` | `MODEL_INFERENCE_ERROR` | Internal error or CUDA exception during PyTorch forward pass. |
| `503 Service Unavailable` | `MODEL_NOT_CONFIGURED` | Required model weights or checkpoint file is missing from host. |
| `503 Service Unavailable` | `DATABASE_UNAVAILABLE` | PostgreSQL database connection timeout or failure. |

---

## 7. Frontend Integration Checklist

- [x] **Single-Image VQA**: Call `POST /api/upload`, then `POST /api/analyze` with single filename. Render `answer`, `confidence`, and `visualizations`.
- [x] **Grounding**: Call `POST /api/analyze` with prompt containing referral/locational query. Render bounding boxes from `evidence.spatial.boxes` and mask overlays.
- [x] **Change Detection**: Call `POST /api/analyze` with two filenames. Render change statistics (`changed_pixels`, `change_ratio`, `estimated_area_sq_m`) and `change_overlay` layer.
- [x] **Layer Switcher**: Call `GET /api/analysis/{job_id}/layers` to populate interactive layer selector. Display `artifact_url` with optional `legend_url`.
- [x] **Interactive Pixel Inspector**: Listen for click events on imagery canvas, call `POST /api/analysis/{job_id}/inspect-pixel`, display top-level `band_values`, `indices`, `prediction`, and `probability`.
- [x] **Histogram Modal**: Call `GET /api/analysis/{job_id}/histogram/{layer_id}`, plot 50-bin bar chart using `bins` and percentile markers (`p2`, `p50`, `p98`).
- [x] **Multi-Format Export**: Provide download links to `/api/analysis/{job_id}/export/{layer_id}?format=png`, `geotiff`, and `geojson`.
- [x] **Video Intelligence**: Use `/api/video/upload`, `/api/video/analyze`, `/api/video/{job_id}/stream`, and `/api/video/{job_id}/results`.
