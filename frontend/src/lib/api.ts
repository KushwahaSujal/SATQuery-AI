import { endpoints, API_BASE } from "./endpoints";
import type {
  AnalyzeRequest,
  AnalysisResult,
  HealthResponse,
  HistogramResponse,
  Layer,
  LegendResponse,
  ModelInfo,
  PixelInspectionRequest,
  PixelInspectionResponse,
  UploadedRaster,
  UploadedVideo,
  VideoAnalyzeRequest,
  VideoJobResult,
} from "./types";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const bodyText = await response.text();
    let message = `Request failed (${response.status}): ${response.statusText}`;
    try {
      const errJson = JSON.parse(bodyText);
      if (errJson.error?.message) {
        message = errJson.error.message;
      } else if (errJson.detail) {
        message = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {}
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: async (): Promise<HealthResponse> => {
    const raw = await http<any>(endpoints.health);
    const modelsAvail = raw.models_available || {};
    const readyCount = Object.values(modelsAvail).filter(Boolean).length;
    const totalCount = Object.keys(modelsAvail).length;

    return {
      api: raw.status === "ok" ? "online" : "degraded",
      database: raw.database_connected ? "connected" : "disconnected",
      storage: "available",
      models_ready: readyCount,
      models_total: totalCount,
      version: raw.version,
      environment: raw.environment,
      device: raw.device,
      models_available: modelsAvail,
      database_connected: raw.database_connected,
    };
  },

  models: async (): Promise<ModelInfo[]> => {
    const raw = await http<any>(endpoints.models);
    const list = Array.isArray(raw) ? raw : (raw.models || []);
    return list.map((m: any) => {
      const isAvailable = Boolean(m.available || m.availability || m.status === "AVAILABLE");
      const isLoaded = Boolean(m.loaded);
      return {
        name: m.name,
        task: m.task || (m.supported_tasks ? m.supported_tasks.join(", ") : "Remote Sensing"),
        device: m.device,
        status: isAvailable ? "AVAILABLE" : "NOT_CONFIGURED",
        loaded: isAvailable,
        description: `Input: ${m.input_relationship} (${m.input_count}), Modalities: ${(m.supported_modalities || []).join(", ")}`,
        capabilities: m.supported_tasks || [],
      };
    });
  },

  uploadRasters: async (files: File[]): Promise<{ rasters: UploadedRaster[] }> => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    const res = await http<any>(endpoints.upload, {
      method: "POST",
      body: formData,
    });

    const requestId = res.request_id || res.job_id || crypto.randomUUID().slice(0, 8);
    const metadataList = res.metadata || [];

    const rasters: UploadedRaster[] = files.map((file, i) => {
      const meta = metadataList[i] || {};
      const preview = meta.preview_url
        ? meta.preview_url.startsWith("http")
          ? meta.preview_url
          : `${API_BASE}${meta.preview_url}`
        : undefined;

      return {
        id: `${requestId}-${i}`,
        request_id: requestId,
        filename: meta.filename || file.name,
        width: meta.width || 1024,
        height: meta.height || 1024,
        bands: meta.bands || 3,
        dtype: meta.dtype || "uint8",
        crs: meta.crs || "EPSG:4326",
        bounds: meta.bounds,
        transform: meta.transform,
        resolution: meta.resolution,
        modality: meta.detected_modality || "Optical",
        modality_confidence: meta.modality_confidence,
        preview_url: preview,
        georeferenced: Boolean(meta.crs),
        valid_raster: true,
      };
    });

    return { rasters };
  },

  uploadVideo: async (file: File): Promise<{ video: UploadedVideo }> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await http<any>(endpoints.videoUpload, {
      method: "POST",
      body: formData,
    });

    const meta = res.video_metadata || {};
    const video: UploadedVideo = {
      id: res.job_id || crypto.randomUUID().slice(0, 8),
      request_id: res.job_id,
      filename: res.filename || file.name,
      duration_sec: meta.duration_sec || 0,
      fps: meta.fps || 30,
      width: meta.width || 1920,
      height: meta.height || 1080,
      frames: meta.frame_count || 0,
      codec: meta.codec || "h264",
      preview_url: `${API_BASE}${res.video_url || endpoints.videoStream(res.job_id)}`,
    };

    return { video };
  },

  analyze: async (payload: AnalyzeRequest): Promise<{ job_id: string }> => {
    const image_filenames = payload.image_filenames || payload.raster_ids || [];
    const body: Record<string, unknown> = {
      query: payload.query,
      image_filenames,
      parameters: payload.params || {},
    };
    if (payload.request_id) body.request_id = payload.request_id;
    if (payload.task && payload.task !== "AUTO") body.override_task = payload.task;

    const res = await http<any>(endpoints.analyze, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    return { job_id: res.request_id || res.job_id };
  },

  analyzeVideo: async (payload: VideoAnalyzeRequest): Promise<{ job_id: string }> => {
    const formData = new FormData();
    formData.append("query", payload.query);
    if (payload.video_id) formData.append("request_id", payload.video_id);
    if (payload.sampling_fps) formData.append("sample_fps", String(payload.sampling_fps));
    if (payload.confidence_threshold) formData.append("min_event_score", String(payload.confidence_threshold));

    const res = await http<any>(endpoints.videoAnalyze, {
      method: "POST",
      body: formData,
    });

    return { job_id: res.job_id || payload.video_id };
  },

  job: (jobId: string) =>
    http<{ job_id: string; status: string; task?: string; query?: string; progress?: number; execution_steps?: any[]; models_used?: string[] }>(
      endpoints.job(jobId),
    ),

  result: (jobId: string) =>
    http<AnalysisResult>(endpoints.result(jobId)),

  layers: async (jobId: string): Promise<{ layers: Layer[] }> => {
    const raw = await http<any>(endpoints.layers(jobId));
    const list = Array.isArray(raw) ? raw : (raw.layers || []);
    const layers: Layer[] = list.map((l: any) => ({
      id: l.layer_id || l.id,
      name: l.title || l.name || l.layer_id,
      category: l.layer_type || "ANALYTICS",
      provenance: l.provenance || "MODEL_OUTPUT",
      description: `${l.units || ""} ${l.layer_type ? "(" + l.layer_type + ")" : ""}`.trim(),
      available: true,
      legend_available: Boolean(l.legend_url),
      artifact_url: l.artifact_url ? `${API_BASE}${l.artifact_url}` : `${API_BASE}${endpoints.visualization(jobId, l.layer_id)}`,
      legend_url: l.legend_url ? `${API_BASE}${l.legend_url}` : undefined,
    }));
    return { layers };
  },

  legend: (jobId: string, layerId: string) =>
    http<LegendResponse>(endpoints.legend(jobId, layerId)),

  inspectPixel: (jobId: string, payload: PixelInspectionRequest) =>
    http<PixelInspectionResponse>(endpoints.inspectPixel(jobId), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),

  histogram: (jobId: string, layerId: string) =>
    http<HistogramResponse>(endpoints.histogram(jobId, layerId)),

  visualizationUrl: (jobId: string, layerId: string) =>
    `${API_BASE}${endpoints.visualization(jobId, layerId)}`,

  exportUrl: (
    jobId: string,
    layerId: string,
    format: "png" | "geotiff" | "geojson",
  ) =>
    `${API_BASE}${endpoints.exportLayer(jobId, layerId)}?format=${format}`,

  videoJob: (jobId: string) =>
    http<VideoJobResult>(endpoints.videoJob(jobId)),

  videoResults: (jobId: string) =>
    http<VideoJobResult>(endpoints.videoResults(jobId)),

  videoStreamUrl: (jobId: string) =>
    `${API_BASE}${endpoints.videoStream(jobId)}`,

  listJobs: async (): Promise<any[]> => {
    try {
      const raw = await http<any>(endpoints.jobs);
      return Array.isArray(raw) ? raw : [];
    } catch {
      return [];
    }
  },

  clearJobs: async (): Promise<{ status: string }> => {
    return http<any>(endpoints.jobs, { method: "DELETE" });
  },
};
