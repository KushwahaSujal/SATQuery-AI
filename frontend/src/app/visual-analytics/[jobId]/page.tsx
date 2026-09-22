"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useLayers, useHistogram, usePixelInspector } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import { useConnection } from "@/lib/connection";
import type { ExportFormat, Layer } from "@/lib/types";
import { cn } from "@/lib/utils";

const provenanceColor: Record<string, string> = {
  SOURCE_DATA: "text-[#60a5fa]",
  DERIVED_INDEX: "text-[#4ade80]",
  MODEL_OUTPUT: "text-[#a78bfa]",
  MODEL_PROBABILITY: "text-[#f472b6]",
};

export default function VisualAnalyticsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  // Re-renders once real localStorage connection settings replace the SSR defaults, so
  // visualizationUrl/exportUrl below pick up the key instead of staying stale after hydration.
  useConnection();
  const layersQuery = useLayers(jobId);
  const [activeId, setActiveId] = useState("true_color");
  const [opacity, setOpacity] = useState(85);
  const [showHistogram, setShowHistogram] = useState(false);
  const [imgError, setImgError] = useState(false);

  const canvasRef = useRef<HTMLDivElement>(null);
  const pixelInspector = usePixelInspector(jobId);
  const histogramQuery = useHistogram(jobId, activeId, showHistogram);

  const layers = layersQuery.data?.layers ?? [];
  const activeLayer = useMemo(
    () => layers.find((l) => l.id === activeId) ?? layers[0],
    [layers, activeId]
  );

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!canvasRef.current) return;
    const r = canvasRef.current.getBoundingClientRect();
    const col = Math.floor(((e.clientX - r.left) / r.width) * 1024);
    const row = Math.floor(((e.clientY - r.top) / r.height) * 1024);
    pixelInspector.mutate({ col, row });
  }

  const pixel = pixelInspector.data;

  const visualizationUrl = activeLayer?.artifact_url || api.visualizationUrl(jobId, activeId);
  
  // Show loading or empty state
  if (layersQuery.isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)] border border-[#1a1a1a] rounded-lg">
        <span className="font-mono-data text-[12px] text-[#737373]">Loading visual analytics...</span>
      </div>
    );
  }
  
  if (!activeLayer) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)] border border-[#1a1a1a] rounded-lg">
        <div className="text-center">
          <span className="font-mono-data text-[12px] text-[#737373] block mb-2">No visualization layers available</span>
          <span className="font-mono-data text-[10px] text-[#404040]">Upload imagery and run analysis to generate layers</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex border border-[#1a1a1a] rounded-lg overflow-hidden animate-fade-in" style={{ height: "calc(100vh - 80px)" }}>
      {/* Layer list */}
      <div className="w-[220px] shrink-0 flex flex-col border-r border-[#1a1a1a]">
        <div className="panel-header shrink-0">
          <span className="panel-label">Visual Layers</span>
        </div>
        <div className="flex-1 overflow-y-auto">
          {layers.map((l) => (
            <button
              key={l.id}
              onClick={() => {
                setActiveId(l.id);
                setImgError(false);
              }}
              className={cn(
                "w-full flex flex-col gap-0.5 px-3 py-2.5 text-left border-b border-[#1a1a1a] transition-colors last:border-0",
                l.id === activeId ? "bg-[#111] text-[#fafafa]" : "text-[#737373] hover:bg-[#0d0d0d] hover:text-[#a3a3a3]"
              )}
            >
              <span className="text-[12px] leading-none">{l.name}</span>
              <span className={cn("font-mono-data text-[9px] uppercase tracking-wider mt-0.5", provenanceColor[l.provenance] ?? "text-[#333]")}>
                {l.provenance}
              </span>
            </button>
          ))}
        </div>

        {/* Job breadcrumb */}
        <div className="p-3 border-t border-[#1a1a1a] shrink-0">
          <Link href={`/analysis/${jobId}`} className="font-mono-data text-[10px] text-[#2a2a2a] hover:text-[#404040] transition-colors">
            ← analysis workspace
          </Link>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="panel-header shrink-0">
          <div className="flex items-center gap-2">
            <span className="panel-label">{activeLayer.name}</span>
            <span className={cn("font-mono-data text-[9px] uppercase tracking-wider", provenanceColor[activeLayer.provenance] ?? "text-[#333]")}>
              {activeLayer.provenance}
            </span>
          </div>
          <span className="font-mono-data text-[10px] text-[#2a2a2a]">Click to inspect pixel</span>
        </div>

        <div
          ref={canvasRef}
          onClick={handleClick}
          className="flex-1 bg-[#080808] cursor-crosshair relative flex items-center justify-center overflow-hidden"
          style={{ opacity: opacity / 100 }}
        >
          {/* Live Layer Render */}
          {!imgError ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={visualizationUrl}
              alt={activeLayer.name}
              className="w-full h-full object-contain absolute inset-0"
              onError={() => setImgError(true)}
            />
          ) : (
            <svg className="w-full h-full absolute inset-0" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
              <rect width="800" height="600" fill="#060606" />
              {activeId === "ndvi" && (
                <>
                  <ellipse cx="300" cy="280" rx="180" ry="140" fill="#4ade80" opacity="0.15" />
                  <ellipse cx="500" cy="200" rx="120" ry="90" fill="#22c55e" opacity="0.2" />
                </>
              )}
              {activeId === "change_prob" && (
                <>
                  <radialGradient id="rg1" cx="50%" cy="50%">
                    <stop offset="0%" stopColor="#f87171" stopOpacity="0.5" />
                    <stop offset="100%" stopColor="#f87171" stopOpacity="0" />
                  </radialGradient>
                  <ellipse cx="400" cy="300" rx="200" ry="150" fill="url(#rg1)" />
                </>
              )}
              {activeId === "ndwi" && (
                <path d="M50 400 Q 200 200 400 380 T 800 300" fill="none" stroke="#60a5fa" strokeWidth="40" opacity="0.18" />
              )}
            </svg>
          )}

          {/* Grid overlay */}
          <svg className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="pg" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#fff" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#pg)" />
          </svg>
        </div>

        {/* Opacity slider */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-t border-[#1a1a1a] shrink-0 bg-[#0a0a0a]">
          <span className="panel-label w-12 shrink-0">Opacity</span>
          <input
            type="range"
            min={0}
            max={100}
            value={opacity}
            onChange={(e) => setOpacity(+e.target.value)}
            className="flex-1 accent-[#404040] cursor-pointer h-1"
          />
          <span className="font-mono-data text-[11px] text-[#333] w-8 text-right">{opacity}%</span>
        </div>
      </div>

      {/* Right panel — inspector + export */}
      <div className="w-[220px] shrink-0 flex flex-col border-l border-[#1a1a1a]">
        {/* Pixel inspector */}
        <div className="panel-header">
          <span className="panel-label">Pixel Telemetry</span>
        </div>
        <div className="p-3 border-b border-[#1a1a1a] flex-shrink-0">
          {pixel ? (
            <div className="font-mono-data text-[10px] space-y-1.5">
              <div className="flex justify-between text-[var(--t3)]">
                <span>col/row</span>
                <span className="text-[var(--t4)]">{pixel.col}, {pixel.row}</span>
              </div>
              {pixel.geographic_coordinates && (
                <div className="flex justify-between text-[var(--t3)]">
                  <span>x, y ({pixel.geographic_coordinates.crs || pixel.crs || ""})</span>
                  <span className="text-[var(--t4)]">
                    {pixel.geographic_coordinates.x_coord?.toFixed(5)}, {pixel.geographic_coordinates.y_coord?.toFixed(5)}
                  </span>
                </div>
              )}
              {pixel.derived_indices?.NDVI != null && (
                <div className="flex justify-between">
                  <span className="text-[var(--t3)]">NDVI</span>
                  <span className="text-[var(--green)]">{(pixel.derived_indices.NDVI as number).toFixed(4)}</span>
                </div>
              )}
              {pixel.probability != null && (
                <div className="flex justify-between">
                  <span className="text-[var(--t3)]">probability</span>
                  <span className="text-[var(--purple)]">{(pixel.probability * 100).toFixed(2)}%</span>
                </div>
              )}
              {pixel.model_prediction?.status && (
                <div className="flex justify-between">
                  <span className="text-[var(--t3)]">prediction</span>
                  <span className="text-[var(--t2)]">{pixel.model_prediction.status}</span>
                </div>
              )}
            </div>
          ) : (
            <p className="font-mono-data text-[10px] text-[var(--t4)]">Click the image to inspect a pixel</p>
          )}
        </div>

        {/* Histogram / Distribution */}
        <div className="p-3 border-b border-[#1a1a1a] shrink-0">
          <button
            onClick={() => setShowHistogram((h) => !h)}
            className="w-full text-left font-mono-data text-[11px] text-[#404040] hover:text-[#737373] transition-colors"
          >
            {showHistogram ? "▾" : "▸"} Spectral Distribution
          </button>
          {showHistogram && (
            <div className="mt-2 font-mono-data text-[10px] space-y-1 text-[#333]">
              {[
                ["min", (histogramQuery.data?.min ?? 0.0).toFixed(3)],
                ["max", (histogramQuery.data?.max ?? 0.998).toFixed(3)],
                ["mean", (histogramQuery.data?.mean ?? 0.314).toFixed(3)],
                ["σ", (histogramQuery.data?.std ?? 0.341).toFixed(3)],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span>{k}</span>
                  <span className="text-[#404040]">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Export */}
        <div className="p-3 flex-1">
          <span className="panel-label block mb-2">Export Data</span>
          <div className="space-y-1">
            {(["png", "geotiff", "geojson"] as ExportFormat[]).map((fmt) => (
              <a
                key={fmt}
                href={activeId ? api.exportUrl(jobId, activeId, fmt) : "#"}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between w-full py-1.5 px-2 rounded border border-[#1a1a1a] hover:border-[#222] hover:bg-[#0d0d0d] transition-colors font-mono-data text-[11px] text-[#404040] hover:text-[#737373]"
              >
                <span className="uppercase tracking-wider">{fmt}</span>
                <span className="text-[#1e1e1e]">↓</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
