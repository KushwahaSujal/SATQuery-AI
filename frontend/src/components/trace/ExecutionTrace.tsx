"use client";

import { useRef, useEffect } from "react";
import type { TraceStep } from "@/lib/types";

export default function ExecutionTrace({ steps }: { steps: TraceStep[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest step
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [steps]);

  if (!steps.length) return null;

  const totalMs = steps.reduce((acc, s) => acc + (s.duration_ms ?? 0), 0);

  // Normalize status to handle backend variations
  const normalizeStatus = (status: string): "success" | "running" | "failed" | "skipped" => {
    const s = status.toLowerCase();
    if (s === "success" || s === "ok") return "success";
    if (s === "running" || s === "started") return "running";
    if (s === "error" || s === "failed" || s === "failure") return "failed";
    if (s === "warning" || s === "skipped" || s === "pending") return "skipped";
    return "success"; // default to success for unknown statuses
  };

  return (
    <div className="flex items-center h-9 px-3 border-t border-[var(--b0)] gap-2 flex-shrink-0 bg-[var(--s0)]">
      {/* Label */}
      <span className="panel-label flex-shrink-0 text-[9px]">Trace</span>

      <div className="w-px h-3 bg-[var(--b1)] flex-shrink-0 mx-0.5" />

      {/* Scrollable steps container */}
      <div
        ref={scrollRef}
        className="flex items-center gap-0 overflow-x-auto flex-1 min-w-0 scrollbar-thin"
        style={{ scrollbarWidth: "thin", scrollbarColor: "var(--b2) transparent" }}
      >
        {steps.map((step, i) => {
          const status = normalizeStatus(step.status);
          const isSuccess = status === "success";
          const isFailed = status === "failed";
          const isRunning = status === "running";
          const isSkipped = status === "skipped";

          // Use step.step field (backend uses "step" field)
          const stepName = step.step || "unknown";
          // Round duration to avoid showing floats like 123.456789ms
          const duration = step.duration_ms != null ? Math.round(step.duration_ms) : undefined;

          return (
            <div key={`${stepName}-${i}`} className="flex items-center gap-0 flex-shrink-0">
              {/* Step node */}
              <div
                className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full transition-all ${
                  isRunning
                    ? "bg-[var(--accent-dim)] border border-[hsla(222,88%,62%,0.2)]"
                    : "bg-transparent border border-transparent"
                }`}
              >
                {/* Status icon */}
                {isSuccess && (
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
                {isFailed && (
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                )}
                {isRunning && (
                  <span className="animate-spin-smooth w-2 h-2 border-[1.5px] border-transparent border-t-[var(--accent)] rounded-full flex-shrink-0" />
                )}
                {isSkipped && (
                  <span className="w-1 h-1 rounded-full bg-[var(--t4)] flex-shrink-0" />
                )}

                {/* Step name */}
                <span
                  className={`font-mono-data text-[9px] tracking-wide whitespace-nowrap ${
                    isRunning
                      ? "text-[var(--accent-text)]"
                      : isSuccess
                      ? "text-[var(--t2)]"
                      : isFailed
                      ? "text-[var(--red)]"
                      : "text-[var(--t4)]"
                  }`}
                >
                  {stepName.replace(/_/g, " ")}
                </span>

                {/* Duration badge */}
                {duration != null && duration > 0 && (
                  <span className="font-mono-data text-[8px] text-[var(--t4)] bg-[var(--s2)] px-1 rounded flex-shrink-0">
                    {duration}ms
                  </span>
                )}
              </div>

              {/* Connector arrow */}
              {i < steps.length - 1 && (
                <svg width="12" height="8" viewBox="0 0 12 8" className="flex-shrink-0 mx-0.5">
                  <line x1="0" y1="4" x2="8" y2="4" stroke="var(--b2)" strokeWidth="1" />
                  <polyline points="6,1 8,4 6,7" fill="none" stroke="var(--b2)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
          );
        })}
      </div>

      {/* Total elapsed */}
      {totalMs > 0 && (
        <span className="font-mono-data text-[9px] text-[var(--t4)] flex-shrink-0 ml-2">
          {Math.round(totalMs)}ms
        </span>
      )}
    </div>
  );
}
