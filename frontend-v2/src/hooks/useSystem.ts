import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PixelInspectionRequest } from "@/lib/types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: async () => await api.models(),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useJob(jobId?: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => {
      try {
        return await api.job(jobId!);
      } catch (jobError) {
        // Video jobs are persisted separately from the generic analysis
        // status in some deployments. Use the dedicated endpoint as a
        // fallback so they never enter the raster-only page path.
        try {
          const video = await api.videoJob(jobId!);
          return {
            job_id: video.job_id,
            status: video.status,
            task: "video_grounding",
            query: video.query,
            models_used: video.models_used,
            execution_steps: video.execution_trace,
          };
        } catch {
          throw jobError;
        }
      }
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;

      if (
        status === "CREATED" ||
        status === "UPLOADED" ||
        status === "QUEUED" ||
        status === "PENDING" ||
        status === "VALIDATING" ||
        status === "PLANNING" ||
        status === "RUNNING" ||
        status === "GENERATING_EVIDENCE"
      ) {
        return 2000;
      }

      return false;
    },
  });
}

export function useAnalysisResult(jobId?: string, enabled?: boolean) {
  return useQuery({
    queryKey: ["result", jobId],
    queryFn: () => api.result(jobId!),
    enabled: Boolean(jobId) && Boolean(enabled),
    staleTime: 30_000,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    refetchInterval: (query) => {
      if (!query.state.data && query.state.fetchFailureCount < 5) {
        return 2000;
      }
      return false;
    },
  });
}

export function useVideoResult(jobId?: string, enabled?: boolean) {
  return useQuery({
    queryKey: ["video-result", jobId],
    queryFn: () => api.videoResult(jobId!),
    enabled: Boolean(jobId) && Boolean(enabled),
    staleTime: 30_000,
    retry: 3,
    refetchInterval: (query) => (query.state.data ? false : 2000),
  });
}

export function useLayers(jobId?: string, enabled = true) {
  return useQuery({
    queryKey: ["layers", jobId],
    queryFn: () => api.layers(jobId!),
    enabled: Boolean(jobId) && enabled,
  });
}

export function usePixelInspector(jobId?: string) {
  return useMutation({
    mutationFn: (payload: PixelInspectionRequest) =>
      api.inspectPixel(jobId!, payload),
  });
}

export function useHistogram(
  jobId?: string,
  layerId?: string,
  enabled?: boolean,
) {
  return useQuery({
    queryKey: ["histogram", jobId, layerId],
    queryFn: () => api.histogram(jobId!, layerId!),
    enabled: Boolean(jobId && layerId) && Boolean(enabled),
  });
}
