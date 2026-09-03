"use client";

import React, { useRef } from "react";
import { UploadCloud, Image as ImageIcon, Trash2, CheckCircle2 } from "lucide-react";

export interface UploadedRasterMeta {
  filename: string;
  format: string;
  width: number;
  height: number;
  bands: number;
  dtype: string;
  crs?: string;
  detected_modality: string;
  modality_confidence: number;
  modality_reason: string;
  preview_url?: string;
}

interface UploadPanelProps {
  files: File[];
  metadata: UploadedRasterMeta[];
  isUploading: boolean;
  onFilesSelected: (files: File[]) => void;
  onClear: () => void;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({
  files,
  metadata,
  isUploading,
  onFilesSelected,
  onClear,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const selected = Array.from(e.dataTransfer.files).slice(0, 2);
      onFilesSelected(selected);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = Array.from(e.target.files).slice(0, 2);
      onFilesSelected(selected);
    }
  };

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">Input Imagery</h2>
          <p className="text-xs text-slate-400">Upload 1 image (VQA/Grounding) or 2 paired images (Change/Optical+SAR)</p>
        </div>
        {files.length > 0 && (
          <button
            onClick={onClear}
            className="flex items-center space-x-1 text-xs text-rose-400 hover:text-rose-300 font-medium px-2 py-1 rounded bg-rose-500/10 border border-rose-500/20 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        )}
      </div>

      {files.length === 0 ? (
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-8 text-center cursor-pointer transition-all duration-200 bg-slate-900/40 hover:bg-slate-900/70 group"
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".tif,.tiff,.png,.jpg,.jpeg,.mp4,.mov"
            onChange={handleChange}
            className="hidden"
          />
          <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
            <UploadCloud className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-slate-200 mb-1">
            Drag & drop Satellite Images or Video Footage here
          </p>
          <p className="text-xs text-slate-500">
            Supports GeoTIFF, PNG, JPG satellite rasters, and MP4 / MOV video footage
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {files.map((file, idx) => {
            const meta = metadata[idx];
            const isVideo = file.name.toLowerCase().endsWith(".mp4") || file.name.toLowerCase().endsWith(".mov");
            return (
              <div
                key={idx}
                className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 flex space-x-3 items-center relative overflow-hidden"
              >
                <div className="w-16 h-16 rounded bg-slate-800 flex-shrink-0 flex items-center justify-center overflow-hidden border border-slate-700">
                  {isVideo ? (
                    <div className="text-center">
                      <span className="text-[10px] uppercase font-bold text-emerald-400 block">VIDEO</span>
                      <span className="text-xs text-slate-400">MP4/MOV</span>
                    </div>
                  ) : meta?.preview_url ? (
                    <img
                      src={meta.preview_url}
                      alt={file.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <ImageIcon className="w-6 h-6 text-slate-500" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-mono font-bold ${
                      isVideo
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}>
                      {isVideo ? "Video" : `Image ${idx + 1}`}
                    </span>
                    <span className="text-xs font-semibold text-white truncate" title={file.name}>
                      {file.name}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-400 mt-1">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • {isVideo ? "Video Footage" : meta ? `${meta.width}x${meta.height} • ${meta.bands} bands` : "Inspecting..."}
                  </p>

                  {meta && !isVideo && (
                    <div className="flex items-center space-x-2 mt-1.5">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                        meta.detected_modality === "sar"
                          ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                          : meta.detected_modality === "optical" || meta.detected_modality === "multispectral"
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          : "bg-slate-700/40 text-slate-400 border-slate-600"
                      }`}>
                        {meta.detected_modality} ({(meta.modality_confidence * 100).toFixed(0)}%)
                      </span>
                      {meta.crs && (
                        <span className="text-[10px] font-mono text-slate-400 truncate max-w-[120px]">
                          {meta.crs}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
