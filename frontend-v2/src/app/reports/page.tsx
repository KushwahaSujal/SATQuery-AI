"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Filter = "All" | "Completed" | "In Progress" | "Failed";

const TYPE_COLORS: Record<string, string> = {
  change: "bg-purple-950/70 text-purple-300 border-purple-800/40",
  optical: "bg-blue-950/70 text-blue-300 border-blue-800/40",
  sar: "bg-indigo-950/70 text-indigo-300 border-indigo-800/40",
  vqa: "bg-teal-950/70 text-teal-300 border-teal-800/40",
  fusion: "bg-sky-950/70 text-sky-300 border-sky-800/40",
};

function getTypeStyle(task: string) {
  const t = (task || "").toLowerCase();
  if (t.includes("change") || t.includes("temporal")) return TYPE_COLORS.change;
  if (t.includes("sar")) return TYPE_COLORS.sar;
  if (t.includes("vqa") || t.includes("caption")) return TYPE_COLORS.vqa;
  if (t.includes("fusion") || t.includes("optical_sar")) return TYPE_COLORS.fusion;
  return TYPE_COLORS.optical;
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
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-cyan-950/60 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mt-0.5 shadow-[0_0_15px_rgba(6,182,212,0.15)]">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Reports</h1>
              <p className="text-xs text-slate-400 mt-0.5">View, manage and download your analysis reports.</p>
            </div>
          </div>
          <button className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 text-white font-medium text-xs shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Generate Report
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 border-b border-[#15243e] pb-3">
          {(["All", "Completed", "In Progress", "Failed"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition ${
                filter === f ? "bg-cyan-950/70 border border-cyan-500/40 text-cyan-400 font-semibold" : "text-slate-400 hover:text-slate-200 hover:bg-[#0d172c]"
              }`}
            >
              <span>{f}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${filter === f ? "bg-cyan-500/20 text-cyan-300" : "bg-[#16233b] text-slate-400"}`}>{counts[f]}</span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <svg className="absolute left-3 top-2 w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <input value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-[#0a1224] border border-[#162542] rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500/40" placeholder="Search reports..." />
        </div>

        {/* Table */}
        <div className="border border-[#15243e] rounded-2xl bg-[#091122]/70 backdrop-blur overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#15243e] text-slate-400 text-[11px] font-semibold tracking-wider bg-[#0c162b]/50">
                  <th className="py-3 px-4">Report</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Created</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#132039] text-slate-300">
                {isLoading ? (
                  <tr><td colSpan={5} className="py-8 text-center text-slate-400">Loading reports...</td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={5} className="py-8 text-center text-slate-400">No reports found.</td></tr>
                ) : (
                  filtered.map((job) => {
                    const jobStatus = job.status === "COMPLETED" ? "completed" : job.status === "FAILED" ? "failed" : job.status === "RUNNING" ? "processing" : "queued";
                    return (
                      <tr key={job.job_id} className="hover:bg-[#101d36]/50 transition-colors cursor-pointer">
                        <td className="py-3 px-4">
                          <div>
                            <div className="font-semibold text-white text-xs">{job.query || "Geospatial analysis"}</div>
                            <div className="text-[11px] text-slate-400">{job.task?.replace(/_/g, " ")}</div>
                          </div>
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-medium border ${getTypeStyle(job.task || "")}`}>{job.task?.replace(/_/g, " ")}</span>
                        </td>
                        <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                          {job.created_at ? new Date(job.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap"><StatusBadge status={jobStatus} /></td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <button className="p-1.5 hover:text-cyan-400 hover:bg-[#152545] rounded-lg transition-colors text-slate-400">
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
        <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
          <div>Showing <span className="text-slate-200 font-medium">{filtered.length}</span> of <span className="text-slate-200 font-medium">{jobs.length}</span> reports</div>
        </div>
      </main>

      {/* Right Detail */}
      <aside className="w-96 shrink-0 border-l border-[#15243e] bg-[#070e1c] overflow-y-auto p-5 flex flex-col space-y-5">
        <div className="text-center py-8 text-slate-400 text-sm">
          <p>Select a report to view details.</p>
        </div>
      </aside>
    </div>
  );
}
