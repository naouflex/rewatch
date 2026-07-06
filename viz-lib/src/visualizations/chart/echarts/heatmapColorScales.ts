const BUILTIN_COLOR_SCALES: Record<string, [number, string][]> = {
  Bluered: [
    [0, "rgb(0,0,255)"],
    [1, "rgb(255,0,0)"],
  ],
  Greys: [
    [0, "rgb(0,0,0)"],
    [1, "rgb(255,255,255)"],
  ],
  YlGnBu: [
    [0, "#ffffcc"],
    [0.25, "#a1dab4"],
    [0.5, "#41b6c4"],
    [0.75, "#2c7fb8"],
    [1, "#253494"],
  ],
  YlOrRd: [
    [0, "#ffffcc"],
    [0.25, "#fed976"],
    [0.5, "#fd8d3c"],
    [0.75, "#e31a1c"],
    [1, "#800026"],
  ],
  Blues: [
    [0, "#f7fbff"],
    [0.25, "#c6dbef"],
    [0.5, "#6baed6"],
    [0.75, "#2171b5"],
    [1, "#08306b"],
  ],
  Viridis: [
    [0, "#440154"],
    [0.25, "#3b528b"],
    [0.5, "#21918c"],
    [0.75, "#5ec962"],
    [1, "#fde725"],
  ],
  Hot: [
    [0, "#000000"],
    [0.3, "#ff0000"],
    [0.6, "#ffff00"],
    [1, "#ffffff"],
  ],
  Jet: [
    [0, "#00007f"],
    [0.35, "#00ffff"],
    [0.66, "#ffff00"],
    [1, "#7f0000"],
  ],
};

export default function getHeatmapColorScale(schemeName: string): [number, string][] {
  return BUILTIN_COLOR_SCALES[schemeName] || BUILTIN_COLOR_SCALES.YlGnBu;
}
