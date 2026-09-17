"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { useJob, useAnalysisResult, useLayers, usePixelInspector } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import { ConfidenceRing } from "@/components/ui/ConfidenceRing";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { TraceStep } from "@/lib/types";

export default function AnalysisJobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const job = useJob(jobId);
  const status = job.data?.status ?? "UNKNOWN";
  const result = useAnalysisResult(jobId, status === "COMPLETED");
  const layersQuery = useLayers(jobId);
  const pixelInspector = usePixelInspector(jobId);
  const data = result.data;
  const [activeTab, setActiveTab] = useState<"chat" | "analysis" | "trace">("chat");
  const [followUp, setFollowUp] = useState("");
  const chatRef = useRef<HTMLDivElement>(null);

  const stats = data?.evidence?.spatial?.statistics;
  const steps = ((job.data?.execution_steps || data?.execution_trace || data?.trace || []) as Record<string, unknown>[]).map((s) => ({
    step: (s.step as string) || (s.step_name as string) || "unknown",
    status: (s.status as string) || "success",
    duration_ms: typeof s.duration_ms === "number" ? s.duration_ms : typeof s.duration_seconds === "number" ? Math.round(s.duration_seconds as number * 1000) : undefined,
  }));

  const layers = layersQuery.data?.layers ?? [];
  const [activeLayer, setActiveLayer] = useState("true_color");

  useEffect(() => { chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" }); }, [data]);

  if (job.isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-64px)]" style={{ background: "var(--canvas)" }}>
        <div className="flex items-center gap-2">
          <span className="animate-spin-smooth w-3 h-3 border-2 rounded-full" style={{ borderColor: "var(--border)", borderTopColor: "var(--cyan)" }} />
          <span className="text-xs" style={{ color: "var(--text-2)" }}>Loading analysis...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden" style={{ background: "var(--canvas)" }}>
      {/* Center: Satellite Canvas */}
      <div className="flex-1 flex flex-col min-w-0" style={{ borderRight: "1px solid var(--border)" }}>
        {/* Header */}
        <div className="px-5 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
          <div className="flex items-center justify-between">
            <div>
              <Link href="/analysis" className="inline-flex items-center gap-1.5 text-xs transition" style={{ color: "var(--text-2)" }}>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Back to Analysis
              </Link>
              <div className="flex items-center gap-2.5 mt-1">
                <h1 className="text-lg font-bold tracking-tight" style={{ color: "var(--heading)" }}>{data?.task ? data.task.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "Analysis"}</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {data?.status && <StatusBadge status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />}
              <a
                href={api.downloadUrl(jobId)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
                style={{ background: "var(--surface-2)", border: "1px solid var(--border-strong)", color: "var(--text)" }}
              >Export</a>
            </div>
          </div>
          {data?.query && <p className="text-xs mt-2" style={{ color: "var(--text-2)" }}>&ldquo;{data.query}&rdquo;</p>}
        </div>

        {/* Canvas */}
        <div className="flex-1 relative flex items-center justify-center overflow-hidden" style={{ background: "var(--workspace)" }}>
          {jobId && layers.length > 0 ? (
            <img
              src={api.visualizationUrl(jobId, activeLayer)}
              alt="Analysis result"
              className="max-w-full max-h-full object-contain"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="text-center">
              <p className="text-xs" style={{ color: "var(--text-2)" }}>Visualization will appear here once analysis completes.</p>
            </div>
          )}

          {/* Layer selector */}
          {layers.length > 0 && (
            <div
              className="absolute left-3 top-3 z-20 w-48 backdrop-blur-md rounded-lg p-2.5 text-xs"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border)", boxShadow: "var(--shadow-lg)" }}
            >
              <span className="text-[10px] uppercase font-semibold tracking-wider" style={{ color: "var(--text-2)" }}>Layers</span>
              <div className="mt-2 space-y-1">
                {layers.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => setActiveLayer(l.id)}
                    className="w-full flex items-center justify-between p-1.5 rounded-md text-[11px] transition"
                    style={l.id === activeLayer ? {
                      background: "var(--sidebar-active-bg)",
                      border: "1px solid var(--border)",
                      color: "var(--cyan)",
                    } : {
                      color: "var(--text-2)",
                    }}
                  >
                    <span>{l.name}</span>
                    <span className="text-[9px] uppercase" style={{ color: "var(--text-3)" }}>{l.provenance}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Thumbnail strip */}
        <div
          className="h-16 px-4 flex items-center gap-3 shrink-0"
          style={{ borderTop: "1px solid var(--border)", background: "var(--surface)" }}
        >
          {layers.slice(0, 4).map((l) => (
            <button
              key={l.id}
              onClick={() => setActiveLayer(l.id)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-pointer transition"
              style={{
                background: "var(--surface-2)",
                border: `1px solid ${l.id === activeLayer ? "var(--cyan)" : "var(--border)"}`,
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div className="w-10 h-8 rounded" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }} />
              <span className="text-xs font-semibold" style={{ color: "var(--text)" }}>{l.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right: Chat / Analysis / Trace */}
      <aside className="w-[420px] flex flex-col shrink-0 overflow-hidden" style={{ background: "var(--surface)" }}>
        {/* Tabs */}
        <div
          className="h-11 px-4 flex items-center justify-between shrink-0"
          style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-2)" }}
        >
          <div className="flex items-center gap-5 text-xs">
            {(["chat", "analysis", "trace"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className="h-11 flex items-center font-semibold border-b-2 px-1 capitalize"
                style={activeTab === tab ? {
                  color: "var(--cyan)",
                  borderColor: "var(--cyan)",
                } : {
                  color: "var(--text-2)",
                  borderColor: "transparent",
                }}
              >
                {tab === "trace" ? "Execution Trace" : tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {activeTab === "chat" && data && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-5 h-5 rounded-md bg-gradient-to-tr from-[#00C9E8] to-[#087FF5] flex items-center justify-center font-bold text-[9px]"
                  style={{ color: "#FFFFFF" }}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2" /></svg>
                </div>
                <span className="font-semibold" style={{ color: "var(--cyan)" }}>SatQuery AI</span>
              </div>
              <div className="p-3.5 rounded-xl space-y-3 leading-relaxed" style={{ background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text)" }}>
                <p>{data.answer || "Analysis in progress..."}</p>
                {data.confidence != null && (
                  <div className="p-2 rounded-lg" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between text-[11px] mb-1.5">
                      <span style={{ color: "var(--text-2)" }}>Confidence</span>
                      <span className="font-bold font-mono" style={{ color: "var(--cyan)" }}>{(data.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ background: "var(--surface-hover)" }}>
                      <div className="h-full rounded-full bg-gradient-to-r from-[#18C7B5] to-[#00C7D9]" style={{ width: `${data.confidence * 100}%` }} />
                    </div>
                  </div>
                )}
                {stats && (
                  <div className="rounded-lg p-2.5 space-y-1.5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center gap-1.5 font-semibold text-[11px]" style={{ color: "var(--cyan)" }}>Key Findings</div>
                    <ul className="space-y-1 pl-2 text-[11px]" style={{ color: "var(--text)" }}>
                      {stats.region_count > 0 && <li className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full" style={{ background: "var(--cyan)" }} />Regions detected: <strong style={{ color: "var(--heading)" }}>{stats.region_count}</strong></li>}
                      {stats.changed_pixels > 0 && <li className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full" style={{ background: "var(--cyan)" }} />Changed pixels: <strong style={{ color: "var(--heading)" }}>{stats.changed_pixels.toLocaleString()}</strong></li>}
                      {stats.estimated_area_sq_m && <li className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full" style={{ background: "var(--cyan)" }} />Area: <strong style={{ color: "var(--heading)" }}>{stats.estimated_area_sq_m.toLocaleString()} m²</strong></li>}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "analysis" && data && (
            <div className="space-y-3">
              <div className="p-3 rounded-lg" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}>
                <h4 className="text-[11px] font-semibold mb-2" style={{ color: "var(--text)" }}>Results Summary</h4>
                <div className="flex items-center gap-3 mb-3">
                  <ConfidenceRing value={Math.round((data.confidence ?? 0) * 100)} status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />
                  <div>
                    <span className="text-xs font-medium" style={{ color: "var(--text)" }}>Confidence</span>
                    <StatusBadge status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} className="mt-0.5" />
                  </div>
                </div>
                {stats && (
                  <div className="grid grid-cols-3 gap-2 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                    {stats.region_count > 0 && <div className="p-2 rounded-lg text-center" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}><div className="text-[10px]" style={{ color: "var(--text-2)" }}>Regions</div><div className="text-xs font-bold mt-1" style={{ color: "var(--cyan)" }}>{stats.region_count}</div></div>}
                    {stats.changed_pixels > 0 && <div className="p-2 rounded-lg text-center" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}><div className="text-[10px]" style={{ color: "var(--text-2)" }}>Changed</div><div className="text-xs font-bold mt-1" style={{ color: "var(--cyan)" }}>{(stats.changed_pixels / 1000).toFixed(1)}k</div></div>}
                    {stats.estimated_area_sq_m && <div className="p-2 rounded-lg text-center" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}><div className="text-[10px]" style={{ color: "var(--text-2)" }}>Area</div><div className="text-xs font-bold mt-1" style={{ color: "var(--cyan)" }}>{(stats.estimated_area_sq_m / 1000).toFixed(1)} km²</div></div>}
                  </div>
                )}
              </div>
              {data.models_used?.length > 0 && (
                <div className="p-3 rounded-lg" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}>
                  <span className="text-[11px] font-semibold" style={{ color: "var(--text)" }}>Models Executed</span>
                  <div className="mt-2 space-y-1">
                    {data.models_used.map((m) => (
                      <div key={m} className="flex items-center gap-2 text-[11px]"><span style={{ color: "var(--green)" }}>&#10003;</span><span style={{ color: "var(--text)" }}>{m}</span></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "trace" && (
            <div className="space-y-1.5 text-[10px]">
              {steps.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-1" style={{ color: "var(--text)" }}>
                  <span className="flex items-center gap-1.5">
                    <span style={{ color: s.status === "success" ? "var(--green)" : s.status === "error" ? "var(--error)" : "var(--warning)" }}>
                      {s.status === "success" ? "\u2713" : s.status === "error" ? "\u2717" : "\u27F3"}
                    </span>
                    {s.step.replace(/_/g, " ")}
                  </span>
                  {s.duration_ms != null && <span className="font-mono" style={{ color: "var(--text-3)" }}>{s.duration_ms}ms</span>}
                </div>
              ))}
              {steps.length === 0 && <p className="text-center py-4" style={{ color: "var(--text-2)" }}>No execution trace available yet.</p>}
            </div>
          )}
        </div>

        {/* Follow-up input */}
        <div className="p-3 shrink-0" style={{ borderTop: "1px solid var(--border)", background: "var(--surface-2)" }}>
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-lg transition" style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)", color: "var(--text-2)" }}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" /></svg>
            </button>
            <input
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              className="flex-1 h-9 px-3 rounded-lg text-xs focus:outline-none transition"
              style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--heading)" }}
              placeholder="Ask a follow-up question..."
            />
            <button
              className="w-7 h-7 rounded-lg flex items-center justify-center font-bold transition"
              style={{ background: "var(--cyan)", color: "var(--canvas)", boxShadow: "0 0 10px var(--cyan-glow)" }}
            >
              <svg className="w-3.5 h-3.5 rotate-45 -mr-0.5 mb-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
