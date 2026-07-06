import React, { useState, useEffect, useContext, useRef } from "react";
import useMedia from "use-media";
import { ErrorBoundaryContext } from "@/components/ErrorBoundary";
import { RendererPropTypes } from "@/visualizations/prop-types";
import { visualizationsSettings } from "@/visualizations/visualizationsSettings";
import getChartData from "../getChartData";
import initChart from "./initEChartsChart";

export interface EChartsChartProps {
  data: {
    rows: any[];
    columns: any[];
  };
  options: object;
}

export default function EChartsChart({ options, data }: EChartsChartProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const [chart, setChart] = useState<any>(null);

  const errorHandler = useContext(ErrorBoundaryContext);
  const errorHandlerRef = useRef<any>();
  errorHandlerRef.current = errorHandler;

  const isMobile = useMedia({ maxWidth: 768 });
  const isMobileRef = useRef<boolean>();
  isMobileRef.current = isMobile;

  useEffect(() => {
    if (container) {
      let isDestroyed = false;

      const chartData = getChartData(data.rows, options);
      const _chart = initChart(container, options, chartData, visualizationsSettings, (error: any) => {
        errorHandlerRef.current?.handleError(error);
      });
      _chart.initialized.then(() => {
        if (!isDestroyed) {
          setChart(_chart);
        }
      });
      return () => {
        isDestroyed = true;
        _chart.destroy();
      };
    }
  }, [options, data, container]);

  useEffect(() => {
    if (chart) {
      chart.setZoomEnabled(!isMobile);
    }
  }, [chart, isMobile]);

  return <div className="chart-visualization-container" ref={setContainer} />;
}

EChartsChart.propTypes = RendererPropTypes;
