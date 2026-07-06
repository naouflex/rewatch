import { isString, isFunction, isNil } from "lodash";
import resizeObserver from "@/services/resizeObserver";
import { formatSimpleTemplate } from "@/lib/value-format";
import echarts from "@/visualizations/shared/echarts/register";
import prepareOption from "../echarts/prepareOption";

const navigateToUrl = (url: string, shouldOpenNewTab = true) =>
  shouldOpenNewTab ? window.open(url, "_blank") : (window.location.href = url);

function createErrorHandler(errorHandler: (error: any) => void) {
  return (error: any) => {
    if (isString(error) && error.startsWith("ax.dtick error")) {
      return;
    }
    errorHandler(error);
  };
}

export default function initChart(
  container: HTMLElement,
  options: any,
  data: any,
  additionalOptions: { hidePlotlyModeBar?: boolean; hideChartToolbox?: boolean },
  onError: (error: any) => void
) {
  const handleError = createErrorHandler(onError);
  const hideToolbox = additionalOptions.hideChartToolbox ?? additionalOptions.hidePlotlyModeBar ?? false;

  let chart: echarts.ECharts | null = null;
  let isDestroyed = false;
  let unwatchResize = () => {};

  function createSafeFunction(fn: (...args: any[]) => any) {
    return (...args: any[]) => {
      if (!isDestroyed) {
        try {
          return fn(...args);
        } catch (error) {
          handleError(error);
        }
      }
    };
  }

  const promise = Promise.resolve()
    .then(
      createSafeFunction(() => {
        chart = echarts.init(container, undefined, { renderer: "canvas" });
        const option = prepareOption(container, data, options, hideToolbox);
        chart.setOption(option, { notMerge: true });

        if (options.enableLink) {
          chart.on(
            "click",
            createSafeFunction((params: any) => {
              try {
                const sourceData = params.data?.sourceData ?? params.data;
                const templateValues: Record<string, any> = {
                  "@@x": params.name ?? params.value?.[0],
                  "@@y": params.value?.[1] ?? params.value,
                };
                navigateToUrl(
                  formatSimpleTemplate(options.linkFormat, templateValues).replace(/{{\s*([^\s]+?)\s*}}/g, () => ""),
                  options.linkOpenNewTab
                );
              } catch (error: any) {
                console.error("Click error: [%s]", error.message, { error });
              }
            })
          );
        }

        if (isFunction(options.onHover)) {
          chart.on("mouseover", options.onHover);
        }
        if (isFunction(options.onUnHover)) {
          chart.on("mouseout", options.onUnHover);
        }

        unwatchResize = resizeObserver(
          container,
          createSafeFunction(() => {
            chart?.resize();
          })
        );
      })
    )
    .catch(handleError);

  const result: {
    initialized: Promise<any>;
    setZoomEnabled: (allowZoom: boolean) => void;
    destroy: () => void;
    getChart: () => echarts.ECharts | null;
  } = {
    initialized: Promise.resolve() as Promise<any>,
    setZoomEnabled: () => {},
    destroy: () => {},
    getChart: () => chart,
  };

  result.initialized = promise.then(() => result);
  result.setZoomEnabled = createSafeFunction((allowZoom: boolean) => {
    chart?.setOption({
      dataZoom: allowZoom ? [{ type: "inside" }, { type: "slider", bottom: 4, height: 20 }] : [],
    });
  });
  result.destroy = createSafeFunction(() => {
    isDestroyed = true;
    unwatchResize();
    if (chart) {
      chart.dispose();
      chart = null;
    }
  });

  return result;
}
