"use client";

import React, { useState, useRef, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { api } from "@/lib/api";
import type { UploadedRaster } from "@/lib/types";

function AnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("view") === "ongoing" ? "ongoing" : "initial";
  
  // State: "initial" (First Open before prompt) or "ongoing" (Active conversation / Split canvas)
  const [viewState, setViewState] = useState<"initial" | "ongoing">(initialMode);
  const [query, setQuery] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [activeTab, setActiveTab] = useState<"chat" | "analysis" | "trace">("chat");
  const [layerSelect, setLayerSelect] = useState("Natural Color (RGB)");
  const [modeSelect, setModeSelect] = useState<"compare" | "change_map" | "overlay">("compare");
  const [opacity, setOpacity] = useState(70);
  const [splitPos, setSplitPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  
  // Floating layer switcher toggles
  const [layerTab, setLayerTab] = useState<"images" | "layers">("images");
  const [layersToggle, setLayersToggle] = useState({
    changeDetection: true,
    urbanArea: false,
    vegetation: false,
    waterBodies: false,
  });

  const [t1Visible, setT1Visible] = useState(true);
  const [t2Visible, setT2Visible] = useState(true);
  const [relatedOpen, setRelatedOpen] = useState(true);
  const [advancedMode, setAdvancedMode] = useState(false);

  // Upload handling
  const [rasters, setRasters] = useState<UploadedRaster[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

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

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      const { rasters: uploaded } = await api.uploadRasters(Array.from(files));
      setRasters((prev) => [...prev, ...uploaded]);
    } catch {
      /* fallback */
    } finally {
      setUploading(false);
    }
  }

  const handleStartAnalysis = (textPrompt?: string) => {
    const promptToUse = textPrompt || query;
    if (promptToUse.trim()) {
      setQuery(promptToUse);
    }
    setViewState("ongoing");
  };

  return (
    <div className="h-screen w-full flex flex-col bg-[#050a12] text-slate-300 font-sans overflow-hidden select-none antialiased">
      {/* TopBar */}
      <TopBar showBrand={true} />

      {/* Main Interface Wrapper */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar hideBrand={true} />

        {/* ========================================================================= */}
        {/* STATE A: FIRST OPEN BEFORE CONVERSATION STARTS                            */}
        {/* ========================================================================= */}
        {viewState === "initial" && (
          <>
            {/* Center Workspace */}
            <main className="flex-1 flex flex-col bg-[#08101d] overflow-y-auto px-6 py-4 space-y-4">
              {/* Hero Banner */}
              <section className="relative overflow-hidden rounded-2xl border border-[#182c47] bg-gradient-to-r from-[#0a182a] via-[#0c1f38] to-[#071322] p-5 shrink-0">
                <div className="hero-glow-overlay absolute inset-0 pointer-events-none" />
                <div className="relative z-10 flex items-center justify-between">
                  {/* Left info */}
                  <div className="max-w-md space-y-2">
                    <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-400/30 text-cyan-400 text-[10px] font-semibold">
                      <svg className="w-3 h-3 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <span>AI ASSISTANT</span>
                    </div>
                    <h1 className="text-xl font-bold text-white tracking-tight">Your Satellite Intelligence Copilot</h1>
                    <p className="text-xs text-slate-300 leading-relaxed font-normal">
                      Ask questions, analyze imagery, get insights — powered by advanced AI and real satellite data.
                    </p>
                  </div>
                  
                  {/* Right Satellite Illustration Graphic */}
                  <div className="relative w-56 h-28 shrink-0 flex items-center justify-end">
                    {/* Globe / Inspection Zone */}
                    <div className="relative w-28 h-28 rounded-full border border-cyan-500/20 bg-gradient-to-tr from-cyan-950/60 to-blue-900/40 shadow-[0_0_25px_rgba(6,182,212,0.2)] overflow-hidden">
                      <div className="absolute inset-0 opacity-40 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:8px_8px]" />
                      <div className="absolute top-4 right-3 w-14 h-14 border border-cyan-400/60 bg-cyan-500/20 rounded-lg transform -rotate-12 backdrop-blur-xs flex items-center justify-center">
                        <span className="text-[8px] font-mono text-cyan-200">AOI-84</span>
                      </div>
                    </div>
                    {/* Orbiting Satellite Illustration */}
                    <div className="absolute -top-1 right-24 animate-pulse">
                      <div className="relative flex items-center">
                        <div className="w-3.5 h-6 bg-cyan-700/80 border border-cyan-400 rounded-sm" />
                        <div className="w-4 h-4 bg-slate-200 border-2 border-cyan-400 rounded-sm mx-0.5 shadow-md flex items-center justify-center">
                          <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full" />
                        </div>
                        <div className="w-3.5 h-6 bg-cyan-700/80 border border-cyan-400 rounded-sm" />
                        <div className="absolute -bottom-4 right-3 w-6 h-6 border-l border-b border-cyan-400/50 rounded-bl-full pointer-events-none" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 4 Action Quick Tiles */}
                <div className="grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-[#16273e]">
                  <div onClick={() => handleStartAnalysis("Perform land cover image analysis")} className="p-2.5 rounded-xl bg-[#0b1828]/90 border border-[#182e49] hover:border-cyan-500/50 hover:bg-[#0e2137] transition cursor-pointer flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <rect height="18" rx="2" strokeWidth="2" width="18" x="3" y="3" />
                        <circle cx="8.5" cy="8.5" fill="currentColor" r="1.5" />
                        <path d="M21 15l-5-5L5 21" strokeWidth="2" />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-white truncate">Image Analysis</h4>
                      <p className="text-[10px] text-slate-400 truncate">Understand what&apos;s in your imagery</p>
                    </div>
                  </div>

                  <div onClick={() => handleStartAnalysis("Extract bi-temporal change patterns")} className="p-2.5 rounded-xl bg-[#0b1828]/90 border border-[#182e49] hover:border-cyan-500/50 hover:bg-[#0e2137] transition cursor-pointer flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-white truncate">Data Insights</h4>
                      <p className="text-[10px] text-slate-400 truncate">Find patterns and changes</p>
                    </div>
                  </div>

                  <div onClick={() => router.push("/reports")} className="p-2.5 rounded-xl bg-[#0b1828]/90 border border-[#182e49] hover:border-cyan-500/50 hover:bg-[#0e2137] transition cursor-pointer flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-white truncate">Reports</h4>
                      <p className="text-[10px] text-slate-400 truncate">Generate detailed reports</p>
                    </div>
                  </div>

                  <div onClick={() => handleStartAnalysis("Fuse Sentinel-1 SAR with Sentinel-2 Optical")} className="p-2.5 rounded-xl bg-[#0b1828]/90 border border-[#182e49] hover:border-cyan-500/50 hover:bg-[#0e2137] transition cursor-pointer flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-white truncate">Multi-Modal</h4>
                      <p className="text-[10px] text-slate-400 truncate">Combine optical + SAR</p>
                    </div>
                  </div>
                </div>
              </section>

              {/* Center Prompt Suggestions Section */}
              <section className="flex-1 flex flex-col items-center justify-center py-6 px-4">
                <div className="w-10 h-10 rounded-full bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center mb-3 glow-cyan-sm">
                  <svg className="w-5 h-5 text-cyan-300" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z" />
                  </svg>
                </div>
                <h2 className="text-lg font-bold text-white text-center">How can I help you today?</h2>
                <p className="text-xs text-slate-400 text-center max-w-md mt-1 mb-6">
                  Ask anything about your satellite data — from land cover analysis to change detection, I&apos;m here to help.
                </p>

                {/* 6 Suggested Prompts Grid */}
                <div className="grid grid-cols-2 gap-3 w-full max-w-2xl">
                  {[
                    { text: "Detect urban expansion in this region", iconPath: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" },
                    { text: "Find changes in vegetation over time", iconPath: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" },
                    { text: "Identify water bodies in the area", iconPath: "M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" },
                    { text: "Generate a summary report", iconPath: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
                    { text: "Compare optical and SAR data", iconPath: "M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" },
                    { text: "Analyze land use patterns", iconPath: "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" },
                  ].map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleStartAnalysis(item.text)}
                      className="flex items-center space-x-3 p-3 text-left rounded-xl bg-[#091524] border border-[#162a42] hover:border-cyan-500/40 hover:bg-[#0c1d32] transition group"
                    >
                      <svg className="w-4 h-4 text-cyan-400 shrink-0 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d={item.iconPath} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      </svg>
                      <span className="text-xs text-slate-300 group-hover:text-white font-medium">{item.text}</span>
                    </button>
                  ))}
                </div>
              </section>

              {/* Bottom Chat Query Composer Box */}
              <div className="mt-auto pt-2 shrink-0">
                <div className="rounded-xl border border-[#1a304e] bg-[#091423] p-3 shadow-lg">
                  {/* Text Input Row */}
                  <div className="flex items-center space-x-3 pb-2.5">
                    <button onClick={() => fileRef.current?.click()} className="text-slate-400 hover:text-cyan-400 transition p-1">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <rect height="18" rx="2" strokeWidth="2" width="18" x="3" y="3" />
                        <circle cx="8.5" cy="8.5" fill="currentColor" r="1.5" />
                        <path d="M21 15l-5-5L5 21" strokeWidth="2" />
                      </svg>
                    </button>
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleStartAnalysis();
                      }}
                      className="flex-1 bg-transparent border-0 text-xs text-white placeholder-slate-400 focus:ring-0 focus:outline-none"
                      placeholder="Ask a question about your satellite imagery..."
                      type="text"
                    />
                    <button
                      onClick={() => handleStartAnalysis()}
                      className="w-8 h-8 rounded-lg bg-gradient-to-r from-cyan-500 to-sky-500 flex items-center justify-center text-slate-950 font-bold hover:brightness-110 transition shadow-[0_0_10px_rgba(6,182,212,0.5)] cursor-pointer"
                    >
                      <svg className="w-4 h-4 text-[#041019]" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>

                  {/* Bottom Action Buttons & Settings */}
                  <div className="flex items-center justify-between pt-2 border-t border-[#132338] text-[11px]">
                    <div className="flex items-center space-x-2">
                      <button onClick={() => fileRef.current?.click()} className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#0e1f34] border border-[#1b3452] text-slate-300 hover:text-white hover:border-cyan-500/40 transition">
                        <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                        </svg>
                        <span>Attach Image</span>
                      </button>
                      <button onClick={() => router.push("/datasets")} className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#0e1f34] border border-[#1b3452] text-slate-300 hover:text-white hover:border-cyan-500/40 transition">
                        <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <ellipse cx="12" cy="5" rx="9" ry="3" strokeWidth="2" />
                          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" strokeWidth="2" />
                          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" strokeWidth="2" />
                        </svg>
                        <span>Select Dataset</span>
                      </button>
                      <div className="relative">
                        <button className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#0e1f34] border border-[#1b3452] text-slate-300 hover:text-white hover:border-cyan-500/40 transition">
                          <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="3" strokeWidth="2" />
                            <path d="M19 12a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeWidth="2" />
                          </svg>
                          <span>Choose Analysis Type</span>
                          <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    {/* Advanced Toggle Switch */}
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-400 font-medium">Advanced</span>
                      <div
                        onClick={() => setAdvancedMode(!advancedMode)}
                        className={`w-8 h-4 rounded-full p-0.5 flex items-center cursor-pointer transition ${
                          advancedMode ? "bg-cyan-600 justify-end" : "bg-[#142840] border border-[#223d60] justify-start"
                        }`}
                      >
                        <div className="w-3 h-3 bg-slate-300 rounded-full" />
                      </div>
                    </div>
                  </div>
                </div>

                <input ref={fileRef} type="file" multiple accept=".tif,.tiff,.png,.jpg,.jpeg" className="hidden" onChange={(e) => handleUpload(e.target.files)} />

                {/* Copilot Status Footer */}
                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2 px-1">
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-1.5">
                      <div className="w-3.5 h-3.5 rounded-full bg-emerald-500/20 border border-emerald-400/50 flex items-center justify-center text-emerald-400">
                        <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                          <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <span className="text-emerald-400 font-medium">AI Assistant Ready</span>
                    </div>
                    <span className="text-slate-600">|</span>
                    <span>Powered by Advanced ML Models</span>
                  </div>

                  {/* Switch to Ongoing View Button for interactive exploration */}
                  <button
                    onClick={() => setViewState("ongoing")}
                    className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 border border-cyan-800/50 px-2 py-0.5 rounded cursor-pointer transition"
                  >
                    <span>Inspect Ongoing Split-Screen Workstation</span>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                    </svg>
                  </button>
                </div>
              </div>
            </main>

            {/* RightSidebar Chat & Analysis Panel */}
            <aside className="w-[430px] bg-[#070d18] border-l border-[#15253b] flex flex-col justify-between shrink-0">
              {/* Top Navigation Tabs */}
              <div className="border-b border-[#15253b] px-4 pt-3 pb-2 flex items-center justify-between shrink-0">
                <div className="flex items-center space-x-6 text-xs font-semibold">
                  <button
                    onClick={() => setActiveTab("chat")}
                    className={`pb-2 -mb-2 px-1 transition ${activeTab === "chat" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"}`}
                  >
                    Chat
                  </button>
                  <button
                    onClick={() => setActiveTab("analysis")}
                    className={`pb-2 -mb-2 px-1 transition ${activeTab === "analysis" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"}`}
                  >
                    Analysis
                  </button>
                  <button
                    onClick={() => setActiveTab("trace")}
                    className={`pb-2 -mb-2 px-1 transition ${activeTab === "trace" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"}`}
                  >
                    Execution Trace
                  </button>
                </div>
                <button onClick={() => setViewState("ongoing")} title="Open Split Screen" className="text-slate-400 hover:text-white transition p-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                </button>
              </div>

              {/* Scrollable Chat Stream */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                {/* User Query Bubble */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-[9px]">
                        SM
                      </div>
                      <span className="font-semibold text-white">You</span>
                    </div>
                    <span className="text-[10px] text-slate-500">11:42 AM</span>
                  </div>
                  <div className="p-3 rounded-xl bg-[#0e1c2e] border border-[#1b3452] text-slate-200 leading-relaxed">
                    Analyze this area and tell me what changes occurred between 2022 and 2025. Focus on vegetation loss and new construction.
                  </div>
                </div>

                {/* AI Response Stream */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 rounded-md bg-gradient-to-tr from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 font-bold text-[9px] shadow-[0_0_8px_rgba(6,182,212,0.5)]">
                        <svg className="w-3 h-3 text-slate-950 transform -rotate-45" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                          <ellipse cx="12" cy="12" rx="10" ry="4" stroke="currentColor" />
                          <circle cx="12" cy="12" fill="currentColor" r="2" />
                        </svg>
                      </div>
                      <span className="font-semibold text-cyan-300">SatQuery AI</span>
                    </div>
                    <span className="text-[10px] text-slate-500">11:44 AM</span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-[#091524] border border-[#162c46] space-y-3 leading-relaxed text-slate-300">
                    <p>Based on the satellite imagery analysis, here are the key findings for the area between 2022 and 2025:</p>
                    
                    {/* Key Findings Box */}
                    <div className="rounded-lg bg-[#0c1c2e]/70 border border-[#1b3552] p-2.5 space-y-1.5">
                      <div className="flex items-center space-x-1.5 text-cyan-400 font-semibold text-[11px]">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <circle cx="11" cy="11" r="7" strokeWidth="2" />
                          <line strokeWidth="2" x1="21" x2="16.65" y1="21" y2="16.65" />
                        </svg>
                        <span>Key Findings</span>
                      </div>
                      <ul className="space-y-1 text-slate-300 pl-2 text-[11px]">
                        <li className="flex items-center space-x-1.5">
                          <span className="w-1 h-1 rounded-full bg-cyan-400" />
                          <span>Vegetation loss: <strong className="text-white">12.4%</strong> (≈ 2.8 km²)</span>
                        </li>
                        <li className="flex items-center space-x-1.5">
                          <span className="w-1 h-1 rounded-full bg-cyan-400" />
                          <span>New built-up area: <strong className="text-white">8.7%</strong> (≈ 1.9 km²)</span>
                        </li>
                        <li className="flex items-center space-x-1.5">
                          <span className="w-1 h-1 rounded-full bg-cyan-400" />
                          <span>Water body change: <strong className="text-white">+1.2%</strong> (≈ 0.3 km²)</span>
                        </li>
                      </ul>
                    </div>

                    {/* Major Changes numbered list */}
                    <div className="space-y-1.5">
                      <div className="flex items-center space-x-1.5 text-cyan-400 font-semibold text-[11px]">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <rect height="18" rx="2" strokeWidth="2" width="18" x="3" y="3" />
                          <path d="M3 9h18M9 21V9" strokeWidth="2" />
                        </svg>
                        <span>Major Changes</span>
                      </div>
                      <ol className="space-y-1 text-slate-300 text-[11px] pl-4 list-decimal marker:text-slate-500">
                        <li>Urban expansion detected in the northern and eastern parts of the area.</li>
                        <li>Significant vegetation loss in the red-marked region (agricultural land → built-up).</li>
                        <li>New road network visible in 2025 (not present in 2022).</li>
                      </ol>
                    </div>

                    {/* Side-by-side Bi-temporal Comparison Cards & Legend */}
                    <div className="pt-1">
                      <div className="flex space-x-2">
                        {/* 2022 image card */}
                        <div className="flex-1">
                          <div className="relative rounded-lg overflow-hidden border border-[#1f3b5e] aspect-[4/3] bg-emerald-950/40 group">
                            <img alt="2022 Satellite Image" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDKIRiHnITIQ7x_KqxlLXRc7Lkse3FAAyyOixrgd4MExlWH2gJpOTRvi16JdlPaDsqx3ImZ4O9XZhQUzVALbBfhVkZarAhqDUJ__tbXM_dOGop4mpwzTWxtJ-Gq326fX9PuDKefCU4OBwT26HcZWBqT5Yt_asLZkHhtzZ3g1P0EyoTTjybhWVbeMppEZEcOzDVyiZ8OGu3YuwvOEHxS_CbmLcEwGwgSTQtpwXkeEbNataoAmHfSHDE" />
                            <span className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-black/70 backdrop-blur-xs text-[9px] font-mono text-slate-200 rounded">
                              2022
                            </span>
                          </div>
                        </div>
                        {/* 2025 image card */}
                        <div className="flex-1">
                          <div className="relative rounded-lg overflow-hidden border border-red-500/40 aspect-[4/3] bg-rose-950/40 group">
                            <img alt="2025 Satellite Image" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAleuPJklrxSMrKt_Jm_gOADvirhDFxyVb8Qg2usFH6JEYf_o9wZ-3A4ar24sLI-mhTyJ2WIOUNvUoOIjcQ-0LM9ZOICH-nfwkX5M6cFjMeSXwvhLQLk3b4-5bAG5SkleUXwDtZLKyE6GzelpBug5BuiT3A94pmxvVnr8qkFC3VYwjhk3uuwg4JfHWWfyLmWZWOyFuRI4K9A0AhWAAz98YN788qrzOc9BecUN9Dtd-o4y6pkl4bdc0" />
                            <span className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-black/70 backdrop-blur-xs text-[9px] font-mono text-slate-200 rounded">
                              2025
                            </span>
                          </div>
                        </div>
                        {/* Legend pills column */}
                        <div className="w-24 space-y-1 shrink-0 text-[9px] text-slate-300 flex flex-col justify-center">
                          <div className="flex items-center space-x-1.5">
                            <span className="w-2 h-2 rounded-xs bg-[#ef4444]" />
                            <span>Built-up area</span>
                          </div>
                          <div className="flex items-center space-x-1.5">
                            <span className="w-2 h-2 rounded-xs bg-[#f97316]" />
                            <span>Vegetation loss</span>
                          </div>
                          <div className="flex items-center space-x-1.5">
                            <span className="w-2 h-2 rounded-xs bg-[#eab308]" />
                            <span>New roads</span>
                          </div>
                          <div className="flex items-center space-x-1.5">
                            <span className="w-2 h-2 rounded-xs bg-[#3b82f6]" />
                            <span>Water body</span>
                          </div>
                        </div>
                      </div>

                      {/* View Full Analysis CTA button */}
                      <button
                        onClick={() => setViewState("ongoing")}
                        className="w-full mt-2.5 py-1.5 px-3 rounded-lg bg-[#0e2239] border border-[#1d3d63] hover:border-cyan-400/50 hover:bg-[#122b49] transition text-cyan-300 text-[11px] font-medium flex items-center justify-center space-x-1.5 cursor-pointer shadow-sm"
                      >
                        <span>View Full Analysis</span>
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Related Insights Accordion Card */}
                  <div className="rounded-xl bg-[#091524] border border-[#162c46] overflow-hidden">
                    <div
                      onClick={() => setRelatedOpen(!relatedOpen)}
                      className="p-2.5 flex items-center justify-between border-b border-[#14263c] cursor-pointer hover:bg-[#0c1a2c]"
                    >
                      <div className="flex items-center space-x-2 text-cyan-400 text-xs font-semibold">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="3" strokeWidth="2" />
                          <path d="M19 12a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeWidth="2" />
                        </svg>
                        <span>Related Insights</span>
                      </div>
                      <svg className={`w-3.5 h-3.5 text-slate-400 transition-transform ${relatedOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      </svg>
                    </div>
                    {relatedOpen && (
                      <div className="divide-y divide-[#122338] text-[11px]">
                        <div onClick={() => setViewState("ongoing")} className="p-2.5 flex items-center justify-between hover:bg-[#0c1b2f] cursor-pointer text-slate-300 hover:text-white transition">
                          <div className="flex items-center space-x-2">
                            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <rect height="18" rx="2" strokeWidth="2" width="18" x="3" y="3" />
                              <circle cx="8.5" cy="8.5" fill="currentColor" r="1.5" />
                              <path d="M21 15l-5-5L5 21" strokeWidth="2" />
                            </svg>
                            <span>Land use change details</span>
                          </div>
                          <svg className="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                          </svg>
                        </div>
                        <div onClick={() => setViewState("ongoing")} className="p-2.5 flex items-center justify-between hover:bg-[#0c1b2f] cursor-pointer text-slate-300 hover:text-white transition">
                          <div className="flex items-center space-x-2">
                            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <rect height="18" rx="2" strokeWidth="2" width="18" x="3" y="3" />
                              <line strokeWidth="2" x1="3" x2="21" y1="9" y2="9" />
                              <line strokeWidth="2" x1="9" x2="9" y1="21" y2="9" />
                            </svg>
                            <span>Change statistics (table)</span>
                          </div>
                          <svg className="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                          </svg>
                        </div>
                        <div onClick={() => router.push("/reports")} className="p-2.5 flex items-center justify-between hover:bg-[#0c1b2f] cursor-pointer text-slate-300 hover:text-white transition">
                          <div className="flex items-center space-x-2">
                            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                            </svg>
                            <span>Download report (PDF)</span>
                          </div>
                          <svg className="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                          </svg>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Bottom Chat Follow-up Input Bar */}
              <div className="p-3 border-t border-[#15253b] bg-[#070e19] shrink-0">
                <div className="flex items-center space-x-2">
                  <button onClick={() => fileRef.current?.click()} className="p-2 rounded-lg bg-[#0b1625] border border-[#1b3452] text-slate-400 hover:text-white transition">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                    </svg>
                  </button>
                  <div className="relative flex-1 flex items-center">
                    <input
                      value={followUp}
                      onChange={(e) => setFollowUp(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleStartAnalysis(followUp);
                      }}
                      className="w-full h-9 px-3 pr-10 text-xs bg-[#0b1625] border border-[#1b3452] rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500 transition"
                      placeholder="Ask a follow-up question..."
                      type="text"
                    />
                    <button
                      onClick={() => handleStartAnalysis(followUp)}
                      className="absolute right-1.5 w-6 h-6 rounded bg-gradient-to-r from-cyan-500 to-sky-500 flex items-center justify-center text-slate-950 font-bold hover:brightness-110 transition cursor-pointer"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </aside>
          </>
        )}

        {/* ========================================================================= */}
        {/* STATE B: ONGOING CONVERSATION WORKSTATION WITH SPLIT-SCREEN VISUALIZER      */}
        {/* ========================================================================= */}
        {viewState === "ongoing" && (
          <>
            {/* Center Workspace */}
            <main className="flex-1 flex flex-col bg-[#070b14] overflow-hidden border-r border-[#152033]">
              {/* Sub-header & Breadcrumb Navigation */}
              <div className="px-5 py-3 border-b border-[#141d2f] bg-[#090f1d] flex flex-col gap-2 shrink-0">
                <div className="flex items-center justify-between">
                  <div>
                    <button
                      onClick={() => setViewState("initial")}
                      className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-300 transition cursor-pointer"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                      </svg>
                      <span>Back to New Analysis</span>
                    </button>
                    <div className="flex items-center gap-2.5 mt-1">
                      <h1 className="text-lg font-bold text-white tracking-tight">Urban Expansion Analysis</h1>
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
                    <button onClick={() => router.push("/reports")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#22334f] bg-[#101a2d] hover:bg-[#16233b] text-xs font-medium text-slate-200 transition">
                      <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                        <polyline points="16 6 12 2 8 6" />
                        <line x1="12" x2="12" y1="2" y2="15" />
                      </svg>
                      <span>Export</span>
                    </button>
                    <button className="p-1.5 rounded-lg border border-[#22334f] bg-[#101a2d] hover:bg-[#16233b] text-slate-400 hover:text-white transition">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="1" />
                        <circle cx="19" cy="12" r="1" />
                        <circle cx="5" cy="12" r="1" />
                      </svg>
                    </button>
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
                    <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <rect height="18" rx="2" ry="2" width="18" x="3" y="3" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <span>2 images</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400 ml-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    <span>Oct 12, 2025, 11:42 AM</span>
                  </div>
                </div>
              </div>

              {/* Satellite View Controls Bar */}
              <div className="h-11 px-4 border-b border-[#141e30] bg-[#0a101f] flex items-center justify-between text-xs shrink-0">
                <div className="flex items-center gap-3">
                  {/* Layer Dropdown */}
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
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <rect height="18" rx="2" width="20" x="2" y="3" />
                        <line x1="12" x2="12" y1="3" y2="21" />
                      </svg>
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
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                        <path d="M2 12h20" />
                      </svg>
                      <span>Change Map</span>
                    </button>
                    <button
                      onClick={() => setModeSelect("overlay")}
                      className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition ${
                        modeSelect === "overlay"
                          ? "bg-cyan-900/60 border border-cyan-600/40 text-cyan-300 font-medium shadow-sm"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <rect height="18" rx="2" width="18" x="3" y="3" />
                        <rect height="3" width="3" x="7" y="7" />
                      </svg>
                      <span>Overlay</span>
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

                {/* Right Tool Icons */}
                <div className="flex items-center gap-1 text-slate-400">
                  <button className="p-1.5 hover:text-slate-200 hover:bg-[#121c2d] rounded transition">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                  </button>
                  <button className="p-1.5 hover:text-slate-200 hover:bg-[#121c2d] rounded transition">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" x2="16.65" y1="21" y2="16.65" />
                    </svg>
                  </button>
                  <button className="p-1.5 hover:text-slate-200 hover:bg-[#121c2d] rounded transition">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M15 3h6v6" />
                      <path d="M9 21H3v-6" />
                      <path d="M21 3l-7 7" />
                      <path d="M3 21l7-7" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Main Satellite Canvas & Overlay Panel */}
              <div ref={containerRef} className="relative flex-1 bg-black overflow-hidden flex select-none">
                {/* Floating Left Layer Switcher Box */}
                <div className="absolute left-3 top-3 z-20 w-52 bg-[#09111e]/90 backdrop-blur-md rounded-lg border border-[#1b2b46] shadow-2xl p-2.5 text-xs select-none">
                  {/* Layer Tabs */}
                  <div className="flex border-b border-[#1b2a42] mb-2.5 pb-1">
                    <button
                      onClick={() => setLayerTab("images")}
                      className={`flex-1 text-center py-1 font-semibold text-[11px] transition ${
                        layerTab === "images" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      Images
                    </button>
                    <button
                      onClick={() => setLayerTab("layers")}
                      className={`flex-1 text-center py-1 text-[11px] transition ${
                        layerTab === "layers" ? "text-cyan-400 border-b-2 border-cyan-400" : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      Layers
                    </button>
                  </div>

                  {/* Image Items */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-1.5 rounded-md bg-[#101b2f] border border-cyan-900/50">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded bg-emerald-900 overflow-hidden border border-emerald-500/40 relative">
                          <div className="w-full h-full satellite-bg-base scale-150" />
                        </div>
                        <div>
                          <div className="text-[11px] font-semibold text-slate-200 leading-tight">T1 - 2023-01-15</div>
                          <div className="text-[9px] text-slate-400">Optical (Sentinel-2)</div>
                        </div>
                      </div>
                      <button onClick={() => setT1Visible(!t1Visible)} className={t1Visible ? "text-cyan-400 hover:text-cyan-300" : "text-slate-600"}>
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      </button>
                    </div>

                    <div className="flex items-center justify-between p-1.5 rounded-md bg-[#101b2f] border border-[#1f314d]">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded bg-emerald-950 overflow-hidden border border-red-500/50 relative">
                          <div className="w-full h-full satellite-bg-base scale-150" />
                          <div className="absolute inset-0 bg-red-500/20" />
                        </div>
                        <div>
                          <div className="text-[11px] font-semibold text-slate-200 leading-tight">T2 - 2025-01-18</div>
                          <div className="text-[9px] text-slate-400">Optical (Sentinel-2)</div>
                        </div>
                      </div>
                      <button onClick={() => setT2Visible(!t2Visible)} className={t2Visible ? "text-cyan-400 hover:text-cyan-300" : "text-slate-600"}>
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Additional Layer Toggles */}
                  <div className="mt-3 pt-2.5 border-t border-[#172439]">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Additional Layers</span>
                    <div className="mt-2 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-300 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-purple-400 shadow-sm shadow-purple-500/50" />
                          Change Detection
                        </span>
                        <div
                          onClick={() => setLayersToggle((p) => ({ ...p, changeDetection: !p.changeDetection }))}
                          className={`w-7 h-4 rounded-full p-0.5 cursor-pointer flex items-center transition ${
                            layersToggle.changeDetection ? "bg-cyan-600 justify-end" : "bg-[#1a273e] border border-[#263a5a] justify-start"
                          }`}
                        >
                          <div className="w-3 h-3 rounded-full bg-white shadow-sm" />
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-300 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-red-400 shadow-sm shadow-red-500/50" />
                          Urban Area (Detected)
                        </span>
                        <div
                          onClick={() => setLayersToggle((p) => ({ ...p, urbanArea: !p.urbanArea }))}
                          className={`w-7 h-4 rounded-full p-0.5 cursor-pointer flex items-center transition ${
                            layersToggle.urbanArea ? "bg-cyan-600 justify-end" : "bg-[#1a273e] border border-[#263a5a] justify-start"
                          }`}
                        >
                          <div className="w-3 h-3 rounded-full bg-slate-400 shadow-sm" />
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-300 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-500/50" />
                          Vegetation (NDVI)
                        </span>
                        <div
                          onClick={() => setLayersToggle((p) => ({ ...p, vegetation: !p.vegetation }))}
                          className={`w-7 h-4 rounded-full p-0.5 cursor-pointer flex items-center transition ${
                            layersToggle.vegetation ? "bg-cyan-600 justify-end" : "bg-[#1a273e] border border-[#263a5a] justify-start"
                          }`}
                        >
                          <div className="w-3 h-3 rounded-full bg-slate-400 shadow-sm" />
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-300 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-sky-400 shadow-sm shadow-sky-500/50" />
                          Water Bodies
                        </span>
                        <div
                          onClick={() => setLayersToggle((p) => ({ ...p, waterBodies: !p.waterBodies }))}
                          className={`w-7 h-4 rounded-full p-0.5 cursor-pointer flex items-center transition ${
                            layersToggle.waterBodies ? "bg-cyan-600 justify-end" : "bg-[#1a273e] border border-[#263a5a] justify-start"
                          }`}
                        >
                          <div className="w-3 h-3 rounded-full bg-slate-400 shadow-sm" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Split Screen Satellite Visualizer Canvas */}
                <div className="relative w-full h-full flex overflow-hidden">
                  {/* LEFT SIDE: T1 (Historical Baseline 2023) */}
                  <div
                    style={{ width: `${splitPos}%`, opacity: t1Visible ? 1 : 0.2 }}
                    className="relative h-full overflow-hidden border-r border-cyan-500/30 transition-opacity"
                  >
                    <div className="absolute inset-0 satellite-bg-base">
                      {/* Natural river representation */}
                      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85" preserveAspectRatio="none" viewBox="0 0 500 500">
                        <path d="M 120 -10 C 260 120, 210 280, 360 520" fill="none" stroke="#122c3f" strokeLinecap="round" strokeWidth="52" />
                        <path d="M 120 -10 C 260 120, 210 280, 360 520" fill="none" stroke="#1a3d54" strokeWidth="44" />
                      </svg>
                      {/* Field and agricultural texture patterns */}
                      <div className="absolute inset-0 opacity-40 mix-blend-overlay" style={{ backgroundImage: "radial-gradient(#6ee7b7 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
                    </div>

                    {/* T1 Timestamp Tag */}
                    <div className="absolute top-3 left-60 bg-[#09111e]/80 backdrop-blur border border-[#1e2f4a] px-2.5 py-1 rounded text-[11px] font-medium text-slate-200 z-10 shadow-md">
                      T1 - 2023-01-15
                    </div>

                    {/* Distance Scale Indicator */}
                    <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-1 bg-[#09111e]/85 backdrop-blur px-2.5 py-1.5 rounded border border-[#1b2b46]">
                      <div className="flex justify-between text-[9px] font-mono text-slate-300 w-28">
                        <span>0</span>
                        <span>0.5</span>
                        <span>1km</span>
                      </div>
                      <div className="h-1 w-28 bg-slate-200 flex">
                        <div className="w-1/2 h-full bg-slate-900 border-r border-slate-200" />
                        <div className="w-1/2 h-full bg-slate-200" />
                      </div>
                    </div>
                  </div>

                  {/* RIGHT SIDE: T2 (Current 2025 with AI Change Detection Vectors) */}
                  <div
                    style={{ width: `${100 - splitPos}%`, opacity: t2Visible ? opacity / 100 : 0.2 }}
                    className="relative h-full overflow-hidden transition-opacity"
                  >
                    <div className="absolute inset-0 satellite-bg-base">
                      {/* River continuous path */}
                      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85" preserveAspectRatio="none" viewBox="0 0 500 500">
                        <path d="M -140 -10 C 0 120, -50 280, 100 520" fill="none" stroke="#122c3f" strokeLinecap="round" strokeWidth="52" />
                        <path d="M -140 -10 C 0 120, -50 280, 100 520" fill="none" stroke="#1a3d54" strokeWidth="44" />
                      </svg>

                      {/* RED AI DETECTION OVERLAYS */}
                      {layersToggle.changeDetection && <div className="absolute inset-0 urban-detection-layer" />}

                      {/* Vectorized High-density Detected Building Outlines */}
                      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 500 500">
                        <g fill="rgba(239, 68, 68, 0.22)" stroke="#ef4444" strokeWidth="1.5">
                          <rect height="18" rx="1" width="22" x="260" y="70" />
                          <rect height="20" rx="1" width="30" x="290" y="65" />
                          <rect height="28" rx="1" width="25" x="330" y="80" />
                          <polygon points="275,100 310,105 305,130 265,120" />
                          <polygon points="320,115 365,120 355,150 315,140" />
                          <rect height="30" width="35" x="375" y="100" />
                          <rect height="22" width="28" x="290" y="145" />
                          <polygon points="330,160 380,165 370,195 325,185" />
                          <polygon points="240,140 280,145 270,180 230,170" />
                          <rect height="35" width="40" x="390" y="150" />
                          <rect height="30" width="45" x="310" y="200" />
                          <polygon points="365,210 410,215 400,245 355,235" />
                          <rect height="25" width="30" x="270" y="220" />
                          <rect height="25" width="35" x="230" y="340" />
                          <polygon points="275,345 315,350 305,385 265,375" />
                          <rect height="30" width="40" x="325" y="360" />
                          <polygon points="245,380 290,390 280,425 235,410" />
                          <rect height="35" width="35" x="300" y="405" />
                        </g>
                        <path d="M 250 80 L 440 140 M 270 140 L 430 220 M 320 60 L 370 280 M 260 330 L 380 430" fill="none" stroke="#ef4444" strokeDasharray="3,3" strokeWidth="1.8" />
                      </svg>
                    </div>

                    {/* T2 Timestamp Tag */}
                    <div className="absolute top-3 right-4 bg-[#09111e]/80 backdrop-blur border border-[#1e2f4a] px-2.5 py-1 rounded text-[11px] font-medium text-slate-200 z-10 shadow-md">
                      T2 - 2025-01-18
                    </div>
                  </div>

                  {/* Interactive Center Splitter Divider / Handle */}
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

                  {/* Map Navigation Widget Controls */}
                  <div className="absolute right-4 bottom-6 z-20 flex flex-col gap-1.5">
                    <div className="flex flex-col bg-[#091222]/90 backdrop-blur rounded-lg border border-[#1c2c48] overflow-hidden shadow-xl">
                      <button className="w-7 h-7 flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#15233c] text-sm font-bold border-b border-[#1c2c48] cursor-pointer">+</button>
                      <button className="w-7 h-7 flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#15233c] text-sm font-bold cursor-pointer">-</button>
                    </div>
                    <button className="w-7 h-7 rounded-lg bg-[#091222]/90 backdrop-blur border border-[#1c2c48] flex items-center justify-center text-slate-300 hover:text-white shadow-xl cursor-pointer">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polygon points="12 2 2 7 12 12 22 7 12 2" />
                        <polyline points="2 17 12 22 22 17" />
                        <polyline points="2 12 12 17 22 12" />
                      </svg>
                    </button>
                    <div className="w-7 h-7 rounded-lg bg-[#091222]/90 backdrop-blur border border-[#1c2c48] flex items-center justify-center text-xs font-bold text-rose-500 shadow-xl">
                      <svg className="w-4 h-4 text-rose-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polygon fill="#ef4444" points="12 2 16 11 12 8 8 11 12 2" />
                        <polygon fill="#64748b" points="12 22 8 13 12 16 16 13 12 22" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Filmstrip / Image Thumbnails Strip */}
              <div className="h-20 border-t border-[#141e31] bg-[#080d19] px-4 flex items-center gap-3 shrink-0">
                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#0e1728] border border-cyan-700/60 shadow-md cursor-pointer">
                  <div className="w-14 h-12 rounded bg-emerald-950 border border-emerald-600/40 relative overflow-hidden shrink-0">
                    <div className="w-full h-full satellite-bg-base scale-125" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">T1 - 2023-01-15</div>
                    <div className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5">
                      <svg className="w-3 h-3 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      Optical (Sentinel-2)
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#0e1728] border border-[#1c2c46] hover:border-slate-500 shadow-md cursor-pointer transition">
                  <div className="w-14 h-12 rounded bg-emerald-950 border border-red-500/50 relative overflow-hidden shrink-0">
                    <div className="w-full h-full satellite-bg-base scale-125" />
                    <div className="absolute inset-0 bg-red-500/20" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">T2 - 2025-01-18</div>
                    <div className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5">
                      <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      Optical (Sentinel-2)
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => fileRef.current?.click()}
                  className="h-14 px-4 rounded-lg border-2 border-dashed border-[#1e2e4b] hover:border-cyan-500/60 bg-[#0a1220] flex flex-col items-center justify-center text-slate-400 hover:text-cyan-400 transition cursor-pointer"
                >
                  <svg className="w-4 h-4 mb-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <line x1="12" x2="12" y1="5" y2="19" />
                    <line x1="5" x2="19" y1="12" y2="12" />
                  </svg>
                  <span className="text-[10px] font-medium">+ Add Image</span>
                </button>
              </div>
            </main>

            {/* Right Chat Drawer */}
            <aside className="w-[420px] bg-[#090f1d] flex flex-col shrink-0 select-text overflow-hidden">
              {/* Drawer Navigation Tabs */}
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
                <button title="Maximize view" className="text-slate-400 hover:text-white p-1 rounded">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <polyline points="15 3 21 3 21 9" />
                    <polyline points="9 21 3 21 3 15" />
                    <line x1="21" x2="14" y1="3" y2="10" />
                    <line x1="3" x2="10" y1="21" y2="14" />
                  </svg>
                </button>
              </div>

              {/* Chat Messages Scrollable Feed */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                {activeTab === "chat" && (
                  <>
                    {/* User Query Bubble */}
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] font-bold text-white shrink-0 mt-0.5">
                        <svg className="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold text-slate-200">You</span>
                          <span className="text-[10px] text-slate-500 font-mono">11:42 AM</span>
                        </div>
                        <div className="bg-[#111b2e] border border-[#1c2c47] rounded-xl rounded-tl-sm p-3 text-slate-200 leading-relaxed shadow-sm">
                          {query || "What changed between these two dates, and where did the change occur?"}
                        </div>
                      </div>
                    </div>

                    {/* AI Assistant Response Bubble */}
                    <div className="flex items-start gap-2.5">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-teal-400 p-0.5 shrink-0 mt-0.5 shadow-md shadow-cyan-500/20">
                        <div className="w-full h-full bg-[#080e1b] rounded-[5px] flex items-center justify-center">
                          <svg className="w-3 h-3 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                            <polygon points="12 2 2 7 12 12 22 7 12 2" />
                          </svg>
                        </div>
                      </div>
                      <div className="flex-1 space-y-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="font-semibold text-white">SatQuery AI</span>
                            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-800/40">
                              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                              Analysis completed • 2.8s
                            </span>
                          </div>
                          <p className="text-slate-300 leading-relaxed">
                            I detected significant urban expansion in the northeastern part of the area between 2023 and 2025.
                          </p>
                          <div className="mt-2 text-slate-300 space-y-1">
                            <p className="font-medium text-slate-200">Major changes include:</p>
                            <ul className="space-y-1 pl-1 text-slate-300">
                              <li className="flex items-center gap-1.5"><span className="text-cyan-400">•</span> New built-up structures (residential/commercial)</li>
                              <li className="flex items-center gap-1.5"><span className="text-cyan-400">•</span> Expansion of road network</li>
                              <li className="flex items-center gap-1.5"><span className="text-cyan-400">•</span> Reduction in vegetation cover</li>
                            </ul>
                          </div>
                          <p className="mt-2 text-slate-300">
                            The change is primarily concentrated in the northeast quadrant of the image.
                          </p>
                        </div>

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
                            <span className="font-bold text-cyan-400 font-mono">87%</span>
                          </div>
                          <div className="h-1.5 w-full bg-[#16233b] rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-teal-400 to-cyan-400 rounded-full" style={{ width: "87%" }} />
                          </div>
                        </div>

                        {/* Visual Evidence Card */}
                        <div className="rounded-lg bg-[#0d1627] border border-[#1a2b47] p-3 space-y-2.5">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-200 flex items-center gap-1.5 text-[11px]">
                              <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <rect height="18" rx="2" width="18" x="3" y="3" />
                                <circle cx="8.5" cy="8.5" r="1.5" />
                                <polyline points="21 15 16 10 5 21" />
                              </svg>
                              Visual Evidence
                            </span>
                          </div>
                          {/* Side by side thumbnails */}
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <div className="h-20 rounded bg-emerald-950 border border-[#1f314d] relative overflow-hidden">
                                <div className="w-full h-full satellite-bg-base scale-125" />
                              </div>
                              <span className="text-[10px] text-slate-400 mt-1 block">2023</span>
                            </div>
                            <div>
                              <div className="h-20 rounded bg-emerald-950 border border-red-500/50 relative overflow-hidden">
                                <div className="w-full h-full satellite-bg-base scale-125" />
                                <div className="absolute inset-0 bg-red-500/25" />
                              </div>
                              <span className="text-[10px] text-slate-400 mt-1 block">2025</span>
                            </div>
                          </div>
                          {/* Legend */}
                          <div className="space-y-1 pt-1 text-[10px] text-slate-400 border-t border-[#17253b]">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-sm bg-red-500" />
                                New built-up area
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-sm bg-emerald-400" />
                                Vegetation loss
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-sm bg-sky-500" />
                                Road expansion
                              </span>
                            </div>
                          </div>
                          <button className="w-full py-1.5 rounded bg-[#132035] hover:bg-[#182944] border border-[#203454] text-[11px] font-medium text-slate-200 flex items-center justify-center gap-1.5 transition cursor-pointer">
                            <span>View Full Map</span>
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <polyline points="15 3 21 3 21 9" />
                              <polyline points="9 21 3 21 3 15" />
                              <line x1="21" x2="14" y1="3" y2="10" />
                              <line x1="3" x2="10" y1="21" y2="14" />
                            </svg>
                          </button>
                        </div>

                        {/* Execution Trace Log Box */}
                        <div className="rounded-lg bg-[#0a1222] border border-[#18263e] p-3">
                          <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5 mb-2">
                            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>
                            Execution Trace
                          </span>
                          <div className="space-y-1.5 text-[10px]">
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="flex items-center gap-1.5">
                                <span className="text-emerald-400">✓</span> Query interpreted
                              </span>
                              <span className="text-slate-500 font-mono">→ Change-based VQA</span>
                            </div>
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="flex items-center gap-1.5">
                                <span className="text-emerald-400">✓</span> Input validated
                              </span>
                              <span className="text-slate-500 font-mono">→ 2 images, Optical + Optical</span>
                            </div>
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="flex items-center gap-1.5">
                                <span className="text-emerald-400">✓</span> Specialist selected
                              </span>
                              <span className="text-slate-500 font-mono">→ Change Analysis Model</span>
                            </div>
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="flex items-center gap-1.5">
                                <span className="text-emerald-400">✓</span> Analysis executed
                              </span>
                              <span className="text-slate-500 font-mono">→ Change regions identified</span>
                            </div>
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="flex items-center gap-1.5">
                                <span className="text-emerald-400">✓</span> Evidence generated
                              </span>
                              <span className="text-slate-500 font-mono">→ Visual + Spatial results</span>
                            </div>
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="flex items-center gap-1.5">
                                <span className="text-emerald-400">✓</span> Response synthesized
                              </span>
                              <span className="text-slate-500 font-mono">→ Natural language answer</span>
                            </div>
                          </div>
                        </div>

                        {/* Action Buttons Row */}
                        <div className="flex items-center gap-2 pt-1">
                          <button onClick={() => router.push("/reports")} className="flex-1 py-1.5 px-3 rounded-lg bg-[#111c2e] hover:bg-[#16253d] border border-[#1f304c] text-xs font-medium text-slate-200 flex items-center justify-center gap-1.5 transition cursor-pointer">
                            <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                              <polyline points="14 2 14 8 20 8" />
                            </svg>
                            <span>View Report</span>
                          </button>
                          <button className="flex-1 py-1.5 px-3 rounded-lg bg-[#111c2e] hover:bg-[#16253d] border border-[#1f304c] text-xs font-medium text-slate-200 flex items-center justify-center gap-1.5 transition cursor-pointer">
                            <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                              <polyline points="7 10 12 15 17 10" />
                              <line x1="12" x2="12" y1="15" y2="3" />
                            </svg>
                            <span>Download</span>
                          </button>
                          <button className="p-1.5 rounded-lg bg-[#111c2e] hover:bg-[#16253d] border border-[#1f304c] text-slate-400 transition">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <circle cx="12" cy="12" r="1" />
                              <circle cx="19" cy="12" r="1" />
                              <circle cx="5" cy="12" r="1" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {activeTab === "analysis" && (
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-[#0c1626] border border-[#182a44]">
                      <h3 className="text-xs font-semibold text-white mb-2">Change Classification Summary</h3>
                      <div className="space-y-2 text-[11px]">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Total Analyzed Area:</span>
                          <span className="text-slate-200 font-mono">22.6 km²</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Changed Area:</span>
                          <span className="text-cyan-400 font-mono">4.7 km² (20.8%)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">New Construction:</span>
                          <span className="text-red-400 font-mono">1.9 km²</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Vegetation Depletion:</span>
                          <span className="text-amber-400 font-mono">2.8 km²</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Cloud Obstruction:</span>
                          <span className="text-slate-400 font-mono">0.0% (Clear)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "trace" && (
                  <div className="space-y-2 text-[11px]">
                    {[
                      { name: "Query Normalization", ms: "32ms", status: "OK" },
                      { name: "Sentinel-2 Tile Retrieval", ms: "410ms", status: "OK" },
                      { name: "Radiometric Alignment", ms: "185ms", status: "OK" },
                      { name: "Change Transformer Forward Pass", ms: "1.42s", status: "OK" },
                      { name: "Polygon Vectorization", ms: "310ms", status: "OK" },
                      { name: "Response Generation (Gemini 1.5)", ms: "450ms", status: "OK" },
                    ].map((step, idx) => (
                      <div key={idx} className="p-2 rounded bg-[#0b1626] border border-[#15253b] flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          <span className="text-slate-300">{step.name}</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">{step.ms}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Bottom Follow-up Input Box */}
              <div className="p-3 border-t border-[#152136] bg-[#090f1d] shrink-0">
                <div className="relative bg-[#0d1627] rounded-xl border border-[#1c2c47] focus-within:border-cyan-500/70 p-2.5 shadow-inner">
                  <div className="flex items-center gap-2">
                    <button onClick={() => fileRef.current?.click()} className="text-slate-400 hover:text-slate-200">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                      </svg>
                    </button>
                    <input
                      value={followUp}
                      onChange={(e) => setFollowUp(e.target.value)}
                      className="w-full bg-transparent border-none p-0 text-xs text-slate-200 placeholder-slate-500 focus:ring-0 focus:outline-none"
                      placeholder="Ask a follow-up question..."
                      type="text"
                    />
                  </div>
                  {/* Bottom Toolbar Inside Input */}
                  <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-[#162339]">
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => fileRef.current?.click()} className="px-2 py-1 rounded bg-[#121c2f] hover:bg-[#182741] text-[10px] text-slate-300 flex items-center gap-1 border border-[#1d2d49]">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <rect height="18" rx="2" width="18" x="3" y="3" />
                          <circle cx="8.5" cy="8.5" r="1.5" />
                          <polyline points="21 15 16 10 5 21" />
                        </svg>
                        <span>Image</span>
                      </button>
                      <button className="px-2 py-1 rounded bg-[#121c2f] hover:bg-[#182741] text-[10px] text-slate-300 flex items-center gap-1 border border-[#1d2d49]">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <rect height="18" rx="2" width="20" x="2" y="3" />
                          <line x1="12" x2="12" y1="3" y2="21" />
                        </svg>
                        <span>Compare</span>
                      </button>
                      <button className="px-2 py-1 rounded bg-[#121c2f] hover:bg-[#182741] text-[10px] text-slate-300 flex items-center gap-1 border border-[#1d2d49]">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10" />
                        </svg>
                        <span>Region</span>
                      </button>
                      <button className="px-2 py-1 rounded bg-[#121c2f] hover:bg-[#182741] text-[10px] text-slate-300 flex items-center gap-1 border border-[#1d2d49]">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="3" />
                          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                        </svg>
                        <span>Parameters</span>
                      </button>
                    </div>
                    {/* Send Button */}
                    <button
                      onClick={() => setFollowUp("")}
                      className="w-7 h-7 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 flex items-center justify-center font-bold shadow-md shadow-cyan-500/25 transition cursor-pointer"
                    >
                      <svg className="w-3.5 h-3.5 rotate-45 -mr-0.5 mb-0.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </aside>
          </>
        )}
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="h-screen w-full bg-[#050a12]" />}>
      <AnalysisContent />
    </Suspense>
  );
}
