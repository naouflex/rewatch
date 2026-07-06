import echarts from "./register";
import getThemePalette from "./getThemePalette";
import resizeObserver from "@/services/resizeObserver";

export type ChartHandle = {
  destroy: () => void;
};

export function createChartInstance(container: HTMLElement, option: any): ChartHandle {
  const palette = getThemePalette();
  let chart: echarts.ECharts | null = null;
  let destroyed = false;

  const ensureChart = () => {
    if (destroyed) {
      return;
    }

    if (!chart) {
      if (container.clientWidth === 0 && container.clientHeight === 0) {
        return;
      }
      chart = echarts.init(container, undefined, { renderer: "canvas" });
      chart.setOption({
        textStyle: { color: palette.text, fontFamily: palette.fontFamily },
        ...option,
      });
      return;
    }

    chart.resize();
  };

  ensureChart();
  const unwatch = resizeObserver(container, ensureChart);

  return {
    destroy: () => {
      destroyed = true;
      unwatch();
      chart?.dispose();
      chart = null;
    },
  };
}

export { echarts, getThemePalette };
