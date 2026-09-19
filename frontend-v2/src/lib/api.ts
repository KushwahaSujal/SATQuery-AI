import { endpoints, API_BASE } from "./endpoints";
import type {
  AnalyzeRequest,
  AnalysisResult,
  HealthResponse,
  HistogramResponse,
  Layer,
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

function httpWithProgress<T>(
  path: string,
  init: RequestInit,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    xhr.setRequestHeader("Accept", "application/json");

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as T);
      } else {
        let message = `Request failed (${xhr.status}): ${xhr.statusText}`;
        try {
          const errJson = JSON.parse(xhr.responseText);
          if (errJson.error?.message) message = errJson.error.message;
          else if (errJson.detail) message = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        } catch {}
        reject(new Error(message));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    if (init.body instanceof FormData) {
      xhr.send(init.body);
    } else {
      reject(new Error("httpWithProgress only supports FormData bodies"));
    }
  });
}

export const api = {
  health: async (): Promise<HealthResponse> => {
    const raw = await http<Record<string, unknown>>(endpoints.health);
    const modelsAvail = (raw.models_available || {}) as Record<string, boolean>;
    const readyCount = Object.values(modelsAvail).filter(Boolean).length;
    const totalCount = Object.keys(modelsAvail).length;

    return {
      api: raw.status === "ok" ? "online" : "degraded",
      database: raw.database_connected ? "connected" : "disconnected",
      models_ready: readyCount,
      models_total: totalCount,
      version: raw.version as string,
      environment: raw.environment as string,
      device: raw.device as string,
      models_available: modelsAvail,
      database_connected: raw.database_connected as boolean,
    };
  },

  models: async (): Promise<ModelInfo[]> => {
    const raw = await http<Record<string, unknown>>(endpoints.models);
    const list = Array.isArray(raw) ? raw : ((raw.models || []) as Record<string, unknown>[]);
    return list.map((m: Record<string, unknown>) => ({
      name: m.name as string,
      task: (m.task as string) || "",
      device: m.device as string,
      status: (m.load_state || m.status || "NOT_CONFIGURED") as ModelInfo["status"],
      loaded: (m.loaded as boolean) || m.load_state === "LOADED",
      description: (m.description as string) || `Input: ${m.input_relationship} (${m.input_count}), Modalities: ${(Array.isArray(m.supported_modalities) ? m.supported_modalities : []).join(", ")}`,
      capabilities: (m.supported_tasks as string[]) || [],
      available: (m.available as boolean) || (m.availability as boolean) || false,
      last_error: m.last_error as string,
      validation_status: m.validation_status as string,
    }));
  },

  uploadRasters: async (files: File[]): Promise<{ rasters: UploadedRaster[] }> => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    const res = await http<Record<string, unknown>>(endpoints.upload, {
      method: "POST",
      body: formData,
    });

    const requestId = (res.request_id || res.job_id) as string;
    if (!requestId) {
      throw new Error("Backend did not return request_id");
    }

    const metadataList = (res.metadata || []) as Record<string, unknown>[];

    const rasters: UploadedRaster[] = files.map((file, i) => {
      const meta = metadataList[i] || {};
      const preview = meta.preview_url
        ? (meta.preview_url as string).startsWith("http")
          ? meta.preview_url as string
          : `${API_BASE}${meta.preview_url}`
        : undefined;

      return {
        id: `${requestId}-${i}`,
        request_id: requestId,
        filename: (meta.filename as string) || file.name,
        width: meta.width as number,
        height: meta.height as number,
        bands: meta.bands as number,
        dtype: meta.dtype as string,
        crs: meta.crs as string,
        bounds: meta.bounds as [number, number, number, number],
        transform: meta.transform as number[],
        resolution: meta.resolution as [number, number],
        modality: meta.detected_modality as string,
        modality_confidence: meta.modality_confidence as number,
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

    const res = await http<Record<string, unknown>>(endpoints.videoUpload, {
      method: "POST",
      body: formData,
    });

    const meta = (res.video_metadata || {}) as Record<string, unknown>;
    const video: UploadedVideo = {
      id: res.job_id as string,
      request_id: res.job_id as string,
      filename: (res.filename as string) || file.name,
      duration_sec: meta.duration_sec as number,
      fps: meta.fps as number,
      width: meta.width as number,
      height: meta.height as number,
      frames: meta.frame_count as number,
      codec: meta.codec as string,
      preview_url: `${API_BASE}${res.video_url || endpoints.videoStream(res.job_id as string)}`,
    };

    return { video };
  },

  uploadRastersWithProgress: async (
    files: File[],
    onProgress?: (percent: number) => void,
  ): Promise<{ rasters: UploadedRaster[] }> => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    const res = await httpWithProgress<Record<string, unknown>>(
      endpoints.upload,
      { method: "POST", body: formData },
      onProgress,
    );

    const requestId = (res.request_id || res.job_id) as string;
    if (!requestId) {
      throw new Error("Backend did not return request_id");
    }

    const metadataList = (res.metadata || []) as Record<string, unknown>[];

    const rasters: UploadedRaster[] = files.map((file, i) => {
      const meta = metadataList[i] || {};
      const preview = meta.preview_url
        ? (meta.preview_url as string).startsWith("http")
          ? (meta.preview_url as string)
          : `${API_BASE}${meta.preview_url}`
        : undefined;

      return {
        id: `${requestId}-${i}`,
        request_id: requestId,
        filename: (meta.filename as string) || file.name,
        width: meta.width as number,
        height: meta.height as number,
        bands: meta.bands as number,
        dtype: meta.dtype as string,
        crs: meta.crs as string,
        bounds: meta.bounds as [number, number, number, number],
        transform: meta.transform as number[],
        resolution: meta.resolution as [number, number],
        modality: meta.detected_modality as string,
        modality_confidence: meta.modality_confidence as number,
        preview_url: preview,
        georeferenced: Boolean(meta.crs),
        valid_raster: true,
      };
    });

    return { rasters };
  },

  uploadVideoWithProgress: async (
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<{ video: UploadedVideo }> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await httpWithProgress<Record<string, unknown>>(
      endpoints.videoUpload,
      { method: "POST", body: formData },
      onProgress,
    );

    const meta = (res.video_metadata || {}) as Record<string, unknown>;
    const video: UploadedVideo = {
      id: res.job_id as string,
      request_id: res.job_id as string,
      filename: (res.filename as string) || file.name,
      duration_sec: meta.duration_sec as number,
      fps: meta.fps as number,
      width: meta.width as number,
      height: meta.height as number,
      frames: meta.frame_count as number,
      codec: meta.codec as string,
      preview_url: `${API_BASE}${res.video_url || endpoints.videoStream(res.job_id as string)}`,
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
    if (payload.task) body.override_task = payload.task;

    const res = await http<Record<string, unknown>>(endpoints.analyze, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    return { job_id: (res.request_id || res.job_id) as string };
  },

  analyzeVideo: async (payload: VideoAnalyzeRequest): Promise<{ job_id: string }> => {
    const formData = new FormData();
    formData.append("query", payload.query);
    if (payload.video_id) formData.append("request_id", payload.video_id);
    if (payload.sampling_fps != null) formData.append("sample_fps", String(payload.sampling_fps));
    if (payload.confidence_threshold != null) formData.append("min_event_score", String(payload.confidence_threshold));

    const res = await http<Record<string, unknown>>(endpoints.videoAnalyze, {
      method: "POST",
      body: formData,
    });

    return { job_id: (res.job_id || payload.video_id) as string };
  },

  job: (jobId: string) =>
    http<{ job_id: string; status: string; task?: string; query?: string; progress?: number; execution_steps?: Record<string, unknown>[]; models_used?: string[] }>(
      endpoints.job(jobId),
    ),

  result: (jobId: string) =>
    http<AnalysisResult>(endpoints.result(jobId)),

  layers: async (jobId: string): Promise<{ layers: Layer[] }> => {
    const raw = await http<Record<string, unknown> | Record<string, unknown>[]>(endpoints.layers(jobId));
    const list = Array.isArray(raw) ? raw : ((raw.layers || []) as Record<string, unknown>[]);
    const layers: Layer[] = list.map((l: Record<string, unknown>) => ({
      id: (l.layer_id || l.id) as string,
      name: (l.title || l.name || l.layer_id) as string,
      category: (l.layer_type || "ANALYTICS") as string,
      provenance: (l.provenance || "MODEL_OUTPUT") as Layer["provenance"],
      description: `${l.units || ""} ${l.layer_type ? "(" + l.layer_type + ")" : ""}`.trim(),
      available: true,
      legend_available: Boolean(l.legend_url),
      artifact_url: l.artifact_url ? `${API_BASE}${l.artifact_url}` : `${API_BASE}${endpoints.visualization(jobId, l.layer_id as string)}`,
      legend_url: l.legend_url ? `${API_BASE}${l.legend_url}` : undefined,
    }));
    return { layers };
  },

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

  reportUrl: (requestId: string) =>
    `${API_BASE}${endpoints.report(requestId)}`,

  downloadUrl: (requestId: string) =>
    `${API_BASE}${endpoints.downloadResult(requestId)}`,

  videoJob: (jobId: string) =>
    http<VideoJobResult>(endpoints.videoJob(jobId)),

  videoStreamUrl: (jobId: string) =>
    `${API_BASE}${endpoints.videoStream(jobId)}`,

  listJobs: async (): Promise<Record<string, unknown>[]> => {
    const raw = await http<Record<string, unknown>[] | Record<string, unknown>>(endpoints.jobs);
    return Array.isArray(raw) ? raw : [];
  },

  clearJobs: async (): Promise<{ status: string }> => {
    return http<{ status: string }>(endpoints.jobs, { method: "DELETE" });
  },

  deleteJob: async (jobId: string): Promise<{ status: string }> => {
    return http<{ status: string }>(endpoints.job(jobId), { method: "DELETE" });
  },
};
