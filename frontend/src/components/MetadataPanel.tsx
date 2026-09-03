"use client";

import React from "react";
import { Info, Layers, Compass, BarChart2 } from "lucide-react";
import { UploadedRasterMeta } from "./UploadPanel";

interface MetadataPanelProps {
  metadata: UploadedRasterMeta[];
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({ metadata }) => {
  if (!metadata || metadata.length === 0) return null;

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm">
      <div className="flex items-center space-x-2 mb-4">
        <Layers className="w-4 h-4 text-cyan-400" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
          Geospatial & Sensor Metadata
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {metadata.map((meta, idx) => (
          <div key={idx} className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-xs font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <span className="font-bold text-slate-200">Image {idx + 1}: {meta.filename}</span>
              <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {meta.format}
              </span>
            </div>

            <div className="space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Dimensions:</span>
                <span className="font-semibold text-slate-200">{meta.width} × {meta.height} px</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Bands / Dtype:</span>
                <span>{meta.bands} bands ({meta.dtype})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">CRS:</span>
                <span className="text-cyan-300">{meta.crs || "Pixel space (Non-georeferenced)"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Modality:</span>
                <span className="text-emerald-300 font-bold uppercase">{meta.detected_modality}</span>
              </div>
              <div className="border-t border-slate-800 pt-2 text-[11px] text-slate-400">
                <span className="text-slate-500">Modality Reason:</span> {meta.modality_reason}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
