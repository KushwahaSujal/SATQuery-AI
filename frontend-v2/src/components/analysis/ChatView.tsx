"use client";

import React, { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useAnalysisStore } from "@/stores/useAnalysisStore";
import { ChatThread } from "./ChatThread";
import { ChatInput } from "./ChatInput";
import { cn } from "@/lib/utils";
import {Sparkles} from "lucide-react";

const SUGGESTED_PROMPTS = [
  { text: "Detect urban expansion in this region", icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4", category: "Urban" },
  { text: "Find changes in vegetation over time", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6", category: "Vegetation" },
  { text: "Identify water bodies and monitor changes", icon: "M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4", category: "Water" },
  { text: "Generate a comprehensive analysis report", icon: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z", category: "Report" },
  { text: "Compare optical and SAR data fusion", icon: "M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2", category: "Multi-Modal" },
  { text: "Analyze land use and land cover patterns", icon: "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z", category: "Land Use" },
];

export function ChatView({ initialPrompt }: { initialPrompt?: string } = {}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const messages = useAnalysisStore((s) => s.messages);
  const rasters = useAnalysisStore((s) => s.rasters);
  const isSubmitting = useAnalysisStore((s) => s.isSubmittingAnalysis);
  const activeJobId = useAnalysisStore((s) => s.activeJobId);
  const activeJobIsVideo = useAnalysisStore((s) => s.activeJobIsVideo);
  const startAnalysis = useAnalysisStore((s) => s.startAnalysis);
  const handleUpload = useAnalysisStore((s) => s.handleUpload);
  const resetAnalysis = useAnalysisStore((s) => s.resetAnalysis);

  const prevJobIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (activeJobId && activeJobId !== prevJobIdRef.current) {
      prevJobIdRef.current = activeJobId;
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      // Keep video and raster results in the same analysis workspace. The
      // result page switches its content based on the persisted task type.
      router.push(`/analysis/${activeJobId}`);
    }
  }, [activeJobId, activeJobIsVideo, queryClient, router]);

  const isRunning = isSubmitting || Boolean(activeJobId);
  const hasMessages = messages.length > 0;
  const attachedImages = rasters.map((r) => r.preview_url).filter(Boolean) as string[];
  const attachedImageLabels = rasters.map((r) => r.filename);
  const videoPreview = useAnalysisStore((s) => s.video?.preview_url);
  const uploadProgress = useAnalysisStore((s) => s.uploadProgress);
  const hasSources = attachedImages.length > 0 || Boolean(videoPreview);

  return (
    <div className="relative h-full min-h-0 flex-1 flex flex-col bg-[var(--canvas)] overflow-hidden">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative flex min-h-0 flex-1 flex-col">
        {hasMessages && (
          <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 pt-3">
            <div className="flex items-center justify-between rounded-2xl border border-[var(--border)] bg-[var(--surface)]/90 px-4 py-3 shadow-sm">
              <div className="flex min-w-0 items-center gap-2.5">
                <span className={cn("h-2 w-2 rounded-full", isRunning ? "bg-amber-400 animate-pulse" : "bg-emerald-400")} />
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-[var(--heading)]">
                    {isRunning ? "Analysis in progress" : "Analysis conversation"}
                  </p>
                  <p className="text-[10px] text-[var(--text-3)]">
                    {rasters.length + (videoPreview ? 1 : 0)} source{rasters.length + (videoPreview ? 1 : 0) === 1 ? "" : "s"} attached
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={resetAnalysis}
                disabled={isRunning}
                className="shrink-0 rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-[10px] font-medium text-[var(--text-2)] transition hover:border-[var(--cyan)]/40 hover:text-[var(--heading)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                New analysis
              </button>
            </div>
          </div>
        )}

        <div className="flex min-h-0 w-full max-w-5xl mx-auto flex-1 flex-col overflow-hidden px-4 sm:px-6">
          {hasMessages ? (
            <ChatThread messages={messages} isRunning={isRunning} />
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="flex min-h-0 flex-1 flex-col justify-center overflow-y-auto py-5 sm:py-8"
            >
              {/* Header — left aligned, asymmetric */}
              <div className={cn("mx-auto w-full max-w-3xl text-center", hasSources && "scale-[0.96]")}>
                <div className="mb-4 flex items-center justify-center gap-3">
                  <div className="w-6 h-6 rounded-lg bg-[var(--cyan)]/10 border border-[var(--cyan)]/20 flex items-center justify-center">
                    <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-[var(--cyan)] to-[var(--teal)] flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="w-4 h-4 text-[var(--canvas)]" />
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--cyan)]">SatQuery AI</span>
                </div>
                <h1 className="text-3xl font-bold tracking-tight leading-tight text-[var(--heading)] sm:text-4xl">
                  What would you like to analyze?
                </h1>
                <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-[var(--text-2)]">
                  Upload satellite imagery and ask anything. Change detection, land classification, object counting, vegetation analysis.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-2 text-[10px] text-[var(--text-3)]">
                  <span>Images + video</span>
                  <span className="text-[var(--border)]">•</span>
                  <span>Evidence-backed results</span>
                  <span className="text-[var(--border)]">•</span>
                  <span>Automatic task routing</span>
                </div>
              </div>

              {/* Quick Actions — horizontal strip, not cards */}
              {!hasSources && (
              <div className="mx-auto mt-8 flex w-full max-w-3xl flex-wrap justify-center gap-2">
                {[
                  { label: "Change Detection", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6", prompt: "Detect changes between two dates" },
                  { label: "Land Classification", icon: "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064", prompt: "Classify land cover types" },
                  { label: "Object Detection", icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z", prompt: "Detect and count objects in the imagery" },
                  { label: "Generate Report", icon: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z", prompt: "Generate a comprehensive analysis report" },
                ].map((item) => (
                  <button
                    key={item.label}
                    onClick={() => startAnalysis(item.prompt)}
                    className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--cyan)]/40 hover:bg-[var(--surface-2)] transition-all text-left group"
                  >
                    <svg className="w-3.5 h-3.5 text-[var(--text-3)] group-hover:text-[var(--cyan)] transition-colors" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d={item.icon} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="text-xs font-medium text-[var(--text-2)] group-hover:text-[var(--heading)]">{item.label}</span>
                  </button>
                ))}
              </div>
              )}

              {/* Divider */}
              {!hasSources && <div className="mx-auto mt-8 w-full max-w-3xl border-t border-[var(--border)] pt-5">
                <p className="mb-3 text-center text-[10px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
                  Suggested analyses
                </p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {SUGGESTED_PROMPTS.map((item) => (
                    <button
                      key={item.text}
                      onClick={() => startAnalysis(item.text)}
                      className="group flex min-h-12 items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)]/50 px-3 py-2.5 text-left transition hover:border-[var(--cyan)]/40 hover:bg-[var(--surface)]"
                    >
                      <div className="w-5 h-5 rounded bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center shrink-0">
                        <svg className="w-2.5 h-2.5 text-[var(--text-3)] group-hover:text-[var(--cyan)] transition-colors" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d={item.icon} strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <span className="flex-1 text-xs text-[var(--text-2)] group-hover:text-[var(--heading)]">
                        {item.text}
                      </span>
                      <span className="hidden shrink-0 text-[9px] font-mono uppercase tracking-wider text-[var(--text-4)] sm:block">
                        {item.category}
                      </span>
                      <svg className="w-3 h-3 text-[var(--text-4)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  ))}
                </div>
              </div>}
            </motion.div>
          )}
        </div>

        {/* Chat Input */}
        <div className="w-full shrink-0 border-t border-[var(--border)] bg-[var(--canvas)]/95 px-3 pb-3 pt-2 backdrop-blur sm:px-6 sm:pb-4 sm:pt-3">
          <div className="mx-auto max-w-4xl">
          <ChatInput
            onSubmit={(text, type) => startAnalysis(text, type)}
            onUpload={handleUpload}
            attachedImages={attachedImages}
            attachedImageLabels={attachedImageLabels}
            videoPreview={videoPreview}
            uploadProgress={uploadProgress}
            disabled={isRunning}
            initialPrompt={initialPrompt}
            variant="centered"
          />
          </div>
        </div>
      </div>
    </div>
  );
}
