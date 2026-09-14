"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useHealth, useModels } from "@/hooks/useSystem";
import { useCommandPalette } from "@/components/ui/CommandPaletteContext";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const navItems = [
  { href: "/", label: "Command Center", short: "CMD" },
  { href: "/jobs", label: "Jobs", short: "JOBS" },
  { href: "/models", label: "Models", short: "MDL" },
  { href: "/system", label: "System", short: "SYS" },
];

function SessionTimer() {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  const fmt = (n: number) => String(n).padStart(2, "0");
  return (
    <span className="font-mono-data text-[10px] text-[var(--t3)] tracking-wider">
      {h > 0 ? `${fmt(h)}:` : ""}
      {fmt(m)}:{fmt(s)}
    </span>
  );
}

export default function AppHeader() {
  const pathname = usePathname();
  const health = useHealth();
  const { toggle } = useCommandPalette();

  const apiOnline = health.data?.api === "online";
  const dbConnected = health.data?.database === "connected";
  const modelsReady = health.data?.models_ready ?? 5;
  const modelsTotal = health.data?.models_total ?? 6;

  const match = pathname.match(/\/(analysis|visual-analytics|video)\/([^/]+)/);
  const jobId = match?.[2];

  const isAnalysisRoute =
    pathname.startsWith("/analysis") ||
    pathname.startsWith("/visual-analytics") ||
    pathname.startsWith("/video");

  return (
    <header
      className="h-12 bg-[var(--s1)] border-b border-[var(--b0)] flex items-center px-3 gap-0 flex-shrink-0 z-40 sticky top-0"
    >
      {/* Left zone: Brand */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Satellite logo */}
        <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 overflow-hidden bg-[var(--s2)] border border-[var(--b1)]">
          <img
            src="/satquery.svg"
            alt="SatQuery AI Logo"
            width={20}
            height={20}
            className="object-contain"
          />
        </div>

        <div className="flex flex-col gap-0">
          <Link
            href="/"
            className="font-mono-data text-[11px] font-bold tracking-[0.10em] uppercase text-[var(--t0)] no-underline hover:text-[var(--accent-text)] transition-colors"
          >
            SatQuery AI
          </Link>
          <span className="font-mono-data text-[9px] text-[var(--t4)] tracking-wider">
            v0.9-alpha
          </span>
        </div>
      </div>

      <Separator orientation="vertical" className="mx-3 h-5" />

      {/* Center zone: Nav */}
      <nav className="flex items-center gap-0.5">
        {navItems.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`px-2.5 py-1 rounded text-xs transition-all relative ${
                active
                  ? "font-medium text-[var(--t0)] bg-[var(--s3)] border border-[var(--b2)]"
                  : "font-normal text-[var(--t3)] hover:text-[var(--t1)] border border-transparent"
              }`}
            >
              {label}
              {active && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 rounded-full bg-[var(--accent)]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Job context breadcrumb */}
      {jobId && (
        <>
          <Separator orientation="vertical" className="mx-3 h-4" />
          <div className="font-mono-data flex items-center gap-1 text-[10px]">
            <span className="text-[var(--t4)]">job</span>
            <span className="text-[var(--t4)]">/</span>
            <span className="text-[var(--t2)]">{jobId.slice(0, 8)}</span>
            <span className="text-[var(--t4)]">/</span>
            {[
              { href: `/analysis/${jobId}`, label: "analysis" },
              { href: `/visual-analytics/${jobId}`, label: "vis-analytics" },
              { href: `/video/${jobId}`, label: "video" },
            ].map(({ href, label }, i, arr) => (
              <span
                key={href}
                className="flex items-center gap-1"
              >
                <Link
                  href={href}
                  className={`no-underline transition-colors ${
                    pathname.startsWith(href.split("/").slice(0, 2).join("/") + "/" + href.split("/")[2])
                      ? "text-[var(--accent-text)]"
                      : "text-[var(--t4)] hover:text-[var(--t2)]"
                  }`}
                >
                  {label}
                </Link>
                {i < arr.length - 1 && (
                  <span className="text-[var(--b2)]">·</span>
                )}
              </span>
            ))}
          </div>
        </>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right zone: Status + controls */}
      <div className="flex items-center gap-2.5">
        {/* System status pills */}
        <div className="flex items-center gap-1.5">
          <Badge variant={apiOnline ? "success" : "destructive"}>
            <span className={`w-1.5 h-1.5 rounded-full ${apiOnline ? "bg-[var(--green)] animate-pulse-dot" : "bg-[var(--red)]"}`} />
            {apiOnline ? "API" : "DEGRADED"}
          </Badge>

          <Badge variant={dbConnected ? "success" : "destructive"}>
            <span className={`w-1.5 h-1.5 rounded-full ${dbConnected ? "bg-[var(--green)] animate-pulse-dot" : "bg-[var(--red)]"}`} />
            DB
          </Badge>

          <Badge variant={modelsReady === modelsTotal ? "accent" : "warning"}>
            <span className={`w-1.5 h-1.5 rounded-full ${modelsReady === modelsTotal ? "bg-[var(--accent)] animate-pulse-dot" : "bg-[var(--amber)] animate-pulse-dot"}`} />
            {modelsReady}/{modelsTotal} MDL
          </Badge>
        </div>

        <Separator orientation="vertical" className="h-4" />

        {/* Session timer */}
        <div className="flex items-center gap-1.5">
          <svg
            width="9"
            height="9"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--t4)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <SessionTimer />
        </div>

        <Separator orientation="vertical" className="h-4" />

        {/* Command palette trigger */}
        <button
          onClick={toggle}
          aria-label="Open command palette"
          className="flex items-center gap-1 bg-transparent border-none cursor-pointer p-0 hover:opacity-80 transition-opacity"
        >
          <span className="kbd-chip">⌘</span>
          <span className="kbd-chip">K</span>
        </button>
      </div>

      {/* Running-job accent bottom border */}
      {isAnalysisRoute && (
        <div
          className="absolute bottom-0 left-0 right-0 h-[1px] pointer-events-none"
          style={{
            background: "linear-gradient(90deg, transparent, var(--accent), transparent)",
            opacity: 0.5,
          }}
        />
      )}
    </header>
  );
}
