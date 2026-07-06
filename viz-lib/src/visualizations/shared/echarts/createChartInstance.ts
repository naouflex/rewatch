import echarts from "./register";
import getThemePalette from "./getThemePalette";
import resizeObserver from "@/services/resizeObserver";

export type ChartHandle = {
  chart: echarts.ECharts;
  destroy: () => void;
};

export function createChartInstance(container: HTMLElement, option: any): ChartHandle {
  const palette = getThemePalette();
  const chart = echarts.init(container, undefined, { renderer: "canvas" });
  chart.setOption({
    textStyle: { color: palette.text, fontFamily: palette.fontFamily },
    ...option,
  });

  const unwatch = resizeObserver(container, () => chart.resize());

  return {
    chart,
    destroy: () => {
      unwatch();
      chart.dispose();
    },
  };
}

export { echarts, getThemePalette };
