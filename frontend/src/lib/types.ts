export type TaskType =
  | "AUTO"
  | "VQA"
  | "GROUNDING"
  | "CHANGE"
  | "TEMPORAL_VQA"
  | "VISUAL_ANALYTICS"
  | "VIDEO";

export interface UploadedRaster {
  id: string;
  filename: string;
  width: number;
  height: number;
  bands: number;
  dtype?: string;
  crs?: string;
  georeferenced?: boolean;
  valid_raster?: boolean;
  modality?: string;
  temporal_role?: string;
  preview_url?: string;
  request_id?: string;
}

export interface UploadedVideo {
  id: string;
  filename: string;
  duration_sec: number;
  fps: number;
  width: number;
  height: number;
  frames: number;
  codec?: string;
}

export interface TraceStep {
  name: string;
  status?: "success" | "failed" | "running" | "pending" | "skipped";
  duration_ms?: number;
  message?: string;
}

export interface LocalJobRecord {
  id?: string;
  job_id: string;
  task: string;
  query: string;
  status: string;
  created_at: string;
  models_used?: string[];
  execution_steps?: TraceStep[];
}

export interface ModelInfo {
  name: string;
  version?: string;
  task?: string;
  description?: string;
  supported_tasks?: string[];
  supported_modalities?: string[];
  input_count?: number;
  input_relationship?: string;
  checkpoint_path?: string | null;
  available?: boolean;
  loaded?: boolean;
  device?: string;
  precision?: string;
  model_id?: string;
  status?: string;
}

export interface PixelInspectionRequest {
  col: number;
  row: number;
}

export interface PixelInspectionResult {
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

export interface Layer {
  id: string;
  name: string;
  provenance: string;
  artifact_url?: string;
  legend_url?: string;
}

export type ExportFormat = "png" | "geotiff" | "geojson";

export interface AnalysisResult {
  job_id?: string;
  task: string;
  query?: string;
  answer: string;
  confidence?: number;
  metrics?: {
    regions?: number;
    area_m2?: number;
    changed_pixels?: number;
  };
  evidence?: Array<{
    id?: string;
    label: string;
    kind: string;
  }>;
  models_used?: string[];
  execution_trace?: TraceStep[];
  trace?: TraceStep[];
}

export interface VideoEvent {
  id: string;
  label: string;
  timestamp_sec: number;
  score: number;
  track_id?: string;
}

export interface VideoJobResult {
  job_id: string;
  status: string;
  query: string;
  events: VideoEvent[];
  keyframes?: unknown[];
  models_used?: string[];
}
