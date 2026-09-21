"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalysisStore } from "@/stores/useAnalysisStore";
import { ChatThread } from "./ChatThread";
import { ChatInput } from "./ChatInput";
import { ResultsCanvas } from "./ResultsCanvas";

type Tab = "chat" | "analysis" | "trace";

export function ResultsView() {
  const router = useRouter();
  const messages = useAnalysisStore((s) => s.messages);
  const rasters = useAnalysisStore((s) => s.rasters);
  const isSubmitting = useAnalysisStore((s) => s.isSubmittingAnalysis);
  const activeJobId = useAnalysisStore((s) => s.activeJobId);
  const liveResult = useAnalysisStore((s) => s.liveResult);
  const liveJob = useAnalysisStore((s) => s.liveJob);
  const resetAnalysis = useAnalysisStore((s) => s.resetAnalysis);
  const startAnalysis = useAnalysisStore((s) => s.startAnalysis);
  const handleUpload = useAnalysisStore((s) => s.handleUpload);

  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [layerSelect, setLayerSelect] = useState("Natural Color (RGB)");
  const [modeSelect, setModeSelect] = useState<"compare" | "change_map" | "overlay">("compare");
  const [opacity, setOpacity] = useState(70);
  const [layerTab, setLayerTab] = useState<"images" | "layers">("images");
  const [layersToggle, setLayersToggle] = useState({
    changeDetection: true,
    urbanArea: false,
    vegetation: false,
    waterBodies: false,
  });

  const isRunning = isSubmitting || Boolean(activeJobId && (!liveJob || ["QUEUED", "CREATED", "UPLOADED", "VALIDATING", "PLANNING", "RUNNING", "GENERATING_EVIDENCE", "PENDING"].includes(liveJob.status)));
  const attachedImages = rasters.map((r) => r.preview_url).filter(Boolean) as string[];

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Chat Panel */}
      <div className="w-[420px] bg-[var(--surface)] flex flex-col shrink-0 border-r border-[var(--border)]">
        {/* Header */}
        <div className="h-11 px-4 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-5 text-xs">
            {(["chat", "analysis", "trace"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`h-11 flex items-center px-1 font-semibold transition ${
                  activeTab === tab
                    ? "text-[var(--cyan)] border-b-2 border-[var(--cyan)]"
                    : "text-[var(--text-3)] hover:text-[var(--text)]"
                }`}
              >
                {tab === "chat" ? "Chat" : tab === "analysis" ? "Analysis" : "Trace"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => { resetAnalysis(); router.push("/analysis"); }}
              className="text-[10px] text-[var(--text-3)] hover:text-[var(--cyan)] px-2 py-0.5 rounded border border-[var(--border)] hover:border-[var(--cyan)]/40 transition"
            >
              New Analysis
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {activeTab === "chat" && (
            <>
              <ChatThread messages={messages} isRunning={isRunning} />
              <ChatInput
                onSubmit={(text) => startAnalysis(text)}
                onUpload={handleUpload}
                attachedImages={attachedImages}
                disabled={isSubmitting}
                variant="compact"
              />
            </>
          )}

          {activeTab === "analysis" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
                <h3 className="text-xs font-semibold text-[var(--heading)] mb-2">Change Classification Summary</h3>
                <div className="space-y-2 text-[11px]">
                  {liveResult ? (
                    <>
                      <div className="flex justify-between">
                        <span className="text-[var(--text-3)]">Status</span>
                        <span className="text-[var(--cyan)] font-mono">{liveResult.status}</span>
                      </div>
                      {liveResult.metrics?.area_km2 != null && (
                        <div className="flex justify-between">
                          <span className="text-[var(--text-3)]">Changed Area</span>
                          <span className="text-[var(--cyan)] font-mono">{liveResult.metrics.area_km2.toFixed(2)} km²</span>
                        </div>
                      )}
                      {liveResult.metrics?.change_ratio != null && (
                        <div className="flex justify-between">
                          <span className="text-[var(--text-3)]">Change Ratio</span>
                          <span className="text-[var(--cyan)] font-mono">{(liveResult.metrics.change_ratio * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {liveResult.confidence != null && (
                        <div className="flex justify-between">
                          <span className="text-[var(--text-3)]">Confidence</span>
                          <span className="text-[var(--cyan)] font-mono">{(liveResult.confidence * 100).toFixed(1)}%</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-[var(--text-3)]">No analysis results yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "trace" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-2 text-[11px]">
              {liveResult?.execution_trace?.length ? (
                liveResult.execution_trace.map((step, idx) => (
                  <div key={idx} className="p-2 rounded bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${step.status === "success" ? "bg-emerald-400" : step.status === "error" ? "bg-red-400" : "bg-amber-400"}`} />
                      <span className="text-[var(--text-2)]">{step.step || step.tool || "Pipeline step"}</span>
                    </div>
                    {step.duration_ms != null && (
                      <span className="text-[10px] font-mono text-[var(--text-3)]">
                        {step.duration_ms > 1000 ? `${(step.duration_ms / 1000).toFixed(1)}s` : `${step.duration_ms}ms`}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-[var(--text-3)]">No trace data available.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Results Canvas */}
      <ResultsCanvas
        layerSelect={layerSelect}
        setLayerSelect={setLayerSelect}
        modeSelect={modeSelect}
        setModeSelect={setModeSelect}
        opacity={opacity}
        setOpacity={setOpacity}
        layerTab={layerTab}
        setLayerTab={setLayerTab}
        layersToggle={layersToggle}
        setLayersToggle={setLayersToggle}
      />
    </div>
  );
}
