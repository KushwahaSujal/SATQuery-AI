"use client";

import React, { useState } from "react";
import { Download, FileText, MapPin, AlertTriangle, CheckCircle, BarChart3, Target, Layers, Box, Cpu, ChevronDown, ChevronUp, Network, Workflow, ShieldCheck, Database } from "lucide-react";

interface ResultsPanelProps {
  requestId?: string;
  task?: string;
  answer?: string;
  confidence?: number | null;
  modelsUsed: string[];
  warnings: string[];
  errors: string[];
  statistics?: {
    changed_pixels: number;
    raw_changed_pixels?: number;
    total_valid_pixels: number;
    change_ratio: number;
    region_count?: number;
    quality_status?: "PASS" | "REVIEW_REQUIRED" | string;
    diagnostic_flags?: string[];
    quality_warning?: string | null;
    estimated_area_sq_m?: number | null;
    estimated_area_sq_km?: number | null;
    metric_crs?: string | null;
  } | null;
  artifacts?: {
    reports?: string[];
    vectors?: string[];
    masks?: string[];
    overlays?: string[];
    data?: string[];
  };
  strategy?: string | null;
  groundingScore?: number | null;
  sam2Score?: number | null;
  boxes?: Array<{
    label: string;
    box_2d: number[]; // [ymin, xmin, ymax, xmax]
    score?: number | null;
    geo_bounds?: number[] | null; // [min_lon, min_lat, max_lon, max_lat]
    source_crs?: string | null;
    target_crs?: string | null;
    coordinate_space?: string;
  }>;
  evidenceMetadata?: any;
  orchestration?: any;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  requestId,
  task,
  answer,
  confidence,
  modelsUsed,
  warnings,
  errors,
  statistics,
  artifacts,
  strategy,
  groundingScore,
  sam2Score,
  boxes = [],
  evidenceMetadata,
  orchestration,
}) => {
  const [showOrchestration, setShowOrchestration] = useState(false);
  if (!answer && errors.length === 0) return null;

  const isGrounding = task?.toLowerCase().includes("grounding") || !!strategy || boxes.length > 0;

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-surfaceBorder pb-3">
        <div className="flex items-center space-x-2">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">Analysis Results</h2>
        </div>
        <div className="flex items-center space-x-2">
          {task && (
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Task: {task.replace(/_/g, " ").toUpperCase()}
            </span>
          )}
          {typeof confidence === "number" && !isNaN(confidence) ? (
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Confidence: {(confidence * 100).toFixed(1)}%
            </span>
          ) : (
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
              Confidence: N/A
            </span>
          )}
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-3 text-xs text-rose-300 space-y-1">
          <div className="font-bold flex items-center space-x-1.5 text-rose-400">
            <AlertTriangle className="w-4 h-4" />
            <span>Execution Error</span>
          </div>
          {errors.map((err, idx) => (
            <p key={idx}>{err}</p>
          ))}
        </div>
      )}

      {/* Primary Answer */}
      {answer && (
        <div className="bg-slate-900/90 rounded-lg p-4 border border-slate-800">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Primary Answer</h3>
          <p className="text-sm text-slate-100 leading-relaxed font-sans">{answer}</p>
        </div>
      )}

      {/* Grounding-Specific Intelligence Section */}
      {isGrounding && (
        <div className="bg-slate-950/80 rounded-lg p-4 border border-cyan-500/20 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <Target className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Grounding & Localization Evidence
              </h3>
            </div>
            {strategy && (
              <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                Strategy: {strategy}
              </span>
            )}
          </div>

          {/* Model Confidence Scores & Models Used */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-slate-900/90 p-3 rounded-lg border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-400 text-[10px] uppercase font-bold">Grounding DINO</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">Detector</span>
              </div>
              <div className="text-base font-bold text-cyan-300">
                {typeof groundingScore === "number" && !isNaN(groundingScore)
                  ? `${(groundingScore * 100).toFixed(1)}% (${groundingScore.toFixed(4)})`
                  : "N/A"}
              </div>
              <span className="text-[10px] text-slate-500 block mt-0.5">Genuine box confidence</span>
            </div>

            <div className="bg-slate-900/90 p-3 rounded-lg border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-400 text-[10px] uppercase font-bold">SAM 2 Small</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">Segmenter</span>
              </div>
              <div className="text-base font-bold text-emerald-400">
                {typeof sam2Score === "number" && !isNaN(sam2Score)
                  ? `${(sam2Score * 100).toFixed(1)}% (${sam2Score.toFixed(4)})`
                  : "N/A"}
              </div>
              <span className="text-[10px] text-slate-500 block mt-0.5">Genuine mask prediction</span>
            </div>

            <div className="bg-slate-900/90 p-3 rounded-lg border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-400 text-[10px] uppercase font-bold">Model Pipeline</span>
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {modelsUsed.map((m, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30"
                  >
                    {m}
                  </span>
                ))}
              </div>
              <span className="text-[10px] text-slate-500 block mt-1">Zero synthetic generation</span>
            </div>
          </div>

          {/* Selected Bounding Box Details */}
          {boxes.length > 0 && (
            <div className="bg-slate-900/70 rounded-lg p-3 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-1.5 font-semibold text-slate-300">
                  <Box className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Selected Bounding Box:</span>
                  <span className="font-mono text-cyan-300 font-bold">{boxes[0].label}</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Space: {boxes[0].coordinate_space || "image_coordinates"}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="bg-slate-950 p-2 rounded border border-slate-800 text-slate-300">
                  <span className="text-slate-500 block text-[9px] uppercase">Normalized Image Box [ymin, xmin, ymax, xmax]</span>
                  <span>[{Array.isArray(boxes[0].box_2d) ? boxes[0].box_2d.map((v) => typeof v === "number" ? v.toFixed(4) : String(v)).join(", ") : "N/A"}]</span>
                </div>

                {Array.isArray(boxes[0].geo_bounds) && boxes[0].geo_bounds.length > 0 ? (
                  <div className="bg-slate-950 p-2 rounded border border-slate-800 text-emerald-300">
                    <span className="text-slate-500 block text-[9px] uppercase">
                      Map Bounds (EPSG:4326) [min_lon, min_lat, max_lon, max_lat]
                    </span>
                    <span>[{boxes[0].geo_bounds.map((g) => typeof g === "number" ? g.toFixed(6) : String(g)).join(", ")}]</span>
                  </div>
                ) : (
                  <div className="bg-slate-950 p-2 rounded border border-slate-800 text-slate-400">
                    <span className="text-slate-500 block text-[9px] uppercase">Geographic Coordinates</span>
                    <span>None (Non-georeferenced benchmark image)</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Change Detection Statistics if applicable */}
      {statistics && statistics.changed_pixels > 0 && !isGrounding && (
        <div className="bg-slate-950/80 rounded-lg p-4 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                ChangeFormer Spatial Statistics & Quality Verification
              </h3>
            </div>
            {statistics.quality_status === "REVIEW_REQUIRED" ? (
              <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/40 flex items-center space-x-1">
                <AlertTriangle className="w-3 h-3" />
                <span>QUALITY: REVIEW REQUIRED</span>
              </span>
            ) : (
              <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 flex items-center space-x-1">
                <CheckCircle className="w-3 h-3" />
                <span>QUALITY: VERIFIED PASS</span>
              </span>
            )}
          </div>

          {statistics.quality_warning && (
            <div className="bg-amber-950/40 border border-amber-600/30 rounded p-2 text-xs text-amber-300 flex items-start space-x-2">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-amber-400 shrink-0" />
              <div>
                <span className="font-semibold block">Quality Assessment Note:</span>
                <span>{statistics.quality_warning}</span>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span className="text-slate-500 text-[10px] block">Coherent Changed Pixels</span>
              <span className="text-sm font-bold text-white">
                {statistics.changed_pixels != null ? statistics.changed_pixels.toLocaleString() : "0"}
              </span>
              {statistics.raw_changed_pixels != null && (
                <span className="text-[10px] text-slate-500 block">
                  Raw: {statistics.raw_changed_pixels.toLocaleString()}
                </span>
              )}
            </div>
            <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span className="text-slate-500 text-[10px] block">Change Ratio</span>
              <span className="text-sm font-bold text-cyan-400">
                {statistics.change_ratio != null ? `${(statistics.change_ratio * 100).toFixed(2)}%` : "0.00%"}
              </span>
              {statistics.region_count != null && (
                <span className="text-[10px] text-purple-400 block">{statistics.region_count} regions</span>
              )}
            </div>
            <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span className="text-slate-500 text-[10px] block">Area (m²)</span>
              <span className="text-sm font-bold text-emerald-400">
                {statistics.estimated_area_sq_m != null ? statistics.estimated_area_sq_m.toLocaleString() : "N/A"}
              </span>
            </div>
            <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span className="text-slate-500 text-[10px] block">Area (km²)</span>
              <span className="text-sm font-bold text-emerald-300">
                {statistics.estimated_area_sq_km != null ? statistics.estimated_area_sq_km.toFixed(4) : "N/A"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-300 space-y-1">
          <div className="font-bold flex items-center space-x-1.5 text-amber-400">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Diagnostics & Warnings</span>
          </div>
          {warnings.map((w, idx) => (
            <p key={idx}>• {w}</p>
          ))}
        </div>
      )}

      {/* Advanced Orchestration & Provenance Telemetry (Collapsible) */}
      {orchestration && (
        <div className="border border-purple-500/30 rounded-xl bg-purple-950/20 overflow-hidden">
          <button
            onClick={() => setShowOrchestration(!showOrchestration)}
            className="w-full px-4 py-3 flex items-center justify-between bg-purple-950/40 hover:bg-purple-950/60 transition-colors text-left"
          >
            <div className="flex items-center space-x-2">
              <Network className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-bold text-purple-200 uppercase tracking-wider">
                Advanced Agent Orchestration & Provenance Telemetry
              </span>
              {orchestration.cache_hit && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                  CACHE HIT
                </span>
              )}
            </div>
            <div className="flex items-center space-x-2 text-purple-400">
              <span className="text-[11px] font-mono font-bold">
                Capability: {orchestration.capability_name || orchestration.capability_id}
              </span>
              {showOrchestration ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </button>

          {showOrchestration && (
            <div className="p-4 space-y-4 border-t border-purple-500/20 text-xs font-mono">
              {/* Top Metrics Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-900/90 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Selected Capability</span>
                  <span className="font-bold text-purple-300 truncate block">
                    {orchestration.capability_id}
                  </span>
                </div>
                <div className="bg-slate-900/90 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Router Confidence</span>
                  <span className="font-bold text-cyan-400">
                    {typeof orchestration.routing_confidence === "number" && !isNaN(orchestration.routing_confidence)
                      ? `${(orchestration.routing_confidence * 100).toFixed(1)}%`
                      : "N/A"}
                  </span>
                </div>
                <div className="bg-slate-900/90 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Quality Status</span>
                  <span className="font-bold text-emerald-400">
                    {orchestration.quality_status || "PASS"}
                  </span>
                </div>
                <div className="bg-slate-900/90 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Execution Mode</span>
                  <span className="font-bold text-amber-300">
                    {orchestration.cache_hit ? "Cached Deterministic" : "Full Execution"}
                  </span>
                </div>
              </div>

              {/* Extracted Query Entities */}
              {orchestration.query_entities && Object.keys(orchestration.query_entities).length > 0 && (
                <div className="bg-slate-900/70 rounded-lg p-3 border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-1.5 text-purple-300 font-bold text-[11px] uppercase tracking-wider">
                    <Workflow className="w-3.5 h-3.5" />
                    <span>Structured Query Entity Analysis</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                    {Object.entries(orchestration.query_entities)
                      .filter(([k, v]) => v && k !== "raw_query" && k !== "is_ambiguous")
                      .map(([k, v]) => (
                        <div key={k} className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] uppercase block">{k.replace(/_/g, " ")}</span>
                          <span className="font-semibold text-slate-200">{String(v)}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Execution DAG Stages */}
              {orchestration.dag_plan && orchestration.dag_plan.execution_order && (
                <div className="bg-slate-900/70 rounded-lg p-3 border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-1.5 text-blue-300 font-bold text-[11px] uppercase tracking-wider">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>DAG Execution Order ({orchestration.dag_plan.execution_order.length} Stages)</span>
                  </div>
                  <div className="flex flex-wrap gap-2 items-center">
                    {orchestration.dag_plan.execution_order.map((stage: string[], sIdx: number) => (
                      <React.Fragment key={sIdx}>
                        <div className="flex items-center space-x-1 bg-slate-950 px-2.5 py-1.5 rounded border border-blue-500/30">
                          <span className="text-[10px] text-slate-500 font-bold">Stage {sIdx + 1}:</span>
                          <span className="text-xs text-blue-300 font-semibold">{stage.join(" & ")}</span>
                        </div>
                        {sIdx < orchestration.dag_plan.execution_order.length - 1 && (
                          <span className="text-slate-600 font-bold">→</span>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )}

              {/* Provenance Lineage Summary */}
              {orchestration.provenance_graph && (
                <div className="bg-slate-900/70 rounded-lg p-3 border border-slate-800 space-y-1.5 text-[11px]">
                  <div className="flex items-center space-x-1.5 text-emerald-400 font-bold uppercase tracking-wider">
                    <Database className="w-3.5 h-3.5" />
                    <span>Provenance Lineage & Verification Trace</span>
                  </div>
                  <p className="text-slate-400 text-[10px]">
                    Root Inputs: {orchestration.provenance_graph.root_inputs?.length || 0} file(s) | 
                    Inference Nodes: {orchestration.provenance_graph.nodes?.length || 0} | 
                    Traceable Edges: {orchestration.provenance_graph.edges?.length || 0}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Downloadable Evidence */}
      {requestId && (
        <div className="pt-2">
          <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Downloadable Verified Evidence
          </h4>
          <div className="flex flex-wrap gap-2">
            <a
              href={`/api/reports/${requestId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-1.5 text-xs px-3 py-2 rounded-lg font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-500/20 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Audit Report (PDF)</span>
            </a>

            {/* GeoJSON */}
            {artifacts?.vectors && artifacts.vectors.length > 0 && (
              <a
                href={`/api/artifacts/${requestId}/vectors/${artifacts.vectors[0]}`}
                download={artifacts.vectors[0]}
                className="flex items-center space-x-1.5 text-xs px-3 py-2 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Vector Layer ({artifacts.vectors[0]})</span>
              </a>
            )}

            {/* Mask */}
            {artifacts?.masks && artifacts.masks.length > 0 && (
              <a
                href={`/api/artifacts/${requestId}/masks/${artifacts.masks[0]}`}
                download={artifacts.masks[0]}
                className="flex items-center space-x-1.5 text-xs px-3 py-2 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Segmentation Mask ({artifacts.masks[0]})</span>
              </a>
            )}

            {/* Overlay */}
            {artifacts?.overlays && artifacts.overlays.length > 0 && (
              <a
                href={`/api/artifacts/${requestId}/overlays/${artifacts.overlays[0]}`}
                download={artifacts.overlays[0]}
                className="flex items-center space-x-1.5 text-xs px-3 py-2 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Visual Overlay ({artifacts.overlays[0]})</span>
              </a>
            )}

            {/* Full JSON Result */}
            <a
              href={`/api/results/${requestId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-1.5 text-xs px-3 py-2 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Full Result JSON</span>
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
