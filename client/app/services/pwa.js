/**
 * Register the service worker that enables "Add to Home Screen" / install as app
 * on Android and iOS (16.4+). Skipped in development to avoid stale caches.
 */
export function registerServiceWorker() {
  if (process.env.NODE_ENV !== "production") {
    return;
  }

  if (!("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/service-worker.js", { scope: "/" }).catch(error => {
      // Non-fatal: the app works without install support.
      console.warn("Service worker registration failed:", error);
    });
  });
}
