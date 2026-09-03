"use client";

import React, { useRef, useState } from "react";
import { Play, Pause, AlertCircle, Eye, CheckCircle2, Crosshair, Clock, ShieldAlert } from "lucide-react";

export interface VideoFlagItem {
  flag_id: string;
  video_id: string;
  start_timestamp: number;
  end_timestamp: number;
  start_frame: number;
  end_frame: number;
  peak_frame: number;
  label: string;
  reason: string;
  event_score: number; // Heuristic event-ranking score; not calibrated probability
  keyframe_url?: string | null;
  overlay_url?: string | null;
  mask_url?: string | null;
  box_2d?: number[] | null;
  model_scores?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface VideoMetadataItem {
  filename: string;
  duration_sec: number;
  fps: number;
  width: number;
  height: number;
  frame_count: number;
  codec?: string | null;
}

interface VideoPlayerPanelProps {
  jobId: string;
  videoMetadata?: VideoMetadataItem | null;
  flags: VideoFlagItem[];
  workflowReason?: string;
  modelsUsed?: string[];
  apiBase: string;
}

export const VideoPlayerPanel: React.FC<VideoPlayerPanelProps> = ({
  jobId,
  videoMetadata,
  flags,
  workflowReason,
  modelsUsed,
  apiBase,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [selectedFlagId, setSelectedFlagId] = useState<string | null>(
    flags.length > 0 ? flags[0].flag_id : null
  );
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [activeViewMode, setActiveViewMode] = useState<"video" | "annotated" | "mask">("video");

  const duration = videoMetadata?.duration_sec || (videoRef.current?.duration || 1);
  const videoUrl = `${apiBase}/api/video/${jobId}/stream`;

  const selectedFlag = flags.find((f) => f.flag_id === selectedFlagId) || flags[0];

  const handleSeek = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, seconds);
      setCurrentTime(seconds);
      setActiveViewMode("video");
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col mb-6">
      {/* Top Header / Metadata Bar */}
      <div className="bg-slate-950/80 px-6 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <span className="flex h-3 w-3 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <h2 className="text-sm font-semibold text-slate-200 tracking-wider uppercase">
            Video Footage Specialist Analysis
          </h2>
          {videoMetadata && (
            <span className="text-xs bg-slate-800 text-slate-400 px-2.5 py-0.5 rounded-full font-mono border border-slate-700">
              {videoMetadata.filename} ({videoMetadata.width}x{videoMetadata.height} · {videoMetadata.fps.toFixed(1)} FPS · {videoMetadata.duration_sec.toFixed(1)}s)
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {modelsUsed && modelsUsed.map((m) => (
            <span key={m} className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded font-mono">
              {m}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-0">
        {/* Left Column: HTML5 Video Player + Visual Overlay Viewer */}
        <div className="lg:col-span-7 p-5 flex flex-col bg-slate-950/40 border-r border-slate-800/80">
          {/* Main Visual Frame */}
          <div className="relative rounded-lg overflow-hidden bg-black border border-slate-800 aspect-video flex items-center justify-center group">
            {activeViewMode === "video" ? (
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                playsInline
                className="w-full h-full object-contain"
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onTimeUpdate={handleTimeUpdate}
              />
            ) : activeViewMode === "annotated" && selectedFlag?.overlay_url ? (
              <img
                src={`${apiBase}${selectedFlag.overlay_url}`}
                alt="Annotated Detection Keyframe"
                className="w-full h-full object-contain"
              />
            ) : activeViewMode === "mask" && selectedFlag?.mask_url ? (
              <img
                src={`${apiBase}${selectedFlag.mask_url}`}
                alt="SAM 2 Segmentation Mask"
                className="w-full h-full object-contain"
              />
            ) : (
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                playsInline
                className="w-full h-full object-contain"
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onTimeUpdate={handleTimeUpdate}
              />
            )}

            {/* Mode Switcher Pill */}
            {selectedFlag && (
              <div className="absolute top-3 right-3 flex bg-slate-900/90 backdrop-blur-md rounded-lg p-1 border border-slate-700 text-xs shadow-lg space-x-1">
                <button
                  type="button"
                  onClick={() => setActiveViewMode("video")}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    activeViewMode === "video"
                      ? "bg-emerald-500 text-slate-950 font-medium"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Footage
                </button>
                {selectedFlag.overlay_url && (
                  <button
                    type="button"
                    onClick={() => setActiveViewMode("annotated")}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      activeViewMode === "annotated"
                        ? "bg-emerald-500 text-slate-950 font-medium"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    Overlay Box
                  </button>
                )}
                {selectedFlag.mask_url && (
                  <button
                    type="button"
                    onClick={() => setActiveViewMode("mask")}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      activeViewMode === "mask"
                        ? "bg-emerald-500 text-slate-950 font-medium"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    SAM 2 Mask
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Interactive Timeline Bar */}
          <div className="mt-4 px-1">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-mono">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                {currentTime.toFixed(2)}s / {duration.toFixed(2)}s
              </span>
              <span>{flags.length} Flagged Moment(s)</span>
            </div>

            {/* Progress Track & Marker Pins */}
            <div className="relative w-full h-4 bg-slate-800 rounded cursor-pointer overflow-hidden group/timeline">
              {/* Playback Progress */}
              <div
                className="absolute top-0 bottom-0 left-0 bg-emerald-500/30"
                style={{ width: `${Math.min(100, (currentTime / duration) * 100)}%` }}
              />

              {/* Event Flags on Timeline */}
              {flags.map((flag) => {
                const leftPct = Math.max(0, (flag.start_timestamp / duration) * 100);
                const widthPct = Math.max(1.5, ((flag.end_timestamp - flag.start_timestamp) / duration) * 100);
                const isSelected = flag.flag_id === selectedFlag?.flag_id;

                return (
                  <div
                    key={flag.flag_id}
                    title={`${flag.label}: ${flag.start_timestamp.toFixed(1)}s - ${flag.end_timestamp.toFixed(1)}s (Event Score: ${flag.event_score})`}
                    onClick={() => {
                      setSelectedFlagId(flag.flag_id);
                      handleSeek(flag.start_timestamp);
                    }}
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                    className={`absolute top-0 bottom-0 transition-all ${
                      isSelected
                        ? "bg-emerald-400 ring-2 ring-emerald-300 z-10"
                        : "bg-amber-400 hover:bg-amber-300 z-0"
                    }`}
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Flagged Events List & Detail Inspection */}
        <div className="lg:col-span-5 p-5 flex flex-col bg-slate-900">
          <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Crosshair className="w-4 h-4 text-emerald-400" />
              Flagged Important Moments
            </h3>
            <span className="text-xs text-slate-500">
              {flags.length > 0 ? `${flags.length} event(s) discovered` : "No events"}
            </span>
          </div>

          {flags.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-lg flex-1">
              <CheckCircle2 className="w-10 h-10 text-slate-600 mb-2" />
              <p className="text-sm font-medium text-slate-400">NO_RELEVANT_EVENTS_FOUND</p>
              <p className="text-xs text-slate-500 mt-1 max-w-xs">
                {workflowReason || "No candidate detections satisfied temporal persistence and event score thresholds."}
              </p>
            </div>
          ) : (
            <div className="space-y-3 overflow-y-auto max-h-[460px] pr-1 flex-1 custom-scrollbar">
              {flags.map((flag, idx) => {
                const isSelected = flag.flag_id === selectedFlag?.flag_id;
                return (
                  <div
                    key={flag.flag_id}
                    onClick={() => {
                      setSelectedFlagId(flag.flag_id);
                      handleSeek(flag.start_timestamp);
                    }}
                    className={`p-3 rounded-lg border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-slate-800/90 border-emerald-500/80 shadow-md shadow-emerald-950/30"
                        : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-bold text-emerald-400 uppercase">
                            #{idx + 1} {flag.label}
                          </span>
                          <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">
                            {flag.start_timestamp.toFixed(2)}s – {flag.end_timestamp.toFixed(2)}s
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{flag.reason}</p>
                      </div>

                      {/* Transparent Heuristic Event Score Badge */}
                      <div className="text-right shrink-0">
                        <div className="text-xs font-bold text-slate-200 font-mono">
                          {flag.event_score.toFixed(2)}
                        </div>
                        <div className="text-[9px] text-slate-500 uppercase tracking-tight">
                          Event Score*
                        </div>
                      </div>
                    </div>

                    {/* Detailed Signals when selected */}
                    {isSelected && (
                      <div className="mt-3 pt-3 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[11px]">
                        <div className="bg-slate-950/70 p-2 rounded border border-slate-800/60">
                          <span className="text-slate-500 block">Detector Score:</span>
                          <span className="font-mono text-slate-300 font-medium">
                            {flag.model_scores?.detector_score ?? "N/A"}
                          </span>
                        </div>
                        <div className="bg-slate-950/70 p-2 rounded border border-slate-800/60">
                          <span className="text-slate-500 block">V4 Reasoning:</span>
                          <span className="font-mono text-slate-300 font-medium">
                            {flag.model_scores?.reasoning_score ?? "N/A"}
                          </span>
                        </div>
                        <div className="bg-slate-950/70 p-2 rounded border border-slate-800/60">
                          <span className="text-slate-500 block">SAM 2 Mask:</span>
                          <span className="font-mono text-slate-300 font-medium">
                            {flag.model_scores?.segmentation_score ?? "N/A"}
                          </span>
                        </div>
                        <div className="bg-slate-950/70 p-2 rounded border border-slate-800/60">
                          <span className="text-slate-500 block">Persistence:</span>
                          <span className="font-mono text-slate-300 font-medium">
                            {flag.model_scores?.persistence_seconds ? `${flag.model_scores.persistence_seconds.toFixed(2)}s` : "N/A"}
                          </span>
                        </div>

                        <div className="col-span-2 mt-1">
                          <p className="text-[10px] text-slate-500 italic">
                            * Note: Heuristic event-ranking score; not calibrated model probability.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
