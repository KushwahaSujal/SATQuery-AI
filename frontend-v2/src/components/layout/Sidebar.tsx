"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/analysis", label: "New Analysis", icon: "plus-circle" },
  { href: "/history", label: "History", icon: "clock" },
  { href: "/datasets", label: "Datasets", icon: "database" },
  { href: "/reports", label: "Reports", icon: "file-text" },
];

const toolItems = [
  { href: "/analysis", label: "AI Assistant", icon: "message-square" },
  { href: "/analysis", label: "VQA", icon: "eye" },
  { href: "/analysis", label: "Grounding", icon: "crosshair" },
  { href: "/analysis", label: "Change Analysis", icon: "arrow-left-right" },
  { href: "/analysis", label: "Optical + SAR Fusion", icon: "layers" },
];

const resourceItems = [
  { href: "/documentation", label: "Documentation", icon: "book-open" },
  { href: "/documentation", label: "Help & Support", icon: "help-circle" },
];

function NavIcon({ name, className, style }: { name: string; className?: string; style?: React.CSSProperties }) {
  const icons: Record<string, React.ReactNode> = {
    home: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    "plus-circle": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 8v8m-4-4h8" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    clock: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    database: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>,
    "file-text": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    "message-square": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    eye: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" /><path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    crosshair: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    "arrow-left-right": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    layers: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>,
    "book-open": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    "help-circle": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3m.08 4h.01" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  };
  const icon = icons[name] ?? null;
  return icon ? <span style={style} className="inline-flex">{icon}</span> : null;
}

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-64 shrink-0 border-r flex flex-col justify-between p-4 sticky top-0 h-screen overflow-y-auto z-40"
      style={{
        background: "var(--sidebar-bg)",
        borderColor: "var(--sidebar-border)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div>
        {/* Brand */}
        <div className="flex items-center gap-3 px-2 py-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#00C9E8] to-[#1758D8] flex items-center justify-center shadow-lg">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
              <polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-1.5 leading-none">
              <span className="text-lg font-bold tracking-tight" style={{ color: "var(--heading)" }}>SatQuery</span>
              <span
                className="text-xs font-bold px-1.5 py-0.5 rounded"
                style={{ background: "var(--primary-glow)", color: "var(--primary)", border: "1px solid var(--primary)" }}
              >AI</span>
            </div>
            <p className="text-[10px] font-medium tracking-wide mt-1" style={{ color: "var(--text-2)" }}>Remote Sensing · Vision · Intelligence</p>
          </div>
        </div>

        {/* Main Nav */}
        <nav className="space-y-1 text-sm font-medium">
          {navItems.map(({ href, label, icon }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={href + label}
                href={href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all"
                style={active ? {
                  background: "var(--sidebar-active-bg)",
                  color: "var(--sidebar-active-text)",
                  border: "1px solid var(--border)",
                  fontWeight: 600,
                } : {
                  color: "var(--sidebar-text)",
                }}
              >
                <NavIcon name={icon} className="w-4 h-4" style={{ color: active ? "var(--sidebar-active-text)" : "var(--sidebar-icon)" }} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Analysis Tools */}
        <div className="mt-7">
          <p className="px-3 text-[11px] font-semibold tracking-wider uppercase mb-2" style={{ color: "var(--sidebar-muted)" }}>Analysis Tools</p>
          <nav className="space-y-1 text-sm font-medium">
            {toolItems.map(({ label, icon }) => (
              <Link
                key={label}
                href="/analysis"
                className="flex items-center gap-3 px-3 py-2 rounded-lg transition-all"
                style={{ color: "var(--sidebar-text)" }}
              >
                <NavIcon name={icon} className="w-4 h-4" style={{ color: "var(--sidebar-icon)" }} />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
        </div>

        {/* Resources */}
        <div className="mt-7">
          <p className="px-3 text-[11px] font-semibold tracking-wider uppercase mb-2" style={{ color: "var(--sidebar-muted)" }}>Resources</p>
          <nav className="space-y-1 text-sm font-medium">
            {resourceItems.map(({ href, label, icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={label}
                  href={href}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg transition-all"
                  style={active ? {
                    background: "var(--sidebar-active-bg)",
                    color: "var(--sidebar-active-text)",
                    border: "1px solid var(--border)",
                    fontWeight: 600,
                  } : {
                    color: "var(--sidebar-text)",
                  }}
                >
                  <NavIcon name={icon} className="w-4 h-4" style={{ color: active ? "var(--sidebar-active-text)" : "var(--sidebar-icon)" }} />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Bottom eco card */}
      <div
        className="mt-6 p-3.5 rounded-xl relative overflow-hidden"
        style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
      >
        <div className="absolute inset-0 opacity-15 bg-[radial-gradient(var(--cyan)_1px,transparent_1px)] [background-size:12px_12px] pointer-events-none" />
        <div className="relative z-10 flex items-start gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)" }}
          >
            <svg className="w-4 h-4" style={{ color: "var(--cyan)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-semibold leading-snug" style={{ color: "var(--heading)" }}>Better insights <br /><span style={{ color: "var(--text)" }} className="font-normal">for a healthier planet</span></p>
            <p className="text-[10px] leading-tight mt-1" style={{ color: "var(--text-2)" }}>AI-powered remote sensing for a sustainable future.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
