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
      <div className="flex items-center justify-center h-[calc(100vh-64px)]">
        <div className="flex items-center gap-2">
          <span className="animate-spin-smooth w-3 h-3 border-2 border-cyan-900 border-t-cyan-400 rounded-full" />
          <span className="text-xs text-slate-400">Loading analysis...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* Center: Satellite Canvas */}
      <div className="flex-1 flex flex-col min-w-0 border-r border-[#152033]">
        {/* Header */}
        <div className="px-5 py-3 border-b border-[#141d2f] bg-[#090f1d]">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/analysis" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Back to Analysis
              </Link>
              <div className="flex items-center gap-2.5 mt-1">
                <h1 className="text-lg font-bold text-white tracking-tight">{data?.task ? data.task.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "Analysis"}</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {data?.status && <StatusBadge status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />}
              <a href={api.downloadUrl(jobId)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#22334f] bg-[#101a2d] hover:bg-[#16233b] text-xs font-medium text-slate-200 transition">Export</a>
            </div>
          </div>
          {data?.query && <p className="text-xs text-slate-400 mt-2">&ldquo;{data.query}&rdquo;</p>}
        </div>

        {/* Canvas */}
        <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden">
          {jobId && layers.length > 0 ? (
            <img
              src={api.visualizationUrl(jobId, activeLayer)}
              alt="Analysis result"
              className="max-w-full max-h-full object-contain"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="text-center">
              <p className="text-xs text-slate-400">Visualization will appear here once analysis completes.</p>
            </div>
          )}

          {/* Layer selector */}
          {layers.length > 0 && (
            <div className="absolute left-3 top-3 z-20 w-48 bg-[#09111e]/90 backdrop-blur-md rounded-lg border border-[#1b2b46] shadow-2xl p-2.5 text-xs">
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Layers</span>
              <div className="mt-2 space-y-1">
                {layers.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => setActiveLayer(l.id)}
                    className={`w-full flex items-center justify-between p-1.5 rounded-md text-[11px] transition ${
                      l.id === activeLayer ? "bg-[#101b2f] border border-cyan-900/50 text-cyan-300" : "text-slate-400 hover:text-slate-200 hover:bg-[#0d1627]"
                    }`}
                  >
                    <span>{l.name}</span>
                    <span className="text-[9px] text-slate-500 uppercase">{l.provenance}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Thumbnail strip */}
        <div className="h-16 border-t border-[#141e31] bg-[#080d19] px-4 flex items-center gap-3 shrink-0">
          {layers.slice(0, 4).map((l) => (
            <button
              key={l.id}
              onClick={() => setActiveLayer(l.id)}
              className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border shadow-md cursor-pointer transition ${
                l.id === activeLayer ? "bg-[#0e1728] border-cyan-700/60" : "bg-[#0e1728] border-[#1c2c46] hover:border-slate-500"
              }`}
            >
              <div className="w-10 h-8 rounded bg-slate-800 border border-slate-600" />
              <span className="text-xs font-semibold text-slate-200">{l.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right: Chat / Analysis / Trace */}
      <aside className="w-[420px] bg-[#090f1d] flex flex-col shrink-0 overflow-hidden">
        {/* Tabs */}
        <div className="h-11 px-4 border-b border-[#162237] bg-[#0a101f] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-5 text-xs">
            {(["chat", "analysis", "trace"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`h-11 flex items-center font-semibold border-b-2 px-1 capitalize ${
                  activeTab === tab ? "text-cyan-400 border-cyan-400" : "text-slate-400 hover:text-slate-200 border-transparent"
                }`}
              >
                {tab === "trace" ? "Execution Trace" : tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {activeTab === "chat" && data && (
            <>
              {/* AI response */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded-md bg-gradient-to-tr from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 font-bold text-[9px] shadow-[0_0_8px_rgba(6,182,212,0.5)]">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2" /></svg>
                  </div>
                  <span className="font-semibold text-cyan-300">SatQuery AI</span>
                </div>
                <div className="p-3.5 rounded-xl bg-[#091524] border border-[#162c46] space-y-3 leading-relaxed text-slate-300">
                  <p>{data.answer || "Analysis in progress..."}</p>
                  {data.confidence != null && (
                    <div className="p-2 rounded-lg bg-[#0e172a] border border-[#1b2b46]">
                      <div className="flex items-center justify-between text-[11px] mb-1.5">
                        <span className="text-slate-400">Confidence</span>
                        <span className="font-bold text-cyan-400 font-mono">{(data.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-[#16233b] rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-teal-400 to-cyan-400 rounded-full" style={{ width: `${data.confidence * 100}%` }} />
                      </div>
                    </div>
                  )}
                  {/* Key findings */}
                  {stats && (
                    <div className="rounded-lg bg-[#0c1c2e]/70 border border-[#1b3552] p-2.5 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-cyan-400 font-semibold text-[11px]">Key Findings</div>
                      <ul className="space-y-1 text-slate-300 pl-2 text-[11px]">
                        {stats.region_count > 0 && <li className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-cyan-400" />Regions detected: <strong className="text-white">{stats.region_count}</strong></li>}
                        {stats.changed_pixels > 0 && <li className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-cyan-400" />Changed pixels: <strong className="text-white">{stats.changed_pixels.toLocaleString()}</strong></li>}
                        {stats.estimated_area_sq_m && <li className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-cyan-400" />Area: <strong className="text-white">{stats.estimated_area_sq_m.toLocaleString()} m²</strong></li>}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {activeTab === "analysis" && data && (
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-[#0b1428] border border-[#172744]">
                <h4 className="text-[11px] font-semibold text-slate-300 mb-2">Results Summary</h4>
                <div className="flex items-center gap-3 mb-3">
                  <ConfidenceRing value={Math.round((data.confidence ?? 0) * 100)} status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} />
                  <div>
                    <span className="text-xs text-slate-300 font-medium">Confidence</span>
                    <StatusBadge status={data.status === "COMPLETED" ? "completed" : data.status === "FAILED" ? "failed" : "processing"} className="mt-0.5" />
                  </div>
                </div>
                {stats && (
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#142c4b]">
                    {stats.region_count > 0 && <div className="bg-[#0d1728] border border-[#1a2b45] p-2 rounded-lg text-center"><div className="text-[10px] text-slate-400">Regions</div><div className="text-xs font-bold text-cyan-300 mt-1">{stats.region_count}</div></div>}
                    {stats.changed_pixels > 0 && <div className="bg-[#0d1728] border border-[#1a2b45] p-2 rounded-lg text-center"><div className="text-[10px] text-slate-400">Changed</div><div className="text-xs font-bold text-cyan-300 mt-1">{(stats.changed_pixels / 1000).toFixed(1)}k</div></div>}
                    {stats.estimated_area_sq_m && <div className="bg-[#0d1728] border border-[#1a2b45] p-2 rounded-lg text-center"><div className="text-[10px] text-slate-400">Area</div><div className="text-xs font-bold text-cyan-300 mt-1">{(stats.estimated_area_sq_m / 1000).toFixed(1)} km²</div></div>}
                  </div>
                )}
              </div>
              {/* Models used */}
              {data.models_used?.length > 0 && (
                <div className="p-3 rounded-lg bg-[#0a1222] border border-[#18263e]">
                  <span className="text-[11px] font-semibold text-slate-300">Models Executed</span>
                  <div className="mt-2 space-y-1">
                    {data.models_used.map((m) => (
                      <div key={m} className="flex items-center gap-2 text-[11px]"><span className="text-emerald-400">✓</span><span className="text-slate-300">{m}</span></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "trace" && (
            <div className="space-y-1.5 text-[10px]">
              {steps.map((s, i) => (
                <div key={i} className="flex items-center justify-between text-slate-300 py-1">
                  <span className="flex items-center gap-1.5">
                    <span className={s.status === "success" ? "text-emerald-400" : s.status === "error" ? "text-red-400" : "text-amber-400"}>
                      {s.status === "success" ? "✓" : s.status === "error" ? "✗" : "⟳"}
                    </span>
                    {s.step.replace(/_/g, " ")}
                  </span>
                  {s.duration_ms != null && <span className="text-slate-500 font-mono">{s.duration_ms}ms</span>}
                </div>
              ))}
              {steps.length === 0 && <p className="text-slate-400 text-center py-4">No execution trace available yet.</p>}
            </div>
          )}
        </div>

        {/* Follow-up input */}
        <div className="p-3 border-t border-[#15253b] bg-[#070e19] shrink-0">
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-lg bg-[#0b1625] border border-[#1b3452] text-slate-400 hover:text-white transition">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" /></svg>
            </button>
            <input
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              className="flex-1 h-9 px-3 bg-[#0b1625] border border-[#1b3452] rounded-lg text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition"
              placeholder="Ask a follow-up question..."
            />
            <button className="w-7 h-7 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 flex items-center justify-center font-bold shadow-md shadow-cyan-500/25 transition">
              <svg className="w-3.5 h-3.5 rotate-45 -mr-0.5 mb-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
