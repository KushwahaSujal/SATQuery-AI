"use client";

import { useRouter } from "next/navigation";
import { useCommandPalette } from "./CommandPaletteContext";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type CommandItem = {
  id: string;
  group: string;
  label: string;
  description?: string;
  shortcut?: string;
  action: () => void;
};

export default function CommandPalette() {
  const { isOpen, setIsOpen } = useCommandPalette();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);

  const navigate = (path: string) => {
    router.push(path);
    setIsOpen(false);
    setQuery("");
  };

  const allItems: CommandItem[] = [
    {
      id: "cmd-center",
      group: "Navigation",
      label: "Command Center",
      description: "Upload data and run queries",
      action: () => navigate("/"),
    },
    {
      id: "jobs",
      group: "Navigation",
      label: "Jobs",
      description: "Analysis execution history",
      action: () => navigate("/jobs"),
    },
    {
      id: "models",
      group: "Navigation",
      label: "Model Observatory",
      description: "Model registry and lifecycle",
      action: () => navigate("/models"),
    },
    {
      id: "system",
      group: "Navigation",
      label: "System Diagnostics",
      description: "API, database, storage health",
      action: () => navigate("/system"),
    },
  ];

  const filtered = query.trim()
    ? allItems.filter(
        (item) =>
          item.label.toLowerCase().includes(query.toLowerCase()) ||
          item.description?.toLowerCase().includes(query.toLowerCase()),
      )
    : allItems;

  useEffect(() => {
    if (isOpen) {
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, filtered.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter") {
        e.preventDefault();
        filtered[activeIdx]?.action();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, filtered, activeIdx]);

  if (!isOpen) return null;

  // Group items
  const groups: Record<string, CommandItem[]> = {};
  for (const item of filtered) {
    if (!groups[item.group]) groups[item.group] = [];
    groups[item.group].push(item);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[18vh]"
      onClick={() => setIsOpen(false)}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Panel */}
      <div
        className="relative w-full max-w-120 rounded-xl border border-[#222] bg-[#0f0f0f] shadow-2xl animate-slide-down overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-2.5 px-4 border-b border-[#1a1a1a]">
          <svg
            className="w-3.5 h-3.5 text-[#404040] shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIdx(0);
            }}
            placeholder="Search workspace..."
            className="w-full bg-transparent py-3 font-mono-data text-[13px] text-[#fafafa] placeholder:text-[#333] outline-none"
          />
          <kbd className="shrink-0 bg-[#161616] border border-[#222] rounded px-1.5 py-0.5 font-mono-data text-[10px] text-[#404040]">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="py-1.5 max-h-72 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-center font-mono-data text-[12px] text-[#333]">
              No results for "{query}"
            </p>
          ) : (
            Object.entries(groups).map(([group, items]) => (
              <div key={group}>
                <div className="px-4 pt-2.5 pb-1 font-mono-data text-[10px] font-medium tracking-[0.08em] uppercase text-[#333]">
                  {group}
                </div>
                {items.map((item) => {
                  const globalIdx = filtered.indexOf(item);
                  return (
                    <button
                      key={item.id}
                      onMouseEnter={() => setActiveIdx(globalIdx)}
                      onClick={item.action}
                      className={cn(
                        "w-full flex items-center justify-between gap-3 px-4 py-2 text-left transition-none",
                        activeIdx === globalIdx ? "bg-[#161616]" : "",
                      )}
                    >
                      <div>
                        <div className="text-[13px] text-[#e5e5e5]">
                          {item.label}
                        </div>
                        {item.description && (
                          <div className="font-mono-data text-[11px] text-[#404040] mt-0.5">
                            {item.description}
                          </div>
                        )}
                      </div>
                      {item.shortcut && (
                        <kbd className="shrink-0 bg-[#111] border border-[#1e1e1e] rounded px-1.5 py-0.5 font-mono-data text-[10px] text-[#404040]">
                          {item.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-[#1a1a1a] font-mono-data text-[10px] text-[#2a2a2a]">
          <span>
            <kbd className="text-[#333]">↑↓</kbd> navigate
          </span>
          <span>
            <kbd className="text-[#333]">↵</kbd> open
          </span>
          <span>
            <kbd className="text-[#333]">ESC</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}
