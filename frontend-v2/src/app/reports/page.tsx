"use client";

import { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

interface ReportItem {
  id: string;
  title: string;
  subtitle: string;
  type: string;
  region: string;
  date: string;
  time: string;
  status: "Completed" | "In Progress" | "Failed";
  imgUrl: string;
  urbanGrowth?: string;
  builtUpArea?: string;
  vegLoss?: string;
  roadGrowth?: string;
}

const REPORTS_DATA: ReportItem[] = [
  {
    id: "r1",
    title: "Urban Area Detection",
    subtitle: "Expansion analysis of Delhi region",
    type: "Optical + SAR",
    region: "Delhi, India",
    date: "Oct 12, 2025",
    time: "11:42 AM",
    status: "Completed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAVFqDueiUGcGN9EAGXeDgGM5-LpGP-9oOT4V28MecMFyWDANyI6VDAl-2bI9kXoFu4DzpJjMT4dC6iG2zCdVk4VcW4GRaStteBa4l8MOmPE0zXJPL8ijunqUTm_kZ4jyCjq3fo2zv9vAo78jY8yvtAGc3tUm8RM0-Mw0iTivC4d-m9KMGiNLb2d5pyJuHu7kMu6p_Gaz-aqFjbI1BhqjHobi0jAZT_i17WwimWklQy-Z9KbTYGstk",
    urbanGrowth: "+18.7%",
    builtUpArea: "12.4 km²",
    vegLoss: "-6.2%",
    roadGrowth: "+3.8%",
  },
  {
    id: "r2",
    title: "River Detection",
    subtitle: "VQA river identification",
    type: "Optical",
    region: "Sundarbans, India",
    date: "Oct 11, 2025",
    time: "04:21 PM",
    status: "Completed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBY-SSY1JxU3dcTxAnqXUCNPGHbUGv7pigKTBrNsKF7GWoRN-iLqDkPgXrFQhxnA9wvWfNuBEvrbw3sfrf08NLbsp7swyQKCIjIf7UROj-_znX2UV43EUf16tuAmDnVfjHXN9dNY1Tc23iInMWNLc2QjX72z9GFuElSGzDA9jQj5kyUw5VzPDqWWx-7Ja1UQVPdGU0lGInCSb1mfIwQswnqzzDmM2Wp8GlA9QoJX-CrndfWVMRYtoh1e5z9kvHKTI3p",
    urbanGrowth: "+1.2%",
    builtUpArea: "0.8 km²",
    vegLoss: "-0.5%",
    roadGrowth: "0.0%",
  },
  {
    id: "r3",
    title: "Forest Cover Monitoring",
    subtitle: "Deforestation tracking",
    type: "Multispectral",
    region: "Amazon, Brazil",
    date: "Oct 08, 2025",
    time: "02:15 PM",
    status: "Completed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAGbD0Frbs3Qt7sz6ESmQlFEsyCNM_f_gro_vHkQYKjiIL3dsbb6-gjgsly7Dn_krZneXIEZj8F0SWMkiP7_4kRg0nxMa8mZCaodUhb7JA_4yaKmYbPATUnGyehZstaPCGoPJnLsPMidpDc-lKo4gr6_Pmz9h8WJ9pL57hTY7YFW7LOgF14nKhuQg1uxPW3MsfwCjGcjbE9SQbSRvMXqGA60Pk2l5xrnF-6zdEhiCVMmua_6_AplANmWWZIuOxA555E",
    urbanGrowth: "+0.4%",
    builtUpArea: "3.2 km²",
    vegLoss: "-14.8%",
    roadGrowth: "+2.1%",
  },
  {
    id: "r4",
    title: "SAR Flood Mapping",
    subtitle: "Disaster response flood extent",
    type: "SAR",
    region: "Assam, India",
    date: "Oct 07, 2025",
    time: "09:30 AM",
    status: "In Progress",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAyXwBIkCAFP5wB6DbnmxWjG7ZrADP3kztslmRY1KkfBHUPpGWFSHcgYJ6_-3aE3cRsykFRn6B0cJ6wuWwwcZs9T16B8WOHE_SyegEK6eqtluBJJe0vOf42OU8wTaljsKD7ZRfqe47TByWsSMWlwJwqXeel_3YnVm8o-seY6njTnyG_WkJJ3NrzVdEJRuOOIbHvtWHe8o-35GPzzzZDDER7vuvsckfjCvt0DYUYan1XyNrYTYjNSh48j0nbNA1LCEwT",
    urbanGrowth: "-4.2%",
    builtUpArea: "0.0 km²",
    vegLoss: "-8.1%",
    roadGrowth: "-1.5%",
  },
  {
    id: "r5",
    title: "Coastal Erosion Tracking",
    subtitle: "Multi-year shoreline change",
    type: "Bi-temporal",
    region: "Odisha, India",
    date: "Oct 05, 2025",
    time: "01:18 PM",
    status: "Completed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBCvypqnqZJ-db5MobrkTSa0_FeceGsxCfC9A94wSNF7vpjmcn-iMSYceb5YTVXLJmTqcQxhMAnybhvVuRwhF5jUXg03XN9e8f8InYIeeqVKzU1RJrWIAUJ4jyJ8STymymaPUsKv1IYj7-jnUn0Vv1lIEbqySVJ44NxH5VbRAfbTIDKOkEdbwSIguB_XQ5qbIwo98xdWy6iMYET9FLhtGCyGHp4-MNgk8sJAr47bC8JIp88xCbV_z0",
    urbanGrowth: "+2.1%",
    builtUpArea: "1.4 km²",
    vegLoss: "-3.4%",
    roadGrowth: "+0.8%",
  },
  {
    id: "r6",
    title: "Agricultural Crop Health",
    subtitle: "NDVI vegetation analysis",
    type: "Multispectral",
    region: "Punjab, India",
    date: "Oct 03, 2025",
    time: "11:05 AM",
    status: "Completed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuDKIRiHnITIQ7x_KqxlLXRc7Lkse3FAAyyOixrgd4MExlWH2gJpOTRvi16JdlPaDsqx3ImZ4O9XZhQUzVALbBfhVkZarAhqDUJ__tbXM_dOGop4mpwzTWxtJ-Gq326fX9PuDKefCU4OBwT26HcZWBqT5Yt_asLZkHhtzZ3g1P0EyoTTjybhWVbeMppEZEcOzDVyiZ8OGu3YuwvOEHxS_CbmLcEwGwgSTQtpwXkeEbNataoAmHfSHDE",
    urbanGrowth: "+0.2%",
    builtUpArea: "0.5 km²",
    vegLoss: "+6.8%",
    roadGrowth: "+0.3%",
  },
  {
    id: "r7",
    title: "Drought Severity Assessment",
    subtitle: "Soil moisture anomaly",
    type: "Optical + SAR",
    region: "Rajasthan, India",
    date: "Sep 30, 2025",
    time: "10:14 AM",
    status: "In Progress",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAN0v0RhlwoMFsAuso5rJgyMSAci3SzBCDNIH0tT6A2wQ8UhglSVSA34j_TTfsPkI0K4HNYiSaWUErQ29QgBcdMjRx4VTyBq-ZWMkhVX9mCNYDGlJG8JSS_v4bnQSMrA_43NxtiLFqwtlGNOTTT59vilh86HNfE-T-hLd9Wy5nWgQg4wTMcMEvEzL_7ifpiCy5hCyaH5GpZ_FwhMCmKqsjUtvIoUm4K4du-FMBJF6VjNK9Lu2Xdn5-8oeJsG55rDI0X",
    urbanGrowth: "0.0%",
    builtUpArea: "0.0 km²",
    vegLoss: "-19.2%",
    roadGrowth: "0.0%",
  },
  {
    id: "r8",
    title: "Infrastructure Mapping",
    subtitle: "Roads and buildings extraction",
    type: "Optical",
    region: "Chennai, India",
    date: "Sep 28, 2025",
    time: "03:22 PM",
    status: "Failed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuCajw9fX8Wx6Z0n_vCBkpTjRF4nfvrYakrg-di47gNRn1PnnfeDGm3gHJ2Rj4Dyqg-ZiU2hdsE9oJHQ1g5Pxq9B504xPd8d6SSXLdY04hyBToaLrY2bnvwFTAwNIiF4BnD9zcnJrAMQH0sGNvHAHlkWhKuuIbO66dMDdYrMlb6At8RyPJZzq9HwR22VdBua5nTPRKR83EFQRs6r9je1HKYLzrmmFjPQUpZBa8e3FW9dDJIDGLNlIJ0",
    urbanGrowth: "N/A",
    builtUpArea: "N/A",
    vegLoss: "N/A",
    roadGrowth: "N/A",
  },
  {
    id: "r9",
    title: "Bi-temporal Change Detection",
    subtitle: "Pre & post event analysis",
    type: "Change Analysis",
    region: "Sundarbans, India",
    date: "Sep 26, 2025",
    time: "05:41 PM",
    status: "Completed",
    imgUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBCvypqnqZJ-db5MobrkTSa0_FeceGsxCfC9A94wSNF7vpjmcn-iMSYceb5YTVXLJmTqcQxhMAnybhvVuRwhF5jUXg03XN9e8f8InYIeeqVKzU1RJrWIAUJ4jyJ8STymymaPUsKv1IYj7-jnUn0Vv1lIEbqySVJ44NxH5VbRAfbTIDKOkEdbwSIguB_XQ5qbIwo98xdWy6iMYET9FLhtGCyGHp4-MNgk8sJAr47bC8JIp88xCbV_z0",
    urbanGrowth: "+3.4%",
    builtUpArea: "2.1 km²",
    vegLoss: "-7.9%",
    roadGrowth: "+1.2%",
  },
];

export default function ReportsPage() {
  const [selectedTab, setSelectedTab] = useState<string>("All Reports");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string>("r1");
  const [sliderPos, setSliderPos] = useState<number>(50);

  const selectedReport = REPORTS_DATA.find((r) => r.id === selectedId) || REPORTS_DATA[0];

  const filteredReports = REPORTS_DATA.filter((item) => {
    const matchesTab =
      selectedTab === "All Reports" ||
      (selectedTab === "Completed" && item.status === "Completed") ||
      (selectedTab === "In Progress" && item.status === "In Progress") ||
      (selectedTab === "Failed" && item.status === "Failed");
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.region.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  return (
    <div className="bg-[var(--canvas)] text-[var(--text)] antialiased font-sans h-screen overflow-hidden flex flex-col selection:bg-cyan-500 selection:text-[var(--canvas)]">
      {/* Top Header */}
      <TopBar
        showBrand={true}
        searchPlaceholder="Search reports, locations, or keywords..."
        onSearch={(q) => setSearchQuery(q)}
      />

      {/* Main Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar hideBrand={true} activeItem="reports" className="h-full" />

        {/* Center Main Section: Reports Management */}
        <main className="flex-1 overflow-y-auto p-6 space-y-5 bg-[var(--canvas)]" data-purpose="reports-management-section">
          {/* Reports Page Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-cyan-950/60 border border-[var(--cyan)]/30 flex items-center justify-center text-[var(--cyan)] mt-0.5 shadow-[0_0_15px_rgba(6,182,212,0.15)]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-[var(--heading)] tracking-tight">Reports</h1>
                <p className="text-xs text-[var(--text-3)] mt-0.5">
                  View, manage and download your analysis reports. Each report includes detailed insights, visualizations and export options.
                </p>
              </div>
            </div>

            {/* Generate Report Button */}
            <Link
              href="/analysis?action=generate-report"
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 text-[var(--heading)] font-medium text-xs shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Generate Report</span>
            </Link>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2 border-b border-[var(--border)] pb-3 text-xs font-semibold">
            {[
              { label: "All Reports", count: 24 },
              { label: "Completed", count: 18 },
              { label: "In Progress", count: 4 },
              { label: "Failed", count: 2 },
            ].map((tab) => {
              const active = selectedTab === tab.label;
              return (
                <button
                  key={tab.label}
                  onClick={() => setSelectedTab(tab.label)}
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-2 transition cursor-pointer ${
                    active
                      ? "bg-cyan-950/70 border border-[var(--cyan)]/40 text-[var(--cyan)] shadow-sm"
                      : "text-[var(--text-3)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)]"
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                      active ? "bg-cyan-500/20 text-[var(--cyan)]" : "bg-[var(--surface-hover)] text-[var(--text-3)]"
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Search and Filter Bar Row */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="relative flex-1 min-w-[200px]">
              <svg className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" x2="16.65" y1="21" y2="16.65" />
              </svg>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-xl pl-9 pr-3 py-1.5 text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--cyan)]/40"
                placeholder="Search reports..."
                type="text"
              />
            </div>

            <select className="bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] text-xs rounded-xl py-1.5 px-3 focus:outline-none focus:border-[var(--cyan)]/40 cursor-pointer">
              <option>All Regions</option>
              <option>Asia</option>
              <option>South America</option>
              <option>Europe</option>
            </select>

            <select className="bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] text-xs rounded-xl py-1.5 px-3 focus:outline-none focus:border-[var(--cyan)]/40 cursor-pointer">
              <option>All Types</option>
              <option>Change Analysis</option>
              <option>Optical + SAR</option>
              <option>VQA</option>
              <option>SAR</option>
            </select>

            <select className="bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] text-xs rounded-xl py-1.5 px-3 focus:outline-none focus:border-[var(--cyan)]/40 cursor-pointer">
              <option>Last 30 days</option>
              <option>Last 7 days</option>
              <option>Last 90 days</option>
              <option>Year to date</option>
            </select>
          </div>

          {/* Reports Table */}
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[10px] font-semibold text-[var(--text-3)] uppercase tracking-wider bg-[var(--surface)]/50">
                    <th className="py-3 px-4">Report Name</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Region</th>
                    <th className="py-3 px-3">Generated</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#121f36] text-xs font-normal">
                  {filteredReports.map((report) => {
                    const isSelected = selectedId === report.id;
                    return (
                      <tr
                        key={report.id}
                        onClick={() => setSelectedId(report.id)}
                        className={`hover:bg-[var(--surface-hover)]/50 transition-colors cursor-pointer ${
                          isSelected ? "bg-cyan-950/20 border-l-2 border-[var(--cyan)]" : ""
                        }`}
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg overflow-hidden shrink-0 border border-[var(--border)] bg-[var(--surface-3)]">
                              <img alt={report.title} className="w-full h-full object-cover" src={report.imgUrl} />
                            </div>
                            <div>
                              <div className="font-semibold text-[var(--heading)] text-xs hover:text-[var(--cyan)]">{report.title}</div>
                              <div className="text-[11px] text-[var(--text-3)]">{report.subtitle}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-950/70 text-blue-300 border border-blue-800/40">
                            {report.type}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-[var(--text-2)] whitespace-nowrap">{report.region}</td>
                        <td className="py-3 px-3 text-[var(--text-3)] whitespace-nowrap">
                          <div className="text-[var(--text-2)] font-medium">{report.date}</div>
                          <div className="text-[10px] text-[var(--text-3)]">{report.time}</div>
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          {report.status === "Completed" && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-[var(--green-bg)]/60 text-emerald-400 border border-emerald-800/40">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Completed
                            </span>
                          )}
                          {report.status === "In Progress" && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-950/60 text-amber-400 border border-amber-800/40">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" /> In Progress
                            </span>
                          )}
                          {report.status === "Failed" && (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-rose-950/60 text-rose-400 border border-rose-800/40">
                              <span className="w-1.5 h-1.5 rounded-full bg-[var(--error)]" /> Failed
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1 text-[var(--text-3)]">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                alert(`Downloading ${report.title}`);
                              }}
                              className="p-1.5 hover:text-[var(--cyan)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors"
                              title="Download"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            </button>
                            <button
                              onClick={(e) => e.stopPropagation()}
                              className="p-1.5 hover:text-[var(--text)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="1" /><circle cx="12" cy="5" r="1" /><circle cx="12" cy="19" r="1" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Bar */}
          <div className="flex items-center justify-between text-xs text-[var(--text-3)] pt-1">
            <div>Showing <span className="text-[var(--text)] font-medium">1 - {filteredReports.length}</span> of <span className="text-[var(--text)] font-medium">24</span> reports</div>
            <div className="flex items-center gap-1.5">
              <button className="p-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--surface-hover)] text-[var(--text-3)] disabled:opacity-40" disabled>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </button>
              <button className="w-7 h-7 rounded-lg bg-[var(--cyan)] text-[var(--heading)] font-semibold flex items-center justify-center text-xs shadow-sm">1</button>
              <button className="w-7 h-7 rounded-lg border border-[var(--border)] hover:bg-[var(--surface-hover)] text-[var(--text-2)] flex items-center justify-center text-xs transition-colors">2</button>
              <button className="w-7 h-7 rounded-lg border border-[var(--border)] hover:bg-[var(--surface-hover)] text-[var(--text-2)] flex items-center justify-center text-xs transition-colors">3</button>
              <button className="p-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--surface-hover)] text-[var(--text-2)] transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>
          </div>
        </main>

        {/* Right Details Drawer */}
        <aside
          className="w-96 shrink-0 border-l border-[var(--border)] bg-[var(--surface)] overflow-y-auto p-5 flex flex-col space-y-5 select-none"
          data-purpose="report-details-drawer"
        >
          {/* Header */}
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-[var(--text-3)] font-medium">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <line x1="19" x2="5" y1="12" y2="12" /><polyline points="12 19 5 12 12 5" />
              </svg>
              <span>Report Details</span>
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-[var(--green-bg)]/70 text-emerald-400 border border-emerald-800/40">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              {selectedReport.status}
            </span>
          </div>

          {/* Title & Subtitle */}
          <div>
            <h2 className="text-base font-bold text-[var(--heading)] tracking-tight">{selectedReport.title}</h2>
            <p className="text-xs text-[var(--text-3)] mt-0.5">{selectedReport.subtitle}</p>
          </div>

          {/* Meta tags row */}
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-2)]">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
              <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect height="18" rx="2" ry="2" width="18" x="3" y="4" />
                <line x1="16" x2="16" y1="2" y2="6" /><line x1="8" x2="8" y1="2" y2="6" />
                <line x1="3" x2="21" y1="10" y2="10" />
              </svg>
              <span>{selectedReport.date} {selectedReport.time}</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
              <svg className="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 21s-6-5.33-6-10a6 6 0 0112 0c0 4.67-6 10-6 10z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>{selectedReport.region}</span>
            </div>
            <span className="px-2.5 py-1 rounded-lg bg-purple-950/60 text-purple-300 border border-purple-800/40 font-medium">
              {selectedReport.type}
            </span>
          </div>

          {/* Split Comparison Satellite Image Viewer */}
          <div
            className="relative w-full h-44 rounded-xl overflow-hidden border border-[var(--border)] shadow-md group cursor-ew-resize select-none"
            data-purpose="satellite-comparison-viewer"
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const x = e.clientX - rect.left;
              const pct = Math.max(10, Math.min(90, (x / rect.width) * 100));
              setSliderPos(pct);
            }}
          >
            {/* Left / Before Image */}
            <div className="absolute inset-0 w-full h-full">
              <img
                alt="Satellite Before"
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAVFqDueiUGcGN9EAGXeDgGM5-LpGP-9oOT4V28MecMFyWDANyI6VDAl-2bI9kXoFu4DzpJjMT4dC6iG2zCdVk4VcW4GRaStteBa4l8MOmPE0zXJPL8ijunqUTm_kZ4jyCjq3fo2zv9vAo78jY8yvtAGc3tUm8RM0-Mw0iTivC4d-m9KMGiNLb2d5pyJuHu7kMu6p_Gaz-aqFjbI1BhqjHobi0jAZT_i17WwimWklQy-Z9KbTYGstk"
              />
            </div>

            {/* Right / After Image with Red Overlay */}
            <div
              className="absolute inset-0 h-full overflow-hidden"
              style={{ left: `${sliderPos}%`, width: `${100 - sliderPos}%` }}
            >
              <div className="w-full h-full relative" style={{ width: `${(100 / (100 - sliderPos)) * 100}%`, marginLeft: `-${(sliderPos / (100 - sliderPos)) * 100}%` }}>
                <img
                  alt="Satellite After"
                  className="w-full h-full object-cover filter contrast-125"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuD1SfN3D-KVs6s3id6ym7yrANCo8Vieu9A2flB2WK4rLK8aY5nhxLR1OCdE_2ml20WJv5rUF8ofeH7WEeU_MJwbHtVDFWzhsydzeaZNr9IjLaHHvb95QgrdnC3N9fAVidEV0MB0aq1KcNNbTNEdzqqaVM-0qiMFIUzJ1ZdJVyWwSD2Ot_4-vr4ahzlhINu7ggfqXMw-v1WfehdFnmj4qEZaB8ouz2Bzo8uxHxNPG8j_iqxla3VrHsU"
                />
                <div className="absolute inset-0 bg-red-600/40 mix-blend-color-dodge" />
              </div>
            </div>

            {/* Vertical Divider Slider with Drag Handle */}
            <div
              className="absolute top-0 bottom-0 -ml-[1px] w-[2px] bg-[var(--cyan)] shadow-[0_0_10px_#00e5ff] flex items-center justify-center pointer-events-none"
              style={{ left: `${sliderPos}%` }}
            >
              <div className="w-6 h-6 rounded-full bg-[var(--surface)] border-2 border-[var(--cyan)] text-[var(--cyan)] flex items-center justify-center shadow-lg">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <polyline points="8 15 5 12 8 9" />
                  <polyline points="16 9 19 12 16 15" />
                </svg>
              </div>
            </div>

            {/* Corner Labels */}
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] text-[var(--heading)] font-medium border border-[var(--border)]">
              Before (2022)
            </div>
            <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-[var(--scrim)] backdrop-blur text-[10px] text-[var(--heading)] font-medium border border-[var(--border)]">
              After (2025)
            </div>
          </div>

          {/* Key Findings Section */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Key Findings</span>
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                <div className="flex items-center gap-1.5 text-[var(--cyan)] mb-1">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="text-sm font-bold text-[var(--heading)]">{selectedReport.urbanGrowth || "+18.7%"}</span>
                </div>
                <p className="text-[10px] text-[var(--text-3)] leading-tight">Urban expansion in target area</p>
              </div>

              <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                <div className="flex items-center gap-1.5 text-[var(--cyan)] mb-1">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <rect height="20" rx="2" ry="2" width="16" x="4" y="2" />
                    <line x1="9" x2="9" y1="6" y2="6.01" /><line x1="15" x2="15" y1="6" y2="6.01" />
                    <line x1="9" x2="9" y1="12" y2="12.01" /><line x1="15" x2="15" y1="12" y2="12.01" />
                  </svg>
                  <span className="text-sm font-bold text-[var(--heading)]">{selectedReport.builtUpArea || "12.4 km²"}</span>
                </div>
                <p className="text-[10px] text-[var(--text-3)] leading-tight">New built-up area</p>
              </div>

              <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                <div className="flex items-center gap-1.5 text-emerald-400 mb-1">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v8m-4-4h8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="text-sm font-bold text-[var(--heading)]">{selectedReport.vegLoss || "-6.2%"}</span>
                </div>
                <p className="text-[10px] text-[var(--text-3)] leading-tight">Vegetation loss</p>
              </div>

              <div className="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
                <div className="flex items-center gap-1.5 text-[var(--cyan)] mb-1">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="text-sm font-bold text-[var(--heading)]">{selectedReport.roadGrowth || "+3.8%"}</span>
                </div>
                <p className="text-[10px] text-[var(--text-3)] leading-tight">Road network expansion</p>
              </div>
            </div>
          </div>

          {/* Insights Section */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Insights</span>
            </h3>
            <ul className="space-y-2 text-[11px] text-[var(--text-2)]">
              <li className="flex items-start gap-2">
                <span className="w-1 h-1 rounded-full bg-[var(--cyan)] mt-1.5 shrink-0" />
                <span>Significant urban growth detected in the eastern and southern sectors of the AOI.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1 h-1 rounded-full bg-[var(--cyan)] mt-1.5 shrink-0" />
                <span>New infrastructure and arterial transport networks are visible in the expanded footprint.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1 h-1 rounded-full bg-[var(--cyan)] mt-1.5 shrink-0" />
                <span>Vegetation conversion is concentrated primarily around newly mapped civil zones.</span>
              </li>
            </ul>
          </div>

          {/* Download CTA Buttons */}
          <div>
            <div className="text-[11px] font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Download Report</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => alert(`Downloading full PDF report for ${selectedReport.title}`)}
                className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-[var(--canvas)] font-bold text-xs flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Download Full Report (PDF)</span>
              </button>
              <button
                onClick={() => alert("Report link copied to clipboard")}
                className="p-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-2)] hover:text-[var(--heading)] hover:border-[var(--border-strong)] transition-colors"
                title="Share or Copy Link"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>

          {/* Related Files Section */}
          <div>
            <div className="text-[11px] font-semibold text-[var(--text-2)] uppercase tracking-wider mb-2">Related Files</div>
            <div className="space-y-1.5">
              {[
                { name: "analysis_visualization.png", size: "2.4 MB" },
                { name: "change_mask.geojson", size: "1.2 MB" },
                { name: "metadata.json", size: "450 KB" },
              ].map((file) => (
                <div
                  key={file.name}
                  className="flex items-center justify-between p-2 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <svg className="w-4 h-4 text-[var(--cyan)] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <rect height="18" rx="2" ry="2" width="18" x="3" y="3" />
                      <circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />
                    </svg>
                    <span className="text-xs text-[var(--text-2)] truncate font-mono">{file.name}</span>
                  </div>
                  <div className="flex items-center gap-2 pl-2 shrink-0">
                    <span className="text-[10px] text-[var(--text-3)]">{file.size}</span>
                    <button
                      onClick={() => alert(`Downloading ${file.name}`)}
                      className="p-1 text-[var(--text-3)] hover:text-[var(--cyan)] transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
