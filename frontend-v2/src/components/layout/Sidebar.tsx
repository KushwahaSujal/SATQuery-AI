"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface SidebarProps {
  hideBrand?: boolean;
  activeItem?: string;
  className?: string;
}

const recentHistory = [
  {
    id: "job_001",
    title: "Urban Expansion Analysis",
    type: "Change Detection",
    time: "2 hours ago",
    status: "completed",
  },
  {
    id: "job_002",
    title: "River Detection & Mapping",
    type: "VQA",
    time: "5 hours ago",
    status: "completed",
  },
  {
    id: "job_003",
    title: "Crop Health Assessment",
    type: "Optical + SAR",
    time: "Yesterday",
    status: "completed",
  },
  {
    id: "job_004",
    title: "Flood Impact Analysis",
    type: "Change Detection",
    time: "Yesterday",
    status: "completed",
  },
  {
    id: "job_005",
    title: "Deforestation Monitoring",
    type: "VQA",
    time: "2 days ago",
    status: "completed",
  },
];

export default function Sidebar({ hideBrand = false, activeItem, className = "" }: SidebarProps) {
  const pathname = usePathname();

  const current = activeItem || (
    pathname === "/" ? "home" :
    pathname.startsWith("/analysis") ? "analysis" :
    pathname.startsWith("/history") ? "history" :
    pathname.startsWith("/datasets") ? "datasets" :
    pathname.startsWith("/reports") ? "reports" :
    pathname.startsWith("/documentation") ? "documentation" : ""
  );

  return (
    <aside
      className={`w-64 min-w-[16rem] max-w-[16rem] bg-[var(--sidebar-bg)]/95 border-r border-[var(--sidebar-border)] flex flex-col justify-between p-4 shrink-0 z-20 overflow-y-auto select-none ${className}`}
      data-purpose="sidebar"
    >
      <div>
        {/* Brand Logo Header (shown when header is not full-width top) */}
        {!hideBrand && (
          <div className="flex items-center gap-3 px-2 py-3 mb-4">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[var(--cyan)] to-[var(--primary)] flex items-center justify-center shadow-lg shadow-teal-500/20 font-bold shrink-0">
              <svg className="w-5 h-5 text-[var(--canvas)]" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="2" x2="12" y2="6" />
                <line x1="12" y1="18" x2="12" y2="22" />
                <line x1="2" y1="12" x2="6" y2="12" />
                <line x1="18" y1="12" x2="22" y2="12" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-lg font-bold text-[var(--sidebar-text)] tracking-tight">SatQuery</span>
                <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-[var(--cyan-glow)] text-[var(--cyan)] border border-[var(--cyan)]/30">AI</span>
              </div>
              <p className="text-[10px] text-[var(--sidebar-muted)] font-medium tracking-wide mt-1">Remote Sensing · Vision · Intelligence</p>
            </div>
          </div>
        )}

        {/* Top Primary Navigation Menu */}
        <nav className="space-y-1 text-sm font-medium">
          <Link
            href="/"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-xs ${
              current === "home"
                ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--cyan)]/30 font-semibold"
                : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Home</span>
          </Link>

          <Link
            href="/analysis"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-xs ${
              current === "analysis"
                ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--cyan)]/30 font-semibold"
                : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v8m-4-4h8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>New Analysis</span>
          </Link>

          {/*<Link*/}
          {/*  href="/history"*/}
          {/*  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-xs ${*/}
          {/*    current === "history"*/}
          {/*      ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--cyan)]/30 font-semibold"*/}
          {/*      : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"*/}
          {/*  }`}*/}
          {/*>*/}
          {/*  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">*/}
          {/*    <circle cx="12" cy="12" r="9" />*/}
          {/*    <polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" />*/}
          {/*  </svg>*/}
          {/*  <span>History</span>*/}
          {/*</Link>*/}

          <Link
            href="/datasets"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-xs ${
              current === "datasets"
                ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--cyan)]/30 font-semibold"
                : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span>Datasets</span>
          </Link>

          <Link
            href="/reports"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-xs ${
              current === "reports"
                ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--cyan)]/30 font-semibold"
                : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Reports</span>
          </Link>
        </nav>

        {/* Recent History Section */}
        <div className="mt-6">
          <div className="flex items-center justify-between px-3 mb-2">
            <p className="text-[10px] font-bold text-[var(--sidebar-muted)] tracking-wider uppercase">Recent Analysis</p>
            <Link href="/history" className="text-[10px] font-medium text-[var(--cyan)] hover:text-[var(--cyan)]/80 transition-colors">
              View all
            </Link>
          </div>
          <div className="space-y-1">
            {recentHistory.map((item) => (
              <Link
                key={item.id}
                href={`/analysis/${item.id}`}
                className="flex items-start gap-2.5 px-3 py-2 rounded-lg hover:bg-[var(--surface-hover)] transition-all group"
              >
                <div className="w-6 h-6 rounded-md bg-[var(--cyan-glow)] border border-[var(--cyan)]/30 flex items-center justify-center shrink-0 mt-0.5">
                  <svg className="w-3 h-3 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-medium text-[var(--sidebar-text)] truncate group-hover:text-[var(--cyan)] transition-colors">
                    {item.title}
                  </p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--green)]" />
                    <span className="text-[9px] text-[var(--sidebar-muted)]">{item.type}</span>
                    <span className="text-[9px] text-[var(--sidebar-muted)]">·</span>
                    <span className="text-[9px] text-[var(--sidebar-muted)]">{item.time}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Resources Section */}
        <div className="mt-6">
          <p className="px-3 text-[10px] font-bold text-[var(--sidebar-muted)] tracking-wider uppercase mb-2">Resources</p>
          <nav className="space-y-1 text-xs">
            <Link
              href="/documentation"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${
                current === "documentation"
                  ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--cyan)]/30 font-semibold"
                  : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
              }`}
            >
              <svg className="w-4 h-4 text-[var(--sidebar-icon)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Documentation</span>
            </Link>
            {/*<Link*/}
            {/*  href="/documentation#support"*/}
            {/*  className="flex items-center gap-3 px-3 py-2 text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)] rounded-lg transition-all"*/}
            {/*>*/}
            {/*  <svg className="w-4 h-4 text-[var(--sidebar-icon)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">*/}
            {/*    <circle cx="12" cy="12" r="9" />*/}
            {/*    <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3m.08 4h.01" strokeLinecap="round" strokeLinejoin="round" />*/}
            {/*  </svg>*/}
            {/*  <span>Help &amp; Support</span>*/}
            {/*</Link>*/}
          </nav>
        </div>
      </div>

      {/* Sidebar Bottom Card: Sustainability / Mission */}
      <div className="mt-6 p-3.5 rounded-xl bg-gradient-to-b from-[var(--surface-2)] to-[var(--surface-3)] border border-[var(--cyan)]/20 relative overflow-hidden group">
        <div className="absolute inset-0 opacity-15 bg-[radial-gradient(var(--cyan)_1px,transparent_1px)] [background-size:12px_12px] pointer-events-none"></div>
        <div className="relative z-10 flex items-start gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[var(--cyan-glow)] border border-[var(--cyan)]/30 flex items-center justify-center shrink-0 mt-0.5">
            <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-semibold text-[var(--heading)] leading-snug">Better insights <br /><span className="text-[var(--text-2)] font-normal">for a healthier planet</span></p>
            <p className="text-[10px] text-[var(--text-3)] leading-tight mt-1">AI-powered remote sensing for a sustainable future.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export { Sidebar };
