"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useJob, useAnalysisResult } from "@/hooks/useSystem";
import ExecutionTrace from "@/components/trace/ExecutionTrace";
import { api } from "@/lib/api";
import { useConnection } from "@/lib/connection";
import type { TraceStep } from "@/lib/types";

export default function AnalysisWorkspacePage() {
  const { jobId } = useParams<{ jobId: string }>();
  // Re-renders once real localStorage connection settings replace the SSR defaults, so
  // overlayUrl/downloadUrl below pick up the key instead of staying stale after hydration.
  useConnection();

  const job = useJob(jobId);
  const status = job.data?.status ?? "UNKNOWN";
  const result = useAnalysisResult(jobId, status === "COMPLETED");

  const data = result.data;

  const rawSteps = (job.data?.execution_steps || data?.execution_trace || data?.trace || []) as Record<string, unknown>[];
  const steps = rawSteps.map((s) => ({
    step: (s.step as string) || (s.step_name as string) || (s.name as string) || "unknown",
    status: (s.status as TraceStep["status"]) || "success",
    duration_ms: typeof s.duration_ms === "number" ? s.duration_ms : typeof s.duration_seconds === "number" ? Math.round(s.duration_seconds as number * 1000) : undefined,
    details: (s.details as string) || (s.message as string),
  }));
  
  // Determine appropriate visualization based on task type
  const getVisualizationLayer = (task: string): string => {
    const taskLower = (task || "").toLowerCase();
    if (taskLower.includes("change") || taskLower.includes("temporal")) {
      return "change_overlay";
    }
    if (taskLower.includes("grounding") || taskLower.includes("detection")) {
      return "grounding_overlay";
    }
    if (taskLower.includes("segmentation") || taskLower.includes("mask")) {
      return "sam2_segmentation_overlay";
    }
    // Default to true color for VQA and other single-image tasks
    return "true_color";
  };

  // Extract metrics from evidence.spatial.statistics
  const stats = data?.evidence?.spatial?.statistics;
  const regions = stats?.region_count ?? 0;
  const changedPixels = stats?.changed_pixels ?? 0;
  const areaM2 = stats?.estimated_area_sq_m;

  const visualizationLayer = getVisualizationLayer(data?.task || "");
  const overlayUrl = api.visualizationUrl(jobId, visualizationLayer);
  
  // Show loading state
  if (job.isLoading || result.isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)] border border-[var(--b1)] rounded-lg">
        <div className="flex items-center gap-2">
          <span className="animate-spin-smooth w-3 h-3 border-2 border-[var(--accent-dim)] border-t-[var(--accent)] rounded-full" />
          <span className="font-mono-data text-[12px] text-[var(--t3)]">Loading analysis...</span>
        </div>
      </div>
    );
  }

  // Show error state
  if (!data && (job.isError || result.isError)) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)] border border-[var(--b1)] rounded-lg">
        <div className="text-center">
          <span className="font-mono-data text-[12px] text-[var(--red)] block mb-2">Failed to load analysis</span>
          <span className="font-mono-data text-[10px] text-[var(--t4)]">The job may not exist or the backend is unreachable</span>
        </div>
      </div>
    );
  }

  // Show result not available state
  if (!data) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)] border border-[var(--b1)] rounded-lg">
        <div className="text-center">
          <span className="font-mono-data text-[12px] text-[var(--t3)] block mb-2">Result not available</span>
          <span className="font-mono-data text-[10px] text-[var(--t4)]">Job status: {status}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0 border border-[var(--b1)] rounded-lg overflow-hidden animate-fade-in">
      {/* Breadcrumb / header strip */}
      <div className="flex items-center gap-3 px-4 h-10 border-b border-[var(--b1)] bg-[var(--s1)]">
        <Link href="/" className="font-mono-data text-[11px] text-[var(--t3)] hover:text-[var(--t2)] transition-colors">
          ← command center
        </Link>
        <span className="text-[var(--b2)]">/</span>
        <span className="font-mono-data text-[11px] text-[var(--t4)]">{jobId}</span>
        <span className="text-[var(--b2)]">/</span>
        <span className="font-mono-data text-[11px] text-[var(--t2)]">analysis</span>
        <div className="flex-1" />

        <span
          className={`font-mono-data text-[10px] px-2 py-0.5 rounded ${
            status === "COMPLETED"
              ? "text-[var(--green)] bg-[var(--green-dim)]"
              : status === "FAILED"
              ? "text-[var(--red)] bg-[var(--red-dim)]"
              : "text-[var(--amber)] bg-[var(--amber-dim)]"
          }`}
        >
          {status}
        </span>

        <Link
          href={`/visual-analytics/${jobId}`}
          className="font-mono-data text-[11px] text-[var(--t4)] border border-[var(--b2)] hover:border-[var(--b3)] hover:text-[var(--t2)] px-2.5 py-1 rounded transition-colors"
        >
          Visual Analytics →
        </Link>
        <a
          href={api.downloadUrl(jobId)}
          target="_blank"
          rel="noreferrer"
          className="font-mono-data text-[11px] text-[var(--t4)] border border-[var(--b2)] hover:border-[var(--b3)] hover:text-[var(--t2)] px-2.5 py-1 rounded transition-colors"
        >
          Download Results ↓
        </a>
      </div>

      {/* Query */}
      <div className="px-4 py-3 border-b border-[var(--b1)]">
        <div className="flex items-start gap-2">
          <span className="font-mono-data text-[10px] text-[var(--t3)] mt-0.5 shrink-0">QUERY</span>
          <p className="font-mono-data text-[12px] text-[var(--t2)]">
            &ldquo;{data.query || "—"}&rdquo;
          </p>
        </div>
        <div className="flex items-center gap-3 mt-1.5 ml-14">
          <span className="font-mono-data text-[10px] text-[var(--t4)]">routing: {data.workflow_reason || data.workflow_id}</span>
          <span className="font-mono-data text-[10px] text-[var(--t4)]">task: {data.task}</span>
        </div>
      </div>

      {/* Warnings */}
      {data.warnings && data.warnings.length > 0 && (
        <div className="px-4 py-2 border-b border-[var(--b1)] bg-[var(--amber-dim)]">
          {data.warnings.map((w, i) => (
            <p key={i} className="font-mono-data text-[10px] text-[var(--amber)] m-0">{w}</p>
          ))}
        </div>
      )}

      {/* Errors */}
      {data.errors && data.errors.length > 0 && (
        <div className="px-4 py-2 border-b border-[var(--b1)] bg-[var(--red-dim)]">
          {data.errors.map((e, i) => (
            <p key={i} className="font-mono-data text-[10px] text-[var(--red)] m-0">{e}</p>
          ))}
        </div>
      )}

      {/* 2-column workspace */}
      <div className="flex divide-x divide-[var(--b1)] min-h-[520px]">
        {/* Spatial canvas */}
        <div className="flex-1 flex flex-col">
          <div className="panel-header">
            <span className="panel-label">Spatial Analysis</span>
            <span className="font-mono-data text-[10px] text-[var(--t3)]">JOB #{jobId}</span>
          </div>
          <div className="flex-1 bg-[var(--s0)] relative flex items-center justify-center overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={overlayUrl}
              alt="Layer Preview"
              className="max-w-full max-h-full object-contain"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
        </div>

        {/* Right detail column */}
        <div className="w-[300px] shrink-0 divide-y divide-[var(--b1)] flex flex-col">
          {/* Answer */}
          <div className="p-4">
            <span className="panel-label block mb-2">Answer</span>
            <p className="text-[12px] text-[var(--t1)] leading-relaxed">{data.answer || "—"}</p>
          </div>

          {/* Metrics grid */}
          <div className="grid grid-cols-2 divide-x divide-[var(--b1)]">
            <div className="p-3">
              <span className="panel-label block">Confidence</span>
              <span className="font-mono-data text-[13px] font-semibold text-[var(--t0)] mt-0.5 block">
                {data.confidence != null ? `${(data.confidence * 100).toFixed(1)}%` : "—"}
              </span>
            </div>
            <div className="p-3">
              <span className="panel-label block">Regions</span>
              <span className="font-mono-data text-[13px] font-semibold text-[var(--t0)] mt-0.5 block">
                {regions > 0 ? String(regions) : "—"}
              </span>
            </div>
            <div className="p-3">
              <span className="panel-label block">Pixels Changed</span>
              <span className="font-mono-data text-[13px] font-semibold text-[var(--t0)] mt-0.5 block">
                {changedPixels > 0 ? changedPixels.toLocaleString("en-US") : "—"}
              </span>
            </div>
            <div className="p-3">
              <span className="panel-label block">Area (m²)</span>
              <span className="font-mono-data text-[13px] font-semibold text-[var(--t0)] mt-0.5 block">
                {areaM2 != null && areaM2 > 0 ? `${areaM2.toLocaleString()} m²` : "—"}
              </span>
            </div>
          </div>

          {/* Evidence */}
          <div className="p-3 flex-1">
            <span className="panel-label block mb-2">Evidence</span>
            <div className="space-y-1">
              {data.evidence?.spatial?.boxes && data.evidence.spatial.boxes.length > 0 ? (
                data.evidence.spatial.boxes.map((box, i) => (
                  <div key={i} className="flex items-center gap-2 py-1">
                    <span className="font-mono-data text-[10px] text-[var(--green)]">✓</span>
                    <span className="text-[11px] text-[var(--t2)] flex-1">{box.label}</span>
                    {box.score != null && (
                      <span className="font-mono-data text-[9px] text-[var(--t4)]">{(box.score * 100).toFixed(0)}%</span>
                    )}
                  </div>
                ))
              ) : (
                <p className="font-mono-data text-[10px] text-[var(--t4)]">No detection boxes.</p>
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
                    <span className="font-mono-data text-[10px] text-[var(--t3)]">○</span>
                    <span className="font-mono-data text-[11px] text-[var(--t4)]">{m}</span>
                  </div>
                ))
              ) : (
                <p className="font-mono-data text-[10px] text-[var(--t4)]">No models recorded</p>
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
