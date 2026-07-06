/* eslint-disable no-restricted-globals */
/**
 * Minimal service worker for PWA installability and faster repeat visits.
 * API calls and navigations always use the network; hashed webpack assets
 * are cached with a cache-first strategy.
 */
const CACHE_VERSION = "__CACHE_VERSION__";
const CACHE_NAME = `rewatch-static-${CACHE_VERSION}`;
const HASHED_STATIC_PATTERN = /\.[a-f0-9]{8,}\.(js|css|woff2?)$/i;

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches
      .keys()
      .then(keys =>
        Promise.all(
          keys
            .filter(key => key.startsWith("rewatch-static-") && key !== CACHE_NAME)
            .map(key => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const { request } = event;

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  if (url.pathname.startsWith("/static/") && HASHED_STATIC_PATTERN.test(url.pathname)) {
    event.respondWith(
      caches.open(CACHE_NAME).then(cache =>
        cache.match(request).then(
          cached =>
            cached ||
            fetch(request).then(response => {
              if (response.ok) {
                cache.put(request, response.clone());
              }
              return response;
            })
        )
      )
    );
    return;
  }

  event.respondWith(fetch(request));
});
