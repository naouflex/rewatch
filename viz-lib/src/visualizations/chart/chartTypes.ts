/** Central registry of CHART visualization types and their ECharts mappings. */

export type ChartTypeDefinition = {
  type: string;
  name: string;
  icon: string;
  /** ECharts series type (defaults to internal type when omitted). */
  echartsType?: string;
  hasAxes?: boolean;
  hasLegend?: boolean;
  hasSeriesTab?: boolean;
  supportsStacking?: boolean;
  supportsHorizontal?: boolean;
  supportsLineShape?: boolean;
  /** Per-series type override in Series tab (mixed charts). */
  supportsMixedSeries?: boolean;
  /** Extra column mapping keys beyond x/y/series. */
  extraColumnMappings?: Array<"size" | "zVal" | "yError" | "open" | "high" | "low" | "close">;
};

export const CHART_TYPES: ChartTypeDefinition[] = [
  { type: "line", name: "Line", icon: "line-chart", supportsStacking: true, supportsHorizontal: true, supportsLineShape: true, supportsMixedSeries: true },
  { type: "column", name: "Bar", icon: "bar-chart", supportsStacking: true, supportsHorizontal: true, supportsMixedSeries: true },
  { type: "area", name: "Area", icon: "area-chart", supportsStacking: true, supportsHorizontal: true, supportsLineShape: true, supportsMixedSeries: true },
  { type: "pie", name: "Pie", icon: "pie-chart", hasAxes: false, hasLegend: true, hasSeriesTab: true },
  { type: "scatter", name: "Scatter", icon: "circle-o", supportsMixedSeries: true },
  { type: "effectScatter", name: "Effect Scatter", icon: "dot-circle-o", echartsType: "effectScatter", supportsMixedSeries: true },
  { type: "bubble", name: "Bubble", icon: "circle-o", extraColumnMappings: ["size"], supportsMixedSeries: true },
  { type: "heatmap", name: "Heatmap", icon: "th", extraColumnMappings: ["zVal"], hasLegend: false },
  { type: "box", name: "Box", icon: "square-o", echartsType: "boxplot", supportsHorizontal: true, supportsMixedSeries: true },
  { type: "candlestick", name: "Candlestick", icon: "bar-chart", echartsType: "candlestick", extraColumnMappings: ["open", "high", "low", "close"] },
  { type: "radar", name: "Radar", icon: "bullseye", hasAxes: false, hasLegend: true },
  { type: "treemap", name: "Treemap", icon: "th-large", echartsType: "treemap", hasAxes: false, hasLegend: false },
  { type: "gauge", name: "Gauge", icon: "tachometer", hasAxes: false, hasLegend: false, hasSeriesTab: false },
  { type: "pictorialBar", name: "Pictorial Bar", icon: "bar-chart", echartsType: "pictorialBar", supportsHorizontal: true, supportsMixedSeries: true },
  { type: "themeRiver", name: "Theme River", icon: "area-chart", echartsType: "themeRiver", hasLegend: true },
  { type: "parallel", name: "Parallel", icon: "bars", echartsType: "parallel", hasAxes: false, hasLegend: false },
];

export const CHART_TYPE_MAP = Object.fromEntries(CHART_TYPES.map(def => [def.type, def])) as Record<
  string,
  ChartTypeDefinition
>;

export function getChartTypeDef(type: string): ChartTypeDefinition | undefined {
  return CHART_TYPE_MAP[type];
}

export function chartTypeHasAxes(type: string): boolean {
  return getChartTypeDef(type)?.hasAxes !== false;
}

export function chartTypeHasLegendSettings(type: string): boolean {
  return getChartTypeDef(type)?.hasLegend !== false;
}

export function chartTypeHasSeriesTab(type: string): boolean {
  return getChartTypeDef(type)?.hasSeriesTab !== false;
}

export function getEChartsSeriesType(type: string): string {
  const def = getChartTypeDef(type);
  if (def?.echartsType) {
    return def.echartsType;
  }
  if (type === "column") {
    return "bar";
  }
  if (type === "box") {
    return "boxplot";
  }
  return type;
}

/** Types hidden from per-series override dropdown (global type only). */
export const PER_SERIES_HIDDEN_TYPES = [
  "pie",
  "heatmap",
  "bubble",
  "box",
  "candlestick",
  "radar",
  "treemap",
  "gauge",
  "themeRiver",
  "parallel",
  "custom",
];
