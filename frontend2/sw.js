// RAPR AI Service Worker — enables PWA install + offline shell
const CACHE_NAME = 'rapr-ai-v4';

// Cache the app shell (CSS, JS) on install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/css/design-system.css',
        '/css/original.css',
        '/css/premium.css',
        '/js/app.js',
        '/js/api.js',
        '/js/ws.js',
        '/js/state.js',
        '/js/config.js',
        '/js/packages.js',
        '/js/memory.js',
        '/js/commands.js',
        '/js/toast.js',
        '/js/backup.js',
        '/js/complete.js',
        '/js/custom_ai.js',
        '/js/agents.js',
        '/static/rapr-logo.png',
        '/static/logo-watermark-dark.png',
        '/static/logo-watermark-light.png',
      ]).catch(() => {
        // Non-critical — app works without cache
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))
      )
    )
  );
  self.clients.claim();
});

// Fetch strategy: network-first (always try live server, fall back to cache)
// This is important for a local app — the server is almost always available
self.addEventListener('fetch', (event) => {
  // Skip non-GET and WebSocket requests
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/ws')) return;
  if (event.request.url.includes('/api/')) return;
  if (event.request.url.includes('/mcp/')) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses for offline fallback
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(() => {
        // Server unreachable — serve from cache
        return caches.match(event.request);
      })
  );
});
