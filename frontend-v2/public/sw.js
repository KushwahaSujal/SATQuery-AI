// SatQuery AI service worker.
//
// Deliberately conservative. Every analysis runs on the GPU backend, so nothing about
// this app works offline in a useful sense -- the job of this worker is only to make
// the shell installable and to survive a flaky lab network on the static assets.
//
// It never touches:
//   * anything that is not a same-origin GET
//   * /api/* (results must never be served stale)
//   * cross-origin requests, which is where the backend actually lives
//   * the background video, which is far too large to be worth caching

const CACHE = "satquery-shell-v1";
const PRECACHE = ["/", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      // A single missing entry must not fail the whole install.
      .then((cache) => Promise.allSettled(PRECACHE.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

function isCacheable(request) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return false;
  if (url.pathname.startsWith("/api/")) return false;
  if (url.pathname.endsWith(".mp4")) return false;
  return true;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (!isCacheable(request)) return;

  // Navigations: network first, so a deployed update is picked up immediately.
  // Fall back to the cached shell only when the network is genuinely unavailable.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((hit) => hit || caches.match("/"))),
    );
    return;
  }

  // Static assets: serve from cache, refresh in the background.
  event.respondWith(
    caches.match(request).then((hit) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => hit);
      return hit || network;
    }),
  );
});
