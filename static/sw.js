const CACHE_NAME = 'data-viz-static-v2';

// Vite build output is content-hashed (new filename per deploy), so it's
// safe to cache aggressively and never re-check the network for it.
const IMMUTABLE_PREFIXES = ['/static/dist/', '/static/icons/'];

// These are edited in place with a stable filename, so a cache-first or
// stale-while-revalidate strategy can keep serving an outdated copy across
// visits. Always prefer the network for them and only fall back to the
// cache when offline.
const REVALIDATED_PATHS = new Set(['/static/style.css', '/static/manifest.json']);

function isImmutableAsset(url) {
  if (url.origin !== self.location.origin) return false;
  return IMMUTABLE_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}

function isRevalidatedAsset(url) {
  if (url.origin !== self.location.origin) return false;
  return REVALIDATED_PATHS.has(url.pathname) || url.pathname.startsWith('/static/js/');
}

self.addEventListener('install', () => {
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

  if (isImmutableAsset(url)) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(event.request);
        if (cached) return cached;
        const response = await fetch(event.request);
        if (response.ok) cache.put(event.request, response.clone());
        return response;
      })
    );
    return;
  }

  if (isRevalidatedAsset(url)) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response.clone()));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  }
});
