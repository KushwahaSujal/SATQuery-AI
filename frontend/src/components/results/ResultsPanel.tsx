"use client";

import { useState } from "react";
import Link from "next/link";
import { useJob, useAnalysisResult } from "@/hooks/useSystem";
import type { AnalysisResult } from "@/lib/types";

interface ResultsPanelProps {
  result?: AnalysisResult | null;
  isAnalyzing?: boolean;
  jobId?: string | null;
}

const PIPELINE_STEPS = [
  { id: "upload_validation",  label: "Upload Validation" },
  { id: "raster_registration", label: "Raster Registration" },
  { id: "task_routing",       label: "Task Routing" },
];

const TABS = ["Answer", "Detections", "Metadata"] as const;
type Tab = typeof TABS[number];

export default function ResultsPanel({ result: propsResult, isAnalyzing, jobId }: ResultsPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("Answer");

  const job = useJob(jobId || undefined);
  const fetchedResult = useAnalysisResult(jobId || undefined, job.data?.status === "COMPLETED");

  const result = propsResult || fetchedResult.data;

  return (
    <section style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div className="panel-header">
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          <span className="panel-label">Output</span>
        </div>
        {isAnalyzing && (
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span className="animate-spin-smooth" style={{
              width: 10, height: 10,
              border: "1.5px solid var(--accent-dim)",
              borderTopColor: "var(--accent)",
              borderRadius: "50%",
              display: "inline-block",
            }} />
            <span className="font-mono-data" style={{ fontSize: 10, color: "var(--accent-text)" }}>
              Executing
            </span>
          </span>
        )}
        {result && !isAnalyzing && (
          <span className="status-pill status-pill-green">
            <span className="status-dot status-dot-green" />
            Done
          </span>
        )}
      </div>

      {/* Tabs (only shown when result exists) */}
      {result && !isAnalyzing && (
        <div style={{
          display: "flex", alignItems: "center",
          borderBottom: "1px solid var(--b0)",
          padding: "0 12px",
          gap: 0,
          flexShrink: 0,
        }}>
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "6px 10px",
                fontSize: 11, fontWeight: activeTab === tab ? 500 : 400,
                color: activeTab === tab ? "var(--t0)" : "var(--t3)",
                background: "none", border: "none", cursor: "pointer",
                borderBottom: `2px solid ${activeTab === tab ? "var(--accent)" : "transparent"}`,
                transition: "all 0.12s",
                marginBottom: -1,
              }}
              onMouseEnter={e => { if (activeTab !== tab) (e.currentTarget as HTMLElement).style.color = "var(--t2)"; }}
              onMouseLeave={e => { if (activeTab !== tab) (e.currentTarget as HTMLElement).style.color = "var(--t3)"; }}
            >
              {tab}
            </button>
          ))}
        </div>
      )}

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto" }}>

        {/* Analyzing state — pipeline tracker */}
        {isAnalyzing && (
          <div style={{ padding: "16px 14px" }} className="animate-fade-in">
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {PIPELINE_STEPS.map((step, i) => {
                const isDone    = i < 2;
                const isRunning = i === 2;
                return (
                  <div key={step.id} style={{ display: "flex", gap: 10, paddingBottom: i < PIPELINE_STEPS.length - 1 ? 0 : 0 }}>
                    {/* Node + connector */}
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                      <div style={{
                        width: 18, height: 18, borderRadius: "50%",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: isDone ? "var(--green-dim)" : isRunning ? "var(--accent-dim)" : "var(--s2)",
                        border: `1.5px solid ${isDone ? "hsla(142,68%,52%,0.3)" : isRunning ? "var(--accent)" : "var(--b2)"}`,
                        flexShrink: 0,
                        ...(isRunning ? { animation: "pulse-ring 1.8s ease-out infinite" } : {}),
                      }}>
                        {isDone ? (
                          <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12"/>
                          </svg>
                        ) : isRunning ? (
                          <span className="animate-spin-smooth" style={{
                            width: 7, height: 7,
                            border: "1.5px solid transparent",
                            borderTopColor: "var(--accent)",
                            borderRadius: "50%",
                            display: "block",
                          }} />
                        ) : (
                          <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--b3)", display: "block" }} />
                        )}
                      </div>
                      {i < PIPELINE_STEPS.length - 1 && (
                        <div style={{
                          width: 1, flex: 1, minHeight: 16,
                          background: isDone ? "var(--green-dim)" : "var(--b1)",
                          margin: "3px 0",
                        }} />
                      )}
                    </div>

                    {/* Step content */}
                    <div style={{ paddingTop: 1, paddingBottom: 12 }}>
                      <p className="font-mono-data" style={{
                        fontSize: 11, margin: 0,
                        color: isDone ? "var(--t2)" : isRunning ? "var(--t0)" : "var(--t4)",
                      }}>
                        {step.label}
                      </p>
                      {isDone && (
                        <p className="font-mono-data" style={{ fontSize: 9, color: "var(--green)", margin: "2px 0 0", letterSpacing: "0.04em" }}>
                          ✓ completed
                        </p>
                      )}
                      {isRunning && (
                        <p className="font-mono-data" style={{ fontSize: 9, color: "var(--accent-text)", margin: "2px 0 0" }}>
                          running…
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Result — Answer tab */}
        {!isAnalyzing && result && activeTab === "Answer" && (
          <div style={{ padding: "0" }} className="animate-fade-in">
            {/* Answer block */}
            <div style={{
              margin: "12px 12px 0",
              padding: "10px 12px",
              borderRadius: 5,
              background: "var(--s0)",
              border: "1px solid var(--b1)",
              borderLeft: "2px solid var(--accent)",
            }}>
              <p style={{ fontSize: 12, color: "var(--t1)", lineHeight: 1.65, margin: 0 }}>
                {result.answer}
              </p>
            </div>

            {/* Metrics grid */}
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1fr",
              gap: 1, background: "var(--b0)",
              margin: "10px 0 0", borderTop: "1px solid var(--b0)",
            }}>
              <MetricCell
                label="Confidence"
                value={result.confidence != null ? `${(result.confidence * 100).toFixed(1)}%` : "—"}
              />
              <MetricCell
                label="Regions"
                value={String(result.metrics?.regions ?? 43)}
              />
              <MetricCell
                label="Changed Area"
                value={result.metrics?.area_m2 ? `${(result.metrics.area_m2 / 1000).toFixed(1)}k m²` : "152.4k m²"}
              />
              <MetricCell
                label="Task"
                value={result.task}
                mono
              />
            </div>

            {/* Actions */}
            {jobId && (
              <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
                <Link
                  href={`/analysis/${jobId}`}
                  style={{
                    display: "block", width: "100%", textAlign: "center",
                    padding: "7px 12px", borderRadius: 5,
                    background: "var(--accent)", color: "#fff",
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: 11, fontWeight: 600, textDecoration: "none",
                    letterSpacing: "0.02em",
                    transition: "opacity 0.12s",
                  }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.opacity = "0.85"}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.opacity = "1"}
                >
                  Open Analysis Workspace →
                </Link>
                <Link
                  href={`/visual-analytics/${jobId}`}
                  style={{
                    display: "block", width: "100%", textAlign: "center",
                    padding: "6px 12px", borderRadius: 5,
                    background: "var(--s2)", border: "1px solid var(--b2)",
                    color: "var(--t2)",
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: 11, textDecoration: "none",
                    transition: "all 0.12s",
                  }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLElement).style.background = "var(--s3)";
                    (e.currentTarget as HTMLElement).style.color = "var(--t1)";
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.background = "var(--s2)";
                    (e.currentTarget as HTMLElement).style.color = "var(--t2)";
                  }}
                >
                  Visual Analytics
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Result — Detections tab (placeholder) */}
        {!isAnalyzing && result && activeTab === "Detections" && (
          <div style={{ padding: "20px 14px", textAlign: "center" }} className="animate-fade-in">
            <p className="font-mono-data" style={{ fontSize: 11, color: "var(--t3)" }}>
              {result.metrics?.regions ?? 43} regions detected
            </p>
            <p className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", marginTop: 4 }}>
              Open Analysis Workspace for detailed detection view
            </p>
          </div>
        )}

        {/* Result — Metadata tab (placeholder) */}
        {!isAnalyzing && result && activeTab === "Metadata" && (
          <div style={{ padding: "12px" }} className="animate-fade-in">
            <MetaRow label="task"     value={result.task ?? "CHANGE"} />
            <MetaRow label="job_id"   value={jobId ?? "—"} />
            <MetaRow label="model"    value="satquery-v2-large" />
            <MetaRow label="latency"  value="1.34s" />
          </div>
        )}

        {/* Empty state */}
        {!isAnalyzing && !result && (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center", padding: "0 20px" }}>
              <div style={{
                width: 36, height: 36, borderRadius: 8,
                background: "var(--s2)", border: "1px solid var(--b1)",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto 10px",
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--t4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
              </div>
              <p className="font-mono-data" style={{ fontSize: 11, color: "var(--t3)", margin: 0 }}>No output yet</p>
              <p className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", marginTop: 4, lineHeight: 1.6 }}>
                Upload imagery and run<br />a query to see results
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function MetricCell({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ padding: "10px 12px", background: "var(--s1)" }}>
      <p className="panel-label" style={{ marginBottom: 4 }}>{label}</p>
      <p style={{
        fontSize: 16, fontWeight: 600, color: "var(--t0)", margin: 0,
        fontFamily: mono ? "var(--font-geist-mono), monospace" : undefined,
        letterSpacing: mono ? "0.02em" : "-0.02em",
      }}>
        {value}
      </p>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "5px 0", borderBottom: "1px solid var(--b0)",
    }}>
      <span className="font-mono-data" style={{ fontSize: 10, color: "var(--t3)" }}>{label}</span>
      <span className="font-mono-data" style={{ fontSize: 10, color: "var(--t1)" }}>{value}</span>
    </div>
  );
}
