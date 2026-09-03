"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Layers,
  Sliders,
  BarChart2,
  Download,
  Crosshair,
  Info,
  SplitSquareVertical,
  Compass,
  CheckCircle2,
  AlertTriangle,
  ZoomIn,
  Cpu,
  Eye,
  Radar
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface VisualizationLayer {
  layer_id: string;
  layer_type: string;
  title: string;
  provenance: "SOURCE_DATA" | "DERIVED_INDEX" | "MODEL_OUTPUT" | "MODEL_PROBABILITY" | "HEURISTIC_ANALYSIS";
  source_model?: string | null;
  units: string;
  min_value: number;
  max_value: number;
  mean_value?: number | null;
  display_stretch: string;
  valid_pixel_pct: number;
  crs?: string | null;
  bounds?: number[] | null;
  resolution?: number[] | null;
  colormap?: string | null;
  legend_labels?: Record<string, string> | null;
  co_registered: boolean;
  artifact_url?: string | null;
  legend_url?: string | null;
  raw_stats?: Record<string, any> | null;
}

export interface PixelInspectionData {
  pixel: { col: number; row: number };
  geographic_coordinates?: { x_coord: number; y_coord: number; crs: string } | null;
  band_values: Record<string, number>;
  derived_indices: Record<string, number>;
  model_prediction?: {
    probability?: number;
    prediction_class?: number;
    status?: string;
  } | null;
}

export interface HistogramData {
  total_pixels: number;
  units: string;
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number;
  percentiles: {
    p2: number;
    p25: number;
    p50: number;
    p75: number;
    p98: number;
  };
  bins: Array<{
    range_start: number;
    range_end: number;
    count: number;
  }>;
}

interface VisualizationPanelProps {
  jobId: string;
  baseImageUrl?: string | null;
  onLayerChange?: (layer: VisualizationLayer | null, opacity: number) => void;
  onInspectRequested?: (active: boolean) => void;
  inspectedPixelData?: PixelInspectionData | null;
}

export const VisualizationPanel: React.FC<VisualizationPanelProps> = ({
  jobId,
  baseImageUrl,
  onLayerChange,
  onInspectRequested,
  inspectedPixelData
}) => {
  const [layers, setLayers] = useState<VisualizationLayer[]>([]);
  const [activeLayerId, setActiveLayerId] = useState<string>("true_color");
  const [opacity, setOpacity] = useState<number>(75);
  const [loading, setLoading] = useState<boolean>(false);
  const [inspectMode, setInspectMode] = useState<boolean>(false);
  const [showHistogram, setShowHistogram] = useState<boolean>(false);
  const [histogramData, setHistogramData] = useState<HistogramData | null>(null);
  const [histogramLoading, setHistogramLoading] = useState<boolean>(false);
  const [exportFormat, setExportFormat] = useState<"png" | "geotiff" | "geojson">("png");

  // Fetch available layers for the job
  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    fetch(`${API_BASE}/api/analysis/${jobId}/layers`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load layers");
        return res.json();
      })
      .then((data: VisualizationLayer[]) => {
        setLayers(data);
        if (data.length > 0) {
          const defaultL = data.find(
            (l) =>
              l.layer_id === "change_overlay" ||
              l.layer_id === "change_probability_heatmap" ||
              l.layer_id === "grounding_bboxes" ||
              l.layer_id === "true_color"
          ) || data[0];
          setActiveLayerId(defaultL.layer_id);
          if (onLayerChange) onLayerChange(defaultL, opacity / 100.0);
        }
      })
      .catch((err) => {
        console.warn("Could not load visualization layers:", err);
      })
      .finally(() => setLoading(false));
  }, [jobId]);

  // Handle active layer selection
  const handleSelectLayer = (layerId: string) => {
    setActiveLayerId(layerId);
    const layer = layers.find((l) => l.layer_id === layerId) || null;
    if (onLayerChange) onLayerChange(layer, opacity / 100.0);
    setShowHistogram(false);
  };

  // Handle opacity change
  const handleOpacityChange = (val: number) => {
    setOpacity(val);
    const layer = layers.find((l) => l.layer_id === activeLayerId) || null;
    if (onLayerChange) onLayerChange(layer, val / 100.0);
  };

  // Toggle pixel inspection mode
  const handleToggleInspect = () => {
    const next = !inspectMode;
    setInspectMode(next);
    if (onInspectRequested) onInspectRequested(next);
  };

  // Fetch histogram on demand
  const handleFetchHistogram = () => {
    if (!activeLayerId || !jobId) return;
    setShowHistogram(true);
    setHistogramLoading(true);
    fetch(`${API_BASE}/api/analysis/${jobId}/histogram/${activeLayerId}`)
      .then((res) => res.json())
      .then((data: HistogramData) => setHistogramData(data))
      .catch((err) => console.error("Histogram fetch error:", err))
      .finally(() => setHistogramLoading(false));
  };

  // Export layer
  const handleExport = () => {
    if (!activeLayerId || !jobId) return;
    window.open(
      `${API_BASE}/api/analysis/${jobId}/export/${activeLayerId}?format=${exportFormat}`,
      "_blank"
    );
  };

  const activeLayer = layers.find((l) => l.layer_id === activeLayerId);

  // Categorize layers for clean UX grouping
  const categorizedLayers = useMemo(() => {
    const modelLayers: VisualizationLayer[] = [];
    const imageLayers: VisualizationLayer[] = [];
    const spectralLayers: VisualizationLayer[] = [];
    const sarLayers: VisualizationLayer[] = [];

    layers.forEach((l) => {
      const id = l.layer_id.toLowerCase();
      if (
        id.includes("change") ||
        id.includes("probability") ||
        id.includes("mask") ||
        id.includes("overlay") ||
        id.includes("grounding") ||
        id.includes("sam2") ||
        id.includes("region")
      ) {
        modelLayers.push(l);
      } else if (
        id.includes("sar") ||
        l.layer_type === "SAR_POLARIZATION"
      ) {
        sarLayers.push(l);
      } else if (
        id.includes("ndvi") ||
        id.includes("ndwi") ||
        id.includes("false_color") ||
        id.startsWith("band_")
      ) {
        spectralLayers.push(l);
      } else {
        imageLayers.push(l);
      }
    });

    return { modelLayers, imageLayers, spectralLayers, sarLayers };
  }, [layers]);

  const getProvenanceBadge = (prov: string) => {
    switch (prov) {
      case "SOURCE_DATA":
        return <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-blue-950/80 text-blue-300 border border-blue-600/40 rounded">ORIGINAL DATA</span>;
      case "DERIVED_INDEX":
        return <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-600/40 rounded">DERIVED INDEX</span>;
      case "MODEL_PROBABILITY":
        return <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-purple-950/80 text-purple-300 border border-purple-600/40 rounded">MODEL PROBABILITY</span>;
      case "MODEL_OUTPUT":
        return <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-950/80 text-amber-300 border border-amber-600/40 rounded">MODEL PREDICTION</span>;
      case "HEURISTIC_ANALYSIS":
        return <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700 rounded">HEURISTIC SCORE</span>;
      default:
        return null;
    }
  };

  if (!jobId || layers.length === 0) {
    return null;
  }

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm space-y-4">
      {/* Top Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Multi-Modal Visual Analytics & Evidence Overlays
          </h3>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleToggleInspect}
            className={`px-3 py-1 text-xs font-semibold rounded flex items-center space-x-1.5 transition-colors border ${
              inspectMode
                ? "bg-cyan-600 text-white border-cyan-400 shadow-md shadow-cyan-500/20"
                : "bg-slate-900 text-slate-300 border-slate-800 hover:text-white"
            }`}
          >
            <Crosshair className="w-3.5 h-3.5" />
            <span>{inspectMode ? "Inspector Active" : "Inspect Pixel"}</span>
          </button>

          <button
            onClick={handleFetchHistogram}
            className="px-3 py-1 text-xs font-semibold rounded bg-slate-900 text-slate-300 border border-slate-800 hover:text-white flex items-center space-x-1.5 transition-colors"
          >
            <BarChart2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Histogram</span>
          </button>

          {/* Export Selector & Button */}
          <div className="flex items-center space-x-1 bg-slate-900 p-0.5 rounded border border-slate-800">
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as any)}
              className="bg-transparent text-xs text-slate-300 px-1 py-0.5 rounded outline-none cursor-pointer"
            >
              <option value="png" className="bg-slate-900">PNG (+ Legend)</option>
              <option value="geotiff" className="bg-slate-900">GeoTIFF</option>
              <option value="geojson" className="bg-slate-900">GeoJSON</option>
            </select>
            <button
              onClick={handleExport}
              title="Download layer artifact"
              className="p-1 text-slate-400 hover:text-cyan-400 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Grouped Layer Selector */}
      <div className="space-y-3">
        {/* Model Evidence & Overlays */}
        {categorizedLayers.modelLayers.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[11px] font-bold uppercase tracking-wider text-purple-400">
              <Cpu className="w-3.5 h-3.5" />
              <span>Model Evidence & Change Detection Layers ({categorizedLayers.modelLayers.length})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categorizedLayers.modelLayers.map((layer) => {
                const isSelected = layer.layer_id === activeLayerId;
                return (
                  <button
                    key={layer.layer_id}
                    onClick={() => handleSelectLayer(layer.layer_id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all border ${
                      isSelected
                        ? "bg-purple-950 text-purple-200 border-purple-500 shadow-md shadow-purple-950/50"
                        : "bg-slate-900/80 text-slate-300 border-slate-800 hover:text-white hover:border-purple-700/50"
                    }`}
                  >
                    <span>{layer.title}</span>
                    {isSelected && <CheckCircle2 className="w-3 h-3 text-purple-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Input Imagery & Epochs */}
        {categorizedLayers.imageLayers.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[11px] font-bold uppercase tracking-wider text-blue-400">
              <Eye className="w-3.5 h-3.5" />
              <span>Input Rasters & Temporal Epochs ({categorizedLayers.imageLayers.length})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categorizedLayers.imageLayers.map((layer) => {
                const isSelected = layer.layer_id === activeLayerId;
                return (
                  <button
                    key={layer.layer_id}
                    onClick={() => handleSelectLayer(layer.layer_id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all border ${
                      isSelected
                        ? "bg-blue-950 text-blue-200 border-blue-500 shadow-md shadow-blue-950/50"
                        : "bg-slate-900/80 text-slate-300 border-slate-800 hover:text-white hover:border-blue-700/50"
                    }`}
                  >
                    <span>{layer.title}</span>
                    {isSelected && <CheckCircle2 className="w-3 h-3 text-blue-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Multispectral & Indices */}
        {categorizedLayers.spectralLayers.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-400">
              <Compass className="w-3.5 h-3.5" />
              <span>Spectral Indices & Bands ({categorizedLayers.spectralLayers.length})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categorizedLayers.spectralLayers.map((layer) => {
                const isSelected = layer.layer_id === activeLayerId;
                return (
                  <button
                    key={layer.layer_id}
                    onClick={() => handleSelectLayer(layer.layer_id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all border ${
                      isSelected
                        ? "bg-emerald-950 text-emerald-200 border-emerald-500 shadow-md shadow-emerald-950/50"
                        : "bg-slate-900/80 text-slate-300 border-slate-800 hover:text-white hover:border-emerald-700/50"
                    }`}
                  >
                    <span>{layer.title}</span>
                    {isSelected && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* SAR Radar */}
        {categorizedLayers.sarLayers.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-400">
              <Radar className="w-3.5 h-3.5" />
              <span>SAR Radar Polarimetry ({categorizedLayers.sarLayers.length})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categorizedLayers.sarLayers.map((layer) => {
                const isSelected = layer.layer_id === activeLayerId;
                return (
                  <button
                    key={layer.layer_id}
                    onClick={() => handleSelectLayer(layer.layer_id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all border ${
                      isSelected
                        ? "bg-amber-950 text-amber-200 border-amber-500 shadow-md shadow-amber-950/50"
                        : "bg-slate-900/80 text-slate-300 border-slate-800 hover:text-white hover:border-amber-700/50"
                    }`}
                  >
                    <span>{layer.title}</span>
                    {isSelected && <CheckCircle2 className="w-3 h-3 text-amber-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Active Layer Details Bar */}
      {activeLayer && (
        <div className="bg-slate-950/70 rounded-lg p-3 border border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-3">
            {getProvenanceBadge(activeLayer.provenance)}
            <div className="text-slate-300">
              <span className="font-semibold text-white">{activeLayer.title}</span>
              <span className="text-slate-400 ml-2">
                [{activeLayer.min_value != null ? activeLayer.min_value.toFixed(2) : "0.00"}, {activeLayer.max_value != null ? activeLayer.max_value.toFixed(2) : "1.00"}] {activeLayer.units || ""}
              </span>
            </div>
          </div>

          {/* Opacity Control */}
          <div className="flex items-center space-x-2">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400 text-[11px]">Opacity:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={opacity}
              onChange={(e) => handleOpacityChange(Number(e.target.value))}
              className="w-24 accent-cyan-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
            />
            <span className="font-mono text-cyan-400 w-8 text-right">{opacity}%</span>
          </div>
        </div>
      )}

      {/* Scientific Legend Display */}
      {activeLayer && activeLayer.legend_url && (
        <div className="bg-slate-950 rounded-lg p-3 border border-slate-800/80 flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <div className="flex items-center space-x-1.5 text-slate-300 text-xs font-semibold">
              <Info className="w-3 h-3 text-cyan-400" />
              <span>Scientific Colorbar Scale</span>
            </div>
            <p className="text-[10px] text-slate-500">
              Normalized color ramp reflecting {activeLayer.units}. Colors reflect numerical values, not subjective confidence.
            </p>
          </div>
          <img
            src={`${API_BASE}${activeLayer.legend_url}`}
            alt="Colorbar Legend"
            className="h-10 object-contain"
          />
        </div>
      )}

      {/* Interactive Pixel Inspector Card */}
      {inspectMode && (
        <div className="bg-cyan-950/30 rounded-lg p-3 border border-cyan-500/30 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5 text-cyan-300 font-semibold text-xs">
              <Crosshair className="w-3.5 h-3.5" />
              <span>Pixel Inspector (Click imagery above to sample)</span>
            </div>
            <span className="text-[10px] font-mono text-cyan-400/80">RAW PHYSICAL DN / REFLECTANCE</span>
          </div>

          {inspectedPixelData ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs pt-1">
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-bold block mb-1">Coordinates</span>
                <p className="text-slate-200 font-mono">
                  Pixel: ({inspectedPixelData.pixel.col}, {inspectedPixelData.pixel.row})
                </p>
                {inspectedPixelData.geographic_coordinates && (
                  <p className="text-slate-400 font-mono text-[11px]">
                    Geo: {inspectedPixelData.geographic_coordinates.x_coord.toFixed(4)}, {inspectedPixelData.geographic_coordinates.y_coord.toFixed(4)}
                  </p>
                )}
              </div>

              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-bold block mb-1">Band Values</span>
                <div className="flex flex-wrap gap-1 font-mono text-[11px]">
                  {Object.entries(inspectedPixelData.band_values).map(([b, val]) => (
                    <span key={b} className="bg-slate-950 px-1.5 py-0.5 rounded text-slate-300 border border-slate-800">
                      {b}: {val}
                    </span>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-bold block mb-1">Derived & Model State</span>
                {Object.keys(inspectedPixelData.derived_indices).length > 0 && (
                  <div className="flex gap-1 mb-1 font-mono text-[11px]">
                    {Object.entries(inspectedPixelData.derived_indices).map(([idx, val]) => (
                      <span key={idx} className="bg-emerald-950/80 px-1.5 py-0.5 rounded text-emerald-300 border border-emerald-700/40">
                        {idx}: {val}
                      </span>
                    ))}
                  </div>
                )}
                {inspectedPixelData.model_prediction?.status && (
                  <span className="inline-block px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-300 border border-amber-700/40">
                    {inspectedPixelData.model_prediction.status}
                    {inspectedPixelData.model_prediction.probability ? ` (${(inspectedPixelData.model_prediction.probability * 100).toFixed(1)}%)` : ""}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">
              Click anywhere on the image viewer above to inspect radiometric values and model states at that exact raster coordinate.
            </p>
          )}
        </div>
      )}

      {/* Histogram Statistics Modal / Card */}
      {showHistogram && (
        <div className="bg-slate-950 rounded-lg p-4 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-200">
              <BarChart2 className="w-4 h-4 text-indigo-400" />
              <span>50-Bin Radiometric Distribution Histogram</span>
            </div>
            <button
              onClick={() => setShowHistogram(false)}
              className="text-xs text-slate-500 hover:text-white"
            >
              Close
            </button>
          </div>

          {histogramLoading ? (
            <p className="text-xs text-slate-400 animate-pulse">Calculating statistical percentiles...</p>
          ) : histogramData ? (
            <div className="space-y-3">
              {/* Summary Stats Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="bg-slate-900 p-2 rounded">
                  <span className="text-[10px] text-slate-500 uppercase block">Min / Max</span>
                  <span className="font-mono text-slate-200">{histogramData.min} / {histogramData.max}</span>
                </div>
                <div className="bg-slate-900 p-2 rounded">
                  <span className="text-[10px] text-slate-500 uppercase block">Mean / Median</span>
                  <span className="font-mono text-slate-200">{histogramData.mean} / {histogramData.median}</span>
                </div>
                <div className="bg-slate-900 p-2 rounded">
                  <span className="text-[10px] text-slate-500 uppercase block">P2% - P98%</span>
                  <span className="font-mono text-cyan-400">{histogramData.percentiles.p2} - {histogramData.percentiles.p98}</span>
                </div>
                <div className="bg-slate-900 p-2 rounded">
                  <span className="text-[10px] text-slate-500 uppercase block">Valid Pixels</span>
                  <span className="font-mono text-slate-200">
                    {histogramData.total_pixels != null ? histogramData.total_pixels.toLocaleString() : "0"}
                  </span>
                </div>
              </div>

              {/* Graphical Bar Histogram */}
              <div className="h-24 flex items-end gap-0.5 pt-2 bg-slate-900/40 rounded p-1">
                {histogramData.bins.map((bin, i) => {
                  const maxCount = Math.max(...histogramData.bins.map((b) => b.count), 1);
                  const heightPct = Math.max(2, (bin.count / maxCount) * 100);
                  return (
                    <div
                      key={i}
                      title={`Range: [${bin.range_start}, ${bin.range_end}] · Count: ${bin.count}`}
                      style={{ height: `${heightPct}%` }}
                      className="flex-1 bg-indigo-500/80 hover:bg-cyan-400 transition-colors rounded-t-xs"
                    />
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500">Histogram data unavailable for this layer.</p>
          )}
        </div>
      )}
    </div>
  );
};
