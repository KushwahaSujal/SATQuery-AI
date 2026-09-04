"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { VideoJobResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const fmt = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = (s % 60).toFixed(1).padStart(4, "0");
  return `${m}:${sec}`;
};

export default function VideoIntelligencePage() {
  const { jobId } = useParams<{ jobId: string }>();

  const { data: videoJob, isLoading } = useQuery({
    queryKey: ["video-job", jobId],
    queryFn: () => api.videoJob(jobId),
    refetchInterval: (q) => (["RUNNING", "PENDING"].includes(q.state.data?.status ?? "") ? 2000 : false),
  });

  const results = videoJob ?? {
    job_id: jobId,
    status: isLoading ? "LOADING" : "NO_DATA",
    query: "Video Tracking & Intelligence",
    events: [],
    keyframes: [],
    models_used: ["SAM 2.1", "Grounding DINO"],
  };
  const totalSec = 45.2;
  const videoStreamUrl = api.videoStreamUrl(jobId);

  return (
    <div className="flex flex-col border border-[#1a1a1a] rounded-lg overflow-hidden animate-fade-in" style={{ height: "calc(100vh - 80px)" }}>
      {/* Breadcrumb */}
      <div className="flex items-center gap-3 px-4 h-10 border-b border-[#1a1a1a] bg-[#0a0a0a] shrink-0">
        <Link href="/" className="font-mono-data text-[11px] text-[#333] hover:text-[#737373] transition-colors">
          ← command center
        </Link>
        <span className="text-[#222]">/</span>
        <span className="font-mono-data text-[11px] text-[#404040]">{jobId}</span>
        <span className="text-[#222]">/</span>
        <span className="font-mono-data text-[11px] text-[#737373]">video intelligence</span>
        <div className="flex-1" />
        <span className="font-mono-data text-[10px] text-[#4ade80]">{results.status || "COMPLETED"}</span>
      </div>

      {/* Query */}
      <div className="px-4 py-2.5 border-b border-[#1a1a1a] shrink-0">
        <span className="font-mono-data text-[10px] text-[#333]">QUERY </span>
        <span className="font-mono-data text-[12px] text-[#737373]">"{results.query}"</span>
      </div>

      {/* Workspace */}
      <div className="flex flex-1 min-h-0 divide-x divide-[#1a1a1a]">
        {/* Video player column */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="panel-header shrink-0">
            <span className="panel-label">Video Feed</span>
            <span className="font-mono-data text-[10px] text-[#333]">H264 Stream · Realtime SAM2 / ByteTrack</span>
          </div>

          {/* Player */}
          <div className="flex-1 bg-[#050505] flex items-center justify-center relative overflow-hidden">
            <video
              src={videoStreamUrl}
              controls
              className="w-full h-full object-contain max-h-[500px]"
              onError={(e) => {
                // If stream fails, show placeholder info box
                (e.currentTarget as HTMLElement).style.display = "none";
              }}
            />

            <div className="text-center space-y-1 p-4 bg-[#080808]/80 rounded border border-[#1a1a1a]">
              <p className="font-mono-data text-[11px] text-[#737373]">Stream Endpoint: /api/video/{jobId}/stream</p>
              <p className="font-mono-data text-[10px] text-[#404040]">Realtime object detection bounding boxes & keyframe extraction</p>
            </div>
          </div>

          {/* Timeline */}
          <div className="px-4 py-3 border-t border-[#1a1a1a] shrink-0 bg-[#0a0a0a]">
            <div className="flex items-center gap-2 mb-2">
              <span className="panel-label">Event Timeline</span>
              <span className="font-mono-data text-[10px] text-[#333]">0:00 → {fmt(totalSec)}</span>
            </div>
            <div className="relative h-1.5 bg-[#111] rounded-full">
              {results.events?.map((ev) => {
                const pct = Math.min((ev.timestamp_sec / totalSec) * 100, 98);
                return (
                  <div
                    key={ev.id}
                    className="absolute -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-[#60a5fa] -top-0.5 cursor-pointer hover:scale-125 transition-transform"
                    style={{ left: `${pct}%` }}
                    title={`${fmt(ev.timestamp_sec)} — ${ev.label}`}
                  />
                );
              })}
            </div>
          </div>
        </div>

        {/* Events column */}
        <div className="w-[280px] shrink-0 flex flex-col min-h-0">
          <div className="panel-header shrink-0">
            <span className="panel-label">Detected Events</span>
            <span className="font-mono-data text-[10px] text-[#333]">{results.events?.length ?? 0} events</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-[#1a1a1a]">
            {results.events && results.events.length > 0 ? (
              results.events.map((ev) => (
                <div key={ev.id} className="p-4 hover:bg-[#0d0d0d] transition-colors">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono-data text-[11px] text-[#60a5fa]">{fmt(ev.timestamp_sec)}</span>
                    {ev.track_id && <span className="font-mono-data text-[10px] text-[#2a2a2a]">{ev.track_id}</span>}
                  </div>
                  <p className="text-[12px] text-[#737373] leading-relaxed">{ev.label}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="font-mono-data text-[10px] text-[#2a2a2a]">confidence score</span>
                    <span
                      className={cn(
                        "font-mono-data text-[11px] font-semibold",
                        ev.score > 0.9 ? "text-[#4ade80]" : ev.score > 0.75 ? "text-[#fbbf24]" : "text-[#737373]"
                      )}
                    >
                      {ev.score.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center font-mono-data text-[11px] text-[#404040]">No events detected</div>
            )}
          </div>

          {/* Pipeline */}
          <div className="p-4 border-t border-[#1a1a1a] shrink-0 bg-[#0a0a0a]">
            <span className="panel-label block mb-2">Models Executed</span>
            {results.models_used?.map((m) => (
              <div key={m} className="flex items-center gap-2 py-0.5">
                <span className="font-mono-data text-[10px] text-[#2a2a2a]">○</span>
                <span className="font-mono-data text-[11px] text-[#333]">{m}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
