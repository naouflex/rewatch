import React, { useState, useEffect, useMemo } from "react";
import { RendererPropTypes } from "@/visualizations/prop-types";
import resizeObserver from "@/services/resizeObserver";
import echarts from "@/visualizations/shared/echarts/register";
import getChartData from "../getChartData";
import { prepareCustomChartData, createCustomChartRenderer } from "../echarts";

export default function CustomEChartsChart({ options, data }: any) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  const renderCustomChart = useMemo(
    () => createCustomChartRenderer(options.customCode, options.enableConsoleLogs),
    [options.customCode, options.enableConsoleLogs]
  );

  const chartData = useMemo(() => prepareCustomChartData(getChartData(data.rows, options)), [options, data]);

  useEffect(() => {
    if (container) {
      const unwatch = resizeObserver(container, () => {
        const existing = echarts.getInstanceByDom(container);
        if (existing) {
          existing.dispose();
        }
        renderCustomChart(chartData.x, chartData.ys, container, echarts);
      });
      return unwatch;
    }
  }, [container, chartData, renderCustomChart]);

  useEffect(() => {
    if (container) {
      return () => {
        const existing = echarts.getInstanceByDom(container);
        if (existing) {
          existing.dispose();
        }
      };
    }
  }, [container]);

  return <div className="chart-visualization-container" ref={setContainer} />;
}

CustomEChartsChart.propTypes = RendererPropTypes;
