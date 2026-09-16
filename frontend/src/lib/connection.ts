const BASE_KEY = "satquery.apiBase";
const API_KEY = "satquery.apiKey";
const DEFAULT_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function read(name: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(name);
  } catch {
    return null;
  }
}

export function getApiBase(): string {
  return (read(BASE_KEY) || DEFAULT_BASE).replace(/\/+$/, "");
}

export function getApiKey(): string | null {
  return read(API_KEY);
}

export function setConnection(base: string, key: string): void {
  try {
    window.localStorage.setItem(BASE_KEY, base.trim());
    if (key.trim()) window.localStorage.setItem(API_KEY, key.trim());
    else window.localStorage.removeItem(API_KEY);
  } catch {
    // storage blocked: the defaults keep working for a local backend
  }
}

export function authHeaders(): Record<string, string> {
  const key = getApiKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

// Any absolute URL with a scheme (http:, https:, blob:, data:, ...) is used as-is;
// only a path (starting with "/") gets the configured API base prefixed onto it.
const HAS_SCHEME = /^[a-z][a-z0-9+.-]*:/i;
const IS_HTTP = /^https?:\/\//i;

/** Absolute URL for media the browser fetches itself (<img>, <video>, downloads), which cannot send headers. */
export function mediaUrl(path: string): string {
  const url = HAS_SCHEME.test(path) ? path : `${getApiBase()}${path}`;
  const key = getApiKey();
  // Only http(s) URLs go through our backend and can carry ?key=; leave blob:/data:/etc. untouched.
  if (!key || !IS_HTTP.test(url) || /[?&]key=/.test(url)) return url;
  return `${url}${url.includes("?") ? "&" : "?"}key=${encodeURIComponent(key)}`;
}
