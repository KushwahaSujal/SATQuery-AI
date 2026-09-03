"use client";

import React, { useState, useEffect, useRef } from "react";
import { Eye, SplitSquareVertical, Layers, ZoomIn, Target, Box, Crosshair } from "lucide-react";
import { UploadedRasterMeta } from "./UploadPanel";

interface MapViewerProps {
  metadata: UploadedRasterMeta[];
  overlayUrl?: string | null;
  activeLayerUrl?: string | null;
  layerOpacity?: number;
  inspectActive?: boolean;
  onPixelClick?: (col: number, row: number) => void;
  boxes?: Array<{
    label: string;
    box_2d: number[]; // [ymin, xmin, ymax, xmax]
    score?: number | null;
    geo_bounds?: number[] | null;
    source_crs?: string | null;
    target_crs?: string | null;
    coordinate_space?: string;
  }>;
}

export const MapViewer: React.FC<MapViewerProps> = ({
  metadata,
  overlayUrl,
  activeLayerUrl,
  layerOpacity = 0.75,
  inspectActive = false,
  onPixelClick,
  boxes = [],
}) => {
  const [viewMode, setViewMode] = useState<"single" | "side_by_side" | "overlay">("single");
  const [selectedImageIdx, setSelectedImageIdx] = useState<number>(0);
  const imgRef = useRef<HTMLImageElement>(null);

  // Auto-switch to overlay or single when overlay becomes available
  useEffect(() => {
    if (overlayUrl) {
      setViewMode("overlay");
    }
  }, [overlayUrl]);

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!inspectActive || !onPixelClick) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    const naturalW = e.currentTarget.naturalWidth || metadata[selectedImageIdx]?.width || 256;
    const naturalH = e.currentTarget.naturalHeight || metadata[selectedImageIdx]?.height || 256;
    const col = Math.max(0, Math.min(naturalW - 1, Math.floor((clickX / rect.width) * naturalW)));
    const row = Math.max(0, Math.min(naturalH - 1, Math.floor((clickY / rect.height) * naturalH)));
    onPixelClick(col, row);
  };

  if (!metadata || metadata.length === 0) {
    return (
      <div className="bg-surface rounded-xl border border-surfaceBorder p-8 text-center text-slate-500 h-[450px] flex flex-col items-center justify-center">
        <Layers className="w-10 h-10 mb-2 text-slate-600" />
        <p className="text-sm font-semibold">No Imagery Loaded</p>
        <p className="text-xs">Upload satellite imagery to activate spatial viewer & vector layers</p>
      </div>
    );
  }

  const currentPreview = metadata[selectedImageIdx]?.preview_url;

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Spatial Evidence Viewer
          </h2>
          {inspectActive && (
            <span className="px-2 py-0.5 text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/40 rounded flex items-center space-x-1 animate-pulse">
              <Crosshair className="w-3 h-3" />
              <span>Inspector Sampling</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {/* Mode Selector */}
          <div className="flex bg-slate-900 rounded-lg p-1 border border-slate-800 text-xs font-medium">
            <button
              onClick={() => setViewMode("single")}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === "single" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              {metadata.length === 1 ? "Base Image" : "Single"}
            </button>

            {metadata.length >= 2 && (
              <button
                onClick={() => setViewMode("side_by_side")}
                className={`px-2.5 py-1 rounded transition-colors ${
                  viewMode === "side_by_side" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Side-by-Side
              </button>
            )}

            {overlayUrl && (
              <button
                onClick={() => setViewMode("overlay")}
                className={`px-2.5 py-1 rounded transition-colors flex items-center space-x-1 ${
                  viewMode === "overlay" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                <Target className="w-3 h-3" />
                <span>Overlay</span>
              </button>
            )}
          </div>

          {/* Multi-image selector in single mode */}
          {viewMode === "single" && metadata.length > 1 && (
            <div className="flex space-x-1">
              {metadata.map((m, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedImageIdx(idx)}
                  className={`text-xs px-2.5 py-1 rounded font-semibold border ${
                    selectedImageIdx === idx
                      ? "bg-blue-600/20 text-blue-400 border-blue-500/40"
                      : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
                  }`}
                >
                  Image {idx + 1}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="relative w-full h-[450px] bg-slate-950 rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
        {viewMode === "side_by_side" && metadata.length >= 2 ? (
          <div className="grid grid-cols-2 w-full h-full gap-1 p-2">
            <div className="relative w-full h-full flex flex-col items-center justify-center bg-slate-900/50 rounded overflow-hidden">
              <span className="absolute top-2 left-2 z-10 px-2 py-0.5 text-[10px] font-bold font-mono rounded bg-black/70 text-white border border-slate-700">
                T1: {metadata[0].filename}
              </span>
              {metadata[0].preview_url && (
                <img
                  src={metadata[0].preview_url}
                  alt="T1"
                  className="w-full h-full object-contain"
                />
              )}
            </div>
            <div className="relative w-full h-full flex flex-col items-center justify-center bg-slate-900/50 rounded overflow-hidden">
              <span className="absolute top-2 left-2 z-10 px-2 py-0.5 text-[10px] font-bold font-mono rounded bg-black/70 text-white border border-slate-700">
                T2: {metadata[1].filename}
              </span>
              {metadata[1].preview_url && (
                <img
                  src={metadata[1].preview_url}
                  alt="T2"
                  className="w-full h-full object-contain"
                />
              )}
            </div>
          </div>
        ) : viewMode === "overlay" && overlayUrl ? (
          <div className="relative w-full h-full flex items-center justify-center">
            <img
              src={overlayUrl}
              alt="Visual Overlay"
              className={`w-full h-full object-contain ${inspectActive ? "cursor-crosshair" : ""}`}
              onClick={handleImageClick}
            />
            <div className="absolute top-3 left-3 flex items-center space-x-2 z-10">
              <span className="px-2 py-1 text-xs font-bold font-mono rounded bg-emerald-950/90 text-emerald-300 border border-emerald-600/40 shadow-lg">
                Segmentation Overlay (SAM 2)
              </span>
            </div>

            {/* Bounding box on top of overlay if present */}
            {boxes.map((box, idx) => {
              const [ymin, xmin, ymax, xmax] = box.box_2d;
              const top = `${ymin * 100}%`;
              const left = `${xmin * 100}%`;
              const width = `${(xmax - xmin) * 100}%`;
              const height = `${(ymax - ymin) * 100}%`;

              return (
                <div
                  key={idx}
                  style={{ top, left, width, height }}
                  className="absolute border-2 border-cyan-400 bg-cyan-500/10 pointer-events-none transition-all rounded-sm"
                >
                  <span className="absolute -top-5 left-0 text-[10px] font-mono font-bold bg-cyan-950/95 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-500/40 whitespace-nowrap shadow-md">
                    {box.label} {box.score ? `(${(box.score * 100).toFixed(1)}%)` : ""}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="relative w-full h-full flex items-center justify-center">
            {/* Base Image */}
            {currentPreview && (
              <img
                ref={imgRef}
                src={currentPreview}
                alt="Raster Preview"
                className={`w-full h-full object-contain ${inspectActive ? "cursor-crosshair" : ""}`}
                onClick={handleImageClick}
              />
            )}

            {/* Active Visualization Layer Overlay (with adjustable opacity) */}
            {activeLayerUrl && (
              <img
                src={activeLayerUrl}
                alt="Active Analytics Layer"
                style={{ opacity: layerOpacity }}
                className="absolute inset-0 w-full h-full object-contain pointer-events-none transition-opacity"
              />
            )}

            {/* Bounding box overlays for grounding */}
            {boxes.map((box, idx) => {
              const [ymin, xmin, ymax, xmax] = box.box_2d;
              const top = `${ymin * 100}%`;
              const left = `${xmin * 100}%`;
              const width = `${(xmax - xmin) * 100}%`;
              const height = `${(ymax - ymin) * 100}%`;

              return (
                <div
                  key={idx}
                  style={{ top, left, width, height }}
                  className="absolute border-2 border-cyan-400 bg-cyan-500/20 pointer-events-none transition-all rounded-sm shadow-[0_0_12px_rgba(6,182,212,0.4)]"
                >
                  <span className="absolute -top-5 left-0 text-[10px] font-mono font-bold bg-cyan-950/95 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-500/40 whitespace-nowrap shadow-md">
                    {box.label} {box.score ? `(${(box.score * 100).toFixed(1)}%)` : ""}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
