"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Filter = "All" | "Completed" | "In Progress" | "Failed";

const typeStyles: Record<string, { bg: string; color: string; border: string }> = {
  change: { bg: "var(--violet-bg)", color: "var(--violet)", border: "var(--violet)" },
  optical: { bg: "var(--primary-glow)", color: "var(--primary)", border: "var(--primary)" },
  sar: { bg: "var(--violet-bg)", color: "var(--violet)", border: "var(--violet)" },
  vqa: { bg: "var(--cyan-glow)", color: "var(--cyan)", border: "var(--cyan)" },
  fusion: { bg: "var(--water-bg)", color: "var(--water)", border: "var(--water)" },
};

function getTypeStyle(task: string) {
  const t = (task || "").toLowerCase();
  if (t.includes("change") || t.includes("temporal")) return typeStyles.change;
  if (t.includes("sar")) return typeStyles.sar;
  if (t.includes("vqa") || t.includes("caption")) return typeStyles.vqa;
  if (t.includes("fusion") || t.includes("optical_sar")) return typeStyles.fusion;
  return typeStyles.optical;
}

export default function ReportsPage() {
  const [filter, setFilter] = useState<Filter>("All");
  const [search, setSearch] = useState("");

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["reports"],
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
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });

  const filtered = jobs.filter((j) => {
    if (filter === "Completed" && j.status !== "COMPLETED") return false;
    if (filter === "In Progress" && j.status !== "RUNNING") return false;
    if (filter === "Failed" && j.status !== "FAILED") return false;
    if (search && !j.query?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    All: jobs.length,
    Completed: jobs.filter(j => j.status === "COMPLETED").length,
    "In Progress": jobs.filter(j => j.status === "RUNNING").length,
    Failed: jobs.filter(j => j.status === "FAILED").length,
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden" style={{ background: "var(--canvas)" }}>
      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center mt-0.5"
              style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--heading)" }}>Reports</h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-2)" }}>View, manage and download your analysis reports.</p>
            </div>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-xs shrink-0 transition-all"
            style={{ background: "var(--primary)", color: "#FFFFFF", boxShadow: "0 0 20px var(--primary-glow)" }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Generate Report
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 pb-3" style={{ borderBottom: "1px solid var(--border)" }}>
          {(["All", "Completed", "In Progress", "Failed"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition"
              style={filter === f ? {
                background: "var(--cyan-glow)",
                border: "1px solid var(--cyan)",
                color: "var(--cyan)",
                fontWeight: 600,
              } : {
                color: "var(--text-2)",
              }}
            >
              <span>{f}</span>
              <span
                className="text-[10px] px-1.5 py-0.2 rounded-full"
                style={filter === f ? {
                  background: "var(--cyan-glow)",
                  color: "var(--cyan)",
                } : {
                  background: "var(--surface-3)",
                  color: "var(--text-2)",
                }}
              >{counts[f]}</span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <svg className="absolute left-3 top-2 w-3.5 h-3.5" style={{ color: "var(--text-2)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl pl-9 pr-3 py-1.5 text-xs focus:outline-none"
            style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--heading)" }}
            placeholder="Search reports..."
          />
        </div>

        {/* Table */}
        <div
          className="rounded-2xl overflow-hidden backdrop-blur"
          style={{ border: "1px solid var(--border)", background: "var(--surface-2)", boxShadow: "var(--shadow-lg)" }}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-2)", background: "var(--surface-3)" }}>
                  <th className="py-3 px-4 text-[11px] font-semibold tracking-wider">Report</th>
                  <th className="py-3 px-3 text-[11px] font-semibold tracking-wider">Type</th>
                  <th className="py-3 px-3 text-[11px] font-semibold tracking-wider">Created</th>
                  <th className="py-3 px-3 text-[11px] font-semibold tracking-wider">Status</th>
                  <th className="py-3 px-4 text-[11px] font-semibold tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody style={{ color: "var(--text)" }}>
                {isLoading ? (
                  <tr><td colSpan={5} className="py-8 text-center" style={{ color: "var(--text-2)" }}>Loading reports...</td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center" style={{ color: "var(--text-2)" }}>No reports found.</td></tr>
                ) : (
                  filtered.map((job) => {
                    const jobStatus = job.status === "COMPLETED" ? "completed" : job.status === "FAILED" ? "failed" : job.status === "RUNNING" ? "processing" : "queued";
                    const ts = getTypeStyle(job.task || "");
                    return (
                      <tr key={job.job_id} className="transition-colors cursor-pointer" style={{ borderBottom: "1px solid var(--border)" }}>
                        <td className="py-3 px-4">
                          <div>
                            <div className="font-semibold text-xs" style={{ color: "var(--heading)" }}>{job.query || "Geospatial analysis"}</div>
                            <div className="text-[11px]" style={{ color: "var(--text-2)" }}>{job.task?.replace(/_/g, " ")}</div>
                          </div>
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className="px-2.5 py-0.5 rounded-full text-[10px] font-medium"
                            style={{ background: ts.bg, color: ts.color, border: `1px solid ${ts.border}` }}
                          >{job.task?.replace(/_/g, " ")}</span>
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap" style={{ color: "var(--text-2)" }}>
                          {job.created_at ? new Date(job.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "\u2014"}
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap"><StatusBadge status={jobStatus} /></td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <button className="p-1.5 rounded-lg transition-colors" style={{ color: "var(--text-2)" }}>
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between text-xs pt-1" style={{ color: "var(--text-2)" }}>
          <div>Showing <span className="font-medium" style={{ color: "var(--text)" }}>{filtered.length}</span> of <span className="font-medium" style={{ color: "var(--text)" }}>{jobs.length}</span> reports</div>
        </div>
      </main>

      {/* Right Detail */}
      <aside
        className="w-96 shrink-0 overflow-y-auto p-5 flex flex-col space-y-5"
        style={{ borderLeft: "1px solid var(--border)", background: "var(--surface)" }}
      >
        <div className="text-center py-8 text-sm" style={{ color: "var(--text-2)" }}>
          <p>Select a report to view details.</p>
        </div>
      </aside>
    </div>
  );
}
