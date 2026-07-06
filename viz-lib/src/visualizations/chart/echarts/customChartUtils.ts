import { each } from "lodash";
import { normalizeValue } from "./utils";

export function prepareCustomChartData(series: any) {
  const x: any = [];
  const ys: Record<string, any[]> = {};

  each(series, ({ name, data }) => {
    ys[name] = [];
    each(data, point => {
      x.push(normalizeValue(point.x, "category"));
      ys[name].push(normalizeValue(point.y, "linear"));
    });
  });

  return { x, ys };
}

export function createCustomChartRenderer(code: string, logErrorsToConsole = false) {
  let render: (x: any, ys: any, element: HTMLElement, echarts: any) => void = () => {};
  try {
    render = new Function("x, ys, element, echarts", code) as typeof render; // eslint-disable-line no-new-func
  } catch (err) {
    if (logErrorsToConsole) {
      console.log(`Error while executing custom graph: ${err}`); // eslint-disable-line no-console
    }
  }

  return (x: any, ys: any, element: HTMLElement, echartsLib: any) => {
    try {
      render(x, ys, element, echartsLib);
    } catch (err) {
      if (logErrorsToConsole) {
        console.log(`Error while executing custom graph: ${err}`); // eslint-disable-line no-console
      }
    }
  };
}
