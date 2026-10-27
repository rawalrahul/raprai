// RAPR AI Service Worker — enables PWA install + offline shell
const CACHE_NAME = 'rapr-ai-v11';

// Cache the app shell (CSS, JS) on install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // What index.html loads (tests/test_frontend_files.py keeps this in step).
      return cache.addAll([
        '/',
        '/css/design-system.css',
        '/css/original.css',
        '/css/premium.css',
        '/css/overhaul.css',
        '/css/impeccable.css',
        '/css/kelvin.css',
        '/css/groupchat.css',
        '/css/header.css',
        '/css/sidebar.css',
        '/css/needs.css',
        '/css/composer.css',
        '/css/picker.css',
        '/js/customize.js',
        '/js/kelvin.js',
        '/js/kelvin_ui.js',
        '/js/core.js',
        '/js/folder_picker.js',
        '/js/chat.js',
        '/js/schedules_history.js',
        '/js/sidebar_panels.js',
        '/js/settings.js',
        '/js/pipelines.js',
        '/js/layout.js',
        '/js/ai_list.js',
        '/js/packages.js',
        '/js/packages_installed.js',
        '/js/packages_browse.js',
        '/js/packages_install.js',
        '/js/memory.js',
        '/js/custom_ai.js',
        '/js/backup.js',
        '/js/agents.js',
        '/js/agent_builder.js',
        '/js/agent_run.js',
        '/js/agent_builder_chat.js',
        '/js/agents_init.js',
        '/js/council.js',
        '/js/groupchat.js',
        '/js/whatsapp.js',
        '/js/telegram.js',
        '/js/voices.js',
        '/js/finish.js',
        '/js/talk.js',
        '/js/share.js',
        '/js/cloud.js',
        '/js/safety.js',
        '/js/needs.js',
        '/js/demos.js',
        '/js/sidebar.js',
        '/js/updates.js',
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

// Phone notifications (Web Push): show the message, and focus or open RAPR on tap.
self.addEventListener('push', (event) => {
  let data = { title: 'RAPR AI', body: '', tag: 'rapr', url: '/' };
  try { data = Object.assign(data, event.data ? event.data.json() : {}); } catch (e) {}
  event.waitUntil(self.registration.showNotification(data.title, {
    body: data.body, tag: data.tag, renotify: true, icon: '/static/rapr-logo.png', data: { url: data.url },
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const c of list) { if ('focus' in c) { c.navigate && c.navigate(url); return c.focus(); } }
    return self.clients.openWindow(url);
  }));
});

