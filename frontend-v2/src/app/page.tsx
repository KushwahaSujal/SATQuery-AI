"use client";

import Link from "next/link";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UploadedRaster, TaskType } from "@/lib/types";

const FEATURE_CARDS = [
  { icon: "maximize-2", title: "Single Image Analysis", desc: "Ask questions, get descriptions, find regions and more.", tags: ["VQA", "Captioning", "Grounding"] },
  { icon: "layers", title: "Optical + SAR Fusion", desc: "Combine multi-sensor data for richer, more reliable insights.", tags: ["Cross-Modal", "Information Extraction"] },
  { icon: "git-compare", title: "Bi-temporal Change Analysis", desc: "Detect and understand changes over time.", tags: ["Change Detection", "Change VQA"] },
  { icon: "cpu", title: "Agentic Model Orchestration", desc: "Automatically selects the right models, validates inputs and returns evidence.", tags: ["Smart Routing", "Execution Trace"] },
];

const EXAMPLE_CHIPS = [
  { label: "Describe this scene", query: "Describe this scene" },
  { label: "Highlight the water body", query: "Highlight the water body in the image" },
  { label: "What changed between these dates?", query: "What changed between these two dates?" },
  { label: "Use optical and SAR together", query: "Use optical and SAR data together for analysis" },
];

function FeatureIcon({ name, className, style }: { name: string; className?: string; style?: React.CSSProperties }) {
  const icons: Record<string, React.ReactNode> = {
    "maximize-2": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect height="18" rx="2" width="18" x="3" y="3" /><circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" /><path d="M21 15l-5-5L5 21" /></svg>,
    layers: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>,
    "git-compare": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    cpu: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect height="16" rx="2" width="16" x="4" y="4" /><path d="M9 9h6v6H9z" /><path d="M9 1v3m6-3v3M9 20v3m6-3v3M20 9h3m-3 6h3M1 9h3m-3 6h3" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    "chevron-right": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    sparkles: <svg className={className} fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z" /></svg>,
    send: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    "cloud-upload": <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>,
    folder: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" /></svg>,
    clock: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  };
  const icon = icons[name] ?? null;
  return icon ? <span style={style} className="inline-flex">{icon}</span> : null;
}

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [rasters, setRasters] = useState<UploadedRaster[]>([]);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      const { rasters } = await api.uploadRasters(Array.from(files));
      setRasters((prev) => [...prev, ...rasters]);
    } catch {
      // Silent fallback
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmit() {
    if (!query.trim()) return;
    if (rasters.length > 0) {
      try {
        const filenames = rasters.map((r) => r.filename);
        const reqId = rasters[0]?.request_id;
        const res = await api.analyze({ query, image_filenames: filenames, request_id: reqId });
        router.push(`/analysis/${res.job_id}`);
      } catch {
        router.push(`/analysis`);
      }
    } else {
      router.push(`/analysis`);
    }
  }

  return (
    <div className="px-8 pt-8 pb-10 space-y-8">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="hero-glow-overlay absolute inset-0 pointer-events-none" />
        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center gap-2 text-xs font-semibold tracking-wider uppercase mb-4" style={{ color: "var(--cyan)" }}>
            <span className="w-4 h-0.5 rounded-full" style={{ background: "var(--cyan)" }} />
            AI COPILOT FOR REMOTE-SENSING ANALYSIS
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight leading-[1.15] mb-4" style={{ color: "var(--heading)" }}>
            Analyze Earth imagery<br />
            with <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00C9E8] to-[#087FF5] glow-primary-text">natural language.</span>
          </h1>
          <p className="text-sm sm:text-base leading-relaxed mb-6" style={{ color: "var(--text-2)" }}>
            Ask questions. Compare imagery. Discover change.<br />
            Understand what&apos;s there — with the power of AI.
          </p>

          {/* Upload + Query Card */}
          <div
            className="backdrop-blur-xl rounded-2xl p-5"
            style={{ background: "var(--surface-2)", border: "1px solid var(--border-strong)", boxShadow: "var(--shadow-lg)" }}
          >
            {/* Upload row */}
            <div className="flex flex-col sm:flex-row items-center gap-4 pb-4" style={{ borderBottom: "1px solid var(--border)" }}>
              <div
                className="flex-1 w-full border-dashed rounded-xl py-4 px-5 text-center cursor-pointer group transition-all"
                style={{ border: "1px dashed var(--border-strong)" }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); handleUpload(e.dataTransfer.files); }}
                onClick={() => fileRef.current?.click()}
              >
                <div className="flex items-center justify-center gap-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                  <FeatureIcon name="cloud-upload" className="w-4 h-4" style={{ color: "var(--cyan)" }} />
                  <span>Drop your satellite images here</span>
                </div>
                <p className="text-[11px] mt-1" style={{ color: "var(--text-2)" }}>Supports GeoTIFF, TIFF, PNG, JPEG</p>
                {rasters.length > 0 && (
                  <p className="text-[11px] mt-1" style={{ color: "var(--cyan)" }}>{rasters.length} file(s) ready</p>
                )}
              </div>
              <div className="text-xs font-medium uppercase px-1 hidden sm:block" style={{ color: "var(--text-2)" }}>or</div>
              <button
                onClick={() => fileRef.current?.click()}
                className="w-full sm:w-auto px-5 py-3.5 rounded-xl flex items-center justify-center gap-2 text-sm font-medium transition-all"
                style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)", color: "var(--text)" }}
              >
                <FeatureIcon name="folder" className="w-4 h-4" style={{ color: "var(--text-2)" }} />
                <span>Browse Files</span>
              </button>
              <input ref={fileRef} type="file" multiple accept=".tif,.tiff,.png,.jpg,.jpeg" className="hidden" onChange={(e) => handleUpload(e.target.files)} />
            </div>

            {/* Query input */}
            <div
              className="mt-4 flex items-center gap-2 rounded-xl px-4 py-2.5 transition-all"
              style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
            >
              <FeatureIcon name="sparkles" className="w-4 h-4 shrink-0" style={{ color: "var(--cyan)" }} />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
                className="bg-transparent border-none text-sm w-full focus:outline-none focus:ring-0 p-0"
                style={{ color: "var(--heading)" }}
                placeholder="Ask a question about your imagery..."
              />
              <button
                onClick={handleSubmit}
                className="p-2 rounded-lg font-semibold shrink-0 transition-all"
                style={{ background: "var(--primary)", color: "#FFFFFF", boxShadow: "0 0 10px var(--primary-glow)" }}
              >
                <FeatureIcon name="send" className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick prompts */}
          <div className="flex flex-wrap items-center gap-2 mt-4 text-xs">
            <span className="font-medium mr-1" style={{ color: "var(--text-2)" }}>Try asking:</span>
            {EXAMPLE_CHIPS.map((chip) => (
              <button
                key={chip.label}
                onClick={() => { setQuery(chip.query); inputRef.current?.focus(); }}
                className="px-3 py-1 rounded-full transition-colors"
                style={{ background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text)" }}
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-bold tracking-tight" style={{ color: "var(--heading)" }}>What can you do with SatQuery AI?</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURE_CARDS.map((card) => (
            <div
              key={card.title}
              className="rounded-xl p-3.5 flex flex-col justify-between transition-all hover:-translate-y-0.5 group"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
            >
              <div>
                <div
                  className="h-28 w-full rounded-lg overflow-hidden mb-3.5 flex items-center justify-center relative"
                  style={{ background: "var(--surface-3)" }}
                >
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center"
                    style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)" }}
                  >
                    <FeatureIcon name={card.icon} className="w-6 h-6" style={{ color: "var(--cyan)" }} />
                  </div>
                  <div className="absolute inset-0 bg-[radial-gradient(var(--primary)_1px,transparent_1px)] [background-size:10px_10px] opacity-10" />
                </div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <FeatureIcon name={card.icon} className="w-4 h-4 shrink-0" style={{ color: "var(--cyan)" }} />
                    <h3 className="text-sm font-semibold" style={{ color: "var(--heading)" }}>{card.title}</h3>
                  </div>
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center transition-colors"
                    style={{ background: "var(--surface-3)", color: "var(--text-3)" }}
                  >
                    <FeatureIcon name="chevron-right" className="w-3.5 h-3.5" />
                  </div>
                </div>
                <p className="text-xs line-clamp-2 mb-4 leading-relaxed" style={{ color: "var(--text-2)" }}>{card.desc}</p>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                {card.tags.map((tag) => (
                  <span key={tag} className="px-2 py-0.5 rounded text-[10px] font-medium" style={{ background: "var(--surface-3)", color: "var(--text-2)" }}>{tag}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Recent Analyses */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FeatureIcon name="clock" className="w-4 h-4" style={{ color: "var(--cyan)" }} />
            <h2 className="text-base font-bold tracking-tight" style={{ color: "var(--heading)" }}>Recent Analyses</h2>
          </div>
          <Link href="/history" className="text-xs font-medium flex items-center gap-1 transition-colors" style={{ color: "var(--primary)" }}>
            View all
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </Link>
        </div>
        <div className="text-center py-12 text-sm" style={{ color: "var(--text-2)" }}>
          <p>No recent analyses yet.</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-3)" }}>Upload imagery and run a query to see analyses here.</p>
        </div>
      </section>
    </div>
  );
}
