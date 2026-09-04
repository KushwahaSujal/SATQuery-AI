"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useJob, useAnalysisResult } from "@/hooks/useSystem";
import ExecutionTrace from "@/components/trace/ExecutionTrace";
import { api } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";

export default function AnalysisWorkspacePage() {
  const { jobId } = useParams<{ jobId: string }>();

  const job = useJob(jobId);
  const status = job.data?.status ?? "COMPLETED";
  const result = useAnalysisResult(jobId, status === "COMPLETED");

  const data: AnalysisResult = result.data ?? {
    job_id: jobId,
    task: (job.data?.task as any) || "ANALYSIS",
    query: job.data?.query || "Satellite intelligence spatial query",
    answer:
      status === "RUNNING"
        ? "Processing spatial analysis pipeline in backend..."
        : "Analysis execution completed. View Visual Analytics to inspect derive layers.",
    confidence: 0.0,
    metrics: {},
    evidence: [],
    models_used: job.data?.models_used || [],
    execution_trace: job.data?.execution_steps || [],
  };

  const steps = job.data?.execution_steps || data.execution_trace || data.trace || [];
  const overlayUrl = api.visualizationUrl(jobId, "change_overlay");

  return (
    <div className="flex flex-col gap-0 border border-[#1a1a1a] rounded-lg overflow-hidden animate-fade-in">
      {/* Breadcrumb / header strip */}
      <div className="flex items-center gap-3 px-4 h-10 border-b border-[#1a1a1a] bg-[#0a0a0a]">
        <Link href="/" className="font-mono-data text-[11px] text-[#333] hover:text-[#737373] transition-colors">
          ← command center
        </Link>
        <span className="text-[#222]">/</span>
        <span className="font-mono-data text-[11px] text-[#404040]">{jobId}</span>
        <span className="text-[#222]">/</span>
        <span className="font-mono-data text-[11px] text-[#737373]">analysis</span>
        <div className="flex-1" />

        <span
          className={[
            "font-mono-data text-[10px] px-2 py-0.5 rounded",
            status === "COMPLETED"
              ? "text-[#4ade80] bg-[#4ade80]/8"
              : status === "FAILED"
              ? "text-[#f87171] bg-[#f87171]/8"
              : "text-[#fbbf24] bg-[#fbbf24]/8",
          ].join(" ")}
        >
          {status}
        </span>

        <Link
          href={`/visual-analytics/${jobId}`}
          className="font-mono-data text-[11px] text-[#404040] border border-[#222] hover:border-[#333] hover:text-[#737373] px-2.5 py-1 rounded transition-colors"
        >
          Visual Analytics →
        </Link>
      </div>

      {/* Query */}
      <div className="px-4 py-3 border-b border-[#1a1a1a]">
        <div className="flex items-start gap-2">
          <span className="font-mono-data text-[10px] text-[#333] mt-0.5 shrink-0">QUERY</span>
          <p className="font-mono-data text-[12px] text-[#737373]">"{data.query}"</p>
        </div>
        <div className="flex items-center gap-3 mt-1.5 ml-14">
          <span className="font-mono-data text-[10px] text-[#2a2a2a]">routing: agent intent controller</span>
          <span className="font-mono-data text-[10px] text-[#404040]">task: {data.task}</span>
        </div>
      </div>

      {/* 2-column workspace */}
      <div className="flex divide-x divide-[#1a1a1a] min-h-[520px]">
        {/* Spatial canvas */}
        <div className="flex-1 flex flex-col">
          <div className="panel-header">
            <span className="panel-label">Spatial Analysis · Primary Derived Layer</span>
            <span className="font-mono-data text-[10px] text-[#333]">JOB #{jobId}</span>
          </div>
          <div className="flex-1 bg-[#080808] relative flex items-center justify-center overflow-hidden">
            {/* Overlay preview or subtle grid */}
            {overlayUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={overlayUrl}
                alt="Layer Preview"
                className="max-w-full max-h-full object-contain"
                onError={(e) => {
                  (e.currentTarget as HTMLElement).style.display = "none";
                }}
              />
            ) : null}

            <div className="absolute bottom-4 left-4 bg-[#0a0a0a]/90 border border-[#222] px-3 py-2 rounded font-mono-data text-[10px] text-[#737373]">
              <div>Target Job ID: {jobId}</div>
              <div>Status: {status}</div>
            </div>
          </div>
        </div>

        {/* Right detail column */}
        <div className="w-[300px] shrink-0 divide-y divide-[#1a1a1a] flex flex-col">
          {/* Answer */}
          <div className="p-4">
            <span className="panel-label block mb-2">Answer</span>
            <p className="text-[12px] text-[#d4d4d4] leading-relaxed">{data.answer}</p>
          </div>

          {/* Metrics grid */}
          <div className="grid grid-cols-2 divide-x divide-[#1a1a1a]">
            {[
              ["Confidence", data.confidence != null ? `${(data.confidence * 100).toFixed(1)}%` : "N/A"],
              ["Regions", String(data.metrics?.regions ?? 0)],
              ["Pixels Changed", data.metrics?.changed_pixels?.toLocaleString("en-US") ?? "0"],
              ["Area (m²)", data.metrics?.area_m2 ? `${(data.metrics.area_m2 / 1000).toFixed(1)}k m²` : "0 m²"],
            ].map(([l, v]) => (
              <div key={l} className="p-3">
                <span className="panel-label block">{l}</span>
                <span className="font-mono-data text-[13px] font-semibold text-[#fafafa] mt-0.5 block">{v}</span>
              </div>
            ))}
          </div>

          {/* Evidence */}
          <div className="p-3 flex-1">
            <span className="panel-label block mb-2">Evidence</span>
            <div className="space-y-1">
              {data.evidence && data.evidence.length > 0 ? (
                data.evidence.map((ev, i) => (
                  <div key={ev.id || i} className="flex items-center gap-2 py-1">
                    <span className="font-mono-data text-[10px] text-[#4ade80]">✓</span>
                    <span className="text-[11px] text-[#737373] flex-1">{ev.label}</span>
                    <span className="font-mono-data text-[9px] text-[#2a2a2a]">{ev.kind}</span>
                  </div>
                ))
              ) : (
                <p className="font-mono-data text-[10px] text-[#404040]">No evidence registered.</p>
              )}
            </div>
          </div>

          {/* Models */}
          <div className="p-3">
            <span className="panel-label block mb-2">Pipeline Models</span>
            <div className="space-y-1">
              {data.models_used && data.models_used.length > 0 ? (
                data.models_used.map((m) => (
                  <div key={m} className="flex items-center gap-2">
                    <span className="font-mono-data text-[10px] text-[#333]">○</span>
                    <span className="font-mono-data text-[11px] text-[#404040]">{m}</span>
                  </div>
                ))
              ) : (
                <p className="font-mono-data text-[10px] text-[#404040]">SatQuery Execution Engine</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Trace */}
      <ExecutionTrace steps={steps} />
    </div>
  );
}
