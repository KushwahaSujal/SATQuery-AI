"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Filter = "ALL" | "RUNNING" | "COMPLETED" | "FAILED";

const STATUS_CONFIG: Record<string, { pill: string; dot: string; label: string }> = {
  COMPLETED: { pill: "status-pill-green",  dot: "status-dot-green",  label: "Completed" },
  RUNNING:   { pill: "status-pill-amber",  dot: "status-dot-amber animate-pulse-dot",  label: "Running"   },
  FAILED:    { pill: "status-pill-red",    dot: "status-dot-red",    label: "Failed"    },
  PENDING:   { pill: "status-pill-muted",  dot: "status-dot-muted",  label: "Pending"   },
};

const TASK_COLORS: Record<string, string> = {
  bi_temporal_change: "var(--accent-text)",
  bi_temporal_change_vqa: "var(--cyan)",
  single_image_vqa: "var(--cyan)",
  single_image_grounding: "var(--purple)",
  single_image_caption: "var(--amber)",
  video_grounding_tracking: "var(--red)",
  ANALYSIS: "var(--t3)",
  CHANGE: "var(--accent-text)",
  VQA: "var(--cyan)",
  GROUNDING: "var(--purple)",
  VIDEO: "var(--red)",
};

export default function JobsPage() {
  const [filter, setFilter] = useState<Filter>("ALL");
  const queryClient = useQueryClient();

  // Fetch jobs with React Query caching
  const { data: jobs = [], isLoading } = useQuery<{ job_id: string; task?: string; query?: string; status?: string; created_at?: string }[]>({
    queryKey: ["jobs"],
    queryFn: async () => {
      const raw = await api.listJobs();
      return raw.map((item: Record<string, unknown>) => ({
        job_id: (item.job_id || item.id || "") as string,
        task: (item.task as string) || "ANALYSIS",
        query: (item.query as string) || "Geospatial query",
        status: (item.status as string) || "COMPLETED",
        created_at: (item.created_at as string) || new Date().toISOString(),
      }));
    },
    staleTime: 60_000,      // Cache for 1 minute
    gcTime: 5 * 60_000,     // Keep in cache for 5 minutes
    refetchOnWindowFocus: false,
  });

  const clearMutation = useMutation({
    mutationFn: () => api.clearJobs(),
    onSuccess: () => {
      queryClient.setQueryData(["jobs"], []);
    },
  });

  const filtered = filter === "ALL" ? jobs : jobs.filter(j => j.status === filter);

  const counts = {
    ALL:       jobs.length,
    RUNNING:   jobs.filter(j => j.status === "RUNNING").length,
    COMPLETED: jobs.filter(j => j.status === "COMPLETED").length,
    FAILED:    jobs.filter(j => j.status === "FAILED").length,
  };

  return (
    <div
      className="animate-fade-in"
      style={{
        border: "1px solid var(--b0)", borderRadius: 6, overflow: "hidden",
        background: "var(--s1)",
        display: "flex", flexDirection: "column",
        height: "calc(100vh - 64px)",
      }}
    >
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 16px", height: 48,
        borderBottom: "1px solid var(--b0)",
        background: "var(--s1)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <span style={{ fontSize: 13, fontWeight: 500, color: "var(--t0)" }}>Job History</span>
          <span style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: 10, color: "var(--t3)",
            background: "var(--s2)", border: "1px solid var(--b1)",
            borderRadius: 3, padding: "1px 6px",
          }}>
            {jobs.length} total
          </span>
          {jobs.length > 0 && (
            <button
              onClick={() => clearMutation.mutate()}
              disabled={clearMutation.isPending}
              className="font-mono-data text-[10px] px-2 py-1 rounded border border-[var(--b1)] bg-transparent text-[var(--red)] cursor-pointer hover:bg-[var(--red-dim)] transition-colors disabled:opacity-50"
            >
              {clearMutation.isPending ? "Clearing..." : "Clear All"}
            </button>
          )}
        </div>

        {/* Filter chips */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {(["ALL", "RUNNING", "COMPLETED", "FAILED"] as Filter[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "3px 8px", borderRadius: 4,
                background: filter === f ? "var(--s3)" : "transparent",
                border: `1px solid ${filter === f ? "var(--b3)" : "transparent"}`,
                cursor: "pointer", transition: "all 0.12s",
              }}
            >
              <span className="font-mono-data" style={{
                fontSize: 10, fontWeight: filter === f ? 600 : 400,
                color: filter === f ? "var(--t0)" : "var(--t3)",
                letterSpacing: "0.04em",
              }}>
                {f}
              </span>
              <span className="font-mono-data" style={{
                fontSize: 9, color: filter === f ? "var(--t2)" : "var(--t4)",
              }}>
                {counts[f]}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ position: "sticky", top: 0, background: "var(--s1)", zIndex: 1 }}>
              {["Job ID", "Task", "Query", "Status", "Created", ""].map((col, i) => (
                <th
                  key={col + i}
                  style={{
                    padding: "8px 14px",
                    textAlign: i === 5 ? "right" : "left",
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: 9, fontWeight: 600,
                    letterSpacing: "0.08em", textTransform: "uppercase",
                    color: "var(--t4)",
                    borderBottom: "1px solid var(--b0)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((job, rowIdx) => {
              const status = STATUS_CONFIG[job.status ?? "PENDING"] ?? STATUS_CONFIG.PENDING;
              const taskColor = TASK_COLORS[job.task ?? "ANALYSIS"] ?? "var(--t3)";

              return (
                <tr
                  key={job.job_id}
                  className="animate-fade-in"
                  style={{
                    background: rowIdx % 2 === 0 ? "var(--s1)" : "var(--s0)",
                    borderBottom: "1px solid var(--b0)",
                    transition: "background 0.1s",
                    cursor: "default",
                  }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLElement).style.background = "var(--s2)";
                    (e.currentTarget as HTMLElement).style.borderLeft = "2px solid var(--accent)";
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.background = rowIdx % 2 === 0 ? "var(--s1)" : "var(--s0)";
                    (e.currentTarget as HTMLElement).style.borderLeft = "";
                  }}
                >
                  {/* Job ID */}
                  <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                    <span className="font-mono-data" style={{ fontSize: 11, color: "var(--accent-text)" }}>
                      {job.job_id}
                    </span>
                  </td>

                  {/* Task */}
                  <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                    <span className="font-mono-data" style={{
                      fontSize: 9, fontWeight: 700,
                      letterSpacing: "0.07em", textTransform: "uppercase",
                      color: taskColor,
                      background: "var(--s0)",
                      border: "1px solid var(--b1)",
                      borderRadius: 3, padding: "2px 6px",
                    }}>
                      {job.task}
                    </span>
                  </td>

                  {/* Query */}
                  <td style={{ padding: "10px 14px", maxWidth: 320 }}>
                    <span
                      style={{ fontSize: 12, color: "var(--t2)", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      title={job.query}
                    >
                      {job.query}
                    </span>
                  </td>

                  {/* Status */}
                  <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                    <span className={`status-pill ${status.pill}`}>
                      <span className={`status-dot ${status.dot}`} />
                      {status.label}
                    </span>
                  </td>

                  {/* Created */}
                  <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                    <span className="font-mono-data" style={{ fontSize: 10, color: "var(--t3)" }}>
                      {job.created_at ? new Date(job.created_at).toLocaleString("en-US", { dateStyle: "short", timeStyle: "short" }) : "—"}
                    </span>
                  </td>

                  {/* Actions */}
                  <td style={{ padding: "10px 14px", whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4 }}>
                      <Link
                        href={job.task === "VIDEO" ? `/video/${job.job_id}` : `/analysis/${job.job_id}`}
                        style={{
                          display: "flex", alignItems: "center", gap: 5,
                          padding: "4px 8px", borderRadius: 4,
                          border: "1px solid var(--b2)",
                          background: "var(--s2)",
                          color: "var(--t2)",
                          fontFamily: "var(--font-geist-mono), monospace",
                          fontSize: 10, textDecoration: "none",
                          transition: "all 0.1s",
                        }}
                        onMouseEnter={e => {
                          (e.currentTarget as HTMLElement).style.background = "var(--s3)";
                          (e.currentTarget as HTMLElement).style.color = "var(--t0)";
                          (e.currentTarget as HTMLElement).style.borderColor = "var(--b3)";
                        }}
                        onMouseLeave={e => {
                          (e.currentTarget as HTMLElement).style.background = "var(--s2)";
                          (e.currentTarget as HTMLElement).style.color = "var(--t2)";
                          (e.currentTarget as HTMLElement).style.borderColor = "var(--b2)";
                        }}
                      >
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                          <polyline points="15 3 21 3 21 9"/>
                          <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        Open
                      </Link>

                      {job.task !== "VIDEO" && (
                        <Link
                          href={`/visual-analytics/${job.job_id}`}
                          style={{
                            display: "flex", alignItems: "center", gap: 5,
                            padding: "4px 8px", borderRadius: 4,
                            border: "1px solid transparent",
                            color: "var(--t4)",
                            fontFamily: "var(--font-geist-mono), monospace",
                            fontSize: 10, textDecoration: "none",
                            transition: "all 0.1s",
                          }}
                          onMouseEnter={e => {
                            (e.currentTarget as HTMLElement).style.color = "var(--t2)";
                            (e.currentTarget as HTMLElement).style.borderColor = "var(--b1)";
                          }}
                          onMouseLeave={e => {
                            (e.currentTarget as HTMLElement).style.color = "var(--t4)";
                            (e.currentTarget as HTMLElement).style.borderColor = "transparent";
                          }}
                        >
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="20" x2="18" y2="10"/>
                            <line x1="12" y1="20" x2="12" y2="4"/>
                            <line x1="6" y1="20" x2="6" y2="14"/>
                          </svg>
                          Analytics
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center gap-2">
              <span className="animate-spin-smooth w-3 h-3 border-2 border-[var(--accent-dim)] border-t-[var(--accent)] rounded-full" />
              <span className="font-mono-data text-[11px] text-[var(--t3)]">Loading jobs...</span>
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "48px 20px", textAlign: "center" }}>
            <p className="font-mono-data" style={{ fontSize: 11, color: "var(--t3)" }}>
              {filter !== "ALL" ? `No ${filter.toLowerCase()} jobs` : "No jobs yet"}
            </p>
            <p className="font-mono-data text-[9px] text-[var(--t4)] mt-1">
              Run an analysis to see jobs here
            </p>
          </div>
        ) : null}
      </div>

      {/* Footer */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "6px 16px",
        borderTop: "1px solid var(--b0)",
        flexShrink: 0,
      }}>
        <span className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)" }}>
          local store · GET /api/jobs for live data
        </span>
        <span className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)" }}>
          {filtered.length} of {jobs.length} jobs
        </span>
      </div>
    </div>
  );
}
