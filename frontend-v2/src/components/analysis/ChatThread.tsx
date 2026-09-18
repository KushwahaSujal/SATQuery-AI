"use client";

import React, { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/stores/useAnalysisStore";

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function AnalysisProgressCard({ content }: { content: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-cyan-500/5 border border-cyan-500/20">
      <div className="relative w-4 h-4 shrink-0">
        <div className="absolute inset-0 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
      </div>
      <span className="text-xs text-[var(--cyan)] font-medium">{content}</span>
    </div>
  );
}

function AnalysisResultCard({ result }: { result: import("@/lib/types").AnalysisResult }) {
  const metrics = result.metrics;
  const spatial = result.evidence?.spatial?.statistics;
  const area = metrics?.area_km2 ?? spatial?.estimated_area_sq_km;
  const ratio = metrics?.change_ratio ?? spatial?.change_ratio;
  const regions = metrics?.regions ?? spatial?.region_count;
  const confidence = result.confidence;

  return (
    <div className="rounded-lg bg-[var(--surface-2)]/80 border border-[var(--border)] p-3 space-y-2">
      <div className="flex items-center gap-2 text-[var(--cyan)] font-semibold text-xs">
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" strokeWidth="2" />
          <line strokeWidth="2" x1="21" x2="16.65" y1="21" y2="16.65" />
        </svg>
        <span>Analysis Complete</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        {area != null && (
          <div>
            <span className="text-[var(--text-3)]">Changed Area</span>
            <p className="text-[var(--heading)] font-mono font-semibold">{area.toFixed(2)} km²</p>
          </div>
        )}
        {ratio != null && (
          <div>
            <span className="text-[var(--text-3)]">Change Ratio</span>
            <p className="text-[var(--cyan)] font-mono font-semibold">{(ratio * 100).toFixed(1)}%</p>
          </div>
        )}
        {regions != null && (
          <div>
            <span className="text-[var(--text-3)]">Regions</span>
            <p className="text-[var(--heading)] font-mono font-semibold">{regions}</p>
          </div>
        )}
        {confidence != null && (
          <div>
            <span className="text-[var(--text-3)]">Confidence</span>
            <p className="text-[var(--heading)] font-mono font-semibold">{(confidence * 100).toFixed(1)}%</p>
          </div>
        )}
      </div>
      {result.warnings?.length > 0 && (
        <div className="pt-1.5 border-t border-[var(--border)]">
          {result.warnings.slice(0, 3).map((w, i) => (
            <p key={i} className="text-[10px] text-[var(--text-3)] leading-relaxed">{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatThread({
  messages,
  isRunning,
  className,
}: {
  messages: ChatMessage[];
  isRunning?: boolean;
  className?: string;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className={cn("flex-1 overflow-y-auto p-4 space-y-4", className)}>
      {messages.map((msg) => (
        <div key={msg.id} className={cn("flex gap-2.5", msg.role === "user" ? "justify-end" : "justify-start")}>
          {msg.role === "assistant" && (
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-sky-500 flex items-center justify-center text-white shrink-0 mt-0.5">
              <svg className="w-3.5 h-3.5 -rotate-45" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <ellipse cx="12" cy="12" rx="9" ry="4" />
                <circle cx="12" cy="12" fill="currentColor" r="2" />
              </svg>
            </div>
          )}

          <div className={cn("max-w-[80%] space-y-1.5", msg.role === "user" ? "items-end" : "items-start")}>
            {msg.role === "user" && (
              <span className="text-[10px] text-[var(--text-3)] font-mono">{formatTime(msg.timestamp)}</span>
            )}

            {msg.images && msg.images.length > 0 && (
              <div className="flex gap-1.5 flex-wrap">
                {msg.images.map((src, i) => (
                  <div key={i} className="w-16 h-12 rounded-md overflow-hidden border border-[var(--border)] bg-[var(--surface-2)]">
                    <img src={src} alt={`Attached ${i + 1}`} className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
            )}

            {msg.type === "progress" ? (
              <AnalysisProgressCard content={msg.content} />
            ) : msg.type === "result" && msg.result ? (
              <AnalysisResultCard result={msg.result} />
            ) : (
              <div
                className={cn(
                  "px-3 py-2 rounded-xl text-xs leading-relaxed",
                  msg.role === "user"
                    ? "bg-[var(--cyan)] text-white rounded-br-sm"
                    : msg.type === "error"
                      ? "bg-red-500/10 border border-red-500/30 text-red-400 rounded-bl-sm"
                      : "bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text)] rounded-bl-sm"
                )}
              >
                {msg.content}
              </div>
            )}

            {msg.role === "assistant" && (
              <span className="text-[10px] text-[var(--text-3)] font-mono">{formatTime(msg.timestamp)}</span>
            )}
          </div>

          {msg.role === "user" && (
            <div className="w-6 h-6 rounded-full bg-[var(--surface-3)] flex items-center justify-center text-[var(--text-2)] shrink-0 mt-0.5">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
          )}
        </div>
      ))}

      {isRunning && messages[messages.length - 1]?.type !== "progress" && (
        <div className="flex gap-2.5">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-sky-500 flex items-center justify-center text-white shrink-0 mt-0.5">
            <svg className="w-3.5 h-3.5 -rotate-45" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <ellipse cx="12" cy="12" rx="9" ry="4" />
              <circle cx="12" cy="12" fill="currentColor" r="2" />
            </svg>
          </div>
          <AnalysisProgressCard content="Analyzing your imagery..." />
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}
