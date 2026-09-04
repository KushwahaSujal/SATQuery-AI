"use client";

import type { UploadedRaster, UploadedVideo } from "@/lib/types";

interface MapViewerProps {
  rasters: UploadedRaster[];
  video: UploadedVideo | null;
}

export default function MapViewer({ rasters, video }: MapViewerProps) {
  const active = rasters[rasters.length - 1];

  return (
    <section style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      {/* Header */}
      <div className="panel-header">
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--t3)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="3 11 22 2 13 21 11 13 3 11"/>
          </svg>
          <span className="panel-label">Imagery Preview</span>
          {active?.crs && (
            <span className="font-mono-data" style={{
              fontSize: 9, color: "var(--accent-text)",
              background: "var(--accent-dim)", border: "1px solid hsla(222,88%,62%,0.15)",
              borderRadius: 2, padding: "1px 5px",
            }}>
              {active.crs}
            </span>
          )}
        </div>

        {/* Layer toggles */}
        <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
          {["RGB", "NDVI", "SAR"].map((layer, i) => (
            <button
              key={layer}
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: 9, fontWeight: 600,
                letterSpacing: "0.06em", textTransform: "uppercase",
                color: i === 0 ? "var(--accent-text)" : "var(--t4)",
                background: i === 0 ? "var(--accent-dim)" : "transparent",
                border: i === 0 ? "1px solid hsla(222,88%,62%,0.2)" : "1px solid transparent",
                borderRadius: 3, padding: "2px 6px",
                cursor: "pointer", transition: "all 0.1s",
              }}
              onMouseEnter={e => { if (i !== 0) (e.currentTarget as HTMLElement).style.color = "var(--t2)"; }}
              onMouseLeave={e => { if (i !== 0) (e.currentTarget as HTMLElement).style.color = "var(--t4)"; }}
            >
              {layer}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <div style={{
        flex: 1, position: "relative",
        background: "var(--s0)",
        display: "flex", alignItems: "center", justifyContent: "center",
        overflow: "hidden",
      }}>
        {active?.preview_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={active.preview_url}
            alt={active.filename}
            style={{ maxHeight: "100%", maxWidth: "100%", objectFit: "contain", display: "block" }}
          />
        ) : video ? (
          /* Video registered state */
          <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 48, height: 48, borderRadius: 10,
              background: "var(--s2)", border: "1px solid var(--b2)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-text)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </div>
            <div>
              <div className="font-mono-data" style={{ fontSize: 10, color: "var(--t2)" }}>
                {video.filename}
              </div>
              <div className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", marginTop: 3 }}>
                {video.duration_sec.toFixed(1)}s · {video.fps}fps · {video.width}×{video.height}
              </div>
            </div>
            <span className="status-pill status-pill-accent" style={{ fontSize: 9 }}>
              <span className="status-dot status-dot-accent animate-pulse-dot" />
              Video stream registered
            </span>
          </div>
        ) : (
          /* Empty state — world grid */
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, userSelect: "none" }}>
            {/* World grid SVG */}
            <div style={{ position: "relative", width: 220, height: 110 }}>
              <svg viewBox="0 0 320 160" style={{ width: "100%", height: "100%", opacity: 0.35 }}>
                {/* Meridians */}
                {[0, 40, 80, 120, 160, 200, 240, 280, 320].map(x => (
                  <line key={x} x1={x} y1="0" x2={x} y2="160" stroke="var(--b3)" strokeWidth="0.75" />
                ))}
                {/* Parallels */}
                {[0, 40, 80, 120, 160].map(y => (
                  <line key={y} x1="0" y1={y} x2="320" y2={y} stroke="var(--b3)" strokeWidth="0.75" />
                ))}
                {/* Equator (bolder) */}
                <line x1="0" y1="80" x2="320" y2="80" stroke="var(--accent)" strokeWidth="1.2" opacity="0.7" />
                {/* Prime meridian (bolder) */}
                <line x1="160" y1="0" x2="160" y2="160" stroke="var(--accent)" strokeWidth="1.2" opacity="0.7" />
                {/* Center crosshair rings */}
                <circle cx="160" cy="80" r="4" fill="none" stroke="var(--accent)" strokeWidth="1.2" opacity="0.8" />
                <circle cx="160" cy="80" r="12" fill="none" stroke="var(--accent)" strokeWidth="0.6" opacity="0.4" />
                <circle cx="160" cy="80" r="24" fill="none" stroke="var(--accent)" strokeWidth="0.4" opacity="0.2" />
              </svg>

              {/* Pulsing dot on top */}
              <div style={{
                position: "absolute", top: "50%", left: "50%",
                transform: "translate(-50%, -50%)",
                width: 6, height: 6, borderRadius: "50%",
                background: "var(--accent)",
                boxShadow: "0 0 8px var(--accent-glow)",
              }} className="animate-pulse-ring" />
            </div>

            <div style={{ textAlign: "center" }}>
              <p className="font-mono-data" style={{ fontSize: 10, color: "var(--t4)", letterSpacing: "0.12em", textTransform: "uppercase", margin: 0 }}>
                Awaiting Imagery
              </p>
              <p className="font-mono-data" style={{ fontSize: 9, color: "var(--t4)", marginTop: 4, letterSpacing: "0.04em" }}>
                Upload GeoTIFF or video to begin
              </p>
            </div>
          </div>
        )}

        {/* HUD overlay — coordinates + dimensions */}
        {active && (
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0,
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "6px 10px",
            background: "linear-gradient(transparent, rgba(6,6,8,0.85))",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <HudField label="FILE" value={active.filename} />
              {active.crs && <HudField label="CRS" value={active.crs} />}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {active.width && <HudField label="W×H" value={`${active.width}×${active.height}`} />}
              {active.bands && <HudField label="BANDS" value={String(active.bands)} />}
            </div>
          </div>
        )}

        {/* Zoom controls */}
        {active?.preview_url && (
          <div style={{
            position: "absolute", right: 10, bottom: active ? 40 : 10,
            display: "flex", flexDirection: "column", gap: 1,
          }}>
            {["+", "−", "⊡"].map((label) => (
              <button key={label} style={{
                width: 24, height: 24, borderRadius: 3,
                background: "var(--s2)", border: "1px solid var(--b2)",
                color: "var(--t3)", fontSize: 12, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.1s",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = "var(--s3)";
                (e.currentTarget as HTMLElement).style.color = "var(--t1)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = "var(--s2)";
                (e.currentTarget as HTMLElement).style.color = "var(--t3)";
              }}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function HudField({ label, value }: { label: string; value: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <span className="font-mono-data" style={{ fontSize: 8, color: "var(--t4)", letterSpacing: "0.08em" }}>{label}</span>
      <span className="font-mono-data" style={{ fontSize: 9, color: "var(--t2)" }}>{value}</span>
    </span>
  );
}
