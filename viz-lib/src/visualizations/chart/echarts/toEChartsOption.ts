import { filter, map, isArray, isNil } from "lodash";
import getThemePalette from "./getThemePalette";
import { ColorPaletteArray } from "../../ColorPalette";
import { getPieDimensions } from "./preparePieData";
import { buildSpecialChartOption, applyTraceEchartsType } from "./specialCharts";
import { getChartTypeDef } from "../chartTypes";

function mapAxisType(type: string) {
  switch (type) {
    case "date":
    case "datetime":
      return "time";
    case "log":
    case "logarithmic":
      return "log";
    case "category":
      return "category";
    default:
      return "value";
  }
}

function buildAxisConfig(layoutAxis: any, palette: ReturnType<typeof getThemePalette>, position?: "left" | "right") {
  if (!layoutAxis) {
    return null;
  }
  const title = layoutAxis.title?.text ?? layoutAxis.title ?? "";
  return {
    type: mapAxisType(layoutAxis.type),
    name: title,
    nameTextStyle: { color: palette.text, fontFamily: palette.fontFamily, fontSize: 12 },
    axisLine: { show: false },
    axisTick: { show: true, lineStyle: { color: palette.divider } },
    splitLine: { lineStyle: { color: palette.divider, width: 1 } },
    axisLabel: {
      color: palette.textMuted,
      fontFamily: palette.fontFamily,
      fontSize: 11,
      show: layoutAxis.showticklabels !== false,
    },
    min: layoutAxis.range?.[0],
    max: layoutAxis.range?.[1],
    position,
    scale: layoutAxis.type === "log",
  };
}

function getLineStyle(shape: string) {
  switch (shape) {
    case "spline":
      return { smooth: true };
    case "hv":
      return { step: "end" };
    case "vh":
      return { step: "start" };
    default:
      return { smooth: false };
  }
}

function convertDefaultSeries(traces: any[], layout: any, options: any, palette: ReturnType<typeof getThemePalette>) {
  const isHorizontal = options.swappedAxes;
  const stackName = layout.barmode === "relative" || options.series?.stacking ? "total" : undefined;

  return filter(traces, t => t.visible !== false).map(trace => {
    const color = trace.marker?.color ?? trace.line?.color ?? palette.brand;
    const yAxisIndex = trace.yaxis === "y2" ? 1 : 0;
    const showLabel = options.showDataLabels && trace.text?.length;

    const base: any = {
      name: trace.name,
      yAxisIndex,
      label: {
        show: !!showLabel,
        formatter: (params: any) => trace.text?.[params.dataIndex] ?? "",
        color: trace.insidetextfont?.color ?? palette.text,
        fontFamily: palette.fontFamily,
        fontSize: 11,
      },
      itemStyle: { color },
      emphasis: { focus: "series" },
    };

    if (stackName) {
      base.stack = stackName;
    }

    const data = map(trace.x, (x, i) => {
      const y = trace.y[i];
      const point: any = isHorizontal ? [y, x] : [x, y];
      if (trace.error_y?.array?.[i]) {
        point.error = trace.error_y.array[i];
      }
      return point;
    });

    switch (trace.type) {
      case "bar":
      case "column":
        return applyTraceEchartsType(
          {
            ...base,
            data: isHorizontal ? map(trace.y, (y, i) => [y, trace.x[i]]) : map(trace.x, (x, i) => [x, trace.y[i]]),
          },
          trace.type
        );
      case "scatter":
      case "effectScatter":
        if (trace.mode?.includes("markers") && trace.marker?.size) {
          return applyTraceEchartsType(
            {
              ...base,
              symbolSize: (val: any, params: any) => trace.marker.size[params.dataIndex] ?? 10,
              data: map(trace.x, (x, i) => [x, trace.y[i]]),
            },
            trace.type
          );
        }
        return applyTraceEchartsType(
          {
            ...base,
            data: map(trace.x, (x, i) => [x, trace.y[i]]),
          },
          trace.type
        );
      case "pictorialBar":
        return applyTraceEchartsType(
          {
            ...base,
            data: isHorizontal ? map(trace.y, (y, i) => [y, trace.x[i]]) : map(trace.x, (x, i) => [x, trace.y[i]]),
          },
          trace.type
        );
      case "box":
        return {
          ...base,
          type: "boxplot",
          data: [trace.y],
        };
      case "line":
      case "scattergl":
      case "area":
      default: {
        const isArea = trace.type === "area" || trace.fill === "tozeroy" || trace.fill === "tonexty";
        const lineOpts = getLineStyle(trace.line?.shape ?? options.lineShape);
        return {
          ...base,
          type: "line",
          data,
          ...lineOpts,
          areaStyle: isArea ? { opacity: 0.25 } : undefined,
          showSymbol: trace.mode?.includes("markers") ?? !isArea,
        };
      }
    }
  });
}

function convertPieSeries(traces: any[], layout: any, options: any, palette: ReturnType<typeof getThemePalette>) {
  const { rows, cellsInRow, cellWidth, cellHeight, xPadding, yPadding } = getPieDimensions(traces);

  return filter(traces, t => t.visible !== false).map((trace, index) => {
    const xPos = (index % cellsInRow) * cellWidth;
    const yPos = Math.floor(index / cellsInRow) * cellHeight;
    const centerX = `${((xPos + (cellWidth - xPadding) / 2) * 100).toFixed(1)}%`;
    const centerY = `${((yPos + cellHeight - yPadding / 2) * 100).toFixed(1)}%`;
    const radius = `${Math.min(cellWidth, cellHeight) * 35}%`;

    return {
      type: "pie",
      name: trace.name,
      center: [centerX, centerY],
      radius: trace.hole ? [`${trace.hole * 100}%`, radius] : radius,
      data: map(trace.labels, (label, i) => ({
        name: label,
        value: trace.values[i],
        itemStyle: { color: trace.marker?.colors?.[i] },
      })),
      label: {
        show: options.showDataLabels,
        color: palette.text,
        fontFamily: palette.fontFamily,
        formatter: (params: any) => trace.text?.[params.dataIndex] ?? params.name,
      },
      clockwise: trace.direction !== "counterclockwise",
      emphasis: { focus: "self" },
    };
  });
}

function convertHeatmapSeries(traces: any[], options: any, palette: ReturnType<typeof getThemePalette>): {
  series: any[];
  xAxisData: any;
  yAxisData: any;
  visualMap: any;
} {
  const heatmapTrace = traces.find(t => t.type === "heatmap");
  if (!heatmapTrace) {
    return { series: [], xAxisData: [], yAxisData: [], visualMap: undefined };
  }

  const data: any[] = [];
  heatmapTrace.z.forEach((row: number[], yi: number) => {
    row.forEach((val: number, xi: number) => {
      data.push([xi, yi, val ?? "-"]);
    });
  });

  const zMax = Math.max(...heatmapTrace.z.flat().filter((v: number) => isFinite(v)));
  const zMin = Math.min(...heatmapTrace.z.flat().filter((v: number) => isFinite(v)));

  const series: any[] = [
    {
      type: "heatmap",
      data,
      label: { show: options.showDataLabels, fontFamily: palette.fontFamily },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.3)" } },
    },
  ];

  return {
    series,
    xAxisData: heatmapTrace.x,
    yAxisData: heatmapTrace.y,
    visualMap: {
      min: zMin,
      max: zMax,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: {
        color: map(heatmapTrace.colorscale ?? [], (entry: [number, string]) => entry[1]),
      },
      textStyle: { color: palette.textMuted, fontFamily: palette.fontFamily },
    },
  };
}

export default function toEChartsOption(traces: any[], layout: any, options: any, hideToolbox = false) {
  const palette = getThemePalette();
  const chartType = options.globalSeriesType;
  const chartDef = getChartTypeDef(chartType);
  const isPie = chartType === "pie";
  const isHeatmap = chartType === "heatmap";
  const isHorizontal = options.swappedAxes && !isPie && !isHeatmap && chartDef?.hasAxes !== false;
  const specialChart = buildSpecialChartOption(chartType, traces, layout, options, palette);

  let series: any[];
  let xAxisData: any;
  let yAxisData: any;
  let visualMap: any;
  let grid: any = { left: 16, right: 16, top: 24, bottom: 8, containLabel: true };

  if (isPie) {
    series = convertPieSeries(traces, layout, options, palette);
    grid = undefined;
  } else if (isHeatmap) {
    const heatmap = convertHeatmapSeries(traces, options, palette) as {
      series: any[];
      xAxisData: any;
      yAxisData: any;
      visualMap: any;
    };
    series = heatmap.series;
    xAxisData = heatmap.xAxisData;
    yAxisData = heatmap.yAxisData;
    visualMap = heatmap.visualMap;
    grid.bottom = 40;
  } else if (specialChart) {
    series = specialChart.series;
    if (specialChart.grid !== undefined) {
      grid = specialChart.grid;
    }
  } else {
    series = convertDefaultSeries(traces, layout, options, palette);
  }

  const hasY2 = layout.yaxis2 != null;
  const xAxisConfig = buildAxisConfig(layout.xaxis, palette);
  const yAxisConfig = buildAxisConfig(layout.yaxis, palette, "left");
  const y2AxisConfig = hasY2 ? buildAxisConfig(layout.yaxis2, palette, "right") : null;
  const disableDataZoom = specialChart && Object.prototype.hasOwnProperty.call(specialChart, "dataZoom");
  const showDataZoom = !isPie && !isHeatmap && chartDef?.hasAxes !== false && !disableDataZoom;

  const option: any = {
    backgroundColor: "transparent",
    color: ColorPaletteArray,
    textStyle: { color: palette.text, fontFamily: palette.fontFamily, fontSize: 12 },
    tooltip: {
      trigger: isPie || chartType === "treemap" || chartType === "gauge" ? "item" : "axis",
      backgroundColor: palette.surface,
      borderColor: palette.border,
      textStyle: { color: palette.text, fontFamily: palette.fontFamily },
      axisPointer: isPie || chartType === "treemap" ? undefined : { type: "cross", crossStyle: { color: palette.divider } },
    },
    legend: {
      show: layout.showlegend !== false && options.legend?.enabled !== false && chartDef?.hasLegend !== false,
      textStyle: { color: palette.text, fontFamily: palette.fontFamily },
      bottom: options.legend?.placement === "below" ? 0 : undefined,
      type: "scroll",
    },
    grid,
    toolbox: hideToolbox
      ? { show: false }
      : {
          show: chartDef?.hasAxes !== false,
          right: 8,
          feature: {
            dataZoom: { yAxisIndex: "none" },
            restore: {},
            saveAsImage: {},
          },
          iconStyle: { borderColor: palette.textMuted },
        },
    dataZoom: showDataZoom ? [{ type: "inside" }, { type: "slider", bottom: 4, height: 20 }] : undefined,
    series,
    visualMap,
  };

  if (specialChart) {
    const { series: _s, grid: _g, dataZoom: _d, ...specialRest } = specialChart;
    Object.assign(option, specialRest);
    option.series = series;
  }

  if (!isPie && chartDef?.hasAxes !== false && !option.xAxis && !option.radar && !option.parallel) {
    if (isHorizontal) {
      option.xAxis = yAxisConfig ? [{ ...yAxisConfig, type: mapAxisType(layout.yaxis?.type ?? "linear") }] : [{ type: "value" }];
      option.yAxis = xAxisConfig
        ? [{ ...xAxisConfig, type: "category", data: xAxisData ?? series[0]?.data?.map((d: any) => d[1]) }]
        : [{ type: "category" }];
    } else if (isHeatmap) {
      option.xAxis = { type: "category", data: xAxisData, splitArea: { show: false }, axisLabel: { color: palette.textMuted } };
      option.yAxis = { type: "category", data: yAxisData, splitArea: { show: false }, axisLabel: { color: palette.textMuted } };
    } else {
      option.xAxis = xAxisConfig
        ? [{ ...xAxisConfig, data: xAxisConfig.type === "category" ? series[0]?.data?.map((d: any) => d[0]) : undefined }]
        : [{ type: "category" }];
      option.yAxis = y2AxisConfig ? [yAxisConfig, y2AxisConfig] : yAxisConfig ? [yAxisConfig] : [{ type: "value" }];
    }
  }

  if (layout.annotations?.length) {
    option.graphic = map(layout.annotations, (ann: any) => ({
      type: "text",
      left: `${ann.x * 100}%`,
      top: `${(1 - ann.y) * 100}%`,
      style: {
        text: ann.text,
        fill: palette.textMuted,
        fontFamily: palette.fontFamily,
        fontSize: 11,
        textAlign: "center",
      },
    }));
  }

  return option;
}
