import React, { useState, useEffect, useMemo } from "react";
import resizeObserver from "@/services/resizeObserver";
import { RendererPropTypes } from "@/visualizations/prop-types";
import echarts from "@/visualizations/shared/echarts/register";
import { createChartInstance, getThemePalette } from "@/visualizations/shared/echarts/createChartInstance";
import { SankeyDataType } from "./index";
import { prepareSankeyGraph, prepareSankeyRows } from "./prepareData";
import "./renderer.less";

function buildSankeySeries(graphData: ReturnType<typeof prepareSankeyGraph>) {
  const nodes = graphData.nodes.map(n => ({ name: n.name, itemStyle: n.itemStyle }));
  const nodeNames = new Set(nodes.map(n => n.name));
  const links = graphData.links
    .filter(link => link.value > 0)
    .map(link => ({
      source: graphData.nodes[link.source]?.name,
      target: graphData.nodes[link.target]?.name,
      value: link.value,
    }))
    .filter(link => link.source && link.target && nodeNames.has(link.source) && nodeNames.has(link.target));

  return { nodes, links };
}

export default function Renderer({ data }: { data: SankeyDataType }) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const graphData = useMemo(() => prepareSankeyGraph(prepareSankeyRows(data.rows)), [data]);

  useEffect(() => {
    if (!container || graphData.nodes.length === 0) {
      return;
    }

    const palette = getThemePalette();
    const { nodes, links } = buildSankeySeries(graphData);
    if (links.length === 0) {
      return;
    }

    const { destroy } = createChartInstance(container, {
      tooltip: { trigger: "item", triggerOn: "mousemove" },
      series: [
        {
          type: "sankey",
          layout: "none",
          emphasis: { focus: "adjacency" },
          data: nodes,
          links,
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
