/**
 * Resolves Redash theme design tokens (CSS custom properties) into plain
 * color strings that Plotly can consume. Falls back to sensible light-theme
 * defaults when running outside the host app or before tokens are defined.
 */

type Palette = {
  background: string;
  surface: string;
  surfaceAlt: string;
  text: string;
  textMuted: string;
  border: string;
  divider: string;
  brand: string;
};

const LIGHT_FALLBACK: Palette = {
  background: "#ffffff",
  surface: "#ffffff",
  surfaceAlt: "#fbfaf7",
  text: "#1f1a16",
  textMuted: "#7a7068",
  border: "#ece8e1",
  divider: "#f1eee8",
  brand: "#ff7230",
};

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return fallback;
  }
  try {
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || fallback;
  } catch (e) {
    return fallback;
  }
}

export default function getThemePalette(): Palette {
  return {
    background: readVar("--rd-color-bg", LIGHT_FALLBACK.background),
    surface: readVar("--rd-color-surface", LIGHT_FALLBACK.surface),
    surfaceAlt: readVar("--rd-color-surface-alt", LIGHT_FALLBACK.surfaceAlt),
    text: readVar("--rd-color-text", LIGHT_FALLBACK.text),
    textMuted: readVar("--rd-color-text-muted", LIGHT_FALLBACK.textMuted),
    border: readVar("--rd-color-border", LIGHT_FALLBACK.border),
    divider: readVar("--rd-color-divider", LIGHT_FALLBACK.divider),
    brand: readVar("--rd-color-brand", LIGHT_FALLBACK.brand),
  };
}
