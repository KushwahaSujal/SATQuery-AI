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
  { name: "Sentinel-2 Land Cover (India)", source: "ESA \u00b7 Sentinel-2", type: "Optical", resolution: "10 m", format: "Tiff", dateRange: "2024 - 2025", region: "India" },
  { name: "RISAT-1 SAR (India)", source: "ISRO \u00b7 RISAT-1", type: "SAR", resolution: "25 m", format: "Tiff", dateRange: "2023 - 2025", region: "India" },
  { name: "Bangladesh Coastal Change", source: "NASA \u00b7 Sentinel-2", type: "Optical", resolution: "10 m", format: "Tiff", dateRange: "2023 - 2025", region: "Bangladesh" },
  { name: "Urban Expansion (Delhi)", source: "ESA \u00b7 Sentinel-2", type: "Optical", resolution: "10 m", format: "Tiff", dateRange: "2022 - 2025", region: "Delhi, India" },
  { name: "Forest Monitoring (Amazon)", source: "ESA \u00b7 Sentinel-2", type: "Multispectral", resolution: "10 m", format: "Tiff", dateRange: "2021 - 2025", region: "Amazon, Brazil" },
  { name: "Water Resources (Ganges Basin)", source: "ISRO \u00b7 RISAT + Sentinel-2", type: "Optical + SAR", resolution: "10 m / 25 m", format: "Tiff", dateRange: "2023 - 2025", region: "India" },
];

const typeStyles: Record<string, { bg: string; color: string }> = {
  Optical: { bg: "var(--primary-glow)", color: "var(--primary)" },
  SAR: { bg: "var(--violet-bg)", color: "var(--violet)" },
  Multispectral: { bg: "var(--green-bg)", color: "var(--green)" },
  "Optical + SAR": { bg: "var(--cyan-glow)", color: "var(--cyan)" },
};

export default function DatasetsPage() {
  const [filter, setFilter] = useState<Filter>("All");
  const [selectedIdx, setSelectedIdx] = useState(0);

  const selected = SAMPLE_DATASETS[selectedIdx];

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden" style={{ background: "var(--canvas)" }}>
      {/* Main */}
      <main className="flex-1 overflow-y-auto px-6 py-5">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "var(--heading)" }}>Datasets</h1>
            <p className="text-xs" style={{ color: "var(--text-2)" }}>Browse and manage satellite imagery datasets. Use these datasets for your analysis or upload your own.</p>
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition"
            style={{ background: "var(--cyan)", color: "var(--canvas)", boxShadow: "0 0 15px var(--cyan-glow)" }}
          >
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
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition"
              style={filter === label ? {
                background: "var(--cyan-glow)",
                border: "1px solid var(--cyan)",
                color: "var(--cyan)",
              } : {
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                color: "var(--text)",
              }}
            >
              <span>{label}</span>
              <span
                className="text-[10px] px-1.5 py-0.2 rounded-full"
                style={filter === label ? {
                  background: "var(--cyan-glow)",
                  color: "var(--cyan)",
                } : {
                  background: "var(--surface-3)",
                  color: "var(--text-2)",
                }}
              >{count}</span>
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {SAMPLE_DATASETS.map((ds, i) => (
            <div
              key={ds.name}
              onClick={() => setSelectedIdx(i)}
              className="rounded-xl overflow-hidden transition group flex flex-col cursor-pointer"
              style={i === selectedIdx ? {
                background: "var(--surface-2)",
                border: "1px solid var(--cyan)",
              } : {
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
              }}
            >
              <div className="h-32 relative overflow-hidden" style={{ background: "var(--surface-3)" }}>
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_60%_40%,var(--green-bg),transparent_60%)]" />
                <span
                  className="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded text-[10px] font-medium backdrop-blur"
                  style={{ background: typeStyles[ds.type]?.bg || "var(--primary-glow)", color: typeStyles[ds.type]?.color || "var(--primary)" }}
                >{ds.type}</span>
              </div>
              <div className="p-3.5 flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-semibold transition" style={{ color: "var(--heading)" }}>{ds.name}</h3>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--text-2)" }}>{ds.source}</p>
                  <div className="flex items-center gap-3 text-[10px] mt-2.5" style={{ color: "var(--text-2)" }}>
                    <span>{ds.resolution}</span>
                    <span>{ds.format}</span>
                    <span>{ds.dateRange}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3 pt-2.5" style={{ borderTop: "1px solid var(--border)" }}>
                  <span className="text-[10px] px-2 py-0.5 rounded" style={{ background: "var(--surface-3)", color: "var(--text)" }}>{ds.region}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Right Detail Panel */}
      <aside
        className="w-[360px] overflow-y-auto shrink-0 flex flex-col p-4"
        style={{ borderLeft: "1px solid var(--border)", background: "var(--surface)" }}
      >
        <div className="relative rounded-xl overflow-hidden h-52 mb-4" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_60%_40%,var(--green-bg),transparent_60%)]" />
        </div>
        <div className="mb-3">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h2 className="text-sm font-bold leading-tight" style={{ color: "var(--heading)" }}>{selected.name}</h2>
            <span
              className="px-2 py-0.5 rounded text-[10px] font-medium shrink-0"
              style={{ background: typeStyles[selected.type]?.bg || "var(--primary-glow)", color: typeStyles[selected.type]?.color || "var(--primary)" }}
            >{selected.type}</span>
          </div>
          <p className="text-[11px]" style={{ color: "var(--text-2)" }}>{selected.source}</p>
        </div>
        <div className="space-y-2 mb-5">
          <h3 className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "var(--text)" }}>Dataset Information</h3>
          {[["Source", selected.source.split(" \u00b7 ")[0]], ["Sensor", selected.source.split(" \u00b7 ")[1] || "\u2014"], ["Resolution", selected.resolution], ["Format", selected.format], ["Date Range", selected.dateRange], ["Region", selected.region]].map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs py-0.5" style={{ borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-2)" }}>{k}</span>
              <span className="font-medium" style={{ color: "var(--text)" }}>{v}</span>
            </div>
          ))}
        </div>
        <button
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-semibold text-xs transition"
          style={{ background: "var(--cyan)", color: "var(--canvas)", boxShadow: "0 0 15px var(--cyan-glow)" }}
        >
          Open in Analysis
        </button>
      </aside>
    </div>
  );
}
