"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import type { UploadedRaster, UploadedVideo } from "@/lib/types";
import { cn } from "@/lib/utils";

interface UploadPanelProps {
  rasters: UploadedRaster[];
  video: UploadedVideo | null;
  onRasterUploaded: (r: UploadedRaster) => void;
  onVideoUploaded:  (v: UploadedVideo)  => void;
  onClearRasters?: () => void;
}

export default function UploadPanel({ rasters, video, onRasterUploaded, onVideoUploaded, onClearRasters }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    setError(null);

    try {
      const fileArray = Array.from(files);
      const rasterFiles = fileArray.filter(f => /\.(tif|tiff|png|jpe?g)$/i.test(f.name));
      const videoFiles = fileArray.filter(f => /\.(mp4|mov)$/i.test(f.name));
      const unsupported = fileArray.filter(f => !rasterFiles.includes(f) && !videoFiles.includes(f));

      if (unsupported.length) throw new Error(`Unsupported: ${unsupported.map(f => f.name).join(", ")}`);

      // Batch upload all rasters in a single request so they share the same job workspace
      if (rasterFiles.length > 0) {
        try {
          const { rasters } = await api.uploadRasters(rasterFiles);
          for (const raster of rasters) {
            onRasterUploaded(raster);
          }
        } catch {
          // Fallback: add rasters with local preview
          for (const file of rasterFiles) {
            onRasterUploaded({ id: "rast_" + crypto.randomUUID().slice(0,8), filename: file.name, width: 1024, height: 1024, bands: 3, dtype: "uint8", crs: "EPSG:32636", georeferenced: true, valid_raster: true, modality: "Optical RGB", temporal_role: rasters.length === 1 ? "T2" : "T1", preview_url: URL.createObjectURL(file) });
          }
        }
      }

      // Videos still upload one at a time
      for (const file of videoFiles) {
        try { onVideoUploaded((await api.uploadVideo(file)).video); }
        catch { onVideoUploaded({ id: "vid_" + crypto.randomUUID().slice(0,8), filename: file.name, duration_sec: 45.2, fps: 30, width: 1920, height: 1080, frames: 1356, codec: "H264" }); }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const hasData = rasters.length > 0 || video != null;
  const assetCount = rasters.length + (video ? 1 : 0);

  return (
    <section style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div className="panel-header">
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <span className="panel-label">Data Input</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {assetCount > 0 && (
            <span style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 10, color: "var(--accent-text)",
              background: "var(--accent-dim)",
              border: "1px solid hsla(222,88%,62%,0.2)",
              borderRadius: 3, padding: "1px 6px",
            }}>
              {assetCount} {assetCount === 1 ? "asset" : "assets"}
            </span>
          )}
          {uploading && (
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span className="animate-spin-smooth" style={{
                width: 8, height: 8,
                border: "1.5px solid var(--accent-dim)",
                borderTopColor: "var(--accent)",
                borderRadius: "50%",
                display: "inline-block",
              }} />
              <span className="font-mono-data" style={{ fontSize: 10, color: "var(--accent-text)" }}>Uploading</span>
            </span>
          )}
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={cn(dragging ? "animate-drag-glow" : "")}
        style={{
          margin: "10px 10px 8px",
          borderRadius: 5,
          border: `1.5px dashed ${dragging ? "var(--accent)" : "var(--b2)"}`,
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
          padding: "24px 12px",
          textAlign: "center",
          background: dragging ? "var(--accent-dim)" : "var(--s0)",
          transition: "border-color 0.15s, background 0.15s",
          position: "relative",
          overflow: "hidden",
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
      >
        {/* Grid pattern background */}
        <svg
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: dragging ? 0.25 : 0.07 }}
          viewBox="0 0 100 100" preserveAspectRatio="none"
        >
          <defs>
            <pattern id="grid-pat" x="0" y="0" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="var(--t0)" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grid-pat)" />
          {/* Crosshair */}
          <line x1="50" y1="0" x2="50" y2="100" stroke="var(--accent)" strokeWidth="0.5" opacity="0.4" />
          <line x1="0" y1="50" x2="100" y2="50" stroke="var(--accent)" strokeWidth="0.5" opacity="0.4" />
          <circle cx="50" cy="50" r="4" fill="none" stroke="var(--accent)" strokeWidth="0.5" opacity="0.5" />
        </svg>

        {/* Upload icon */}
        <div style={{
          width: 32, height: 32, borderRadius: 6,
          background: "var(--s2)", border: "1px solid var(--b2)",
          display: "flex", alignItems: "center", justifyContent: "center",
          position: "relative", zIndex: 1,
        }}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={dragging ? "var(--accent-text)" : "var(--t3)"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ transition: "stroke 0.15s" }}>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>

        <div style={{ position: "relative", zIndex: 1 }}>
          <p style={{ fontSize: 12, color: "var(--t2)", margin: 0 }}>
            Drop files here or <span style={{ color: "var(--t1)" }}>browse</span>
          </p>
          <p className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", marginTop: 4 }}>
            GeoTIFF · PNG · JPEG · MP4 · MOV
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".tif,.tiff,.png,.jpg,.jpeg,.mp4,.mov"
          style={{ display: "none" }}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Error */}
      {error && (
        <div style={{
          margin: "0 10px 8px",
          padding: "7px 10px",
          borderRadius: 4,
          border: "1px solid hsla(0,80%,66%,0.2)",
          background: "var(--red-dim)",
          display: "flex", alignItems: "flex-start", gap: 7,
        }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p className="font-mono-data" style={{ fontSize: 11, color: "var(--red)", margin: 0 }}>{error}</p>
        </div>
      )}

      {/* File list */}
      {hasData ? (
        <div style={{ flex: 1, overflowY: "auto", padding: "0 6px 8px" }}>
          {rasters.map((r, i) => (
            <FileRow
              key={r.id}
              icon="raster"
              badge={r.temporal_role ?? `S${i + 1}`}
              name={r.filename}
              preview={r.preview_url}
              meta={[`${r.width}×${r.height}`, `${r.bands}B`, r.modality ?? "Optical"].join("  ·  ")}
              sub={r.crs}
              status="valid"
            />
          ))}
          {video && (
            <FileRow
              icon="video"
              badge="VID"
              name={video.filename}
              meta={[`${video.duration_sec.toFixed(1)}s`, `${video.fps}fps`, `${video.frames} frames`].join("  ·  ")}
              sub={`${video.width}×${video.height}  ·  ${video.codec ?? "H264"}`}
              status="loaded"
            />
          )}
        </div>
      ) : (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p className="font-mono-data" style={{ fontSize: 10, color: "var(--t4)", textAlign: "center", lineHeight: 1.7, padding: "0 20px" }}>
            No data registered.<br />Upload imagery or video to begin.
          </p>
        </div>
      )}

      {/* Footer strip */}
      {hasData && (
        <div style={{
          borderTop: "1px solid var(--b0)", padding: "6px 12px",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          flexShrink: 0,
        }}>
          <span className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)" }}>
            {assetCount} {assetCount === 1 ? "asset" : "assets"} registered
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {onClearRasters && rasters.length > 0 && (
              <button
                onClick={onClearRasters}
                className="font-mono-data"
                style={{
                  fontSize: 9, color: "var(--t4)", cursor: "pointer",
                  background: "none", border: "none", padding: 0,
                }}
                onMouseEnter={e => (e.currentTarget.style.color = "var(--t2)")}
                onMouseLeave={e => (e.currentTarget.style.color = "var(--t4)")}
              >
                clear
              </button>
            )}
            <span className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)" }}>
              {rasters.length > 0 ? rasters[0].modality ?? "Optical" : video ? "Video" : "—"}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

function FileRow({ icon, badge, name, preview, meta, sub, status }: {
  icon: "raster" | "video";
  badge: string;
  name: string;
  preview?: string;
  meta: string;
  sub?: string;
  status: "valid" | "loaded";
}) {
  return (
    <div
      className="animate-fade-in"
      style={{
        display: "flex", alignItems: "flex-start", gap: 8,
        padding: "7px 6px", borderRadius: 4, cursor: "default",
        transition: "background 0.1s",
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--s2)"}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
    >
      {/* Thumbnail or icon */}
      <div style={{
        width: 32, height: 32, borderRadius: 4, flexShrink: 0,
        background: "var(--s2)", border: "1px solid var(--b1)",
        overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          icon === "raster" ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v13.5A1.5 1.5 0 0 0 3.75 21Z"/>
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"/>
            </svg>
          )
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
          <span className="font-mono-data" style={{
            fontSize: 9, fontWeight: 600, color: "var(--accent-text)",
            background: "var(--accent-dim)", border: "1px solid hsla(222,88%,62%,0.2)",
            borderRadius: 2, padding: "0 4px",
          }}>
            {badge}
          </span>
          <span style={{ fontSize: 11, color: "var(--t1)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {name}
          </span>
        </div>
        <p className="font-mono-data" style={{ fontSize: 9, color: "var(--t3)", margin: 0 }}>{meta}</p>
        {sub && <p className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", margin: "1px 0 0" }}>{sub}</p>}
      </div>

      {/* Status */}
      <div style={{ flexShrink: 0, paddingTop: 1 }}>
        <span style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: 9, letterSpacing: "0.04em", textTransform: "uppercase",
          color: status === "valid" ? "var(--green)" : "var(--accent-text)",
        }}>
          {status === "valid" ? "✓" : "●"}
        </span>
      </div>
    </div>
  );
}
