import React, { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

function readVar(name, fallback) {
  if (typeof document === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export default function EChartsLineChart({ data, height = 300, color }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !data?.length) {
      return;
    }

    const text = readVar("--rd-color-text", "#1f1a16");
    const textMuted = readVar("--rd-color-text-muted", "#7a7068");
    const surface = readVar("--rd-color-surface", "#ffffff");
    const border = readVar("--rd-color-border", "#ece8e1");
    const divider = readVar("--rd-color-divider", "#f1eee8");
    const brand = readVar("--rd-color-brand", "#ff7230");
    const fontFamily = readVar(
      "--rd-font",
      '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    );
    const lineColor = color ?? brand;

    const chart = echarts.init(container);

    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 48, right: 24, top: 24, bottom: 32, containLabel: true },
      tooltip: {
        trigger: "axis",
        backgroundColor: surface,
        borderColor: border,
        textStyle: { color: text, fontFamily },
      },
      xAxis: {
        type: "category",
        data: data.map(d => d.date),
        axisLabel: { color: textMuted, fontFamily, fontSize: 11 },
        axisLine: { lineStyle: { color: divider } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: textMuted, fontFamily, fontSize: 11 },
        splitLine: { lineStyle: { color: divider } },
      },
      series: [
        {
          type: "line",
          data: data.map(d => d.value),
          smooth: true,
          symbol: "circle",
          symbolSize: 6,
          lineStyle: { width: 2, color: lineColor },
          itemStyle: { color: lineColor },
          areaStyle: { color: lineColor, opacity: 0.08 },
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [data, color]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
