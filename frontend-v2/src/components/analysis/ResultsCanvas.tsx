"use client";

import React, { useState } from "react";
import { SideBySideSlide } from "@/components/ui/side-by-side-slide";
import { useAnalysisStore } from "@/stores/useAnalysisStore";

export function ResultsCanvas({
  layerSelect,
  setLayerSelect,
  modeSelect,
  setModeSelect,
  opacity,
  setOpacity,
  layerTab,
  setLayerTab,
  layersToggle,
  setLayersToggle,
}: {
  layerSelect: string;
  setLayerSelect: (v: string) => void;
  modeSelect: "compare" | "change_map" | "overlay";
  setModeSelect: (v: "compare" | "change_map" | "overlay") => void;
  opacity: number;
  setOpacity: (v: number) => void;
  layerTab: "images" | "layers";
  setLayerTab: (v: "images" | "layers") => void;
  layersToggle: {
    changeDetection: boolean;
    urbanArea: boolean;
    vegetation: boolean;
    waterBodies: boolean;
  };
  setLayersToggle: React.Dispatch<React.SetStateAction<{
    changeDetection: boolean;
    urbanArea: boolean;
    vegetation: boolean;
    waterBodies: boolean;
  }>>;
}) {
  const rasters = useAnalysisStore((s) => s.rasters);
  const activeJobId = useAnalysisStore((s) => s.activeJobId);
  const liveResult = useAnalysisStore((s) => s.liveResult);
  const [layerPanelOpen, setLayerPanelOpen] = useState(true);

  const isLiveComplete = liveResult?.status === "COMPLETED";
  const t1Raster = rasters[0];
  const t2Raster = rasters[1] || rasters[0];

  const beforeImage = isLiveComplete && activeJobId
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/jobs/${activeJobId}/layers/${layerSelect || "true_color"}/visualization`
    : (t1Raster?.preview_url || "");
  const afterImage = isLiveComplete && activeJobId
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/jobs/${activeJobId}/layers/change_probability_heatmap/visualization`
    : (t2Raster?.preview_url || "");

  return (
    <div className="flex-1 flex flex-col bg-[var(--scrim)] overflow-hidden min-w-0">
      {/* Controls Bar */}
      <div className="h-11 px-4 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-[var(--text-3)]">Layer</span>
            <div className="relative">
              <select
                value={layerSelect}
                onChange={(e) => setLayerSelect(e.target.value)}
                className="bg-[var(--surface-3)] text-[var(--text)] text-xs py-1 pl-2.5 pr-7 rounded border border-[var(--border)] focus:outline-none focus:border-[var(--cyan)] appearance-none cursor-pointer"
              >
                <option>Natural Color (RGB)</option>
                <option>False Color (Infrared)</option>
                <option>NDVI Difference</option>
              </select>
              <svg className="w-3 h-3 text-[var(--text-3)] absolute right-2 top-2 pointer-events-none" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </div>
          </div>

          <div className="flex items-center bg-[var(--surface-2)] p-0.5 rounded-lg border border-[var(--border)]">
            {(["compare", "change_map", "overlay"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setModeSelect(mode)}
                className={`px-2.5 py-1 rounded text-[10px] transition ${
                  modeSelect === mode
                    ? "bg-[var(--cyan-glow)] border border-cyan-600/40 text-[var(--cyan)] font-medium"
                    : "text-[var(--text-3)] hover:text-[var(--text)]"
                }`}
              >
                {mode === "compare" ? "Compare" : mode === "change_map" ? "Change Map" : "Overlay"}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 pl-2">
            <span className="text-[var(--text-3)]">Opacity</span>
            <input
              type="range"
              min="10"
              max="100"
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="w-20 h-1 bg-[var(--border)] accent-[var(--cyan)] rounded cursor-pointer"
            />
            <span className="text-[10px] text-[var(--text-2)] font-mono">{opacity}%</span>
          </div>
        </div>

        {/* Layer panel toggle */}
        <button
          onClick={() => setLayerPanelOpen(!layerPanelOpen)}
          className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] transition ${
            layerPanelOpen ? "bg-[var(--cyan)]/10 text-[var(--cyan)] border border-[var(--cyan)]/30" : "text-[var(--text-3)] hover:text-[var(--text)] border border-[var(--border)]"
          }`}
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
          </svg>
          <span>Layers</span>
        </button>
      </div>

      {/* Canvas Area */}
      <div className="relative flex-1 overflow-hidden">
        {/* SideBySideSlide */}
        <SideBySideSlide
          beforeImage={beforeImage}
          afterImage={afterImage}
          beforeAlt={t1Raster?.temporal_role || "T1"}
          afterAlt={t2Raster?.temporal_role || "T2"}
          className="w-full h-full"
          initialPosition={50}
        />

        {/* Floating Layer Switcher - Collapsible */}
        {layerPanelOpen && (
          <div className="absolute left-3 top-3 z-30 w-48 bg-[var(--surface)]/95 backdrop-blur-md rounded-lg border border-[var(--border)] shadow-2xl p-2.5 text-xs select-none">
            <div className="flex border-b border-[var(--border)] mb-2 pb-1">
              <button
                onClick={() => setLayerTab("images")}
                className={`flex-1 text-center py-1 font-semibold text-[11px] transition ${layerTab === "images" ? "text-[var(--cyan)] border-b-2 border-[var(--cyan)]" : "text-[var(--text-3)] hover:text-[var(--text)]"}`}
              >
                Images
              </button>
              <button
                onClick={() => setLayerTab("layers")}
                className={`flex-1 text-center py-1 text-[11px] transition ${layerTab === "layers" ? "text-[var(--cyan)] border-b-2 border-[var(--cyan)]" : "text-[var(--text-3)] hover:text-[var(--text)]"}`}
              >
                Layers
              </button>
            </div>

            <div className="space-y-1.5">
              {rasters.map((r) => (
                <div key={r.id} className="flex items-center gap-2 p-1.5 rounded-md bg-[var(--surface-3)] border border-[var(--border)]">
                  <div className="w-7 h-7 rounded overflow-hidden bg-[var(--surface-2)] border border-[var(--border)] shrink-0">
                    {r.preview_url ? (
                      <img src={r.preview_url} alt={r.filename} className="w-full h-full object-cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
                    ) : (
                      <div className="w-full h-full bg-[var(--surface-3)]" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="text-[10px] font-semibold text-[var(--text)] leading-tight truncate">{r.temporal_role} - {r.filename.slice(0, 12)}</div>
                    <div className="text-[8px] text-[var(--text-3)]">{r.modality}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-2 pt-2 border-t border-[var(--border)]">
              <span className="text-[9px] uppercase font-semibold text-[var(--text-3)] tracking-wider">Layers</span>
              <div className="mt-1.5 space-y-1">
                {([
                  { key: "changeDetection" as const, label: "Change", color: "bg-purple-400" },
                  { key: "urbanArea" as const, label: "Urban", color: "bg-red-400" },
                  { key: "vegetation" as const, label: "NDVI", color: "bg-emerald-400" },
                  { key: "waterBodies" as const, label: "Water", color: "bg-sky-400" },
                ]).map((layer) => (
                  <div key={layer.key} className="flex items-center justify-between">
                    <span className="text-[10px] text-[var(--text-2)] flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${layer.color}`} />
                      {layer.label}
                    </span>
                    <div
                      onClick={() => setLayersToggle((p) => ({ ...p, [layer.key]: !p[layer.key] }))}
                      className={`w-6 h-3.5 rounded-full p-0.5 cursor-pointer flex items-center transition ${
                        layersToggle[layer.key] ? "bg-[var(--cyan)] justify-end" : "bg-[var(--surface-hover)] border border-[var(--border-strong)] justify-start"
                      }`}
                    >
                      <div className="w-2.5 h-2.5 rounded-full bg-white shadow-sm" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Image Labels - positioned relative to the divider */}
        <div className="absolute top-3 left-4 z-20 bg-[var(--surface)]/80 backdrop-blur border border-[var(--border)] px-2 py-0.5 rounded text-[10px] font-mono text-[var(--text)] shadow-md pointer-events-none">
          {t1Raster?.temporal_role || "T1"} — {t1Raster?.filename?.slice(0, 12) || "Before"}
        </div>
        <div className="absolute top-3 right-4 z-20 bg-[var(--surface)]/80 backdrop-blur border border-[var(--border)] px-2 py-0.5 rounded text-[10px] font-mono text-[var(--text)] shadow-md pointer-events-none">
          {t2Raster?.temporal_role || "T2"} — {t2Raster?.filename?.slice(0, 12) || "After"}
        </div>

        {/* Distance Scale */}
        <div className="absolute bottom-4 left-4 z-20 flex flex-col gap-0.5 bg-[var(--surface)]/85 backdrop-blur px-2 py-1 rounded border border-[var(--border)] pointer-events-none">
          <div className="flex justify-between text-[8px] font-mono text-[var(--text-2)] w-24">
            <span>0</span>
            <span>0.5</span>
            <span>1km</span>
          </div>
          <div className="h-0.5 w-24 bg-[var(--text-4)] flex">
            <div className="w-1/2 h-full bg-[var(--surface-3)] border-r border-[var(--border)]" />
            <div className="w-1/2 h-full bg-[var(--text-4)]" />
          </div>
        </div>

        {/* Zoom Controls */}
        <div className="absolute right-3 bottom-4 z-20 flex flex-col gap-1">
          <div className="flex flex-col bg-[var(--surface)]/90 backdrop-blur rounded-lg border border-[var(--border)] overflow-hidden shadow-xl">
            <button className="w-6 h-6 flex items-center justify-center text-[var(--text-2)] hover:text-[var(--heading)] hover:bg-[var(--surface-hover)] text-xs font-bold border-b border-[var(--border)] cursor-pointer">+</button>
            <button className="w-6 h-6 flex items-center justify-center text-[var(--text-2)] hover:text-[var(--heading)] hover:bg-[var(--surface-hover)] text-xs font-bold cursor-pointer">-</button>
          </div>
        </div>
      </div>

      {/* Filmstrip */}
      <div className="h-16 border-t border-[var(--border)] bg-[var(--surface)] px-3 flex items-center gap-2 shrink-0">
        {rasters.slice(0, 4).map((r, idx) => (
          <div key={r.id} className={`flex items-center gap-2 px-2 py-1 rounded-lg bg-[var(--surface-2)] border ${idx === 0 ? "border-[var(--green)]/50" : "border-red-500/50"} relative overflow-hidden shrink-0`}>
            <div className={`w-10 h-10 rounded ${idx === 0 ? "border border-emerald-600/40" : "border border-red-500/50"} overflow-hidden shrink-0`}>
              {r.preview_url ? (
                <img src={r.preview_url} alt={r.filename} className="w-full h-full object-cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
              ) : (
                <div className="w-full h-full bg-[var(--surface-3)]" />
              )}
            </div>
            <div className="min-w-0">
              <div className="text-[10px] font-semibold text-[var(--text)] truncate max-w-[80px]">{r.filename.slice(0, 14)}</div>
              <div className="text-[8px] text-[var(--text-3)]">{r.modality}</div>
            </div>
            {idx === 1 && <div className="absolute inset-0 bg-red-500/10" />}
          </div>
        ))}
      </div>
    </div>
  );
}
