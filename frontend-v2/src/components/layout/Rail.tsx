"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const sections = [
  {
    label: null,
    items: [
      { href: "/", label: "Home" },
      { href: "/analysis", label: "New Analysis" },
      { href: "/history", label: "History" },
      { href: "/datasets", label: "Datasets" },
      { href: "/reports", label: "Reports" },
    ],
  },
  {
    label: "Analysis Tools",
    items: [
      { href: "/analysis", label: "AI Assistant" },
      { href: "/analysis", label: "VQA" },
      { href: "/analysis", label: "Grounding" },
      { href: "/analysis", label: "Change Analysis" },
      { href: "/analysis", label: "Optical + SAR Fusion" },
    ],
  },
  {
    label: "Resources",
    items: [
      { href: "/documentation", label: "Documentation" },
      { href: "/documentation", label: "Help & Support" },
    ],
  },
];

export default function Rail() {
  const pathname = usePathname();

  return (
    <nav className="rail" aria-label="Main navigation">
      {sections.map((section, si) => (
        <div key={si}>
          {section.label && <div className="rail-h">{section.label}</div>}
          {section.items.map(({ href, label }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={label}
                href={href}
                className={`item ${active ? "on" : ""}`}
              >
                <span className={`tick ${active ? "" : "mute"}`} />
                {label}
              </Link>
            );
          })}
        </div>
      ))}

      {/* Bottom eco card */}
      <div style={{ marginTop: "auto", paddingTop: 16 }}>
        <div style={{ padding: "12px 14px", borderRadius: "var(--r-lg)", border: "1px solid color-mix(in srgb, var(--accent) 20%, transparent)", background: "var(--raised)" }}>
          <div style={{ fontSize: 10.5, color: "var(--accent)", fontWeight: 600, marginBottom: 4 }}>SatQuery AI</div>
          <div style={{ fontSize: 11, color: "var(--tx3)", lineHeight: 1.5 }}>AI-powered remote sensing for a sustainable future.</div>
        </div>
      </div>
    </nav>
  );
}
