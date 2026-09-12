export type JobStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELED";

export type TaskType =
  | "AUTO"
  | "VQA"
  | "GROUNDING"
  | "CHANGE"
  | "TEMPORAL_VQA"
  | "VISUAL_ANALYTICS"
  | "VIDEO";

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

export interface TraceStep {
  name: string;
  status: "success" | "running" | "failed" | "skipped";
  duration_ms?: number;
  message?: string;
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

export interface SpatialMetrics {
  changed_pixels?: number;
  change_ratio?: number;
  regions?: number;
  area_m2?: number;
  area_km2?: number;
  bbox?: [number, number, number, number];
  centroid?: [number, number];
}

export interface AnalysisResult {
  job_id: string;
  request_id?: string;
  task: TaskType;
  query: string;
  answer: string;
  confidence?: number;
  metrics?: SpatialMetrics;
  evidence?: EvidenceItem[];
  models_used?: string[];
  artifacts?: Record<string, string[]> | string[];
  execution_trace?: TraceStep[];
  trace?: TraceStep[];
  visualizations?: Array<Record<string, unknown>>;
  created_at?: string;
  completed_at?: string;
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

export interface PixelInspectionResponse {
  col: number;
  row: number;
  crs?: string;
  coordinates?: [number, number];
  bands?: Record<string, number>;
  indices?: Record<string, number>;
  model?: {
    probability?: number;
    prediction?: string;
  };
}

export interface HistogramResponse {
  layer_id: string;
  bins: number[];
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number;
  percentiles: {
    p2?: number;
    p25?: number;
    p50?: number;
    p75?: number;
    p98?: number;
  };
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
  /** The API returns `flags`; `events` was never emitted by the backend. */
  flags?: VideoFlag[];
  /** Why the run produced what it did — carries NOT_APPLICABLE / DETECTION_FAILED. */
  workflow_reason?: string;
  video_metadata?: VideoMetadata;
  events?: VideoEvent[];
  keyframes?: string[];
  models_used?: string[];
  execution_trace?: TraceStep[];
}
