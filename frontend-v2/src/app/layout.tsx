import "./globals.css";
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "SatQuery AI — Remote Sensing Intelligence Dashboard",
  description: "Institutional-grade geospatial intelligence workstation powered by satellite imagery analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body
        suppressHydrationWarning
        className="bg-[var(--canvas)] text-[var(--text)] font-sans min-h-screen antialiased selection:bg-teal-500 selection:text-black"
      >
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
