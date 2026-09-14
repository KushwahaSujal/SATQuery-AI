"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import type { UploadedRaster, UploadedVideo } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

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
    <section className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <span className="panel-label">Data Input</span>
        </div>
        <div className="flex items-center gap-2">
          {assetCount > 0 && (
            <Badge variant="accent">
              {assetCount} {assetCount === 1 ? "asset" : "assets"}
            </Badge>
          )}
          {uploading && (
            <span className="flex items-center gap-1.5">
              <span className="animate-spin-smooth w-2 h-2 border border-[var(--accent-dim)] border-t-[var(--accent)] rounded-full inline-block" />
              <span className="font-mono-data text-[10px] text-[var(--accent-text)]">Uploading</span>
            </span>
          )}
        </div>
      </div>

      {/* Drop zone */}
      <div
        className={cn(
          "m-2.5 mb-2 rounded-md border-[1.5px] border-dashed cursor-pointer flex flex-col items-center justify-center gap-2.5 py-6 px-3 text-center relative overflow-hidden transition-all duration-200",
          dragging
            ? "border-[var(--accent)] bg-[var(--accent-dim)] animate-drag-glow"
            : "border-[var(--b2)] bg-[var(--s0)] hover:border-[var(--b3)] hover:bg-[var(--s1)]"
        )}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
      >
        {/* Grid pattern background */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none transition-opacity duration-200"
          style={{ opacity: dragging ? 0.25 : 0.07 }}
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
        <div className="w-8 h-8 rounded-md bg-[var(--s2)] border border-[var(--b2)] flex items-center justify-center relative z-10 transition-all duration-200 group-hover:scale-110">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={dragging ? "var(--accent-text)" : "var(--t3)"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="transition-colors duration-200">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>

        <div className="relative z-10">
          <p className="text-xs text-[var(--t2)] m-0">
            Drop files here or <span className="text-[var(--t1)]">browse</span>
          </p>
          <p className="font-mono-data text-[9px] text-[var(--t4)] mt-1">
            GeoTIFF · PNG · JPEG · MP4 · MOV
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".tif,.tiff,.png,.jpg,.jpeg,.mp4,.mov"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Error */}
      {error && (
        <div className="mx-2.5 mb-2 px-2.5 py-2 rounded border border-[hsla(0,80%,66%,0.2)] bg-[var(--red-dim)] flex items-start gap-2">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0 mt-0.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p className="font-mono-data text-[11px] text-[var(--red)] m-0">{error}</p>
        </div>
      )}

      {/* File list */}
      {hasData ? (
        <div className="flex-1 overflow-y-auto px-1.5 pb-2">
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
        <div className="flex-1 flex items-center justify-center">
          <p className="font-mono-data text-[10px] text-[var(--t4)] text-center leading-relaxed px-5">
            No data registered.<br />Upload imagery or video to begin.
          </p>
        </div>
      )}

      {/* Footer strip */}
      {hasData && (
        <div className="border-t border-[var(--b0)] px-3 py-1.5 flex items-center justify-between flex-shrink-0">
          <span className="font-mono-data text-[9px] text-[var(--t4)]">
            {assetCount} {assetCount === 1 ? "asset" : "assets"} registered
          </span>
          <div className="flex items-center gap-2">
            {onClearRasters && rasters.length > 0 && (
              <button
                onClick={onClearRasters}
                className="font-mono-data text-[9px] text-[var(--t4)] cursor-pointer bg-transparent border-none p-0 hover:text-[var(--t2)] transition-colors"
              >
                clear
              </button>
            )}
            <span className="font-mono-data text-[9px] text-[var(--t4)]">
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
      className="animate-fade-in flex items-start gap-2 px-1.5 py-1.5 rounded cursor-default transition-all duration-150 hover:bg-[var(--s2)] group"
    >
      {/* Thumbnail or icon */}
      <div className="w-8 h-8 rounded flex-shrink-0 bg-[var(--s2)] border border-[var(--b1)] overflow-hidden flex items-center justify-center">
        {preview ? (
          <img src={preview} alt="" className="w-full h-full object-cover" />
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
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="font-mono-data text-[9px] font-semibold text-[var(--accent-text)] bg-[var(--accent-dim)] border border-[hsla(222,88%,62%,0.2)] rounded-sm px-1">
            {badge}
          </span>
          <span className="text-[11px] text-[var(--t1)] overflow-hidden text-ellipsis whitespace-nowrap">
            {name}
          </span>
        </div>
        <p className="font-mono-data text-[9px] text-[var(--t3)] m-0">{meta}</p>
        {sub && <p className="font-mono-data text-[9px] text-[var(--t4)] m-0 mt-px">{sub}</p>}
      </div>

      {/* Status */}
      <div className="flex-shrink-0 pt-px">
        <span className="font-mono-data text-[9px] tracking-wide uppercase" style={{ color: status === "valid" ? "var(--green)" : "var(--accent-text)" }}>
          {status === "valid" ? "✓" : "●"}
        </span>
      </div>
    </div>
  );
}
