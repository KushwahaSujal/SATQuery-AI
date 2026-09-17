import "./globals.css";
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import Rail from "@/components/layout/Rail";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "SatQuery AI — Earth Observation Workstation",
  description: "Institutional-grade geospatial intelligence workstation powered by satellite imagery analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body suppressHydrationWarning style={{ height: "100vh", overflow: "hidden" }}>
        <Providers>
          <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
            {/* Topbar — 52px */}
            <header className="topbar">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-[10px] flex items-center justify-center" style={{ background: "linear-gradient(150deg, var(--brand-cyan), #0EA5A2 55%, #1E3A8A)", boxShadow: "0 0 0 1px rgba(0,213,191,.4), 0 0 26px -8px var(--brand-cyan)" }}>
                  <svg className="w-5 h-5" fill="none" stroke="#06110f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />
                  </svg>
                </div>
                <span className="name">SatQuery</span>
              </div>
              <span className="spacer" />
              {/* Search */}
              <div className="relative flex-1 max-w-xl mx-6">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="8" /><line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <input
                  className="w-full pl-10 pr-12 py-2 bg-[#0c1424] border border-[#1d2a44] rounded-lg text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:border-teal-500/60 focus:ring-1 focus:ring-teal-500/40 transition-all"
                  placeholder='Search anything... (e.g. "urban expansion in Delhi")'
                />
                <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center">
                  <kbd className="px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-[#142036] border border-[#233352] rounded shadow-sm flex items-center gap-0.5">
                    <span>⌘</span><span>K</span>
                  </kbd>
                </div>
              </div>
              <span className="spacer" />
              {/* Right controls */}
              <div className="flex items-center gap-3">
                <button className="btn btn-ghost btn-sm">Docs</button>
                <div className="flex items-center gap-2.5 pl-2 border-l border-[#1b263b] cursor-pointer">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-slate-700 to-slate-600 border border-slate-500 flex items-center justify-center text-xs font-semibold text-white">SM</div>
                  <span className="text-sm font-medium text-slate-200 hidden sm:inline-block">Sandipan Majumder</span>
                  <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <polyline points="6 9 12 15 18 9" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              </div>
            </header>
            {/* Body row: Rail + Content */}
            <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
              <Rail />
              <main style={{ flex: 1, minWidth: 0, background: "var(--brand-dark)", overflowY: "auto" }}>
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
