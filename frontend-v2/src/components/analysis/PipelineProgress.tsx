"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { DURATION, EASE } from "@/lib/motion";
import { humanizeStep, type JobProgress } from "@/hooks/useJobProgress";

type StepState = "done" | "active" | "failed" | "pending";

/**
 * Checkpoint progress for a running analysis.
 *
 * Every value shown here comes from GET /api/jobs/{id}/progress, which the controller
 * writes at each pipeline checkpoint: the ordered tool list is the real plan (known once
 * planning finishes, before any of it runs), the durations are measured, and the model
 * list is what the planner actually selected. Nothing is simulated -- in particular the
 * ring does not animate on a timer, it reflects completed steps.
 */
export function PipelineProgress({
  progress,
  isPlanning,
}: {
  progress: JobProgress | null;
  /** True before the progress file exists, i.e. the plan is not known yet. */
  isPlanning: boolean;
}) {
  const steps = progress?.planned_steps ?? [];
  const completed = new Set(progress?.completed_steps ?? []);
  const current = progress?.current_step ?? null;
  const failed = progress?.status === "FAILED";

  const stateOf = (step: string, index: number): StepState => {
    if (completed.has(step)) return "done";
    if (failed && step === current) return "failed";
    if (step === current) return "active";
    // Before the first tool starts, the first step reads as active so the row is never
    // entirely inert while the backend is between checkpoints.
    if (!current && completed.size === 0 && index === 0 && progress?.status === "RUNNING") return "active";
    return "pending";
  };

  // The trace carries the real narration: capability, routing confidence, per-tool timing.
  const trace = progress?.trace ?? [];
  const latest = trace.length > 0 ? trace[trace.length - 1] : null;

  if (isPlanning || steps.length === 0) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="flex items-center gap-2.5">
          <motion.span
            className="h-2 w-2 rounded-full bg-[var(--amber)]"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
          <span className="text-xs text-[var(--text-2)]">
            {progress?.status === "VALIDATING" ? "Validating inputs" : "Planning the workflow"}
          </span>
        </div>
        <p className="mt-2 text-[11px] text-[var(--text-3)]">
          The step list appears once the planner has chosen a capability.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      {/* Header: what the planner decided. All real values. */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono-data text-[10px] uppercase tracking-[0.14em] text-[var(--text-3)]">
            {failed ? "Pipeline failed" : progress?.status === "COMPLETED" ? "Pipeline complete" : "Running pipeline"}
          </span>
          {progress?.task && (
            <span className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 font-mono-data text-[10px] text-[var(--text-2)]">
              {progress.task}
            </span>
          )}
        </div>
        <span className="font-mono-data text-[10px] text-[var(--text-3)]">
          {completed.size}/{steps.length} steps
        </span>
      </div>

      {/* The checkpoint row: circle, connecting pipe, circle... */}
      <div className="flex items-start overflow-x-auto pb-1">
        {steps.map((step, i) => {
          const state = stateOf(step, i);
          const entry = trace.find((t) => t.tool === step);
          const isLast = i === steps.length - 1;
          // The pipe leading OUT of this circle fills only once this step is done.
          const pipeFilled = completed.has(step);

          return (
            <div key={step} className="flex min-w-0 flex-1 items-start" style={{ minWidth: 92 }}>
              <div className="flex min-w-0 flex-col items-center gap-1.5" style={{ width: 92 }}>
                <StepCircle state={state} index={i} />
                <span
                  className={`max-w-[88px] text-center text-[10px] leading-tight ${
                    state === "pending" ? "text-[var(--text-3)]" : "text-[var(--text-2)]"
                  }`}
                  title={step}
                >
                  {humanizeStep(step)}
                </span>
                {/* Measured duration, shown only once the step has actually finished. */}
                {state === "done" && entry?.duration_ms != null && (
                  <span className="font-mono-data text-[9px] text-[var(--text-3)]">
                    {formatMs(entry.duration_ms)}
                  </span>
                )}
              </div>

              {!isLast && (
                <div className="relative mt-3.5 h-0.5 flex-1 overflow-hidden rounded-full bg-[var(--surface-3)]">
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full bg-[var(--cyan)]"
                    initial={{ width: "0%" }}
                    animate={{ width: pipeFilled ? "100%" : "0%" }}
                    transition={{ duration: DURATION.slow, ease: EASE }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Live narration straight from the trace. */}
      <div className="mt-4 space-y-1.5 border-t border-[var(--border)] pt-3">
        {latest && (
          <div className="flex items-start gap-2">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[var(--cyan)]" />
            <p className="min-w-0 text-[11px] text-[var(--text-2)]">
              {latest.step}
              {latest.details && (
                <span className="text-[var(--text-3)]"> — {latest.details}</span>
              )}
            </p>
          </div>
        )}
        {progress?.selected_models && progress.selected_models.length > 0 && (
          <p className="font-mono-data text-[10px] text-[var(--text-3)]">
            models: {progress.selected_models.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}

function StepCircle({ state, index }: { state: StepState; index: number }) {
  const base = "relative flex h-7 w-7 items-center justify-center rounded-full border text-[10px] font-medium";

  if (state === "done") {
    return (
      <motion.div
        className={`${base} border-[var(--cyan)] bg-[var(--cyan)] text-[var(--canvas)]`}
        initial={{ scale: 0.8, opacity: 0.4 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: DURATION.base, ease: EASE }}
      >
        <motion.span
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.22, ease: EASE }}
        >
          <Check className="h-3.5 w-3.5" strokeWidth={3} />
        </motion.span>
      </motion.div>
    );
  }

  if (state === "failed") {
    return (
      <div className={`${base} border-[var(--error)] bg-[var(--error-bg)] text-[var(--error)]`}>
        <X className="h-3.5 w-3.5" strokeWidth={3} />
      </div>
    );
  }

  if (state === "active") {
    return (
      <div className={`${base} border-[var(--cyan)] text-[var(--cyan)]`}>
        {/* The ring sweeps to show the step is live. It is a busy indicator, not a
            percentage -- the backend reports step boundaries, not sub-step fractions,
            and drawing a fake fill rate would be inventing precision. */}
        <motion.span
          className="absolute inset-[-3px] rounded-full border-2 border-transparent border-t-[var(--cyan)]"
          animate={{ rotate: 360 }}
          transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
        />
        <motion.span
          className="absolute inset-0 rounded-full bg-[var(--cyan)]"
          animate={{ opacity: [0.12, 0.28, 0.12] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        />
        <span className="relative">{index + 1}</span>
      </div>
    );
  }

  return (
    <div className={`${base} border-[var(--border)] text-[var(--text-3)]`}>
      <span>{index + 1}</span>
    </div>
  );
}

function formatMs(ms: number): string {
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
