/**
 * RoundLab Service Worker — offline app-shell + pending audio recovery.
 *
 * Strategy:
 *  - Cache-first for static assets (JS/CSS/fonts/images)
 *  - Network-first for API calls (/api/*, /auth/*)
 *  - Offline fallback: serve cached /training page for navigation requests
 *
 * Pending audio recovery:
 *  - Listens for background sync tag "audio-upload-retry"
 *  - On sync: reads pending recordings from IndexedDB and retries upload
 */

const CACHE_NAME = "roundlab-shell-v1";
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

const DB_NAME = "roundlab_audio";
const STORE_NAME = "pending_recordings";
const UPLOAD_ENDPOINT = "/api/speech/upload";

function openAudioDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function retryPendingUploads() {
  let db;
  try {
    db = await openAudioDB();
  } catch {
    return; // DB not yet created — nothing to retry
  }

  const records = await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

  for (const record of records) {
    if (record.status !== "pending" && record.status !== "failed") continue;
    try {
      const form = new FormData();
      form.append("file", record.blob, `${record.uploadId}.${record.mimeType.split("/")[1] || "webm"}`);
      form.append("upload_id", record.uploadId);

      const res = await fetch(UPLOAD_ENDPOINT, { method: "POST", body: form });
      if (res.ok) {
        // Remove from IDB on success
        const tx = db.transaction(STORE_NAME, "readwrite");
        tx.objectStore(STORE_NAME).delete(record.uploadId);
      } else {
        // Mark failed
        const tx = db.transaction(STORE_NAME, "readwrite");
        tx.objectStore(STORE_NAME).put({ ...record, status: "failed", attempts: record.attempts + 1 });
      }
    } catch {
      // Network still offline — will retry on next sync
    }
  }
}

self.addEventListener("sync", (event) => {
  if (event.tag === "audio-upload-retry") {
    event.waitUntil(retryPendingUploads());
  }
});
