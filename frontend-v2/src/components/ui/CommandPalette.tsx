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

  // Routes this app actually has. The original list was written against the old
  // frontend and pointed at /jobs, which does not exist in this app -- v2 splits that
  // into /history and /reports.
  const allItems: CommandItem[] = [
    {
      id: "home",
      group: "Navigation",
      label: "Home",
      description: "Overview and recent analyses",
      action: () => navigate("/"),
    },
    {
      id: "analysis",
      group: "Navigation",
      label: "New Analysis",
      description: "Upload imagery or video and run a query",
      action: () => navigate("/analysis"),
    },
    {
      id: "history",
      group: "Navigation",
      label: "History",
      description: "Every analysis run, with execution traces",
      action: () => navigate("/history"),
    },
    {
      id: "reports",
      group: "Navigation",
      label: "Reports",
      description: "Completed analyses and downloads",
      action: () => navigate("/reports"),
    },
    {
      id: "datasets",
      group: "Navigation",
      label: "Sample Data",
      description: "Demo imagery and video bundled with the repo",
      action: () => navigate("/datasets"),
    },
    {
      id: "documentation",
      group: "Navigation",
      label: "Documentation",
      description: "Repository docs, rendered live",
      action: () => navigate("/documentation"),
    },
    {
      id: "models",
      group: "Diagnostics",
      label: "Model Registry",
      description: "Model lifecycle, checkpoints and refusal reasons",
      action: () => navigate("/models"),
    },
    {
      id: "system",
      group: "Diagnostics",
      label: "System Diagnostics",
      description: "API reachability, database and device",
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
      <div className="absolute inset-0" style={{ background: "var(--scrim)" }} />

      <div
        className="relative w-full max-w-120 rounded-xl animate-slide-down overflow-hidden"
        style={{ border: "1px solid var(--border-strong)", background: "var(--surface-2)", boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 px-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <svg
            className="w-3.5 h-3.5 shrink-0"
            style={{ color: "var(--text-3)" }}
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
            className="w-full bg-transparent py-3 font-mono-data text-[13px] outline-none"
            style={{ color: "var(--heading)" }}
          />
          <kbd
            className="shrink-0 rounded px-1.5 py-0.5 font-mono-data text-[10px]"
            style={{ background: "var(--surface-3)", border: "1px solid var(--border)", color: "var(--text-3)" }}
          >ESC</kbd>
        </div>

        <div className="py-1.5 max-h-72 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-center font-mono-data text-[12px]" style={{ color: "var(--text-3)" }}>
              No results for &ldquo;{query}&rdquo;
            </p>
          ) : (
            Object.entries(groups).map(([group, items]) => (
              <div key={group}>
                <div
                  className="px-4 pt-2.5 pb-1 font-mono-data text-[10px] font-medium tracking-[0.08em] uppercase"
                  style={{ color: "var(--text-3)" }}
                >{group}</div>
                {items.map((item) => {
                  const globalIdx = filtered.indexOf(item);
                  return (
                    <button
                      key={item.id}
                      onMouseEnter={() => setActiveIdx(globalIdx)}
                      onClick={item.action}
                      className={cn(
                        "w-full flex items-center justify-between gap-3 px-4 py-2 text-left transition-none",
                      )}
                      style={activeIdx === globalIdx ? { background: "var(--surface-3)" } : undefined}
                    >
                      <div>
                        <div className="text-[13px]" style={{ color: "var(--text)" }}>{item.label}</div>
                        {item.description && (
                          <div className="font-mono-data text-[11px] mt-0.5" style={{ color: "var(--text-3)" }}>{item.description}</div>
                        )}
                      </div>
                      {item.shortcut && (
                        <kbd
                          className="shrink-0 rounded px-1.5 py-0.5 font-mono-data text-[10px]"
                          style={{ background: "var(--surface-3)", border: "1px solid var(--border)", color: "var(--text-3)" }}
                        >{item.shortcut}</kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div
          className="flex items-center gap-4 px-4 py-2 font-mono-data text-[10px]"
          style={{ borderTop: "1px solid var(--border)", color: "var(--text-3)" }}
        >
          <span><kbd style={{ color: "var(--text-2)" }}>&#8593;&#8595;</kbd> navigate</span>
          <span><kbd style={{ color: "var(--text-2)" }}>&#8629;</kbd> open</span>
          <span><kbd style={{ color: "var(--text-2)" }}>ESC</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
