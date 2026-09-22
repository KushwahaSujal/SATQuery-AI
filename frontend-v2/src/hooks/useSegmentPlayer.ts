"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface VideoSegment {
  id: string;
  start: number;
  end: number;
}

export type SegmentStatus = "idle" | "playing" | "paused" | "ended" | "blocked";

/** A single-frame event still gets a visible clip; otherwise pausing "at the end" would pause immediately. */
const MIN_SEGMENT_SEC = 1;
/** A manual seek further than this outside the active segment releases the segment. */
const SEEK_RELEASE_SEC = 0.25;

/**
 * Plays a [start, end] segment of a <video> and pauses exactly at `end`.
 *
 * `timeupdate` fires only ~4 times a second, which would overshoot the end by up to 250 ms, so the end is
 * checked on every animation frame while a segment plays.
 */
export function useSegmentPlayer() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const segmentRef = useRef<VideoSegment | null>(null);
  const frameRef = useRef<number | null>(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState<number | null>(null);
  const [activeSegment, setActiveSegment] = useState<VideoSegment | null>(null);
  const [status, setStatus] = useState<SegmentStatus>("idle");

  const stopWatching = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
  }, []);

  const startWatching = useCallback(() => {
    stopWatching();
    const watch = () => {
      const video = videoRef.current;
      const segment = segmentRef.current;
      if (!video) return;
      if (segment && video.currentTime >= segment.end) {
        video.pause();
        video.currentTime = segment.end;
        setCurrentTime(segment.end);
        setStatus("ended");
        segmentRef.current = null;
        frameRef.current = null;
        return;
      }
      setCurrentTime(video.currentTime);
      frameRef.current = requestAnimationFrame(watch);
    };
    frameRef.current = requestAnimationFrame(watch);
  }, [stopWatching]);

  const playSegment = useCallback(
    (segment: VideoSegment) => {
      const video = videoRef.current;
      if (!video) return;
      const clip: VideoSegment = {
        ...segment,
        end: segment.end > segment.start ? segment.end : segment.start + MIN_SEGMENT_SEC,
      };
      segmentRef.current = clip;
      setActiveSegment(clip);

      const begin = () => {
        video.currentTime = clip.start;
        setCurrentTime(clip.start);
        video
          .play()
          .catch(() => {
            // Browsers refuse unmuted autoplay without a user gesture; muted playback is always allowed.
            video.muted = true;
            return video.play();
          })
          .then(() => {
            setStatus("playing");
            startWatching();
          })
          .catch(() => setStatus("blocked"));
      };

      if (video.readyState >= HTMLMediaElement.HAVE_METADATA) begin();
      else video.addEventListener("loadedmetadata", begin, { once: true });
    },
    [startWatching]
  );

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onMetadata = () => setDuration(Number.isFinite(video.duration) ? video.duration : null);
    const onTime = () => {
      if (frameRef.current === null) setCurrentTime(video.currentTime);
    };
    const onPause = () => {
      if (segmentRef.current) setStatus("paused");
    };
    const onPlay = () => {
      if (segmentRef.current) {
        setStatus("playing");
        startWatching();
      } else {
        stopWatching();
      }
    };
    const onSeeked = () => {
      const segment = segmentRef.current;
      if (
        segment &&
        (video.currentTime < segment.start - SEEK_RELEASE_SEC || video.currentTime > segment.end + SEEK_RELEASE_SEC)
      ) {
        segmentRef.current = null;
        setActiveSegment(null);
        setStatus("idle");
        stopWatching();
      }
      setCurrentTime(video.currentTime);
    };

    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) onMetadata();
    video.addEventListener("loadedmetadata", onMetadata);
    video.addEventListener("timeupdate", onTime);
    video.addEventListener("pause", onPause);
    video.addEventListener("play", onPlay);
    video.addEventListener("seeked", onSeeked);
    return () => {
      video.removeEventListener("loadedmetadata", onMetadata);
      video.removeEventListener("timeupdate", onTime);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("seeked", onSeeked);
      stopWatching();
    };
  }, [startWatching, stopWatching]);

  const seek = useCallback((seconds: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = seconds;
    setCurrentTime(seconds);
  }, []);

  return { videoRef, currentTime, duration, activeSegment, status, playSegment, seek };
}
