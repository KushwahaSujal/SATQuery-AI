import { useSyncExternalStore } from "react";

const BASE_KEY = "satquery.apiBase";
const API_KEY = "satquery.apiKey";
const DEFAULT_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
// Fired after setConnection() writes to localStorage, so same-tab listeners (useConnection)
// learn about the change immediately; the native "storage" event only fires in OTHER tabs.
const CONNECTION_EVENT = "satquery:connection";
const SCHEME = /^https?:\/\//i;

function read(name: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(name);
  } catch {
    return null;
  }
}

export function getApiBase(): string {
  const stored = read(BASE_KEY);
  // A value saved without a scheme (e.g. "x.modal.run") would resolve against the frontend's
  // own origin in fetch() and never carry a key in mediaUrl() — treat it as unset instead.
  const base = stored && SCHEME.test(stored) ? stored : DEFAULT_BASE;
  return base.replace(/\/+$/, "");
}

export function getApiKey(): string | null {
  return read(API_KEY);
}

export function setConnection(base: string, key: string): void {
  try {
    window.localStorage.setItem(BASE_KEY, base.trim());
    if (key.trim()) window.localStorage.setItem(API_KEY, key.trim());
    else window.localStorage.removeItem(API_KEY);
    window.dispatchEvent(new Event(CONNECTION_EVENT));
  } catch {
    // storage blocked: the defaults keep working for a local backend
  }
}

export type ConnectionSnapshot = { base: string; key: string | null };

// Server-rendered HTML (and the first client render, which must match it for hydration) can
// never see localStorage, so both must resolve to this same fixed snapshot.
const SERVER_SNAPSHOT: ConnectionSnapshot = { base: DEFAULT_BASE, key: null };

let cachedSnapshot: ConnectionSnapshot = SERVER_SNAPSHOT;

function getClientSnapshot(): ConnectionSnapshot {
  const base = getApiBase();
  const key = getApiKey();
  // useSyncExternalStore requires a referentially stable return value when nothing changed,
  // or it re-renders forever.
  if (cachedSnapshot.base !== base || cachedSnapshot.key !== key) {
    cachedSnapshot = { base, key };
  }
  return cachedSnapshot;
}

function subscribe(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", onChange);
  window.addEventListener(CONNECTION_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(CONNECTION_EVENT, onChange);
  };
}

function getServerSnapshot(): ConnectionSnapshot {
  return SERVER_SNAPSHOT;
}

/**
 * The stored backend base URL and API key, hydration-safe: renders the same default on the
 * server and the first client pass, then re-renders once with the real localStorage values
 * right after hydration (and again whenever setConnection() runs or another tab changes them).
 * Any component that renders a URL built from getApiBase()/getApiKey()/mediaUrl() must call
 * this so it re-renders — and any useMemo building such a URL must depend on its result —
 * otherwise React 19 will leave stale (keyless, localhost) src/href attributes from the SSR
 * pass in the DOM, since hydration does not patch mismatched attributes on its own.
 */
export function useConnection(): ConnectionSnapshot {
  return useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);
}

export function authHeaders(): Record<string, string> {
  const key = getApiKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

// Any absolute URL with a scheme (http:, https:, blob:, data:, ...) is used as-is;
// only a path (starting with "/") gets the configured API base prefixed onto it.
const HAS_SCHEME = /^[a-z][a-z0-9+.-]*:/i;

/** Absolute URL for media the browser fetches itself (<img>, <video>, downloads), which cannot send headers. */
export function mediaUrl(path: string): string {
  const url = HAS_SCHEME.test(path) ? path : `${getApiBase()}${path}`;
  const key = getApiKey();
  // Only http(s) URLs go through our backend and can carry ?key=; leave blob:/data:/etc. untouched.
  if (!key || !SCHEME.test(url) || /[?&]key=/.test(url)) return url;
  return `${url}${url.includes("?") ? "&" : "?"}key=${encodeURIComponent(key)}`;
}
