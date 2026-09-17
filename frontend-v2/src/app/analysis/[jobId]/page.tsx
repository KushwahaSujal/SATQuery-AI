"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { useJob, useAnalysisResult, useLayers } from "@/hooks/useSystem";
import { api } from "@/lib/api";

export default function AnalysisJobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const job = useJob(jobId);
  const status = job.data?.status ?? "UNKNOWN";
  const result = useAnalysisResult(jobId, status === "COMPLETED");
  const layersQuery = useLayers(jobId);
  const data = result.data;
  
  const [activeTab, setActiveTab] = useState<"chat" | "analysis" | "trace">("chat");
  const [followUp, setFollowUp] = useState("");
  const [layerSelect, setLayerSelect] = useState("Natural Color (RGB)");
  const [modeSelect, setModeSelect] = useState<"compare" | "change_map" | "overlay">("compare");
  const [opacity, setOpacity] = useState(70);
  const [splitPos, setSplitPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  
  const [layerTab, setLayerTab] = useState<"images" | "layers">("images");
  const [layersToggle, setLayersToggle] = useState({
    changeDetection: true,
    urbanArea: false,
    vegetation: false,
    waterBodies: false,
  });

  const [t1Visible, setT1Visible] = useState(true);
  const [t2Visible, setT2Visible] = useState(true);
  const [activeLayer, setActiveLayer] = useState("true_color");
  const containerRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  const layers = layersQuery.data?.layers ?? [];
  const stats = data?.evidence?.spatial?.statistics;

  // Splitter dragging logic
  const handleMouseDown = () => setIsDragging(true);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.max(10, Math.min(90, (x / rect.width) * 100));
      setSplitPos(pct);
    };
    const handleMouseUp = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div className="h-screen w-full flex flex-col bg-[#050a12] text-slate-300 font-sans overflow-hidden select-none antialiased">
      {/* TopBar */}
      <TopBar showBrand={true} />

      {/* Main Interface Wrapper */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar hideBrand={true} />

        {/* Center Workspace */}
        <main className="flex-1 flex flex-col bg-[#070b14] overflow-hidden border-r border-[#152033]">
          {/* Sub-header & Breadcrumb Navigation */}
          <div className="px-5 py-3 border-b border-[#141d2f] bg-[#090f1d] flex flex-col gap-2 shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <Link
                  href="/analysis"
                  className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-300 transition"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                  <span>Back to New Analysis</span>
                </Link>
                <div className="flex items-center gap-2.5 mt-1">
                  <h1 className="text-lg font-bold text-white tracking-tight">
                    {data?.task ? data.task.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Urban Expansion Analysis"}
                  </h1>
                  <button className="text-slate-400 hover:text-white transition">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                  </button>
                </div>
              </div>
              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#22334f] bg-[#101a2d] hover:bg-[#16233b] text-xs font-medium text-slate-200 transition">
                  <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                    <polyline points="17 21 17 13 7 13 7 21" />
                    <polyline points="7 3 7 8 15 8" />
                  </svg>
                  <span>Save</span>
                </button>
                <a
                  href={api.downloadUrl(jobId)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#22334f] bg-[#101a2d] hover:bg-[#16233b] text-xs font-medium text-slate-200 transition"
                >
                  <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                    <polyline points="16 6 12 2 8 6" />
                    <line x1="12" x2="12" y1="2" y2="15" />
                  </svg>
                  <span>Export</span>
                </a>
              </div>
            </div>
            {/* Badges Info Row */}
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#101a2c] border border-[#1d2d47] text-slate-300">
                <svg className="w-3 h-3 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <rect height="18" rx="2" ry="2" width="18" x="3" y="3" />
                  <line x1="9" x2="9" y1="3" y2="21" />
                </svg>
                <span>Bi-temporal</span>
              </div>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#101a2c] border border-[#1d2d47] text-slate-300">
                <svg className="w-3 h-3 text-teal-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" x2="22" y1="12" y2="12" />
                </svg>
                <span>Optical</span>
              </div>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#101a2c] border border-[#1d2d47] text-slate-300">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>{status}</span>
              </div>
            </div>
          </div>

          {/* Satellite View Controls Bar */}
          <div className="h-11 px-4 border-b border-[#141e30] bg-[#0a101f] flex items-center justify-between text-xs shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Layer</span>
                <div className="relative">
                  <select
                    value={layerSelect}
                    onChange={(e) => setLayerSelect(e.target.value)}
                    className="bg-[#111c30] text-slate-200 text-xs py-1 pl-2.5 pr-7 rounded border border-[#20314f] focus:outline-none focus:border-cyan-500 appearance-none cursor-pointer"
                  >
                    <option>Natural Color (RGB)</option>
                    <option>False Color (Infrared)</option>
                    <option>NDVI Difference</option>
                  </select>
                  <svg className="w-3 h-3 text-slate-400 absolute right-2 top-2 pointer-events-none" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
              </div>

              {/* Mode Switches */}
              <div className="flex items-center bg-[#0d1627] p-0.5 rounded-lg border border-[#1b2b46]">
                <button
                  onClick={() => setModeSelect("compare")}
                  className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition ${
                    modeSelect === "compare"
                      ? "bg-cyan-900/60 border border-cyan-600/40 text-cyan-300 font-medium shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>Compare</span>
                </button>
                <button
                  onClick={() => setModeSelect("change_map")}
                  className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition ${
                    modeSelect === "change_map"
                      ? "bg-cyan-900/60 border border-cyan-600/40 text-cyan-300 font-medium shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>Change Map</span>
                </button>
              </div>

              {/* Opacity Slider */}
              <div className="flex items-center gap-2 pl-2">
                <span className="text-slate-400">Opacity</span>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={opacity}
                  onChange={(e) => setOpacity(Number(e.target.value))}
                  className="w-20 h-1 bg-[#1c2c47] accent-cyan-400 rounded cursor-pointer"
                />
                <span className="text-[11px] text-slate-300 font-mono">{opacity}%</span>
              </div>
            </div>
          </div>

          {/* Main Satellite Canvas */}
          <div ref={containerRef} className="relative flex-1 bg-black overflow-hidden flex select-none">
            {/* Split Screen Canvas */}
            <div className="relative w-full h-full flex overflow-hidden">
              {/* LEFT SIDE */}
              <div
                style={{ width: `${splitPos}%`, opacity: t1Visible ? 1 : 0.2 }}
                className="relative h-full overflow-hidden border-r border-cyan-500/30 transition-opacity"
              >
                <div className="absolute inset-0 satellite-bg-base">
                  <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85" preserveAspectRatio="none" viewBox="0 0 500 500">
                    <path d="M 120 -10 C 260 120, 210 280, 360 520" fill="none" stroke="#122c3f" strokeLinecap="round" strokeWidth="52" />
                    <path d="M 120 -10 C 260 120, 210 280, 360 520" fill="none" stroke="#1a3d54" strokeWidth="44" />
                  </svg>
                  <div className="absolute inset-0 opacity-40 mix-blend-overlay" style={{ backgroundImage: "radial-gradient(#6ee7b7 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
                </div>
                <div className="absolute top-3 left-6 bg-[#09111e]/80 backdrop-blur border border-[#1e2f4a] px-2.5 py-1 rounded text-[11px] font-medium text-slate-200 z-10 shadow-md">
                  Baseline (T1)
                </div>
              </div>

              {/* RIGHT SIDE */}
              <div
                style={{ width: `${100 - splitPos}%`, opacity: t2Visible ? opacity / 100 : 0.2 }}
                className="relative h-full overflow-hidden transition-opacity"
              >
                <div className="absolute inset-0 satellite-bg-base">
                  <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85" preserveAspectRatio="none" viewBox="0 0 500 500">
                    <path d="M -140 -10 C 0 120, -50 280, 100 520" fill="none" stroke="#122c3f" strokeLinecap="round" strokeWidth="52" />
                    <path d="M -140 -10 C 0 120, -50 280, 100 520" fill="none" stroke="#1a3d54" strokeWidth="44" />
                  </svg>
                  {layersToggle.changeDetection && <div className="absolute inset-0 urban-detection-layer" />}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 500 500">
                    <g fill="rgba(239, 68, 68, 0.22)" stroke="#ef4444" strokeWidth="1.5">
                      <rect height="18" rx="1" width="22" x="260" y="70" />
                      <rect height="20" rx="1" width="30" x="290" y="65" />
                      <rect height="28" rx="1" width="25" x="330" y="80" />
                      <polygon points="275,100 310,105 305,130 265,120" />
                      <polygon points="320,115 365,120 355,150 315,140" />
                      <rect height="30" width="35" x="375" y="100" />
                      <rect height="35" width="40" x="390" y="150" />
                    </g>
                    <path d="M 250 80 L 440 140 M 270 140 L 430 220" fill="none" stroke="#ef4444" strokeDasharray="3,3" strokeWidth="1.8" />
                  </svg>
                </div>
                <div className="absolute top-3 right-4 bg-[#09111e]/80 backdrop-blur border border-[#1e2f4a] px-2.5 py-1 rounded text-[11px] font-medium text-slate-200 z-10 shadow-md">
                  Current (T2)
                </div>
              </div>

              {/* Draggable Divider */}
              <div
                onMouseDown={handleMouseDown}
                style={{ left: `${splitPos}%` }}
                className="absolute top-0 bottom-0 -translate-x-1/2 w-1 bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.8)] z-30 flex items-center justify-center cursor-ew-resize"
              >
                <div className="w-8 h-8 rounded-full bg-[#091222] border-2 border-cyan-400 flex items-center justify-center text-cyan-300 shadow-xl hover:scale-110 transition-transform">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <polyline points="9 18 3 12 9 6" />
                    <polyline points="15 6 21 12 15 18" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Filmstrip */}
          <div className="h-20 border-t border-[#141e31] bg-[#080d19] px-4 flex items-center gap-3 shrink-0">
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#0e1728] border border-cyan-700/60 shadow-md cursor-pointer">
              <div className="w-14 h-12 rounded bg-emerald-950 border border-emerald-600/40 relative overflow-hidden shrink-0">
                <div className="w-full h-full satellite-bg-base scale-125" />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-200">T1 - 2023-01-15</div>
                <div className="text-[10px] text-slate-400">Optical (Sentinel-2)</div>
              </div>
            </div>
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#0e1728] border border-[#1c2c46] hover:border-slate-500 shadow-md cursor-pointer transition">
              <div className="w-14 h-12 rounded bg-emerald-950 border border-red-500/50 relative overflow-hidden shrink-0">
                <div className="w-full h-full satellite-bg-base scale-125" />
                <div className="absolute inset-0 bg-red-500/20" />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-200">T2 - 2025-01-18</div>
                <div className="text-[10px] text-slate-400">Optical (Sentinel-2)</div>
              </div>
            </div>
          </div>
        </main>

        {/* Right Chat Drawer */}
        <aside className="w-[420px] bg-[#090f1d] flex flex-col shrink-0 select-text overflow-hidden">
          <div className="h-11 px-4 border-b border-[#162237] bg-[#0a101f] flex items-center justify-between shrink-0">
            <div className="flex items-center gap-5 text-xs">
              <button
                onClick={() => setActiveTab("chat")}
                className={`h-11 flex items-center px-1 font-semibold transition ${
                  activeTab === "chat" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Chat
              </button>
              <button
                onClick={() => setActiveTab("analysis")}
                className={`h-11 flex items-center px-1 font-medium transition ${
                  activeTab === "analysis" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Analysis
              </button>
              <button
                onClick={() => setActiveTab("trace")}
                className={`h-11 flex items-center px-1 font-medium transition ${
                  activeTab === "trace" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Execution Trace
              </button>
            </div>
          </div>

          <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            {activeTab === "chat" && (
              <>
                <div className="flex items-start gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] font-bold text-white shrink-0 mt-0.5">
                    SM
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-slate-200">You</span>
                      <span className="text-[10px] text-slate-500 font-mono">11:42 AM</span>
                    </div>
                    <div className="bg-[#111b2e] border border-[#1c2c47] rounded-xl rounded-tl-sm p-3 text-slate-200 leading-relaxed shadow-sm">
                      {data?.query || "What changes occurred between these two dates?"}
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-teal-400 p-0.5 shrink-0 mt-0.5 shadow-md shadow-cyan-500/20">
                    <div className="w-full h-full bg-[#080e1b] rounded-[5px] flex items-center justify-center">
                      <svg className="w-3 h-3 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <polygon points="12 2 2 7 12 12 22 7 12 2" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex-1 space-y-3">
                    <div className="p-3.5 rounded-xl bg-[#091524] border border-[#162c46] space-y-3 leading-relaxed text-slate-300">
                      <p>{data?.answer || "I detected significant urban expansion in the northeastern part of the area between 2023 and 2025."}</p>
                      
                      {/* Confidence Meter */}
                      <div className="p-2 rounded-lg bg-[#0e172a] border border-[#1b2b46]">
                        <div className="flex items-center justify-between text-[11px] mb-1.5">
                          <span className="text-slate-400 flex items-center gap-1.5">
                            Confidence
                            <span className="flex items-center gap-1 text-emerald-400 font-medium">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                              High
                            </span>
                          </span>
                          <span className="font-bold text-cyan-400 font-mono">{Math.round((data?.confidence ?? 0.87) * 100)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-[#16233b] rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-teal-400 to-cyan-400 rounded-full" style={{ width: `${Math.round((data?.confidence ?? 0.87) * 100)}%` }} />
                        </div>
                      </div>

                      {/* Key stats if present */}
                      {stats && (
                        <div className="rounded-lg bg-[#0c1c2e]/70 border border-[#1b3552] p-2.5 space-y-1.5">
                          <div className="text-cyan-400 font-semibold text-[11px]">Key Findings</div>
                          <ul className="space-y-1 text-slate-300 pl-2 text-[11px]">
                            {stats.region_count > 0 && <li>Regions detected: <strong className="text-white">{stats.region_count}</strong></li>}
                            {stats.changed_pixels > 0 && <li>Changed pixels: <strong className="text-white">{stats.changed_pixels.toLocaleString()}</strong></li>}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === "analysis" && (
              <div className="p-3 rounded-lg bg-[#0c1626] border border-[#182a44] space-y-2">
                <h4 className="text-xs font-semibold text-white">Results Summary</h4>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-emerald-400 font-mono">{status}</span>
                </div>
              </div>
            )}

            {activeTab === "trace" && (
              <div className="space-y-2 text-[11px]">
                {[
                  { name: "Query interpreted", ms: "32ms" },
                  { name: "Input validated", ms: "410ms" },
                  { name: "Specialist selected", ms: "185ms" },
                  { name: "Analysis executed", ms: "1.42s" },
                ].map((step, idx) => (
                  <div key={idx} className="p-2 rounded bg-[#0b1626] border border-[#15253b] flex items-center justify-between">
                    <span className="text-slate-300">{step.name}</span>
                    <span className="text-[10px] font-mono text-slate-500">{step.ms}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="p-3 border-t border-[#152136] bg-[#090f1d] shrink-0">
            <div className="relative bg-[#0d1627] rounded-xl border border-[#1c2c47] focus-within:border-cyan-500/70 p-2.5">
              <input
                value={followUp}
                onChange={(e) => setFollowUp(e.target.value)}
                className="w-full bg-transparent border-none p-0 text-xs text-slate-200 placeholder-slate-500 focus:ring-0 focus:outline-none"
                placeholder="Ask a follow-up question..."
                type="text"
              />
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
