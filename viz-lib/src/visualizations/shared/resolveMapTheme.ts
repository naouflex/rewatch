import getThemePalette from "./echarts/getThemePalette";

const LIGHT_MAP_TILE = "//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const DARK_MAP_TILE = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

const DEFAULT_BACKGROUNDS = new Set(["#ffffff", "#fff", "white"]);
const DEFAULT_BORDERS = new Set(["#ffffff", "#fff", "white"]);

function isDarkTheme() {
  if (typeof document === "undefined") {
    return false;
  }
  return document.documentElement.getAttribute("data-theme") === "dark";
}

export function resolveMapTileUrl(mapTileUrl: string | undefined) {
  const url = mapTileUrl || LIGHT_MAP_TILE;
  if (!isDarkTheme()) {
    return url;
  }

  const normalized = url.replace(/^https?:/, "");
  const defaultOsm = LIGHT_MAP_TILE.replace(/^https?:/, "");
  if (normalized === defaultOsm) {
    return DARK_MAP_TILE;
  }

  return url;
}

export function resolveChoroplethOptions<T extends { colors?: Record<string, string> }>(options: T | undefined): T {
  if (!options || !isDarkTheme()) {
    return options as T;
  }

  const palette = getThemePalette();
  const colors = options.colors ?? {};

  return {
    ...options,
    colors: {
      ...colors,
      background:
        !colors.background || DEFAULT_BACKGROUNDS.has(String(colors.background).toLowerCase())
          ? palette.surfaceAlt
          : colors.background,
      borders:
        !colors.borders || DEFAULT_BORDERS.has(String(colors.borders).toLowerCase())
          ? palette.border
          : colors.borders,
      noValue: colors.noValue ?? palette.divider,
    },
  };
}

export { DARK_MAP_TILE, LIGHT_MAP_TILE };
