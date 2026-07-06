import React, { useMemo, useState, useEffect } from "react";
import resizeObserver from "@/services/resizeObserver";
import { RendererPropTypes } from "@/visualizations/prop-types";
import echarts from "@/visualizations/shared/echarts/register";
import { createChartInstance, getThemePalette } from "@/visualizations/shared/echarts/createChartInstance";
import ColorPalette from "@/visualizations/ColorPalette";
import { createNumberFormatter } from "@/lib/value-format";
import prepareData from "./prepareData";
import "./index.less";

export default function Renderer({ data, options }: any) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const funnelData = useMemo(() => prepareData(data.rows, options), [data, options]);
  const formatValue = useMemo(() => createNumberFormatter(options.numberFormat), [options.numberFormat]);

  useEffect(() => {
    if (!container || funnelData.length === 0) {
      return;
    }

    const palette = getThemePalette();
    const { destroy } = createChartInstance(container, {
      tooltip: {
        trigger: "item",
        formatter: (params: any) => `${params.name}: ${formatValue(params.value)}`,
      },
      series: [
        {
          type: "funnel",
          left: "10%",
          top: 20,
          bottom: 20,
          width: "80%",
          min: 0,
          max: funnelData[0]?.value ?? 100,
          minSize: "10%",
          maxSize: "100%",
          sort: "descending",
          gap: 4,
          label: {
            show: true,
            position: "inside",
            formatter: (params: any) => `${params.name}\n${formatValue(params.value)}`,
            color: "#fff",
            fontFamily: palette.fontFamily,
            fontSize: 12,
          },
          itemStyle: {
            borderColor: palette.surface,
            borderWidth: 2,
          },
          emphasis: {
            label: { fontSize: 14 },
          },
          data: funnelData.map((d: any) => ({
            name: d.step,
            value: d.value,
          })),
          color: [ColorPalette.Cyan, ColorPalette["Light Blue"], ColorPalette.Indigo, ColorPalette.Forest, ColorPalette.Orange],
        },
      ],
    });

    const unwatch = resizeObserver(container, () => {
      echarts.getInstanceByDom(container)?.resize();
    });

    return () => {
      unwatch();
      destroy();
    };
  }, [container, funnelData, formatValue]);

  if (funnelData.length === 0) {
    return null;
  }

  return <div className="funnel-visualization-container" ref={setContainer} />;
}

Renderer.propTypes = RendererPropTypes;
