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
    <div className="bg-[var(--canvas)] text-[var(--text)] font-sans antialiased h-screen overflow-hidden flex flex-col selection:bg-[var(--cyan)]/30 selection:text-[var(--canvas)]">
      {/* Full-width TopBar */}
      <TopBar
        showBrand={true}
        searchPlaceholder="Search documentation, endpoints, guides, or keywords..."
        onSearch={(q) => setSearchDoc(q)}
      />

      {/* Main Body Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar hideBrand={true} activeItem="documentation" className="h-full" />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto" data-purpose="documentation-content">
          {/* Scrollable Content Container */}
          <div className="flex-1 px-6 py-5">
            <div className="grid grid-cols-12 gap-5 max-w-[1440px] mx-auto">
              {/* Left / Center Column */}
              <main className="col-span-12 xl:col-span-9 space-y-5">
                {/* Hero Section */}
                <section
                  className="relative rounded-2xl border border-[var(--border)] bg-gradient-to-r from-[var(--surface-2)] via-[var(--surface-3)] to-[var(--surface)] overflow-hidden p-6 lg:p-8 shadow-xl"
                  data-purpose="documentation-hero"
                >
                  {/* Satellite Orbit & Glow Background Art */}
                  <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    <div className="absolute -right-24 -bottom-48 w-[460px] h-[460px] rounded-full border border-[var(--cyan)]/30 bg-gradient-to-t from-cyan-600/20 via-blue-700/10 to-transparent blur-sm" />
                    <div className="absolute -right-20 -bottom-44 w-[450px] h-[450px] rounded-full bg-[var(--surface-3)] opacity-90" />
                    <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-cyan-500/20 via-sky-600/5 to-transparent" />

                    {/* Satellite Graphic SVG */}
                    <svg className="absolute right-12 top-6 w-72 h-72 text-[var(--cyan)]/90 drop-shadow-[0_0_20px_rgba(0,210,255,0.4)] hidden lg:block" fill="none" viewBox="0 0 200 200">
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
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/60 border border-[var(--cyan)]/40 text-[var(--cyan)] text-[11px] font-semibold tracking-wider uppercase mb-3 shadow-[0_0_10px_rgba(0,229,255,0.15)]">
                      <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <span>Documentation</span>
                    </div>
                    <h1 className="text-2xl lg:text-3xl font-bold text-[var(--heading)] tracking-tight leading-snug">
                      SatQuery AI Documentation
                    </h1>
                    <p className="text-xs lg:text-sm text-[var(--text-2)] mt-2 leading-relaxed">
                      Everything you need to build, analyze and get insights from satellite data. Explore guides, API references, tutorials and more.
                    </p>

                    {/* Search inside Hero */}
                    <div className="mt-5 max-w-md relative">
                      <svg className="w-4 h-4 text-[var(--text-3)] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" x2="16.65" y1="21" y2="16.65" />
                      </svg>
                      <input
                        value={searchDoc}
                        onChange={(e) => setSearchDoc(e.target.value)}
                        className="w-full bg-[var(--surface-2)]/90 border border-[var(--border)] rounded-lg pl-9 pr-12 py-2 text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)] focus:ring-1 focus:ring-cyan-400 shadow-inner"
                        placeholder="Search documentation..."
                        type="text"
                      />
                      <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-[var(--surface-3)] border border-[var(--border-strong)] text-[10px] font-mono text-[var(--text-3)]">
                        <span>⌘</span><span>K</span>
                      </div>
                    </div>
                  </div>

                  {/* Hero 4 Quick Action Cards */}
                  <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-[var(--border)]/80">
                    <button
                      onClick={() => setActiveTab("Getting Started")}
                      className="p-3 rounded-xl bg-[var(--surface-2)]/80 border border-[var(--border)] hover:border-[var(--cyan)]/50 hover:bg-[var(--surface-hover)] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-[var(--cyan)]/30 text-[var(--cyan)] group-hover:text-[var(--cyan)] shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)]">Quick Start</h3>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5 leading-snug">Get up and running in minutes</p>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("API Reference")}
                      className="p-3 rounded-xl bg-[var(--surface-2)]/80 border border-[var(--border)] hover:border-[var(--cyan)]/50 hover:bg-[var(--surface-hover)] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-[var(--cyan)]/30 text-[var(--cyan)] group-hover:text-[var(--cyan)] shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)]">API Reference</h3>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5 leading-snug">Explore all endpoints</p>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("Tutorials")}
                      className="p-3 rounded-xl bg-[var(--surface-2)]/80 border border-[var(--border)] hover:border-[var(--cyan)]/50 hover:bg-[var(--surface-hover)] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-[var(--cyan)]/30 text-[var(--cyan)] group-hover:text-[var(--cyan)] shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10" /><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)]">Tutorials</h3>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5 leading-snug">Step-by-step guides</p>
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("Examples")}
                      className="p-3 rounded-xl bg-[var(--surface-2)]/80 border border-[var(--border)] hover:border-[var(--cyan)]/50 hover:bg-[var(--surface-hover)] transition flex items-start gap-2.5 group text-left cursor-pointer"
                    >
                      <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-[var(--cyan)]/30 text-[var(--cyan)] group-hover:text-[var(--cyan)] shrink-0">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /><path d="M9 15l2 2 4-4" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)]">Examples</h3>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5 leading-snug">Real use cases &amp; workflows</p>
                      </div>
                    </button>
                  </div>
                </section>

                {/* Navigation Tabs */}
                <div className="flex items-center gap-6 border-b border-[var(--border)] text-xs font-medium px-2">
                  {tabs.map((tab) => {
                    const active = activeTab === tab;
                    return (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`pb-2.5 transition-colors cursor-pointer ${
                          active
                            ? "text-[var(--cyan)] border-b-2 border-[var(--cyan)] font-semibold tracking-wide"
                            : "text-[var(--text-3)] hover:text-[var(--text)]"
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
                    <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-[var(--cyan)]/30 text-[var(--cyan)]">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-[var(--heading)] tracking-tight">1. Getting Started</h2>
                      <p className="text-[11px] text-[var(--text-3)]">Learn the basics and get your first analysis running with SatQuery AI.</p>
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
                        className="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--cyan)]/40 transition flex flex-col justify-between group"
                      >
                        <div>
                          <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-[var(--surface-3)] border border-[var(--border)] text-[var(--cyan)] shrink-0">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            </div>
                            <div>
                              <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)]">{item.title}</h3>
                              <p className="text-[11px] text-[var(--text-3)] mt-1 leading-relaxed">{item.desc}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center justify-between mt-4 pt-2 border-t border-[var(--border)]">
                          <span className="flex items-center gap-1.5 text-[10px] text-[var(--text-3)] font-medium">
                            <svg className="w-3 h-3 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
                            </svg>
                            {item.time}
                          </span>
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--cyan)] group-hover:text-[var(--cyan)] transition">
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
                    <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-[var(--cyan)]/30 text-[var(--cyan)]">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-[var(--heading)] tracking-tight">2. Core Guides</h2>
                      <p className="text-[11px] text-[var(--text-3)]">Deep-dive into specialized vision and multi-sensor capabilities.</p>
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
                        className="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--cyan)]/40 transition flex flex-col justify-between group"
                      >
                        <div>
                          <span className="px-2 py-0.5 rounded text-[9px] font-semibold bg-cyan-950/60 text-[var(--cyan)] border border-[var(--cyan)]/30 mb-2 inline-block">
                            {guide.tag}
                          </span>
                          <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)]">{guide.title}</h3>
                          <p className="text-[11px] text-[var(--text-3)] mt-1 leading-relaxed">{guide.desc}</p>
                        </div>
                        <div className="flex items-center justify-between mt-4 pt-2 border-t border-[var(--border)]">
                          <span className="text-[10px] text-[var(--text-3)]">Guide</span>
                          <span className="text-[11px] font-semibold text-[var(--cyan)] group-hover:text-[var(--cyan)]">View Guide →</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Section 3 - API Reference Preview */}
                <section className="space-y-3 pt-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-[var(--cyan)]/30 text-[var(--cyan)]">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-[var(--heading)] tracking-tight">3. API Reference</h2>
                      <p className="text-[11px] text-[var(--text-3)]">Programmatic endpoints for automated remote sensing pipelines.</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {[
                      { method: "POST", path: "/api/v1/analyze", desc: "Submit an image query and receive natural language reasoning and grounded masks." },
                      { method: "POST", path: "/api/v1/fusion", desc: "Submit aligned optical and SAR GeoTIFFs to run cross-modal information fusion." },
                      { method: "GET", path: "/api/v1/jobs/{jobId}", desc: "Poll execution status and retrieve generated metrics and GeoJSON change masks." },
                    ].map((api) => (
                      <div key={api.path} className="p-3 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-between">
                        <div className="flex items-center gap-3 font-mono text-xs">
                          <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-[var(--cyan)] font-bold border border-[var(--cyan)]/20 text-[10px]">
                            {api.method}
                          </span>
                          <span className="text-[var(--heading)] font-medium">{api.path}</span>
                          <span className="text-[var(--text-3)] font-sans text-[11px] hidden sm:inline">{api.desc}</span>
                        </div>
                        <span className="text-[var(--cyan)] text-xs font-sans hover:underline cursor-pointer">Specs →</span>
                      </div>
                    ))}
                  </div>
                </section>
              </main>

              {/* Right Column Info Panel */}
              <aside className="col-span-12 xl:col-span-3 space-y-5">
                {/* Card 1: Quick Links */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div className="flex items-center gap-2 mb-3">
                    <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    <h3 className="text-xs font-bold text-[var(--heading)] tracking-wide">Popular Resources</h3>
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
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-[var(--surface-hover)] transition group cursor-pointer"
                      >
                        <div>
                          <div className="text-[11px] font-semibold text-[var(--text)] group-hover:text-[var(--cyan)]">{item.title}</div>
                          <div className="text-[9px] text-[var(--text-3)]">{item.desc}</div>
                        </div>
                        <svg className="w-3.5 h-3.5 text-[var(--text-3)] group-hover:text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Card 2: Table of Contents */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div
                    onClick={() => setTocOpen(!tocOpen)}
                    className="flex items-center justify-between mb-3 cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <line x1="8" x2="21" y1="6" y2="6" /><line x1="8" x2="21" y1="12" y2="12" /><line x1="8" x2="21" y1="18" y2="18" />
                        <line x1="3" x2="3.01" y1="6" y2="6" /><line x1="3" x2="3.01" y1="12" y2="12" /><line x1="3" x2="3.01" y1="18" y2="18" />
                      </svg>
                      <h3 className="text-xs font-bold text-[var(--heading)] tracking-wide">Table of Contents</h3>
                    </div>
                    <svg className={`w-3.5 h-3.5 text-[var(--text-3)] transform transition-transform ${tocOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                    </svg>
                  </div>
                  {tocOpen && (
                    <div className="space-y-1 text-xs">
                      <div className="flex items-center justify-between py-1 text-[var(--text)] font-medium">
                        <span className="flex items-center gap-1.5 text-[11px]">
                          <span className="w-1.5 h-1.5 rounded-full bg-[var(--cyan)]" /> 1. Getting Started
                        </span>
                      </div>
                      <div className="pl-4 ml-1.5 border-l border-[var(--border)] space-y-1 py-1">
                        <span className="block text-[10px] text-[var(--cyan)] font-medium cursor-pointer">1.1 Introduction</span>
                        <span className="block text-[10px] text-[var(--text-3)] hover:text-[var(--text)] cursor-pointer">1.2 Account Setup</span>
                        <span className="block text-[10px] text-[var(--text-3)] hover:text-[var(--text)] cursor-pointer">1.3 Uploading Data</span>
                        <span className="block text-[10px] text-[var(--text-3)] hover:text-[var(--text)] cursor-pointer">1.4 First Analysis</span>
                      </div>
                      {["2. Core Guides", "3. API Reference", "4. Tutorials", "5. Examples", "6. Advanced"].map((sect) => (
                        <div key={sect} className="flex items-center justify-between py-1.5 text-[var(--text-2)] text-[11px] hover:text-[var(--cyan)] cursor-pointer">
                          <span>{sect}</span>
                          <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <polyline points="9 18 15 12 9 6" />
                          </svg>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card 3: System Status */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" strokeWidth="2" />
                      </svg>
                      <h3 className="text-xs font-bold text-[var(--heading)] tracking-wide">System Status</h3>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--green-bg)]/60 border border-emerald-500/40 text-[9px] font-semibold text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> All Systems Operational
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-[var(--surface-3)] border border-[var(--border)] rounded-lg p-2 text-center">
                      <div className="text-[9px] text-[var(--text-3)] font-medium">API Uptime</div>
                      <div className="text-xs font-bold text-[var(--cyan)] mt-1">99.9%</div>
                    </div>
                    <div className="bg-[var(--surface-3)] border border-[var(--border)] rounded-lg p-2 text-center">
                      <div className="text-[9px] text-[var(--text-3)] font-medium">Queue</div>
                      <div className="text-xs font-bold text-[var(--cyan)] mt-1">2 jobs</div>
                    </div>
                    <div className="bg-[var(--surface-3)] border border-[var(--border)] rounded-lg p-2 text-center">
                      <div className="text-[9px] text-[var(--text-3)] font-medium">Active Users</div>
                      <div className="text-xs font-bold text-[var(--cyan)] mt-1">12.4K</div>
                    </div>
                  </div>
                  <div className="mt-3 pt-2 border-t border-[var(--border)] flex items-center justify-between text-[9px] text-[var(--text-3)]">
                    <span>Last updated: Oct 12, 2025</span>
                    <span>11:42 AM</span>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
