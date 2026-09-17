import "./globals.css";
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "SatQuery AI — Remote Sensing Intelligence Dashboard",
  description: "Institutional-grade geospatial intelligence workstation powered by satellite imagery analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body suppressHydrationWarning className="font-sans min-h-screen antialiased flex overflow-x-hidden" style={{ background: "var(--canvas)", color: "var(--text)" }}>
        <Providers>
          <Sidebar />
          <main className="flex-1 flex flex-col min-w-0 relative" style={{ background: "var(--workspace)" }}>
            <TopBar />
            <div className="flex-1 overflow-y-auto">
              {children}
            </div>
          </main>
        </Providers>
      </body>
    </html>
  );
}
