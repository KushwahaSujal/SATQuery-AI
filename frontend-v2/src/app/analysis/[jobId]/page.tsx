"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useJob, useAnalysisResult, useLayers } from "@/hooks/useSystem";
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
  const data = result.data;
  const chatRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "analysis" | "trace">("chat");
  const [activeLayer, setActiveLayer] = useState("true_color");
  const [followUp, setFollowUp] = useState("");
  const [traceOpen, setTraceOpen] = useState(true);

  const stats = data?.evidence?.spatial?.statistics;
  const layers = layersQuery.data?.layers ?? [];

  const steps = ((job.data?.execution_steps || data?.execution_trace || data?.trace || []) as Record<string, unknown>[]).map((s) => ({
    step: (s.step as string) || (s.step_name as string) || "unknown",
    status: (s.status as string) || "success",
    duration_ms: typeof s.duration_ms === "number" ? s.duration_ms : typeof s.duration_seconds === "number" ? Math.round(s.duration_seconds as number * 1000) : undefined,
    model: (s.model_name as string) || (s.model as string),
  }));

  useEffect(() => { chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" }); }, [data]);

  if (job.isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 52px - 42px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="animate-spin-smooth" style={{ width: 12, height: 12, border: "2px solid #1e252f", borderTopColor: "#2dd4bf", borderRadius: "50%" }} />
          <span style={{ fontSize: 12, color: "#64748b" }}>Loading analysis...</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
      {/* ─── STAGE (left: satellite canvas) ─── */}
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", background: "#0d1117" }}>
        {/* Sub-header */}
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #1e252f", background: "#11151c", display: "flex", alignItems: "center", justifyContent: "space-between", flex: "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Link href="/analysis" style={{ fontSize: 12, color: "#64748b", textDecoration: "none" }}>← Back to Analysis</Link>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0", margin: 0 }}>
              {data?.task ? data.task.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "Analysis"}
            </h2>
            {data?.status && <StatusBadge status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <a href={api.downloadUrl(jobId)} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">Export</a>
          </div>
        </div>

        {/* Badges row */}
        {data?.query && (
          <div style={{ padding: "8px 16px", borderBottom: "1px solid #1e252f", display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#9aa8b9", flex: "none" }}>
            <span className="chip chip-mono" style={{ padding: "3px 7px" }}>{data.task?.replace(/_/g, " ")}</span>
            <span style={{ color: "#64748b" }}>·</span>
            <span style={{ color: "#64748b" }}>&ldquo;{data.query}&rdquo;</span>
          </div>
        )}

        {/* Viewport */}
        <div className="viewport">
          {/* Layer image */}
          {jobId && layers.length > 0 ? (
            <img
              src={api.visualizationUrl(jobId, activeLayer)}
              alt="Analysis result"
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <p style={{ fontSize: 12, color: "#64748b" }}>Visualization will appear once analysis completes.</p>
            </div>
          )}

          {/* Layer selector overlay */}
          {layers.length > 0 && (
            <div style={{ position: "absolute", top: 12, left: 12, zIndex: 20, width: 200, background: "rgba(9,17,30,.9)", backdropFilter: "blur(12px)", borderRadius: 10, border: "1px solid #1e252f", padding: 10 }}>
              <div style={{ display: "flex", borderBottom: "1px solid #1e252f", marginBottom: 8, paddingBottom: 6 }}>
                <button className={`tab ${true ? "on" : ""}`} style={{ flex: 1, textAlign: "center", fontSize: 11 }}>Images</button>
                <button className="tab" style={{ flex: 1, textAlign: "center", fontSize: 11 }}>Layers</button>
              </div>
              {layers.slice(0, 4).map((l) => (
                <button
                  key={l.id}
                  onClick={() => setActiveLayer(l.id)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "6px 8px", borderRadius: 6, fontSize: 11, cursor: "pointer",
                    background: l.id === activeLayer ? "#101b2f" : "transparent",
                    border: l.id === activeLayer ? "1px solid rgba(0,213,191,.3)" : "1px solid transparent",
                    color: l.id === activeLayer ? "#2dd4bf" : "#9aa8b9",
                    marginBottom: 2,
                  }}
                >
                  <span>{l.name}</span>
                  <span style={{ fontSize: 9, color: "#64748b", textTransform: "uppercase" }}>{l.provenance}</span>
                </button>
              ))}
            </div>
          )}

          {/* Readout bar */}
          <div className="readout">
            <span><b>CRS</b> EPSG:32636</span><span className="sep" />
            <span><b>GSD</b> 0.5 m</span><span className="sep" />
            <span><b>Bands</b> R,G,B</span><span className="sep" />
            <span><b>Size</b> 1024 × 1024</span>
          </div>
        </div>

        {/* Stat strip */}
        {stats && (
          <div className="stat-row">
            {stats.region_count > 0 && (
              <div className="stat"><div className="k">Regions</div><div className="v">{stats.region_count}</div></div>
            )}
            {stats.changed_pixels > 0 && (
              <div className="stat"><div className="k">Changed Pixels</div><div className="v">{stats.changed_pixels.toLocaleString()}</div></div>
            )}
            {stats.estimated_area_sq_m && (
              <div className="stat"><div className="k">Area</div><div className="v">{stats.estimated_area_sq_m.toLocaleString()} m²</div></div>
            )}
            {stats.change_ratio != null && (
              <div className="stat"><div className="k">Change Ratio</div><div className="v">{(stats.change_ratio * 100).toFixed(1)}%</div></div>
            )}
          </div>
        )}
      </div>

      {/* ─── ASIDE (right: chat + trace + composer) ─── */}
      <aside style={{ width: 364, flex: "none", borderLeft: "1px solid #1e252f", background: "#11151c", display: "flex", flexDirection: "column", minHeight: 0 }}>
        {/* Tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: 2, padding: "8px 14px", borderBottom: "1px solid #1e252f", flex: "none" }}>
          {(["chat", "analysis", "trace"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`tab ${activeTab === t ? "on" : ""}`}
              style={{ textTransform: "capitalize" }}
            >
              {t === "trace" ? "Execution Trace" : t}
            </button>
          ))}
        </div>

        {/* Content */}
        <div ref={chatRef} style={{ flex: 1, overflow: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 15 }}>
          {activeTab === "chat" && data && (
            <>
              {/* User message */}
              <div className="msg user">
                <div className="av">SM</div>
                <div className="bubble">{data.query || "Run analysis"}</div>
              </div>

              {/* AI response */}
              <div className="msg ai">
                <div className="av">◈</div>
                <div className="bubble">
                  <p>{data.answer || "Analysis complete."}</p>

                  {/* Confidence meter */}
                  {data.confidence != null && (
                    <div className="meter" style={{ margin: "12px 0 0" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, color: "#64748b", width: 66, flex: "none" }}>Confidence</span>
                      <span className="track"><span className="fill" style={{ width: `${data.confidence * 100}%` }} /></span>
                      <span className="val">{data.confidence.toFixed(2)}</span>
                    </div>
                  )}

                  {/* Execution trace */}
                  {steps.length > 0 && (
                    <div className="trace" data-open={traceOpen ? "true" : "false"}>
                      <button className="trace-h" onClick={() => setTraceOpen(!traceOpen)}>
                        <span className="chip chip-accent chip-mono" style={{ padding: "3px 7px" }}>{steps.length} steps</span>
                        Execution summary
                        <span className="caret">▾</span>
                      </button>
                      <div className="trace-b">
                        {steps.map((s, i) => (
                          <div key={i} className="step">
                            <span className={`idx ${s.status === "success" ? "done" : s.status === "running" ? "run" : ""}`}>
                              {s.status === "success" ? "✓" : i + 1}
                            </span>
                            <div className="body">
                              <b>{s.step.replace(/_/g, " ")}</b>
                              <span>{s.model || ""}{s.duration_ms != null ? ` · ${s.duration_ms}ms` : ""}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {activeTab === "analysis" && data && (
            <div style={{ fontSize: 13, color: "#9aa8b9" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                <ConfidenceRing value={Math.round((data.confidence ?? 0) * 100)} status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />
                <div>
                  <div style={{ fontSize: 12, color: "#e2e8f0", fontWeight: 500 }}>Confidence</div>
                  <StatusBadge status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />
                </div>
              </div>
              {stats && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, paddingTop: 12, borderTop: "1px solid #1e252f" }}>
                  {stats.region_count > 0 && <div style={{ background: "#0d1728", border: "1px solid #1a2b45", padding: 8, borderRadius: 10, textAlign: "center" }}><div style={{ fontSize: 10, color: "#64748b" }}>Regions</div><div style={{ fontSize: 13, fontWeight: 600, color: "#2dd4bf", marginTop: 4 }}>{stats.region_count}</div></div>}
                  {stats.changed_pixels > 0 && <div style={{ background: "#0d1728", border: "1px solid #1a2b45", padding: 8, borderRadius: 10, textAlign: "center" }}><div style={{ fontSize: 10, color: "#64748b" }}>Changed</div><div style={{ fontSize: 13, fontWeight: 600, color: "#2dd4bf", marginTop: 4 }}>{(stats.changed_pixels / 1000).toFixed(1)}k</div></div>}
                  {stats.estimated_area_sq_m && <div style={{ background: "#0d1728", border: "1px solid #1a2b45", padding: 8, borderRadius: 10, textAlign: "center" }}><div style={{ fontSize: 10, color: "#64748b" }}>Area</div><div style={{ fontSize: 13, fontWeight: 600, color: "#2dd4bf", marginTop: 4 }}>{(stats.estimated_area_sq_m / 1000).toFixed(1)} km²</div></div>}
                </div>
              )}
            </div>
          )}

          {activeTab === "trace" && (
            <div style={{ fontSize: 11.5 }}>
              {steps.map((s, i) => (
                <div key={i} style={{ display: "flex", gap: 10, padding: "7px 0", borderTop: i > 0 ? "1px dashed #1e252f" : "none" }}>
                  <span style={{ color: s.status === "success" ? "#34d399" : s.status === "error" ? "#ef4444" : "#f59e0b", width: 17, height: 17, borderRadius: 5, display: "grid", placeItems: "center", fontSize: 9.5, fontFamily: "var(--font-mono)", background: s.status === "success" ? "#0f2a1c" : "#11302e", flex: "none" }}>
                    {s.status === "success" ? "✓" : i + 1}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <b style={{ display: "block", fontWeight: 500, color: "#e2e8f0", fontSize: 12 }}>{s.step.replace(/_/g, " ")}</b>
                    <span style={{ color: "#64748b", fontFamily: "var(--font-mono)", fontSize: 10.5 }}>{s.model || ""}{s.duration_ms != null ? ` · ${s.duration_ms}ms` : ""}</span>
                  </div>
                </div>
              ))}
              {steps.length === 0 && <p style={{ color: "#64748b", textAlign: "center", padding: "24px 0" }}>No execution trace available.</p>}
            </div>
          )}
        </div>

        {/* Follow-up composer */}
        <div className="composer">
          <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
            <button className="chip">Quantify the change</button>
            <button className="chip">Export the mask</button>
          </div>
          <div className="box">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", padding: 4 }}>＋</button>
              <input
                value={followUp}
                onChange={(e) => setFollowUp(e.target.value)}
                placeholder="Ask a follow-up question…"
                style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#e2e8f0", fontFamily: "var(--font-sans)", fontSize: 13 }}
              />
              <button className="send">➤</button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
