// Backend task enum (lowercase, matches backend/app/schemas/agent.py)
export type TaskType =
  | "single_image_vqa"
  | "single_image_caption"
  | "single_image_grounding"
  | "bi_temporal_change"
  | "bi_temporal_change_vqa"
  | "optical_sar_analysis"
  | "video_grounding"
  | "video_grounding_tracking"
  | "video_vqa"
  | "video_change"
  | "unsupported";

// Backend job status enum (matches backend/app/schemas/agent.py)
export type JobStatus =
  | "QUEUED"
  | "VALIDATING"
  | "PLANNING"
  | "RUNNING"
  | "GENERATING_EVIDENCE"
  | "COMPLETED"
  | "FAILED"
  | "CREATED"
  | "UPLOADED";

export type ModelLifecycle =
  | "NOT_CONFIGURED"
  | "AVAILABLE"
  | "LOADED"
  | "FAILED";

export type LayerProvenance =
  | "SOURCE_DATA"
  | "DERIVED_INDEX"
  | "MODEL_OUTPUT"
  | "MODEL_PROBABILITY";

export type ExportFormat = "png" | "geotiff" | "geojson";

export interface HealthResponse {
  api: "online" | "offline" | "degraded";
  database: "connected" | "disconnected" | "unknown";
  storage?: "available" | "unavailable" | "unknown";
  models_ready?: number;
  models_total?: number;
  active_requests?: number;
  recent_errors?: string[];
  version?: string;
  environment?: string;
  device?: string;
  models_available?: Record<string, boolean>;
  database_connected?: boolean;
}

export interface ModelInfo {
  name: string;
  task: string;
  device?: string;
  status: ModelLifecycle;
  loaded?: boolean;
  description?: string;
  capabilities?: string[];
  available?: boolean;
  last_error?: string;
  validation_status?: string;
}

export interface UploadedRaster {
  id: string;
  request_id?: string;
  filename: string;
  width: number;
  height: number;
  bands: number;
  dtype: string;
  crs?: string;
  bounds?: [number, number, number, number];
  transform?: number[];
  resolution?: [number, number];
  modality?: string;
  modality_confidence?: number;
  preview_url?: string;
  georeferenced: boolean;
  valid_raster: boolean;
  temporal_role?: "T1" | "T2";
}

export interface UploadedVideo {
  id: string;
  request_id?: string;
  filename: string;
  duration_sec: number;
  fps: number;
  width: number;
  height: number;
  frames: number;
  codec?: string;
  preview_url?: string;
}

export interface AnalyzeRequest {
  query: string;
  raster_ids?: string[];
  image_filenames?: string[];
  request_id?: string;
  video_id?: string;
  task?: TaskType;
  params?: Record<string, unknown>;
}

// Backend trace step (matches backend/app/schemas/agent.py ExecutionStep)
export interface TraceStep {
  step: string;
  status: "success" | "warning" | "error" | "running" | "skipped";
  model?: string;
  tool?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  details?: string;
}

export interface EvidenceItem {
  id: string;
  label: string;
  kind: string;
  verified: boolean;
  artifact_path?: string;
  preview_url?: string;
  description?: string;
}

// Backend AreaStatistics (matches backend/app/schemas/evidence.py)
export interface AreaStatistics {
  changed_pixels: number;
  raw_changed_pixels?: number;
  total_valid_pixels: number;
  change_ratio: number;
  threshold: number;
  region_count: number;
  quality_status: string;
  quality_warning?: string;
  diagnostic_flags: string[];
  estimated_area_sq_m?: number;
  estimated_area_sq_km?: number;
  area_unit: string;
  metric_crs?: string;
}

// Backend BoundingBoxEvidence (matches backend/app/schemas/evidence.py)
export interface BoundingBoxEvidence {
  label: string;
  box_2d: number[];
  score?: number;
  geo_bounds?: number[];
  source_crs?: string;
  target_crs?: string;
  coordinate_space: string;
}

// Backend SpatialEvidence (matches backend/app/schemas/evidence.py)
export interface SpatialEvidence {
  boxes: BoundingBoxEvidence[];
  has_mask: boolean;
  mask_path?: string;
  geojson_path?: string;
  overlay_path?: string;
  statistics?: AreaStatistics;
  geojson_data?: Record<string, unknown>;
  candidate_boxes: number[][];
  candidate_scores: number[];
  selected_box?: number[];
  reasoning_strategy?: string;
  reasoning_score?: number;
  sam2_artifact?: string;
  sam2_score?: number;
}

// Backend ConsistencySignal (matches backend/app/schemas/evidence.py)
export interface ConsistencySignal {
  signal_type: string;
  agreement: boolean;
  description: string;
  details: Record<string, unknown>;
}

// Backend EvidencePackage (matches backend/app/schemas/evidence.py)
export interface EvidencePackage {
  spatial: SpatialEvidence;
  consistency: ConsistencySignal[];
  summary?: string;
  metadata: Record<string, unknown>;
}

// Backend SpatialMetricsResponse (from responses.py)
export interface SpatialMetricsResponse {
  changed_pixels?: number;
  change_ratio?: number;
  regions?: number;
  area_m2?: number;
  area_km2?: number;
}

// Analysis result (matches backend/app/schemas/responses.py AnalyzeResponse)
export interface AnalysisResult {
  job_id: string;
  request_id?: string;
  status: JobStatus;
  task: TaskType;
  workflow_id: string;
  workflow?: string;
  workflow_reason: string;
  query?: string;
  answer?: string;
  confidence?: number;
  models_used: string[];
  parameters: Record<string, unknown>;
  evidence: EvidencePackage;
  metrics?: SpatialMetricsResponse;
  execution_trace: TraceStep[];
  trace: TraceStep[];
  warnings: string[];
  errors: string[];
  artifacts: Record<string, string[]>;
  visualizations: Record<string, unknown>[];
  orchestration?: Record<string, unknown>;
}

export interface Layer {
  id: string;
  name: string;
  category: string;
  provenance: LayerProvenance;
  description?: string;
  available: boolean;
  legend_available?: boolean;
  export_formats?: ExportFormat[];
  artifact_url?: string;
  legend_url?: string;
}

export interface LegendResponse {
  min: number;
  max: number;
  unit?: string;
  colormap?: string;
  ticks?: number[];
  labels?: string[];
}

export interface PixelInspectionRequest {
  col: number;
  row: number;
}

// Backend pixel inspection response (matches visualization/inspector.py)
export interface PixelInspectionResponse {
  col: number;
  row: number;
  crs?: string;
  band_values?: Record<string, number>;
  geographic_coordinates?: {
    x_coord?: number;
    y_coord?: number;
    crs?: string;
  };
  probability?: number;
  prediction?: number;
  model_prediction?: {
    status?: string;
    probability?: number;
  };
  derived_indices?: Record<string, number>;
}

// Backend histogram response (matches visualization/inspector.py)
export interface HistogramResponse {
  layer_id: string;
  counts: number[];
  bins: Array<{ range_start: number; range_end: number; count: number }>;
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number;
  units: string;
  total_pixels: number;
}

export interface VideoAnalyzeRequest {
  video_id: string;
  query: string;
  sampling_fps?: number;
  confidence_threshold?: number;
}

export interface VideoEvent {
  id: string;
  timestamp_sec: number;
  label: string;
  score: number;
  track_id?: string;
  box?: [number, number, number, number];
  keyframe_url?: string;
}

export interface VideoFlag {
  flag_id: string;
  start_timestamp: number;
  end_timestamp: number;
  label: string;
  event_score: number;
  keyframe_url?: string;
  overlay_url?: string;
  mask_url?: string;
  box_2d?: number[];
  metadata?: {
    /** Object track inside the event window (video only): box per frame, normalised [ymin, xmin, ymax, xmax]. */
    track?: VideoTrackPoint[];
    [key: string]: unknown;
  };
}

export interface VideoTrackPoint {
  t: number;
  frame: number;
  box_2d: [number, number, number, number];
  /** Median colour of the object's own mask pixels on this frame. */
  rgb: [number, number, number] | null;
}

export interface VideoMetadata {
  filename: string;
  duration_sec: number;
  fps: number;
  width: number;
  height: number;
  frame_count: number;
  codec: string;
}

export interface VideoJobResult {
  job_id: string;
  status: JobStatus;
  query: string;
  flags?: VideoFlag[];
  workflow_reason?: string;
  video_metadata?: VideoMetadata;
  events?: VideoEvent[];
  keyframes?: string[];
  models_used?: string[];
  execution_trace?: TraceStep[];
}
