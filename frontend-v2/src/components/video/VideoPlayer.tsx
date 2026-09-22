"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Maximize,
  Minimize,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from "lucide-react";
import TrackOverlay, { type ObjectTrack } from "@/components/video/TrackOverlay";
import { useSegmentPlayer } from "@/hooks/useSegmentPlayer";
import { DURATION, EASE } from "@/lib/motion";
import type { VideoFlag } from "@/lib/types";

/**
 * Video player for an analysed clip.
 *
 * Three things the previous player did not do:
 *  - boxes the tracked object while it moves, from the per-frame track the backend
 *    already returns under flag.metadata.track;
 *  - skips between detected events rather than seeking blindly;
 *  - plays a single event from its start to its end and pauses exactly there.
 *
 * The event markers on the scrub bar are placed from real start/end timestamps, so a clip
 * with no detections simply has none -- the bar never shows invented activity.
 */
/** Imperative surface so a sibling list (e.g. "Detected events") can drive playback. */
export interface VideoPlayerHandle {
  /** Play one event from its start to its end, pausing exactly at the end. */
  playEvent: (flag: Pick<VideoFlag, "flag_id" | "start_timestamp" | "end_timestamp">) => void;
  /** Move the playhead without starting a segment. */
  seekTo: (seconds: number) => void;
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, {
  src: string;
  flags?: VideoFlag[];
  className?: string;
}>(function VideoPlayer({ src, flags = [], className = "" }, ref) {
  const { videoRef, currentTime, duration, activeSegment, status, playSegment, seek } =
    useSegmentPlayer();
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [scrubbing, setScrubbing] = useState(false);

  // Events sorted by time; this ordering is what prev/next step through.
  const events = useMemo(
    () => [...flags].sort((a, b) => a.start_timestamp - b.start_timestamp),
    [flags],
  );

  // Every event that actually carries per-frame tracking becomes a drawable track.
  const tracks: ObjectTrack[] = useMemo(
    () =>
      events
        .filter((f) => (f.metadata?.track?.length ?? 0) > 0)
        .map((f) => ({
          id: f.flag_id,
          label: f.label,
          score: f.event_score,
          points: f.metadata!.track!,
        })),
    [events],
  );

  const total = duration ?? 0;
  const progress = total > 0 ? Math.min(100, (currentTime / total) * 100) : 0;

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play().catch(() => {
        // Unmuted autoplay can be refused without a gesture; muting always succeeds.
        video.muted = true;
        setMuted(true);
        void video.play();
      });
    } else {
      video.pause();
    }
  }, [videoRef]);

  // The index of the event the playhead currently sits in, or the previous one.
  const currentEventIndex = useMemo(() => {
    if (events.length === 0) return -1;
    let idx = -1;
    for (let i = 0; i < events.length; i++) {
      if (currentTime >= events[i].start_timestamp - 0.05) idx = i;
      else break;
    }
    return idx;
  }, [events, currentTime]);

  const goToEvent = useCallback(
    (index: number) => {
      const target = events[index];
      if (!target) return;
      playSegment({
        id: target.flag_id,
        start: target.start_timestamp,
        end: target.end_timestamp,
      });
    },
    [events, playSegment],
  );

  const prevEvent = useCallback(() => {
    if (events.length === 0) return;
    // If we are partway into an event, the first press returns to its start.
    const active = events[currentEventIndex];
    if (active && currentTime > active.start_timestamp + 0.75) {
      goToEvent(currentEventIndex);
      return;
    }
    goToEvent(Math.max(0, currentEventIndex - 1));
  }, [events, currentEventIndex, currentTime, goToEvent]);

  const nextEvent = useCallback(() => {
    if (events.length === 0) return;
    goToEvent(Math.min(events.length - 1, currentEventIndex + 1));
  }, [events, currentEventIndex, goToEvent]);

  // Keep local play/mute state in step with the element, which the segment player also drives.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onVolume = () => {
      setMuted(video.muted);
      setVolume(video.volume);
    };
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("volumechange", onVolume);
    return () => {
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("volumechange", onVolume);
    };
  }, [videoRef]);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      playEvent: (flag) =>
        playSegment({
          id: flag.flag_id,
          start: flag.start_timestamp,
          end: flag.end_timestamp,
        }),
      seekTo: (seconds: number) => seek(seconds),
    }),
    [playSegment, seek],
  );

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement) void document.exitFullscreen();
    else void el.requestFullscreen?.();
  }, []);

  const scrubTo = useCallback(
    (clientX: number, bar: HTMLElement) => {
      if (!total) return;
      const rect = bar.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      seek(ratio * total);
    },
    [seek, total],
  );

  return (
    <div
      ref={containerRef}
      className={`group relative overflow-hidden rounded-xl border border-[var(--border)] bg-black ${className}`}
    >
      <video
        ref={videoRef}
        src={src}
        className="h-full w-full object-contain"
        playsInline
        onClick={togglePlay}
      />

      {/* Live boxes on the tracked object. */}
      <TrackOverlay videoRef={videoRef} tracks={tracks} activeId={activeSegment?.id ?? null} />

      {/* Centre play affordance, shown while paused. */}
      {!isPlaying && (
        <motion.button
          type="button"
          onClick={togglePlay}
          aria-label="Play"
          className="absolute inset-0 m-auto flex h-14 w-14 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur-sm"
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          transition={{ duration: DURATION.fast, ease: EASE }}
        >
          <Play className="ml-0.5 h-6 w-6" fill="currentColor" />
        </motion.button>
      )}

      {/* Controls */}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/55 to-transparent px-3 pb-2 pt-6">
        {/* Scrub bar with real event markers */}
        <div
          className="relative mb-2 h-3 cursor-pointer"
          onMouseDown={(e) => {
            setScrubbing(true);
            scrubTo(e.clientX, e.currentTarget);
          }}
          onMouseMove={(e) => scrubbing && scrubTo(e.clientX, e.currentTarget)}
          onMouseUp={() => setScrubbing(false)}
          onMouseLeave={() => setScrubbing(false)}
          role="slider"
          aria-label="Seek"
          aria-valuemin={0}
          aria-valuemax={Math.round(total)}
          aria-valuenow={Math.round(currentTime)}
          tabIndex={0}
        >
          <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/25" />
          <div
            className="absolute left-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-[var(--cyan)]"
            style={{ width: `${progress}%` }}
          />
          {/* One marker per detected event, at its real position in the clip. */}
          {total > 0 &&
            events.map((f) => {
              const left = (f.start_timestamp / total) * 100;
              const width = Math.max(0.6, ((f.end_timestamp - f.start_timestamp) / total) * 100);
              const isActive = activeSegment?.id === f.flag_id;
              return (
                <button
                  key={f.flag_id}
                  type="button"
                  title={`${f.label} · ${f.start_timestamp.toFixed(1)}s–${f.end_timestamp.toFixed(1)}s`}
                  aria-label={`Play event ${f.label}`}
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => {
                    e.stopPropagation();
                    playSegment({ id: f.flag_id, start: f.start_timestamp, end: f.end_timestamp });
                  }}
                  className={`absolute top-1/2 h-2 -translate-y-1/2 rounded-sm transition-colors ${
                    isActive ? "bg-[var(--amber)]" : "bg-[var(--amber)]/70 hover:bg-[var(--amber)]"
                  }`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                />
              );
            })}
          <div
            className="pointer-events-none absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--cyan)] opacity-0 transition-opacity group-hover:opacity-100"
            style={{ left: `${progress}%` }}
          />
        </div>

        <div className="flex items-center gap-2 text-white">
          <ControlButton onClick={prevEvent} label="Previous event" disabled={events.length === 0}>
            <SkipBack className="h-4 w-4" fill="currentColor" />
          </ControlButton>
          <ControlButton onClick={togglePlay} label={isPlaying ? "Pause" : "Play"}>
            {isPlaying ? (
              <Pause className="h-4 w-4" fill="currentColor" />
            ) : (
              <Play className="h-4 w-4" fill="currentColor" />
            )}
          </ControlButton>
          <ControlButton onClick={nextEvent} label="Next event" disabled={events.length === 0}>
            <SkipForward className="h-4 w-4" fill="currentColor" />
          </ControlButton>

          <span className="ml-1 font-mono-data text-[11px] tabular-nums text-white/85">
            {formatTime(currentTime)} / {formatTime(total)}
          </span>

          {events.length > 0 && (
            <span className="rounded bg-white/10 px-1.5 py-0.5 font-mono-data text-[10px] text-white/80">
              {currentEventIndex >= 0 ? `event ${currentEventIndex + 1}/${events.length}` : `${events.length} events`}
            </span>
          )}

          {status === "blocked" && (
            <span className="font-mono-data text-[10px] text-[var(--amber)]">
              playback blocked by the browser
            </span>
          )}

          <div className="ml-auto flex items-center gap-2">
            <ControlButton
              onClick={() => {
                const v = videoRef.current;
                if (!v) return;
                v.muted = !v.muted;
              }}
              label={muted ? "Unmute" : "Mute"}
            >
              {muted || volume === 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            </ControlButton>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={muted ? 0 : volume}
              aria-label="Volume"
              onChange={(e) => {
                const v = videoRef.current;
                if (!v) return;
                v.volume = Number(e.target.value);
                v.muted = Number(e.target.value) === 0;
              }}
              className="hidden h-1 w-16 cursor-pointer accent-[var(--cyan)] sm:block"
            />
            <ControlButton onClick={toggleFullscreen} label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
              {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </ControlButton>
          </div>
        </div>
      </div>
    </div>
  );
});

function ControlButton({
  children,
  onClick,
  label,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.12 }}
      whileTap={disabled ? undefined : { scale: 0.9 }}
      transition={{ duration: DURATION.fast, ease: EASE }}
      className="rounded p-1 text-white/90 hover:text-white disabled:cursor-not-allowed disabled:opacity-35"
    >
      {children}
    </motion.button>
  );
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}
