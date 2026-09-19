"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useJobs } from "@/hooks/useJobs";

interface SidebarProps {
  hideBrand?: boolean;
  activeItem?: string;
  className?: string;
}

const TASK_LABELS: Record<string, string> = {
  bi_temporal_change: "Change Detection",
  bi_temporal_change_vqa: "Change VQA",
  single_image_vqa: "VQA",
  single_image_grounding: "Grounding",
  single_image_caption: "Captioning",
  video_grounding_tracking: "Video",
  video_vqa: "Video VQA",
  video_change: "Video Change",
  optical_sar_analysis: "Optical + SAR",
};

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

  const recentHistory = (jobs ?? [])
    .map((j: Record<string, unknown>) => ({
      id: (j.job_id || j.id) as string,
      title: (j.query as string)?.slice(0, 40) || "Analysis",
      type: TASK_LABELS[(j.task as string) || ""] || (j.task as string) || "Analysis",
      status: (j.status as string) || "UNKNOWN",
      time: timeAgo((j.created_at as string) || new Date().toISOString()),
    }));

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
      className={`h-full min-h-0 w-60 min-w-[15rem] max-w-[15rem] bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)] flex flex-col justify-between py-4 px-3 shrink-0 z-20 overflow-y-auto select-none ${className}`}
      data-purpose="sidebar"
    >
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
              <svg className="w-4 h-4 text-[var(--primary)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="2" x2="12" y2="6" />
                <line x1="12" y1="18" x2="12" y2="22" />
                <line x1="2" y1="12" x2="6" y2="12" />
                <line x1="18" y1="12" x2="22" y2="12" />
              </svg>
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
              <motion.div key={key} variants={itemVariants}>
                <Link
                  href={href}
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
                  className="flex items-start gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[var(--surface-hover)] transition-all duration-150 group"
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
                <motion.div key={key} variants={itemVariants}>
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

      {/* Bottom Mission Card */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.4 }}
        className="mt-4 p-3 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]"
      >
        <div className="flex items-start gap-2.5">
          <div className="w-6 h-6 rounded-md bg-[var(--primary-glow)] border border-[var(--primary)]/20 flex items-center justify-center shrink-0 mt-0.5">
            <svg className="w-3 h-3 text-[var(--primary)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-[var(--heading)] leading-snug">
              Better insights <br />
              <span className="text-[var(--text-2)] font-normal">for a healthier planet</span>
            </p>
            <p className="text-[9px] text-[var(--text-3)] leading-tight mt-1">AI-powered remote sensing for a sustainable future.</p>
          </div>
        </div>
      </motion.div>
    </aside>
  );
}

export { Sidebar };
