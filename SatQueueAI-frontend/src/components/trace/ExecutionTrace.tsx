"use client";

import type { TraceStep } from "@/lib/types";

export default function ExecutionTrace({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) return null;

  const totalMs = steps.reduce((acc, s) => acc + (s.duration_ms ?? 0), 0);

  return (
    <div style={{
      display: "flex", alignItems: "center",
      padding: "0 14px",
      height: 36,
      borderTop: "1px solid var(--b0)",
      gap: 6,
      overflowX: "auto",
      flexShrink: 0,
      background: "var(--s0)",
    }}>
      <span className="panel-label" style={{ flexShrink: 0 }}>Trace</span>

      <div style={{ width: 1, height: 12, background: "var(--b1)", flexShrink: 0, margin: "0 2px" }} />

      <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
        {steps.map((step, i) => {
          const isSuccess = step.status === "success";
          const isFailed  = step.status === "failed";
          const isRunning = step.status === "running";
          const isPending = step.status === "skipped";

          const dotColor = isSuccess ? "var(--green)" : isFailed ? "var(--red)" : isRunning ? "var(--accent)" : "var(--t4)";

          return (
            <div key={step.name} style={{ display: "flex", alignItems: "center", gap: 0 }}>
              {/* Node */}
              <div style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "2px 8px",
                borderRadius: 12,
                background: isRunning ? "var(--accent-dim)" : "transparent",
                border: isRunning ? "1px solid hsla(222,88%,62%,0.2)" : "1px solid transparent",
              }}>
                {/* Status indicator */}
                {isSuccess && (
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
                {isFailed && (
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                )}
                {isRunning && (
                  <span className="animate-spin-smooth" style={{
                    width: 7, height: 7,
                    border: "1.5px solid transparent",
                    borderTopColor: "var(--accent)",
                    borderRadius: "50%",
                    display: "inline-block",
                    flexShrink: 0,
                  }} />
                )}
                {isPending && (
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--t4)", display: "inline-block", flexShrink: 0 }} />
                )}

                {/* Step name */}
                <span className="font-mono-data" style={{
                  fontSize: 9, color: isRunning ? "var(--accent-text)" : isSuccess ? "var(--t2)" : "var(--t4)",
                  letterSpacing: "0.02em",
                }}>
                  {step.name.replace(/_/g, "_")}
                </span>

                {/* Duration */}
                {step.duration_ms != null && (
                  <span className="font-mono-data" style={{ fontSize: 8, color: "var(--t4)" }}>
                    {step.duration_ms}ms
                  </span>
                )}
              </div>

              {/* Connector arrow */}
              {i < steps.length - 1 && (
                <svg width="16" height="10" viewBox="0 0 16 10" style={{ flexShrink: 0 }}>
                  <line x1="0" y1="5" x2="12" y2="5" stroke="var(--b2)" strokeWidth="1" />
                  <polyline points="8,2 12,5 8,8" fill="none" stroke="var(--b2)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
          );
        })}
      </div>

      {/* Total elapsed */}
      {totalMs > 0 && (
        <>
          <div style={{ flex: 1 }} />
          <span className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", flexShrink: 0 }}>
            {totalMs}ms total
          </span>
        </>
      )}
    </div>
  );
}
