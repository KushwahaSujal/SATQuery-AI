import { endpoints, API_BASE, authHeaders, withKey } from "./endpoints";
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
      ...authHeaders(),
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
    // Uploads go through XHR rather than http() so the progress bar has an event to
    // read, which means the key set in http() never reached them: every upload against
    // an authenticated backend came back 401 while the rest of the app worked.
    for (const [k, v] of Object.entries(authHeaders())) xhr.setRequestHeader(k, v);

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
      // Pass the registry's identity, provenance and refusal fields through
      // untouched. Dropping them here previously meant the UI could show that a
      // model was not serving but never why, which is the opposite of the
      // backend's structurally honest refusals.
      model_id: m.model_id as string,
      family: m.family as string,
      version: m.version as string,
      adapter: m.adapter as string,
      checkpoint: (m.checkpoint as string) || (m.checkpoint_path as string),
      license: m.license as string,
      precision: m.precision as string,
      supported_modalities: Array.isArray(m.supported_modalities) ? (m.supported_modalities as string[]) : undefined,
      input_count: m.input_count as number,
      input_relationship: m.input_relationship as string,
      input_requirements: m.input_requirements as Record<string, unknown>,
      output_schema: m.output_schema as Record<string, unknown>,
      device_requirements: m.device_requirements as Record<string, unknown>,
      refusal_reason: m.refusal_reason as string,
      serving: m.serving as boolean,
    }));
  },

  documentation: async (): Promise<{
    documents: { path: string; title: string; summary: string; bytes: number; sections: number; updated_at: number; search_text: string }[];
    count: number;
  }> => http(endpoints.documentation),

  documentationContent: async (path: string): Promise<{ path: string; content: string }> =>
    http(endpoints.documentationContent(path)),

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
        ? withKey(
            (meta.preview_url as string).startsWith("http")
              ? (meta.preview_url as string)
              : `${API_BASE}${meta.preview_url}`,
          )
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
      preview_url: withKey(`${API_BASE}${res.video_url || endpoints.videoStream(res.job_id as string)}`),
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
        ? withKey(
            (meta.preview_url as string).startsWith("http")
              ? (meta.preview_url as string)
              : `${API_BASE}${meta.preview_url}`,
          )
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
      preview_url: withKey(`${API_BASE}${res.video_url || endpoints.videoStream(res.job_id as string)}`),
    };

    return { video };
  },

  // Copies an existing job's source imagery into a fresh workspace so the same scene
  // can be re-queried without re-uploading it, and without overwriting that job.
  reuseSource: async (jobId: string): Promise<{ request_id: string; image_filenames: string[] }> => {
    const res = await http<{ request_id: string; image_filenames: string[] }>(
      endpoints.reuseSource(jobId),
      { method: "POST" },
    );
    return res;
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
      artifact_url: withKey(l.artifact_url ? `${API_BASE}${l.artifact_url}` : `${API_BASE}${endpoints.visualization(jobId, l.layer_id as string)}`),
      legend_url: l.legend_url ? withKey(`${API_BASE}${l.legend_url}`) : undefined,
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
    withKey(`${API_BASE}${endpoints.visualization(jobId, layerId)}`),

  exportUrl: (
    jobId: string,
    layerId: string,
    format: "png" | "geotiff" | "geojson",
  ) =>
    withKey(`${API_BASE}${endpoints.exportLayer(jobId, layerId)}?format=${format}`),

  reportUrl: (requestId: string) =>
    withKey(`${API_BASE}${endpoints.report(requestId)}`),

  downloadUrl: (requestId: string) =>
    withKey(`${API_BASE}${endpoints.downloadResult(requestId)}`),

  videoJob: (jobId: string) =>
    http<VideoJobResult>(endpoints.videoJob(jobId)),

  videoResult: async (jobId: string): Promise<AnalysisResult> => {
    const result = await http<VideoJobResult>(endpoints.videoResults(jobId));
    return {
      job_id: result.job_id,
      request_id: result.job_id,
      status: result.status,
      task: "video_grounding",
      workflow_id: "workflow_video_analysis",
      workflow: "Video analysis",
      workflow_reason: result.workflow_reason || "",
      query: result.query,
      models_used: result.models_used || [],
      parameters: {},
      evidence: {
        spatial: {
          boxes: [],
          has_mask: false,
          candidate_boxes: [],
          candidate_scores: [],
        },
        consistency: [],
        metadata: {},
      },
      execution_trace: result.execution_trace || [],
      trace: result.execution_trace || [],
      warnings: result.warnings || [],
      errors: result.errors || [],
      artifacts: result.artifacts || {},
      visualizations: [],
      flags: result.flags || [],
      video_metadata: result.video_metadata,
    };
  },

  videoStreamUrl: (jobId: string) =>
    withKey(`${API_BASE}${endpoints.videoStream(jobId)}`),

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
