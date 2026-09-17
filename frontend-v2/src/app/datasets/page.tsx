"use client";

import { useState } from "react";

type Filter = "All" | "Optical" | "SAR" | "Multispectral" | "Bi-temporal";

const FILTERS: { label: string; count: number }[] = [
  { label: "All", count: 124 },
  { label: "Optical", count: 68 },
  { label: "SAR", count: 32 },
  { label: "Multispectral", count: 18 },
  { label: "Bi-temporal", count: 6 },
];

const SAMPLE_DATASETS = [
  { name: "Sentinel-2 Land Cover (India)", source: "ESA · Sentinel-2", type: "Optical", resolution: "10 m", format: "Tiff", dateRange: "2024 - 2025", region: "India" },
  { name: "RISAT-1 SAR (India)", source: "ISRO · RISAT-1", type: "SAR", resolution: "25 m", format: "Tiff", dateRange: "2023 - 2025", region: "India" },
  { name: "Bangladesh Coastal Change", source: "NASA · Sentinel-2", type: "Optical", resolution: "10 m", format: "Tiff", dateRange: "2023 - 2025", region: "Bangladesh" },
  { name: "Urban Expansion (Delhi)", source: "ESA · Sentinel-2", type: "Optical", resolution: "10 m", format: "Tiff", dateRange: "2022 - 2025", region: "Delhi, India" },
  { name: "Forest Monitoring (Amazon)", source: "ESA · Sentinel-2", type: "Multispectral", resolution: "10 m", format: "Tiff", dateRange: "2021 - 2025", region: "Amazon, Brazil" },
  { name: "Water Resources (Ganges Basin)", source: "ISRO · RISAT + Sentinel-2", type: "Optical + SAR", resolution: "10 m / 25 m", format: "Tiff", dateRange: "2023 - 2025", region: "India" },
];

const typeColors: Record<string, string> = {
  Optical: "bg-sky-500/80",
  SAR: "bg-purple-600/80",
  Multispectral: "bg-purple-600/80",
  "Optical + SAR": "bg-emerald-600/80",
};

export default function DatasetsPage() {
  const [filter, setFilter] = useState<Filter>("All");
  const [view, setView] = useState<"grid" | "list">("grid");
  const [selectedIdx, setSelectedIdx] = useState(0);

  const selected = SAMPLE_DATASETS[selectedIdx];

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* Main */}
      <main className="flex-1 overflow-y-auto px-6 py-5">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight mb-1">Datasets</h1>
            <p className="text-xs text-slate-400">Browse and manage satellite imagery datasets. Use these datasets for your analysis or upload your own.</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 text-xs font-semibold shadow-[0_0_15px_rgba(6,182,212,0.4)] transition">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Upload Dataset
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
          {FILTERS.map(({ label, count }) => (
            <button
              key={label}
              onClick={() => setFilter(label as Filter)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filter === label ? "bg-cyan-950/60 border border-cyan-500/50 text-cyan-400" : "bg-[#0b1324] border border-[#17233d] text-slate-300 hover:border-slate-700"
              }`}
            >
              <span>{label}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${filter === label ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"}`}>{count}</span>
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {SAMPLE_DATASETS.map((ds, i) => (
            <div
              key={ds.name}
              onClick={() => setSelectedIdx(i)}
              className={`rounded-xl overflow-hidden transition group flex flex-col cursor-pointer ${
                i === selectedIdx ? "bg-[#0b1324] border border-cyan-500/40" : "bg-[#0b1324] border border-[#17233d] hover:border-slate-600"
              }`}
            >
              <div className="h-32 bg-gradient-to-br from-slate-800 to-slate-900 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_60%_40%,rgba(34,197,94,0.15),transparent_60%)]" />
                <span className={`absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded text-[10px] font-medium text-white backdrop-blur ${typeColors[ds.type] || "bg-sky-500/80"}`}>{ds.type}</span>
              </div>
              <div className="p-3.5 flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-semibold text-white group-hover:text-cyan-400 transition">{ds.name}</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">{ds.source}</p>
                  <div className="flex items-center gap-3 text-[10px] text-slate-400 mt-2.5">
                    <span>{ds.resolution}</span>
                    <span>{ds.format}</span>
                    <span>{ds.dateRange}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-slate-800/80">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">{ds.region}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Right Detail Panel */}
      <aside className="w-[360px] border-l border-[#17233d] bg-[#050a14] overflow-y-auto shrink-0 flex flex-col p-4">
        <div className="relative rounded-xl overflow-hidden h-52 bg-gradient-to-br from-slate-800 to-slate-900 border border-[#17233d] mb-4">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_60%_40%,rgba(34,197,94,0.2),transparent_60%)]" />
        </div>
        <div className="mb-3">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h2 className="text-sm font-bold text-white leading-tight">{selected.name}</h2>
            <span className={`px-2 py-0.5 rounded text-[10px] font-medium text-white backdrop-blur shrink-0 ${typeColors[selected.type] || "bg-sky-500/80"}`}>{selected.type}</span>
          </div>
          <p className="text-[11px] text-slate-400">{selected.source}</p>
        </div>
        <div className="space-y-2 mb-5">
          <h3 className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">Dataset Information</h3>
          {[["Source", selected.source.split(" · ")[0]], ["Sensor", selected.source.split(" · ")[1] || "—"], ["Resolution", selected.resolution], ["Format", selected.format], ["Date Range", selected.dateRange], ["Region", selected.region]].map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs py-0.5 border-b border-slate-900">
              <span className="text-slate-400">{k}</span>
              <span className="text-slate-200 font-medium">{v}</span>
            </div>
          ))}
        </div>
        <button className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-semibold text-xs transition shadow-[0_0_15px_rgba(6,182,212,0.3)]">
          Open in Analysis
        </button>
      </aside>
    </div>
  );
}
