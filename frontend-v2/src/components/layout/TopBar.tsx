"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import Link from "next/link";

interface TopBarProps {
  showBrand?: boolean;
  searchPlaceholder?: string;
  className?: string;
  onSearch?: (query: string) => void;
}

export default function TopBar({
  showBrand = false,
  searchPlaceholder = 'Search anything... (e.g. "urban expansion in Delhi")',
  className = "",
  onSearch,
}: TopBarProps) {
  const [query, setQuery] = useState("");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && onSearch) {
      onSearch(query);
    }
  };

  return (
    <header
      className={`h-16 border-b border-[#162033] bg-[#070d18]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30 shrink-0 ${className}`}
      data-purpose="topbar"
    >
      {/* Optional Brand Logo for top-spanning layouts */}
      {showBrand ? (
        <div className="flex items-center gap-3 w-64 shrink-0">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#00d5be] to-[#0077b6] flex items-center justify-center shadow-lg shadow-teal-500/20 text-slate-950 font-bold shrink-0">
              <svg className="w-5 h-5 text-slate-950" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="2" x2="12" y2="6" />
                <line x1="12" y1="18" x2="12" y2="22" />
                <line x1="2" y1="12" x2="6" y2="12" />
                <line x1="18" y1="12" x2="22" y2="12" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-lg font-bold text-white tracking-tight group-hover:text-cyan-300 transition-colors">SatQuery</span>
                <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-teal-500/20 text-[#00d5be] border border-teal-500/30">AI</span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium tracking-wide mt-1">Remote Sensing · Vision · Intelligence</p>
            </div>
          </Link>
        </div>
      ) : null}

      {/* Central Search Input */}
      <div className="relative w-full max-w-xl">
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full pl-10 pr-12 py-2 bg-[#0c1424] border border-[#1d2a44] rounded-lg text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-teal-500/60 focus:ring-1 focus:ring-teal-500/40 transition-all"
          placeholder={searchPlaceholder}
          type="text"
        />
        <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">
          <kbd className="px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-[#142036] border border-[#233352] rounded shadow-sm flex items-center gap-0.5">
            <span>⌘</span><span>K</span>
          </kbd>
        </div>
      </div>

      {/* Right Controls: Theme Toggle, Notifications, User Profile */}
      <div className="flex items-center gap-4 ml-4 shrink-0">
        {/* Sun / Moon Toggle */}
        <div className="flex items-center bg-[#0c1424] border border-[#1d2a44] rounded-full p-1 text-slate-400">
          <button
            onClick={() => setTheme("light")}
            className={`p-1 rounded-full transition-colors ${
              mounted && theme === "light" ? "bg-[#1b273d] text-amber-300 shadow-sm" : "text-slate-400 hover:text-white"
            }`}
            title="Light theme"
            type="button"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button
            onClick={() => setTheme("dark")}
            className={`p-1 rounded-full transition-colors ${
              mounted && theme !== "light" ? "bg-[#1b273d] text-teal-300 shadow-sm" : "text-slate-400 hover:text-white"
            }`}
            title="Dark theme active"
            type="button"
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
            </svg>
          </button>
        </div>

        {/* Notification Bell with Counter */}
        <button
          className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-[#0e172a] transition-all"
          type="button"
          aria-label="Notifications"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[9px] font-bold flex items-center justify-center border-2 border-[#070d18]">
            1
          </span>
        </button>

        {/* Profile / Account Menu */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-[#1b263b] cursor-pointer group">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-700 via-blue-600 to-indigo-600 border border-cyan-500/40 flex items-center justify-center text-xs font-semibold text-white shadow-inner">
            SM
          </div>
          <span className="text-xs font-medium text-slate-200 group-hover:text-teal-300 transition-colors hidden sm:inline-block">
            Sandipan Majumder
          </span>
          <svg className="w-3.5 h-3.5 text-slate-400 group-hover:text-white transition-colors" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    </header>
  );
}

export { TopBar };
