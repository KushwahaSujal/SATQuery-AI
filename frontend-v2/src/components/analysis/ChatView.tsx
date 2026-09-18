"use client";

import React, { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAnalysisStore } from "@/stores/useAnalysisStore";
import { ChatThread } from "./ChatThread";
import { ChatInput } from "./ChatInput";

const SUGGESTED_PROMPTS = [
  { text: "Detect urban expansion in this region", icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4", category: "Urban" },
  { text: "Find changes in vegetation over time", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6", category: "Vegetation" },
  { text: "Identify water bodies and monitor changes", icon: "M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4", category: "Water" },
  { text: "Generate a comprehensive analysis report", icon: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z", category: "Report" },
  { text: "Compare optical and SAR data fusion", icon: "M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2", category: "Multi-Modal" },
  { text: "Analyze land use and land cover patterns", icon: "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z", category: "Land Use" },
];

export function ChatView() {
  const router = useRouter();
  const messages = useAnalysisStore((s) => s.messages);
  const rasters = useAnalysisStore((s) => s.rasters);
  const isSubmitting = useAnalysisStore((s) => s.isSubmittingAnalysis);
  const activeJobId = useAnalysisStore((s) => s.activeJobId);
  const startAnalysis = useAnalysisStore((s) => s.startAnalysis);
  const handleUpload = useAnalysisStore((s) => s.handleUpload);

  const prevJobIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (activeJobId && activeJobId !== prevJobIdRef.current) {
      prevJobIdRef.current = activeJobId;
      router.push(`/analysis/${activeJobId}`);
    }
  }, [activeJobId, router]);

  const isRunning = isSubmitting || Boolean(activeJobId);
  const hasMessages = messages.length > 0;
  const attachedImages = rasters.map((r) => r.preview_url).filter(Boolean) as string[];
  const videoPreview = useAnalysisStore((s) => s.video?.preview_url);
  const uploadProgress = useAnalysisStore((s) => s.uploadProgress);

  return (
    <div className="flex-1 flex flex-col bg-[var(--canvas)] overflow-hidden">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="flex-1 flex flex-col relative">
        <div className="flex-1 w-full max-w-4xl mx-auto flex flex-col overflow-hidden px-6">
          {hasMessages ? (
            <ChatThread messages={messages} isRunning={isRunning} />
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="flex-1 flex flex-col justify-center py-8"
            >
              {/* Header — left aligned, asymmetric */}
              <div className="max-w-xl">
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-8 h-8 rounded-lg bg-[var(--cyan)]/10 border border-[var(--cyan)]/20 flex items-center justify-center">
                    <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="9" />
                      <line x1="12" y1="2" x2="12" y2="6" />
                      <line x1="12" y1="18" x2="12" y2="22" />
                      <line x1="2" y1="12" x2="6" y2="12" />
                      <line x1="18" y1="12" x2="22" y2="12" />
                    </svg>
                  </div>
                  <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--cyan)]">SatQuery AI</span>
                </div>
                <h1 className="text-3xl font-bold text-[var(--heading)] tracking-tight leading-tight">
                  What would you like to analyze?
                </h1>
                <p className="text-sm text-[var(--text-2)] mt-2 leading-relaxed">
                  Upload satellite imagery and ask anything. Change detection, land classification, object counting, vegetation analysis.
                </p>
              </div>

              {/* Quick Actions — horizontal strip, not cards */}
              <div className="mt-8 flex gap-2 flex-wrap">
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

              {/* Divider */}
              <div className="mt-8 pt-6 border-t border-[var(--border)]">
                <p className="text-[10px] uppercase font-semibold text-[var(--text-3)] tracking-wider mb-4">
                  Suggested analyses
                </p>
                <div className="grid grid-cols-1 gap-1">
                  {SUGGESTED_PROMPTS.map((item) => (
                    <button
                      key={item.text}
                      onClick={() => startAnalysis(item.text)}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-[var(--surface)] transition group"
                    >
                      <div className="w-5 h-5 rounded bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center shrink-0">
                        <svg className="w-2.5 h-2.5 text-[var(--text-3)] group-hover:text-[var(--cyan)] transition-colors" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d={item.icon} strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <span className="text-xs text-[var(--text-2)] group-hover:text-[var(--heading)] flex-1">
                        {item.text}
                      </span>
                      <span className="text-[9px] text-[var(--text-4)] font-mono uppercase tracking-wider shrink-0">
                        {item.category}
                      </span>
                      <svg className="w-3 h-3 text-[var(--text-4)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Chat Input */}
        <div className="w-full max-w-3xl mx-auto px-6 pb-6">
          <ChatInput
            onSubmit={(text, type) => startAnalysis(text, type)}
            onUpload={handleUpload}
            attachedImages={attachedImages}
            videoPreview={videoPreview}
            uploadProgress={uploadProgress}
            disabled={isSubmitting}
            variant="centered"
          />
        </div>
      </div>
    </div>
  );
}
