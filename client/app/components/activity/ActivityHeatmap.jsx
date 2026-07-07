import React, { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { HeatmapChart } from "echarts/charts";
import { CalendarComponent, TooltipComponent, VisualMapComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([HeatmapChart, CalendarComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

function readVar(name, fallback) {
  if (typeof document === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function formatDayLabel(value) {
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

export default function ActivityHeatmap({ daily, height = 150 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !daily?.length) {
      return undefined;
    }

    const text = readVar("--rd-color-text", "#1f1a16");
    const textMuted = readVar("--rd-color-text-muted", "#7a7068");
    const surface = readVar("--rd-color-surface", "#ffffff");
    const border = readVar("--rd-color-border", "#ece8e1");
    const brand = readVar("--rd-color-brand", "#ff7230");
    const brandSoft = readVar("--rd-color-brand-soft", "#fff1ea");
    const fontFamily = readVar(
      "--rd-font",
      '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    );

    const counts = daily.map(item => item.count);
    const maxCount = Math.max(...counts, 1);
    const startDate = daily[0].date;
    const endDate = daily[daily.length - 1].date;
    const heatmapData = daily.map(item => [item.date, item.count]);

    const chart = echarts.init(container);
    chart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        backgroundColor: surface,
        borderColor: border,
        textStyle: { color: text, fontFamily },
        formatter(params) {
          const value = params.value?.[1] ?? 0;
          const day = params.value?.[0];
          return `${formatDayLabel(day)}<br/>${value} contribution${value === 1 ? "" : "s"}`;
        },
      },
      visualMap: {
        min: 0,
        max: maxCount,
        calculable: false,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        itemWidth: 10,
        itemHeight: 10,
        inRange: {
          color: [brandSoft, brand],
        },
        textStyle: { color: textMuted, fontSize: 11, fontFamily },
      },
      calendar: {
        top: 28,
        left: 24,
        right: 12,
        bottom: 36,
        range: [startDate, endDate],
        cellSize: ["auto", 13],
        splitLine: { show: false },
        itemStyle: {
          borderWidth: 3,
          borderColor: surface,
        },
        dayLabel: {
          firstDay: 1,
          nameMap: ["S", "M", "T", "W", "T", "F", "S"],
          color: textMuted,
          fontSize: 10,
          fontFamily,
        },
        monthLabel: {
          color: textMuted,
          fontSize: 11,
          fontFamily,
        },
        yearLabel: { show: false },
      },
      series: [
        {
          type: "heatmap",
          coordinateSystem: "calendar",
          data: heatmapData,
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [daily]);

  return <div ref={containerRef} style={{ width: "100%", height }} aria-label="Activity calendar" />;
}
