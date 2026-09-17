export interface LocalJobRecord {
  job_id: string;
  task: string;
  query: string;
  status: string;
  created_at: string;
}

const LOCAL_JOBS_KEY = "satquery.local_jobs";

export function getLocalJobs(): LocalJobRecord[] {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = window.localStorage.getItem(LOCAL_JOBS_KEY);

  if (!raw) {
    return [];
  }

  try {
    return JSON.parse(raw) as LocalJobRecord[];
  } catch {
    return [];
  }
}

export function addLocalJob(job: LocalJobRecord) {
  if (typeof window === "undefined") return;
  const jobs = getLocalJobs();
  const next = [job, ...jobs.filter((item) => item.job_id !== job.job_id)];
  window.localStorage.setItem(LOCAL_JOBS_KEY, JSON.stringify(next.slice(0, 100)));
}

export function clearLocalJobs() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LOCAL_JOBS_KEY);
}
