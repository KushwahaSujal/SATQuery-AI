"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const simulateProcessing = (callback: () => void) => {
    setIsUploading(true);
    setTimeout(() => {
      callback();
    }, 800);
  };

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
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      simulateProcessing(() => router.push("/analysis"));
    }
  };

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: `body { overflow-y: auto !important; height: auto !important; }` }} />
      <div className="bg-[#050911] text-slate-200 font-sans min-h-screen flex antialiased selection:bg-teal-500 selection:text-black">
        {/* Left Sidebar Navigation */}
        <Sidebar activeItem="home" hideBrand={false} className="sticky top-0 h-screen flex-shrink-0" />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#050911] relative">
        {/* TopBar Header */}
        <TopBar
          showBrand={false}
          searchPlaceholder='Search anything... (e.g. "urban expansion in Delhi")'
          onSearch={(val) => {
            if (val) router.push(`/analysis?q=${encodeURIComponent(val)}`);
          }}
        />

        {/* Hero Section */}
        <section className="relative px-8 pt-8 pb-10 border-b border-[#141e30] overflow-hidden">
          {/* Ambient Glow */}
          <div className="absolute inset-0 hero-glow-overlay pointer-events-none" />

          {/* Semi-transparent Earth Satellite Backdrop */}
          <div className="absolute right-0 top-0 w-3/5 h-full opacity-35 pointer-events-none select-none overflow-hidden mix-blend-screen hidden lg:block">
            <img
              alt="Satellite earth backdrop"
              className="w-full h-full object-cover object-right scale-110 blur-[1px]"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBiSm38CjZwA9aZcIl0dpx0SygZnM98iDrTy5AfRejRWjqJGG_AIbAKBxM5dJ44TH1nLSdHLZhZ3zXw-JlXlP5SAm_fi1m4t5WZ51bXqI_BfSmpDIHYXPXQWfnDPeFahqC1-uLnEEex4AhzD4j4A1cOW68ODyn7hZpg1YXeVlva6EpssfkzGGHCbvkAWrl-wDlzrTJnz8uu53TGwfomQwkV7Gg9WRiYdEs01h7kH7TjduJknv-Tc2pvIq4PoXcitRpB"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#050911] via-[#050911]/80 to-transparent" />
          </div>

          <div className="relative z-10 max-w-7xl mx-auto flex flex-col lg:flex-row gap-8 items-start justify-between">
            {/* Left Hero Text & Search Box */}
            <div className="max-w-2xl">
              {/* Tagline */}
              <div className="inline-flex items-center gap-2 text-xs font-semibold tracking-wider text-[#00d5be] uppercase mb-4">
                <span className="w-4 h-0.5 bg-[#00d5be] rounded-full" />
                <span>AI COPILOT FOR REMOTE-SENSING ANALYSIS</span>
              </div>

              {/* Main Heading */}
              <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.15] mb-4">
                Analyze Earth imagery <br />
                with <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00d5be] to-[#00f2fe] glow-cyan-text">natural language.</span>
              </h1>

              {/* Hero Subtitle */}
              <p className="text-slate-400 text-sm sm:text-base leading-relaxed mb-6 font-normal">
                Ask questions. Compare imagery. Discover change.<br />
                Understand what&apos;s there — with the power of AI.
              </p>

              {/* Central Upload & Query Card */}
              <div className="bg-[#091120]/90 backdrop-blur-xl border border-[#1b2b48] rounded-2xl p-5 shadow-2xl shadow-cyan-950/20">
                {/* Top Dropzone & Browse Row */}
                <div className="flex flex-col sm:flex-row items-center gap-4 pb-4 border-b border-[#162238]">
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".tif,.tiff,.png,.jpg,.jpeg,.geojson"
                    className="hidden"
                    disabled={isUploading || isSubmitting}
                    onChange={() => simulateProcessing(() => router.push("/analysis"))}
                  />
                  {/* Drag & Drop Zone */}
                  <div
                    onClick={() => !isUploading && !isSubmitting && fileInputRef.current?.click()}
                    onDragOver={(e) => { e.preventDefault(); !isUploading && setDragActive(true); }}
                    onDragLeave={() => setDragActive(false)}
                    onDrop={handleFileDrop}
                    className={`flex-1 w-full border border-dashed rounded-xl py-4 px-5 text-center transition-all ${isUploading || isSubmitting ? 'cursor-not-allowed opacity-70' : 'cursor-pointer group hover:bg-teal-500/5'} ${
                      dragActive
                        ? "border-teal-400 bg-teal-500/10"
                        : "border-[#243555] hover:border-teal-500/50"
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2 text-slate-200 text-sm font-medium group-hover:text-teal-300">
                      {isUploading ? (
                        <>
                          <svg className="w-5 h-5 text-teal-400 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span>Processing Imagery...</span>
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          <span>Drop your satellite images here</span>
                        </>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">Supports GeoTIFF, TIFF, PNG, JPEG (for benchmarks)</p>
                  </div>

                  {/* Divider */}
                  <div className="text-xs text-slate-400 font-medium uppercase px-1 hidden sm:block">or</div>

                  {/* Browse Files Button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading || isSubmitting}
                    className="w-full sm:w-auto px-5 py-3.5 rounded-xl bg-[#101b30] border border-[#233554] hover:border-teal-400/40 text-slate-200 hover:text-white flex items-center justify-center gap-2 text-sm font-medium transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    type="button"
                  >
                    <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span>Browse Files</span>
                  </button>
                </div>

                {/* Natural Language Query Bar */}
                <form onSubmit={handleQuerySubmit} className="mt-4 flex items-center gap-2 bg-[#060c18] border border-[#1b2c4c] rounded-xl px-4 py-2.5 focus-within:border-teal-500/80 focus-within:ring-1 focus-within:ring-teal-500/30 transition-all">
                  <svg className="w-4 h-4 text-teal-400 shrink-0" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4L12 2z" />
                  </svg>
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    disabled={isUploading || isSubmitting}
                    className="bg-transparent border-none text-slate-200 placeholder-slate-400 text-sm w-full focus:outline-none focus:ring-0 p-0 disabled:opacity-50"
                    placeholder="Ask a question about your imagery..."
                    type="text"
                  />
                  <button
                    type="submit"
                    disabled={isUploading || isSubmitting || !query.trim()}
                    className="p-2 rounded-lg bg-[#00d5be] text-slate-950 hover:bg-[#00f2fe] transition-all font-semibold shrink-0 shadow-md shadow-teal-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center w-8 h-8"
                    title="Submit query"
                  >
                    {isSubmitting ? (
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </button>
                </form>
              </div>

              {/* Quick Prompts Row */}
              <div className="flex flex-wrap items-center gap-2 mt-4 text-xs">
                <span className="text-slate-400 font-medium mr-1">Try asking:</span>
                <button
                  onClick={() => handleQuickPrompt("Describe this scene")}
                  className="px-3 py-1 rounded-full bg-[#0d172a] border border-[#1b2b48] text-slate-300 hover:border-teal-400/50 hover:text-teal-300 transition-colors"
                  type="button"
                >
                  Describe this scene
                </button>
                <button
                  onClick={() => handleQuickPrompt("Highlight the water body in the image")}
                  className="px-3 py-1 rounded-full bg-[#0d172a] border border-[#1b2b48] text-slate-300 hover:border-teal-400/50 hover:text-teal-300 transition-colors"
                  type="button"
                >
                  Highlight the water body
                </button>
                <button
                  onClick={() => handleQuickPrompt("What changed between these dates?")}
                  className="px-3 py-1 rounded-full bg-[#0d172a] border border-[#1b2b48] text-slate-300 hover:border-teal-400/50 hover:text-teal-300 transition-colors"
                  type="button"
                >
                  What changed between these dates?
                </button>
                <button
                  onClick={() => handleQuickPrompt("Use optical and SAR together for analysis")}
                  className="px-3 py-1 rounded-full bg-[#0d172a] border border-[#1b2b48] text-slate-300 hover:border-teal-400/50 hover:text-teal-300 transition-colors"
                  type="button"
                >
                  Use optical and SAR together
                </button>
              </div>
            </div>

            {/* Right Hero Floating Satellite Analytics Preview */}
            <div className="relative w-full lg:w-[480px] shrink-0 hidden md:block">
              {/* Optical + SAR Comparison Pill Floating Container */}
              <div className="bg-[#0b1424]/90 border border-[#1e2f4f] backdrop-blur-md rounded-2xl p-3.5 shadow-xl mb-4">
                <div className="flex items-center gap-3 justify-center">
                  {/* Optical Preview Box */}
                  <div className="relative w-36 h-24 rounded-lg overflow-hidden border border-teal-500/40 bg-slate-900 group">
                    <img
                      alt="Optical satellite imagery"
                      className="w-full h-full object-cover scale-[2.2] object-top contrast-125"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuD1hS1hH89YqsbwG0KdMrp51ez_5hcxUhWTae6DNhBmfj4ffLgOvc4S7xIpljGic3ROODyWCpo7YLQzj5rFKrc5TfIhHTeJJkOEqjGQGV8sKvbGZpQMjvG_EHmZ-5eDYxZqPCqyPISHEtzaVpVt09G79IWPnvarfmHlK-wNzETxlGRAbGNPQJuZKUYwrkHw6EI-31SkPESHuTU8hrRPItTLmCVT4CfHJ0-UX4rk_ltrIc1SNTHt-Lg2KVIJ_ko3JKyr"
                    />
                    <span className="absolute bottom-1.5 left-2 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur-sm text-[10px] font-semibold text-slate-200">Optical</span>
                  </div>
                  {/* Plus icon separator */}
                  <div className="text-slate-400 font-bold text-lg">+</div>
                  {/* SAR Preview Box */}
                  <div className="relative w-36 h-24 rounded-lg overflow-hidden border border-slate-700 bg-slate-900 group">
                    <img
                      alt="SAR radar imagery"
                      className="w-full h-full object-cover grayscale contrast-200 scale-[2.2] object-right"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuAyXwBIkCAFP5wB6DbnmxWjG7ZrADP3kztslmRY1KkfBHUPpGWFSHcgYJ6_-3aE3cRsykFRn6B0cJ6wuWwwcZs9T16B8WOHE_SyegEK6eqtluBJJe0vOf42OU8wTaljsKD7ZRfqe47TByWsSMWlwJwqXeel_3YnVm8o-seY6njTnyG_WkJJ3NrzVdEJRuOOIbHvtWHe8o-35GPzzzZDDER7vuvsckfjCvt0DYUYan1XyNrYTYjNSh48j0nbNA1LCEwT"
                    />
                    <span className="absolute bottom-1.5 left-2 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur-sm text-[10px] font-semibold text-slate-200">SAR</span>
                  </div>
                </div>
              </div>

              {/* Detection Bounding Target & Layer Tags Container */}
              <div className="relative flex items-start justify-between gap-4">
                {/* Dotted bounding box over Earth landscape */}
                <div className="relative w-44 h-36 border-2 border-dashed border-teal-400/80 rounded-xl bg-teal-500/5 backdrop-blur-[1px] p-2 flex flex-col justify-between">
                  <span className="self-start text-[9px] font-bold px-1.5 py-0.5 rounded bg-teal-500 text-slate-950 uppercase tracking-wider">ROI Target</span>
                  <div className="flex items-center gap-1.5 self-end px-2 py-1 rounded bg-[#091322]/90 border border-teal-400/50 text-[10px] text-teal-300 font-medium shadow-lg">
                    <svg className="w-3 h-3 text-teal-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M4 7V4h3m10 0h3v3m0 10v3h-3M7 20H4v-3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span>AI detects changes</span>
                  </div>
                </div>

                {/* Vertical Classification Pills */}
                <div className="flex flex-col gap-2 shrink-0">
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0b1526]/90 border border-[#1b2b48] text-xs font-medium text-slate-200 shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span>Land Cover</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0b1526]/90 border border-[#1b2b48] text-xs font-medium text-slate-200 shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-sky-400" />
                    <span>Water Bodies</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0b1526]/90 border border-[#1b2b48] text-xs font-medium text-slate-200 shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span>Built-up Areas</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0b1526]/90 border border-[#1b2b48] text-xs font-medium text-slate-200 shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-rose-400" />
                    <span>Change Detection</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid Section */}
        <section className="px-8 py-8 border-b border-[#141e30]" data-purpose="features-showcase">
          <div className="max-w-7xl mx-auto">
            {/* Section Title & Link */}
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-white tracking-tight">What can you do with SatQuery AI?</h2>
              <Link href="/analysis" className="text-xs font-medium text-[#00d5be] hover:text-[#00f2fe] flex items-center gap-1 transition-colors">
                <span>Explore all features</span>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
            </div>

            {/* 4 Feature Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Card 1: Single Image Analysis */}
              <Link
                href="/analysis?tool=vqa"
                className="bg-[#091120] border border-[#192742] hover:border-teal-500/40 rounded-xl p-3.5 flex flex-col justify-between transition-all hover:-translate-y-0.5 group"
              >
                <div>
                  <div className="h-28 w-full rounded-lg overflow-hidden mb-3.5 relative bg-slate-900">
                    <img
                      alt="Single Image Analysis preview"
                      className="w-full h-full object-cover scale-[2.5] object-center group-hover:scale-[2.6] transition-transform duration-300"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuA484pOnfeDELf_4y67ntdWCmOkfQ29rzml1fWDKyJco_2R2kYQY0IZV0uTckNun1QdfEht8Y_40sxpvr_CPZHjIRUobqxjNScT5oD0o6164IPV8DNlAkDYWrvFPQPKt6WpvfpM28hZE0k6MqTg1NIbvuqNd8bywOIrlKvvGmwLNAwMD7MCAbhvw5z5GI4aDUeEt0UPwxpyTfLo8jmxvQVCgTED7EUwBqPuNdtske7P6zKQnxRKs0rorfcOgOtr_zAa"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#091120] via-transparent to-transparent opacity-60" />
                  </div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-teal-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <h3 className="text-sm font-semibold text-white">Single Image Analysis</h3>
                    </div>
                    <div className="w-6 h-6 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-400 group-hover:text-teal-300 group-hover:bg-slate-700/80 transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">Ask questions, get descriptions, find regions and more.</p>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[#141f33]">
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">VQA</span>
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Captioning</span>
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Grounding</span>
                </div>
              </Link>

              {/* Card 2: Optical + SAR Fusion */}
              <Link
                href="/analysis?tool=fusion"
                className="bg-[#091120] border border-[#192742] hover:border-teal-500/40 rounded-xl p-3.5 flex flex-col justify-between transition-all hover:-translate-y-0.5 group"
              >
                <div>
                  <div className="h-28 w-full rounded-lg overflow-hidden mb-3.5 relative bg-slate-900">
                    <img
                      alt="Optical SAR Fusion preview"
                      className="w-full h-full object-cover scale-[2.7] object-top group-hover:scale-[2.8] transition-transform duration-300"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuCHe-JINOUV1q-IZzPzi0fKnUItljYiA17FLkcnUwweMOqDyFrwDzrzDzxzCr32H8FCjw11nbbTphiiUxwjp8I0fexgznu3ngVHgmSEKu4rnCQIrei5CE4fDlthxoxuRgEIANHG4QAxGx80XFjWoIGq0VIlzBTSrqTkOLgEqJeQsfsgWNf_p6-AnjVb0E568F2xcW6cscpsM-SWgWJKvwgisVUmExsiK5iiZdtos7xHhz0mNSeYbwFfKlQQHOFhGBDW"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#091120] via-transparent to-transparent opacity-60" />
                  </div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-teal-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <polygon points="12 2 2 7 12 12 22 7 12 2" />
                        <polyline points="2 17 12 22 22 17" />
                        <polyline points="2 12 12 17 22 12" />
                      </svg>
                      <h3 className="text-sm font-semibold text-white">Optical + SAR Fusion</h3>
                    </div>
                    <div className="w-6 h-6 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-400 group-hover:text-teal-300 group-hover:bg-slate-700/80 transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">Combine multi-sensor data for richer, more reliable insights.</p>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[#141f33]">
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Cross-Modal</span>
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Information Extraction</span>
                </div>
              </Link>

              {/* Card 3: Bi-temporal Change Analysis */}
              <Link
                href="/analysis?tool=change"
                className="bg-[#091120] border border-[#192742] hover:border-teal-500/40 rounded-xl p-3.5 flex flex-col justify-between transition-all hover:-translate-y-0.5 group"
              >
                <div>
                  <div className="h-28 w-full rounded-lg overflow-hidden mb-3.5 relative bg-slate-900">
                    <img
                      alt="Bi-temporal Change Analysis"
                      className="w-full h-full object-cover scale-[2.9] object-center group-hover:scale-[3.0] transition-transform duration-300"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuCHJvu4nRtRtapN9lJTOQiCnBQ0jQu_C8wxtFAqXqH9O8m2FbfD0-K1eJ3nzNPlVLhvHDOT2YiWkuPoCyTlYZ5KV1f_ajmPTdOMJ9bK2CxwNdc1svtMOmUWRkk_mmmrMme7cHmcAGF0mIsZpxEmXLdHGMcraoHFYmSAxz3lZPgqs4re9fpzI1TonRyOg5V-yn2TKI9cmsHV55sVyEx0B2AN0PljLFRlIA6sI6dBD4is90JIOCsR5TTes7lua8RlvVwF"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#091120] via-transparent to-transparent opacity-60" />
                  </div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-teal-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <h3 className="text-sm font-semibold text-white">Bi-temporal Change Analysis</h3>
                    </div>
                    <div className="w-6 h-6 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-400 group-hover:text-teal-300 group-hover:bg-slate-700/80 transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">Detect and understand changes over time.</p>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[#141f33]">
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Change Detection</span>
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Change VQA</span>
                </div>
              </Link>

              {/* Card 4: Agentic Model Orchestration */}
              <Link
                href="/analysis"
                className="bg-[#091120] border border-[#192742] hover:border-teal-500/40 rounded-xl p-3.5 flex flex-col justify-between transition-all hover:-translate-y-0.5 group"
              >
                <div>
                  <div className="h-28 w-full rounded-lg overflow-hidden mb-3.5 relative bg-gradient-to-tr from-cyan-950 via-slate-900 to-blue-950 flex items-center justify-center">
                    <div className="w-12 h-12 rounded-full bg-teal-500/20 border border-teal-400/50 flex items-center justify-center animate-pulse">
                      <svg className="w-6 h-6 text-teal-300" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <rect height="16" rx="2" width="16" x="4" y="4" />
                        <path d="M9 9h6v6H9zM9 1v3m6-3v3M9 20v3m6-3v3M20 9h3m-3 6h3M1 9h3m-3 6h3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <div className="absolute inset-0 bg-[radial-gradient(#00d5be_1px,transparent_1px)] [background-size:10px_10px] opacity-25" />
                  </div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-teal-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="3" />
                        <path d="M12 2v3m0 14v3M2 12h3m14 0h3" strokeLinecap="round" strokeWidth="2" />
                      </svg>
                      <h3 className="text-sm font-semibold text-white">Agentic Model Orchestration</h3>
                    </div>
                    <div className="w-6 h-6 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-400 group-hover:text-teal-300 group-hover:bg-slate-700/80 transition-colors">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">Automatically selects the right models, validates inputs and returns evidence.</p>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[#141f33]">
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Smart Routing</span>
                  <span className="px-2 py-0.5 rounded bg-[#101b30] text-[10px] font-medium text-slate-400">Execution Trace</span>
                </div>
              </Link>
            </div>
          </div>
        </section>

        {/* Recent Analyses Section */}
        <section className="px-8 py-8" data-purpose="recent-activities">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="9" />
                  <polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <h2 className="text-base font-bold text-white tracking-tight">Recent Analyses</h2>
              </div>
              <Link href="/history" className="text-xs font-medium text-[#00d5be] hover:text-[#00f2fe] flex items-center gap-1 transition-colors">
                <span>View all</span>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
            </div>

            {/* 4 Recent Activity Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Item 1 */}
              <Link
                href="/history"
                className="bg-[#091120] border border-[#17253d] hover:border-teal-500/30 rounded-xl p-3 flex items-center gap-3 transition-all hover:bg-[#0c1527] cursor-pointer"
              >
                <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-slate-900">
                  <img
                    alt="Urban Expansion Analysis"
                    className="w-full h-full object-cover scale-[3.5] object-bottom"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuCnr6Hf5AuFazIFhbmD_t7DQlPxM22OCoNCt1mN08gu8mFDignS-myqLVvAXG9PnIqPvw5UPeE5f78_Oz2Hx9T-CcAooTv01AViQBnIEx_RaelKpo45Xec6QnieWMlENui7lVuROBx67IAf2RN57OOb5rPhhLrWogIBGds7CM6tRoeeN6DJn-8S3zIufUbRI6KMBHQqOXPG8sDQRkP3bj7UtAQ96MayjiAwFhalyUOVGXmV8ehtb2WM_MTnbmwq7ZyW"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-white truncate">Urban Expansion Analysis</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-1.5 py-0.2 rounded bg-teal-500/10 text-[9px] font-medium text-teal-300 border border-teal-500/20">Change Analysis</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 truncate">2 images • 12 Oct 2025, 11:42 AM</p>
                </div>
                <button className="text-slate-400 hover:text-white p-1" title="Options" type="button" onClick={(e) => e.preventDefault()}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="1" /><circle cx="12" cy="5" r="1" /><circle cx="12" cy="19" r="1" />
                  </svg>
                </button>
              </Link>

              {/* Item 2 */}
              <Link
                href="/history"
                className="bg-[#091120] border border-[#17253d] hover:border-teal-500/30 rounded-xl p-3 flex items-center gap-3 transition-all hover:bg-[#0c1527] cursor-pointer"
              >
                <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-slate-900">
                  <img
                    alt="River Detection"
                    className="w-full h-full object-cover scale-[3.2] object-left"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuBY-SSY1JxU3dcTxAnqXUCNPGHbUGv7pigKTBrNsKF7GWoRN-iLqDkPgXrFQhxnA9wvWfNuBEvrbw3sfrf08NLbsp7swyQKCIjIf7UROj-_znX2UV43EUf16tuAmDnVfjHXN9dNY1Tc23iInMWNLc2QjX72z9GFuElSGzDA9jQj5kyUw5VzPDqWWx-7Ja1UQVPdGU0lGInCSb1mfIwQswnqzzDmM2Wp8GlA9QoJX-CrndfWVMRYtoh1e5z9kvHKTI3p"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-white truncate">River Detection</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-1.5 py-0.2 rounded bg-teal-500/10 text-[9px] font-medium text-teal-300 border border-teal-500/20">VQA</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 truncate">1 image • 11 Oct 2025, 04:21 PM</p>
                </div>
                <button className="text-slate-400 hover:text-white p-1" title="Options" type="button" onClick={(e) => e.preventDefault()}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="1" /><circle cx="12" cy="5" r="1" /><circle cx="12" cy="19" r="1" />
                  </svg>
                </button>
              </Link>

              {/* Item 3 */}
              <Link
                href="/history"
                className="bg-[#091120] border border-[#17253d] hover:border-teal-500/30 rounded-xl p-3 flex items-center gap-3 transition-all hover:bg-[#0c1527] cursor-pointer"
              >
                <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-slate-900">
                  <img
                    alt="Optical + SAR Fusion"
                    className="w-full h-full object-cover scale-[2.8] object-center"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAN0v0RhlwoMFsAuso5rJgyMSAci3SzBCDNIH0tT6A2wQ8UhglSVSA34j_TTfsPkI0K4HNYiSaWUErQ29QgBcdMjRx4VTyBq-ZWMkhVX9mCNYDGlJG8JSS_v4bnQSMrA_43NxtiLFqwtlGNOTTT59vilh86HNfE-T-hLd9Wy5nWgQg4wTMcMEvEzL_7ifpiCy5hCyaH5GpZ_FwhMCmKqsjUtvIoUm4K4du-FMBJF6VjNK9Lu2Xdn5-8oeJsG55rDI0X"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-white truncate">Optical + SAR Fusion</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-1.5 py-0.2 rounded bg-teal-500/10 text-[9px] font-medium text-teal-300 border border-teal-500/20">Cross-Modal</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 truncate">2 images • 10 Oct 2025, 09:16 AM</p>
                </div>
                <button className="text-slate-400 hover:text-white p-1" title="Options" type="button" onClick={(e) => e.preventDefault()}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="1" /><circle cx="12" cy="5" r="1" /><circle cx="12" cy="19" r="1" />
                  </svg>
                </button>
              </Link>

              {/* Item 4 */}
              <Link
                href="/history"
                className="bg-[#091120] border border-[#17253d] hover:border-teal-500/30 rounded-xl p-3 flex items-center gap-3 transition-all hover:bg-[#0c1527] cursor-pointer"
              >
                <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-slate-900">
                  <img
                    alt="Forest Monitoring"
                    className="w-full h-full object-cover scale-[3.4] object-right"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAGbD0Frbs3Qt7sz6ESmQlFEsyCNM_f_gro_vHkQYKjiIL3dsbb6-gjgsly7Dn_krZneXIEZj8F0SWMkiP7_4kRg0nxMa8mZCaodUhb7JA_4yaKmYbPATUnGyehZstaPCGoPJnLsPMidpDc-lKo4gr6_Pmz9h8WJ9pL57hTY7YFW7LOgF14nKhuQg1uxPW3MsfwCjGcjbE9SQbSRvMXqGA60Pk2l5xrnF-6zdEhiCVMmua_6_AplANmWWZIuOxA555E"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-white truncate">Forest Monitoring</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-1.5 py-0.2 rounded bg-teal-500/10 text-[9px] font-medium text-teal-300 border border-teal-500/20">VQA</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 truncate">1 image • 09 Oct 2025, 02:33 PM</p>
                </div>
                <button className="text-slate-400 hover:text-white p-1" title="Options" type="button" onClick={(e) => e.preventDefault()}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="1" /><circle cx="12" cy="5" r="1" /><circle cx="12" cy="19" r="1" />
                  </svg>
                </button>
              </Link>
            </div>
          </div>
        </section>
        </main>
      </div>
    </>
  );
}
