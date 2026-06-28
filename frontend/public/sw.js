/**
 * Dissio Service Worker — offline app-shell + pending audio recovery.
 *
 * Strategy:
 *  - Cache-first for static assets (JS/CSS/fonts/images)
 *  - Network-first for API calls (/api/*, /auth/*)
 *  - Offline fallback: serve cached /training page for navigation requests
 *
 * Pending audio recovery:
 *  - Listens for background sync tag "audio-upload-retry"
 *  - On sync: uploads pending recordings from dissio_audio and the legacy
 *    roundlab_audio database via retryPendingUploads() (defined in swHelpers.js).
 *  - After a successful upload the record is removed from every store that
 *    contained it, preventing cross-sync duplicate uploads.
 */

const CACHE_NAME = "dissio-shell-v1";
const OFFLINE_PAGE = "/training";

// Assets to pre-cache on install
const PRECACHE_URLS = [
  "/training",
  "/dashboard",
  "/manifest.json",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg",
];

// ── Install ────────────────────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

// ── Activate ───────────────────────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ── Fetch ──────────────────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Bypass: non-GET, cross-origin, API, auth
  if (
    request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/auth/")
  ) {
    return;
  }

  // Navigation requests: network-first, fallback to offline page
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, clone));
          return res;
        })
        .catch(() =>
          caches.match(OFFLINE_PAGE).then((cached) => cached ?? new Response("Offline", { status: 503 }))
        )
    );
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((res) => {
        if (!res.ok) return res;
        const clone = res.clone();
        caches.open(CACHE_NAME).then((c) => c.put(request, clone));
        return res;
      });
    })
  );
});

// ── Background Sync: audio upload retry ───────────────────────────────────

// Load helpers (openAudioDB, getAllFromDB, deleteRecord, markRecordFailed,
// retryPendingUploads, SW_DB_NAME, SW_DB_NAME_LEGACY, ...) into the SW scope.
importScripts("./swHelpers.js");

self.addEventListener("sync", (event) => {
  if (event.tag === "audio-upload-retry") {
    // retryPendingUploads() is defined by swHelpers.js (loaded above).
    // In production it uses the global indexedDB and fetch.
    event.waitUntil(retryPendingUploads());
  }
});
