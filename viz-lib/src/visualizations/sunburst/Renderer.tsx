import React, { useState, useEffect, useMemo } from "react";
import resizeObserver from "@/services/resizeObserver";
import { RendererPropTypes } from "@/visualizations/prop-types";
import echarts from "@/visualizations/shared/echarts/register";
import { createChartInstance, getThemePalette } from "@/visualizations/shared/echarts/createChartInstance";
import { buildSunburstHierarchy, isSunburstDataValid } from "./prepareHierarchy";
import "./renderer.less";

function pruneExitNodes(node: any): any {
  if (!node.children?.length) {
    return node;
  }

  const children = node.children.filter((child: any) => !String(child.id).endsWith(" · Exit")).map(pruneExitNodes);
  return children.length ? { ...node, children } : { id: node.id, value: node.value ?? 0 };
}

function toEChartsNode(node: any): any {
  const name = String(node.id);
  if (!node.children?.length) {
    return { name, value: node.value ?? 0 };
  }

  return {
    name,
    children: node.children.map(toEChartsNode),
  };
}

export default function Renderer({ data }: any) {
  const chartData = useMemo(() => {
    if (!isSunburstDataValid(data)) {
      return null;
    }
    const hierarchy = pruneExitNodes(buildSunburstHierarchy(data.rows));
    const children = hierarchy.children?.map(toEChartsNode) ?? [];
    return children.length ? children : null;
  }, [data]);

  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!container || !chartData) {
      return;
    }

    const palette = getThemePalette();
    const { destroy } = createChartInstance(container, {
      tooltip: {
        trigger: "item",
        formatter: (params: any) => `${params.name}: ${params.value}`,
      },
      series: [
        {
          type: "sunburst",
          data: chartData,
          radius: [0, "90%"],
          label: { show: false },
          itemStyle: {
            borderWidth: 1,
            borderColor: palette.surface,
          },
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
  }, [container, chartData]);

  if (!chartData) {
    return null;
  }

  return (
    <div className="sunburst-visualization-container" style={{ height: "100%", width: "100%" }} ref={setContainer} />
  );
}

Renderer.propTypes = RendererPropTypes;
