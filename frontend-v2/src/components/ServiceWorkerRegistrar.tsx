"use client";

import { useEffect } from "react";

/**
 * Registers the service worker that makes the app installable.
 *
 * Skipped in development: a worker that caches the shell fights Turbopack's HMR and
 * produces stale pages that look like real bugs.
 */
export function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    const register = () => {
      navigator.serviceWorker.register("/sw.js").catch((err) => {
        // Never surface this: the app is fully functional without it.
        console.warn("Service worker registration failed", err);
      });
    };

    if (document.readyState === "complete") register();
    else {
      window.addEventListener("load", register);
      return () => window.removeEventListener("load", register);
    }
  }, []);

  return null;
}
