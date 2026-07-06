import { filter, map, max, uniq } from "lodash";
import getThemePalette from "./getThemePalette";
import { getEChartsSeriesType } from "../chartTypes";

function convertEffectScatterSeries(traces: any[], palette: ReturnType<typeof getThemePalette>) {
  return filter(traces, t => t.visible !== false).map(trace => {
    const color = trace.marker?.color ?? trace.line?.color ?? palette.brand;
    return {
      type: "effectScatter",
      name: trace.name,
      data: map(trace.x, (x, i) => [x, trace.y[i]]),
      itemStyle: { color },
      rippleEffect: { scale: 2.5, brushType: "stroke" },
      symbolSize: 10,
    };
  });
}

function convertPictorialBarSeries(traces: any[], options: any, palette: ReturnType<typeof getThemePalette>) {
  const isHorizontal = options.swappedAxes;
  return filter(traces, t => t.visible !== false).map(trace => {
    const color = trace.marker?.color ?? palette.brand;
    const data = isHorizontal
      ? map(trace.y, (y, i) => [y, trace.x[i]])
      : map(trace.x, (x, i) => [x, trace.y[i]]);
    return {
      type: "pictorialBar",
      name: trace.name,
      data,
      itemStyle: { color },
      symbol: "roundRect",
      symbolRepeat: true,
      symbolSize: isHorizontal ? [4, "100%"] : ["100%", 4],
      symbolClip: true,
    };
  });
}

function convertRadarSeries(traces: any[], palette: ReturnType<typeof getThemePalette>) {
  const indicators = uniq(traces[0]?.x ?? []).map((name: any) => ({
    name: String(name),
    max: max(map(traces, t => max(t.y))) ?? 100,
  }));

  return {
    indicators,
    series: filter(traces, t => t.visible !== false).map(trace => ({
      type: "radar",
      name: trace.name,
      data: [{ value: trace.y, name: trace.name }],
      itemStyle: { color: trace.marker?.color ?? palette.brand },
      areaStyle: { opacity: 0.15 },
    })),
  };
}

function convertTreemapSeries(traces: any[], palette: ReturnType<typeof getThemePalette>) {
  const data = filter(traces, t => t.visible !== false).flatMap(trace =>
    map(trace.x, (name, i) => ({
      name: String(name),
      value: trace.y[i],
      itemStyle: { color: trace.marker?.color ?? palette.brand },
    }))
  );

  return [
    {
      type: "treemap",
      data,
      label: { show: true, color: palette.text },
      breadcrumb: { itemStyle: { color: palette.surface, textStyle: { color: palette.text } } },
    },
  ];
}

function convertGaugeSeries(traces: any[], palette: ReturnType<typeof getThemePalette>) {
  const trace = traces.find(t => t.visible !== false) ?? traces[0];
  const value = trace?.y?.[trace.y.length - 1] ?? 0;
  const maxValue = Math.max(100, max(trace?.y) ?? 0, value);

  return [
    {
      type: "gauge",
      min: 0,
      max: maxValue,
      progress: { show: true, width: 12 },
      axisLine: { lineStyle: { width: 12, color: [[1, palette.divider]] } },
      axisLabel: { color: palette.textMuted },
      detail: { valueAnimation: true, color: palette.text, fontSize: 18 },
      data: [{ value, name: trace?.name ?? "" }],
    },
  ];
}

function convertCandlestickSeries(traces: any[], palette: ReturnType<typeof getThemePalette>) {
  const trace = traces.find(t => t.visible !== false) ?? traces[0];
  if (!trace?.open) {
    return [];
  }

  return [
    {
      type: "candlestick",
      name: trace.name,
      data: map(trace.x, (_x, i) => [trace.open[i], trace.close[i], trace.low[i], trace.high[i]]),
      itemStyle: {
        color: palette.brand,
        color0: palette.textMuted,
        borderColor: palette.brand,
        borderColor0: palette.textMuted,
      },
    },
  ];
}

function convertThemeRiverSeries(traces: any[], palette: ReturnType<typeof getThemePalette>) {
  const data: any[] = [];
  filter(traces, t => t.visible !== false).forEach(trace => {
    map(trace.x, (x, i) => {
      data.push([x, trace.y[i], trace.name]);
    });
  });

  return [
    {
      type: "themeRiver",
      data,
      label: { show: false },
      emphasis: { focus: "series" },
    },
  ];
}

function convertParallelSeries(traces: any[], options: any, palette: ReturnType<typeof getThemePalette>) {
  const yColumns = Object.entries(options.columnMapping ?? {})
    .filter(([, type]) => type === "y")
    .map(([col]) => col);

  const parallelAxis = map(yColumns, (name, index) => ({
    dim: index,
    name,
    axisLabel: { color: palette.textMuted },
  }));

  const rows: any[] = [];
  const visibleTraces = filter(traces, t => t.visible !== false);
  const tracesByName = Object.fromEntries(visibleTraces.map(t => [t.name, t]));
  const rowCount = Math.max(...yColumns.map(col => tracesByName[col]?.y?.length ?? 0), 0);

  for (let i = 0; i < rowCount; i += 1) {
    rows.push(map(yColumns, col => tracesByName[col]?.y?.[i]));
  }

  return {
    parallelAxis,
    series: [{ type: "parallel", lineStyle: { width: 2, opacity: 0.6 }, data: rows }],
  };
}

export function buildSpecialChartOption(
  chartType: string,
  traces: any[],
  layout: any,
  options: any,
  palette: ReturnType<typeof getThemePalette>
) {
  switch (chartType) {
    case "effectScatter":
      return { series: convertEffectScatterSeries(traces, palette) };
    case "pictorialBar":
      return { series: convertPictorialBarSeries(traces, options, palette) };
    case "radar": {
      const radar = convertRadarSeries(traces, palette);
      return {
        radar: {
          indicator: radar.indicators,
          axisName: { color: palette.textMuted, fontFamily: palette.fontFamily },
          splitLine: { lineStyle: { color: palette.divider } },
          splitArea: { areaStyle: { color: [palette.surface, palette.surfaceAlt] } },
        },
        series: radar.series,
      };
    }
    case "treemap":
      return { series: convertTreemapSeries(traces, palette), grid: undefined };
    case "gauge":
      return { series: convertGaugeSeries(traces, palette), grid: undefined };
    case "candlestick":
      return {
        series: convertCandlestickSeries(traces, palette),
        xAxis: { type: "category", data: traces[0]?.x, axisLabel: { color: palette.textMuted } },
        yAxis: { scale: true, axisLabel: { color: palette.textMuted }, splitLine: { lineStyle: { color: palette.divider } } },
      };
    case "themeRiver":
      return {
        series: convertThemeRiverSeries(traces, palette),
        singleAxis: { type: "time", axisLabel: { color: palette.textMuted } },
        grid: undefined,
        dataZoom: undefined,
      };
    case "parallel": {
      const parallel = convertParallelSeries(traces, options, palette);
      return {
        parallelAxis: parallel.parallelAxis,
        parallel: { left: 40, right: 40, bottom: 30, top: 30, parallelAxisDefault: { type: "value" } },
        series: parallel.series,
        grid: undefined,
        dataZoom: undefined,
      };
    }
    default:
      return null;
  }
}

export function resolveTraceEchartsType(traceType: string): string {
  return getEChartsSeriesType(traceType);
}

export function applyTraceEchartsType(base: any, traceType: string) {
  const echartsType = resolveTraceEchartsType(traceType);
  if (echartsType === "effectScatter") {
    return { ...base, type: "effectScatter", rippleEffect: { scale: 2.5, brushType: "stroke" }, symbolSize: 10 };
  }
  if (echartsType === "pictorialBar") {
    return {
      ...base,
      type: "pictorialBar",
      symbol: "roundRect",
      symbolRepeat: true,
      symbolSize: ["100%", 4],
      symbolClip: true,
    };
  }
  if (echartsType === "bar") {
    return { ...base, type: "bar" };
  }
  return { ...base, type: echartsType };
}
