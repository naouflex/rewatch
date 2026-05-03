/**
 * Landing-site theme service. Mirrors the host app's
 * client/app/services/theme.js so the look-and-feel stays consistent when
 * the help drawer iframes this site.
 *
 * Resolution order:
 *   1. URL param `?theme=light|dark|system` (also the inverse-watch
 *      shorthand `?dark=1|0|true|false`).
 *   2. postMessage from the parent window: { type: "set_theme", theme }.
 *      The host help drawer pushes one of these whenever the user
 *      toggles theme inside the app while the drawer is open.
 *   3. localStorage key `landing.theme`.
 *   4. system / OS preference via `prefers-color-scheme`.
 *
 * The active theme is applied to <html data-theme="dark"|null>, which
 * the CSS in styles/globals.css reads.
 */

const STORAGE_KEY = "landing.theme";
const ROOT_ATTRIBUTE = "data-theme";
const PREFERENCES = ["light", "dark", "system"];
const SET_THEME_MESSAGE = "set_theme";

let urlOverride = false;
let parentOverride = false;
let currentPreference = "system";

const listeners = new Set();

function readPreferenceFromStorage() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && PREFERENCES.includes(stored)) return stored;
  } catch {
    // localStorage may be unavailable (private mode, sandboxed iframe…).
  }
  return "system";
}

function readPreferenceFromUrl() {
  if (typeof window === "undefined" || !window.location) return null;
  let params;
  try {
    params = new URLSearchParams(window.location.search);
  } catch {
    return null;
  }

  const theme = params.get("theme");
  if (theme && PREFERENCES.includes(theme)) return theme;

  const dark = params.get("dark");
  if (dark !== null) {
    const normalized = dark.toLowerCase();
    if (normalized === "1" || normalized === "true") return "dark";
    if (normalized === "0" || normalized === "false") return "light";
  }
  return null;
}

function getSystemTheme() {
  if (typeof window === "undefined") return "light";
  if (typeof window.matchMedia !== "function") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function getResolvedTheme(preference = currentPreference) {
  return preference === "system" ? getSystemTheme() : preference;
}

function applyResolvedTheme() {
  if (typeof document === "undefined") return;
  const resolved = getResolvedTheme();
  const root = document.documentElement;
  if (resolved === "dark") {
    root.setAttribute(ROOT_ATTRIBUTE, "dark");
  } else {
    root.removeAttribute(ROOT_ATTRIBUTE);
  }
  root.style.colorScheme = resolved === "dark" ? "dark" : "light";
}

function notifyListeners() {
  const payload = {
    preference: currentPreference,
    resolved: getResolvedTheme(),
  };
  listeners.forEach((listener) => {
    try {
      listener(payload);
    } catch {
      // swallow listener errors so one bad consumer can't break the rest
    }
  });
}

export function setThemePreference(preference, options = {}) {
  if (!PREFERENCES.includes(preference)) return;
  currentPreference = preference;

  // Internal callers (URL / postMessage driven) opt-in to "transient" mode
  // so the override doesn't get persisted to localStorage and hijack the
  // user's saved preference.
  if (options.urlOverride === true) {
    urlOverride = true;
    parentOverride = false;
  } else if (options.parentOverride === true) {
    parentOverride = true;
    urlOverride = false;
  } else {
    urlOverride = false;
    parentOverride = false;
  }

  if (
    options.persist !== false &&
    !urlOverride &&
    !parentOverride
  ) {
    try {
      if (preference === "system") {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, preference);
      }
    } catch {
      // ignore
    }
  }

  applyResolvedTheme();
  notifyListeners();
}

export function getThemePreference() {
  return currentPreference;
}

export function toggleTheme() {
  const resolved = getResolvedTheme();
  setThemePreference(resolved === "dark" ? "light" : "dark");
}

export function subscribeToTheme(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// ---------------------------------------------------------------------------
// Bootstrapping — runs once at module import (well before React mounts) so
// there's no flash of unstyled content when the saved theme is dark.
// ---------------------------------------------------------------------------
function init() {
  const fromUrl = readPreferenceFromUrl();
  if (fromUrl) {
    currentPreference = fromUrl;
    urlOverride = true;
  } else {
    currentPreference = readPreferenceFromStorage();
  }
  applyResolvedTheme();

  if (typeof window === "undefined") return;

  // React to OS theme changes while preference is "system".
  if (typeof window.matchMedia === "function") {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (currentPreference === "system") {
        applyResolvedTheme();
        notifyListeners();
      }
    };
    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", handler);
    } else if (typeof media.addListener === "function") {
      media.addListener(handler);
    }
  }

  // Listen for the parent (host help drawer) pushing a theme change.
  window.addEventListener("message", (event) => {
    const data = event && event.data;
    if (!data || data.type !== SET_THEME_MESSAGE) return;
    const theme = data.theme;
    if (PREFERENCES.includes(theme)) {
      setThemePreference(theme, { persist: false, parentOverride: true });
    }
  });
}

init();

export default {
  getThemePreference,
  getResolvedTheme,
  setThemePreference,
  toggleTheme,
  subscribeToTheme,
};
