"use client";

import { useRef, useState, useEffect } from "react";
import type { TaskType } from "@/lib/types";

const TASK_OPTIONS: { value: TaskType; label: string; desc: string; color: string }[] = [
  { value: "AUTO",             label: "AUTO",           desc: "Auto-detect task from query",         color: "var(--accent-text)" },
  { value: "VQA",              label: "VQA",            desc: "Visual question answering",            color: "var(--cyan)" },
  { value: "GROUNDING",        label: "GROUNDING",      desc: "Ground language to image regions",     color: "var(--purple)" },
  { value: "CHANGE",           label: "CHANGE",         desc: "Detect change between two images",     color: "var(--accent-text)" },
  { value: "TEMPORAL_VQA",     label: "TEMPORAL VQA",   desc: "VQA across temporal image pairs",      color: "var(--cyan)" },
  { value: "VISUAL_ANALYTICS", label: "VIS. ANALYTICS", desc: "Generate charts and analytics",        color: "var(--amber)" },
  { value: "VIDEO",            label: "VIDEO",          desc: "Video stream analysis & tracking",     color: "var(--red)" },
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
    <div>
      {/* ── Suggestion chips (only when no query typed) ── */}
      {!query && !loading && (
        <div style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "7px 14px 0",
          flexWrap: "wrap",
        }}>
          <span style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: 9, color: "var(--t4)", letterSpacing: "0.06em",
            flexShrink: 0, textTransform: "uppercase",
          }}>
            Try:
          </span>
          {EXAMPLE_CHIPS.map(chip => (
            <button
              key={chip.label}
              onClick={() => { setQuery(chip.query); inputRef.current?.focus(); }}
              style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "2px 8px", borderRadius: 10,
                background: "var(--s2)", border: "1px solid var(--b1)",
                cursor: "pointer", transition: "all 0.12s",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = "var(--s3)";
                (e.currentTarget as HTMLElement).style.borderColor = "var(--b3)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = "var(--s2)";
                (e.currentTarget as HTMLElement).style.borderColor = "var(--b1)";
              }}
            >
              <span style={{ fontSize: 10 }}>{chip.icon}</span>
              <span style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: 10, color: "var(--t2)",
              }}>
                {chip.label}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* ── Main bar ── */}
      <div style={{
        display: "flex", alignItems: "stretch",
        height: 50,
        margin: "6px 0 0",
        background: focused ? "var(--s2)" : "var(--s1)",
        borderTop: `1px solid ${focused ? "var(--b2)" : "var(--b0)"}`,
        boxShadow: focused ? "0 -2px 12px rgba(0,0,0,0.3), inset 0 1px 0 var(--accent-dim)" : "none",
        transition: "all 0.18s",
      }}>

        {/* >_ glyph */}
        <div style={{
          display: "flex", alignItems: "center",
          padding: "0 12px 0 16px", flexShrink: 0,
          borderRight: "1px solid var(--b0)",
        }}>
          <span style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: 14, fontWeight: 700, lineHeight: 1,
            color: focused ? "var(--accent)" : "var(--t3)",
            textShadow: focused ? "0 0 10px var(--accent-glow)" : "none",
            transition: "color 0.18s, text-shadow 0.18s",
            userSelect: "none",
          }}>
            &gt;_
          </span>
        </div>

        {/* Input */}
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ask a question about the uploaded imagery…"
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: 13,
            color: "var(--t0)",
            padding: "0 16px",
            caretColor: "var(--accent)",
            /* placeholder color handled via CSS class below */
          }}
          className="query-input"
        />

        {/* Hint text when focused + has query */}
        {focused && query && (
          <div style={{
            display: "flex", alignItems: "center",
            paddingRight: 10, flexShrink: 0,
          }}>
            <span style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 9, color: "var(--t4)", letterSpacing: "0.04em",
            }}>
              ↵ to run
            </span>
          </div>
        )}

        {/* Task selector */}
        <div
          ref={dropdownRef}
          style={{ position: "relative", flexShrink: 0, display: "flex", alignItems: "center", padding: "0 6px" }}
        >
          <button
            onClick={() => setTaskOpen(o => !o)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 10px",
              background: taskOpen ? "var(--s4)" : "var(--s2)",
              border: `1px solid ${taskOpen ? "var(--accent)" : "var(--b2)"}`,
              borderRadius: 5,
              cursor: "pointer",
              transition: "all 0.12s",
              height: 32,
            }}
            onMouseEnter={e => {
              if (!taskOpen) {
                (e.currentTarget as HTMLElement).style.background = "var(--s3)";
                (e.currentTarget as HTMLElement).style.borderColor = "var(--b3)";
              }
            }}
            onMouseLeave={e => {
              if (!taskOpen) {
                (e.currentTarget as HTMLElement).style.background = "var(--s2)";
                (e.currentTarget as HTMLElement).style.borderColor = "var(--b2)";
              }
            }}
          >
            <span style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 10, fontWeight: 700,
              color: selectedTask.color,
              letterSpacing: "0.07em",
            }}>
              {selectedTask.label}
            </span>
            <svg
              width="8" height="8" viewBox="0 0 24 24"
              fill="none" stroke="var(--t3)" strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round"
              style={{ transform: taskOpen ? "rotate(180deg)" : "none", transition: "transform 0.15s", flexShrink: 0 }}
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>

          {/* Dropdown popover */}
          {taskOpen && (
            <div
              className="animate-slide-down"
              style={{
                position: "absolute", bottom: "calc(100% + 8px)", right: 0,
                width: 240,
                background: "var(--s3)",
                border: "1px solid var(--b2)",
                borderRadius: 7,
                overflow: "hidden",
                zIndex: 60,
                boxShadow: "0 -4px 32px rgba(0,0,0,0.5), 0 0 0 1px var(--b1)",
              }}
            >
              {/* Dropdown header */}
              <div style={{
                padding: "8px 12px 6px",
                borderBottom: "1px solid var(--b1)",
              }}>
                <span style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: 9, color: "var(--t4)", letterSpacing: "0.08em", textTransform: "uppercase",
                }}>
                  Select Task Type
                </span>
              </div>
              <div style={{ padding: "4px 0" }}>
                {TASK_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => { setTaskOverride(opt.value); setTaskOpen(false); }}
                    style={{
                      display: "flex", alignItems: "center", gap: 10,
                      width: "100%", textAlign: "left",
                      padding: "8px 12px",
                      background: opt.value === taskOverride ? "var(--accent-dim)" : "transparent",
                      border: "none", cursor: "pointer",
                      transition: "background 0.1s",
                      borderLeft: `2px solid ${opt.value === taskOverride ? "var(--accent)" : "transparent"}`,
                    }}
                    onMouseEnter={e => {
                      if (opt.value !== taskOverride)
                        (e.currentTarget as HTMLElement).style.background = "var(--s4)";
                    }}
                    onMouseLeave={e => {
                      if (opt.value !== taskOverride)
                        (e.currentTarget as HTMLElement).style.background = "transparent";
                    }}
                  >
                    {/* Active indicator dot */}
                    <span style={{
                      width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                      background: opt.value === taskOverride ? "var(--accent)" : "var(--b3)",
                      boxShadow: opt.value === taskOverride ? "0 0 6px var(--accent-glow)" : "none",
                    }} />
                    <div>
                      <span style={{
                        fontFamily: "var(--font-geist-mono), monospace",
                        fontSize: 10, fontWeight: 700,
                        color: opt.value === taskOverride ? "var(--accent-text)" : opt.color,
                        letterSpacing: "0.06em", display: "block",
                      }}>
                        {opt.label}
                      </span>
                      <span style={{ fontSize: 10, color: "var(--t3)", marginTop: 1, display: "block" }}>
                        {opt.desc}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div style={{ width: 1, background: "var(--b0)", flexShrink: 0, alignSelf: "stretch" }} />

        {/* Run button */}
        <button
          onClick={onAnalyze}
          disabled={!canRun}
          title={canRun ? "Run analysis (Enter)" : "Upload data and enter a query first"}
          style={{
            height: "100%",
            padding: "0 22px",
            background: canRun ? "var(--accent)" : "var(--s2)",
            border: "none",
            cursor: canRun ? "pointer" : "not-allowed",
            display: "flex", alignItems: "center", gap: 8,
            transition: "all 0.15s",
            flexShrink: 0,
            opacity: disabled ? 0.4 : 1,
            position: "relative",
            overflow: "hidden",
          }}
          onMouseEnter={e => {
            if (canRun) {
              (e.currentTarget as HTMLElement).style.background = "hsl(222, 88%, 68%)";
            }
          }}
          onMouseLeave={e => {
            if (canRun) {
              (e.currentTarget as HTMLElement).style.background = "var(--accent)";
            }
          }}
        >
          {/* Shimmer on hover when ready */}
          {canRun && (
            <div style={{
              position: "absolute", inset: 0,
              background: "linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.08) 50%, transparent 60%)",
              backgroundSize: "200% 100%",
            }} />
          )}

          {loading ? (
            <>
              <span className="animate-spin-smooth" style={{
                width: 12, height: 12,
                border: "2px solid rgba(255,255,255,0.3)",
                borderTopColor: "#fff",
                borderRadius: "50%",
                display: "block", flexShrink: 0,
              }} />
              <span style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: 11, fontWeight: 700, color: "#fff", letterSpacing: "0.06em",
              }}>
                Running…
              </span>
            </>
          ) : (
            <>
              <svg width="11" height="11" viewBox="0 0 24 24"
                fill={canRun ? "#fff" : "var(--t3)"} stroke="none"
                style={{ flexShrink: 0 }}
              >
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: 12, fontWeight: 700,
                color: canRun ? "#fff" : "var(--t3)",
                letterSpacing: "0.05em",
              }}>
                Run
              </span>
              {canRun && (
                <span style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: 9, color: "rgba(255,255,255,0.5)",
                  letterSpacing: "0.02em",
                  marginLeft: 2,
                }}>
                  ↵
                </span>
              )}
            </>
          )}
        </button>
      </div>

      {/* ── Error banner ── */}
      {error && (
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "7px 16px",
          background: "var(--red-dim)",
          borderTop: "1px solid hsla(0,80%,66%,0.15)",
        }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
            stroke="var(--red)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <p style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: 11, color: "var(--red)", margin: 0,
          }}>
            {error}
          </p>
        </div>
      )}
    </div>
  );
}
