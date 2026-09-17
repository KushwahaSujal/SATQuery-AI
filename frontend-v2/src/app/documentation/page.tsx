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
    <div className="flex-1 overflow-y-auto px-6 py-5" style={{ background: "var(--canvas)" }}>
      <div className="grid grid-cols-12 gap-5 max-w-[1440px] mx-auto">
        {/* Main content */}
        <main className="col-span-12 xl:col-span-9 space-y-5">
          {/* Hero */}
          <section
            className="relative rounded-2xl overflow-hidden p-6 lg:p-8"
            style={{ border: "1px solid var(--border-strong)", background: "var(--surface-2)", boxShadow: "var(--shadow-lg)" }}
          >
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              <div className="absolute -right-24 -bottom-48 w-[460px] h-[460px] rounded-full" style={{ border: "1px solid var(--cyan-glow)", background: "radial-gradient(var(--cyan-glow), transparent 60%)" }} />
            </div>
            <div className="relative z-10 max-w-xl">
              <div
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wider uppercase mb-3"
                style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Documentation
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold tracking-tight leading-snug" style={{ color: "var(--heading)" }}>SatQuery AI Documentation</h1>
              <p className="text-xs lg:text-sm mt-2 leading-relaxed" style={{ color: "var(--text)" }}>Everything you need to build, analyze and get insights from satellite data.</p>
            </div>

            {/* Quick cards */}
            <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5" style={{ borderTop: "1px solid var(--border)" }}>
              {[
                { icon: "\ud83d\ude80", title: "Quick Start", desc: "Get up and running in minutes" },
                { icon: "\ud83d\udcbb", title: "API Reference", desc: "Explore all endpoints" },
                { icon: "\u25b6\ufe0f", title: "Tutorials", desc: "Step-by-step guides" },
                { icon: "\u2705", title: "Examples", desc: "Real use cases & workflows" },
              ].map((item) => (
                <Link
                  key={item.title}
                  href="#"
                  className="p-3 rounded-xl transition flex items-start gap-2.5 group"
                  style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
                >
                  <div
                    className="p-1.5 rounded-lg shrink-0 text-sm"
                    style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}
                  >{item.icon}</div>
                  <div>
                    <h3 className="text-xs font-semibold" style={{ color: "var(--heading)" }}>{item.title}</h3>
                    <p className="text-[10px] mt-0.5" style={{ color: "var(--text-2)" }}>{item.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* Getting Started */}
          <section className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg" style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}>\ud83d\ude80</div>
              <div>
                <h2 className="text-sm font-bold tracking-tight" style={{ color: "var(--heading)" }}>1. Getting Started</h2>
                <p className="text-[11px]" style={{ color: "var(--text-2)" }}>Learn the basics and get your first analysis running.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {QUICK_START.map((item) => (
                <div
                  key={item.title}
                  className="p-4 rounded-xl transition group"
                  style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
                >
                  <h3 className="text-xs font-semibold" style={{ color: "var(--heading)" }}>{item.title}</h3>
                  <p className="text-[11px] mt-1 leading-relaxed" style={{ color: "var(--text-2)" }}>{item.desc}</p>
                  <div className="flex items-center justify-between mt-3 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                    <span className="text-[10px]" style={{ color: "var(--text-2)" }}>{item.time}</span>
                    <span className="text-[11px] font-semibold" style={{ color: "var(--cyan)" }}>Read &rarr;</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Core Guides */}
          <section className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg" style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}>\ud83e\udded</div>
              <div>
                <h2 className="text-sm font-bold tracking-tight" style={{ color: "var(--heading)" }}>2. Core Guides</h2>
                <p className="text-[11px]" style={{ color: "var(--text-2)" }}>In-depth guides to help you master SatQuery AI.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {CORE_GUIDES.map((item) => (
                <div
                  key={item.title}
                  className="p-3.5 rounded-xl transition flex flex-col justify-between group"
                  style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
                >
                  <div>
                    <h3 className="text-xs font-semibold" style={{ color: "var(--heading)" }}>{item.title}</h3>
                    <p className="text-[10px] mt-1 leading-relaxed" style={{ color: "var(--text-2)" }}>{item.desc}</p>
                  </div>
                  <div className="flex items-center justify-between mt-3 pt-2 text-[10px]" style={{ borderTop: "1px solid var(--border)", color: "var(--text-2)" }}>
                    <span>{item.time}</span>
                    <span style={{ color: "var(--cyan)" }}>&rarr;</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>

        {/* Right sidebar */}
        <aside className="col-span-12 xl:col-span-3 space-y-4">
          {/* Quick Links */}
          <div
            className="rounded-xl p-4"
            style={{ border: "1px solid var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-md)" }}
          >
            <h3 className="text-xs font-bold tracking-wide mb-3" style={{ color: "var(--heading)" }}>Quick Links</h3>
            <div className="space-y-1 text-xs">
              {QUICK_LINKS.map((link) => (
                <Link key={link.label} href="#" className="flex items-center justify-between p-2 rounded-lg transition group" style={{ color: "var(--text)" }}>
                  <div>
                    <div className="text-[11px] font-semibold" style={{ color: "var(--text)" }}>{link.label}</div>
                    <div className="text-[9px]" style={{ color: "var(--text-2)" }}>{link.desc}</div>
                  </div>
                  <svg className="w-3.5 h-3.5" style={{ color: "var(--text-3)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </Link>
              ))}
            </div>
          </div>

          {/* System Status */}
          <div
            className="rounded-xl p-4"
            style={{ border: "1px solid var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-md)" }}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold tracking-wide" style={{ color: "var(--heading)" }}>System Status</h3>
              <span
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-semibold"
                style={{ background: "var(--status-completed-bg)", color: "var(--status-completed-text)", border: "1px solid var(--green)" }}
              >
                <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--green)" }} />
                All Systems Operational
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "API Uptime", value: "99.9%" },
                { label: "Queue", value: "2 jobs" },
                { label: "Users", value: "12.4K" },
              ].map((stat) => (
                <div key={stat.label} className="rounded-lg p-2 text-center" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                  <div className="text-[9px] font-medium" style={{ color: "var(--text-2)" }}>{stat.label}</div>
                  <div className="text-xs font-bold mt-1" style={{ color: "var(--cyan)" }}>{stat.value}</div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
