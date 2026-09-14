"use client";

import { useState } from "react";
import Link from "next/link";
import { useJob, useAnalysisResult } from "@/hooks/useSystem";
import type { AnalysisResult } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { GlowCard } from "@/components/ui/glow-card";
import { PieMetrics } from "@/components/charts/PieMetrics";

interface ResultsPanelProps {
  result?: AnalysisResult | null;
  isAnalyzing?: boolean;
  jobId?: string | null;
}

const PIPELINE_STEPS = [
  { id: "upload_validation", label: "Upload Validation" },
  { id: "raster_registration", label: "Raster Registration" },
  { id: "task_routing", label: "Task Routing" },
];

export default function ResultsPanel({ result: propsResult, isAnalyzing, jobId }: ResultsPanelProps) {
  const job = useJob(jobId || undefined);
  const fetchedResult = useAnalysisResult(jobId || undefined, job.data?.status === "COMPLETED");
  const result = propsResult || fetchedResult.data;

  // Extract metrics from evidence.spatial.statistics
  const stats = result?.evidence?.spatial?.statistics;
  const regions = stats?.region_count ?? 0;
  const changedPixels = stats?.changed_pixels ?? 0;
  const areaM2 = stats?.estimated_area_sq_m;

  return (
    <section className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          <span className="panel-label">Output</span>
        </div>
        {isAnalyzing && (
          <Badge variant="accent">
            <span className="animate-spin-smooth w-2 h-2 border border-[var(--accent-dim)] border-t-[var(--accent)] rounded-full inline-block mr-1.5" />
            Executing
          </Badge>
        )}
        {result && !isAnalyzing && (
          <Badge variant={result.status === "COMPLETED" ? "success" : result.status === "FAILED" ? "destructive" : "warning"}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              result.status === "COMPLETED" ? "bg-[var(--green)]" : result.status === "FAILED" ? "bg-[var(--red)]" : "bg-[var(--amber)]"
            } mr-1.5`} />
            {result.status}
          </Badge>
        )}
      </div>

      {/* Tabs */}
      {result && !isAnalyzing && (
        <Tabs defaultValue="answer">
          <TabsList className="px-3">
            <TabsTrigger value="answer">Answer</TabsTrigger>
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
            <TabsTrigger value="metadata">Metadata</TabsTrigger>
          </TabsList>

          {/* Body */}
          <div className="flex-1 overflow-y-auto">
            <TabsContent value="answer">
              <div className="p-3 space-y-3">
                {/* Answer block */}
                {result.answer && (
                  <GlowCard className="border-l-2 border-l-[var(--accent)]">
                    <p className="text-xs text-[var(--t1)] leading-relaxed m-0">
                      {result.answer}
                    </p>
                  </GlowCard>
                )}

                {/* Warnings */}
                {result.warnings && result.warnings.length > 0 && (
                  <div className="p-2 rounded bg-[var(--amber-dim)] border border-[hsla(38,92%,56%,0.2)]">
                    <p className="font-mono-data text-[10px] text-[var(--amber)] m-0">
                      {result.warnings.join("; ")}
                    </p>
                  </div>
                )}

                {/* Quick stats */}
                <div className="grid grid-cols-2 gap-2">
                  <MetricCell
                    label="Confidence"
                    value={result.confidence != null ? `${(result.confidence * 100).toFixed(1)}%` : "—"}
                    color="var(--accent)"
                  />
                  <MetricCell
                    label="Regions"
                    value={regions > 0 ? String(regions) : "—"}
                    color="var(--cyan)"
                  />
                  <MetricCell
                    label="Changed Pixels"
                    value={changedPixels > 0 ? `${(changedPixels / 1000).toFixed(1)}k` : "—"}
                    color="var(--green)"
                  />
                  <MetricCell
                    label="Task"
                    value={result.task}
                    color="var(--purple)"
                    mono
                  />
                </div>

                {/* Actions */}
                {jobId && (
                  <div className="flex flex-col gap-2 pt-1">
                    <Link href={`/analysis/${jobId}`} className="block">
                      <Button className="w-full" size="sm">
                        Open Analysis Workspace →
                      </Button>
                    </Link>
                    <Link href={`/visual-analytics/${jobId}`} className="block">
                      <Button variant="outline" className="w-full" size="sm">
                        Visual Analytics
                      </Button>
                    </Link>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="metrics">
              <div className="p-3 space-y-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {stats && (
                      <PieMetrics
                        confidence={result.confidence ?? 0}
                        regions={regions}
                        pixelsChanged={changedPixels}
                      />
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Detailed Metrics</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <MetricRow label="Confidence" value={result.confidence != null ? `${(result.confidence * 100).toFixed(1)}%` : "—"} />
                    <Separator />
                    <MetricRow label="Regions" value={regions > 0 ? String(regions) : "—"} />
                    <Separator />
                    <MetricRow label="Changed Pixels" value={changedPixels > 0 ? String(changedPixels) : "—"} />
                    <Separator />
                    <MetricRow label="Area (m²)" value={areaM2 != null && areaM2 > 0 ? `${areaM2.toLocaleString()} m²` : "—"} />
                    {stats?.quality_status && (
                      <>
                        <Separator />
                        <MetricRow label="Quality" value={stats.quality_status} />
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="metadata">
              <div className="p-3">
                <Card>
                  <CardContent className="p-3 space-y-1">
                    <MetaRow label="task" value={result.task} />
                    <Separator />
                    <MetaRow label="job_id" value={jobId ?? "—"} />
                    <Separator />
                    <MetaRow label="models" value={result.models_used?.join(", ") || "—"} />
                    <Separator />
                    <MetaRow label="workflow" value={result.workflow_id} />
                    {result.workflow_reason && (
                      <>
                        <Separator />
                        <MetaRow label="reason" value={result.workflow_reason} />
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      )}

      {/* Analyzing state */}
      {isAnalyzing && (
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 animate-fade-in">
            <PipelineTracker />
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isAnalyzing && !result && (
        <div className="flex-1 flex items-center justify-center">
          <EmptyState />
        </div>
      )}
    </section>
  );
}

function MetricCell({ label, value, color, mono }: { label: string; value: string; color: string; mono?: boolean }) {
  return (
    <Card className="p-3 transition-all hover:border-[var(--b3)]">
      <p className="panel-label text-[9px] mb-1">{label}</p>
      <p
        className={`text-sm font-semibold text-[var(--t0)] m-0 ${mono ? "font-mono-data tracking-tight" : ""}`}
        style={{ letterSpacing: mono ? "0.02em" : "-0.02em" }}
      >
        <span className="inline-block w-1.5 h-1.5 rounded-full mr-2" style={{ backgroundColor: color }} />
        {value}
      </p>
    </Card>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="font-mono-data text-[10px] text-[var(--t3)]">{label}</span>
      <span className="font-mono-data text-[10px] text-[var(--t1)]">{value}</span>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="font-mono-data text-[10px] text-[var(--t3)]">{label}</span>
      <span className="font-mono-data text-[10px] text-[var(--t1)]">{value}</span>
    </div>
  );
}

function PipelineTracker() {
  return (
    <div className="space-y-0">
      {PIPELINE_STEPS.map((step, i) => {
        const isDone = i < 2;
        const isRunning = i === 2;
        return (
          <div key={step.id} className="flex gap-3">
            {/* Node + connector */}
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isDone
                    ? "bg-[var(--green-dim)] border border-[hsla(142,68%,52%,0.3)]"
                    : isRunning
                    ? "bg-[var(--accent-dim)] border border-[var(--accent)] animate-pulse-ring"
                    : "bg-[var(--s2)] border border-[var(--b2)]"
                }`}
              >
                {isDone ? (
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                ) : isRunning ? (
                  <span className="animate-spin-smooth w-2 h-2 border-[1.5px] border-transparent border-t-[var(--accent)] rounded-full block" />
                ) : (
                  <span className="w-1 h-1 rounded-full bg-[var(--b3)] block" />
                )}
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div className={`w-px flex-1 min-h-[16px] my-1 ${isDone ? "bg-[var(--green-dim)]" : "bg-[var(--b1)]"}`} />
              )}
            </div>

            {/* Step content */}
            <div className="pt-0.5 pb-3">
              <p className={`font-mono-data text-[11px] m-0 ${
                isDone ? "text-[var(--t2)]" : isRunning ? "text-[var(--t0)]" : "text-[var(--t4)]"
              }`}>
                {step.label}
              </p>
              {isDone && (
                <p className="font-mono-data text-[9px] text-[var(--green)] m-0 mt-0.5 tracking-wide">
                  ✓ completed
                </p>
              )}
              {isRunning && (
                <p className="font-mono-data text-[9px] text-[var(--accent-text)] m-0 mt-0.5">
                  running...
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center px-8">
      <div className="w-10 h-10 rounded-lg bg-[var(--s2)] border border-[var(--b1)] flex items-center justify-center mx-auto mb-3">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--t4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
      </div>
      <p className="font-mono-data text-[11px] text-[var(--t3)] m-0">No output yet</p>
      <p className="font-mono-data text-[9px] text-[var(--t4)] mt-1 leading-relaxed">
        Upload imagery and run<br />a query to see results
      </p>
    </div>
  );
}
