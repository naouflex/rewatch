/**
 * Theme service
 *
 * Manages light / dark / system theme preference. The active theme is applied
 * to the <html> element via the `data-theme` attribute, which is then consumed
 * by the CSS custom properties defined in `client/app/assets/less/inc/tokens.less`.
 *
 * The initial theme is applied synchronously at module load time (before React
 * mounts) to prevent a flash of unstyled content (FOUC).
 */

const STORAGE_KEY = "redash.theme";
const ROOT_ATTRIBUTE = "data-theme";

const PREFERENCES = ["light", "dark", "system"];

const listeners = new Set();
let currentPreference = readPreferenceFromStorage();

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
}

export function setThemePreference(preference) {
  if (!PREFERENCES.includes(preference)) {
    return;
  }
  currentPreference = preference;
  persistPreference(preference);
  applyResolvedTheme();
  listeners.forEach((listener) => {
    try {
      listener({ preference, resolved: getResolvedTheme(preference) });
    } catch (e) {
      // swallow listener errors so one bad consumer can't break the rest
    }
  });
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

// Keep "system" preference in sync if the OS theme changes while the app is open.
if (typeof window.matchMedia === "function") {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = () => {
    if (currentPreference === "system") {
      applyResolvedTheme();
      listeners.forEach((listener) => {
        try {
          listener({ preference: currentPreference, resolved: getResolvedTheme() });
        } catch (e) {
          // ignore
        }
      });
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
