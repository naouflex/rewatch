import prepareData from "./prepareData";
import prepareLayout from "./prepareLayout";
import toEChartsOption from "./toEChartsOption";

export default function prepareOption(
  element: HTMLElement,
  seriesList: any[],
  options: any,
  hideToolbox = false
) {
  const traces = prepareData(seriesList, options);
  const layout = prepareLayout(element, options, traces);
  return toEChartsOption(traces, layout, options, hideToolbox);
}

export { prepareData, prepareLayout, toEChartsOption };
export { prepareCustomChartData, createCustomChartRenderer } from "./customChartUtils";
