"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { UploadPanel, UploadedRasterMeta } from "@/components/UploadPanel";
import { MetadataPanel } from "@/components/MetadataPanel";
import { WorkflowDecisionPanel } from "@/components/WorkflowDecisionPanel";
import { QueryBar } from "@/components/QueryBar";
import { ResultsPanel } from "@/components/ResultsPanel";
import { MapViewer } from "@/components/MapViewer";
import { TracePanel, ExecutionStepItem } from "@/components/TracePanel";
import { ModelStatusPanel, ModelCapability } from "@/components/ModelStatusPanel";
import { VideoPlayerPanel, VideoFlagItem, VideoMetadataItem } from "@/components/VideoPlayerPanel";
import { VisualizationPanel, VisualizationLayer, PixelInspectionData } from "@/components/VisualizationPanel";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

export default function Home() {
  const [isHealthy, setIsHealthy] = useState<boolean>(false);
  const [device, setDevice] = useState<string>("Auto");
  const [models, setModels] = useState<ModelCapability[]>([]);

  const [files, setFiles] = useState<File[]>([]);
  const [metadata, setMetadata] = useState<UploadedRasterMeta[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  const [query, setQuery] = useState<string>("");
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

  const [requestId, setRequestId] = useState<string>("");
  const [workflowId, setWorkflowId] = useState<string>("");
  const [workflowReason, setWorkflowReason] = useState<string>("");
  const [task, setTask] = useState<string>("");
  const [modelsUsed, setModelsUsed] = useState<string[]>([]);
  const [answer, setAnswer] = useState<string>("");
  const [confidence, setConfidence] = useState<number | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [statistics, setStatistics] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<any>(null);
  const [trace, setTrace] = useState<ExecutionStepItem[]>([]);
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null);
  const [boxes, setBoxes] = useState<any[]>([]);

  // Grounding-specific intelligence states
  const [strategy, setStrategy] = useState<string | null>(null);
  const [groundingScore, setGroundingScore] = useState<number | null>(null);
  const [sam2Score, setSam2Score] = useState<number | null>(null);
  const [evidenceMetadata, setEvidenceMetadata] = useState<any>({});

  // Video-specific intelligence states
  const [isVideo, setIsVideo] = useState<boolean>(false);
  const [videoMetadata, setVideoMetadata] = useState<VideoMetadataItem | null>(null);
  const [videoFlags, setVideoFlags] = useState<VideoFlagItem[]>([]);

  // Visual Analytics & Evidence Overlay states
  const [activeLayer, setActiveLayer] = useState<VisualizationLayer | null>(null);
  const [activeLayerUrl, setActiveLayerUrl] = useState<string | null>(null);
  const [layerOpacity, setLayerOpacity] = useState<number>(0.75);
  const [inspectActive, setInspectActive] = useState<boolean>(false);
  const [inspectedPixelData, setInspectedPixelData] = useState<PixelInspectionData | null>(null);
  const [orchestration, setOrchestration] = useState<any>(null);

  const handleLayerChange = (layer: VisualizationLayer | null, opacityVal: number) => {
    setActiveLayer(layer);
    setLayerOpacity(opacityVal);
    if (layer && layer.artifact_url) {
      const url = layer.artifact_url.startsWith("http") ? layer.artifact_url : `${API_BASE}${layer.artifact_url}`;
      setActiveLayerUrl(url);
    } else {
      setActiveLayerUrl(null);
    }
  };

  const handlePixelClick = async (col: number, row: number) => {
    if (!requestId) return;
    try {
      const res = await fetch(`${API_BASE}/api/analysis/${requestId}/inspect-pixel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ col, row })
      });
      if (res.ok) {
        const data = await res.json();
        setInspectedPixelData(data);
      }
    } catch (err) {
      console.error("Pixel inspection failed:", err);
    }
  };

  // Fetch initial health and model capabilities
  useEffect(() => {
    fetchHealth();
    fetchModels();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setIsHealthy(true);
        setDevice(data.device || "Auto");
      }
    } catch (e) {
      setIsHealthy(false);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models`);
      if (res.ok) {
        const data = await res.json();
        setModels(data.models || []);
      }
    } catch (e) {
      console.error("Failed to fetch models:", e);
    }
  };

  const handleFilesSelected = async (selected: File[]) => {
    setFiles(selected);
    setIsUploading(true);
    setErrors([]);

    const isVid = selected.length === 1 && (selected[0].name.toLowerCase().endsWith(".mp4") || selected[0].name.toLowerCase().endsWith(".mov"));
    setIsVideo(isVid);

    if (isVid) {
      const formData = new FormData();
      formData.append("file", selected[0]);
      try {
        const res = await fetch(`${API_BASE}/api/video/upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error("Video upload failed");
        const data = await res.json();
        setRequestId(data.job_id);
        setVideoMetadata(data.video_metadata);
        setWorkflowId("video_analysis");
        setTask("video_grounding");
      } catch (err: any) {
        setErrors([err.message || "Video upload failed"]);
      } finally {
        setIsUploading(false);
      }
      return;
    }

    const formData = new FormData();
    selected.forEach((f) => formData.append("files", f));

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        let errMsg = `Upload failed (${res.status} ${res.statusText})`;
        try {
          const errData = JSON.parse(errText);
          errMsg = errData.error?.message || errData.message || errData.detail || errMsg;
        } catch {
          if (errText) errMsg = errText;
        }
        throw new Error(errMsg);
      }

      const data = await res.json();
      setRequestId(data.request_id);
      setMetadata(data.metadata || []);
      setWorkflowId(data.suggested_workflow || "");
    } catch (err: any) {
      setErrors([err.message || "Upload failed."]);
      setFiles([]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClear = () => {
    setFiles([]);
    setMetadata([]);
    setRequestId("");
    setWorkflowId("");
    setWorkflowReason("");
    setTask("");
    setModelsUsed([]);
    setAnswer("");
    setConfidence(null);
    setWarnings([]);
    setErrors([]);
    setTrace([]);
    setStatistics(null);
    setArtifacts(null);
    setOverlayUrl(null);
    setBoxes([]);
    setStrategy(null);
    setGroundingScore(null);
    setSam2Score(null);
    setEvidenceMetadata({});
    setOrchestration(null);
    setIsVideo(false);
    setVideoMetadata(null);
    setVideoFlags([]);
  };

  const handleAnalyze = async () => {
    if (!query.trim() || files.length === 0 || !requestId) return;

    setIsAnalyzing(true);
    setErrors([]);

    if (isVideo) {
      const formData = new FormData();
      formData.append("request_id", requestId);
      formData.append("query", query.trim());

      try {
        const res = await fetch(`${API_BASE}/api/video/analyze`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errText = await res.text();
          let errMsg = `Video analysis failed (${res.status} ${res.statusText})`;
          try {
            const errData = JSON.parse(errText);
            errMsg = errData.error?.message || errData.message || errData.detail || errMsg;
          } catch {
            if (errText) errMsg = errText;
          }
          throw new Error(errMsg);
        }

        const data = await res.json();
        setTask(data.task || "video_grounding");
        setWorkflowReason(data.workflow_reason || "");
        setModelsUsed(data.models_used || []);
        setVideoFlags(data.flags || []);
        setVideoMetadata(data.video_metadata || videoMetadata);
        setTrace(data.execution_trace || []);
        setWarnings(data.warnings || []);
        setErrors(data.errors || []);
        setArtifacts(data.artifacts || {});
        setAnswer(data.flags?.length > 0 
          ? `Discovered and flagged ${data.flags.length} event moment(s) with visual evidence.`
          : data.workflow_reason || "No events found.");
      } catch (err: any) {
        setErrors([err.message || "Video analysis error occurred."]);
      } finally {
        setIsAnalyzing(false);
      }
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId,
          query: query.trim(),
          image_filenames: files.map((f) => f.name),
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        let errMsg = `Analysis request failed (${res.status} ${res.statusText})`;
        try {
          const errData = JSON.parse(errText);
          errMsg = errData.error?.message || errData.message || errData.detail || errMsg;
        } catch {
          if (errText) errMsg = errText;
        }
        throw new Error(errMsg);
      }

      const data = await res.json();

      setTask(data.task || "");
      setWorkflowId(data.workflow_id || "");
      setWorkflowReason(data.workflow_reason || "");
      setModelsUsed(data.models_used || []);
      setAnswer(data.answer || "");
      setConfidence(data.confidence);
      setWarnings(data.warnings || []);
      setErrors(data.errors || []);
      setTrace(data.execution_trace || []);
      setArtifacts(data.artifacts || {});

      // Grounding & relational intelligence metadata
      setStrategy(data.evidence?.metadata?.strategy || null);
      setGroundingScore(data.evidence?.metadata?.grounding_score ?? null);
      setSam2Score(data.evidence?.metadata?.sam2_score ?? null);
      setEvidenceMetadata(data.evidence?.metadata || {});
      setOrchestration(data.orchestration || null);

      if (data.evidence?.spatial?.statistics) {
        setStatistics(data.evidence.spatial.statistics);
      }
      if (data.evidence?.spatial?.boxes) {
        setBoxes(data.evidence.spatial.boxes);
      }

      // Overlay resolution (supports both grounding_overlay and change_overlay)
      if (data.evidence?.spatial?.overlay_path) {
        const overlayName = data.evidence.spatial.overlay_path.split(/[\\/]/).pop() || "overlay.png";
        setOverlayUrl(`${API_BASE}/api/artifacts/${requestId}/overlays/${overlayName}`);
      } else if (data.artifacts?.overlays && data.artifacts.overlays.length > 0) {
        setOverlayUrl(`${API_BASE}/api/artifacts/${requestId}/overlays/${data.artifacts.overlays[0]}`);
      }
    } catch (err: any) {
      setErrors([err.message || "Analysis error occurred."]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col">
      <Header device={device} isHealthy={isHealthy} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        <UploadPanel
          files={files}
          metadata={metadata}
          isUploading={isUploading}
          onFilesSelected={handleFilesSelected}
          onClear={handleClear}
        />

        {!isVideo && <MetadataPanel metadata={metadata} />}

        <WorkflowDecisionPanel
          workflowId={workflowId}
          task={task}
          reason={workflowReason}
          selectedModels={modelsUsed}
        />

        <QueryBar
          query={query}
          isAnalyzing={isAnalyzing}
          canAnalyze={files.length > 0 && !!requestId}
          onChange={setQuery}
          onSubmit={handleAnalyze}
        />

        {isVideo && (
          <VideoPlayerPanel
            jobId={requestId}
            videoMetadata={videoMetadata}
            flags={videoFlags}
            workflowReason={workflowReason}
            modelsUsed={modelsUsed}
            apiBase={API_BASE}
          />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <ResultsPanel
              requestId={requestId}
              task={task}
              answer={answer}
              confidence={confidence}
              modelsUsed={modelsUsed}
              warnings={warnings}
              errors={errors}
              statistics={statistics}
              artifacts={artifacts}
              strategy={strategy}
              groundingScore={groundingScore}
              sam2Score={sam2Score}
              boxes={boxes}
              evidenceMetadata={evidenceMetadata}
              orchestration={orchestration}
            />

            <TracePanel trace={trace} />
          </div>

          <div className="space-y-6">
            <MapViewer
              metadata={metadata}
              overlayUrl={overlayUrl}
              activeLayerUrl={activeLayerUrl}
              layerOpacity={layerOpacity}
              inspectActive={inspectActive}
              onPixelClick={handlePixelClick}
              boxes={boxes}
            />

            {!isVideo && (
              <VisualizationPanel
                jobId={requestId}
                onLayerChange={handleLayerChange}
                onInspectRequested={setInspectActive}
                inspectedPixelData={inspectedPixelData}
              />
            )}
          </div>
        </div>

        <ModelStatusPanel models={models} />
      </main>

      <footer className="border-t border-surfaceBorder py-4 text-center text-xs text-slate-500 font-mono">
        SatQuery AI • Production-Ready Inference Engine • Real Remote-Sensing Intelligence
      </footer>
    </div>
  );
}
