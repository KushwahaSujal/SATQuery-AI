"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useHealth, useModels } from "@/hooks/useSystem";
import { useCommandPalette } from "@/components/ui/CommandPaletteContext";

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
    <span
      className="font-mono-data"
      style={{ fontSize: 10, color: "var(--t3)", letterSpacing: "0.05em" }}
    >
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
      style={{
        height: 48,
        background: "var(--s1)",
        borderBottom: "1px solid var(--b0)",
        display: "flex",
        alignItems: "center",
        paddingLeft: 12,
        paddingRight: 12,
        gap: 0,
        flexShrink: 0,
        zIndex: 40,
        position: "sticky",
        top: 0,
      }}
    >
      {/* ── Left zone: Brand ── */}
      <div
        style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}
      >
        {/* Satellite logo */}
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: 5,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            overflow: "hidden",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/satquery.svg"
            alt="SatQuery AI Logo"
            width={24}
            height={24}
            style={{ objectFit: "contain" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          <Link
            href="/"
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.10em",
              textTransform: "uppercase",
              color: "var(--t0)",
              textDecoration: "none",
            }}
          >
            SatQuery AI
          </Link>
          <span
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 9,
              color: "var(--t4)",
              letterSpacing: "0.06em",
            }}
          >
            v0.9-alpha
          </span>
        </div>
      </div>

      {/* Divider */}
      <div
        style={{
          width: 1,
          height: 20,
          background: "var(--b1)",
          margin: "0 14px",
          flexShrink: 0,
        }}
      />

      {/* ── Center zone: Nav ── */}
      <nav style={{ display: "flex", alignItems: "center", gap: 2 }}>
        {navItems.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              style={{
                padding: "4px 10px",
                borderRadius: 4,
                fontSize: 12,
                fontWeight: active ? 500 : 400,
                color: active ? "var(--t0)" : "var(--t3)",
                background: active ? "var(--s3)" : "transparent",
                border: active
                  ? "1px solid var(--b2)"
                  : "1px solid transparent",
                textDecoration: "none",
                transition: "all 0.12s",
                position: "relative",
              }}
              onMouseEnter={(e) => {
                if (!active)
                  (e.currentTarget as HTMLElement).style.color = "var(--t1)";
              }}
              onMouseLeave={(e) => {
                if (!active)
                  (e.currentTarget as HTMLElement).style.color = "var(--t3)";
              }}
            >
              {label}
              {active && (
                <span
                  style={{
                    position: "absolute",
                    bottom: -1,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: 16,
                    height: 2,
                    borderRadius: 1,
                    background: "var(--accent)",
                  }}
                />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Job context breadcrumb */}
      {jobId && (
        <>
          <div
            style={{
              width: 1,
              height: 16,
              background: "var(--b1)",
              margin: "0 12px",
              flexShrink: 0,
            }}
          />
          <div
            className="font-mono-data"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: 10,
            }}
          >
            <span style={{ color: "var(--t4)" }}>job</span>
            <span style={{ color: "var(--t4)" }}>/</span>
            <span style={{ color: "var(--t2)" }}>{jobId.slice(0, 8)}</span>
            <span style={{ color: "var(--t4)" }}>/</span>
            {[
              { href: `/analysis/${jobId}`, label: "analysis" },
              { href: `/visual-analytics/${jobId}`, label: "vis-analytics" },
              { href: `/video/${jobId}`, label: "video" },
            ].map(({ href, label }, i, arr) => (
              <span
                key={href}
                style={{ display: "flex", alignItems: "center", gap: 4 }}
              >
                <Link
                  href={href}
                  style={{
                    color: pathname.startsWith(
                      href.split("/").slice(0, 2).join("/") +
                        "/" +
                        href.split("/")[2],
                    )
                      ? "var(--accent-text)"
                      : "var(--t4)",
                    textDecoration: "none",
                    transition: "color 0.1s",
                  }}
                >
                  {label}
                </Link>
                {i < arr.length - 1 && (
                  <span style={{ color: "var(--b2)" }}>·</span>
                )}
              </span>
            ))}
          </div>
        </>
      )}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* ── Right zone: Status + controls ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* System status pills */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            className={`status-pill ${apiOnline ? "status-pill-green" : "status-pill-red"}`}
          >
            <span
              className={`status-dot ${apiOnline ? "status-dot-green animate-pulse-dot" : "status-dot-red"}`}
            />
            {apiOnline ? "API" : "DEGRADED"}
          </span>

          <span
            className={`status-pill ${dbConnected ? "status-pill-green" : "status-pill-red"}`}
          >
            <span
              className={`status-dot ${dbConnected ? "status-dot-green animate-pulse-dot" : "status-dot-red"}`}
            />
            DB
          </span>

          <span
            className={`status-pill ${modelsReady === modelsTotal ? "status-pill-accent" : "status-pill-amber"}`}
          >
            <span
              className={`status-dot ${modelsReady === modelsTotal ? "status-dot-accent animate-pulse-dot" : "status-dot-amber animate-pulse-dot"}`}
            />
            {modelsReady}/{modelsTotal} MDL
          </span>
        </div>

        <div style={{ width: 1, height: 16, background: "var(--b1)" }} />

        {/* Session timer */}
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
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

        <div style={{ width: 1, height: 16, background: "var(--b1)" }} />

        {/* Command palette trigger */}
        <button
          onClick={toggle}
          aria-label="Open command palette"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          <span className="kbd-chip">⌘</span>
          <span className="kbd-chip">K</span>
        </button>
      </div>

      {/* Running-job accent bottom border */}
      {isAnalysisRoute && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 1,
            background:
              "linear-gradient(90deg, transparent, var(--accent), transparent)",
            opacity: 0.5,
            pointerEvents: "none",
          }}
        />
      )}
    </header>
  );
}
