"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { describeTask, taskCategory, taskLabel, TASK_CATEGORIES } from "@/lib/taskLabels";
import { describeJobStatus, jobStatusDotClasses, jobStatusPillClasses } from "@/lib/statusMap";
import { useJobs } from "@/hooks/useJobs";
import { clearLocalJobs } from "@/lib/localJobs";
import type { AnalysisResult } from "@/lib/types";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { SpotlightCard } from "@/components/ui/spotlight-card";

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } } };
const rowVariant = { hidden: { opacity: 0, x: -12 }, show: { opacity: 1, x: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } } };



function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true });
  } catch {
    return iso;
  }
}

export default function HistoryPage() {
  const queryClient = useQueryClient();
  const [selectedTab, setSelectedTab] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedChecks, setSelectedChecks] = useState<Record<string, boolean>>({});
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [sliderPos, setSliderPos] = useState(50);

  const { data: rawJobs = [], isLoading } = useJobs();
  const jobs = rawJobs.map((item: Record<string, unknown>) => ({
        id: (item.job_id || item.id || "") as string,
        query: (item.query as string) || "Geospatial query",
        task: (item.task as string) || "single_image_vqa",
        status: (item.status as string) || "COMPLETED",
        created_at: (item.created_at as string) || new Date().toISOString(),
        confidence: (item.confidence as number) ?? undefined,
        models_used: (item.models_used as string[]) || [],
      }));

  const clearMutation = useMutation({
    mutationFn: async () => {
      await api.clearJobs();
      clearLocalJobs();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setShowClearConfirm(false);
      setSelectedId(null);
      setSelectedChecks({});
    },
  });

  const deleteSelectedMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      await Promise.all(ids.map((id) => api.deleteJob(id)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setSelectedChecks({});
      setShowClearConfirm(false);
    },
  });

  const selectedIds = Object.entries(selectedChecks)
    .filter(([, checked]) => checked)
    .map(([id]) => id);
  const selectedCount = selectedIds.length;

  const toggleAll = () => {
    if (allVisibleChecked) {
      setSelectedChecks({});
    } else {
      const next: Record<string, boolean> = {};
      filteredItems.forEach((item) => { next[item.id] = true; });
      setSelectedChecks(next);
    }
  };

  const activeId = selectedId || (jobs.length > 0 ? jobs[0].id : null);

  const { data: result } = useQuery<AnalysisResult>({
    queryKey: ["result", activeId],
    queryFn: () => api.result(activeId!),
    enabled: Boolean(activeId),
    staleTime: 60_000,
    retry: 1,
  });

  const categories = ["All", ...TASK_CATEGORIES];
  const tabCounts: Record<string, number> = { All: jobs.length };
  for (const j of jobs) {
    const cat = taskCategory(j.task);
    tabCounts[cat] = (tabCounts[cat] || 0) + 1;
  }

  const filteredItems = jobs.filter((item) => {
    const cat = taskCategory(item.task);
    const matchesTab = selectedTab === "All" || cat === selectedTab;
    const matchesSearch = item.query.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  const allVisibleChecked = filteredItems.length > 0 && filteredItems.every((item) => selectedChecks[item.id]);

  const toggleCheck = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedChecks((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const displayConfidence = result?.confidence != null ? Math.round(result.confidence * 100) : null;
  // No default status: an unknown state must not be reported as a finished one.
  const displayStatus = result?.status || jobs.find((j) => j.id === activeId)?.status;
  const statusInfo = describeJobStatus(displayStatus);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="bg-[var(--canvas)] text-[var(--text)] antialiased font-sans h-screen overflow-hidden flex flex-col selection:bg-cyan-500 selection:text-[var(--canvas)]"
    >
      <TopBar showBrand={true} searchPlaceholder="Search your analyses, locations, or queries..." onSearch={(q) => setSearchQuery(q)} />

      {/* See reports/page.tsx: stacks below lg so the 380px detail panel does not
          swallow a phone-width row. */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
        <Sidebar hideBrand={true} activeItem="history" className="h-full" />

        <main className="flex-1 flex flex-col min-h-0 min-w-0 bg-[var(--canvas)] overflow-hidden">
          <div className="p-6 pb-3 border-b border-[var(--border)] shrink-0">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-xl font-bold text-[var(--heading)] tracking-tight">Analysis History</h1>
                <p className="text-xs text-[var(--text-3)] mt-0.5">
                  View and manage your past analyses. Revisit results, download reports, or continue where you left off.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {/* Bulk Delete Controls */}
                <AnimatePresence>
                  {selectedCount > 0 && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, x: 10 }}
                      animate={{ opacity: 1, scale: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.95, x: 10 }}
                      className="flex items-center gap-2"
                    >
                      <span className="text-[11px] text-[var(--text-2)] font-medium">
                        {selectedCount} selected
                      </span>
                      <div className="relative">
                        <button
                          onClick={() => setShowClearConfirm(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/30 bg-red-500/5 text-red-400 hover:bg-red-500/10 hover:border-red-500/50 text-xs font-medium transition"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          <span>Delete</span>
                        </button>

                        <AnimatePresence>
                          {showClearConfirm && (
                            <>
                              <div className="fixed inset-0 z-40" onClick={() => setShowClearConfirm(false)} />
                              <div className="absolute right-0 top-full mt-2 w-72 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-2xl z-50 p-4">
                                <div className="flex items-center gap-2.5 mb-3">
                                  <div className="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center shrink-0">
                                    <svg className="w-4.5 h-4.5 text-red-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                      <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                  </div>
                                  <div>
                                    <p className="text-xs font-semibold text-[var(--heading)]">Delete {selectedCount} item{selectedCount !== 1 ? "s" : ""}?</p>
                                    <p className="text-[10px] text-[var(--text-3)]">This action cannot be undone.</p>
                                  </div>
                                </div>
                                <p className="text-[11px] text-[var(--text-3)] mb-3">
                                  Selected analysis jobs and their reports will be permanently deleted.
                                </p>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => deleteSelectedMutation.mutate(selectedIds)}
                                    disabled={deleteSelectedMutation.isPending}
                                    className="flex-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition disabled:opacity-50"
                                  >
                                    {deleteSelectedMutation.isPending ? "Deleting..." : "Delete Selected"}
                                  </button>
                                  <button
                                    onClick={() => setShowClearConfirm(false)}
                                    className="flex-1 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--heading)] transition"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            </>
                          )}
                        </AnimatePresence>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Clear All Button */}
                {jobs.length > 0 && selectedCount === 0 && (
                  <div className="relative">
                    <button
                      onClick={() => setShowClearConfirm(!showClearConfirm)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/30 bg-red-500/5 text-red-400 hover:bg-red-500/10 hover:border-red-500/50 text-xs font-medium transition"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <span>Clear All</span>
                    </button>

                    <AnimatePresence>
                      {showClearConfirm && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setShowClearConfirm(false)} />
                          <div className="absolute right-0 top-full mt-2 w-64 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-2xl z-50 p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                                <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                  <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </div>
                              <div>
                                <p className="text-xs font-semibold text-[var(--heading)]">Clear all history?</p>
                                <p className="text-[10px] text-[var(--text-3)]">This cannot be undone.</p>
                              </div>
                            </div>
                            <p className="text-[11px] text-[var(--text-3)] mb-3">
                              All {jobs.length} analysis jobs and their reports will be permanently deleted.
                            </p>
                            <div className="flex gap-2">
                              <button
                                onClick={() => clearMutation.mutate()}
                                disabled={clearMutation.isPending}
                                className="flex-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition disabled:opacity-50"
                              >
                                {clearMutation.isPending ? "Deleting..." : "Delete All"}
                              </button>
                              <button
                                onClick={() => setShowClearConfirm(false)}
                                className="flex-1 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--heading)] transition"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                <div className="relative">
                  <svg className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" x2="16.65" y1="21" y2="16.65" />
                  </svg>
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-[var(--surface-2)] border border-[var(--border)] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[var(--text-2)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)] w-52"
                    placeholder="Search history..."
                    type="text"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 mt-5 overflow-x-auto pb-1 text-xs">
              {categories.map((tab) => {
                const active = selectedTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => setSelectedTab(tab)}
                    className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-medium transition shrink-0 cursor-pointer ${
                      active
                        ? "bg-[var(--surface-3)] text-[var(--cyan)] border border-[var(--cyan)]/40 shadow-sm"
                        : "bg-[var(--surface-2)] text-[var(--text-3)] border border-[var(--border)] hover:text-[var(--text)]"
                    }`}
                  >
                    <span>{tab}</span>
                    <span className={`ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] ${active ? "bg-cyan-500/20 text-[var(--cyan)] font-semibold" : "bg-[var(--surface-2)] text-[var(--text-2)]"}`}>
                      {tabCounts[tab] ?? 0}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Select All Header */}
          {filteredItems.length > 0 && (
            <div className="px-5 py-2 border-b border-[var(--border)] flex items-center gap-3 text-[11px] text-[var(--text-3)]">
              <input
                type="checkbox"
                checked={allVisibleChecked}
                onChange={toggleAll}
                className="w-4 h-4 rounded bg-[var(--surface)] border-[var(--border)] text-[var(--cyan)] cursor-pointer accent-[var(--cyan)]"
              />
              <span className="font-medium">
                {allVisibleChecked ? "Deselect all" : `Select all (${filteredItems.length})`}
              </span>
            </div>
          )}

          <motion.div variants={stagger} initial="hidden" animate="show" className="flex-1 overflow-y-auto p-5 space-y-2.5">
            {isLoading && jobs.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <span className="text-xs text-[var(--text-3)]">Loading analyses...</span>
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-xs text-[var(--text-3)]">No analyses found</p>
                <p className="text-[10px] text-[var(--text-4)] mt-1">Run an analysis to see results here</p>
              </div>
            ) : (
              filteredItems.map((item) => {
                const isSelected = activeId === item.id;
                const isChecked = !!selectedChecks[item.id];
                const taskInfo = describeTask(item.task);
                const status = describeJobStatus(item.status);
                return (
                  <motion.div key={item.id} variants={rowVariant}>
                    <SpotlightCard
                      spotlightColor={isSelected ? "rgba(0,199,217,0.06)" : "rgba(0,199,217,0.05)"}
                      onClick={() => setSelectedId(item.id)}
                      className={`relative flex items-center justify-between p-3.5 rounded-xl transition-all duration-150 cursor-pointer ${
                        isSelected
                          ? "bg-[var(--surface)] border-2 border-[var(--cyan)] shadow-[0_0_20px_rgba(0,229,255,0.12)]"
                          : "bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--border-strong)]"
                      }`}
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onClick={(e) => toggleCheck(item.id, e)}
                          onChange={() => {}}
                          className="w-4 h-4 rounded bg-[var(--surface)] border-[var(--cyan)] text-[var(--cyan)] cursor-pointer"
                        />

                        <div className="w-28 h-14 rounded-lg overflow-hidden border border-[var(--border)] shrink-0 relative shadow-inner bg-[var(--surface-2)] flex">
                          {["bi_temporal_change", "bi_temporal_change_vqa"].includes(item.task) ? (
                            <>
                              <img
                                src={api.visualizationUrl(item.id, "temporal_image_a")}
                                alt=""
                                className="w-1/2 h-full object-cover border-r border-[var(--border)]"
                                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                              />
                              <img
                                src={api.visualizationUrl(item.id, "temporal_image_b")}
                                alt=""
                                className="w-1/2 h-full object-cover"
                                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                              />
                            </>
                          ) : (
                            <img
                              src={api.visualizationUrl(item.id, "true_color")}
                              alt=""
                              className="w-full h-full object-cover"
                              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                            />
                          )}
                          <svg className="w-5 h-5 text-[var(--text-4)] hidden absolute inset-0 m-auto" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                            <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>

                        <div className="min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-0.5 text-[10px] font-medium rounded bg-[var(--cyan-glow)] border border-[var(--cyan)]/30 text-[var(--cyan)]">
                              {taskInfo.label}
                            </span>
                            <h3 className="text-sm font-semibold text-[var(--heading)] truncate">{item.query}</h3>
                          </div>
                          <div className="flex items-center gap-3 mt-2 text-[11px] text-[var(--text-3)]">
                            <span className="flex items-center gap-1.5">
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <rect height="18" rx="2" ry="2" width="18" x="3" y="4" />
                                <line x1="16" x2="16" y1="2" y2="6" />
                                <line x1="8" x2="8" y1="2" y2="6" />
                                <line x1="3" x2="21" y1="10" y2="10" />
                              </svg>
                              {formatTimestamp(item.created_at)}
                            </span>
                            <span className="font-mono text-[10px] text-[var(--text-4)]">{item.id.slice(0, 8)}...</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-5 shrink-0 pl-4">
                        <div className="flex items-center gap-3">
                          <div className="flex flex-col items-end">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${jobStatusPillClasses(item.status)}`}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${jobStatusDotClasses(item.status)} ${status.active ? "animate-ping" : ""}`}
                              />
                              {status.label}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 text-[var(--text-3)]">
                          <Link href={`/analysis/${item.id}`} onClick={(e) => e.stopPropagation()} className="p-1.5 hover:text-[var(--heading)] rounded hover:bg-[var(--surface-hover)] transition" title="View">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                              <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                            </svg>
                          </Link>
                          <a href={api.downloadUrl(item.id)} onClick={(e) => e.stopPropagation()} className="p-1.5 hover:text-[var(--heading)] rounded hover:bg-[var(--surface-hover)] transition" title="Download">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                            </svg>
                          </a>
                        </div>
                      </div>
                    </SpotlightCard>
                  </motion.div>
                );
              })
            )}
          </motion.div>
        </main>

        {/* Right Details Drawer */}
        <aside className="w-full lg:w-[380px] max-h-[60vh] lg:max-h-none border-t lg:border-t-0 lg:border-l border-[var(--border)] bg-[var(--surface)] flex flex-col justify-between overflow-y-auto shrink-0 select-none">
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
              <span className="flex items-center gap-1.5 text-xs text-[var(--text-2)] font-medium">
                <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
                <span>Analysis Details</span>
              </span>
              <span
                className={`inline-flex items-center gap-1 text-[10px] font-medium px-2.5 py-0.5 rounded-full border ${jobStatusPillClasses(displayStatus)}`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${jobStatusDotClasses(displayStatus)} ${statusInfo.active ? "animate-ping" : ""}`}
                />
                {statusInfo.label}
              </span>
            </div>

            {/* Visualization Preview */}
            {result && activeId && (
              <div
                className="relative h-64 rounded-xl border border-[var(--border)] overflow-hidden shadow-lg cursor-ew-resize select-none"
                onMouseMove={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
                  setSliderPos(pct);
                }}
              >
                {["bi_temporal_change", "bi_temporal_change_vqa"].includes(result.task) ? (
                  <>
                    {/* Base image */}
                    <img
                      src={api.visualizationUrl(activeId, "temporal_image_a")}
                      alt="Before"
                      className="absolute inset-0 w-full h-full object-cover"
                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                    />
                    {/* Overlay image — clipped */}
                    <div
                      className="absolute inset-0 overflow-hidden"
                      style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
                    >
                      <img
                        src={api.visualizationUrl(activeId, "temporal_image_b")}
                        alt="After"
                        className="absolute inset-0 w-full h-full object-cover"
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                    {/* Divider */}
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-white/80 shadow-[0_0_8px_rgba(255,255,255,0.5)] z-10 pointer-events-none"
                      style={{ left: `${sliderPos}%` }}
                    />
                    {/* Labels */}
                    <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] text-[var(--heading)] font-medium border border-[var(--border)] z-10">
                      Before
                    </div>
                    <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] text-[var(--heading)] font-medium border border-[var(--border)] z-10">
                      After
                    </div>
                  </>
                ) : (
                  <img
                    src={api.visualizationUrl(activeId, "true_color")}
                    alt="Analysis visualization"
                    className="w-full h-full object-cover"
                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                  />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-[var(--surface)]/80 to-transparent pointer-events-none" />
                <div className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/40 backdrop-blur-md z-10">
                  {taskLabel(result.task)}
                </div>
              </div>
            )}

            {/* Details */}
            <div>
              <h2 className="text-base font-bold text-[var(--heading)]">
                {result?.query || jobs.find((j) => j.id === activeId)?.query || "Analysis"}
              </h2>
              <p className="text-[11px] text-[var(--text-3)] mt-0.5">
                {formatTimestamp(result?.job_id ? (jobs.find((j) => j.id === activeId)?.created_at || "") : "")}
              </p>
              {result?.answer && (
                <p className="text-xs text-[var(--text-2)] mt-2 leading-relaxed">{result.answer}</p>
              )}
              {result?.models_used && result.models_used.length > 0 && (
                <div className="flex items-center gap-1.5 mt-2.5">
                  {result.models_used.map((m) => (
                    <span key={m} className="px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] text-[10px] text-[var(--text-2)]">
                      {m}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Results Summary */}
            {displayConfidence != null && (
              <motion.div variants={fadeUp} initial="hidden" animate="show" className="pt-2 border-t border-[var(--border)]">
                <h4 className="text-xs font-semibold text-[var(--text-2)] mb-2.5">Results Summary</h4>
                <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="relative w-10 h-10 flex items-center justify-center">
                        <svg className="w-10 h-10 transform -rotate-90" viewBox="0 0 36 36">
                          <path className="text-[var(--heading)]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3.5" />
                          <path className="text-[var(--cyan)]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${displayConfidence}, 100`} strokeLinecap="round" strokeWidth="3.5" />
                        </svg>
                        <span className="absolute text-[11px] font-bold text-[var(--heading)]">{displayConfidence}%</span>
                      </div>
                      <span className="text-xs text-[var(--text-2)] font-medium">Confidence</span>
                    </div>
                  </div>

                  {/* Spatial metrics */}
                  {result?.evidence?.spatial?.statistics && (
                    <div className="grid grid-cols-3 gap-2 pt-1">
                      <div className="bg-[var(--surface-2)] border border-[var(--border)] p-2 rounded-lg text-center">
                        <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--text-3)]">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Changed
                        </div>
                        <div className="text-xs font-bold text-red-400 mt-1">
                          {result.evidence.spatial.statistics.changed_pixels?.toLocaleString() || "—"}
                        </div>
                      </div>
                      <div className="bg-[var(--surface-2)] border border-[var(--border)] p-2 rounded-lg text-center">
                        <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--text-3)]">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-400" /> Regions
                        </div>
                        <div className="text-xs font-bold text-[var(--primary)] mt-1">
                          {result.evidence.spatial.statistics.region_count || "—"}
                        </div>
                      </div>
                      <div className="bg-[var(--surface-2)] border border-[var(--border)] p-2 rounded-lg text-center">
                        <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--text-3)]">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Area
                        </div>
                        <div className="text-xs font-bold text-[var(--green)] mt-1">
                          {result.evidence.spatial.statistics.estimated_area_sq_km
                            ? `${result.evidence.spatial.statistics.estimated_area_sq_km.toFixed(2)} km²`
                            : result.evidence.spatial.statistics.estimated_area_sq_m
                              ? `${(result.evidence.spatial.statistics.estimated_area_sq_m / 1000000).toFixed(2)} km²`
                              : "—"}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Execution Trace */}
            {result?.execution_trace && result.execution_trace.length > 0 && (
              <div className="pt-2 border-t border-[var(--border)]">
                <h4 className="text-xs font-semibold text-[var(--text-2)] mb-2">Execution Trace</h4>
                <div className="space-y-1.5">
                  {result.execution_trace.map((step, i) => (
                    <div key={i} className="flex items-center justify-between py-1 px-2 rounded bg-[var(--surface-2)] border border-[var(--border)]">
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          step.status === "success" ? "bg-emerald-400" :
                          step.status === "error" ? "bg-red-400" :
                          step.status === "running" ? "bg-amber-400 animate-pulse" : "bg-[var(--text-4)]"
                        }`} />
                        <span className="text-[10px] text-[var(--text-2)] font-mono">{step.step}</span>
                      </div>
                      {step.model && <span className="text-[9px] text-[var(--text-4)] font-mono">{step.model}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="p-4 border-t border-[var(--border)] space-y-2 bg-[var(--canvas)]">
            <Link
              href="/analysis"
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-[var(--cyan)] hover:bg-cyan-300 text-[var(--canvas)] font-semibold text-xs transition shadow-[0_0_15px_rgba(0,229,255,0.3)]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              <span>New Analysis</span>
            </Link>
            {activeId && (
              <div className="flex items-center gap-2">
                <a
                  href={api.downloadUrl(activeId)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] text-[var(--text-2)] text-xs font-medium transition"
                >
                  <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                  <span>Download Results</span>
                </a>
                <a
                  href={api.reportUrl(activeId)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] text-[var(--text-3)] hover:text-[var(--heading)] transition"
                  title="View Report"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                </a>
              </div>
            )}
          </div>
        </aside>
      </div>
    </motion.div>
  );
}
