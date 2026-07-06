import React, { useState, useEffect, useMemo } from "react";
import resizeObserver from "@/services/resizeObserver";
import { RendererPropTypes } from "@/visualizations/prop-types";
import echarts from "@/visualizations/shared/echarts/register";
import { createChartInstance, getThemePalette } from "@/visualizations/shared/echarts/createChartInstance";
import { SankeyDataType } from "./index";
import { prepareSankeyGraph, prepareSankeyRows } from "./prepareData";
import "./renderer.less";

export default function Renderer({ data }: { data: SankeyDataType }) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const graphData = useMemo(() => prepareSankeyGraph(prepareSankeyRows(data.rows)), [data]);

  useEffect(() => {
    if (!container || graphData.nodes.length === 0) {
      return;
    }

    const palette = getThemePalette();
    const { destroy } = createChartInstance(container, {
      tooltip: { trigger: "item", triggerOn: "mousemove" },
      series: [
        {
          type: "sankey",
          layout: "none",
          emphasis: { focus: "adjacency" },
          data: graphData.nodes.map(n => ({ name: n.name, itemStyle: n.itemStyle })),
          links: graphData.links,
          lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.4 },
          label: { color: palette.text, fontFamily: palette.fontFamily, fontSize: 11 },
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
  }, [container, graphData]);

  return <div className="sankey-visualization-container" ref={setContainer} />;
}

Renderer.propTypes = RendererPropTypes;
