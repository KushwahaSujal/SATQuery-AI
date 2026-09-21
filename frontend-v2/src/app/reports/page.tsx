"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  describeJobStatus,
  isJobComplete,
  jobStatusDotClasses,
  jobStatusLabel,
  jobStatusPillClasses,
} from "@/lib/statusMap";
import { useJobs } from "@/hooks/useJobs";
import type { AnalysisResult } from "@/lib/types";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { BorderBeam } from "@/components/ui/border-beam";

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } } };
const rowVariant = { hidden: { opacity: 0, x: -8 }, show: { opacity: 1, x: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } } };

const TASK_LABELS: Record<string, { label: string; type: string }> = {
  bi_temporal_change: { label: "Change Detection", type: "Change Analysis" },
  bi_temporal_change_vqa: { label: "Change VQA", type: "Change Analysis" },
  single_image_vqa: { label: "VQA Analysis", type: "Optical" },
  single_image_grounding: { label: "Grounding", type: "Optical" },
  single_image_caption: { label: "Captioning", type: "Optical" },
  video_grounding_tracking: { label: "Video Tracking", type: "Video" },
  video_vqa: { label: "Video VQA", type: "Video" },
  video_change: { label: "Video Change", type: "Video" },
  optical_sar_analysis: { label: "Optical + SAR", type: "Optical + SAR" },
};


function formatDate(iso: string): { date: string; time: string } {
  try {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      time: d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }),
    };
  } catch {
    return { date: "", time: "" };
  }
}

export default function ReportsPage() {
  const [selectedTab, setSelectedTab] = useState<string>("All Reports");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sliderPos, setSliderPos] = useState<number>(50);

  const { data: rawJobs = [], isLoading } = useJobs();
  const jobs = rawJobs.map((item: Record<string, unknown>) => ({
        id: (item.job_id || item.id || "") as string,
        query: (item.query as string) || "Geospatial query",
        task: (item.task as string) || "single_image_vqa",
        status: (item.status as string) || "COMPLETED",
        created_at: (item.created_at as string) || new Date().toISOString(),
        confidence: (item.confidence as number) ?? undefined,
      }));

  const activeId = selectedId || (jobs.length > 0 ? jobs[0].id : null);

  const { data: result } = useQuery<AnalysisResult>({
    queryKey: ["result", activeId],
    queryFn: () => api.result(activeId!),
    enabled: Boolean(activeId),
    staleTime: 60_000,
    retry: 1,
  });

  const filteredReports = jobs.filter((item) => {
    const matchesTab =
      selectedTab === "All Reports" ||
      (selectedTab === "Completed" && item.status === "COMPLETED") ||
      (selectedTab === "In Progress" && ["RUNNING", "PENDING", "QUEUED", "VALIDATING", "PLANNING"].includes(item.status)) ||
      (selectedTab === "Failed" && item.status === "FAILED");
    const matchesSearch = item.query.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  const tabCounts = {
    "All Reports": jobs.length,
    "Completed": jobs.filter((j) => j.status === "COMPLETED").length,
    "In Progress": jobs.filter((j) => ["RUNNING", "PENDING", "QUEUED", "VALIDATING", "PLANNING"].includes(j.status)).length,
    "Failed": jobs.filter((j) => j.status === "FAILED").length,
  };

  const displayConfidence = result?.confidence != null ? Math.round(result.confidence * 100) : null;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }} className="bg-[var(--canvas)] text-[var(--text)] antialiased font-sans h-screen overflow-hidden flex flex-col selection:bg-cyan-500 selection:text-[var(--canvas)]">
      <TopBar showBrand={true} searchPlaceholder="Search reports, locations, or keywords..." onSearch={(q) => setSearchQuery(q)} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="reports" className="h-full" />

        <main className="flex-1 overflow-y-auto p-6 space-y-5 bg-[var(--canvas)]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="relative w-10 h-10 rounded-xl bg-cyan-950/60 border border-[var(--cyan)]/30 flex items-center justify-center text-[var(--cyan)] mt-0.5 shadow-[0_0_15px_rgba(6,182,212,0.15)] overflow-hidden">
                <BorderBeam duration={5} size={60} colorFrom="#00d5be" colorTo="#00f2fe" />
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-[var(--heading)] tracking-tight">Reports</h1>
                <p className="text-xs text-[var(--text-3)] mt-0.5">
                  View, manage and download your analysis reports. Each report includes detailed insights, visualizations and export options.
                </p>
              </div>
            </div>
            <Link
              href="/analysis"
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 text-[var(--heading)] font-medium text-xs shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Generate Report</span>
            </Link>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2 border-b border-[var(--border)] pb-3 text-xs font-semibold">
            {["All Reports", "Completed", "In Progress", "Failed"].map((tab) => {
              const active = selectedTab === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setSelectedTab(tab)}
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-2 transition cursor-pointer ${
                    active
                      ? "bg-cyan-950/70 border border-[var(--cyan)]/40 text-[var(--cyan)] shadow-sm"
                      : "text-[var(--text-3)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)]"
                  }`}
                >
                  <span>{tab}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${active ? "bg-cyan-500/20 text-[var(--cyan)]" : "bg-[var(--surface-hover)] text-[var(--text-3)]"}`}>
                    {tabCounts[tab as keyof typeof tabCounts] ?? 0}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="relative flex-1 min-w-[200px]">
              <svg className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" x2="16.65" y1="21" y2="16.65" />
              </svg>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-xl pl-9 pr-3 py-1.5 text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)]/40"
                placeholder="Search reports..."
                type="text"
              />
            </div>
          </div>

          {/* Reports Table */}
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[10px] font-semibold text-[var(--text-3)] uppercase tracking-wider bg-[var(--surface)]/50">
                    <th className="py-3 px-4">Report Name</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Generated</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <motion.tbody variants={stagger} initial="hidden" animate="show" className="divide-y divide-[#121f36] text-xs font-normal">
                  {isLoading && jobs.length === 0 ? (
                    <tr><td colSpan={5} className="py-8 text-center text-[var(--text-3)]">Loading reports...</td></tr>
                  ) : filteredReports.length === 0 ? (
                    <tr><td colSpan={5} className="py-8 text-center text-[var(--text-3)]">No reports found</td></tr>
                  ) : (
                    filteredReports.map((report) => {
                      const isSelected = activeId === report.id;
                      const taskInfo = TASK_LABELS[report.task] || { label: report.task, type: "Analysis" };
                      const status = describeJobStatus(report.status);
                      const { date, time } = formatDate(report.created_at);
                      return (
                        <motion.tr
                          key={report.id}
                          variants={rowVariant}
                          onClick={() => setSelectedId(report.id)}
                          className={`hover:bg-[var(--surface-hover)]/50 transition-colors cursor-pointer ${isSelected ? "bg-cyan-950/20 border-l-2 border-[var(--cyan)]" : ""}`}
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-14 h-10 rounded-lg overflow-hidden shrink-0 border border-[var(--border)] bg-[var(--surface-3)] flex">
                                {["bi_temporal_change", "bi_temporal_change_vqa"].includes(report.task) ? (
                                  <>
                                    <img
                                      src={api.visualizationUrl(report.id, "temporal_image_a")}
                                      alt=""
                                      className="w-1/2 h-full object-cover border-r border-[var(--border)]"
                                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                                    />
                                    <img
                                      src={api.visualizationUrl(report.id, "temporal_image_b")}
                                      alt=""
                                      className="w-1/2 h-full object-cover"
                                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                                    />
                                  </>
                                ) : (
                                  <img
                                    src={api.visualizationUrl(report.id, "true_color")}
                                    alt=""
                                    className="w-full h-full object-cover"
                                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                                  />
                                )}
                                <svg className="w-4 h-4 text-[var(--text-4)] hidden absolute inset-0 m-auto" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                                  <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5z" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </div>
                              <div>
                                <div className="font-semibold text-[var(--heading)] text-xs hover:text-[var(--cyan)]">{report.query.slice(0, 50)}</div>
                                <div className="text-[11px] text-[var(--text-3)]">{taskInfo.label}</div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-950/70 text-blue-300 border border-blue-800/40">
                              {taskInfo.type}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-[var(--text-3)] whitespace-nowrap">
                            <div className="text-[var(--text-2)] font-medium">{date}</div>
                            <div className="text-[10px] text-[var(--text-3)]">{time}</div>
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium border ${jobStatusPillClasses(report.status)}`}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${jobStatusDotClasses(report.status)} ${status.active ? "animate-ping" : ""}`}
                              />
                              {status.label}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1 text-[var(--text-3)]">
                              <a
                                href={api.downloadUrl(report.id)}
                                onClick={(e) => e.stopPropagation()}
                                className="p-1.5 hover:text-[var(--cyan)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors"
                                title="Download"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                  <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </a>
                              <Link
                                href={`/analysis/${report.id}`}
                                onClick={(e) => e.stopPropagation()}
                                className="p-1.5 hover:text-[var(--heading)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors"
                                title="View"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                  <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" />
                                  <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </Link>
                            </div>
                          </td>
                        </motion.tr>
                      );
                    })
                  )}
                </motion.tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-[var(--text-3)] pt-1">
            <div>Showing <span className="text-[var(--text)] font-medium">1 - {filteredReports.length}</span> of <span className="text-[var(--text)] font-medium">{jobs.length}</span> reports</div>
          </div>
        </main>

        {/* Right Details Drawer */}
        <aside className="w-96 shrink-0 border-l border-[var(--border)] bg-[var(--surface)] overflow-y-auto p-5 flex flex-col space-y-5 select-none">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-[var(--text-3)] font-medium">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <line x1="19" x2="5" y1="12" y2="12" /><polyline points="12 19 5 12 12 5" />
              </svg>
              <span>Report Details</span>
            </span>
            {result && (
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium border ${jobStatusPillClasses(result.status)}`}
              >
                {isJobComplete(result.status) ? (
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span className={`w-1.5 h-1.5 rounded-full ${jobStatusDotClasses(result.status)}`} />
                )}
                {jobStatusLabel(result.status)}
              </span>
            )}
          </div>

          <div>
            <h2 className="text-base font-bold text-[var(--heading)] tracking-tight">
              {result?.query || jobs.find((j) => j.id === activeId)?.query || "Report"}
            </h2>
            {result?.workflow && <p className="text-xs text-[var(--text-3)] mt-0.5">{result.workflow}</p>}
          </div>

          {/* Meta */}
          {result && (
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-2)]">
              {result.task && (
                <span className="px-2.5 py-1 rounded-lg bg-purple-950/60 text-purple-300 border border-purple-800/40 font-medium">
                  {TASK_LABELS[result.task]?.label || result.task}
                </span>
              )}
              {result.models_used?.map((m) => (
                <span key={m} className="px-2.5 py-1 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">{m}</span>
              ))}
            </div>
          )}

          {/* Visualization */}
          {result && activeId && (
            <div
              className="relative w-full h-80 rounded-xl overflow-hidden border border-[var(--border)] shadow-md cursor-ew-resize select-none"
              onMouseMove={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
                setSliderPos(pct);
              }}
            >
              {/* Base image (True Color) */}
              <img
                alt="True Color"
                className="absolute inset-0 w-full h-full object-cover"
                src={api.visualizationUrl(activeId, "true_color")}
                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
              />

              {/* Overlay image (Change Heatmap) — clipped */}
              <div
                className="absolute inset-0 overflow-hidden"
                style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
              >
                <img
                  alt="Change Heatmap"
                  className="absolute inset-0 w-full h-full object-cover"
                  src={api.visualizationUrl(activeId, "change_probability_heatmap")}
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                />
                <div className="absolute inset-0 bg-red-600/20 mix-blend-color-dodge" />
              </div>

              {/* Divider */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-white/80 shadow-[0_0_8px_rgba(255,255,255,0.5)] z-10 pointer-events-none"
                style={{ left: `${sliderPos}%` }}
              />

              {/* Labels */}
              <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] text-[var(--heading)] font-medium border border-[var(--border)] z-10">
                True Color
              </div>
              <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] text-[var(--heading)] font-medium border border-[var(--border)] z-10">
                Change Heatmap
              </div>
            </div>
          )}

          {/* Key Findings */}
          {result?.evidence?.spatial?.statistics && (
            <div>
              <h3 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Key Findings</span>
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                  <div className="flex items-center gap-1.5 text-[var(--cyan)] mb-1">
                    <span className="text-sm font-bold text-[var(--heading)]">
                      {result.evidence.spatial.statistics.changed_pixels?.toLocaleString() || "—"}
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-3)] leading-tight">Changed pixels</p>
                </div>
                <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                  <div className="flex items-center gap-1.5 text-[var(--cyan)] mb-1">
                    <span className="text-sm font-bold text-[var(--heading)]">
                      {result.evidence.spatial.statistics.region_count || "—"}
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-3)] leading-tight">Change regions</p>
                </div>
                <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                  <div className="flex items-center gap-1.5 text-emerald-400 mb-1">
                    <span className="text-sm font-bold text-[var(--heading)]">
                      {result.evidence.spatial.statistics.estimated_area_sq_km
                        ? `${result.evidence.spatial.statistics.estimated_area_sq_km.toFixed(2)} km²`
                        : "—"}
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-3)] leading-tight">Affected area</p>
                </div>
                <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                  <div className="flex items-center gap-1.5 text-[var(--cyan)] mb-1">
                    <span className="text-sm font-bold text-[var(--heading)]">
                      {result.evidence.spatial.statistics.change_ratio
                        ? `${(result.evidence.spatial.statistics.change_ratio * 100).toFixed(1)}%`
                        : "—"}
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-3)] leading-tight">Change ratio</p>
                </div>
              </div>
            </div>
          )}

          {/* Answer */}
          {result?.answer && (
            <div>
              <h3 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>AI Analysis</span>
              </h3>
              <p className="text-[11px] text-[var(--text-2)] leading-relaxed">{result.answer}</p>
            </div>
          )}

          {/* Download Buttons */}
          {activeId && (
            <div>
              <div className="text-[11px] font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Download Report</span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={api.downloadUrl(activeId)}
                  className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-[var(--canvas)] font-bold text-xs flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>Download Results</span>
                </a>
                <a
                  href={api.reportUrl(activeId)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-2)] hover:text-[var(--heading)] hover:border-[var(--border-strong)] transition-colors"
                  title="View Report"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </a>
              </div>
            </div>
          )}

          {/* Export Formats */}
          {/*{result && activeId && (*/}
          {/*  <div>*/}
          {/*    <h3 className="text-[11px] font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2">Export Formats</h3>*/}
          {/*    <div className="space-y-1.5">*/}
          {/*      {(["png", "geotiff", "geojson"] as const).map((fmt) => (*/}
          {/*        <a*/}
          {/*          key={fmt}*/}
          {/*          href={result.visualizations?.[0] ? api.exportUrl(activeId, (result.visualizations[0] as Record<string, unknown>).layer_id as string || "true_color", fmt) : "#"}*/}
          {/*          className="flex items-center justify-between p-2 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"*/}
          {/*        >*/}
          {/*          <div className="flex items-center gap-2">*/}
          {/*            <svg className="w-4 h-4 text-[var(--cyan)] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">*/}
          {/*              <rect height="18" rx="2" ry="2" width="18" x="3" y="3" />*/}
          {/*              <circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />*/}
          {/*            </svg>*/}
          {/*            <span className="text-xs text-[var(--text-2)] font-mono">.{fmt}</span>*/}
          {/*          </div>*/}
          {/*          <svg className="w-3.5 h-3.5 text-[var(--text-4)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">*/}
          {/*            <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />*/}
          {/*          </svg>*/}
          {/*        </a>*/}
          {/*      ))}*/}
          {/*    </div>*/}
          {/*  </div>*/}
          {/*)}*/}
        </aside>
      </div>
    </motion.div>
  );
}
