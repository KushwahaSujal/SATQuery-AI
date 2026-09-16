"use client";

import { useState, useEffect, useMemo } from "react";
import type { UploadedRaster, UploadedVideo } from "@/lib/types";
import { useLayers } from "@/hooks/useSystem";
import { api } from "@/lib/api";
import { useConnection } from "@/lib/connection";
import { Badge } from "@/components/ui/badge";

interface MapViewerProps {
  rasters: UploadedRaster[];
  video: UploadedVideo | null;
  jobId?: string | null;
}

// Map frontend layer labels to backend layer IDs
const LAYER_MAP: Record<string, string[]> = {
  RGB: ["true_color", "false_color_nir", "grayscale"],
  NDVI: ["ndvi", "ndwi"],
  SAR: ["sar_vv", "sar_vh", "sar_dual_pol"],
};

const LAYER_LABELS: Record<string, string> = {
  true_color: "RGB",
  false_color_nir: "False Color",
  ndvi: "NDVI",
  ndwi: "NDWI",
  sar_vv: "SAR VV",
  sar_vh: "SAR VH",
  sar_dual_pol: "SAR Dual",
  grayscale: "Grayscale",
};

export default function MapViewer({ rasters, video, jobId }: MapViewerProps) {
  const active = rasters[rasters.length - 1];
  const [activeLayer, setActiveLayer] = useState("RGB");
  const [selectedBackendLayer, setSelectedBackendLayer] = useState<string | null>(null);
  // Re-renders once real localStorage connection settings replace the SSR defaults, and again
  // on any later change, so imageUrl/legend src below pick up the key instead of staying stale.
  const connection = useConnection();

  // Fetch available layers from backend when we have a jobId
  const layersQuery = useLayers(jobId || undefined);
  const backendLayers = layersQuery.data?.layers ?? [];

  // Build available layer groups from backend data
  const availableGroups = useMemo(() => {
    if (backendLayers.length === 0) return { RGB: true, NDVI: false, SAR: false };
    const layerIds = backendLayers.map(l => l.id);
    return {
      RGB: layerIds.some(id => LAYER_MAP.RGB.includes(id)),
      NDVI: layerIds.some(id => LAYER_MAP.NDVI.includes(id)),
      SAR: layerIds.some(id => LAYER_MAP.SAR.includes(id)),
    };
  }, [backendLayers]);

  // Get the best layer ID for a group
  const getBestLayerId = (group: string): string | null => {
    const candidates = LAYER_MAP[group] || [];
    const layerIds = backendLayers.map(l => l.id);
    for (const candidate of candidates) {
      if (layerIds.includes(candidate)) return candidate;
    }
    return null;
  };

  // Auto-select first available backend layer when layers load
  useEffect(() => {
    if (backendLayers.length > 0 && !selectedBackendLayer) {
      const best = getBestLayerId("RGB") || backendLayers[0]?.id;
      if (best) setSelectedBackendLayer(best);
    }
  }, [backendLayers, selectedBackendLayer]);

  // Handle layer group switch
  const handleLayerSwitch = (group: string) => {
    setActiveLayer(group);
    const layerId = getBestLayerId(group);
    if (layerId) setSelectedBackendLayer(layerId);
  };

  // Build image URL
  const imageUrl = useMemo(() => {
    // Referenced only to force a recompute once useConnection() reports the real stored
    // base/key (post-hydration) — api.visualizationUrl()/mediaUrl() read them directly,
    // not via this closure, so exhaustive-deps can't see the dependency on its own.
    void connection.base;
    void connection.key;
    if (jobId && selectedBackendLayer) {
      return api.visualizationUrl(jobId, selectedBackendLayer);
    }
    return active?.preview_url || null;
  }, [jobId, selectedBackendLayer, active?.preview_url, connection.base, connection.key]);

  // Check if selected layer has a legend
  const activeLayerInfo = backendLayers.find(l => l.id === selectedBackendLayer);
  const hasLegend = activeLayerInfo?.legend_available;

  return (
    <section className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="3 11 22 2 13 21 11 13 3 11"/>
          </svg>
          <span className="panel-label">Imagery Preview</span>
          {active?.crs && (
            <Badge variant="accent" className="text-[9px] px-1.5 py-0">
              {active.crs}
            </Badge>
          )}
          {selectedBackendLayer && (
            <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
              {LAYER_LABELS[selectedBackendLayer] || selectedBackendLayer}
            </Badge>
          )}
        </div>

        {/* Layer toggles — only show available layers */}
        <div className="flex items-center gap-0.5">
          {(["RGB", "NDVI", "SAR"] as const)
            .filter((group) => availableGroups[group])
            .map((group) => (
              <button
                key={group}
                onClick={() => handleLayerSwitch(group)}
                className={`font-mono-data text-[9px] font-semibold tracking-widest uppercase px-1.5 py-0.5 rounded border transition-all ${
                  activeLayer === group
                    ? "text-[var(--accent-text)] bg-[var(--accent-dim)] border-[hsla(222,88%,62%,0.2)]"
                    : "text-[var(--t3)] bg-transparent border-transparent hover:text-[var(--t1)] cursor-pointer"
                }`}
              >
                {group}
              </button>
            ))}
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative bg-[var(--s0)] flex items-center justify-center overflow-hidden">
        {imageUrl ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt={active?.filename || `${activeLayer} view`}
              className="max-h-full max-w-full object-contain block"
              key={`${jobId}-${selectedBackendLayer}`}
            />
            {/* Layer loading indicator */}
            {layersQuery.isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-[var(--s0)]/80">
                <div className="flex items-center gap-2">
                  <span className="animate-spin-smooth w-3 h-3 border-2 border-[var(--accent-dim)] border-t-[var(--accent)] rounded-full" />
                  <span className="font-mono-data text-[10px] text-[var(--t3)]">Loading layers...</span>
                </div>
              </div>
            )}
          </>
        ) : video ? (
          /* Video registered state */
          <div className="text-center flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-[10px] bg-[var(--s2)] border border-[var(--b2)] flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-text)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </div>
            <div>
              <div className="font-mono-data text-[10px] text-[var(--t2)]">
                {video.filename}
              </div>
              <div className="font-mono-data text-[9px] text-[var(--t4)] mt-0.5">
                {video.duration_sec.toFixed(1)}s · {video.fps}fps · {video.width}×{video.height}
              </div>
            </div>
            <Badge variant="accent" className="text-[9px]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse-dot mr-1.5" />
              Video stream registered
            </Badge>
          </div>
        ) : (
          /* Empty state — world grid */
          <div className="flex flex-col items-center gap-4 select-none">
            {/* World grid SVG */}
            <div className="relative" style={{ width: 220, height: 110 }}>
              <svg viewBox="0 0 320 160" className="w-full h-full" style={{ opacity: 0.35 }}>
                {/* Meridians */}
                {[0, 40, 80, 120, 160, 200, 240, 280, 320].map(x => (
                  <line key={x} x1={x} y1="0" x2={x} y2="160" stroke="var(--b3)" strokeWidth="0.75" />
                ))}
                {/* Parallels */}
                {[0, 40, 80, 120, 160].map(y => (
                  <line key={y} x1="0" y1={y} x2="320" y2={y} stroke="var(--b3)" strokeWidth="0.75" />
                ))}
                {/* Equator (bolder) */}
                <line x1="0" y1="80" x2="320" y2="80" stroke="var(--accent)" strokeWidth="1.2" opacity="0.7" />
                {/* Prime meridian (bolder) */}
                <line x1="160" y1="0" x2="160" y2="160" stroke="var(--accent)" strokeWidth="1.2" opacity="0.7" />
                {/* Center crosshair rings */}
                <circle cx="160" cy="80" r="4" fill="none" stroke="var(--accent)" strokeWidth="1.2" opacity="0.8" />
                <circle cx="160" cy="80" r="12" fill="none" stroke="var(--accent)" strokeWidth="0.6" opacity="0.4" />
                <circle cx="160" cy="80" r="24" fill="none" stroke="var(--accent)" strokeWidth="0.4" opacity="0.2" />
              </svg>

              {/* Pulsing dot on top */}
              <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse-ring"
                style={{ boxShadow: "0 0 8px var(--accent-glow)" }}
              />
            </div>

            <div className="text-center">
              <p className="font-mono-data text-[10px] text-[var(--t4)] tracking-[0.12em] uppercase m-0">
                Awaiting Imagery
              </p>
              <p className="font-mono-data text-[9px] text-[var(--t4)] mt-1 tracking-wide">
                Upload GeoTIFF or video to begin
              </p>
            </div>
          </div>
        )}

        {/* HUD overlay — coordinates + dimensions */}
        {active && (
          <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-2.5 py-1.5"
            style={{ background: "linear-gradient(transparent, rgba(6,6,8,0.85))" }}
          >
            <div className="flex items-center gap-3">
              <HudField label="FILE" value={active.filename} />
              {active.crs && <HudField label="CRS" value={active.crs} />}
            </div>
            <div className="flex items-center gap-3">
              {active.width && <HudField label="W×H" value={`${active.width}×${active.height}`} />}
              {active.bands && <HudField label="BANDS" value={String(active.bands)} />}
              {selectedBackendLayer && <HudField label="LAYER" value={LAYER_LABELS[selectedBackendLayer] || selectedBackendLayer} />}
            </div>
          </div>
        )}

        {/* Legend overlay */}
        {hasLegend && jobId && selectedBackendLayer && (
          <div className="absolute bottom-12 right-2 w-20 bg-[var(--s2)] border border-[var(--b1)] rounded p-1 opacity-80 hover:opacity-100 transition-opacity">
            <img
              src={api.legendUrl(jobId, selectedBackendLayer)}
              alt="Layer legend"
              className="w-full h-auto"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </div>
        )}

        {/* Zoom controls */}
        {imageUrl && (
          <div className="absolute right-2.5 flex flex-col gap-px" style={{ bottom: active ? 40 : 10 }}>
            {["+", "−", "⊡"].map((label) => (
              <button
                key={label}
                className="w-6 h-6 rounded bg-[var(--s2)] border border-[var(--b2)] text-[var(--t3)] text-xs cursor-pointer flex items-center justify-center transition-all hover:bg-[var(--s3)] hover:text-[var(--t1)]"
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function HudField({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="font-mono-data text-[8px] text-[var(--t4)] tracking-[0.08em]">{label}</span>
      <span className="font-mono-data text-[9px] text-[var(--t2)]">{value}</span>
    </span>
  );
}
