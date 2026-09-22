"use client";

import Link from "next/link";
import { taskLabel } from "@/lib/taskLabels";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { DURATION, EASE } from "@/lib/motion";
import { api } from "@/lib/api";
import { useJobs } from "@/hooks/useJobs";
import { useAnalysisStore } from "@/stores/useAnalysisStore";
import { useMobileNav } from "@/components/layout/MobileNavContext";

interface SidebarProps {
  hideBrand?: boolean;
  activeItem?: string;
  className?: string;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

const navItems = [
  {
    key: "home",
    href: "/",
    label: "Home",
    icon: (
      <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    key: "analysis",
    href: "/analysis",
    label: "New Analysis",
    icon: (
      <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    key: "datasets",
    href: "/datasets",
    label: "Datasets",
    icon: (
      <>
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      </>
    ),
  },
  {
    key: "reports",
    href: "/reports",
    label: "Reports",
    icon: (
      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    key: "history",
    href: "/history",
    label: "History",
    icon: (
      <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
];

const resourceItems = [
  {
    key: "documentation",
    href: "/documentation",
    label: "Documentation",
    icon: (
      <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    key: "models",
    href: "/models",
    label: "Models",
    icon: (
      <path d="M4 7v10l8 4 8-4V7l-8-4-8 4zm8 4l8-4m-8 4L4 7m8 4v10" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    key: "system",
    href: "/system",
    label: "System",
    icon: (
      <path d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
];

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};
const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

export default function Sidebar({ hideBrand = false, activeItem, className = "" }: SidebarProps) {
  const pathname = usePathname();
  const { data: jobs } = useJobs();
  const resetAnalysis = useAnalysisStore((state) => state.resetAnalysis);

  const recentHistory = (jobs ?? [])
    .map((j: Record<string, unknown>) => ({
      id: (j.job_id || j.id) as string,
      title: (j.query as string)?.slice(0, 40) || "Analysis",
      type: taskLabel(j.task as string),
      status: (j.status as string) || "UNKNOWN",
      time: timeAgo((j.created_at as string) || new Date().toISOString()),
    }));

  const { isOpen, close } = useMobileNav();

  const current = activeItem || (
    pathname === "/" ? "home" :
    pathname === "/analysis" ? "analysis" :
    pathname.startsWith("/history") ? "history" :
    pathname.startsWith("/datasets") ? "datasets" :
    pathname.startsWith("/reports") ? "reports" :
    pathname.startsWith("/documentation") ? "documentation" :
    pathname.startsWith("/models") ? "models" :
    pathname.startsWith("/system") ? "system" :
    pathname.startsWith("/visual-analytics") ? "history" :
    pathname.startsWith("/video") ? "history" : ""
  );

  return (
    <>
      {/* Scrim, mobile only. The drawer sits over the content at small widths because
          the sidebar used to be a hard 15rem, which ate ~60% of a 390px viewport and
          clipped the body copy of every page. */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-[var(--scrim)] md:hidden"
          onClick={close}
          aria-hidden="true"
        />
      )}
      <aside
        id="app-sidebar"
        className={`fixed inset-y-0 left-0 z-40 w-[17rem] max-w-[85vw] transform transition-transform duration-200 ease-out md:static md:z-20 md:w-60 md:min-w-[15rem] md:max-w-[15rem] md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        } h-full min-h-0 bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)] flex flex-col justify-between pt-4 pb-14 px-3 shrink-0 overflow-y-auto select-none ${className}`}
        data-purpose="sidebar"
        aria-hidden={isOpen ? undefined : "true"}
      >
        {/* Close control, mobile only */}
        <button
          type="button"
          onClick={close}
          aria-label="Close navigation"
          className="md:hidden absolute top-3 right-3 p-1.5 rounded-lg text-[var(--text-3)] hover:text-[var(--heading)] hover:bg-[var(--surface-hover)] transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" />
          </svg>
        </button>
      <div>
        {/* Brand */}
        {!hideBrand && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
            className="flex items-center gap-3 px-2 py-3 mb-3"
          >
            <div className="w-8 h-8 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center shrink-0">
              <img
                src="/satquery.svg"
                alt="SatQuery AI"
                className="w-6 h-6 rounded-md object-cover"
              />
            </div>
            <div>
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-base font-bold text-[var(--sidebar-text)] tracking-tight">SatQuery</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/30">AI</span>
              </div>
              <p className="text-[9px] text-[var(--sidebar-muted)] font-medium tracking-wide mt-0.5">Remote Sensing · Vision</p>
            </div>
          </motion.div>
        )}

        {/* Primary Nav */}
        <motion.nav
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-0.5 text-xs font-medium"
        >
          {navItems.map(({ key, href, label, icon }) => {
            const isActive = current === key;
            return (
              <motion.div key={key} variants={itemVariants} whileHover={{ x: 2 }} whileTap={{ scale: 0.985 }} transition={{ duration: DURATION.fast, ease: EASE }}>
                <Link
                  href={href}
                  onClick={key === "analysis" ? resetAnalysis : undefined}
                  className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 overflow-hidden ${
                    isActive
                      ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] font-semibold"
                      : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
                  }`}
                >
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-bar"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-[var(--cyan)]"
                    />
                  )}
                  <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    {icon}
                  </svg>
                  <span>{label}</span>
                </Link>
              </motion.div>
            );
          })}
        </motion.nav>

        {/* Recent History */}
        <div className="mt-5">
          <div className="flex items-center justify-between px-2 mb-1.5">
            <p className="text-[10px] font-bold text-[var(--sidebar-muted)] tracking-wider uppercase">
              Analysis history
            </p>
            <Link href="/history" className="text-[10px] font-medium text-[var(--cyan)] hover:opacity-80 transition-opacity">
              View all
            </Link>
          </div>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="max-h-72 space-y-0.5 overflow-y-auto pr-1"
          >
            {recentHistory.map((item) => (
              <motion.div key={item.id} variants={itemVariants}>
                <Link
                  href={`/analysis/${item.id}`}
                  className={`flex items-start gap-2.5 px-2.5 py-2 rounded-lg transition-all duration-150 group ${
                    pathname === `/analysis/${item.id}`
                      ? "bg-[var(--sidebar-active-bg)]"
                      : "hover:bg-[var(--surface-hover)]"
                  }`}
                >
                  <div className="w-5 h-5 rounded bg-[var(--cyan-glow)] border border-[var(--cyan)]/20 flex items-center justify-center shrink-0 mt-0.5">
                    <svg className="w-2.5 h-2.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-medium text-[var(--sidebar-text)] truncate group-hover:text-[var(--cyan)] transition-colors">
                      {item.title}
                    </p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className={`w-1 h-1 rounded-full ${
                        item.status === "COMPLETED" ? "bg-[var(--green)]" :
                        item.status === "RUNNING" || item.status === "QUEUED" || item.status === "GENERATING_EVIDENCE" ? "bg-[var(--cyan)] animate-pulse" :
                        "bg-[var(--text-4)]"
                      }`} />
                      <span className="text-[9px] text-[var(--sidebar-muted)]">{item.type} · {item.time}</span>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* Resources */}
        <div className="mt-5">
          <p className="px-2 text-[10px] font-bold text-[var(--sidebar-muted)] tracking-wider uppercase mb-1.5">Resources</p>
          <motion.nav
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="space-y-0.5 text-xs"
          >
            {resourceItems.map(({ key, href, label, icon }) => {
              const isActive = current === key;
              return (
                <motion.div key={key} variants={itemVariants} whileHover={{ x: 2 }} whileTap={{ scale: 0.985 }} transition={{ duration: DURATION.fast, ease: EASE }}>
                  <Link
                    href={href}
                    className={`relative flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-150 overflow-hidden ${
                      isActive
                        ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] font-semibold"
                        : "text-[var(--sidebar-icon)] hover:text-[var(--sidebar-text)] hover:bg-[var(--surface-hover)]"
                    }`}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-[var(--cyan)]" />
                    )}
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      {icon}
                    </svg>
                    <span>{label}</span>
                  </Link>
                </motion.div>
              );
            })}
          </motion.nav>
        </div>
      </div>

      {/* Social Links */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.4 }}
        className="mt-4 flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
      >
        <span className="text-[9px] font-semibold uppercase tracking-wider text-[var(--text-3)]">Connect with Us</span>
        <div className="flex items-center gap-1.5">
          <a
            href="https://github.com/KushwahaSujal/SATQuery-AI"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Open SatQuery AI on GitHub"
            title="GitHub"
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-1.5 text-[var(--text-2)] transition hover:border-[var(--primary)]/50 hover:text-[var(--primary)]"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 .7a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.5-1.4-1.3-1.7-1.3-1.7-1.1-.8.1-.8.1-.8 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.4-5.5-6A4.7 4.7 0 0 1 5.7 9c-.1-.3-.5-1.6.1-3.3 0 0 1-.3 3.4 1.3a11.7 11.7 0 0 1 6.2 0c2.4-1.6 3.4-1.3 3.4-1.3.6 1.7.2 3 .1 3.3a4.7 4.7 0 0 1 1.3 3.3c0 4.6-2.8 5.7-5.5 6 .4.3.8 1 .8 2v2.9c0 .3.2.7.8.6A12 12 0 0 0 12 .7Z" />
            </svg>
            <span className="sr-only">GitHub</span>
          </a>
          <a
            href="https://www.youtube.com/@SatQueryAI"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Watch SatQuery AI on YouTube"
            title="YouTube"
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-1.5 text-[var(--text-2)] transition hover:border-[#ff0033]/50 hover:text-[#ff0033]"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.3 3.6-6.3 3.6Z" />
            </svg>
            <span className="sr-only">YouTube</span>
          </a>
        </div>
      </motion.div>

    </aside>
    </>
  );
}

export { Sidebar };
