import type { JobStatus } from "@/lib/types";

/**
 * Single source of truth for how a job status is shown.
 *
 * This exists because Reports, History and the job page each kept their own
 * status table covering a different subset of states -- 5, 8 and 10 keys. The
 * backend emits 7 (backend/app/schemas/agent.py), and Reports' table was missing
 * VALIDATING, PLANNING and GENERATING_EVIDENCE. Because its lookup fell back to
 * the COMPLETED entry, a job in any of those three states rendered as a green
 * "Completed" pill while it was still running.
 *
 * Two rules follow from that, and both are load-bearing:
 *
 *   1. Every status the backend can emit has an entry here.
 *   2. An unrecognised status NEVER falls back to a success state. `describeJobStatus`
 *      returns a neutral "unknown" descriptor built from the raw string, so a status
 *      added to the backend later shows up as unknown rather than as finished.
 *
 * Colours come from the palette tokens in globals.css, which are defined for both
 * the dark and light themes. Do not replace them with hardcoded Tailwind shades
 * like bg-amber-950/60 -- those only work in dark mode and are the reason the light
 * theme had washed-out, low-contrast pills.
 */

/** Visual family for a status. Drives colour, never copy. */
export type JobStatusTone = "success" | "progress" | "error" | "neutral";

export interface JobStatusDescriptor {
  /** Human-readable label. */
  label: string;
  tone: JobStatusTone;
  /** True once the job has stopped changing, successfully or not. */
  terminal: boolean;
  /** True ONLY for a genuinely finished, successful job. */
  complete: boolean;
  /** True while the backend is still working the job. */
  active: boolean;
}

/**
 * globals.css ships a --status-{completed,processing,failed}-{bg,text,dot} family
 * defined in BOTH the dark and light blocks, purpose-built for status badges. These
 * are the tokens the hardcoded bg-amber-950/60-style shades were bypassing.
 */
const TONE_CLASSES: Record<JobStatusTone, { pill: string; dot: string; text: string }> = {
  success: {
    pill: "bg-[var(--status-completed-bg)] text-[var(--status-completed-text)] border-[var(--status-completed-dot)]/30",
    dot: "bg-[var(--status-completed-dot)]",
    text: "text-[var(--status-completed-text)]",
  },
  progress: {
    pill: "bg-[var(--status-processing-bg)] text-[var(--status-processing-text)] border-[var(--status-processing-dot)]/30",
    dot: "bg-[var(--status-processing-dot)]",
    text: "text-[var(--status-processing-text)]",
  },
  error: {
    pill: "bg-[var(--status-failed-bg)] text-[var(--status-failed-text)] border-[var(--status-failed-dot)]/30",
    dot: "bg-[var(--status-failed-dot)]",
    text: "text-[var(--status-failed-text)]",
  },
  neutral: {
    pill: "bg-[var(--surface-2)] text-[var(--text-2)] border-[var(--border)]",
    dot: "bg-[var(--text-3)]",
    text: "text-[var(--text-2)]",
  },
};

/**
 * Every status the backend can emit, plus CREATED/UPLOADED which the frontend
 * uses locally before a job reaches the API.
 */
const JOB_STATUS: Record<JobStatus, JobStatusDescriptor> = {
  CREATED: { label: "Created", tone: "neutral", terminal: false, complete: false, active: false },
  UPLOADED: { label: "Uploaded", tone: "neutral", terminal: false, complete: false, active: false },
  QUEUED: { label: "Queued", tone: "progress", terminal: false, complete: false, active: true },
  PENDING: { label: "Pending", tone: "progress", terminal: false, complete: false, active: true },
  VALIDATING: { label: "Validating", tone: "progress", terminal: false, complete: false, active: true },
  PLANNING: { label: "Planning", tone: "progress", terminal: false, complete: false, active: true },
  RUNNING: { label: "Running", tone: "progress", terminal: false, complete: false, active: true },
  GENERATING_EVIDENCE: {
    label: "Generating evidence",
    tone: "progress",
    terminal: false,
    complete: false,
    active: true,
  },
  COMPLETED: { label: "Completed", tone: "success", terminal: true, complete: true, active: false },
  FAILED: { label: "Failed", tone: "error", terminal: true, complete: false, active: false },
};

/** Turn an unrecognised status into something readable without inventing meaning. */
function unknownStatus(raw: string | null | undefined): JobStatusDescriptor {
  const cleaned = (raw ?? "").trim();
  const label = cleaned
    ? cleaned.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase())
    : "Unknown";
  return { label, tone: "neutral", terminal: false, complete: false, active: false };
}

/**
 * Describe any job status. Accepts a plain string because job payloads are not
 * type-checked at the network boundary. Never reports success for a status it
 * does not recognise.
 */
export function describeJobStatus(status: string | null | undefined): JobStatusDescriptor {
  // The backend emits upper-case statuses; normalise so a case variant resolves to
  // the real entry rather than being prettified into a label that looks familiar
  // ("completed") while carrying neutral, not-complete semantics.
  const key = status?.trim().toUpperCase();
  if (key && key in JOB_STATUS) {
    return JOB_STATUS[key as JobStatus];
  }
  return unknownStatus(status);
}

/** Tailwind classes for a status pill (background, text and border). */
export function jobStatusPillClasses(status: string | null | undefined): string {
  return TONE_CLASSES[describeJobStatus(status).tone].pill;
}

/** Tailwind classes for a small status dot. */
export function jobStatusDotClasses(status: string | null | undefined): string {
  return TONE_CLASSES[describeJobStatus(status).tone].dot;
}

/** Tailwind text-colour class for a status. */
export function jobStatusTextClasses(status: string | null | undefined): string {
  return TONE_CLASSES[describeJobStatus(status).tone].text;
}

/** Convenience: the label alone. */
export function jobStatusLabel(status: string | null | undefined): string {
  return describeJobStatus(status).label;
}

/** True only for a job that genuinely finished successfully. */
export function isJobComplete(status: string | null | undefined): boolean {
  return describeJobStatus(status).complete;
}

/** True while the backend is still working the job. */
export function isJobActive(status: string | null | undefined): boolean {
  return describeJobStatus(status).active;
}

/**
 * globals.css already ships a `.status-pill*` / `.status-dot*` utility family, and
 * the job page uses it while Reports and History use rounded-full pills built from
 * inline token classes. Both vocabularies are kept -- restyling Sandipan's pill
 * shapes is out of scope -- but they now derive from the SAME tone decision above,
 * which is the duplication that caused the false "Completed" in the first place.
 *
 * Note: the job page previously asked for `status-pill-cyan`, which globals.css does
 * not define, so every in-progress state rendered with no colour at all. Progress
 * maps to the defined amber classes, matching Reports and History; cyan stays the
 * brand accent for interactive state rather than a status colour.
 */
const TONE_UTILITY: Record<JobStatusTone, { pill: string; dot: string }> = {
  success: { pill: "status-pill-green", dot: "status-dot-green" },
  progress: { pill: "status-pill-amber", dot: "status-dot-amber" },
  error: { pill: "status-pill-red", dot: "status-dot-red" },
  neutral: { pill: "", dot: "status-dot-muted" },
};

/** globals.css modifier to pair with the base `status-pill` class. */
export function jobStatusPillClass(status: string | null | undefined): string {
  return TONE_UTILITY[describeJobStatus(status).tone].pill;
}

/** globals.css modifier to pair with the base `status-dot` class. */
export function jobStatusDotClass(status: string | null | undefined): string {
  return TONE_UTILITY[describeJobStatus(status).tone].dot;
}

export { TONE_CLASSES };
