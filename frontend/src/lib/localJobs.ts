import type { LocalJobRecord, TraceStep } from "@/lib/types";

const LOCAL_JOBS_KEY = "satquery_local_jobs";

export function getLocalJobs(): LocalJobRecord[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(LOCAL_JOBS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function setLocalJobs(jobs: LocalJobRecord[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LOCAL_JOBS_KEY, JSON.stringify(jobs));
}

export function addLocalJob(job: LocalJobRecord) {
  const jobs = getLocalJobs();
  const next = [job, ...jobs.filter((item) => item.job_id !== job.job_id)];
  setLocalJobs(next);
  return next;
}

export function clearLocalJobs() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LOCAL_JOBS_KEY);
}

export type { LocalJobRecord, TraceStep };
