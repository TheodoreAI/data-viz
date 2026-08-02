const CACHE_NAME = 'data-viz-static-v1';

// Only cache actual static assets (built JS/CSS, icons, fonts). Pages and
// /api/* are left untouched so logged-in content and live data are never
// served stale or from the wrong account.
function isCacheableStaticAsset(url) {
  if (url.origin !== self.location.origin) return false;
  return (
    url.pathname.startsWith('/static/dist/') ||
    url.pathname.startsWith('/static/icons/') ||
    url.pathname === '/static/style.css' ||
    url.pathname.startsWith('/static/js/') ||
    url.pathname === '/static/manifest.json'
  );
}

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  if (!isCacheableStaticAsset(url)) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(event.request);
      const fetchPromise = fetch(event.request)
        .then((response) => {
          if (response.ok) cache.put(event.request, response.clone());
          return response;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
