import React, { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

function readVar(name, fallback) {
  if (typeof document === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function shortDayLabel(value) {
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString(undefined, { weekday: "short" });
}

export default function ActivityWeekChart({ week, height = 160 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !week?.length) {
      return undefined;
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

    const chart = echarts.init(container);
    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 8, right: 8, top: 16, bottom: 24, containLabel: true },
      tooltip: {
        trigger: "axis",
        backgroundColor: surface,
        borderColor: border,
        textStyle: { color: text, fontFamily },
        formatter(params) {
          const item = params[0];
          const day = week[item.dataIndex]?.date;
          return `${shortDayLabel(day)}<br/>${item.value} contribution${item.value === 1 ? "" : "s"}`;
        },
      },
      xAxis: {
        type: "category",
        data: week.map(item => shortDayLabel(item.date)),
        axisLabel: { color: textMuted, fontFamily, fontSize: 11 },
        axisLine: { lineStyle: { color: divider } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        axisLabel: { color: textMuted, fontFamily, fontSize: 11 },
        splitLine: { lineStyle: { color: divider } },
      },
      series: [
        {
          type: "bar",
          data: week.map(item => item.count),
          itemStyle: {
            color: brand,
            borderRadius: [4, 4, 0, 0],
          },
          barMaxWidth: 28,
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [week]);

  return <div ref={containerRef} style={{ width: "100%", height }} aria-label="Weekly activity chart" />;
}
