"use client";

import React, { useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { ProgressiveFluxLoader } from "@/components/ui/progressive-flux-loader";
import type { TaskType } from "@/lib/types";

type AnalysisType = TaskType | "auto";

const ANALYSIS_TYPES: { value: AnalysisType; label: string; icon: string; category: string }[] = [
  { value: "auto", label: "Auto Detect", icon: "M13 10V3L4 14h7v7l9-11h-7z", category: "Smart" },
  { value: "single_image_vqa", label: "Image Analysis", icon: "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z", category: "Single Image" },
  { value: "single_image_caption", label: "Captioning", icon: "M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z", category: "Single Image" },
  { value: "single_image_grounding", label: "Object Detection", icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z", category: "Single Image" },
  { value: "bi_temporal_change", label: "Change Detection", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6", category: "Change Analysis" },
  { value: "bi_temporal_change_vqa", label: "Change VQA", icon: "M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2", category: "Change Analysis" },
  { value: "optical_sar_analysis", label: "Optical + SAR", icon: "M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4", category: "Multi-Modal" },
  { value: "video_vqa", label: "Video Analysis", icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z", category: "Video" },
  { value: "video_grounding", label: "Video Grounding", icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z", category: "Video" },
  { value: "video_change", label: "Video Change", icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z", category: "Video" },
];

export function ChatInput({
  onSubmit,
  onUpload,
  attachedImages = [],
  attachedImageLabels = [],
  videoPreview,
  uploadProgress,
  disabled = false,
  variant = "centered",
  className,
}: {
  onSubmit: (text: string, type?: AnalysisType) => void;
  onUpload: (files: FileList) => void;
  attachedImages?: string[];
  attachedImageLabels?: string[];
  videoPreview?: string | null;
  uploadProgress?: number | null;
  disabled?: boolean;
  variant?: "centered" | "compact";
  className?: string;
}) {
  const [text, setText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [analysisType, setAnalysisType] = useState<AnalysisType>("auto");
  const [showTypeSelector, setShowTypeSelector] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    if (!text.trim() || disabled) return;
    onSubmit(text.trim(), analysisType);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, disabled, onSubmit, analysisType]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files);
    }
  }, [onUpload]);

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  const isCentered = variant === "centered";
  const currentType = ANALYSIS_TYPES.find((t) => t.value === analysisType);

  return (
    <div
      className={cn(
        isCentered ? "px-0 pb-0" : "p-3 border-t border-[var(--border)]",
        isDragging && "ring-2 ring-[var(--cyan)]/50 ring-offset-2 ring-offset-[var(--canvas)]",
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Attached Image/Video Previews */}
      {!disabled && (attachedImages.length > 0 || videoPreview) && (
        <div className="mb-2 flex max-h-[76px] items-center gap-2 overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface-2)]/60 px-2 py-1.5">
          <div className="flex shrink-0 flex-col justify-center pr-1">
            <span className="text-[9px] font-semibold uppercase tracking-wider text-[var(--text-3)]">
              Sources
            </span>
            <span className="text-[9px] text-[var(--text-3)]">
              {attachedImages.length + (videoPreview ? 1 : 0)} attached
            </span>
          </div>
          <div className="flex shrink-0 gap-2">
          {videoPreview && (
            <div className="relative group">
              <div className="h-12 w-12 rounded-lg overflow-hidden border border-purple-500/30 bg-[var(--surface-2)] sm:h-14 sm:w-14">
                <img src={videoPreview} alt="Video" className="w-full h-full object-cover" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-purple-500 text-white flex items-center justify-center shadow">
                <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
          )}
          {attachedImages.map((src, i) => (
            <div key={i} className="relative group">
              <div className="h-12 w-12 rounded-lg overflow-hidden border border-[var(--cyan)]/30 bg-[var(--surface-2)] sm:h-14 sm:w-14">
                <img
                  src={src}
                  alt={attachedImageLabels[i] || `Attached ${i + 1}`}
                  className="relative z-10 h-full w-full object-cover"
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                  }}
                />
                <div className="absolute inset-0 z-0 flex flex-col items-center justify-center gap-1 p-1 text-center">
                  <svg className="h-5 w-5 text-[var(--cyan)]/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M4 5a2 2 0 012-2h8l6 6v10a2 2 0 01-2 2H6a2 2 0 01-2-2V5zM14 3v6h6" strokeWidth="1.5" />
                  </svg>
                  <span className="max-w-full truncate text-[8px] text-[var(--text-3)]">
                    {attachedImageLabels[i] || `Raster ${i + 1}`}
                  </span>
                </div>
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--cyan)] text-white flex items-center justify-center text-[8px] font-bold shadow">
                {i + 1}
              </div>
            </div>
          ))}
          <div className="h-12 w-12 rounded-lg border-2 border-dashed border-[var(--border)] flex items-center justify-center text-[var(--text-3)] hover:border-[var(--cyan)]/50 hover:text-[var(--cyan)] transition cursor-pointer sm:h-14 sm:w-14" onClick={() => fileRef.current?.click()}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <line x1="12" x2="12" y1="5" y2="19" />
              <line x1="5" x2="19" y1="12" y2="12" />
            </svg>
          </div>
          </div>
        </div>
      )}

      {/* Upload Progress Bar */}
      {uploadProgress != null && (
        <div className="mb-2">
          <ProgressiveFluxLoader
            value={uploadProgress}
            phases={[
              { at: 0, label: "uploading..." },
              { at: 40, label: "processing..." },
              { at: 75, label: "finalizing..." },
              { at: 100, label: "complete" },
            ]}
            showLabel={true}
          />
        </div>
      )}

      <div
        className={cn(
          "relative bg-[var(--surface)] border transition-all duration-200",
          isDragging
            ? "border-[var(--cyan)] shadow-[0_0_20px_rgba(6,182,212,0.15)]"
            : "border-[var(--border)] focus-within:border-[var(--cyan)]/50 focus-within:shadow-[0_0_15px_rgba(6,182,212,0.1)]",
          isCentered ? "rounded-2xl p-3 sm:p-4" : "rounded-xl p-2.5"
        )}
      >
        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 rounded-[inherit] bg-[var(--cyan)]/5 flex items-center justify-center z-10 pointer-events-none">
            <div className="flex flex-col items-center gap-1">
              <svg className="w-6 h-6 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path d="M12 16V4m0 0L8 8m4-4l4 4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-[10px] text-[var(--cyan)] font-medium">Drop images here</span>
            </div>
          </div>
        )}

        {/* Textarea */}
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleTextareaChange}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            rows={1}
            className={cn(
              "flex-1 bg-transparent border-0 text-[var(--heading)] placeholder-[var(--text-3)] focus:outline-none resize-none leading-relaxed",
              isCentered ? "text-sm" : "text-xs"
            )}
            placeholder={isCentered ? "Describe what you want to analyze from your satellite imagery..." : "Ask a follow-up question..."}
            disabled={disabled}
            style={{ minHeight: isCentered ? "36px" : "32px" }}
          />

          <button
            onClick={handleSubmit}
            disabled={!text.trim() || disabled}
            className={cn(
              "rounded-xl flex items-center justify-center font-bold transition-all duration-200 shrink-0",
              isCentered ? "w-10 h-10" : "w-8 h-8",
              text.trim() && !disabled
                ? "bg-gradient-to-r from-cyan-500 to-sky-500 text-white hover:brightness-110 hover:shadow-lg hover:shadow-cyan-500/25 cursor-pointer active:scale-95"
                : "bg-[var(--surface-3)] text-[var(--text-3)] cursor-not-allowed"
            )}
          >
            <svg className={cn(isCentered ? "w-4 h-4" : "w-3.5 h-3.5")} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Bottom Toolbar */}
        {isCentered && (
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--border)]">
            <div className="flex items-center gap-1.5">
              {/* Attach button */}
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={disabled}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--cyan)]/40 hover:bg-[var(--surface-hover)] text-[10px] text-[var(--text-2)] transition"
              >
                <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <rect height="18" rx="2" strokeWidth="2" width="18" x="3" y="3" />
                  <circle cx="8.5" cy="8.5" fill="currentColor" r="1.5" />
                  <path d="M21 15l-5-5L5 21" strokeWidth="2" />
                </svg>
                <span>Attach</span>
              </button>

              {/* Analysis Type Selector */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowTypeSelector(!showTypeSelector)}
                  disabled={disabled}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--cyan)]/40 hover:bg-[var(--surface-hover)] text-[10px] text-[var(--text-2)] transition"
                >
                  <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d={currentType?.icon} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                  <span>{currentType?.label}</span>
                  <svg className="w-2.5 h-2.5 text-[var(--text-3)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </button>

                {showTypeSelector && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowTypeSelector(false)} />
                    <div className="absolute bottom-full left-0 mb-1 w-56 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-2xl z-50 overflow-hidden max-h-80 overflow-y-auto">
                      {["Smart", "Single Image", "Change Analysis", "Multi-Modal", "Video"].map((cat) => {
                        const items = ANALYSIS_TYPES.filter((t) => t.category === cat);
                        if (items.length === 0) return null;
                        return (
                          <div key={cat}>
                            <div className="px-3 py-1.5 text-[9px] uppercase font-semibold text-[var(--text-3)] tracking-wider bg-[var(--surface-2)]">
                              {cat}
                            </div>
                            {items.map((type) => (
                              <button
                                key={type.value}
                                onClick={() => { setAnalysisType(type.value); setShowTypeSelector(false); }}
                                className={cn(
                                  "w-full flex items-center gap-2.5 px-3 py-2 text-[11px] transition text-left",
                                  analysisType === type.value
                                    ? "bg-[var(--cyan)]/10 text-[var(--cyan)]"
                                    : "text-[var(--text-2)] hover:bg-[var(--surface-hover)]"
                                )}
                              >
                                <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path d={type.icon} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                                </svg>
                                <span className="font-medium">{type.label}</span>
                                {analysisType === type.value && (
                                  <svg className="w-3 h-3 ml-auto text-[var(--cyan)]" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                  </svg>
                                )}
                              </button>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>

              <span className="text-[9px] text-[var(--text-3)] ml-1">.tif · .png · .jpg · .mp4</span>
            </div>

            <div className="flex items-center gap-2 text-[9px] text-[var(--text-3)]">
              <kbd className="px-1 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] font-mono">Enter</kbd>
              <span>to send</span>
              <kbd className="px-1 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] font-mono">Shift+Enter</kbd>
              <span>new line</span>
            </div>
          </div>
        )}
      </div>

      <input
        ref={fileRef}
        type="file"
        multiple
        accept=".tif,.tiff,.png,.jpg,.jpeg,.mp4,.avi,.mov,.mkv,.webm"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) onUpload(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
