export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");

export function apiUrl(path: string) {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

export const API_ENDPOINTS = {
  health: "/health",
  models: "/models",
  upload: "/upload",
  analyze: "/analyze",
  analysis: (jobId: string) => `/analysis/${encodeURIComponent(jobId)}`,
  layers: (jobId: string) => `/analysis/${encodeURIComponent(jobId)}/layers`,
  inspectPixel: (jobId: string) => `/analysis/${encodeURIComponent(jobId)}/inspect-pixel`,
  histogram: (jobId: string, layerId: string) => `/analysis/${encodeURIComponent(jobId)}/histogram/${encodeURIComponent(layerId)}`,
  result: (jobId: string) => `/analysis/${encodeURIComponent(jobId)}/result`,
  job: (jobId: string) => `/analysis/${encodeURIComponent(jobId)}`,
  jobs: "/jobs",
  clearJobs: "/jobs/clear",
  videoUpload: "/video/upload",
  videoAnalyze: "/video/analyze",
  videoJob: (jobId: string) => `/video/${encodeURIComponent(jobId)}`,
  videoStream: (jobId: string) => `/video/${encodeURIComponent(jobId)}/stream`,
  visualization: (jobId: string, layerId: string) => `/analysis/${encodeURIComponent(jobId)}/visualization/${encodeURIComponent(layerId)}`,
  export: (jobId: string, layerId: string, format: string) => `/analysis/${encodeURIComponent(jobId)}/export/${encodeURIComponent(layerId)}?format=${encodeURIComponent(format)}`,
};
