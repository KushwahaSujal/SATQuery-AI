"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { mediaUrl } from "@/lib/connection";
import { cn } from "@/lib/utils";
import { useSegmentPlayer } from "@/hooks/useSegmentPlayer";
import TrackOverlay, { type ObjectTrack } from "@/components/video/TrackOverlay";

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
      keyframe_url: f.keyframe_url ? mediaUrl(f.keyframe_url) : undefined,
      track_id: undefined as string | undefined,
    })) ?? results.events ?? [];

  const videoStreamUrl = api.videoStreamUrl(jobId);
  const { videoRef, currentTime, duration, activeSegment, status, playSegment, seek } = useSegmentPlayer();
  const [videoError, setVideoError] = useState(false);
  const tracks: ObjectTrack[] = (videoJob?.flags ?? [])
    .filter((f) => (f.metadata?.track?.length ?? 0) > 0)
    .map((f) => ({ id: f.flag_id, label: f.label, score: f.event_score, points: f.metadata!.track! }));
  // The old fallback was a hard-coded 45.2 s, which misplaced every marker on any other clip.
  const totalSec = duration ?? videoJob?.video_metadata?.duration_sec ?? 0;
  const pctOf = (sec: number) => (totalSec > 0 ? Math.min(Math.max((sec / totalSec) * 100, 0), 100) : 0);
  const segmentOf = (ev: (typeof events)[number]) => ({
    id: ev.id,
    start: ev.timestamp_sec,
    end: "end_sec" in ev && typeof ev.end_sec === "number" ? ev.end_sec : ev.timestamp_sec,
  });

  // Auto-play the first detected event once, as soon as results arrive.
  const autoPlayed = useRef(false);
  const firstEvent = events[0];
  useEffect(() => {
    if (autoPlayed.current || !firstEvent) return;
    autoPlayed.current = true;
    playSegment(segmentOf(firstEvent));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firstEvent?.id, playSegment]);

  const inActiveSegment =
    activeSegment !== null && currentTime >= activeSegment.start - 0.05 && currentTime <= activeSegment.end + 0.05;
  const statusText =
    status === "playing" ? "Playing event"
    : status === "paused" ? "Paused in event"
    : status === "ended" ? "Stopped at event end"
    : status === "blocked" ? "Click an event to play"
    : "";

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
              ref={videoRef}
              src={videoStreamUrl}
              controls
              playsInline
              preload="metadata"
              className={cn("w-full h-full object-contain max-h-[500px]", videoError && "hidden")}
              onError={() => setVideoError(true)}
            />

            {!videoError && <TrackOverlay videoRef={videoRef} tracks={tracks} activeId={activeSegment?.id} />}

            {activeSegment && statusText && (
              <div
                data-testid="segment-status"
                className={cn(
                  "absolute top-3 left-3 font-mono-data text-[11px] px-2.5 py-1 rounded border",
                  status === "playing"
                    ? "text-[var(--accent-text)] bg-[var(--accent-dim)] border-[var(--accent)]"
                    : "text-[var(--amber)] bg-[var(--amber-dim)] border-[var(--amber)]"
                )}
              >
                {statusText} · {fmt(activeSegment.start)} → {fmt(activeSegment.end)}
              </div>
            )}

            {videoError && (
              <div className="text-center space-y-1 p-4 bg-[var(--s1)]/80 rounded border border-[var(--b1)]">
                <p className="font-mono-data text-[11px] text-[var(--t2)]">
                  Video stream unavailable: /api/video/{jobId}/stream
                </p>
              </div>
            )}
          </div>

          {/* Timeline */}
          <div className="px-4 py-3 border-t border-[var(--b1)] shrink-0 bg-[var(--s1)]">
            <div className="flex items-center gap-2 mb-2">
              <span className="panel-label">Event Timeline</span>
              <span className="font-mono-data text-[10px] text-[var(--t3)]">
                {fmt(currentTime)} / {fmt(totalSec)}
              </span>
            </div>
            <div
              data-testid="event-timeline"
              className="relative h-2 bg-[var(--s2)] rounded-full cursor-pointer"
              onClick={(e) => {
                if (totalSec <= 0) return;
                const rect = e.currentTarget.getBoundingClientRect();
                seek(((e.clientX - rect.left) / rect.width) * totalSec);
              }}
            >
              {events.map((ev) => {
                const seg = segmentOf(ev);
                const active = activeSegment?.id === ev.id;
                return (
                  <button
                    key={ev.id}
                    type="button"
                    aria-label={`Play event ${fmt(seg.start)} to ${fmt(seg.end)}`}
                    className={cn(
                      "absolute top-0 h-full rounded-full transition-colors min-w-[6px]",
                      active ? "bg-[var(--accent)]" : "bg-[var(--accent-text)]/50 hover:bg-[var(--accent-text)]"
                    )}
                    style={{ left: `${pctOf(seg.start)}%`, width: `${Math.max(pctOf(seg.end) - pctOf(seg.start), 0)}%` }}
                    title={`${fmt(seg.start)} → ${fmt(seg.end)} — ${ev.label}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      playSegment(seg);
                    }}
                  />
                );
              })}
              {totalSec > 0 && (
                <div
                  data-testid="playhead"
                  data-highlighted={inActiveSegment ? "true" : "false"}
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                  style={{ left: `${pctOf(currentTime)}%` }}
                >
                  <div
                    className={cn(
                      "w-1 h-5 rounded-full transition-[background-color,box-shadow]",
                      inActiveSegment
                        ? "bg-[var(--amber)] shadow-[0_0_0_3px_var(--amber-dim),0_0_12px_var(--amber)]"
                        : "bg-[var(--t2)]",
                      inActiveSegment && status === "ended" && "animate-pulse"
                    )}
                  />
                </div>
              )}
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
                <button
                  key={ev.id}
                  type="button"
                  onClick={() => playSegment(segmentOf(ev))}
                  className={cn(
                    "block w-full text-left p-4 hover:bg-[var(--s2)] transition-colors border-l-2",
                    activeSegment?.id === ev.id ? "bg-[var(--accent-dim)] border-[var(--accent)]" : "border-transparent"
                  )}
                >
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
                  <span className="block mt-2 font-mono-data text-[10px] text-[var(--accent-text)]">
                    {activeSegment?.id === ev.id && status === "playing" ? "▶ playing…" : "▶ play this event"}
                  </span>
                </button>
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
