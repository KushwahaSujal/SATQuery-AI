"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useTheme } from "@/providers";

interface TopBarProps {
  showBrand?: boolean;
  searchPlaceholder?: string;
  className?: string;
  onSearch?: (query: string) => void;
}

export default function TopBar({
  showBrand = false,
  searchPlaceholder = 'Search anything… e.g. "urban expansion in Delhi"',
  className = "",
  onSearch,
}: TopBarProps) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const { mode, setMode } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    refetchInterval: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const isOnline = health?.api === "online";
  const modelsReady = health?.models_ready ?? 0;
  const modelsTotal = health?.models_total ?? 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && onSearch) onSearch(query);
  };

  return (
    <motion.header
      initial={{ y: -8, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
      className={`h-14 border-b border-[var(--border)] bg-[var(--topbar-bg)]/90 backdrop-blur-md px-5 flex items-center justify-between sticky top-0 z-30 shrink-0 gap-4 ${className}`}
      data-purpose="topbar"
    >
      {/* Optional Brand */}
      {showBrand && (
        <div className="flex items-center gap-3 w-56 shrink-0">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center shrink-0 group-hover:border-[var(--border-strong)] transition-colors">
              <img
                  src="/satquery.svg"
                  alt="SatQuery AI"
                  className="w-6 h-6 rounded-md object-cover"
              />
            </div>
            <div>
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-base font-bold text-[var(--heading)] tracking-tight group-hover:text-[var(--primary)] transition-colors">SatQuery</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[var(--primary-glow)] text-[var(--primary)] border border-[var(--primary)]/30">AI</span>
              </div>
              <p className="text-[9px] text-[var(--text-3)] font-medium tracking-wide mt-0.5">Remote Sensing · Vision</p>
            </div>
          </Link>
        </div>
      )}

      {/* Search bar */}
      {/*<div*/}
      {/*  className={`relative flex-1 max-w-xl transition-all duration-200 ${focused ? "max-w-2xl" : ""}`}*/}
      {/*>*/}
      {/*  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-3)]">*/}
      {/*    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">*/}
      {/*      <circle cx="11" cy="11" r="8" />*/}
      {/*      <line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" />*/}
      {/*    </svg>*/}
      {/*  </div>*/}
      {/*  <input*/}
      {/*    value={query}*/}
      {/*    onChange={(e) => setQuery(e.target.value)}*/}
      {/*    onKeyDown={handleKeyDown}*/}
      {/*    onFocus={() => setFocused(true)}*/}
      {/*    onBlur={() => setFocused(false)}*/}
      {/*    className={`w-full pl-9 pr-10 py-2 bg-[var(--input-bg)] border rounded-lg text-xs text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none transition-all duration-200 ${*/}
      {/*      focused*/}
      {/*        ? "border-[var(--cyan)]/60 ring-1 ring-[var(--cyan)]/20 shadow-[0_0_16px_rgba(0,199,217,0.08)]"*/}
      {/*        : "border-[var(--input-border)] hover:border-[var(--border-strong)]"*/}
      {/*    }`}*/}
      {/*    placeholder={searchPlaceholder}*/}
      {/*    type="text"*/}
      {/*  />*/}
      {/*  <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">*/}
      {/*    <kbd className="px-1.5 py-0.5 text-[9px] font-mono text-[var(--text-3)] bg-[var(--kbd-bg)] border border-[var(--border)] rounded flex items-center gap-0.5 opacity-60">*/}
      {/*      <span>⌘</span><span>K</span>*/}
      {/*    </kbd>*/}
      {/*  </div>*/}
      {/*</div>*/}

      {/* Right Controls */}
      <div className="flex items-center gap-3 ml-auto shrink-0">
        {/* AI Ready Indicator */}
        <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${
          isOnline
            ? "bg-[var(--green-bg)] border-[var(--green)]/30"
            : "bg-[var(--amber-bg)] border-[var(--warning)]/30"
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-[var(--green)]" : "bg-[var(--warning)]"}`} />
          <span className={`text-[10px] font-medium ${isOnline ? "text-[var(--green)]" : "text-[var(--warning)]"}`}>
            {isOnline
              ? `AI Ready${modelsTotal > 0 ? ` · ${modelsReady}/${modelsTotal}` : ""}`
              : "Backend offline"}
          </span>
        </div>

        {/* Theme Toggle */}
        <div className="flex items-center bg-[var(--surface-2)] border border-[var(--border)] rounded-full p-0.5">
          <button
            onClick={() => setMode("light")}
            className={`p-1.5 rounded-full transition-all duration-150 ${
              mounted && mode === "light"
                ? "bg-[var(--surface-3)] text-[var(--amber)] shadow-sm"
                : "text-[var(--text-3)] hover:text-[var(--heading)]"
            }`}
            title="Light theme"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" strokeLinecap="round" />
            </svg>
          </button>
          <button
            onClick={() => setMode("dark")}
            className={`p-1.5 rounded-full transition-all duration-150 ${
              mounted && mode === "dark"
                ? "bg-[var(--surface-3)] text-[var(--accent)] shadow-sm"
                : "text-[var(--text-3)] hover:text-[var(--heading)]"
            }`}
            title="Dark theme"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
            </svg>
          </button>
        </div>
      </div>
    </motion.header>
  );
}

export { TopBar };
