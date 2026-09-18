"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useMemo, useRef, useState, useEffect } from "react";
import { useJob, useAnalysisResult, useLayers } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { BlurFade } from "@/components/ui/blur-fade";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Badge,
  Progress,
  Skeleton,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui";
import {
  AlertCircle,
  ArrowLeft,
  ArrowLeftRight,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Download,
  Eye,
  FileText,
  Layers,
  Loader2,
  MapPin,
  Maximize2,
  Send,
  Sparkles,
  Target,
} from "lucide-react";
import type { JobStatus } from "@/lib/types";

const STATUS_LABEL: Record<JobStatus, string> = {
  CREATED: "Created",
  UPLOADED: "Uploaded",
  QUEUED: "Queued",
  VALIDATING: "Validating",
  PLANNING: "Planning",
  RUNNING: "Running",
  GENERATING_EVIDENCE: "Generating evidence",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

const STATUS_DOT: Record<JobStatus, string> = {
  CREATED: "bg-[var(--text-4)]",
  UPLOADED: "bg-[var(--text-4)]",
  QUEUED: "bg-[var(--text-4)]",
  VALIDATING: "bg-[var(--cyan)]",
  PLANNING: "bg-[var(--cyan)]",
  RUNNING: "bg-[var(--cyan)] animate-pulse-dot",
  GENERATING_EVIDENCE: "bg-[var(--cyan)] animate-pulse-dot",
  COMPLETED: "bg-[var(--green)]",
  FAILED: "bg-[var(--error)]",
};

const STATUS_PILL: Record<JobStatus, string> = {
  CREATED: "status-pill",
  UPLOADED: "status-pill",
  QUEUED: "status-pill",
  VALIDATING: "status-pill-cyan",
  PLANNING: "status-pill-cyan",
  RUNNING: "status-pill-cyan",
  GENERATING_EVIDENCE: "status-pill-cyan",
  COMPLETED: "status-pill-green",
  FAILED: "status-pill-red",
};

function formatTime(ms?: number) {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function AnalysisJobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const job = useJob(jobId);
  const result = useAnalysisResult(jobId, job.data?.status === "COMPLETED");
  const layersQuery = useLayers(jobId);

  const [activeTab, setActiveTab] = useState<"chat" | "analysis" | "trace">("chat");
  const [followUp, setFollowUp] = useState("");
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [splitPos, setSplitPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const status: JobStatus = (job.data?.status as JobStatus) || "QUEUED";
  const isFailed = status === "FAILED";
  const isRunning =
    status === "RUNNING" ||
    status === "VALIDATING" ||
    status === "PLANNING" ||
    status === "GENERATING_EVIDENCE";
  const isCompleted = status === "COMPLETED";

  const layers = layersQuery.data?.layers ?? [];
  const currentLayer = useMemo(() => {
    if (activeLayerId) return layers.find((l) => l.id === activeLayerId) || layers[0];
    return layers[0];
  }, [layers, activeLayerId]);

  const data = result.data;
  const evidence = data?.evidence;
  const spatial = evidence?.spatial;
  const statistics = spatial?.statistics;
  const trace = data?.trace || data?.execution_trace || [];

  // Splitter dragging logic
  const handleMouseDown = () => setIsDragging(true);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.max(10, Math.min(90, (x / rect.width) * 100));
      setSplitPos(pct);
    };
    const handleMouseUp = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <TooltipProvider delayDuration={120}>
      <div className="h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text)] font-sans overflow-hidden antialiased">
        <TopBar showBrand={true} />

        <div className="flex-1 flex overflow-hidden">
          <Sidebar hideBrand={true} />

          <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Sub-header */}
            <div className="border-b border-[var(--border)] bg-[var(--surface)] px-6 py-3 flex items-center justify-between gap-4 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <Link
                  href="/history"
                  className="w-7 h-7 rounded-md border border-[var(--border)] bg-[var(--surface-2)] flex items-center justify-center text-[var(--text-2)] hover:text-[var(--heading)] hover:border-[var(--border-strong)] transition"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                </Link>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-[11px] text-[var(--text-3)] font-mono-data">
                    <span>analysis</span>
                    <ChevronRight className="w-3 h-3" />
                    <span className="text-[var(--text-2)] truncate max-w-[180px]">{jobId}</span>
                  </div>
                  <h1 className="text-sm font-semibold text-[var(--heading)] truncate mt-0.5">
                    {data?.query || job.data?.query || "Untitled analysis"}
                  </h1>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className={`status-dot ${STATUS_DOT[status]}`} />
                <span className={`${STATUS_PILL[status]} text-[10px]`}>
                  {STATUS_LABEL[status]}
                </span>
                {data?.confidence != null && (
                  <Badge variant="success" className="font-mono-data">
                    {Math.round(data.confidence * 100)}% confidence
                  </Badge>
                )}
                <a
                  href={api.downloadUrl(jobId)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[var(--border)] bg-[var(--surface-2)] hover:bg-[var(--surface-hover)] text-xs font-medium text-[var(--text)] transition"
                >
                  <Download className="w-3.5 h-3.5 text-[var(--text-3)]" />
                  Export
                </a>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_400px] overflow-hidden">
              {/* Center workspace */}
              <div className="flex flex-col overflow-hidden bg-[var(--workspace)] border-r border-[var(--border)]">
                {/* Layer toolbar */}
                <div className="h-10 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between px-4 shrink-0">
                  <div className="flex items-center gap-3 text-xs">
                    <div className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[var(--cyan)]" />
                      <span className="font-medium text-[var(--heading)]">Layer</span>
                    </div>
                    {isCompleted && layers.length > 0 ? (
                      <div className="flex items-center gap-1.5">
                        {layers.map((layer) => {
                          const active = layer.id === currentLayer?.id;
                          return (
                            <button
                              key={layer.id}
                              onClick={() => setActiveLayerId(layer.id)}
                              className={`px-2 py-1 rounded-md text-[11px] transition border ${
                                active
                                  ? "bg-[var(--cyan)]/10 border-[var(--cyan)]/40 text-[var(--cyan)] font-medium"
                                  : "border-transparent text-[var(--text-2)] hover:text-[var(--heading)] hover:bg-[var(--surface-2)]"
                              }`}
                            >
                              {layer.name}
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <span className="text-[var(--text-3)] font-mono-data">
                        {isCompleted ? "No layers" : "Awaiting completion"}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button className="w-7 h-7 rounded-md hover:bg-[var(--surface-2)] text-[var(--text-3)] hover:text-[var(--heading)] transition flex items-center justify-center">
                          <ArrowLeftRight className="w-3.5 h-3.5" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>Compare split</TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button className="w-7 h-7 rounded-md hover:bg-[var(--surface-2)] text-[var(--text-3)] hover:text-[var(--heading)] transition flex items-center justify-center">
                          <Maximize2 className="w-3.5 h-3.5" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>Fullscreen</TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <a
                          href={currentLayer?.artifact_url ? api.exportUrl(jobId, currentLayer.id, "png") : "#"}
                          target="_blank"
                          rel="noopener"
                          className="w-7 h-7 rounded-md hover:bg-[var(--surface-2)] text-[var(--text-3)] hover:text-[var(--heading)] transition flex items-center justify-center"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                      </TooltipTrigger>
                      <TooltipContent>Download layer</TooltipContent>
                    </Tooltip>
                  </div>
                </div>

                {/* Canvas */}
                <div className="flex-1 relative overflow-hidden bg-[var(--canvas)]">
                  {job.isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="flex flex-col items-center gap-3 text-[var(--text-3)]">
                        <Loader2 className="w-6 h-6 animate-spin text-[var(--cyan)]" />
                        <p className="text-xs font-mono-data">Loading job</p>
                      </div>
                    </div>
                  )}

                  {isFailed && (
                    <BlurFade className="absolute inset-0 flex items-center justify-center">
                      <div className="max-w-sm text-center px-6">
                        <div className="w-12 h-12 rounded-xl bg-[var(--error-bg)] border border-[var(--error)]/30 flex items-center justify-center mx-auto mb-4">
                          <AlertCircle className="w-6 h-6 text-[var(--error)]" />
                        </div>
                        <h3 className="text-sm font-semibold text-[var(--heading)] mb-1">Analysis failed</h3>
                        <p className="text-xs text-[var(--text-2)] mb-4">
                          The pipeline encountered an error. Inspect the execution trace for details.
                        </p>
                        <Link
                          href="/analysis"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--cyan)] text-[var(--canvas)] text-xs font-semibold hover:brightness-110 transition"
                        >
                          Start a new analysis
                        </Link>
                      </div>
                    </BlurFade>
                  )}

                  {isRunning && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <BlurFade className="text-center">
                        <div className="relative w-16 h-16 mx-auto mb-4">
                          <div className="absolute inset-0 rounded-full border-2 border-[var(--border)]" />
                          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-[var(--cyan)] animate-spin-smooth" />
                          <Sparkles className="absolute inset-0 m-auto w-6 h-6 text-[var(--cyan)]" />
                        </div>
                        <p className="text-sm font-semibold text-[var(--heading)]">{STATUS_LABEL[status]}</p>
                        <p className="text-xs text-[var(--text-3)] mt-1 max-w-xs">
                          Running geospatial pipeline · usually takes 20–60 seconds
                        </p>
                      </BlurFade>
                    </div>
                  )}

                  {isCompleted && currentLayer?.artifact_url && (
                    <BlurFade className="absolute inset-0 p-4">
                      <div ref={containerRef} className="relative w-full h-full rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--canvas)]">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={currentLayer.artifact_url}
                          alt={currentLayer.name}
                          className="absolute inset-0 w-full h-full object-contain"
                        />
                        {currentLayer.legend_url && (
                          <div className="absolute bottom-3 right-3 px-2.5 py-1.5 rounded-md bg-[var(--surface)]/90 border border-[var(--border)] backdrop-blur-sm">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={currentLayer.legend_url}
                              alt="Legend"
                              className="h-4 w-auto"
                            />
                          </div>
                        )}
                        {/* Split divider overlay (visual cue) */}
                        <div
                          style={{ left: `${splitPos}%` }}
                          className="absolute top-0 bottom-0 -translate-x-1/2 w-px bg-[var(--cyan)]/40 pointer-events-none"
                        />
                      </div>
                    </BlurFade>
                  )}

                  {isCompleted && !currentLayer?.artifact_url && (
                    <div className="absolute inset-0 flex items-center justify-center text-[var(--text-3)] text-xs font-mono-data">
                      No artifact URL for selected layer
                    </div>
                  )}

                  {!job.isLoading && !isRunning && !isFailed && !isCompleted && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <BlurFade className="text-center">
                        <div className="relative w-16 h-16 mx-auto mb-4">
                          <div className="absolute inset-0 rounded-full border-2 border-[var(--border)]" />
                          <Loader2 className="absolute inset-0 m-auto w-6 h-6 text-[var(--text-3)] animate-spin" />
                        </div>
                        <p className="text-sm font-semibold text-[var(--heading)]">{STATUS_LABEL[status]}</p>
                        <p className="text-xs text-[var(--text-3)] mt-1">
                          Waiting for pipeline to start
                        </p>
                      </BlurFade>
                    </div>
                  )}
                </div>

                {/* Footer hint */}
                <div className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-2 flex items-center justify-between text-[10px] font-mono-data text-[var(--text-3)] shrink-0">
                  <div className="flex items-center gap-3">
                    <span>Job ID: <span className="text-[var(--text-2)]">{jobId}</span></span>
                    {data?.models_used && data.models_used.length > 0 && (
                      <span>· Models: <span className="text-[var(--text-2)]">{data.models_used.join(", ")}</span></span>
                    )}
                  </div>
                  {data?.execution_trace && (
                    <span>Trace: {trace.length} steps</span>
                  )}
                </div>
              </div>

              {/* Right panel */}
              <aside className="flex flex-col bg-[var(--surface)] overflow-hidden shrink-0">
                <Tabs
                  value={activeTab}
                  onValueChange={(v) => setActiveTab(v as typeof activeTab)}
                  className="flex-1 flex flex-col overflow-hidden"
                >
                  <div className="border-b border-[var(--border)] px-4 shrink-0">
                    <TabsList className="border-b-0 gap-3">
                      <TabsTrigger value="chat">Chat</TabsTrigger>
                      <TabsTrigger value="analysis">Analysis</TabsTrigger>
                      <TabsTrigger value="trace">Trace</TabsTrigger>
                    </TabsList>
                  </div>

                  <div className="flex-1 overflow-y-auto">
                    {/* Chat */}
                    <TabsContent value="chat" className="p-4 space-y-4">
                      <div className="flex items-start gap-2.5">
                        <div className="w-6 h-6 rounded-full bg-[var(--surface-3)] flex items-center justify-center text-[10px] font-bold text-[var(--heading)] shrink-0 mt-0.5">
                          YOU
                        </div>
                        <div className="flex-1">
                          <div className="bg-[var(--surface-3)] border border-[var(--border)] rounded-xl rounded-tl-sm p-3 text-[var(--text)] text-xs leading-relaxed">
                            {data?.query || job.data?.query || "Untitled analysis"}
                          </div>
                        </div>
                      </div>

                      {(isCompleted || data?.answer) && (
                        <BlurFade>
                          <div className="flex items-start gap-2.5">
                            <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-[var(--cyan)] to-[var(--teal)] flex items-center justify-center shrink-0 mt-0.5">
                              <Sparkles className="w-3 h-3 text-[var(--canvas)]" />
                            </div>
                            <div className="flex-1">
                              <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-2)] leading-relaxed space-y-3">
                                {data?.answer || "Analysis complete. View layers and metrics in the Analysis tab."}

                                {data?.confidence != null && (
                                  <div className="p-2 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
                                    <div className="flex items-center justify-between text-[11px] mb-1.5">
                                      <span className="text-[var(--text-3)]">Confidence</span>
                                      <span className="font-mono-data font-bold text-[var(--cyan)]">
                                        {Math.round(data.confidence * 100)}%
                                      </span>
                                    </div>
                                    <Progress value={data.confidence * 100} className="h-1" />
                                  </div>
                                )}

                                {statistics && (
                                  <div className="rounded-lg bg-[var(--surface-2)] border border-[var(--border)] p-2.5 space-y-1.5">
                                    <p className="text-[var(--cyan)] font-semibold text-[11px]">Key Findings</p>
                                    <ul className="space-y-1 text-[var(--text-2)] text-[11px]">
                                      {statistics.region_count > 0 && (
                                        <li>Regions detected: <strong className="text-[var(--heading)]">{statistics.region_count}</strong></li>
                                      )}
                                      {statistics.changed_pixels > 0 && (
                                        <li>Changed pixels: <strong className="text-[var(--heading)]">{statistics.changed_pixels.toLocaleString()}</strong></li>
                                      )}
                                      {statistics.estimated_area_sq_km != null && (
                                        <li>Estimated area: <strong className="text-[var(--heading)]">{statistics.estimated_area_sq_km.toFixed(2)} km²</strong></li>
                                      )}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </BlurFade>
                      )}

                      {!isCompleted && !data?.answer && !isFailed && (
                        <div className="flex items-start gap-2.5">
                          <div className="w-6 h-6 rounded-md bg-[var(--surface-3)] flex items-center justify-center shrink-0 mt-0.5">
                            <Loader2 className="w-3 h-3 text-[var(--cyan)] animate-spin" />
                          </div>
                          <div className="flex-1 space-y-2">
                            <Skeleton className="h-3 w-full" />
                            <Skeleton className="h-3 w-5/6" />
                            <Skeleton className="h-3 w-2/3" />
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    {/* Analysis */}
                    <TabsContent value="analysis" className="p-4 space-y-4">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-xs flex items-center gap-2">
                            <Cpu className="w-3.5 h-3.5 text-[var(--cyan)]" />
                            Workflow
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <div>
                            <p className="text-[10px] font-mono-data uppercase tracking-wider text-[var(--text-3)] mb-1">
                              Selected
                            </p>
                            <p className="text-xs font-medium text-[var(--heading)]">
                              {data?.workflow || "—"}
                            </p>
                          </div>
                          {data?.workflow_reason && (
                            <div>
                              <p className="text-[10px] font-mono-data uppercase tracking-wider text-[var(--text-3)] mb-1">
                                Reasoning
                              </p>
                              <p className="text-xs text-[var(--text-2)] leading-relaxed">
                                {data.workflow_reason}
                              </p>
                            </div>
                          )}
                        </CardContent>
                      </Card>

                      {spatial && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-xs flex items-center gap-2">
                              <Target className="w-3.5 h-3.5 text-[var(--cyan)]" />
                              Detected Regions
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            {spatial.boxes.length > 0 ? (
                              <div className="space-y-1">
                                {spatial.boxes.slice(0, 8).map((b, i) => (
                                  <div
                                    key={i}
                                    className="flex items-center justify-between p-2 rounded-md bg-[var(--surface-2)] border border-[var(--border)]"
                                  >
                                    <span className="text-xs text-[var(--text-2)] truncate">{b.label}</span>
                                    {b.score != null && (
                                      <span className="text-[10px] font-mono-data text-[var(--cyan)]">
                                        {(b.score * 100).toFixed(0)}%
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs text-[var(--text-3)] text-center py-3">
                                No regions detected
                              </p>
                            )}
                          </CardContent>
                        </Card>
                      )}

                      {data?.warnings && data.warnings.length > 0 && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-xs flex items-center gap-2 text-[var(--warning)]">
                              <AlertCircle className="w-3.5 h-3.5" />
                              Warnings
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <ul className="space-y-1.5 text-xs text-[var(--text-2)]">
                              {data.warnings.map((w, i) => (
                                <li key={i} className="flex items-start gap-1.5">
                                  <span className="text-[var(--warning)] mt-0.5">•</span>
                                  <span>{w}</span>
                                </li>
                              ))}
                            </ul>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>

                    {/* Trace */}
                    <TabsContent value="trace" className="p-4">
                      {trace.length === 0 ? (
                        <div className="text-center py-12 text-xs text-[var(--text-3)]">
                          No execution trace yet
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {trace.map((step, i) => {
                            const statusIcon =
                              step.status === "success" ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-[var(--green)]" />
                              ) : step.status === "running" ? (
                                <Loader2 className="w-3.5 h-3.5 text-[var(--cyan)] animate-spin" />
                              ) : step.status === "error" ? (
                                <AlertCircle className="w-3.5 h-3.5 text-[var(--error)]" />
                              ) : (
                                <Clock className="w-3.5 h-3.5 text-[var(--text-4)]" />
                              );

                            return (
                              <div
                                key={i}
                                className="p-3 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]"
                              >
                                <div className="flex items-center justify-between gap-2 mb-1">
                                  <div className="flex items-center gap-2 min-w-0">
                                    {statusIcon}
                                    <span className="text-xs font-medium text-[var(--heading)] truncate">
                                      {step.step}
                                    </span>
                                  </div>
                                  {step.duration_ms != null && (
                                    <span className="text-[10px] font-mono-data text-[var(--text-3)] shrink-0">
                                      {formatTime(step.duration_ms)}
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-[var(--text-3)] font-mono-data">
                                  {step.model && <span>{step.model}</span>}
                                  {step.model && step.tool && <span>·</span>}
                                  {step.tool && <span>{step.tool}</span>}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </TabsContent>
                  </div>
                </Tabs>

                {/* Follow-up composer */}
                {/*<div className="border-t border-[var(--border)] p-3 bg-[var(--surface-2)] shrink-0">*/}
                {/*  <div className="flex items-center gap-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 focus-within:border-[var(--cyan)] focus-within:ring-1 focus-within:ring-[var(--cyan)]/30 transition">*/}
                {/*    <input*/}
                {/*      value={followUp}*/}
                {/*      onChange={(e) => setFollowUp(e.target.value)}*/}
                {/*      type="text"*/}
                {/*      placeholder="Ask a follow-up question…"*/}
                {/*      className="flex-1 bg-transparent border-0 text-xs text-[var(--heading)] placeholder-[var(--text-3)] focus:outline-none"*/}
                {/*    />*/}
                {/*    <button className="w-7 h-7 rounded-md bg-[var(--cyan)] text-[var(--canvas)] hover:brightness-110 transition flex items-center justify-center shrink-0">*/}
                {/*      <Send className="w-3.5 h-3.5" />*/}
                {/*    </button>*/}
                {/*  </div>*/}
                {/*</div>*/}
              </aside>
            </div>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}