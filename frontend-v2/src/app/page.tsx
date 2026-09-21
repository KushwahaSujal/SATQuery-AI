"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useInView } from "framer-motion";
import { api } from "@/lib/api";
import { useJobs } from "@/hooks/useJobs";
import { useAnalysisStore } from "@/stores/useAnalysisStore";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { NumberTicker } from "@/components/ui/number-ticker";

// ─── Animation Variants ──────────────────────────────────────────────────────
const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};
const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};
const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  show: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

// ─── Stats Data ───────────────────────────────────────────────────────────────
const stats = [
  { value: 98, suffix: "%", label: "Detection Accuracy" },
  { value: 12, suffix: "x", label: "Faster Than Manual" },
  { value: 2500, suffix: "+", label: "Analyses Run" },
  { value: 47, suffix: "", label: "Data Sources" },
];

// ─── Feature Cards Data ───────────────────────────────────────────────────────
const features = [
  {
    id: "vqa",
    href: "/analysis?tool=vqa",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "Single Image Analysis",
    desc: "Ask questions, get scene descriptions, localize objects, and extract region insights from a single satellite frame.",
    tags: ["VQA", "Captioning", "Grounding"],
    accent: "from-teal-500/20 to-cyan-500/10",
    border: "hover:border-teal-500/50",
    glow: "rgba(0, 213, 190, 0.08)",
    imgClass: "sat-crop-delhi-main",
  },
  {
    id: "fusion",
    href: "/analysis?tool=fusion",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <polygon points="12 2 2 7 12 12 22 7 12 2" />
        <polyline points="2 17 12 22 22 17" />
        <polyline points="2 12 12 17 22 12" />
      </svg>
    ),
    title: "Optical + SAR Fusion",
    desc: "Combine multi-spectral optical data with radar imagery for all-weather, all-condition intelligence extraction.",
    tags: ["Cross-Modal", "Multi-Sensor", "Fusion"],
    accent: "from-violet-500/20 to-blue-500/10",
    border: "hover:border-violet-500/50",
    glow: "rgba(121, 87, 255, 0.08)",
    imgClass: "sat-crop-sar",
  },
  {
    id: "change",
    href: "/analysis?tool=change",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "Bi-temporal Change",
    desc: "Detect, measure, and interpret land surface changes over time with AI-powered difference analysis.",
    tags: ["Change Detection", "Change VQA", "Temporal"],
    accent: "from-amber-500/20 to-orange-500/10",
    border: "hover:border-[var(--amber)]/50",
    glow: "rgba(245, 166, 35, 0.08)",
    imgClass: "sat-crop-river",
  },
  {
    id: "agentic",
    href: "/analysis",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3m0 14v3M2 12h3m14 0h3m-3.2-6.8-2.1 2.1M7.3 16.7l-2.1 2.1M18.8 18.8l-2.1-2.1M7.3 7.3 5.2 5.2" strokeLinecap="round" />
      </svg>
    ),
    title: "Agentic Orchestration",
    desc: "Let the AI automatically select the right models, validate inputs, chain steps, and return structured evidence.",
    tags: ["Smart Routing", "Multi-Step", "Evidence"],
    accent: "from-emerald-500/20 to-teal-500/10",
    border: "hover:border-[var(--green)]/50",
    glow: "rgba(40, 201, 138, 0.08)",
    imgClass: "sat-crop-urban",
  },
];

// ─── Recent Analyses (fetched from backend) ──────────────────────────────────
const THUMB_CLASSES = ["sat-crop-urban", "sat-crop-river", "sat-crop-sar", "sat-crop-amazon"];
const TASK_TAGS: Record<string, string> = {
  bi_temporal_change: "Change Detection",
  bi_temporal_change_vqa: "Change VQA",
  single_image_vqa: "VQA",
  single_image_grounding: "Grounding",
  single_image_caption: "Captioning",
  video_grounding_tracking: "Video",
  optical_sar_analysis: "Cross-Modal",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return "";
  }
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const handleUpload = useAnalysisStore((s) => s.handleUpload);
  const uploadProgress = useAnalysisStore((s) => s.uploadProgress);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const statsRef = useRef(null);
  const statsInView = useInView(statsRef, { once: true, margin: "-80px" });

  const { data: jobs } = useJobs();

  const recentAnalyses = (jobs ?? []).slice(0, 4).map((j: Record<string, unknown>, i: number) => ({
    title: (j.query as string)?.slice(0, 50) || "Analysis",
    tag: TASK_TAGS[(j.task as string) || ""] || (j.task as string) || "Analysis",
    meta: `${formatDate((j.created_at as string) || new Date().toISOString())}`,
    imgClass: THUMB_CLASSES[i % THUMB_CLASSES.length],
    job_id: (j.job_id || j.id) as string,
    status: (j.status as string) || "COMPLETED",
  }));

  async function handleUploadFiles(files: FileList | File[]) {
    setIsUploading(true);
    setUploadError(null);
    // Upload through the shared store rather than calling api.uploadRasters directly.
    // The old code uploaded the files and then threw the response away, so /analysis
    // opened with an empty workspace and the same file had to be picked a second time.
    // The store is a module singleton, so what it holds survives the client-side
    // navigation below. It also accepts video, which api.uploadRasters does not.
    const ok = await handleUpload(Array.from(files));
    setIsUploading(false);
    if (ok) {
      router.push(query.trim() ? `/analysis?q=${encodeURIComponent(query.trim())}` : "/analysis");
    } else {
      setUploadError(useAnalysisStore.getState().uploadError ?? "Upload failed");
    }
  }

  const handleQuerySubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSubmitting(true);
    if (query.trim()) {
      router.push(`/analysis?q=${encodeURIComponent(query.trim())}`);
    } else {
      router.push("/analysis");
    }
  };

  const handleQuickPrompt = (promptText: string) => {
    setQuery(promptText);
    setIsSubmitting(true);
    router.push(`/analysis?q=${encodeURIComponent(promptText)}`);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.length > 0) handleUploadFiles(e.dataTransfer.files);
  };

return (
    <>
      {/* Background Video */}
      <div
        className="fixed inset-0 top-0 -z-10 overflow-hidden pointer-events-none"
      >
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover"
          src="/4788-180289892.mp4"
        />
        <div
          className="absolute inset-0 bg-[rgba(2,13,25,0.6)] backdrop-blur-md"
        />
      </div>

      <div className="bg-[var(--canvas)] text-[var(--text)] font-sans min-h-screen flex antialiased">
        <Sidebar activeItem="home" hideBrand={false} className="sticky top-0 h-screen flex-shrink-0" />

        <main className="flex-1 flex flex-col min-w-0 bg-[var(--canvas)] relative">
          <TopBar
            showBrand={false}
            searchPlaceholder='Search anything… e.g. "urban expansion in Delhi"'
            onSearch={(val) => { if (val) router.push(`/analysis?q=${encodeURIComponent(val)}`); }}
          />

          {/* ── HERO: TASKING CONSOLE ────────────────────────────────────── */}
          <section className="relative px-6 md:px-10 pt-12 pb-16 overflow-hidden border-b border-[var(--border)]">
            {/* Grid-line texture, faded at the edges */}
            <div
              aria-hidden
              className="absolute inset-0 pointer-events-none opacity-20"
              style={{
                backgroundImage:
                  "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
                backgroundSize: "56px 56px",
                maskImage: "radial-gradient(ellipse 90% 85% at 35% 15%, black 25%, transparent 78%)",
                WebkitMaskImage: "radial-gradient(ellipse 90% 85% at 35% 15%, black 25%, transparent 78%)",
              }}
            />

            <div className="relative z-10 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
              {/* Left: headline + tasking console */}
              <motion.div variants={stagger} initial="hidden" animate="show" className="lg:col-span-7">
                {/* Category tag */}
                <motion.div variants={fadeUp} className="flex items-center gap-3 mb-6">
                  <span className="w-1.5 h-1.5 bg-[var(--accent)]" />
                  <span className="font-mono-data text-[10px] font-medium tracking-[0.18em] uppercase text-[var(--text-3)]">
                    SatQuery · Geospatial Analysis Console
                  </span>
                  <span className="flex-1 border-t border-[var(--border)]" />
                </motion.div>

                {/* H1 */}
                <motion.h1
                  variants={fadeUp}
                  className="text-[2.5rem] sm:text-5xl font-extrabold text-[var(--heading)] tracking-tight leading-[1.06] mb-5"
                >
                  Analyze Earth imagery
                  <br />
                  <span className="text-[var(--accent)]">with natural language.</span>
                </motion.h1>

                <motion.p variants={fadeUp} className="text-[var(--text-2)] text-sm leading-relaxed mb-8 max-w-md">
                  Ask questions. Compare scenes. Measure change. Satellite AI that answers in plain English, no code required.
                </motion.p>

                {/* Tasking console */}
                <motion.div variants={fadeUp} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
                  {/* Console header */}
                  <div className="panel-header">
                    <span className="panel-label">New analysis</span>
                    <span className={`font-mono-data text-[10px] tracking-[0.14em] uppercase ${isUploading || isSubmitting ? "text-[var(--warning)]" : "text-[var(--accent)]"}`}>
                      {isUploading ? "Receiving imagery" : isSubmitting ? "Routing query" : "Ready"}
                    </span>
                  </div>

                  {/* 01 · Imagery */}
                  <div className="px-4 pt-3 pb-4 border-b border-[var(--border)]">
                    <p className="font-mono-data text-[9px] tracking-[0.18em] uppercase text-[var(--text-4)] mb-2">01 · Imagery input</p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".tif,.tiff,.png,.jpg,.jpeg,.geojson"
                      className="hidden"
                      disabled={isUploading || isSubmitting}
                      onChange={(e) => { if (e.target.files?.length) handleUploadFiles(e.target.files) }}
                    />
                    <div
                      onClick={() => !isUploading && !isSubmitting && fileInputRef.current?.click()}
                      onDragOver={(e) => { e.preventDefault(); if (!isUploading) setDragActive(true); }}
                      onDragLeave={() => setDragActive(false)}
                      onDrop={handleFileDrop}
                      className={`group flex items-center justify-between gap-3 w-full border border-dashed rounded-lg px-4 py-3.5 transition-colors duration-150 ${
                        isUploading || isSubmitting
                          ? "cursor-not-allowed opacity-60"
                          : "cursor-pointer"
                      } ${dragActive ? "border-[var(--accent)] bg-[var(--accent)]/5" : "border-[var(--border-strong)] hover:border-[var(--accent)]/50 hover:bg-[var(--surface-2)]"}`}
                    >
                      {isUploading ? (
                        <div className="flex items-center gap-2.5 text-xs font-medium text-[var(--heading)]">
                          <svg className="w-4 h-4 text-[var(--accent)] animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          <span>Processing imagery…</span>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-3 min-w-0">
                            <svg className="w-4 h-4 text-[var(--accent)] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-[var(--heading)]">Drop satellite imagery to upload</p>
                              <p className="font-mono-data text-[9px] tracking-[0.14em] text-[var(--text-3)] mt-0.5">GEOTIFF · TIFF · PNG · JPEG · GEOJSON</p>
                            </div>
                          </div>
                          <span className="shrink-0 font-mono-data text-[10px] tracking-[0.12em] uppercase text-[var(--text-2)] border border-[var(--border-strong)] rounded-md px-2.5 py-1.5 group-hover:border-[var(--accent)]/50 group-hover:text-[var(--accent)] transition-colors">
                            Browse
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* 02 · Query */}
                  <div className="px-4 pt-3 pb-4">
                    <p className="font-mono-data text-[9px] tracking-[0.18em] uppercase text-[var(--text-4)] mb-2">02 · Natural language query</p>
                    <form onSubmit={handleQuerySubmit} className="flex items-center gap-2">
                      <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        disabled={isUploading || isSubmitting}
                        className="flex-1 min-w-0 bg-[var(--canvas)] border border-[var(--border-strong)] rounded-lg px-3.5 py-2.5 text-sm text-[var(--heading)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--accent)]/60 focus:ring-1 focus:ring-[var(--accent)]/15 transition-all disabled:opacity-50"
                        placeholder="Ask a question about your imagery…"
                      />
                      <button
                        type="submit"
                        disabled={isUploading || isSubmitting || !query.trim()}
                        className="h-[38px] px-4 rounded-lg bg-[var(--accent)] text-[var(--canvas)] font-mono-data text-[11px] font-bold tracking-[0.1em] uppercase hover:brightness-110 transition-all shrink-0 flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {isSubmitting ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                        ) : (
                          <>
                            Run
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                              <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </>
                        )}
                      </button>
                    </form>
                  </div>
                </motion.div>

                {uploadError && (
                  <motion.div variants={fadeUp} className="mt-3 px-3 py-2.5 rounded-lg border border-[var(--error)]/40 bg-[var(--error-bg)] text-[var(--error)] text-xs flex items-start gap-2">
                    <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span>{uploadError}</span>
                  </motion.div>
                )}

                {/* Sample queries: list rows */}
                <motion.div variants={fadeUp} className="mt-7">
                  <p className="font-mono-data text-[9px] tracking-[0.18em] uppercase text-[var(--text-4)] mb-1.5">Sample queries</p>
                  <div className="border-t border-[var(--border)]">
                    {[
                      "Describe this scene",
                      "Highlight the water body",
                      "What changed between these dates?",
                      "Optical + SAR analysis",
                    ].map((p, i) => (
                      <button
                        key={p}
                        onClick={() => handleQuickPrompt(p)}
                        className="group flex w-full items-center gap-3 px-1 py-2.5 border-b border-[var(--border)] text-left transition-colors hover:bg-[var(--surface-2)]/60"
                      >
                        <span className="font-mono-data text-[9px] text-[var(--text-4)] w-5 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                        <span className="flex-1 text-xs text-[var(--text-2)] group-hover:text-[var(--heading)] transition-colors">{p}</span>
                        <svg className="w-3.5 h-3.5 text-[var(--text-4)] opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 group-hover:text-[var(--accent)] transition-all" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                    ))}
                  </div>
                </motion.div>
              </motion.div>

              {/* Right: scene viewport */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.55, delay: 0.15, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
                className="lg:col-span-5"
              >
                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
                  <div className="panel-header">
                    <span className="panel-label">Scene viewport · Earth</span>
                    <span className="font-mono-data text-[10px] text-[var(--text-3)] tracking-[0.1em]">AVYAN NETRA</span>
                  </div>

                  <div className="relative h-64 sm:h-72 lg:h-[340px] overflow-hidden">
                    <video
                      className="absolute inset-0 h-full w-full object-cover"
                      src="/4788-180289892.mp4"
                      autoPlay
                      muted
                      loop
                      playsInline
                      aria-label="Satellite imagery viewport"
                    />
                    {/* Fine survey grid */}
                    <div
                      aria-hidden
                      className="absolute inset-0 opacity-40 pointer-events-none"
                      style={{
                        backgroundImage:
                          "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
                        backgroundSize: "28px 28px",
                      }}
                    />
                    {/* Sensor sweep */}
                    <div aria-hidden className="absolute inset-0 scan-sweep pointer-events-none" />
                    {/* Vignette for caption legibility */}
                    <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-black/25 pointer-events-none" />

                    {/* Corner brackets */}
                    <span aria-hidden className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-[var(--accent)]/70" />
                    <span aria-hidden className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-[var(--accent)]/70" />
                    <span aria-hidden className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-[var(--accent)]/70" />
                    <span aria-hidden className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-[var(--accent)]/70" />

                    {/* Crosshair */}
                    <div aria-hidden className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
                      <div className="w-9 h-9 rounded-full border border-[var(--accent)]/50" />
                      <span className="absolute left-1/2 top-1/2 w-1 h-1 -translate-x-1/2 -translate-y-1/2 bg-[var(--accent)]" />
                    </div>

                    {/* Coordinates */}
                    <span className="absolute top-3.5 left-9 font-mono-data text-[9px] tracking-[0.12em] text-white/75">28.6139°N · 77.2090°E</span>

                    {/* Sample detections */}
                    <div className="absolute left-[16%] bottom-[18%] w-24 h-14 border border-dashed border-[var(--accent)]/80">
                      <span className="absolute -top-[18px] left-0 font-mono-data text-[8px] tracking-[0.14em] text-[var(--accent)] bg-black/55 px-1 py-px">WATER BODY</span>
                    </div>
                    <div className="absolute right-[12%] top-[24%] w-20 h-20 border border-dashed border-white/50">
                      <span className="absolute -top-[18px] left-0 font-mono-data text-[8px] tracking-[0.14em] text-white/80 bg-black/55 px-1 py-px">BUILT-UP</span>
                    </div>
                  </div>

                  {/* Readout strip */}
                  <div className="grid grid-cols-3 divide-x divide-[var(--border)] border-t border-[var(--border)] bg-[var(--surface-2)]">
                    {["Optical + SAR", "Bi-temporal", "10 m / px"].map((t) => (
                      <span key={t} className="py-2 text-center font-mono-data text-[9px] tracking-[0.14em] uppercase text-[var(--text-3)]">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </motion.div>
            </div>
          </section>

          {/* ── STATS ROW ────────────────────────────────────────────────── */}
          <section ref={statsRef} className="px-6 md:px-10 py-10 border-b border-[var(--border)]">
            <motion.div
              variants={stagger}
              initial="hidden"
              animate={statsInView ? "show" : "hidden"}
              className="max-w-7xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6"
            >
              {stats.map(({ value, suffix, label }) => (
                <motion.div key={label} variants={fadeUp} className="text-center">
                  <div className="text-3xl font-black text-[var(--heading)] tracking-tight mb-1 font-mono-data">
                    <NumberTicker value={value} suffix={suffix} duration={1600} />
                  </div>
                  <p className="text-xs text-[var(--text-3)] font-medium">{label}</p>
                </motion.div>
              ))}
            </motion.div>
          </section>

          {/* ── FEATURES: BENTO GRID ─────────────────────────────────────── */}
          <section className="px-6 md:px-10 py-10 border-b border-[var(--border)]">
            <div className="max-w-7xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5 }}
                className="flex items-end justify-between mb-6"
              >
                <div>
                  <p className="text-[11px] font-bold text-[var(--accent)] uppercase tracking-widest mb-1 font-mono-data">Capabilities</p>
                  <h2 className="text-2xl font-bold text-[var(--heading)] tracking-tight">What can you do with SatQuery AI?</h2>
                </div>
                <Link
                  href="/analysis"
                  className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-[var(--accent)] hover:text-[var(--primary)] transition-colors"
                >
                  Explore all
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
              </motion.div>

              <motion.div
                variants={stagger}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, margin: "-40px" }}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
              >
                {features.map((f) => (
                  <motion.div key={f.id} variants={scaleIn}>
                    <Link href={f.href} className="block h-full">
                      <SpotlightCard
                        spotlightColor={f.glow}
                        className={`h-full bg-[var(--surface)] border border-[var(--border)] ${f.border} rounded-xl p-4 flex flex-col gap-3 transition-all duration-200 hover:-translate-y-0.5 group cursor-pointer`}
                      >
                        {/* Mini image */}
                        <div className="h-24 rounded-lg overflow-hidden relative">
                          <div className={`absolute inset-0 ${f.imgClass}`} />
                          <div className="absolute inset-0 bg-gradient-to-t from-[var(--surface)]/80 to-transparent" />
                          <div className={`absolute inset-0 bg-gradient-to-br ${f.accent} opacity-50`} />
                        </div>

                        {/* Icon + Title */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)] group-hover:border-[var(--accent)]/40 transition-colors shrink-0">
                              {f.icon}
                            </div>
                            <h3 className="text-sm font-semibold text-[var(--heading)] leading-snug">{f.title}</h3>
                          </div>
                          <svg className="w-4 h-4 text-[var(--text-4)] group-hover:text-[var(--accent)] transition-colors shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>

                        <p className="text-xs text-[var(--text-2)] leading-relaxed flex-1">{f.desc}</p>

                        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[var(--border)]">
                          {f.tags.map((t) => (
                            <span key={t} className="px-2 py-0.5 rounded-md bg-[var(--surface-2)] text-[10px] font-medium text-[var(--text-3)]">
                              {t}
                            </span>
                          ))}
                        </div>
                      </SpotlightCard>
                    </Link>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </section>

          {/* ── CTA BANNER ───────────────────────────────────────────────── */}
          <motion.section
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.55 }}
            className="px-6 md:px-10 py-10 border-b border-[var(--border)]"
          >
            <div className="max-w-7xl mx-auto">
              <div className="relative overflow-hidden rounded-2xl border border-[var(--accent)]/20 bg-gradient-to-r from-[var(--surface-2)] via-[var(--surface-3)] to-[var(--surface-2)] px-8 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(var(--accent)_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none" />
                <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full bg-[var(--accent)]/10 blur-3xl pointer-events-none" />
                <div className="relative z-10">
                  <h3 className="text-xl font-bold text-[var(--heading)] mb-1.5">Ready to analyze your first scene?</h3>
                  <p className="text-sm text-[var(--text-2)]">Upload imagery or start with a natural language query — no code required.</p>
                </div>
                <div className="relative z-10 flex gap-3 shrink-0">
                  <ShimmerButton
                    onClick={() => router.push("/analysis")}
                    shimmerColor="rgba(0, 213, 190, 0.15)"
                    shimmerDuration="2.5s"
                    className="px-5 py-2.5 rounded-xl bg-[var(--accent)] text-[var(--canvas)] text-sm font-bold hover:brightness-110 transition-colors shadow-md shadow-[var(--accent)]/30"
                  >
                    Start Analysis
                  </ShimmerButton>
                  <Link
                    href="/documentation"
                    className="px-5 py-2.5 rounded-xl border border-[var(--border-strong)] text-[var(--text-2)] hover:text-[var(--heading)] hover:border-[var(--accent)]/40 text-sm font-medium transition-all"
                  >
                    Read Docs
                  </Link>
                </div>
              </div>
            </div>
          </motion.section>

          {/* ── RECENT ANALYSES ──────────────────────────────────────────── */}
          <section className="px-6 md:px-10 py-10">
            <div className="max-w-7xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5 }}
                className="flex items-center justify-between mb-5"
              >
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-[var(--accent)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="9" />
                    <polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <h2 className="text-base font-bold text-[var(--heading)] tracking-tight">Recent Analyses</h2>
                </div>
                <Link href="/history" className="text-xs font-medium text-[var(--accent)] hover:text-[var(--primary)] flex items-center gap-1 transition-colors">
                  View all
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
              </motion.div>

              <motion.div
                variants={stagger}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, margin: "-40px" }}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
              >
                {recentAnalyses.map((item, i) => (
                  <motion.div key={item.job_id || i} variants={fadeUp}>
                    <Link
                      href={`/analysis/${item.job_id}`}
                      className="flex items-center gap-3 p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)]/30 hover:bg-[var(--surface-2)] transition-all duration-200 group"
                    >
                      <div className={`w-12 h-12 rounded-lg overflow-hidden shrink-0 relative border border-[var(--border)]`}>
                        <div className={`absolute inset-0 ${item.imgClass}`} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-[var(--heading)] truncate group-hover:text-[var(--accent)] transition-colors">{item.title}</p>
                        <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded bg-[var(--accent)]/10 text-[9px] font-medium text-[var(--accent)] border border-[var(--accent)]/20 font-mono-data">
                          {item.tag}
                        </span>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5 truncate">{item.meta}</p>
                      </div>
                      <svg className="w-3.5 h-3.5 text-[var(--text-4)] group-hover:text-[var(--accent)] transition-colors shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </Link>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
