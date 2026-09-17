"use client";

import Link from "next/link";

const QUICK_START = [
  { title: "1.1 Introduction", desc: "Overview of SatQuery AI, key features, and use cases across agriculture, urban, water and more.", time: "5 min read" },
  { title: "1.2 Account Setup", desc: "Create your account, verify email, and configure your workspace.", time: "7 min read" },
  { title: "1.3 Uploading Data", desc: "Learn how to upload satellite imagery, shapefiles, or use public datasets.", time: "8 min read" },
  { title: "1.4 First Analysis", desc: "Run your first change detection or land cover analysis using the web interface.", time: "10 min read" },
];

const CORE_GUIDES = [
  { title: "Satellite Imagery Basics", desc: "Understand bands, resolutions, and formats.", time: "12 min read" },
  { title: "Change Detection Guide", desc: "Detect changes over time with multi-temporal analysis.", time: "15 min read" },
  { title: "Land Cover Classification", desc: "Classify land use with AI models and spectral indices.", time: "14 min read" },
  { title: "SAR & Optical Fusion", desc: "Combine SAR and optical data for better results.", time: "11 min read" },
];

const QUICK_LINKS = [
  { label: "API Documentation", desc: "Endpoints, parameters, responses" },
  { label: "Postman Collection", desc: "Test APIs directly" },
  { label: "Model Documentation", desc: "AI models and capabilities" },
  { label: "Sample Datasets", desc: "Public datasets for practice" },
  { label: "Best Practices", desc: "Tips for better results" },
];

export default function DocumentationPage() {
  return (
    <div className="flex-1 overflow-y-auto px-6 py-5">
      <div className="grid grid-cols-12 gap-5 max-w-[1440px] mx-auto">
        {/* Main content */}
        <main className="col-span-12 xl:col-span-9 space-y-5">
          {/* Hero */}
          <section className="relative rounded-2xl border border-[#142b47] bg-gradient-to-r from-[#071324] via-[#091a32] to-[#07152b] overflow-hidden p-6 lg:p-8 shadow-xl">
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              <div className="absolute -right-24 -bottom-48 w-[460px] h-[460px] rounded-full border border-cyan-400/30 bg-gradient-to-t from-cyan-600/20 via-blue-700/10 to-transparent blur-sm" />
              <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-cyan-500/20 via-sky-600/5 to-transparent" />
            </div>
            <div className="relative z-10 max-w-xl">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 text-[11px] font-semibold tracking-wider uppercase mb-3 shadow-[0_0_10px_rgba(0,229,255,0.15)]">
                <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Documentation
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">SatQuery AI Documentation</h1>
              <p className="text-xs lg:text-sm text-slate-300 mt-2 leading-relaxed">Everything you need to build, analyze and get insights from satellite data.</p>
            </div>

            {/* Quick cards */}
            <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-[#132d4e]/80">
              {[
                { icon: "🚀", title: "Quick Start", desc: "Get up and running in minutes" },
                { icon: "💻", title: "API Reference", desc: "Explore all endpoints" },
                { icon: "▶️", title: "Tutorials", desc: "Step-by-step guides" },
                { icon: "✅", title: "Examples", desc: "Real use cases & workflows" },
              ].map((item) => (
                <Link key={item.title} href="#" className="p-3 rounded-xl bg-[#09182d]/80 border border-[#163359] hover:border-cyan-500/50 hover:bg-[#0d213d] transition flex items-start gap-2.5 group">
                  <div className="p-1.5 rounded-lg bg-cyan-950/70 border border-cyan-500/30 text-cyan-400 shrink-0 text-sm">{item.icon}</div>
                  <div>
                    <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">{item.title}</h3>
                    <p className="text-[10px] text-slate-400 mt-0.5">{item.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* Getting Started */}
          <section className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">🚀</div>
              <div>
                <h2 className="text-sm font-bold text-white tracking-tight">1. Getting Started</h2>
                <p className="text-[11px] text-slate-400">Learn the basics and get your first analysis running.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {QUICK_START.map((item) => (
                <div key={item.title} className="p-4 rounded-xl bg-[#081426] border border-[#142c4c] hover:border-cyan-500/40 transition group">
                  <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">{item.title}</h3>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{item.desc}</p>
                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#10233c]">
                    <span className="text-[10px] text-slate-400">{item.time}</span>
                    <span className="text-[11px] font-semibold text-cyan-400">Read →</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Core Guides */}
          <section className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400">🧭</div>
              <div>
                <h2 className="text-sm font-bold text-white tracking-tight">2. Core Guides</h2>
                <p className="text-[11px] text-slate-400">In-depth guides to help you master SatQuery AI.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {CORE_GUIDES.map((item) => (
                <div key={item.title} className="p-3.5 rounded-xl bg-[#081426] border border-[#142c4c] hover:border-cyan-500/40 transition flex flex-col justify-between group">
                  <div>
                    <h3 className="text-xs font-semibold text-white group-hover:text-cyan-300">{item.title}</h3>
                    <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">{item.desc}</p>
                  </div>
                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#10233c] text-[10px] text-slate-400">
                    <span>{item.time}</span>
                    <span className="text-cyan-400">→</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>

        {/* Right sidebar */}
        <aside className="col-span-12 xl:col-span-3 space-y-4">
          {/* Quick Links */}
          <div className="rounded-xl border border-[#132a47] bg-[#07111f] p-4 shadow-md">
            <h3 className="text-xs font-bold text-white tracking-wide mb-3">Quick Links</h3>
            <div className="space-y-1 text-xs">
              {QUICK_LINKS.map((link) => (
                <Link key={link.label} href="#" className="flex items-center justify-between p-2 rounded-lg hover:bg-[#0c1e34] transition group">
                  <div>
                    <div className="text-[11px] font-semibold text-slate-200 group-hover:text-cyan-300">{link.label}</div>
                    <div className="text-[9px] text-slate-400">{link.desc}</div>
                  </div>
                  <svg className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </Link>
              ))}
            </div>
          </div>

          {/* System Status */}
          <div className="rounded-xl border border-[#132a47] bg-[#07111f] p-4 shadow-md">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-white tracking-wide">System Status</h3>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-[9px] font-semibold text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                All Systems Operational
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
                <div className="text-[9px] text-slate-400 font-medium">Users</div>
                <div className="text-xs font-bold text-cyan-300 mt-1">12.4K</div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
