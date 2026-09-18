"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useInView } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { BorderBeam } from "@/components/ui/border-beam";
import { NumberTicker } from "@/components/ui/number-ticker";
import { BlurFade } from "@/components/ui/blur-fade";
import { AuroraText } from "@/components/ui/aurora-text";
import { Marquee } from "@/components/ui/marquee";

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
    border: "hover:border-amber-500/50",
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
    border: "hover:border-emerald-500/50",
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
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const statsRef = useRef(null);
  const statsInView = useInView(statsRef, { once: true, margin: "-80px" });

  const { data: jobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.listJobs(),
    staleTime: 30_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: false,
  });

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
    try {
      await api.uploadRasters(Array.from(files));
      router.push("/analysis");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setUploadError(msg);
    } finally {
      setIsUploading(false);
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
      <style dangerouslySetInnerHTML={{ __html: `body { overflow-y: auto !important; height: auto !important; }` }} />
      <div className="bg-[var(--canvas)] text-[var(--text)] font-sans min-h-screen flex antialiased">
        <Sidebar activeItem="home" hideBrand={false} className="sticky top-0 h-screen flex-shrink-0" />

        <main className="flex-1 flex flex-col min-w-0 bg-[var(--canvas)] relative">
          <TopBar
            showBrand={false}
            searchPlaceholder='Search anything… e.g. "urban expansion in Delhi"'
            onSearch={(val) => { if (val) router.push(`/analysis?q=${encodeURIComponent(val)}`); }}
          />

          {/* ── HERO ─────────────────────────────────────────────────────── */}
          <section className="relative px-6 md:px-10 pt-10 pb-14 overflow-hidden border-b border-[var(--border)]">
            {/* Radial glow blob (subtle, single source) */}
            <div className="absolute -top-32 left-1/3 w-[600px] h-[600px] rounded-full bg-[var(--cyan)]/[0.04] blur-[120px] pointer-events-none" />

            <div className="relative z-10 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              {/* Left: Headline + Upload Card */}
              <motion.div variants={stagger} initial="hidden" animate="show">
                {/* Pill badge */}
                <motion.div variants={fadeUp}>
                  <div className="inline-flex items-center gap-2 mb-5 px-3 py-1.5 rounded-full border border-[var(--cyan)]/30 bg-[var(--cyan)]/8 backdrop-blur-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--cyan)] animate-pulse-dot" />
                    <span className="text-[11px] font-semibold tracking-widest text-[var(--cyan)] uppercase">
                      AI Copilot for Remote Sensing
                    </span>
                  </div>
                </motion.div>

                {/* H1 */}
                <motion.h1
                  variants={fadeUp}
                  className="text-[2.6rem] sm:text-5xl font-extrabold text-[var(--heading)] tracking-tight leading-[1.1] mb-5"
                >
                  Analyze Earth imagery
                  <br />
                  with{" "}
                  <AuroraText
                    as="span"
                    colors={["#00d5be", "#168BFF", "#7957FF", "#00d5be"]}
                    speed={8}
                    className="font-extrabold"
                  >
                    natural language.
                  </AuroraText>
                </motion.h1>

                <motion.p variants={fadeUp} className="text-[var(--text-2)] text-[15px] leading-relaxed mb-7 max-w-lg">
                  Ask questions. Compare imagery. Discover change.
                  Understand what&apos;s there — powered by satellite AI that doesn&apos;t need code.
                </motion.p>

                {/* Upload + Query card */}
                <motion.div variants={scaleIn} className="relative rounded-2xl overflow-hidden">
                  <div className="relative bg-[var(--surface)]/90 backdrop-blur-xl border border-[var(--border)] rounded-2xl p-5 shadow-2xl shadow-black/40">
                    <BorderBeam duration={6} size={250} colorFrom="#00d5be" colorTo="#00f2fe" />

                    {/* Drop zone */}
                    <div className="flex flex-col sm:flex-row items-center gap-4 pb-4 border-b border-[var(--border)]">
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
                        onDragOver={(e) => { e.preventDefault(); !isUploading && setDragActive(true); }}
                        onDragLeave={() => setDragActive(false)}
                        onDrop={handleFileDrop}
                        className={`flex-1 w-full border border-dashed rounded-xl py-4 px-5 text-center transition-all duration-200 ${
                          isUploading || isSubmitting
                            ? "cursor-not-allowed opacity-60"
                            : "cursor-pointer hover:bg-[var(--cyan)]/5"
                        } ${dragActive ? "border-[var(--cyan)] bg-[var(--cyan)]/10" : "border-[var(--border-strong)] hover:border-[var(--cyan)]/40"}`}
                      >
                        <div className="flex items-center justify-center gap-2 text-sm font-medium text-[var(--heading)]">
                          {isUploading ? (
                            <>
                              <svg className="w-4 h-4 text-[var(--cyan)] animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                              <span>Processing imagery…</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                              <span>Drop satellite images here</span>
                            </>
                          )}
                        </div>
                        <p className="text-[11px] text-[var(--text-3)] mt-1">GeoTIFF · TIFF · PNG · JPEG · GeoJSON</p>
                      </div>

                      <span className="text-[11px] text-[var(--text-3)] font-semibold uppercase hidden sm:block px-1">or</span>

                      <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading || isSubmitting}
                        className="shrink-0 w-full sm:w-auto px-4 py-3 rounded-xl bg-[var(--surface-2)] border border-[var(--border-strong)] hover:border-[var(--cyan)]/40 text-[var(--heading)] hover:text-[var(--heading)] flex items-center justify-center gap-2 text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-4 h-4 text-[var(--text-3)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        Browse Files
                      </button>
                    </div>

                    {/* Query bar */}
                    <form onSubmit={handleQuerySubmit} className="mt-4 flex items-center gap-2 bg-[var(--canvas)] border border-[var(--border-strong)] rounded-xl px-4 py-2.5 focus-within:border-[var(--cyan)]/70 focus-within:ring-1 focus-within:ring-[var(--cyan)]/20 transition-all">
                      <svg className="w-4 h-4 text-[var(--cyan)] shrink-0" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z" />
                      </svg>
                      <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        disabled={isUploading || isSubmitting}
                        className="bg-transparent border-none text-[var(--heading)] placeholder-[var(--text-3)] text-sm w-full focus:outline-none p-0 disabled:opacity-50"
                        placeholder="Ask a question about your imagery…"
                      />
                      <button
                        type="submit"
                        disabled={isUploading || isSubmitting || !query.trim()}
                        className="w-8 h-8 rounded-lg bg-[var(--cyan)] text-[var(--canvas)] hover:brightness-110 transition-all shrink-0 flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-[var(--cyan)]/30"
                      >
                        {isSubmitting ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                            <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </button>
                    </form>
                  </div>
                </motion.div>

                {uploadError && (
                  <motion.div variants={fadeUp} className="mt-4 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 text-xs flex items-start gap-2">
                    <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <span>{uploadError}</span>
                  </motion.div>
                )}

                {/* Quick prompts */}
                <motion.div variants={fadeUp} className="flex flex-wrap items-center gap-2 mt-4 text-xs">
                  <span className="text-[var(--text-3)] font-medium">Try asking:</span>
                  {[
                    "Describe this scene",
                    "Highlight the water body",
                    "What changed between these dates?",
                    "Optical + SAR analysis",
                  ].map((p) => (
                    <button
                      key={p}
                      onClick={() => handleQuickPrompt(p)}
                      className="px-3 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-2)] hover:border-[var(--cyan)]/50 hover:text-[var(--cyan)] transition-all duration-150 hover:bg-[var(--cyan)]/5"
                    >
                      {p}
                    </button>
                  ))}
                </motion.div>
              </motion.div>

              {/* Right: Floating analytics preview */}
              {/*<motion.div*/}
              {/*  initial={{ opacity: 0, x: 32 }}*/}
              {/*  animate={{ opacity: 1, x: 0 }}*/}
              {/*  transition={{ duration: 0.7, delay: 0.3, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}*/}
              {/*  className="hidden lg:flex flex-col gap-4"*/}
              {/*>*/}
              {/*  /!* Optical + SAR side-by-side *!/*/}
              {/*  <div className="relative bg-[var(--surface)]/80 border border-[var(--border)] backdrop-blur-md rounded-2xl p-4 shadow-xl">*/}
              {/*    <p className="text-[10px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-3">Live Fusion Preview</p>*/}
              {/*    <div className="flex items-center gap-3 justify-center">*/}
              {/*      <div className="relative w-40 h-28 rounded-lg overflow-hidden border border-[var(--cyan)]/40">*/}
              {/*        <div className="absolute inset-0 sat-crop-delhi-main" />*/}
              {/*        <span className="absolute bottom-1.5 left-2 px-1.5 py-0.5 rounded bg-black/60 text-[10px] font-semibold text-[var(--text-2)]">Optical</span>*/}
              {/*      </div>*/}
              {/*      <div className="text-[var(--text-3)] font-bold text-xl">+</div>*/}
              {/*      <div className="relative w-40 h-28 rounded-lg overflow-hidden border border-[var(--text-4)]/60">*/}
              {/*        <div className="absolute inset-0 sat-crop-sar" />*/}
              {/*        <span className="absolute bottom-1.5 left-2 px-1.5 py-0.5 rounded bg-black/60 text-[10px] font-semibold text-[var(--text-2)]">SAR</span>*/}
              {/*      </div>*/}
              {/*    </div>*/}
              {/*  </div>*/}

              {/*  /!* Classification pill list *!/*/}
              {/*  <div className="flex flex-col gap-2">*/}
              {/*    {[*/}
              {/*      { color: "bg-[var(--green)]", label: "Land Cover", val: "73%" },*/}
              {/*      { color: "bg-[var(--cyan)]", label: "Water Bodies", val: "18%" },*/}
              {/*      { color: "bg-[var(--warning)]", label: "Built-up Areas", val: "6%" },*/}
              {/*      { color: "bg-[var(--error)]", label: "Change Detected", val: "3%" },*/}
              {/*    ].map(({ color, label, val }) => (*/}
              {/*      <div key={label} className="flex items-center justify-between px-4 py-2.5 rounded-xl bg-[var(--surface)]/80 border border-[var(--border)] backdrop-blur-sm">*/}
              {/*        <div className="flex items-center gap-2.5">*/}
              {/*          <span className={`w-2 h-2 rounded-full ${color}`} />*/}
              {/*          <span className="text-xs font-medium text-[var(--text-2)]">{label}</span>*/}
              {/*        </div>*/}
              {/*        <span className="text-xs font-bold text-[var(--text-3)] font-mono-data">{val}</span>*/}
              {/*      </div>*/}
              {/*    ))}*/}
              {/*  </div>*/}

              {/*  /!* AI detection badge *!/*/}
              {/*  <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-[var(--cyan)]/5 border border-[var(--cyan)]/20 backdrop-blur-sm">*/}
              {/*    <div className="w-2 h-2 rounded-full bg-[var(--cyan)] animate-pulse-dot" />*/}
              {/*    <p className="text-xs text-[var(--cyan)] font-medium">*/}
              {/*      AI model running — <span className="text-[var(--text-3)] font-normal">GeoFM · Change-VQA · SAR-Encoder</span>*/}
              {/*    </p>*/}
              {/*  </div>*/}
              {/*</motion.div>*/}
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
                  <p className="text-[11px] font-bold text-[var(--cyan)] uppercase tracking-widest mb-1 font-mono-data">Capabilities</p>
                  <h2 className="text-2xl font-bold text-[var(--heading)] tracking-tight">What can you do with SatQuery AI?</h2>
                </div>
                <Link
                  href="/analysis"
                  className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-[var(--cyan)] hover:text-[var(--primary)] transition-colors"
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
                            <div className="w-8 h-8 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center text-[var(--cyan)] group-hover:border-[var(--cyan)]/40 transition-colors shrink-0">
                              {f.icon}
                            </div>
                            <h3 className="text-sm font-semibold text-[var(--heading)] leading-snug">{f.title}</h3>
                          </div>
                          <svg className="w-4 h-4 text-[var(--text-4)] group-hover:text-[var(--cyan)] transition-colors shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
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
              <div className="relative overflow-hidden rounded-2xl border border-[var(--cyan)]/20 bg-gradient-to-r from-[var(--surface-2)] via-[var(--surface-3)] to-[var(--surface-2)] px-8 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(var(--cyan)_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none" />
                <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full bg-[var(--cyan)]/10 blur-3xl pointer-events-none" />
                <div className="relative z-10">
                  <h3 className="text-xl font-bold text-[var(--heading)] mb-1.5">Ready to analyze your first scene?</h3>
                  <p className="text-sm text-[var(--text-2)]">Upload imagery or start with a natural language query — no code required.</p>
                </div>
                <div className="relative z-10 flex gap-3 shrink-0">
                  <ShimmerButton
                    onClick={() => router.push("/analysis")}
                    shimmerColor="rgba(0, 213, 190, 0.15)"
                    shimmerDuration="2.5s"
                    className="px-5 py-2.5 rounded-xl bg-[var(--cyan)] text-[var(--canvas)] text-sm font-bold hover:brightness-110 transition-colors shadow-md shadow-[var(--cyan)]/30"
                  >
                    Start Analysis
                  </ShimmerButton>
                  <Link
                    href="/documentation"
                    className="px-5 py-2.5 rounded-xl border border-[var(--border-strong)] text-[var(--text-2)] hover:text-[var(--heading)] hover:border-[var(--cyan)]/40 text-sm font-medium transition-all"
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
                  <svg className="w-4 h-4 text-[var(--cyan)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="9" />
                    <polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <h2 className="text-base font-bold text-[var(--heading)] tracking-tight">Recent Analyses</h2>
                </div>
                <Link href="/history" className="text-xs font-medium text-[var(--cyan)] hover:text-[var(--primary)] flex items-center gap-1 transition-colors">
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
                      className="flex items-center gap-3 p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--cyan)]/30 hover:bg-[var(--surface-2)] transition-all duration-200 group"
                    >
                      <div className={`w-12 h-12 rounded-lg overflow-hidden shrink-0 relative border border-[var(--border)]`}>
                        <div className={`absolute inset-0 ${item.imgClass}`} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-[var(--heading)] truncate group-hover:text-[var(--cyan)] transition-colors">{item.title}</p>
                        <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded bg-[var(--cyan)]/10 text-[9px] font-medium text-[var(--cyan)] border border-[var(--cyan)]/20 font-mono-data">
                          {item.tag}
                        </span>
                        <p className="text-[10px] text-[var(--text-3)] mt-0.5 truncate">{item.meta}</p>
                      </div>
                      <svg className="w-3.5 h-3.5 text-[var(--text-4)] group-hover:text-[var(--cyan)] transition-colors shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
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
