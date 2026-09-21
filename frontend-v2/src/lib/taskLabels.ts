import type { TaskType } from "@/lib/types";

/**
 * Single source of truth for how a backend task id is shown.
 *
 * This replaces three hand-copied tables -- Sidebar.tsx (bare string), reports
 * (`{label, type}`) and history (`{label, category}`) -- which had already drifted:
 * `single_image_vqa` was "VQA" in two of them and "VQA Analysis" in the third, and
 * `video_grounding_tracking` was "Video" in one and "Video Tracking" in the others.
 * Reports also grouped single-image tasks under "Optical", which matches none of the
 * category tabs History filters by, so that grouping could never line up.
 *
 * The canonical categories are History's filter tabs. "Other" exists so an
 * unrecognised task is not silently filed under "Single Image", which is what the
 * old `|| "Single Image"` fallbacks did.
 */

export type TaskCategory =
  | "Single Image"
  | "Change Analysis"
  | "Optical + SAR"
  | "Video"
  | "Other";

/** The category tabs a job list can filter by, in display order. */
export const TASK_CATEGORIES: TaskCategory[] = [
  "Single Image",
  "Change Analysis",
  "Optical + SAR",
  "Video",
];

export interface TaskDescriptor {
  label: string;
  category: TaskCategory;
}

const TASKS: Record<TaskType, TaskDescriptor> = {
  single_image_vqa: { label: "VQA", category: "Single Image" },
  single_image_caption: { label: "Captioning", category: "Single Image" },
  single_image_grounding: { label: "Grounding", category: "Single Image" },
  // EuroSAT land-cover classification, routed as a capability in abaa376. None of
  // the three old tables knew about it.
  single_image_classification: { label: "Land Cover", category: "Single Image" },
  bi_temporal_change: { label: "Change Detection", category: "Change Analysis" },
  bi_temporal_change_vqa: { label: "Change VQA", category: "Change Analysis" },
  optical_sar_analysis: { label: "Optical + SAR", category: "Optical + SAR" },
  video_vqa: { label: "Video VQA", category: "Video" },
  video_grounding: { label: "Video Grounding", category: "Video" },
  video_grounding_tracking: { label: "Video Tracking", category: "Video" },
  video_change: { label: "Video Change", category: "Video" },
  unsupported: { label: "Unsupported", category: "Other" },
};

/**
 * Describe any task id. Unrecognised ids keep their raw string as the label -- which
 * is more useful than a wrong friendly name -- and land in "Other".
 */
export function describeTask(task: string | null | undefined): TaskDescriptor {
  if (task && task in TASKS) {
    return TASKS[task as TaskType];
  }
  return { label: (task ?? "Unknown").trim() || "Unknown", category: "Other" };
}

/** Convenience: the display label alone. */
export function taskLabel(task: string | null | undefined): string {
  return describeTask(task).label;
}

/** Convenience: the filter category alone. */
export function taskCategory(task: string | null | undefined): TaskCategory {
  return describeTask(task).category;
}
