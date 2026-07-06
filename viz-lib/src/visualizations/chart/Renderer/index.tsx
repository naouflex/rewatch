import React from "react";
import { RendererPropTypes } from "@/visualizations/prop-types";

import EChartsChart from "./EChartsChart";
import CustomEChartsChart from "./CustomEChartsChart";
import { visualizationsSettings } from "@/visualizations/visualizationsSettings";

import "./renderer.less";

export default function Renderer({ options, ...props }: any) {
  if (options.globalSeriesType === "custom" && visualizationsSettings.allowCustomJSVisualizations) {
    return <CustomEChartsChart options={options} {...props} />;
  }
  return <EChartsChart options={options} {...props} />;
}

Renderer.propTypes = RendererPropTypes;
