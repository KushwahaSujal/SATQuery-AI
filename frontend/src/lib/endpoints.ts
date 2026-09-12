export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const endpoints = {
  health: "/api/health",
  models: "/api/models",

  upload: "/api/upload",
  analyze: "/api/analyze",

  jobs: "/api/jobs",
  job: (jobId: string) => `/api/jobs/${jobId}`,
  result: (jobId: string) => `/api/results/${jobId}`,
  artifacts: (jobId: string, path: string) =>
    `/api/artifacts/${jobId}/${path}`,

  layers: (jobId: string) => `/api/analysis/${jobId}/layers`,
  visualization: (jobId: string, layerId: string) =>
    `/api/analysis/${jobId}/visualizations/${layerId}`,
  legend: (jobId: string, layerId: string) =>
    `/api/analysis/${jobId}/visualizations/${layerId}/legend`,
  inspectPixel: (jobId: string) => `/api/analysis/${jobId}/inspect-pixel`,
  histogram: (jobId: string, layerId: string) =>
    `/api/analysis/${jobId}/histogram/${layerId}`,
  exportLayer: (jobId: string, layerId: string) =>
    `/api/analysis/${jobId}/export/${layerId}`,

  videoUpload: "/api/video/upload",
  videoAnalyze: "/api/video/analyze",
  videoJob: (jobId: string) => `/api/video/${jobId}`,
  videoResults: (jobId: string) => `/api/video/${jobId}/results`,
  videoStream: (jobId: string) => `/api/video/${jobId}/stream`,
};
