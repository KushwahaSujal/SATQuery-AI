"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UploadedRaster } from "@/lib/types";

const SUGGESTIONS = [
  { icon: "building", label: "Detect urban expansion in this region" },
  { icon: "chart", label: "Find changes in vegetation over time" },
  { icon: "inbox", label: "Identify water bodies in the area" },
  { icon: "file", label: "Generate a summary report" },
  { icon: "copy", label: "Compare optical and SAR data" },
  { icon: "edit", label: "Analyze land use patterns" },
];

function SugIcon({ name, className, style }: { name: string; className?: string; style?: React.CSSProperties }) {
  const m: Record<string, React.ReactNode> = {
    building: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    chart: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    inbox: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    file: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    copy: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    edit: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    send: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    image: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect height="18" rx="2" width="18" x="3" y="3" /><circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" /><path d="M21 15l-5-5L5 21" /></svg>,
    database: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>,
    target: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>,
    sliders: <svg className={className} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    check: <svg className={className} fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  };
  const icon = m[name] ?? null;
  return icon ? <span style={style} className="inline-flex">{icon}</span> : null;
}

export default function AnalysisPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [rasters, setRasters] = useState<UploadedRaster[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      const { rasters } = await api.uploadRasters(Array.from(files));
      setRasters((prev) => [...prev, ...rasters]);
    } catch { /* silent */ } finally { setUploading(false); }
  }

  async function handleSubmit() {
    if (!query.trim()) return;
    if (rasters.length > 0) {
      try {
        const res = await api.analyze({ query, image_filenames: rasters.map(r => r.filename), request_id: rasters[0]?.request_id });
        router.push(`/analysis/${res.job_id}`);
        return;
      } catch { /* fallback */ }
    }
    router.push(`/analysis`);
  }

  return (
    <div className="flex-1 flex flex-col overflow-y-auto px-6 py-4 space-y-4 h-[calc(100vh-64px)]" style={{ background: "var(--canvas)" }}>
      {/* Hero Banner */}
      <section
        className="relative overflow-hidden rounded-2xl p-5 shrink-0"
        style={{ border: "1px solid var(--border-strong)", background: "var(--surface-2)" }}
      >
        <div className="hero-glow-overlay absolute inset-0 pointer-events-none" />
        <div className="relative z-10 flex items-center justify-between">
          <div className="max-w-md space-y-2">
            <div
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold"
              style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)", color: "var(--cyan)" }}
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
              <span>AI ASSISTANT</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--heading)" }}>Your Satellite Intelligence Copilot</h1>
            <p className="text-xs leading-relaxed" style={{ color: "var(--text)" }}>Ask questions, analyze imagery, get insights — powered by advanced AI and real satellite data.</p>
          </div>
        </div>

        {/* Quick action tiles */}
        <div className="grid grid-cols-4 gap-3 mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          {[
            { icon: "image", title: "Image Analysis", desc: "Understand what's in your imagery" },
            { icon: "chart", title: "Data Insights", desc: "Find patterns and changes" },
            { icon: "file", title: "Reports", desc: "Generate detailed reports" },
            { icon: "sliders", title: "Multi-Modal", desc: "Combine optical + SAR" },
          ].map((item) => (
            <div
              key={item.title}
              className="p-2.5 rounded-xl cursor-pointer flex items-center gap-3 transition"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)" }}
              >
                <SugIcon name={item.icon} className="w-4 h-4" style={{ color: "var(--cyan)" }} />
              </div>
              <div className="min-w-0">
                <h4 className="text-xs font-semibold truncate" style={{ color: "var(--heading)" }}>{item.title}</h4>
                <p className="text-[10px] truncate" style={{ color: "var(--text-2)" }}>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Center suggestions */}
      <section className="flex-1 flex flex-col items-center justify-center py-6 px-4">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center mb-3 glow-cyan-sm"
          style={{ background: "var(--cyan-glow)", border: "1px solid var(--cyan)" }}
        >
          <svg className="w-5 h-5" style={{ color: "var(--cyan)" }} fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z" /></svg>
        </div>
        <h2 className="text-lg font-bold text-center" style={{ color: "var(--heading)" }}>How can I help you today?</h2>
        <p className="text-xs text-center max-w-md mt-1 mb-6" style={{ color: "var(--text-2)" }}>Ask anything about your satellite data — from land cover analysis to change detection.</p>

        <div className="grid grid-cols-2 gap-3 w-full max-w-2xl">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => { setQuery(s.label); }}
              className="flex items-center gap-3 p-3 text-left rounded-xl transition group"
              style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
            >
              <SugIcon name={s.icon} className="w-4 h-4 shrink-0 group-hover:scale-110 transition-transform" style={{ color: "var(--cyan)" }} />
              <span className="text-xs font-medium" style={{ color: "var(--text)" }}>{s.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Bottom composer */}
      <div className="mt-auto shrink-0">
        <div className="rounded-xl p-3" style={{ border: "1px solid var(--border-strong)", background: "var(--surface-2)", boxShadow: "var(--shadow-md)" }}>
          <div className="flex items-center gap-3 pb-2.5">
            <button onClick={() => fileRef.current?.click()} className="p-1 transition" style={{ color: "var(--text-2)" }}>
              <SugIcon name="image" className="w-5 h-5" />
            </button>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
              className="flex-1 bg-transparent border-0 text-xs focus:ring-0 focus:outline-none"
              style={{ color: "var(--heading)" }}
              placeholder="Ask a question about your satellite imagery..."
            />
            <button
              onClick={handleSubmit}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition"
              style={{ background: "var(--primary)", color: "#FFFFFF" }}
            >
              <SugIcon name="send" className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between pt-2 text-[11px]" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2">
              <button
                onClick={() => fileRef.current?.click()}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md transition"
                style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)", color: "var(--text)" }}
              >
                <SugIcon name="image" className="w-3.5 h-3.5" style={{ color: "var(--cyan)" }} />
                <span>Attach Image</span>
              </button>
              <button
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md transition"
                style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)", color: "var(--text)" }}
              >
                <SugIcon name="database" className="w-3.5 h-3.5" style={{ color: "var(--cyan)" }} />
                <span>Select Dataset</span>
              </button>
              <button
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md transition"
                style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)", color: "var(--text)" }}
              >
                <SugIcon name="target" className="w-3.5 h-3.5" style={{ color: "var(--cyan)" }} />
                <span>Choose Analysis Type</span>
              </button>
            </div>
            <div className="flex items-center gap-2">
              <span style={{ color: "var(--text-2)" }} className="font-medium">Advanced</span>
              <div
                className="w-8 h-4 rounded-full p-0.5 flex items-center cursor-pointer"
                style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)" }}
              >
                <div className="w-3 h-3 rounded-full" style={{ background: "var(--text)" }} />
              </div>
            </div>
          </div>
        </div>
        <input ref={fileRef} type="file" multiple accept=".tif,.tiff,.png,.jpg,.jpeg" className="hidden" onChange={(e) => handleUpload(e.target.files)} />

        <div className="flex items-center gap-3 text-[10px] mt-2 px-1" style={{ color: "var(--text-2)" }}>
          <div className="flex items-center gap-1.5">
            <div
              className="w-3.5 h-3.5 rounded-full flex items-center justify-center"
              style={{ background: "var(--green-bg)", border: "1px solid var(--green)" }}
            >
              <SugIcon name="check" className="w-2.5 h-2.5" style={{ color: "var(--green)" }} />
            </div>
            <span className="font-medium" style={{ color: "var(--green)" }}>AI Assistant Ready</span>
          </div>
          <span style={{ color: "var(--text-4)" }}>|</span>
          <span>Powered by Advanced ML Models</span>
        </div>
      </div>
    </div>
  );
}
