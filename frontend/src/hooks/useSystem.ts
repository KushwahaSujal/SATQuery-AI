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
    queryFn: api.models,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useJob(jobId?: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;

      if (status === "RUNNING" || status === "PENDING") {
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
  });
}

export function useLayers(jobId?: string) {
  return useQuery({
    queryKey: ["layers", jobId],
    queryFn: () => api.layers(jobId!),
    enabled: Boolean(jobId),
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
