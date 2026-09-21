"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { useJob, useAnalysisResult, useLayers, useVideoResult } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import { useJobProgress } from "@/hooks/useJobProgress";
import { PipelineProgress } from "@/components/analysis/PipelineProgress";
import { ResultsSkeleton } from "@/components/analysis/ResultsSkeleton";
import {
  describeJobStatus,
  jobStatusDotClass,
  jobStatusLabel,
  jobStatusPillClass,
} from "@/lib/statusMap";
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
  Minimize2,
  Send,
  Sparkles,
  Target,
} from "lucide-react";
import type { JobStatus } from "@/lib/types";

function formatTime(ms?: number) {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function AnalysisJobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const job = useJob(jobId);
  const isVideoJob = job.data?.task?.startsWith("video") === true;
  const result = useAnalysisResult(jobId, job.data?.status === "COMPLETED" && !isVideoJob);
  const videoResult = useVideoResult(jobId, job.data?.status === "COMPLETED" && isVideoJob);
  // Do not request raster layers until the job has loaded and is known to be
  // a raster analysis. The initial undefined task would otherwise trigger a
  // raster request for every video job.
  const layersQuery = useLayers(jobId, Boolean(job.data) && !isVideoJob);

  const [activeTab, setActiveTab] = useState<"chat" | "analysis" | "trace">("chat");
  const [followUp, setFollowUp] = useState("");
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const status: JobStatus = (job.data?.status as JobStatus) || "QUEUED";
  const isFailed = status === "FAILED";
  const isRunning =
    status === "CREATED" ||
    status === "UPLOADED" ||
    status === "PENDING" ||
    status === "RUNNING" ||
    status === "VALIDATING" ||
    status === "PLANNING" ||
    status === "GENERATING_EVIDENCE";
  const isCompleted = status === "COMPLETED";
  const { data: progress } = useJobProgress(jobId, isRunning);

  const layers = layersQuery.data?.layers ?? [];
  const currentLayer = useMemo(() => {
    if (activeLayerId) return layers.find((l) => l.id === activeLayerId) || layers[0];
    return layers[0];
  }, [layers, activeLayerId]);

  const data = isVideoJob ? videoResult.data : result.data;
  const videoFlags = data?.flags ?? [];
  const videoMetadata = data?.video_metadata;
  const evidence = data?.evidence;
  const spatial = evidence?.spatial;
  const statistics = spatial?.statistics;
  const trace = data?.trace || data?.execution_trace || [];

  const toggleFullscreen = () => {
    setIsFullscreen((fullscreen) => !fullscreen);
  };

  return (
    <TooltipProvider delayDuration={120}>
      <div className={`${isFullscreen ? "fixed inset-0 z-50" : "h-screen w-full"} flex flex-col bg-[var(--canvas)] text-[var(--text)] font-sans overflow-hidden antialiased`}>
        {!isFullscreen && <TopBar showBrand={true} />}

        <div className="flex-1 flex overflow-hidden">
          {!isFullscreen && <Sidebar hideBrand={true} />}

          <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Sub-header */}
            {!isFullscreen && <div className="border-b border-[var(--border)] bg-[var(--surface)] px-6 py-3 flex items-center justify-between gap-4 shrink-0">
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
                <span className={`status-dot ${jobStatusDotClass(status)} ${describeJobStatus(status).active ? "animate-pulse-dot" : ""}`} />
                <span className={`status-pill ${jobStatusPillClass(status)} text-[10px]`}>
                  {jobStatusLabel(status)}
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
            </div>}

            {/* Body */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_400px] overflow-hidden">
              {/* Center workspace */}
              <div className="flex flex-col overflow-hidden bg-[var(--workspace)] border-r border-[var(--border)]">
                {/* Layer toolbar */}
                <div className="min-h-14 border-b border-[var(--border)] bg-[var(--surface)] flex items-stretch justify-between px-4 shrink-0">
                  <div className="flex min-w-0 flex-1 items-stretch gap-3 text-xs">
                    <div className="flex shrink-0 items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[var(--cyan)]" />
                      <span className="font-medium text-[var(--heading)]">Layer</span>
                    </div>
                    {isCompleted && layers.length > 0 ? (
                      <div className="flex min-w-0 flex-1 items-stretch gap-1 overflow-x-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-[var(--border)]">
                        {layers.map((layer) => {
                          const active = layer.id === currentLayer?.id;
                          return (
                            <button
                              key={layer.id}
                              onClick={() => setActiveLayerId(layer.id)}
                              title={layer.name}
                              className={`min-w-[92px] max-w-[190px] shrink-0 px-2.5 py-1.5 text-center text-[11px] leading-4 transition border border-b-2 ${
                                active
                                  ? "bg-[var(--cyan)]/10 border-[var(--cyan)]/40 border-b-[var(--cyan)] text-[var(--cyan)] font-medium"
                                  : "border-transparent text-[var(--text-2)] hover:border-[var(--border)] hover:text-[var(--heading)] hover:bg-[var(--surface-2)]"
                              }`}
                            >
                              <span className="line-clamp-3">{layer.name}</span>
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
                  <div className="flex shrink-0 items-center gap-1 border-l border-[var(--border)] pl-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          onClick={toggleFullscreen}
                          aria-label={isFullscreen ? "Exit fullscreen" : "View layer fullscreen"}
                          className="w-7 h-7 rounded-md hover:bg-[var(--surface-2)] text-[var(--text-3)] hover:text-[var(--heading)] transition flex items-center justify-center"
                        >
                          {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>{isFullscreen ? "Exit fullscreen" : "Fullscreen"}</TooltipContent>
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
                    <div className="absolute inset-0 overflow-y-auto p-4">
                      <BlurFade className="mx-auto w-full max-w-3xl space-y-3">
                        {/* Real checkpoint progress from GET /api/jobs/{id}/progress,
                            replacing a spinner that could only say "usually takes
                            20-60 seconds" without knowing what was actually running. */}
                        <PipelineProgress progress={progress ?? null} isPlanning={!progress} />
                        <ResultsSkeleton layerCount={isVideoJob ? 3 : 4} />
                      </BlurFade>
                    </div>
                  )}

                  {isCompleted && isVideoJob && (
                    <BlurFade className="absolute inset-0 flex flex-col p-4">
                      <div className="relative min-h-0 flex-1 overflow-hidden rounded-xl border border-[var(--border)] bg-black">
                        <video
                          src={api.videoStreamUrl(jobId)}
                          controls
                          className="absolute inset-0 h-full w-full object-contain"
                        />
                        {videoFlags.length > 0 && videoMetadata && (
                          <div className="absolute bottom-14 left-4 right-4 rounded-lg border border-white/15 bg-black/70 p-2 backdrop-blur-sm">
                            <div className="mb-1 flex items-center justify-between text-[10px] text-white/70">
                              <span>Detected moments</span>
                              <span>{videoFlags.length} event{videoFlags.length === 1 ? "" : "s"}</span>
                            </div>
                            <div className="relative h-1.5 rounded-full bg-white/20">
                              {videoFlags.map((flag) => (
                                <span
                                  key={flag.flag_id}
                                  title={`${flag.label} at ${flag.start_timestamp.toFixed(1)}s`}
                                  className="absolute -top-0.5 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[var(--cyan)]"
                                  style={{
                                    left: `${Math.min(
                                      (flag.start_timestamp / Math.max(videoMetadata.duration_sec, 1)) * 100,
                                      98,
                                    )}%`,
                                  }}
                                />
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="mt-3 flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[10px] font-mono-data text-[var(--text-3)]">
                        <span>Video intelligence feed</span>
                        <span>{data?.video_metadata?.duration_sec?.toFixed(1) ?? "—"}s</span>
                      </div>
                    </BlurFade>
                  )}

                  {isCompleted && !isVideoJob && currentLayer?.artifact_url && (
                    <BlurFade className="absolute inset-0 p-4">
                      <div
                        ref={containerRef}
                        className="relative w-full h-full rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--canvas)]"
                      >
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
                      </div>
                    </BlurFade>
                  )}

                  {isCompleted && !isVideoJob && !currentLayer?.artifact_url && (
                    <div className="absolute inset-0 flex items-center justify-center text-[var(--text-3)] text-xs font-mono-data">
                      No artifact URL for selected layer
                    </div>
                  )}

                  {!job.isLoading && status !== "QUEUED" && !isRunning && !isFailed && !isCompleted && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <BlurFade className="text-center">
                        <div className="relative w-16 h-16 mx-auto mb-4">
                          <div className="absolute inset-0 rounded-full border-2 border-[var(--border)]" />
                          <Loader2 className="absolute inset-0 m-auto w-6 h-6 text-[var(--text-3)] animate-spin" />
                        </div>
                        <p className="text-sm font-semibold text-[var(--heading)]">{jobStatusLabel(status)}</p>
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
                                {isVideoJob
                                  ? data?.workflow_reason || "Video analysis completed."
                                  : data?.answer || "Analysis complete. View layers and metrics in the Analysis tab."}

                                {isVideoJob && videoMetadata && (
                                  <div className="grid grid-cols-2 gap-2">
                                    {[
                                      ["Duration", `${videoMetadata.duration_sec.toFixed(1)}s`],
                                      ["Resolution", `${videoMetadata.width} × ${videoMetadata.height}`],
                                      ["Frame rate", `${videoMetadata.fps.toFixed(2)} fps`],
                                      ["Events", `${videoFlags.length}`],
                                    ].map(([label, value]) => (
                                      <div key={label} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-2">
                                        <p className="text-[10px] text-[var(--text-3)]">{label}</p>
                                        <p className="mt-0.5 text-xs font-semibold text-[var(--heading)]">{value}</p>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {isVideoJob && videoFlags.length > 0 && (
                                  <div className="space-y-2">
                                    <p className="text-[11px] font-semibold text-[var(--cyan)]">Detected moments</p>
                                    {videoFlags.map((flag) => (
                                      <div key={flag.flag_id} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-2.5">
                                        <div className="flex items-center justify-between gap-2">
                                          <span className="truncate text-[11px] font-semibold text-[var(--heading)]">{flag.label}</span>
                                          <span className="font-mono-data text-[10px] text-[var(--cyan)]">{flag.event_score.toFixed(2)}</span>
                                        </div>
                                        <p className="mt-1 text-[10px] text-[var(--text-3)]">
                                          {flag.start_timestamp.toFixed(2)}s → {flag.end_timestamp.toFixed(2)}s
                                        </p>
                                        {flag.reason && <p className="mt-1 text-[10px] leading-relaxed text-[var(--text-2)]">{flag.reason}</p>}
                                      </div>
                                    ))}
                                  </div>
                                )}

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

                      {/* Video events are a per-job concern, not a per-region one:
                          this Card used to sit inside the boxes .map() as a third flex
                          child of each region row, so it rendered once per box (up to
                          the .slice(0, 8) cap) and was laid out in a row sized for a
                          label and a percentage. */}
                      {isVideoJob && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-xs flex items-center gap-2">
                              <Clock className="w-3.5 h-3.5 text-[var(--cyan)]" />
                              Detected events
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            {data?.flags && data.flags.length > 0 ? (
                              <div className="space-y-1.5">
                                {data.flags.map((flag) => (
                                  <div
                                    key={flag.flag_id}
                                    className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-2"
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="truncate text-xs text-[var(--heading)]">{flag.label}</span>
                                      <span className="shrink-0 font-mono-data text-[10px] text-[var(--cyan)]">
                                        {flag.event_score.toFixed(2)}
                                      </span>
                                    </div>
                                    <p className="mt-1 text-[10px] text-[var(--text-3)]">
                                      {flag.start_timestamp.toFixed(1)}s → {flag.end_timestamp.toFixed(1)}s
                                    </p>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="py-3 text-center text-xs text-[var(--text-3)]">
                                {data?.workflow_reason || "No events detected"}
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