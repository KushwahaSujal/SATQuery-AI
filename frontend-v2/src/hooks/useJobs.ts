"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getLocalJobs, saveLocalJobs } from "@/lib/localJobs";

export const JOBS_QUERY_KEY = ["jobs"] as const;
type JobRecord = Record<string, unknown>;

export function useJobs() {
  return useQuery({
    queryKey: JOBS_QUERY_KEY,
    queryFn: async (): Promise<JobRecord[]> => {
      const cachedJobs = getLocalJobs();

      try {
        const remoteJobs = await api.listJobs();
        saveLocalJobs(
          remoteJobs.map((job) => ({
            job_id: String(job.job_id || job.id || ""),
            task: String(job.task || "Analysis"),
            query: String(job.query || ""),
            status: String(job.status || "UNKNOWN"),
            created_at: String(job.created_at || new Date().toISOString()),
          })),
        );
        return remoteJobs;
      } catch (error) {
        if (cachedJobs.length > 0) {
          return cachedJobs as unknown as JobRecord[];
        }
        throw error;
      }
    },
    retry: 3,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 5000),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    // Always refresh when a jobs surface is opened, even when cached data exists.
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    // Active jobs can change outside this browser; completed jobs do not need polling.
    refetchInterval: (query) => {
      const jobs = query.state.data ?? [];
      const hasActiveJob = jobs.some((job) =>
        ["PENDING", "QUEUED", "RUNNING", "VALIDATING", "PLANNING"].includes(
          String(job.status),
        ),
      );
      return hasActiveJob ? 5_000 : false;
    },
  });
}
