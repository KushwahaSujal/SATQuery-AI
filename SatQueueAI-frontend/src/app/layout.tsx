import "./globals.css";
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import AppHeader from "@/components/layout/AppHeader";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "SatQuery AI — Earth Observation Workstation",
  description: "Institutional-grade geospatial intelligence workstation powered by satellite imagery analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body suppressHydrationWarning style={{ height: "100vh", overflow: "hidden" }}>
        <Providers>
          <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
            <AppHeader />
            <main style={{ flex: 1, minHeight: 0, padding: "6px 8px 8px", overflowY: "auto" }}>
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
