"use client";

import { useRef, useState, useEffect } from "react";
import type { TaskType } from "@/lib/types";

const TASK_OPTIONS: { value: TaskType; label: string; desc: string; color: string }[] = [
  { value: "unsupported", label: "AUTO", desc: "Auto-detect task from query", color: "var(--accent-text)" },
  { value: "single_image_vqa", label: "VQA", desc: "Visual question answering", color: "var(--cyan)" },
  { value: "single_image_grounding", label: "GROUNDING", desc: "Ground language to image regions", color: "var(--purple)" },
  { value: "bi_temporal_change", label: "CHANGE", desc: "Detect change between two images", color: "var(--accent-text)" },
  { value: "bi_temporal_change_vqa", label: "TEMPORAL VQA", desc: "VQA across temporal image pairs", color: "var(--cyan)" },
  { value: "single_image_caption", label: "CAPTION", desc: "Generate scene description", color: "var(--amber)" },
  { value: "video_grounding_tracking", label: "VIDEO", desc: "Video stream analysis & tracking", color: "var(--red)" },
];

const EXAMPLE_CHIPS = [
  { icon: "🏗", label: "Building damage", query: "Identify all buildings damaged between image A and image B" },
  { icon: "🌊", label: "Flood extent",    query: "Detect flood extent in the eastern district" },
  { icon: "🌿", label: "NDVI change",     query: "Compare vegetation cover between T1 and T2" },
  { icon: "🚗", label: "Vehicle count",   query: "Count the number of vehicles in the parking lot" },
];

interface QueryBarProps {
  query: string;
  setQuery: (v: string) => void;
  taskOverride: TaskType;
  setTaskOverride: (v: TaskType) => void;
  onAnalyze: () => void;
  disabled: boolean;
  loading: boolean;
  error?: string | null;
}

export default function QueryBar({
  query, setQuery, taskOverride, setTaskOverride,
  onAnalyze, disabled, loading, error,
}: QueryBarProps) {
  const [taskOpen, setTaskOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const selectedTask = TASK_OPTIONS.find(t => t.value === taskOverride) ?? TASK_OPTIONS[0];
  const canRun = !disabled && !loading;

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setTaskOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if ((e.key === "Enter") && !disabled && !loading) onAnalyze();
    if (e.key === "Escape") { setTaskOpen(false); inputRef.current?.blur(); }
  }

  return (
    <div className="border-t border-[var(--b0)] bg-[var(--s1)]">
      {/* Suggestion chips (only when no query typed) */}
      {!query && !loading && (
        <div className="flex items-center gap-1.5 px-4 pt-2.5 pb-1 flex-wrap">
          <span className="font-mono-data text-[9px] text-[var(--t4)] tracking-widest flex-shrink-0 uppercase">
            Try:
          </span>
          {EXAMPLE_CHIPS.map(chip => (
            <button
              key={chip.label}
              onClick={() => { setQuery(chip.query); inputRef.current?.focus(); }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--s2)] border border-[var(--b1)] cursor-pointer transition-all hover:bg-[var(--s3)] hover:border-[var(--b3)] active:scale-95"
            >
              <span className="text-[11px]">{chip.icon}</span>
              <span className="font-mono-data text-[10px] text-[var(--t2)]">
                {chip.label}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Main input bar */}
      <div className="flex items-stretch h-11 mx-3 mb-2.5 rounded-lg bg-[var(--s2)] border border-[var(--b2)] transition-all duration-200"
        style={{
          boxShadow: focused ? "0 0 0 1px var(--accent), 0 0 12px var(--accent-dim)" : "none",
        }}
      >
        {/* >_ prompt glyph */}
        <div className="flex items-center pl-3 pr-2 flex-shrink-0">
          <span
            className={`font-mono-data text-sm font-bold leading-none transition-colors duration-200 select-none ${
              focused ? "text-[var(--accent)]" : "text-[var(--t3)]"
            }`}
          >
            &gt;_
          </span>
        </div>

        {/* Input field */}
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ask a question about the uploaded imagery..."
          className="flex-1 bg-transparent border-none outline-none font-mono-data text-[13px] text-[var(--t0)] py-2.5 caret-[var(--accent)] query-input min-w-0"
        />

        {/* Enter hint */}
        {focused && query && (
          <div className="flex items-center pr-3 flex-shrink-0">
            <span className="font-mono-data text-[9px] text-[var(--t4)] bg-[var(--s3)] px-1.5 py-0.5 rounded border border-[var(--b2)]">
              ↵
            </span>
          </div>
        )}

        {/* Task selector */}
        <div ref={dropdownRef} className="relative flex items-center pr-1 flex-shrink-0">
          <button
            onClick={() => setTaskOpen(o => !o)}
            className={`flex items-center gap-1 px-2.5 h-7 my-auto rounded text-[10px] font-bold tracking-wider font-mono-data transition-all cursor-pointer border ${
              taskOpen
                ? "bg-[var(--accent-dim)] text-[var(--accent-text)] border-[var(--accent)]"
                : "bg-[var(--s3)] text-[var(--t2)] border-[var(--b2)] hover:border-[var(--b3)] hover:text-[var(--t1)]"
            }`}
            style={!taskOpen ? { color: selectedTask.color } : undefined}
          >
            {selectedTask.label}
            <svg
              width="8" height="8" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round"
              className={`transition-transform duration-150 ${taskOpen ? "rotate-180" : ""}`}
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>

          {/* Dropdown */}
          {taskOpen && (
            <div className="absolute bottom-full mb-2 right-0 w-56 bg-[var(--s3)] border border-[var(--b2)] rounded-lg overflow-hidden z-60 shadow-[0_-4px_24px_rgba(0,0,0,0.4)] animate-slide-down">
              <div className="px-3 py-1.5 border-b border-[var(--b1)]">
                <span className="font-mono-data text-[8px] text-[var(--t4)] tracking-[0.1em] uppercase">
                  Task Type
                </span>
              </div>
              <div className="py-0.5">
                {TASK_OPTIONS.map(opt => {
                  const isActive = opt.value === taskOverride;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => { setTaskOverride(opt.value); setTaskOpen(false); }}
                      className={`flex items-center gap-2 w-full text-left px-3 py-1.5 border-none cursor-pointer transition-colors ${
                        isActive
                          ? "bg-[var(--accent-dim)]"
                          : "bg-transparent hover:bg-[var(--s4)]"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                          isActive ? "bg-[var(--accent)]" : "bg-[var(--b3)]"
                        }`}
                      />
                      <div className="min-w-0">
                        <span
                          className="font-mono-data text-[10px] font-bold tracking-wider block leading-tight"
                          style={{ color: isActive ? "var(--accent-text)" : opt.color }}
                        >
                          {opt.label}
                        </span>
                        <span className="text-[9px] text-[var(--t4)] block leading-tight truncate">
                          {opt.desc}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-px bg-[var(--b2)] flex-shrink-0 self-stretch my-1.5" />

        {/* Run button */}
        <button
          onClick={onAnalyze}
          disabled={!canRun}
          title={canRun ? "Run analysis (Enter)" : "Upload data and enter a query first"}
          className={`flex items-center gap-1.5 px-4 my-1 mr-1 rounded transition-all flex-shrink-0 font-mono-data text-[11px] font-bold tracking-wider ${
            canRun
              ? "bg-[var(--accent)] text-white cursor-pointer hover:brightness-110"
              : "bg-[var(--s3)] text-[var(--t4)] cursor-not-allowed"
          }`}
        >
          {loading ? (
            <>
              <span className="animate-spin-smooth w-3 h-3 border-2 border-white/30 border-t-white rounded-full" />
              <span>Running</span>
            </>
          ) : (
            <>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>Run</span>
            </>
          )}
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 mx-3 mb-2 px-3 py-2 rounded-lg bg-[var(--red-dim)] border border-[hsla(0,80%,66%,0.2)]">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
            stroke="var(--red)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p className="font-mono-data text-[11px] text-[var(--red)] m-0">
            {error}
          </p>
        </div>
      )}
    </div>
  );
}
