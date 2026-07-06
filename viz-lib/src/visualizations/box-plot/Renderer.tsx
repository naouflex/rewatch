import { map, each } from "lodash";
import React, { useState, useEffect, useMemo } from "react";
import resizeObserver from "@/services/resizeObserver";
import { RendererPropTypes } from "@/visualizations/prop-types";
import echarts from "@/visualizations/shared/echarts/register";
import { createChartInstance, getThemePalette } from "@/visualizations/shared/echarts/createChartInstance";
import ColorPalette from "@/visualizations/ColorPalette";
import "./renderer.less";

function computeBoxplotStats(values: number[]) {
  if (values.length === 0) {
    return [0, 0, 0, 0, 0];
  }
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p: number) => {
    const pos = (sorted.length - 1) * p;
    const base = Math.floor(pos);
    const rest = pos - base;
    if (sorted[base + 1] !== undefined) {
      return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
    }
    return sorted[base];
  };
  return [sorted[0], q(0.25), q(0.5), q(0.75), sorted[sorted.length - 1]];
}

function computeBoxplotData(data: any) {
  const columns = map(data.columns, col => col.name);
  return columns.map(column => {
    const values = data.rows.map((row: any) => row[column]).filter((v: any) => v != null && !isNaN(v));
    return { name: column, stats: computeBoxplotStats(values), values };
  });
}

export default function Renderer({ data, options }: any) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const boxData = useMemo(() => computeBoxplotData(data), [data]);

  useEffect(() => {
    if (!container || boxData.length === 0) {
      return;
    }

    const palette = getThemePalette();
    const categories = boxData.map(d => d.name);

    const { destroy } = createChartInstance(container, {
      grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: true },
      tooltip: { trigger: "item", axisPointer: { type: "shadow" } },
      xAxis: {
        type: "category",
        data: categories,
        axisLabel: { color: palette.textMuted, fontFamily: palette.fontFamily },
        name: options.xAxisLabel,
        nameTextStyle: { color: palette.text },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: palette.textMuted, fontFamily: palette.fontFamily },
        splitLine: { lineStyle: { color: palette.divider } },
        name: options.yAxisLabel,
        nameTextStyle: { color: palette.text },
      },
      series: [
        {
          name: "boxplot",
          type: "boxplot",
          data: boxData.map(d => d.stats),
          itemStyle: { color: ColorPalette.Cyan, borderColor: palette.brand },
        },
        ...(options.showPoints
          ? [
              {
                name: "outlier",
                type: "scatter",
                data: boxData.flatMap((d, i) => d.values.map((v: number) => [i, v])),
                itemStyle: { color: palette.brand, opacity: 0.6 },
              },
            ]
          : []),
      ],
    });

    const unwatch = resizeObserver(container, () => {
      echarts.getInstanceByDom(container)?.resize();
    });

    return () => {
      unwatch();
      destroy();
    };
  }, [container, boxData, options]);

  return <div className="box-plot-deprecated-visualization-container" ref={setContainer} />;
}

Renderer.propTypes = RendererPropTypes;
