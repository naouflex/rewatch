import React, { useEffect, useRef } from "react";
import echarts from "@/visualizations/shared/echarts/register";
import getThemePalette from "@/visualizations/shared/echarts/getThemePalette";
import ColorPalette from "@/visualizations/ColorPalette";

function makeRenderer(chartType: string, chartOptions: any = {}) {
  return function EChartsPivotRenderer(props: any) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<echarts.ECharts | null>(null);

    useEffect(() => {
      const container = containerRef.current;
      if (!container) {
        return;
      }

      const palette = getThemePalette();
      chartRef.current = echarts.init(container);

      const { cols, rows, aggregatorName, vals } = props;
      const pivotData = props.pivotData ?? props.data;

      let categories: string[] = [];
      let seriesData: any[] = [];

      if (pivotData?.getRowKeys && pivotData?.getColKeys) {
        categories = pivotData.getColKeys().map((k: any) => k.join("-") || "Total");
        const rowKeys = pivotData.getRowKeys();
        seriesData = rowKeys.map((rowKey: any) => ({
          name: rowKey.join("-") || "Series",
          type: chartType,
          data: pivotData.getColKeys().map((colKey: any) => {
            const val = pivotData.getAggregator(aggregatorName, vals)([], rowKey, colKey);
            return val.value?.() ?? 0;
          }),
          ...(chartType === "line" ? { smooth: true } : {}),
          ...(chartType === "bar" ? { itemStyle: { color: ColorPalette.Cyan } } : {}),
        }));
      }

      chartRef.current.setOption({
        textStyle: { color: palette.text, fontFamily: palette.fontFamily },
        tooltip: { trigger: "axis" },
        legend: { textStyle: { color: palette.textMuted } },
        grid: { left: 40, right: 20, top: 30, bottom: 30, containLabel: true },
        xAxis: {
          type: "category",
          data: categories,
          axisLabel: { color: palette.textMuted, fontFamily: palette.fontFamily },
        },
        yAxis: {
          type: "value",
          axisLabel: { color: palette.textMuted },
          splitLine: { lineStyle: { color: palette.divider } },
        },
        series: seriesData,
        ...chartOptions,
      });

      const ro = new ResizeObserver(() => chartRef.current?.resize());
      ro.observe(container);

      return () => {
        ro.disconnect();
        chartRef.current?.dispose();
        chartRef.current = null;
      };
    }, [props]);

    return <div ref={containerRef} style={{ width: "100%", height: 400 }} />;
  };
}

export default {
  "Grouped Column Chart": makeRenderer("bar"),
  "Stacked Column Chart": makeRenderer("bar", { series: [{ stack: "total" }] }),
  "Grouped Bar Chart": makeRenderer("bar"),
  "Stacked Bar Chart": makeRenderer("bar", { series: [{ stack: "total" }] }),
  "Line Chart": makeRenderer("line"),
  "Scatter Chart": makeRenderer("scatter"),
  "Multiple Pie Chart": makeRenderer("pie"),
};
