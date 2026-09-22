export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Lives here, beside API_BASE, because three separate call sites reach the backend:
// http() in api.ts, the XHR uploader (it needs progress events), and the progress
// poller in useJobProgress. Each one that forgot the key returned 401 against the
// hosted backend while working locally, where no key is configured.
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

/** Auth headers for a backend call, empty when no key is configured. */
export function authHeaders(): Record<string, string> {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

/** <img>, <video> and download anchors cannot set headers; the backend takes ?key= too. */
export function withKey(url: string): string {
  if (!API_KEY) return url;
  return url + (url.includes("?") ? "&" : "?") + "key=" + encodeURIComponent(API_KEY);
}

export const endpoints = {
  health: "/api/health",
  models: "/api/models",
  documentation: "/api/documentation",
  documentationContent: (path: string) => `/api/documentation/content?path=${encodeURIComponent(path)}`,

  upload: "/api/upload",
  analyze: "/api/analyze",

  jobs: "/api/jobs",
  job: (jobId: string) => `/api/jobs/${jobId}`,
  reuseSource: (jobId: string) => `/api/jobs/${jobId}/reuse-source`,
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

  report: (requestId: string) => `/api/reports/${requestId}`,
  downloadResult: (requestId: string) => `/api/results/${requestId}/download`,

  videoUpload: "/api/video/upload",
  videoAnalyze: "/api/video/analyze",
  videoJob: (jobId: string) => `/api/video/${jobId}`,
  videoResults: (jobId: string) => `/api/video/${jobId}/results`,
  videoStream: (jobId: string) => `/api/video/${jobId}/stream`,
};
