/**
 * Theme service
 *
 * Manages light / dark / system theme preference. The active theme is applied
 * to the <html> element via the `data-theme` attribute, which is then consumed
 * by the CSS custom properties defined in `client/app/assets/less/inc/tokens.less`.
 * For backward compatibility with inverse-watch-ported components that style
 * themselves via `body.dark-mode`, the same class is also toggled on <body>.
 *
 * URL overrides
 * -------------
 * Public dashboards / shared queries / embeds need to be themable per-link
 * without touching localStorage. Two query parameters are honoured (in order):
 *
 *   ?theme=light|dark|system       Explicit preference.
 *   ?dark=1|0|true|false           Inverse-watch alias; `1`/`true` -> dark,
 *                                  `0`/`false` -> light.
 *
 * When a URL override is present the resolved theme is applied immediately
 * but is NOT persisted to localStorage (the override is transient and only
 * lives for the duration of that page load + session). A `popstate` listener
 * re-reads the URL when the user navigates back/forward.
 *
 * The initial theme is applied synchronously at module load time (before React
 * mounts) to prevent a flash of unstyled content (FOUC).
 */

const STORAGE_KEY = "redash.theme";
const ROOT_ATTRIBUTE = "data-theme";
const BODY_DARK_CLASS = "dark-mode";

const PREFERENCES = ["light", "dark", "system"];

const listeners = new Set();
// `urlOverride` tracks whether the current preference was forced by a URL
// parameter; if so we skip localStorage persistence to keep the override
// scoped to that link.
let urlOverride = false;
let currentPreference = readInitialPreference();

function readPreferenceFromStorage() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && PREFERENCES.includes(stored)) {
      return stored;
    }
  } catch (e) {
    // localStorage may be disabled (e.g. private mode); fall back to system.
  }
  return "system";
}

function readPreferenceFromUrl() {
  if (typeof window === "undefined" || !window.location) {
    return null;
  }
  let params;
  try {
    params = new URLSearchParams(window.location.search);
  } catch (e) {
    return null;
  }

  const theme = params.get("theme");
  if (theme && PREFERENCES.includes(theme)) {
    return theme;
  }

  // Inverse-watch alias: `?dark=1` / `?dark=0` (also accepts true/false).
  const dark = params.get("dark");
  if (dark !== null) {
    const normalized = dark.toLowerCase();
    if (normalized === "1" || normalized === "true") {
      return "dark";
    }
    if (normalized === "0" || normalized === "false") {
      return "light";
    }
  }
  return null;
}

function readInitialPreference() {
  const fromUrl = readPreferenceFromUrl();
  if (fromUrl) {
    urlOverride = true;
    return fromUrl;
  }
  urlOverride = false;
  return readPreferenceFromStorage();
}

function persistPreference(preference) {
  try {
    if (preference === "system") {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, preference);
    }
  } catch (e) {
    // ignore
  }
}

function getSystemTheme() {
  if (typeof window.matchMedia === "function") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return "light";
}

export function getResolvedTheme(preference = currentPreference) {
  return preference === "system" ? getSystemTheme() : preference;
}

export function getThemePreference() {
  return currentPreference;
}

function applyResolvedTheme() {
  const resolved = getResolvedTheme();
  const root = document.documentElement;
  if (resolved === "dark") {
    root.setAttribute(ROOT_ATTRIBUTE, "dark");
  } else {
    root.removeAttribute(ROOT_ATTRIBUTE);
  }
  // Hint the UA so native form controls / scrollbars match.
  root.style.colorScheme = resolved === "dark" ? "dark" : "light";

  // Inverse-watch-ported components (json-view-interactive, ML model views,
  // prediction views, etc.) style themselves via `body.dark-mode`. Mirror the
  // resolved theme onto the body so those styles activate alongside the CSS
  // variable swap on <html>.
  if (typeof document !== "undefined" && document.body) {
    if (resolved === "dark") {
      document.body.classList.add(BODY_DARK_CLASS);
    } else {
      document.body.classList.remove(BODY_DARK_CLASS);
    }
  }
}

function notifyListeners(preference) {
  listeners.forEach((listener) => {
    try {
      listener({ preference, resolved: getResolvedTheme(preference) });
    } catch (e) {
      // swallow listener errors so one bad consumer can't break the rest
    }
  });
}

export function setThemePreference(preference, options = {}) {
  if (!PREFERENCES.includes(preference)) {
    return;
  }
  currentPreference = preference;
  // A user-driven change clears the URL override flag, so the new preference
  // becomes the new sticky default and is persisted normally. Internal callers
  // (e.g. URL-driven re-init) can pass `{ persist: false, urlOverride: true }`
  // to keep the value transient.
  if (options.urlOverride === true) {
    urlOverride = true;
  } else if (options.urlOverride === false) {
    urlOverride = false;
  } else {
    urlOverride = false;
  }
  if (options.persist !== false && !urlOverride) {
    persistPreference(preference);
  }
  applyResolvedTheme();
  notifyListeners(preference);
}

export function toggleTheme() {
  // Cycle: system -> dark -> light -> system. Most users want a quick flip,
  // so when explicitly toggling we move to the opposite of the *resolved* theme
  // (not the preference) and then stay there.
  const resolved = getResolvedTheme();
  setThemePreference(resolved === "dark" ? "light" : "dark");
}

export function subscribeToTheme(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// Apply the initial theme synchronously so the user never sees a light flash
// when the saved preference is dark.
applyResolvedTheme();

// Re-read the URL when the user navigates back/forward; this lets a user open
// `?dark=1` then hit Back to a `?dark=0` page and have the theme follow.
if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
  const reapplyFromUrl = () => {
    const fromUrl = readPreferenceFromUrl();
    if (fromUrl) {
      if (fromUrl !== currentPreference || !urlOverride) {
        setThemePreference(fromUrl, { persist: false, urlOverride: true });
      }
      return;
    }
    // URL no longer carries an override: revert to the persisted preference
    // (if we previously had one applied transiently).
    if (urlOverride) {
      const stored = readPreferenceFromStorage();
      setThemePreference(stored, { persist: false, urlOverride: false });
    }
  };
  window.addEventListener("popstate", reapplyFromUrl);
  window.addEventListener("hashchange", reapplyFromUrl);
}

// Keep "system" preference in sync if the OS theme changes while the app is open.
if (typeof window.matchMedia === "function") {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = () => {
    if (currentPreference === "system") {
      applyResolvedTheme();
      notifyListeners(currentPreference);
    }
  };
  if (typeof media.addEventListener === "function") {
    media.addEventListener("change", handler);
  } else if (typeof media.addListener === "function") {
    // Safari < 14
    media.addListener(handler);
  }
}

export default {
  getThemePreference,
  getResolvedTheme,
  setThemePreference,
  toggleTheme,
  subscribeToTheme,
};
