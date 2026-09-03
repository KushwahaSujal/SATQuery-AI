import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SatQuery AI — Agentic Remote-Sensing Intelligence",
  description: "Next-generation agentic Earth observation platform for VQA, Grounding, Change Detection, and Optical-SAR Fusion.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
