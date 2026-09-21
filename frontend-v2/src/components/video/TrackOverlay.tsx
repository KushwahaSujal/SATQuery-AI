"use client";

import { useEffect, useState, type RefObject } from "react";
import type { VideoTrackPoint } from "@/lib/types";

export interface ObjectTrack {
  id: string;
  label: string;
  score: number;
  points: VideoTrackPoint[];
}

interface TrackOverlayProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  tracks: ObjectTrack[];
  activeId?: string | null;
}

/** Track points are ~0.1 s apart; a wider gap means the object was not visible, so no box is drawn across it. */
const MAX_GAP_SEC = 0.5;
/** Keep the box for a moment past the first/last point so it does not flicker at the edges. */
const EDGE_SEC = 0.15;

interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** The area inside the <video> element where frames are actually drawn (object-contain letterboxing). */
function contentRect(video: HTMLVideoElement): Rect | null {
  const { videoWidth, videoHeight, offsetWidth, offsetHeight, offsetLeft, offsetTop } = video;
  if (!videoWidth || !videoHeight || !offsetWidth || !offsetHeight) return null;
  const scale = Math.min(offsetWidth / videoWidth, offsetHeight / videoHeight);
  const width = videoWidth * scale;
  const height = videoHeight * scale;
  return { left: offsetLeft + (offsetWidth - width) / 2, top: offsetTop + (offsetHeight - height) / 2, width, height };
}

function boxAt(points: VideoTrackPoint[], t: number): VideoTrackPoint | null {
  if (points.length === 0) return null;
  const first = points[0];
  const last = points[points.length - 1];
  if (t < first.t - EDGE_SEC || t > last.t + EDGE_SEC) return null;
  if (t <= first.t) return first;
  if (t >= last.t) return last;
  const next = points.findIndex((p) => p.t >= t);
  const a = points[next - 1];
  const b = points[next];
  if (b.t - a.t > MAX_GAP_SEC) return null;
  const k = (t - a.t) / (b.t - a.t);
  const box = a.box_2d.map((v, i) => v + (b.box_2d[i] - v) * k) as VideoTrackPoint["box_2d"];
  return { ...a, t, box_2d: box, rgb: k < 0.5 ? a.rgb : b.rgb };
}

/**
 * Draws an outline box (no fill, so the object's real colour stays visible) that follows each tracked object
 * while the video plays, with the label and a swatch of the object's measured colour.
 */
export default function TrackOverlay({ videoRef, tracks, activeId }: TrackOverlayProps) {
  const [time, setTime] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let frame: number | null = null;

    const measure = () => setRect(contentRect(video));
    const sync = () => setTime(video.currentTime);
    const loop = () => {
      sync();
      frame = video.paused ? null : requestAnimationFrame(loop);
    };
    const onPlay = () => {
      if (frame === null) frame = requestAnimationFrame(loop);
    };

    measure();
    sync();
    const resize = new ResizeObserver(measure);
    resize.observe(video);
    video.addEventListener("loadedmetadata", measure);
    video.addEventListener("play", onPlay);
    video.addEventListener("seeked", sync);
    video.addEventListener("pause", sync);
    if (!video.paused) onPlay();
    return () => {
      resize.disconnect();
      video.removeEventListener("loadedmetadata", measure);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("seeked", sync);
      video.removeEventListener("pause", sync);
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [videoRef]);

  if (!rect) return null;

  return (
    <div
      className="absolute pointer-events-none"
      style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }}
      data-testid="track-overlay"
    >
      {tracks.map((track) => {
        const point = boxAt(track.points, time);
        if (!point) return null;
        const [ymin, xmin, ymax, xmax] = point.box_2d;
        const active = !activeId || activeId === track.id;
        const swatch = point.rgb ? `rgb(${point.rgb.join(",")})` : null;
        return (
          <div
            key={track.id}
            data-testid="track-box"
            className="absolute rounded-sm"
            style={{
              left: `${xmin * 100}%`,
              top: `${ymin * 100}%`,
              width: `${(xmax - xmin) * 100}%`,
              height: `${(ymax - ymin) * 100}%`,
              border: `2px solid ${active ? "#22d3ee" : "rgba(34,211,238,0.5)"}`,
              boxShadow: "0 0 0 1px rgba(0,0,0,0.7)",
            }}
          >
            <div
              className="absolute left-0 flex items-center gap-1.5 whitespace-nowrap font-mono-data text-[10px] px-1.5 py-0.5 rounded-sm bg-black/75 text-[#22d3ee]"
              style={ymin > 0.06 ? { bottom: "100%", marginBottom: 2 } : { top: "100%", marginTop: 2 }}
            >
              {swatch && (
                <span
                  data-testid="track-colour"
                  className="inline-block w-2.5 h-2.5 rounded-[2px] border border-white/60"
                  style={{ backgroundColor: swatch }}
                  title={`Measured object colour ${swatch}`}
                />
              )}
              <span>
                {track.label} · {track.score.toFixed(2)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
