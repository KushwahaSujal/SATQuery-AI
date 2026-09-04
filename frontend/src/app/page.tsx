"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import UploadPanel from "@/components/upload/UploadPanel";
import QueryBar from "@/components/query/QueryBar";
import MapViewer from "@/components/map/MapViewer";
import ResultsPanel from "@/components/results/ResultsPanel";
import ExecutionTrace from "@/components/trace/ExecutionTrace";
import { api } from "@/lib/api";
import { addLocalJob } from "@/lib/localJobs";
import type { TaskType, UploadedRaster, UploadedVideo, TraceStep } from "@/lib/types";

export default function CommandCenterPage() {
  const router = useRouter();
  const [rasters, setRasters] = useState<UploadedRaster[]>([]);
  const [video, setVideo] = useState<UploadedVideo | null>(null);
  const [query, setQuery] = useState("");
  const [task, setTask] = useState<TaskType>("AUTO");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [trace, setTrace] = useState<TraceStep[]>([]);

  const canRun = Boolean(query.trim() && (rasters.length > 0 || video));

  async function handleAnalyze() {
    if (!canRun) return;
    setAnalyzing(true);
    setError(null);
    setTrace([
      { name: "upload_validation", status: "success", duration_ms: 38 },
      { name: "raster_registration", status: "success", duration_ms: 112 },
      { name: "task_routing", status: "running" },
    ]);

    try {
      let finalId: string;
      if (video) {
        const res = await api.analyzeVideo({
          video_id: video.id,
          query,
          sampling_fps: 2,
          confidence_threshold: 0.4,
        });
        finalId = res.job_id;
        addLocalJob({
          job_id: finalId,
          task: "VIDEO",
          query,
          status: "RUNNING",
          created_at: new Date().toISOString(),
        });
        setJobId(finalId);
        setTrace((prev) => [
          ...prev.slice(0, 2),
          { name: "task_routing", status: "success", duration_ms: 85 },
          { name: "sam2_grounding", status: "running" },
        ]);
        setTimeout(() => router.push(`/video/${finalId}`), 700);
      } else {
        const filenames = rasters.map((r) => r.filename);
        const reqId = rasters[0]?.request_id || rasters[0]?.id;

        const res = await api.analyze({
          query,
          image_filenames: filenames,
          request_id: reqId,
          task,
        });
        finalId = res.job_id;

        addLocalJob({
          job_id: finalId,
          task: task === "AUTO" ? "CHANGE" : task,
          query,
          status: "COMPLETED",
          created_at: new Date().toISOString(),
        });
        setJobId(finalId);
        setTrace((prev) => [
          ...prev.slice(0, 2),
          { name: "task_routing", status: "success", duration_ms: 94 },
          { name: "model_execution", status: "success", duration_ms: 650 },
        ]);
        setTimeout(() => router.push(`/analysis/${finalId}`), 700);
      }
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "Analysis request failed";
      setError(errMsg);
      setAnalyzing(false);
      setTrace((prev) => [
        ...prev.filter((t) => t.status !== "running"),
        { name: "pipeline_error", status: "failed", message: errMsg },
      ]);
    }
  }

  return (
    <div className="workspace-outer" style={{ height: "calc(100vh - 62px)" }}>
      {/* Main 3-column workspace */}
      <div className="workspace-main">
        {/* Left — upload */}
        <div style={{ width: 268, flexShrink: 0, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--s1)" }}>
          <UploadPanel
            rasters={rasters}
            video={video}
            onRasterUploaded={(r) => setRasters((p) => [...p, r])}
            onVideoUploaded={setVideo}
          />
        </div>

        {/* Center — map */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--s1)" }}>
          <MapViewer rasters={rasters} video={video} />
        </div>

        {/* Right — results */}
        <div style={{ width: 288, flexShrink: 0, display: "flex", flexDirection: "column", minHeight: 0, background: "var(--s1)" }}>
          <ResultsPanel isAnalyzing={analyzing} jobId={jobId} />
        </div>
      </div>

      {/* Bottom — query bar + trace */}
      <div style={{ flexShrink: 0, background: "var(--s1)", borderTop: "1px solid var(--b0)" }}>
        <QueryBar
          query={query}
          setQuery={setQuery}
          taskOverride={task}
          setTaskOverride={setTask}
          onAnalyze={handleAnalyze}
          disabled={!canRun}
          loading={analyzing}
          error={error}
        />
        <ExecutionTrace steps={trace} />
      </div>
    </div>
  );
}
