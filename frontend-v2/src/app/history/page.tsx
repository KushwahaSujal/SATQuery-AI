"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ConfidenceRing } from "@/components/ui/ConfidenceRing";
import { StatusBadge } from "@/components/ui/StatusBadge";

type Filter = "ALL" | "Single Image" | "Change Analysis" | "Optical + SAR" | "Bi-temporal";

export default function HistoryPage() {
  const [filter, setFilter] = useState<Filter>("ALL");
  const [search, setSearch] = useState("");

  const { data: jobs = [], isLoading } = useQuery<{ job_id: string; task?: string; query?: string; status?: string; created_at?: string; confidence?: number }[]>({
    queryKey: ["jobs"],
    queryFn: async () => {
      const raw = await api.listJobs();
      return raw.map((item: Record<string, unknown>) => ({
        job_id: (item.job_id || item.id || "") as string,
        task: (item.task as string) || "ANALYSIS",
        query: (item.query as string) || "Geospatial query",
        status: (item.status as string) || "COMPLETED",
        created_at: (item.created_at as string) || new Date().toISOString(),
        confidence: item.confidence as number | undefined,
      }));
    },
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });

  const filtered = jobs.filter((j) => {
    if (filter !== "ALL" && j.task !== filter) return false;
    if (search && !j.query?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    ALL: jobs.length,
    "Single Image": jobs.filter(j => j.task === "single_image_vqa" || j.task === "single_image_caption").length,
    "Change Analysis": jobs.filter(j => j.task === "bi_temporal_change" || j.task === "bi_temporal_change_vqa").length,
    "Optical + SAR": jobs.filter(j => j.task === "optical_sar_analysis").length,
    "Bi-temporal": jobs.filter(j => j.task?.includes("temporal")).length,
  };

  return (
    <div className="p-6 space-y-5" style={{ background: "var(--canvas)" }}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--heading)" }}>Analysis History</h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-2)" }}>View and manage your past analyses. Revisit results, download reports, or continue where you left off.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <svg className="absolute left-3 top-2.5 w-3.5 h-3.5" style={{ color: "var(--text-2)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent rounded-lg pl-8 pr-3 py-1.5 text-xs focus:outline-none w-52"
              style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--heading)" }}
              placeholder="Search history..."
            />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {(["ALL", "Single Image", "Change Analysis", "Optical + SAR", "Bi-temporal"] as Filter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-medium text-xs shrink-0 transition"
            style={filter === f ? {
              background: "var(--sidebar-active-bg)",
              color: "var(--cyan)",
              border: "1px solid var(--cyan)",
            } : {
              background: "var(--surface-2)",
              color: "var(--text-2)",
              border: "1px solid var(--border)",
            }}
          >
            <span>{f}</span>
            <span
              className="ml-0.5 px-1.5 py-0.2 rounded-full text-[10px]"
              style={filter === f ? {
                background: "var(--cyan-glow)",
                color: "var(--cyan)",
                fontWeight: 600,
              } : {
                background: "var(--surface-3)",
                color: "var(--text)",
              }}
            >{counts[f]}</span>
          </button>
        ))}
      </div>

      {/* History List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <span className="animate-spin-smooth w-3 h-3 border-2 rounded-full" style={{ borderColor: "var(--border)", borderTopColor: "var(--cyan)" }} />
            <span className="ml-2 text-xs" style={{ color: "var(--text-2)" }}>Loading history...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-sm" style={{ color: "var(--text-2)" }}>No analyses found.</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-3)" }}>Run an analysis to see history here.</p>
          </div>
        ) : (
          filtered.map((job, i) => {
            const isVideo = job.task?.includes("video");
            const conf = job.confidence != null ? Math.round(job.confidence * 100) : null;
            const jobStatus = job.status === "COMPLETED" ? "completed" as const : job.status === "FAILED" ? "failed" as const : "processing" as const;

            return (
              <Link
                key={job.job_id}
                href={isVideo ? `/analysis/${job.job_id}` : `/analysis/${job.job_id}`}
                className="relative flex items-center justify-between p-3.5 rounded-xl transition-all block"
                style={i === 0 ? {
                  background: "var(--surface-2)",
                  border: "2px solid var(--cyan)",
                  boxShadow: "0 0 20px var(--cyan-glow)",
                } : {
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                }}
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-24 h-14 rounded-lg overflow-hidden shrink-0" style={{ border: "1px solid var(--border)", background: "var(--surface-3)" }} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="px-2 py-0.5 text-[10px] font-medium rounded"
                        style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}
                      >{job.task?.replace(/_/g, " ") || "Analysis"}</span>
                      <h3 className="text-sm font-semibold truncate" style={{ color: "var(--heading)" }}>{job.query || "Geospatial query"}</h3>
                    </div>
                    <div className="flex items-center gap-3 mt-2 text-[11px]" style={{ color: "var(--text-2)" }}>
                      <span>{job.created_at ? new Date(job.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "\u2014"}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-5 shrink-0 pl-4">
                  {conf != null && (
                    <div className="flex items-center gap-3">
                      <ConfidenceRing value={conf} status={jobStatus} />
                      <div className="flex flex-col">
                        <span className="text-[10px]" style={{ color: "var(--text-2)" }}>Confidence</span>
                        <StatusBadge status={jobStatus} className="mt-0.5" />
                      </div>
                    </div>
                  )}
                </div>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
