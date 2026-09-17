"use client";

import { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

export default function DocumentationPage() {
  const [activeTab, setActiveTab] = useState("Getting Started");
  const [searchDoc, setSearchDoc] = useState("");
  const [tocOpen, setTocOpen] = useState(true);

  const tabs = ["Getting Started", "Guides", "API Reference", "Tutorials", "Examples", "Advanced"];

  return (
    <div className="bg-[#050B14] text-slate-200 font-sans antialiased min-h-screen flex flex-col selection:bg-cyan-500 selection:text-black">
      {/* Top Outer Wrapper */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar hideBrand={false} activeItem="documentation" className="sticky top-0 h-screen" />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#060b13] overflow-y-auto">
          {/* TopBar Header */}
          <TopBar
            showBrand={false}
            searchPlaceholder="Search documentation, endpoints, guides, or keywords..."
            onSearch={(q) => setSearchDoc(q)}
          />

          {/* Scrollable Content Container */}
          <div className="flex-1 px-6 py-5">
            <div className="grid grid-cols-12 gap-5 max-w-[1440px] mx-auto">
              {/* Left / Center Column */}
              <main className="col-span-12 xl:col-span-9 space-y-5">
                {/* Hero Section */}
                <section
                  className="relative rounded-2xl border border-[#142b47] bg-gradient-to-r from-[#071324] via-[#091a32] to-[#07152b] overflow-hidden p-6 lg:p-8 shadow-xl"
                  data-purpose="documentation-hero"
                >
                  {/* Satellite Orbit & Glow Background Art */}
                  <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    <div className="absolute -right-24 -bottom-48 w-[460px] h-[460px] rounded-full border border-cyan-400/30 bg-gradient-to-t from-cyan-600/20 via-blue-700/10 to-transparent blur-sm" />
                    <div className="absolute -right-20 -bottom-44 w-[450px] h-[450px] rounded-full bg-[#061830] opacity-90" />
                    <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-cyan-500/20 via-sky-600/5 to-transparent" />

                    {/* Satellite Graphic SVG */}
                    <svg className="absolute right-12 top-6 w-72 h-72 text-cyan-400/90 drop-shadow-[0_0_20px_rgba(0,210,255,0.4)] hidden lg:block" fill="none" viewBox="0 0 200 200">
                      <path d="M-20 180 C 60 100, 150 50, 220 10" stroke="rgba(0, 229, 255, 0.25)" strokeDasharray="3 3" strokeWidth="1.2" />
                      <g transform="rotate(35 90 90)">
                        <rect fill="#0c2544" height="22" rx="2" stroke="#00e5ff" strokeWidth="1" width="38" x="25" y="80" />
                        <line stroke="#00e5ff" strokeWidth="0.7" x1="37" x2="37" y1="80" y2="102" />
                        <line stroke="#00e5ff" strokeWidth="0.7" x1="50" x2="50" y1="80" y2="102" />
                        <line stroke="#00e5ff" strokeWidth="0.7" x1="25" x2="63" y1="91" y2="91" />
                        <line stroke="#94a3b8" strokeWidth="2" x1="63" x2="74" y1="91" y2="91" />
                        <rect fill="#14345c" height="18" rx="2" stroke="#38bdf8" strokeWidth="1.2" width="22" x="74" y="82" />
                        <circle cx="85" cy="91" fill="#00e5ff" r="3.5" />
                        <path d="M 85 75 A 8 8 0 0 1 95 82" fill="none" stroke="#38bdf8" strokeWidth="1.5" />
                        <line stroke="#00e5ff" strokeWidth="1.5" x1="90" x2="96" y1="78" y2="72" />
                        <line stroke="#94a3b8" strokeWidth="2" x1="96" x2="107" y1="91" y2="91" />
                        <rect fill="#0c2544" height="22" rx="2" stroke="#00e5ff" strokeWidth="1" width="38" x="107" y="80" />
                        <line stroke="#00e5ff" strokeWidth="0.7" x1="120" x2="120" y1="80" y2="102" />
                        <line stroke="#00e5ff" strokeWidth="0.7" x1="132" x2="132" y1="80" y2="102" />
                        <line stroke="#00e5ff" strokeWidth="0.7" x1="107" x2="145" y1="91" y2="91" />
                      </g>
                    </svg>
                  </div>

                  {/* Hero Content Body */}
                  <div className="relative z-10 max-w-xl">
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 text-[11px] font-semibold tracking-wider uppercase mb-3 shadow-[0_0_10px_rgba(0,229,255,0.15)]">
                      <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <span>Documentation</span>
                    </div>
                    <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                      SatQuery AI Documentation
                    </h1>
                    <p className="text-xs lg:text-sm text-slate-300 mt-2 leading-relaxed">
                      Everything you need to build, analyze and get insights from satellite data. Explore guides, API references, tutorials and more.
                    </p>

                    {/* Search inside Hero */}
                    <div className="mt-5 max-w-md relative">
                      <svg className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" x2="16.65" y1="21" y2="16.65" />
                      </svg>
                      <input
                        value={searchDoc}
                        onChange={(e) => setSearchDoc(e.target.value)}
                        className="w-full bg-[#081528]/90 border border-[#1c385f] rounded-lg pl-9 pr-12 py-2 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 shadow-inner"
                        placeholder="Search documentation..."
                        type="text"
                      />
                      <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-[#10223b] border border-[#203e68] text-[10px] font-mono text-slate-400">
                        <span>⌘</span><span>K</span>
                      </div>
                    </div>
                  </div>

                  {/* Hero 4 Quick Action Cards */}
                  <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-[#132d4e]/80">
                    <button
                      onClick={() => setActiveTab("Getting Started")}
                      className="p-3 rounded-xl bg-[#09182d]/80 border border-[#163359] hover:border-cyan-500/50 hover:bg-[#0d213d] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 group-hover:text-cyan-300 shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">Quick Start</h3>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">Get up and running in minutes</p>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("API Reference")}
                      className="p-3 rounded-xl bg-[#09182d]/80 border border-[#163359] hover:border-cyan-500/50 hover:bg-[#0d213d] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 group-hover:text-cyan-300 shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">API Reference</h3>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">Explore all endpoints</p>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("Tutorials")}
                      className="p-3 rounded-xl bg-[#09182d]/80 border border-[#163359] hover:border-cyan-500/50 hover:bg-[#0d213d] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 group-hover:text-cyan-300 shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10" /><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">Tutorials</h3>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">Step-by-step guides</p>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("Examples")}
                      className="p-3 rounded-xl bg-[#09182d]/80 border border-[#163359] hover:border-cyan-500/50 hover:bg-[#0d213d] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 group-hover:text-cyan-300 shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><path d="M9 15l2 2 4-4" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">Examples</h3>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">Real use cases &amp; workflows</p>
                      </div>
                    </button>
                  </div>
                </section>

                {/* Navigation Tabs */}
                <div className="flex items-center gap-6 border-b border-[#142844] text-xs font-medium px-2">
                  {tabs.map((tab) => {
                    const active = activeTab === tab;
                    return (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`pb-2.5 transition-colors cursor-pointer ${
                          active
                            ? "text-cyan-400 border-b-2 border-cyan-400 font-semibold tracking-wide"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {tab}
                      </button>
                    );
                  })}
                </div>

                {/* Section 1 - Getting Started */}
                <section className="space-y-3 pt-1" data-purpose="getting-started-section">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-white tracking-tight">1. Getting Started</h2>
                      <p className="text-[11px] text-slate-400">Learn the basics and get your first analysis running with SatQuery AI.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
                    {[
                      {
                        title: "1.1 Introduction",
                        desc: "Overview of SatQuery AI, key features, and use cases across agriculture, urban, water and more.",
                        time: "5 min read",
                        icon: "book",
                      },
                      {
                        title: "1.2 Account Setup",
                        desc: "Create your account, verify credentials, and configure your multi-sensor workspace.",
                        time: "7 min read",
                        icon: "user",
                      },
                      {
                        title: "1.3 Uploading Data",
                        desc: "Learn how to upload satellite imagery, shapefiles, or use public catalog datasets.",
                        time: "8 min read",
                        icon: "upload",
                      },
                      {
                        title: "1.4 First Analysis",
                        desc: "Run your first change detection or land cover analysis using natural language prompts.",
                        time: "10 min read",
                        icon: "chart",
                      },
                    ].map((item) => (
                      <div
                        key={item.title}
                        className="p-4 rounded-xl bg-[#081426] border border-[#142c4c] hover:border-cyan-500/40 transition flex flex-col justify-between group"
                      >
                        <div>
                          <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-[#0d213a] border border-[#1b3b64] text-cyan-400 shrink-0">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            </div>
                            <div>
                              <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">{item.title}</h3>
                              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{item.desc}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center justify-between mt-4 pt-2 border-t border-[#10233c]">
                          <span className="flex items-center gap-1.5 text-[10px] text-slate-400 font-medium">
                            <svg className="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
                            </svg>
                            {item.time}
                          </span>
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-400 group-hover:text-cyan-300 transition">
                            <span>Read</span>
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Section 2 - Core Guides */}
                <section className="space-y-3 pt-4" data-purpose="core-guides-section">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-white tracking-tight">2. Core Guides</h2>
                      <p className="text-[11px] text-slate-400">Deep-dive into specialized vision and multi-sensor capabilities.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 pt-1">
                    {[
                      {
                        title: "2.1 Single Image Analysis",
                        desc: "Visual question answering, automatic scene captioning, and bounding-box grounding.",
                        tag: "VQA",
                      },
                      {
                        title: "2.2 Change Detection",
                        desc: "Bi-temporal alignment, pseudo-color change masking, and quantitative difference analysis.",
                        tag: "ChangeFormer",
                      },
                      {
                        title: "2.3 Optical + SAR Fusion",
                        desc: "Registering SAR radar backscatter with multi-band optical sensors to penetrate cloud cover.",
                        tag: "Multi-Modal",
                      },
                    ].map((guide) => (
                      <div
                        key={guide.title}
                        className="p-4 rounded-xl bg-[#081426] border border-[#142c4c] hover:border-cyan-500/40 transition flex flex-col justify-between group"
                      >
                        <div>
                          <span className="px-2 py-0.5 rounded text-[9px] font-semibold bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 mb-2 inline-block">
                            {guide.tag}
                          </span>
                          <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">{guide.title}</h3>
                          <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{guide.desc}</p>
                        </div>
                        <div className="flex items-center justify-between mt-4 pt-2 border-t border-[#10233c]">
                          <span className="text-[10px] text-slate-500">Guide</span>
                          <span className="text-[11px] font-semibold text-cyan-400 group-hover:text-cyan-300">View Guide →</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Section 3 - API Reference Preview */}
                <section className="space-y-3 pt-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-white tracking-tight">3. API Reference</h2>
                      <p className="text-[11px] text-slate-400">Programmatic endpoints for automated remote sensing pipelines.</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {[
                      { method: "POST", path: "/api/v1/analyze", desc: "Submit an image query and receive natural language reasoning and grounded masks." },
                      { method: "POST", path: "/api/v1/fusion", desc: "Submit aligned optical and SAR GeoTIFFs to run cross-modal information fusion." },
                      { method: "GET", path: "/api/v1/jobs/{jobId}", desc: "Poll execution status and retrieve generated metrics and GeoJSON change masks." },
                    ].map((api) => (
                      <div key={api.path} className="p-3 rounded-xl bg-[#081426] border border-[#142c4c] flex items-center justify-between">
                        <div className="flex items-center gap-3 font-mono text-xs">
                          <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 font-bold border border-cyan-500/20 text-[10px]">
                            {api.method}
                          </span>
                          <span className="text-white font-medium">{api.path}</span>
                          <span className="text-slate-400 font-sans text-[11px] hidden sm:inline">{api.desc}</span>
                        </div>
                        <span className="text-cyan-400 text-xs font-sans hover:underline cursor-pointer">Specs →</span>
                      </div>
                    ))}
                  </div>
                </section>
              </main>

              {/* Right Column Info Panel */}
              <aside className="col-span-12 xl:col-span-3 space-y-5">
                {/* Card 1: Quick Links */}
                <div className="rounded-xl border border-[#132a47] bg-[#07111f] p-4 shadow-md">
                  <div className="flex items-center gap-2 mb-3">
                    <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    <h3 className="text-xs font-bold text-white tracking-wide">Popular Resources</h3>
                  </div>
                  <div className="space-y-1.5">
                    {[
                      { title: "Change Detection Guide", desc: "Bi-temporal analysis workflow" },
                      { title: "Optical + SAR Fusion", desc: "Multi-sensor registration" },
                      { title: "Model Architecture", desc: "AI models and capabilities" },
                      { title: "Sample Datasets", desc: "Public datasets for practice" },
                      { title: "Best Practices", desc: "Tips for better inference" },
                    ].map((item) => (
                      <div
                        key={item.title}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-[#0c1e34] transition group cursor-pointer"
                      >
                        <div>
                          <div className="text-[11px] font-semibold text-slate-200 group-hover:text-cyan-300">{item.title}</div>
                          <div className="text-[9px] text-slate-400">{item.desc}</div>
                        </div>
                        <svg className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Card 2: Table of Contents */}
                <div className="rounded-xl border border-[#132a47] bg-[#07111f] p-4 shadow-md">
                  <div
                    onClick={() => setTocOpen(!tocOpen)}
                    className="flex items-center justify-between mb-3 cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <line x1="8" x2="21" y1="6" y2="6" /><line x1="8" x2="21" y1="12" y2="12" /><line x1="8" x2="21" y1="18" y2="18" />
                        <line x1="3" x2="3.01" y1="6" y2="6" /><line x1="3" x2="3.01" y1="12" y2="12" /><line x1="3" x2="3.01" y1="18" y2="18" />
                      </svg>
                      <h3 className="text-xs font-bold text-white tracking-wide">Table of Contents</h3>
                    </div>
                    <svg className={`w-3.5 h-3.5 text-slate-400 transform transition-transform ${tocOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                    </svg>
                  </div>
                  {tocOpen && (
                    <div className="space-y-1 text-xs">
                      <div className="flex items-center justify-between py-1 text-slate-200 font-medium">
                        <span className="flex items-center gap-1.5 text-[11px]">
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> 1. Getting Started
                        </span>
                      </div>
                      <div className="pl-4 ml-1.5 border-l border-[#193252] space-y-1 py-1">
                        <span className="block text-[10px] text-cyan-300 font-medium cursor-pointer">1.1 Introduction</span>
                        <span className="block text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer">1.2 Account Setup</span>
                        <span className="block text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer">1.3 Uploading Data</span>
                        <span className="block text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer">1.4 First Analysis</span>
                      </div>
                      {["2. Core Guides", "3. API Reference", "4. Tutorials", "5. Examples", "6. Advanced"].map((sect) => (
                        <div key={sect} className="flex items-center justify-between py-1.5 text-slate-300 text-[11px] hover:text-cyan-300 cursor-pointer">
                          <span>{sect}</span>
                          <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <polyline points="9 18 15 12 9 6" />
                          </svg>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card 3: System Status */}
                <div className="rounded-xl border border-[#132a47] bg-[#07111f] p-4 shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" strokeWidth="2" />
                      </svg>
                      <h3 className="text-xs font-bold text-white tracking-wide">System Status</h3>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-[9px] font-semibold text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> All Systems Operational
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-[#0b1b30] border border-[#142c4b] rounded-lg p-2 text-center">
                      <div className="text-[9px] text-slate-400 font-medium">API Uptime</div>
                      <div className="text-xs font-bold text-cyan-300 mt-1">99.9%</div>
                    </div>
                    <div className="bg-[#0b1b30] border border-[#142c4b] rounded-lg p-2 text-center">
                      <div className="text-[9px] text-slate-400 font-medium">Queue</div>
                      <div className="text-xs font-bold text-cyan-300 mt-1">2 jobs</div>
                    </div>
                    <div className="bg-[#0b1b30] border border-[#142c4b] rounded-lg p-2 text-center">
                      <div className="text-[9px] text-slate-400 font-medium">Active Users</div>
                      <div className="text-xs font-bold text-cyan-300 mt-1">12.4K</div>
                    </div>
                  </div>
                  <div className="mt-3 pt-2 border-t border-[#12253e] flex items-center justify-between text-[9px] text-slate-400">
                    <span>Last updated: Oct 12, 2025</span>
                    <span>11:42 AM</span>
                  </div>
                </div>
              </aside>
            </div>
          </div>

          {/* Page Footer */}
          <footer className="border-t border-[#12233b] bg-[#060e1a] px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400 shrink-0">
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="font-semibold text-slate-200">SatQuery <span className="text-cyan-400">AI</span></span>
              <span className="text-slate-600">|</span>
              <span>© 2025. All rights reserved.</span>
            </div>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-4 text-[11px]">
                <Link href="#" className="hover:text-cyan-300 transition-colors">Privacy</Link>
                <Link href="#" className="hover:text-cyan-300 transition-colors">Terms</Link>
                <Link href="#" className="hover:text-cyan-300 transition-colors">Contact</Link>
              </div>
              <div className="flex items-center gap-3 pl-3 border-l border-[#162c47]">
                <span className="text-slate-400 hover:text-white cursor-pointer transition-colors text-xs font-bold">GH</span>
                <span className="text-slate-400 hover:text-white cursor-pointer transition-colors text-xs font-bold">IN</span>
                <span className="text-slate-400 hover:text-white cursor-pointer transition-colors text-xs font-bold">X</span>
                <span className="text-slate-400 hover:text-white cursor-pointer transition-colors text-xs font-bold">YT</span>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
