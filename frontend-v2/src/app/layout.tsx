import "./globals.css";
import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/Providers";
import { ServiceWorkerRegistrar } from "@/components/ServiceWorkerRegistrar";

export const metadata: Metadata = {
  title: "SatQuery AI — Remote Sensing Intelligence Dashboard",
  description: "Institutional-grade geospatial intelligence workstation powered by satellite imagery analysis",
  applicationName: "SatQuery AI",
  appleWebApp: {
    capable: true,
    title: "SatQuery AI",
    // The UI is dark end to end; a translucent bar would show white behind the notch.
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#080E17",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
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
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
