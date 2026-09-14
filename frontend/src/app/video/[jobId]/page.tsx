"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
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

  const events =
    videoJob?.flags?.map((f) => ({
      id: f.flag_id,
      timestamp_sec: f.start_timestamp,
      end_sec: f.end_timestamp,
      label: f.label,
      score: f.event_score,
      keyframe_url: f.keyframe_url,
      track_id: undefined as string | undefined,
    })) ?? results.events ?? [];

  const totalSec = videoJob?.video_metadata?.duration_sec ?? 45.2;
  const videoStreamUrl = api.videoStreamUrl(jobId);

  return (
    <div className="flex flex-col border border-[var(--b1)] rounded-lg overflow-hidden animate-fade-in" style={{ height: "calc(100vh - 80px)" }}>
      {/* Breadcrumb */}
      <div className="flex items-center gap-3 px-4 h-10 border-b border-[var(--b1)] bg-[var(--s1)] shrink-0">
        <Link href="/" className="font-mono-data text-[11px] text-[var(--t3)] hover:text-[var(--t2)] transition-colors">
          ← command center
        </Link>
        <span className="text-[var(--b2)]">/</span>
        <span className="font-mono-data text-[11px] text-[var(--t4)]">{jobId}</span>
        <span className="text-[var(--b2)]">/</span>
        <span className="font-mono-data text-[11px] text-[var(--t2)]">video intelligence</span>
        <div className="flex-1" />
        <span className={`font-mono-data text-[10px] px-2 py-0.5 rounded ${
          results.status === "COMPLETED" ? "text-[var(--green)] bg-[var(--green-dim)]"
          : results.status === "FAILED" ? "text-[var(--red)] bg-[var(--red-dim)]"
          : results.status === "LOADING" ? "text-[var(--amber)] bg-[var(--amber-dim)]"
          : "text-[var(--t4)] bg-[var(--s2)]"
        }`}>
          {results.status || "—"}
        </span>
      </div>

      {/* Query */}
      <div className="px-4 py-2.5 border-b border-[var(--b1)] shrink-0">
        <span className="font-mono-data text-[10px] text-[var(--t3)]">QUERY </span>
        <span className="font-mono-data text-[12px] text-[var(--t2)]">&ldquo;{results.query}&rdquo;</span>
      </div>

      {/* Workspace */}
      <div className="flex flex-1 min-h-0 divide-x divide-[var(--b1)]">
        {/* Video player column */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="panel-header shrink-0">
            <span className="panel-label">Video Feed</span>
            <span className="font-mono-data text-[10px] text-[var(--t3)]">
              {videoJob?.video_metadata?.codec || "H264"}
            </span>
          </div>

          {/* Player */}
          <div className="flex-1 bg-[var(--s0)] flex items-center justify-center relative overflow-hidden">
            <video
              src={videoStreamUrl}
              controls
              className="w-full h-full object-contain max-h-[500px]"
              onError={(e) => {
                (e.currentTarget as HTMLElement).style.display = "none";
              }}
            />

            <div className="text-center space-y-1 p-4 bg-[var(--s1)]/80 rounded border border-[var(--b1)]">
              <p className="font-mono-data text-[11px] text-[var(--t2)]">
                Stream: /api/video/{jobId}/stream
              </p>
              <p className="font-mono-data text-[10px] text-[var(--t4)]">
                Object detection & keyframe extraction
              </p>
            </div>
          </div>

          {/* Timeline */}
          <div className="px-4 py-3 border-t border-[var(--b1)] shrink-0 bg-[var(--s1)]">
            <div className="flex items-center gap-2 mb-2">
              <span className="panel-label">Event Timeline</span>
              <span className="font-mono-data text-[10px] text-[var(--t3)]">0:00 → {fmt(totalSec)}</span>
            </div>
            <div className="relative h-1.5 bg-[var(--s2)] rounded-full">
              {events.map((ev) => {
                const pct = Math.min((ev.timestamp_sec / totalSec) * 100, 98);
                return (
                  <div
                    key={ev.id}
                    className="absolute -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-[var(--accent-text)] -top-0.5 cursor-pointer hover:scale-125 transition-transform"
                    style={{ left: `${pct}%` }}
                    title={
                      "end_sec" in ev && typeof ev.end_sec === "number" && ev.end_sec > ev.timestamp_sec
                        ? `${fmt(ev.timestamp_sec)} → ${fmt(ev.end_sec)} — ${ev.label}`
                        : `${fmt(ev.timestamp_sec)} — ${ev.label}`
                    }
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
            <span className="font-mono-data text-[10px] text-[var(--t3)]">{events.length} events</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-[var(--b1)]">
            {events.length > 0 ? (
              events.map((ev) => (
                <div key={ev.id} className="p-4 hover:bg-[var(--s2)] transition-colors">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono-data text-[11px] text-[var(--accent-text)]">
                      {fmt(ev.timestamp_sec)}
                      {"end_sec" in ev && typeof ev.end_sec === "number" && ev.end_sec > ev.timestamp_sec && (
                        <>
                          <span className="text-[var(--t4)]"> → </span>
                          {fmt(ev.end_sec)}
                          <span className="text-[var(--t4)] ml-1.5">
                            ({(ev.end_sec - ev.timestamp_sec).toFixed(1)}s)
                          </span>
                        </>
                      )}
                    </span>
                    {ev.track_id && <span className="font-mono-data text-[10px] text-[var(--t4)]">{ev.track_id}</span>}
                  </div>
                  <p className="text-[12px] text-[var(--t2)] leading-relaxed">{ev.label}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="font-mono-data text-[10px] text-[var(--t4)]">event score</span>
                    <span
                      className={cn(
                        "font-mono-data text-[11px] font-semibold",
                        ev.score > 0.9 ? "text-[var(--green)]" : ev.score > 0.75 ? "text-[var(--amber)]" : "text-[var(--t2)]"
                      )}
                    >
                      {ev.score.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              (() => {
                const reason = videoJob?.workflow_reason ?? "";
                const notApplicable = reason.startsWith("NOT_APPLICABLE");
                const failed = reason.startsWith("DETECTION_FAILED");
                const heading = notApplicable
                  ? "Not applicable"
                  : failed
                    ? "Detection failed"
                    : "No events detected";
                const detail = reason.includes(":") ? reason.slice(reason.indexOf(":") + 1).trim() : "";
                return (
                  <div className="p-4 text-center">
                    <p
                      className={cn(
                        "font-mono-data text-[11px] mb-1.5",
                        notApplicable ? "text-[var(--amber)]" : failed ? "text-[var(--red)]" : "text-[var(--t4)]"
                      )}
                    >
                      {heading}
                    </p>
                    {detail && (
                      <p className="text-[11px] text-[var(--t3)] leading-relaxed text-left">{detail}</p>
                    )}
                  </div>
                );
              })()
            )}
          </div>

          {/* Pipeline */}
          <div className="p-4 border-t border-[var(--b1)] shrink-0 bg-[var(--s1)]">
            <span className="panel-label block mb-2">Models Executed</span>
            {results.models_used?.map((m) => (
              <div key={m} className="flex items-center gap-2 py-0.5">
                <span className="font-mono-data text-[10px] text-[var(--t4)]">○</span>
                <span className="font-mono-data text-[11px] text-[var(--t3)]">{m}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
