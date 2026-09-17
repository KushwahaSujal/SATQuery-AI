"use client";

import { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

interface HistoryItem {
  id: string;
  title: string;
  type: string;
  typeCategory: "Single Image" | "Change Analysis" | "Optical + SAR" | "Bi-temporal";
  desc: string;
  timestamp: string;
  confidence: number;
  status: "Completed" | "Processing" | "Failed";
  tags: string[];
  dualThumb?: { opt: string; sar: string };
  singleThumb?: string;
  stats?: {
    builtUp: string;
    water: string;
    vegetation: string;
  };
}

const HISTORY_ITEMS: HistoryItem[] = [
  {
    id: "h1",
    title: "Urban Area Detection",
    type: "Optical + SAR",
    typeCategory: "Optical + SAR",
    desc: "Use the optical and SAR images together to identify built-up and water-covered regions.",
    timestamp: "Oct 12, 2025 · 11:42 AM",
    confidence: 92,
    status: "Completed",
    tags: ["Optical", "SAR", "Fusion"],
    dualThumb: { opt: "thumb-optical-1", sar: "thumb-sar-1" },
    stats: { builtUp: "+12.4%", water: "+5.1%", vegetation: "-8.7%" },
  },
  {
    id: "h2",
    title: "River Detection",
    type: "Single Image",
    typeCategory: "Single Image",
    desc: "Identify and highlight the river channel in the satellite image.",
    timestamp: "Oct 11, 2025 · 04:21 PM",
    confidence: 89,
    status: "Completed",
    tags: ["Optical", "VQA"],
    singleThumb: "thumb-optical-1",
    stats: { builtUp: "0.0%", water: "+18.2%", vegetation: "-2.1%" },
  },
  {
    id: "h3",
    title: "Urban Expansion Analysis",
    type: "Change Analysis",
    typeCategory: "Change Analysis",
    desc: "Detect urban growth between 2022 and 2025 using bi-temporal images.",
    timestamp: "Oct 09, 2025 · 10:15 AM",
    confidence: 95,
    status: "Completed",
    tags: ["Optical", "Change"],
    dualThumb: { opt: "thumb-optical-1", sar: "thumb-change-red" },
    stats: { builtUp: "+15.8%", water: "-1.2%", vegetation: "-11.4%" },
  },
  {
    id: "h4",
    title: "Water Body Identification",
    type: "Optical + SAR",
    typeCategory: "Optical + SAR",
    desc: "Use optical and SAR data to identify water bodies in the region.",
    timestamp: "Oct 06, 2025 · 02:48 PM",
    confidence: 91,
    status: "Completed",
    tags: ["Optical", "SAR", "Fusion"],
    dualThumb: { opt: "thumb-optical-1", sar: "thumb-sar-1" },
    stats: { builtUp: "+3.1%", water: "+22.4%", vegetation: "-4.5%" },
  },
  {
    id: "h5",
    title: "Region Grounding",
    type: "Single Image",
    typeCategory: "Single Image",
    desc: "Highlight the forest area mentioned in the query.",
    timestamp: "Oct 04, 2025 · 01:12 PM",
    confidence: 76,
    status: "Processing",
    tags: ["Optical", "Grounding"],
    singleThumb: "thumb-forest",
    stats: { builtUp: "+0.5%", water: "0.0%", vegetation: "+1.2%" },
  },
  {
    id: "h6",
    title: "Deforestation Analysis",
    type: "Bi-temporal",
    typeCategory: "Bi-temporal",
    desc: "Has the forest area increased or decreased over the observation period?",
    timestamp: "Oct 02, 2025 · 06:45 PM",
    confidence: 84,
    status: "Completed",
    tags: ["Optical", "Change"],
    dualThumb: { opt: "thumb-forest", sar: "thumb-change-red" },
    stats: { builtUp: "+8.2%", water: "-0.8%", vegetation: "-19.5%" },
  },
  {
    id: "h7",
    title: "Infrastructure Mapping",
    type: "Optical + SAR",
    typeCategory: "Optical + SAR",
    desc: "Identify roads and buildings using optical and SAR multi-sensor data.",
    timestamp: "Sep 27, 2025 · 04:33 PM",
    confidence: 82,
    status: "Completed",
    tags: ["Optical", "Captioning"],
    dualThumb: { opt: "thumb-forest", sar: "thumb-sar-1" },
    stats: { builtUp: "+11.1%", water: "+1.0%", vegetation: "-7.4%" },
  },
];

export default function HistoryPage() {
  const [selectedTab, setSelectedTab] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string>("h1");
  const [selectedChecks, setSelectedChecks] = useState<Record<string, boolean>>({ h1: true });

  const selectedItem = HISTORY_ITEMS.find((item) => item.id === selectedId) || HISTORY_ITEMS[0];

  const filteredItems = HISTORY_ITEMS.filter((item) => {
    const matchesTab = selectedTab === "All" || item.typeCategory === selectedTab;
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.desc.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  const tabCounts: Record<string, number> = {
    All: 24,
    "Single Image": 8,
    "Change Analysis": 6,
    "Optical + SAR": 5,
    "Bi-temporal": 5,
  };

  const toggleCheck = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedChecks((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="bg-[var(--canvas)] text-[var(--text)] antialiased font-sans h-screen overflow-hidden flex flex-col selection:bg-cyan-500 selection:text-[var(--canvas)]">
      {/* Top Global Header */}
      <TopBar
        showBrand={true}
        searchPlaceholder="Search your analyses, locations, or queries..."
        onSearch={(q) => setSearchQuery(q)}
      />

      {/* Core App Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar hideBrand={true} activeItem="history" className="h-full" />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-w-0 bg-[var(--canvas)] overflow-hidden">
          {/* Title & Filters Bar */}
          <div className="p-6 pb-3 border-b border-[var(--border)] shrink-0">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-xl font-bold text-[var(--heading)] tracking-tight">Analysis History</h1>
                <p className="text-xs text-[var(--text-3)] mt-0.5">
                  View and manage your past analyses. Revisit results, download reports, or continue where you left off.
                </p>
              </div>

              {/* Secondary Inline Search */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <svg className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" x2="16.65" y1="21" y2="16.65" />
                  </svg>
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-[var(--surface-2)] border border-[var(--border)] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[var(--text-2)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)] w-52"
                    placeholder="Search history..."
                    type="text"
                  />
                </div>
                <button className="p-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-3)] hover:text-[var(--heading)] transition">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Filter Category Tabs */}
            <div className="flex items-center gap-2 mt-5 overflow-x-auto pb-1 text-xs">
              {["All", "Single Image", "Change Analysis", "Optical + SAR", "Bi-temporal"].map((tab) => {
                const active = selectedTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => setSelectedTab(tab)}
                    className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-medium transition shrink-0 cursor-pointer ${
                      active
                        ? "bg-[var(--surface-3)] text-[var(--cyan)] border border-[var(--cyan)]/40 shadow-sm"
                        : "bg-[var(--surface-2)] text-[var(--text-3)] border border-[var(--border)] hover:text-[var(--text)]"
                    }`}
                  >
                    <span>{tab}</span>
                    <span
                      className={`ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] ${
                        active ? "bg-cyan-500/20 text-[var(--cyan)] font-semibold" : "bg-[var(--surface-2)] text-[var(--text-2)]"
                      }`}
                    >
                      {tabCounts[tab] ?? 0}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* History List Items Scrollable Area */}
          <div className="flex-1 overflow-y-auto p-5 space-y-3">
            {filteredItems.map((item) => {
              const isSelected = selectedId === item.id;
              const isChecked = !!selectedChecks[item.id];
              return (
                <article
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`relative flex items-center justify-between p-3.5 rounded-xl transition-all cursor-pointer ${
                    isSelected
                      ? "bg-[var(--surface)] border-2 border-[var(--cyan)] shadow-[0_0_20px_rgba(0,229,255,0.12)]"
                      : "bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--border-strong)]"
                  }`}
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onClick={(e) => toggleCheck(item.id, e)}
                      onChange={() => {}}
                      className="w-4 h-4 rounded bg-[var(--surface)] border-[var(--cyan)] text-[var(--cyan)]   cursor-pointer"
                    />

                    {/* Dual or Single Thumbnails */}
                    {item.dualThumb ? (
                      <div className="flex items-center gap-1 shrink-0">
                        <div className={`w-14 h-14 rounded-lg overflow-hidden border border-[var(--border)] ${item.dualThumb.opt} relative shadow-inner`}>
                          <span className="absolute bottom-0.5 left-1 text-[8px] font-mono text-[var(--cyan)] bg-[var(--scrim)] px-1 rounded">OPT</span>
                        </div>
                        <div className={`w-14 h-14 rounded-lg overflow-hidden border border-[var(--border)] ${item.dualThumb.sar} relative shadow-inner`}>
                          <span className="absolute bottom-0.5 left-1 text-[8px] font-mono text-[var(--text-2)] bg-[var(--scrim)] px-1 rounded">SAR</span>
                        </div>
                      </div>
                    ) : (
                      <div className={`w-28 h-14 rounded-lg overflow-hidden border border-[var(--border)] ${item.singleThumb || "thumb-forest"} shrink-0 relative shadow-inner`} />
                    )}

                    {/* Analysis Details */}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 text-[10px] font-medium rounded bg-cyan-950/70 border border-[var(--cyan)]/30 text-[var(--cyan)]">
                          {item.type}
                        </span>
                        <h3 className="text-sm font-semibold text-[var(--heading)] truncate">{item.title}</h3>
                      </div>
                      <p className="text-xs text-[var(--text-3)] line-clamp-1">{item.desc}</p>
                      <div className="flex items-center gap-3 mt-2 text-[11px] text-[var(--text-3)]">
                        <span className="flex items-center gap-1.5 text-[var(--text-3)]">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <rect height="18" rx="2" ry="2" width="18" x="3" y="4" />
                            <line x1="16" x2="16" y1="2" y2="6" />
                            <line x1="8" x2="8" y1="2" y2="6" />
                            <line x1="3" x2="21" y1="10" y2="10" />
                          </svg>
                          {item.timestamp}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {item.tags.map((tag) => (
                            <span key={tag} className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] text-[10px] text-[var(--text-2)]">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Confidence & Actions */}
                  <div className="flex items-center gap-5 shrink-0 pl-4">
                    <div className="flex items-center gap-3">
                      {/* Circular Gauge */}
                      <div className="relative w-11 h-11 flex items-center justify-center">
                        <svg className="w-11 h-11 transform -rotate-90" viewBox="0 0 36 36">
                          <path
                            className="text-[var(--heading)]"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3.5"
                          />
                          <path
                            className={item.status === "Processing" ? "text-amber-400" : "text-emerald-400"}
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeDasharray={`${item.confidence}, 100`}
                            strokeLinecap="round"
                            strokeWidth="3.5"
                          />
                        </svg>
                        <span className="absolute text-[11px] font-bold text-[var(--heading)]">{item.confidence}%</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] text-[var(--text-3)]">Confidence</span>
                        {item.status === "Completed" ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-[var(--green-bg)]/40 border border-emerald-500/30 px-2 py-0.5 rounded-full mt-0.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Completed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-400 bg-amber-950/40 border border-amber-500/30 px-2 py-0.5 rounded-full mt-0.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" /> Processing
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 text-[var(--text-3)]">
                      <button className="p-1.5 hover:text-[var(--heading)] rounded hover:bg-[var(--surface-hover)] transition" title="View">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                          <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                        </svg>
                      </button>
                      <button className="p-1.5 hover:text-[var(--heading)] rounded hover:bg-[var(--surface-hover)] transition" title="Download">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                        </svg>
                      </button>
                      <button className="p-1.5 hover:text-[var(--heading)] rounded hover:bg-[var(--surface-hover)] transition" title="More">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </main>

        {/* Right Details Drawer */}
        <aside
          className="w-[380px] border-l border-[var(--border)] bg-[var(--surface)] flex flex-col justify-between overflow-y-auto shrink-0 select-none"
          data-purpose="history-detail-drawer"
        >
          <div className="p-4 space-y-4">
            {/* Drawer Header */}
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
              <span className="flex items-center gap-1.5 text-xs text-[var(--text-2)] font-medium">
                <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
                <span>Analysis Details</span>
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-[var(--green-bg)]/50 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> {selectedItem.status}
              </span>
            </div>

            {/* Large False-Color Map Preview Card */}
            <div className="relative h-44 rounded-xl border border-[var(--border)] hero-map-overlay overflow-hidden shadow-lg p-2.5 flex flex-col justify-between">
              <div className="flex justify-end">
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-900/80 text-blue-200 border border-blue-400/40 backdrop-blur-md">
                  {selectedItem.type}
                </span>
              </div>
              {/* Bottom Legend on Map */}
              <div className="bg-[var(--scrim)] backdrop-blur-md p-2 rounded-lg border border-[var(--border)] self-end space-y-1">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm bg-red-500" />
                  <span className="text-[10px] text-[var(--text)] font-medium">Built-up area</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
                  <span className="text-[10px] text-[var(--text)] font-medium">Vegetation</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
                  <span className="text-[10px] text-[var(--text)] font-medium">Water body</span>
                </div>
              </div>
            </div>

            {/* Details Info */}
            <div>
              <h2 className="text-base font-bold text-[var(--heading)]">{selectedItem.title}</h2>
              <div className="flex items-center gap-2 text-[11px] text-[var(--text-3)] mt-0.5">
                <span>{selectedItem.timestamp}</span>
              </div>
              <p className="text-xs text-[var(--text-2)] mt-2 leading-relaxed">{selectedItem.desc}</p>
              <div className="flex items-center gap-1.5 mt-2.5">
                {selectedItem.tags.map((tag) => (
                  <span key={tag} className="px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border)] text-[10px] text-[var(--text-2)]">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Results Summary */}
            <div className="pt-2 border-t border-[var(--border)]">
              <h4 className="text-xs font-semibold text-[var(--text-2)] mb-2.5">Results Summary</h4>
              <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative w-10 h-10 flex items-center justify-center">
                      <svg className="w-10 h-10 transform -rotate-90" viewBox="0 0 36 36">
                        <path
                          className="text-[var(--heading)]"
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3.5"
                        />
                        <path
                          className="text-[var(--cyan)]"
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="currentColor"
                          strokeDasharray={`${selectedItem.confidence}, 100`}
                          strokeLinecap="round"
                          strokeWidth="3.5"
                        />
                      </svg>
                      <span className="absolute text-[11px] font-bold text-[var(--heading)]">{selectedItem.confidence}%</span>
                    </div>
                    <span className="text-xs text-[var(--text-2)] font-medium">Confidence</span>
                  </div>
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-[var(--green-bg)]/50 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> {selectedItem.status}
                  </span>
                </div>

                {/* Stats Metric Cards */}
                <div className="grid grid-cols-3 gap-2 pt-1">
                  <div className="bg-[var(--surface-2)] border border-[var(--border)] p-2 rounded-lg text-center">
                    <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--text-3)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Built-up
                    </div>
                    <div className="text-xs font-bold text-red-400 mt-1">
                      {selectedItem.stats?.builtUp || "+12.4%"}
                    </div>
                  </div>
                  <div className="bg-[var(--surface-2)] border border-[var(--border)] p-2 rounded-lg text-center">
                    <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--text-3)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400" /> Water
                    </div>
                    <div className="text-xs font-bold text-blue-400 mt-1">
                      {selectedItem.stats?.water || "+5.1%"}
                    </div>
                  </div>
                  <div className="bg-[var(--surface-2)] border border-[var(--border)] p-2 rounded-lg text-center">
                    <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--text-3)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Vegetation
                    </div>
                    <div className="text-xs font-bold text-emerald-400 mt-1">
                      {selectedItem.stats?.vegetation || "-8.7%"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Input Images */}
            <div className="pt-2 border-t border-[var(--border)]">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-[var(--text-2)]">Input Images</h4>
                <Link href="/analysis" className="text-[11px] text-[var(--cyan)] hover:underline flex items-center gap-0.5">
                  <span>View Full Image</span>
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                </Link>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded-lg p-2">
                  <div className="h-16 rounded overflow-hidden thumb-forest relative border border-[var(--border)]/50" />
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] font-mono text-[var(--text-3)]">Optical (T1)</span>
                  </div>
                </div>
                <div className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded-lg p-2">
                  <div className="h-16 rounded overflow-hidden thumb-sar-1 relative border border-[var(--border)]/50" />
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] font-mono text-[var(--text-3)]">SAR (T2)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Model Details */}
            <div className="pt-2 border-t border-[var(--border)]">
              <div className="flex items-center justify-between py-1">
                <h4 className="text-xs font-semibold text-[var(--text-2)]">Model Details</h4>
                <svg className="w-4 h-4 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M5 15l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
              </div>
              <div className="space-y-1.5 text-xs mt-2 bg-[var(--surface)] p-2.5 rounded-lg border border-[var(--border)]">
                <div className="flex justify-between">
                  <span className="text-[var(--text-3)]">Task</span>
                  <span className="text-[var(--text)] font-medium">{selectedItem.type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-3)]">Model</span>
                  <span className="text-[var(--text)] font-medium">Remote Sensing VLM (BigEarthNet)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-3)]">Parameters</span>
                  <span className="text-[var(--text)] font-medium">Default (Auto)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons Footer */}
          <div className="p-4 border-t border-[var(--border)] space-y-2 bg-[var(--canvas)]">
            <Link
              href="/analysis"
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-[var(--cyan)] hover:bg-cyan-300 text-[var(--canvas)] font-semibold text-xs transition shadow-[0_0_15px_rgba(0,229,255,0.3)]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              <span>Open in New Analysis</span>
            </Link>
            <div className="flex items-center gap-2">
              <Link
                href="/reports"
                className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] text-[var(--text-2)] text-xs font-medium transition"
              >
                <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
                <span>Download Report</span>
              </Link>
              <button
                onClick={() => alert("Report settings")}
                className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] text-[var(--text-3)] hover:text-[var(--heading)] transition"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
                </svg>
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
