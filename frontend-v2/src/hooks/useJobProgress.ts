"use client";

import { useQuery } from "@tanstack/react-query";
import { API_BASE } from "@/lib/endpoints";

/** One entry from the pipeline's execution trace. */
export interface ProgressTraceEntry {
  step: string;
  status: string;
  tool?: string | null;
  model?: string | null;
  details?: string | null;
  duration_ms?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  timestamp?: string | null;
}

/** Shape of GET /api/jobs/{id}/progress, written by the controller during a run. */
export interface JobProgress {
  job_id: string;
  status: string;
  task?: string | null;
  query?: string | null;
  /** The full ordered tool list, known once planning completes. */
  planned_steps: string[];
  completed_steps: string[];
  current_step?: string | null;
  selected_models: string[];
  trace: ProgressTraceEntry[];
  updated_at?: string;
}

const TERMINAL = new Set(["COMPLETED", "FAILED"]);

/**
 * Poll a running job's live progress.
 *
 * The progress file does not exist until the pipeline reaches planning, so a 404 means
 * "not started yet", not an error -- it resolves to null and the caller shows its
 * pre-planning state. Polling stops once the job reaches a terminal status so a finished
 * job is not polled forever.
 */
export function useJobProgress(jobId?: string | null, enabled = true) {
  return useQuery<JobProgress | null>({
    queryKey: ["job-progress", jobId],
    enabled: Boolean(jobId) && enabled,
    // Fast enough to feel live, slow enough not to hammer a machine that is busy
    // running inference.
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && TERMINAL.has(data.status)) return false;
      return 700;
    },
    refetchOnWindowFocus: false,
    gcTime: 60_000,
    staleTime: 0,
    retry: false,
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}/progress`);
      if (res.status === 404) return null;
      if (!res.ok) throw new Error(`Progress unavailable (${res.status})`);
      return (await res.json()) as JobProgress;
    },
  });
}

/** Turn a backend tool id into something readable, without inventing meaning. */
export function humanizeStep(step: string): string {
  return step
    .replace(/_/g, " ")
    .replace(/\b(vqa|sar|dino|sam|gpu|ai)\b/gi, (m) => m.toUpperCase())
    .replace(/^./, (c) => c.toUpperCase());
}
