"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";

export default function TopBar() {
  const [query, setQuery] = useState("");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <header
      className="h-16 border-b px-6 flex items-center justify-between sticky top-0 z-30"
      style={{
        background: "var(--topbar-bg)",
        borderColor: "var(--border)",
        backdropFilter: "blur(8px)",
      }}
    >
      {/* Search */}
      <div className="relative w-full max-w-xl">
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none" style={{ color: "var(--text-2)" }}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" /><line x1="21" x2="16.65" y1="21" y2="16.65" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-10 pr-12 py-2 rounded-lg text-sm focus:outline-none transition-all"
          style={{
            background: "var(--input-bg)",
            border: "1px solid var(--input-border)",
            color: "var(--heading)",
          }}
          placeholder='Search anything... (e.g. "urban expansion in Delhi")'
        />
        <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center">
          <kbd
            className="px-2 py-0.5 text-[10px] font-mono rounded shadow-sm flex items-center gap-0.5"
            style={{ background: "var(--kbd-bg)", border: "1px solid var(--border)", color: "var(--text-2)" }}
          >
            <span>&#8984;</span><span>K</span>
          </kbd>
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-4 ml-4 shrink-0">
        {/* Theme toggle */}
        <div
          className="flex items-center rounded-full p-1"
          style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)" }}
        >
          <button
            onClick={() => setTheme("light")}
            className="p-1 rounded-full transition-colors"
            style={{ color: mounted && theme === "light" ? "var(--primary)" : "var(--text-3)" }}
            suppressHydrationWarning
            title="Light theme"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button
            onClick={() => setTheme("dark")}
            className="p-1 rounded-full transition-colors"
            style={{
              background: mounted && theme === "dark" ? "var(--surface-3)" : "transparent",
              color: mounted && theme === "dark" ? "var(--cyan)" : "var(--text-3)",
            }}
            suppressHydrationWarning
            title="Dark theme"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
            </svg>
          </button>
        </div>

        {/* Notifications */}
        <button
          className="relative p-2 rounded-lg transition-all"
          style={{ color: "var(--text-2)" }}
          type="button"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span
            className="absolute top-1 right-1 w-4 h-4 text-white rounded-full text-[9px] font-bold flex items-center justify-center"
            style={{ background: "var(--error)", border: "2px solid var(--topbar-bg)" }}
          >1</span>
        </button>

        {/* Profile */}
        <div className="flex items-center gap-2.5 pl-2 cursor-pointer group" style={{ borderLeft: "1px solid var(--border)" }}>
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white"
            style={{ background: "var(--surface-3)", border: "1px solid var(--border-strong)" }}
          >SM</div>
          <span className="text-sm font-medium hidden sm:inline-block transition-colors" style={{ color: "var(--text)" }}>Sandipan Majumder</span>
          <svg className="w-3.5 h-3.5 transition-colors" style={{ color: "var(--text-3)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <polyline points="6 9 12 15 18 9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    </header>
  );
}
