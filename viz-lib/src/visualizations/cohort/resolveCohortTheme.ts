import getThemePalette from "@/visualizations/shared/echarts/getThemePalette";

const DEFAULT_MINS = new Set(["#ffffff", "#fff", "white"]);

export function resolveCohortOptions<T extends { colors?: { min?: string; max?: string; steps?: number } }>(
  options: T
): T {
  const palette = getThemePalette();
  const colors = options.colors ?? {};

  if (!colors.min || DEFAULT_MINS.has(String(colors.min).toLowerCase())) {
    return {
      ...options,
      colors: {
        ...colors,
        min: palette.surfaceAlt,
      },
    };
  }

  return options;
}
