import type { MetadataRoute } from "next";

// Served at /manifest.webmanifest and linked automatically by the App Router.
// Installability needs name, start_url, display, and both a 192px and a 512px icon.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SatQuery AI — Remote Sensing Intelligence",
    short_name: "SatQuery AI",
    description:
      "Agentic remote-sensing workstation: ask questions of satellite imagery in plain English and get evidence-backed answers.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#080E17",
    theme_color: "#080E17",
    categories: ["productivity", "utilities", "education"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "New analysis", url: "/analysis" },
      { name: "History", url: "/history" },
    ],
  };
}
