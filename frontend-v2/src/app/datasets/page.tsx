"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { SpotlightCard } from "@/components/ui/spotlight-card";

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } } };
const cardVariant = { hidden: { opacity: 0, y: 16, scale: 0.97 }, show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } } };

interface DatasetItem {
  id: string;
  name: string;
  source: string;
  type: string;
  resolution: string;
  format: string;
  years: string;
  region: string;
  size: string;
  dateAdded: string;
  cropClass: string;
  typeColor: string;
  bands?: string;
  projection?: string;
  files?: string;
  license?: string;
  desc?: string;
}

const DATASETS: DatasetItem[] = [
  {
    id: "delhi-urban",
    name: "Urban Area Detection (Delhi)",
    source: "ESA · Sentinel-2",
    type: "Optical",
    resolution: "10 m",
    format: "Tiff",
    years: "2022 - 2025",
    region: "Delhi, India",
    size: "2.4 GB",
    dateAdded: "Oct 12, 2025",
    cropClass: "sat-crop-urban",
    typeColor: "bg-sky-950 text-sky-400 border-sky-800/60",
    bands: "B02, B03, B04, B08, B11, B12",
    projection: "UTM Zone 44N (EPSG:32644)",
    files: "12 GeoTIFF files",
    license: "Open Data (CC BY 4.0)",
    desc: "High-resolution optical imagery for urban area analysis and land use classification in Delhi region.",
  },
  {
    id: "sentinel-india",
    name: "Sentinel-2 Land Cover (India)",
    source: "ESA · Sentinel-2",
    type: "Optical",
    resolution: "10 m",
    format: "Tiff",
    years: "2024 - 2025",
    region: "India",
    size: "3.8 GB",
    dateAdded: "Oct 11, 2025",
    cropClass: "sat-crop-river",
    typeColor: "bg-sky-950 text-sky-400 border-sky-800/60",
    bands: "B02, B03, B04, B08",
    projection: "WGS 84 / UTM 43N",
    files: "18 GeoTIFF files",
    license: "Open Data (CC BY 4.0)",
    desc: "Comprehensive multispectral optical data surveying diverse land cover classes across the Indian subcontinent.",
  },
  {
    id: "risat-sar",
    name: "RISAT-1 SAR (India)",
    source: "ISRO · RISAT-1",
    type: "SAR",
    resolution: "25 m",
    format: "Tiff",
    years: "2023 - 2025",
    region: "India",
    size: "1.9 GB",
    dateAdded: "Oct 05, 2025",
    cropClass: "sat-crop-sar",
    typeColor: "bg-[var(--surface-3)] text-[var(--text-2)] border-[var(--border)]",
    bands: "C-band (HH, HV)",
    projection: "LCC (ISRO Indian Grid)",
    files: "8 GeoTIFF files",
    license: "ISRO Open Science",
    desc: "Active synthetic aperture radar imagery providing all-weather, day-and-night surface backscatter observation.",
  },
  {
    id: "bangladesh-coast",
    name: "Bangladesh Coastal Change",
    source: "NASA · Sentinel-2",
    type: "Bi-temporal",
    resolution: "10 m",
    format: "Tiff",
    years: "2023 - 2025",
    region: "Bangladesh",
    size: "4.8 GB",
    dateAdded: "Oct 10, 2025",
    cropClass: "sat-crop-coastal",
    typeColor: "bg-[var(--green-bg)] text-[var(--green)] border-[var(--green)]/40",
    bands: "B02, B03, B04, B08, NDVI",
    projection: "UTM Zone 45N",
    files: "14 GeoTIFF files",
    license: "Open Data (CC BY 4.0)",
    desc: "Multi-year coastal shoreline change detection and erosion tracking in the Bengal delta region.",
  },
  {
    id: "amazon-forest",
    name: "Forest Monitoring (Amazon)",
    source: "ESA · Sentinel-2",
    type: "Multispectral",
    resolution: "10 m",
    format: "Tiff",
    years: "2021 - 2025",
    region: "Amazon, Brazil",
    size: "3.6 GB",
    dateAdded: "Oct 08, 2025",
    cropClass: "sat-crop-amazon",
    typeColor: "bg-[var(--surface-3)] text-[var(--text-2)] border-[var(--border)]",
    bands: "All 13 Sentinel-2 Bands",
    projection: "UTM Zone 20S",
    files: "24 GeoTIFF files",
    license: "Copernicus Open Access",
    desc: "Dense rainforest canopy observation and biomass disturbance tracking across the Brazilian Amazon basin.",
  },
  {
    id: "ganges-water",
    name: "Water Resources (Ganges Basin)",
    source: "ISRO · RISAT + Sentinel-2",
    type: "Optical + SAR",
    resolution: "10 m / 25 m",
    format: "Tiff",
    years: "2023 - 2025",
    region: "India",
    size: "5.2 GB",
    dateAdded: "Oct 02, 2025",
    cropClass: "sat-crop-water",
    typeColor: "bg-[var(--surface-2)] text-[var(--cyan)] border-[var(--cyan)]/40",
    bands: "Optical RGB-NIR + SAR HH/HV",
    projection: "UTM Zone 44N",
    files: "16 GeoTIFF files",
    license: "Joint Mission Research",
    desc: "Fused optical and SAR telemetry monitoring hydrologic extent, flood plains, and riverbank dynamics.",
  },
];

export default function DatasetsPage() {
  const [selectedFilter, setSelectedFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDataset, setSelectedDataset] = useState<DatasetItem>(DATASETS[0]);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [carouselIndex, setCarouselIndex] = useState(1);

  const filterCounts: Record<string, number> = {
    All: 124,
    Optical: 68,
    SAR: 32,
    Multispectral: 18,
    "Bi-temporal": 6,
  };

  const filteredDatasets = DATASETS.filter((item) => {
    const matchesFilter = selectedFilter === "All" || item.type.includes(selectedFilter);
    const matchesSearch =
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.region.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }} className="bg-[var(--canvas)] text-[var(--text)] antialiased font-sans h-screen overflow-hidden flex flex-col selection:bg-cyan-500/30 selection:text-[var(--cyan)]">
      {/* Full-width TopBar */}
      <TopBar
        showBrand={true}
        searchPlaceholder="Search datasets, locations, or keywords..."
        onSearch={(q) => setSearchQuery(q)}
      />

      {/* Main Body Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar hideBrand={true} activeItem="datasets" className="h-full" />

        {/* Workspace Center Content */}
        <main className="flex-1 overflow-y-auto px-6 py-5" data-purpose="datasets-workspace">
          {/* Workspace Header */}
          <div className="flex items-start justify-between mb-5">
            <div>
              <h1 className="text-2xl font-bold text-[var(--heading)] tracking-tight mb-1">Datasets</h1>
              <p className="text-xs text-[var(--text-3)]">
                Browse and manage satellite imagery datasets. Use these datasets for your analysis or upload your own.
              </p>
            </div>
            <Link
              href="/analysis?action=upload"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--cyan)] hover:bg-cyan-300 text-[var(--canvas)] text-xs font-semibold shadow-[0_0_15px_rgba(6,182,212,0.4)] transition"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Upload Dataset</span>
            </Link>
          </div>

          {/* Filter Pills Row */}
          <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1" data-purpose="category-filters">
            {["All", "Optical", "SAR", "Multispectral", "Bi-temporal"].map((filter) => {
              const active = selectedFilter === filter;
              return (
                <button
                  key={filter}
                  onClick={() => setSelectedFilter(filter)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
                    active
                      ? "bg-[var(--cyan-glow)] border border-[var(--cyan)]/50 text-[var(--cyan)] shadow-[0_0_10px_rgba(6,182,212,0.15)]"
                      : "bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text-2)] hover:border-[var(--border-strong)]"
                  }`}
                >
                  <span>{filter}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      active ? "bg-cyan-500/20 text-[var(--cyan)]" : "bg-[var(--surface-2)] text-[var(--text-3)]"
                    }`}
                  >
                    {filterCounts[filter] ?? 0}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Secondary Controls & Filter Dropdowns */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5" data-purpose="secondary-filter-bar">
            {/* Sub Search Input */}
            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <svg className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)]"
                placeholder="Search datasets..."
                type="text"
              />
            </div>

            <div className="flex items-center gap-2.5">
              {/* Dropdown: Regions */}
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] text-xs text-[var(--text-2)] hover:border-[var(--border-strong)]">
                <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M12 21s-6-5.33-6-10a6 6 0 0112 0c0 4.67-6 10-6 10z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
                <span>All Regions</span>
                <svg className="w-3 h-3 text-[var(--text-3)] ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
              </button>

              {/* Dropdown: Resolutions */}
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] text-xs text-[var(--text-2)] hover:border-[var(--border-strong)]">
                <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <rect height="7" rx="1" width="7" x="3" y="3" />
                  <rect height="7" rx="1" width="7" x="14" y="3" />
                  <rect height="7" rx="1" width="7" x="14" y="14" />
                  <rect height="7" rx="1" width="7" x="3" y="14" />
                </svg>
                <span>All Resolutions</span>
                <svg className="w-3 h-3 text-[var(--text-3)] ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
              </button>

              {/* Dropdown: Sort */}
              <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] text-xs text-[var(--text-2)] hover:border-[var(--border-strong)]">
                <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
                <span>Newest First</span>
                <svg className="w-3 h-3 text-[var(--text-3)] ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
              </button>

              {/* View Switcher (Grid / List) */}
              <div className="flex items-center rounded-lg bg-[var(--surface-2)] border border-[var(--border)] p-0.5">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-1 rounded transition ${viewMode === "grid" ? "bg-[var(--surface-2)] text-[var(--cyan)]" : "text-[var(--text-3)] hover:text-[var(--text)]"}`}
                  title="Grid View"
                >
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`p-1 rounded transition ${viewMode === "list" ? "bg-[var(--surface-2)] text-[var(--cyan)]" : "text-[var(--text-3)] hover:text-[var(--text)]"}`}
                  title="List View"
                >
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* Dataset Cards Grid */}
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8"
            data-purpose="dataset-card-grid"
          >
            {filteredDatasets.map((dataset) => {
              const isSelected = selectedDataset.id === dataset.id;
              return (
                <motion.div key={dataset.id} variants={cardVariant}>
                <SpotlightCard
                  spotlightColor="rgba(0, 199, 217, 0.06)"
                  onClick={() => setSelectedDataset(dataset)}
                  className={`rounded-xl bg-[var(--surface-2)] border transition-all duration-150 group flex flex-col cursor-pointer overflow-hidden ${
                    isSelected ? "border-[var(--cyan)] shadow-[0_0_15px_rgba(6,182,212,0.2)]" : "border-[var(--border)] hover:border-[var(--border-strong)]"
                  }`}
                >
                  <div className={`h-32 ${dataset.cropClass} relative overflow-hidden`}>
                    <span className="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded text-[10px] font-medium bg-sky-500/80 text-[var(--heading)] backdrop-blur">
                      {dataset.type}
                    </span>
                  </div>
                  <div className="p-3.5 flex-1 flex flex-col justify-between">
                    <div>
                      <h3 className="text-xs font-semibold text-[var(--heading)] group-hover:text-[var(--cyan)] transition">{dataset.name}</h3>
                      <p className="text-[11px] text-[var(--text-3)] mt-0.5">{dataset.source}</p>
                      <div className="flex items-center gap-3 text-[10px] text-[var(--text-3)] mt-2.5">
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="12 6 12 12 16 14" />
                          </svg>
                          {dataset.resolution}
                        </span>
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                          </svg>
                          {dataset.format}
                        </span>
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <rect height="18" rx="2" width="18" x="3" y="4" />
                            <line x1="16" x2="16" y1="2" y2="6" />
                            <line x1="8" x2="8" y1="2" y2="6" />
                            <line x1="3" x2="21" y1="10" y2="10" />
                          </svg>
                          {dataset.years}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-[var(--border)]/80">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[var(--surface-2)] text-[var(--text-2)]">{dataset.region}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          alert(`Downloading metadata for ${dataset.name}`);
                        }}
                        className="p-1 text-[var(--text-3)] hover:text-[var(--heading)] transition"
                        title="Download"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </SpotlightCard>
                </motion.div>
              );
            })}
          </motion.div>

          {/* Recent Datasets Table */}
          <section className="rounded-xl bg-[var(--surface-2)] border border-[var(--border)] p-4 mb-4" data-purpose="recent-datasets-section">
            <div className="flex items-center justify-between mb-3.5">
              <h2 className="text-xs font-semibold text-[var(--heading)] tracking-wide">Recent Datasets</h2>
              <button onClick={() => setSelectedFilter("All")} className="text-xs font-medium text-[var(--cyan)] hover:text-[var(--cyan)] transition">
                View All
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[10px] font-semibold text-[var(--text-3)] uppercase tracking-wider">
                    <th className="py-2.5 px-3">Name</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Resolution</th>
                    <th className="py-2.5 px-3">Region</th>
                    <th className="py-2.5 px-3">Date Added</th>
                    <th className="py-2.5 px-3">Size</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-xs divide-y divide-slate-800/60 font-normal">
                  {DATASETS.map((ds) => (
                    <tr
                      key={ds.id}
                      onClick={() => setSelectedDataset(ds)}
                      className="hover:bg-[var(--surface-hover)]/30 transition cursor-pointer"
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2.5">
                          <div className={`w-7 h-7 rounded ${ds.cropClass} shrink-0 border border-[var(--border)]`} />
                          <span className="font-medium text-[var(--text)]">{ds.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${ds.typeColor}`}>
                          {ds.type}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-[var(--text-2)]">{ds.resolution}</td>
                      <td className="py-3 px-3 text-[var(--text-2)]">{ds.region}</td>
                      <td className="py-3 px-3 text-[var(--text-3)]">{ds.dateAdded}</td>
                      <td className="py-3 px-3 text-[var(--text-2)] font-mono text-[11px]">{ds.size}</td>
                      <td className="py-3 px-3 text-right">
                        <button className="text-[var(--text-3)] hover:text-[var(--heading)] p-1">⋮</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </main>

        {/* Right Detail Panel */}
        <aside
          className="w-[360px] border-l border-[var(--border)] bg-[var(--surface)] overflow-y-auto shrink-0 flex flex-col p-4 select-none"
          data-purpose="dataset-detail-panel"
        >
          {/* Preview Carousel Card */}
          <div className="relative rounded-xl overflow-hidden h-52 sat-preview-delhi-main border border-[var(--border)] mb-4 group shadow-lg">
            <div className="absolute top-2.5 right-2.5 z-10 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] font-semibold text-[var(--heading)] border border-[var(--border)]">
              {carouselIndex}/4
            </div>
            <button
              onClick={() => setCarouselIndex((prev) => (prev > 1 ? prev - 1 : 4))}
              className="absolute left-2 top-1/2 -translate-y-1/2 z-10 w-6 h-6 rounded-full bg-[var(--scrim)] hover:bg-[var(--scrim)]/80 flex items-center justify-center text-[var(--heading)] border border-[var(--border)] transition"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M15 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
            </button>
            <button
              onClick={() => setCarouselIndex((prev) => (prev < 4 ? prev + 1 : 1))}
              className="absolute right-2 top-1/2 -translate-y-1/2 z-10 w-6 h-6 rounded-full bg-[var(--scrim)] hover:bg-[var(--scrim)]/80 flex items-center justify-center text-[var(--heading)] border border-[var(--border)] transition"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
            </button>
          </div>

          {/* Detail Header */}
          <div className="mb-3">
            <div className="flex items-start justify-between gap-2 mb-1">
              <h2 className="text-sm font-bold text-[var(--heading)] leading-tight">{selectedDataset.name}</h2>
              <span className={`px-2 py-0.5 rounded text-[10px] font-medium border shrink-0 ${selectedDataset.typeColor}`}>
                {selectedDataset.type}
              </span>
            </div>
            <p className="text-[11px] text-[var(--text-3)]">{selectedDataset.source}</p>
          </div>

          {/* Quick Specs Row */}
          <div className="flex items-center gap-3 text-[11px] text-[var(--text-2)] pb-3 mb-3 border-b border-[var(--border)]">
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              {selectedDataset.resolution}
            </span>
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              {selectedDataset.format}
            </span>
            <span className="text-[var(--text-3)]">{selectedDataset.years}</span>
          </div>

          {/* Location Badge */}
          <div className="mb-3">
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[var(--surface-2)]/80 text-[var(--cyan)] border border-[var(--border)]">
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M12 21s-6-5.33-6-10a6 6 0 0112 0c0 4.67-6 10-6 10z" />
              </svg>
              {selectedDataset.region}
            </span>
          </div>

          {/* Text Description */}
          <p className="text-[11px] text-[var(--text-3)] leading-relaxed mb-4">
            {selectedDataset.desc || "High-resolution optical imagery for remote sensing and land use classification."}
          </p>

          {/* Dataset Information List */}
          <div className="space-y-2 mb-5">
            <h3 className="text-[11px] font-bold text-[var(--text-2)] uppercase tracking-wider mb-2">Dataset Information</h3>
            <div className="flex justify-between text-xs py-0.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-3)]">Source</span>
              <span className="text-[var(--text)] font-medium">{selectedDataset.source.split("·")[0].trim()}</span>
            </div>
            <div className="flex justify-between text-xs py-0.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-3)]">Sensor</span>
              <span className="text-[var(--text)] font-medium">{selectedDataset.source.split("·")[1]?.trim() || "Multi"}</span>
            </div>
            <div className="flex justify-between text-xs py-0.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-3)]">Bands</span>
              <span className="text-[var(--text)] font-medium">{selectedDataset.bands || "Optical RGB-NIR"}</span>
            </div>
            <div className="flex justify-between text-xs py-0.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-3)]">Projection</span>
              <span className="text-[var(--text)] font-medium">{selectedDataset.projection || "WGS 84 / UTM"}</span>
            </div>
            <div className="flex justify-between text-xs py-0.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-3)]">Size</span>
              <span className="text-[var(--text)] font-medium font-mono">{selectedDataset.size}</span>
            </div>
            <div className="flex justify-between text-xs py-0.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-3)]">Files</span>
              <span className="text-[var(--text)] font-medium">{selectedDataset.files || "12 files"}</span>
            </div>
            <div className="flex justify-between text-xs py-0.5">
              <span className="text-[var(--text-3)]">License</span>
              <span className="text-[var(--text)] font-medium">{selectedDataset.license || "Open Data (CC BY 4.0)"}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-2 mb-6" data-purpose="detail-actions">
            <Link
              href={`/analysis?dataset=${encodeURIComponent(selectedDataset.id)}`}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[var(--cyan)] hover:bg-cyan-300 text-[var(--canvas)] font-semibold text-xs transition shadow-[0_0_15px_rgba(6,182,212,0.3)]"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Open in Analysis</span>
            </Link>
            <button
              onClick={() => alert(`Starting download for ${selectedDataset.name}`)}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[var(--surface-2)] hover:bg-[var(--surface-hover)] border border-[var(--border)] text-[var(--text)] text-xs font-medium transition"
            >
              <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              <span>Download Dataset</span>
            </button>
          </div>

          {/* Related Datasets Section */}
          <div>
            <h3 className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-2.5">Related Datasets</h3>
            <div className="space-y-2.5">
              {DATASETS.filter((d) => d.id !== selectedDataset.id)
                .slice(0, 3)
                .map((rel) => (
                  <div
                    key={rel.id}
                    onClick={() => setSelectedDataset(rel)}
                    className="flex items-center justify-between p-2 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--border-strong)] transition cursor-pointer"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`w-10 h-10 rounded ${rel.cropClass} shrink-0 border border-[var(--border)]`} />
                      <div>
                        <p className="text-xs font-medium text-[var(--text)]">{rel.name}</p>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5">
                          {rel.resolution} · {rel.years}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium border ${rel.typeColor}`}>
                        {rel.type}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </aside>
      </div>
    </motion.div>
  );
}
