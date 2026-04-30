import { isObject, isUndefined, filter, map } from "lodash";
import { getPieDimensions } from "./preparePieData";
import getThemePalette from "./getThemePalette";

function getAxisTitle(axis: any) {
  return isObject(axis.title) ? axis.title.text : null;
}

function getAxisScaleType(axis: any) {
  switch (axis.type) {
    case "datetime":
      return "date";
    case "logarithmic":
      return "log";
    default:
      return axis.type;
  }
}

function applyThemeToAxis(axis: any, palette: ReturnType<typeof getThemePalette>) {
  axis.gridcolor = palette.divider;
  axis.zerolinecolor = palette.border;
  axis.linecolor = palette.border;
  axis.tickcolor = palette.border;
  axis.tickfont = { color: palette.textMuted };
  if (axis.title && typeof axis.title === "string") {
    axis.title = { text: axis.title, font: { color: palette.text } };
  } else if (axis.title) {
    axis.title.font = { ...(axis.title.font || {}), color: palette.text };
  }
  return axis;
}

function prepareXAxis(axisOptions: any, additionalOptions: any) {
  const axis = {
    title: getAxisTitle(axisOptions),
    type: getAxisScaleType(axisOptions),
    automargin: true,
    tickformat: axisOptions.tickFormat ?? null,
  };

  if (additionalOptions.sortX && axis.type === "category") {
    if (additionalOptions.reverseX) {
      // @ts-expect-error ts-migrate(2339) FIXME: Property 'categoryorder' does not exist on type '{... Remove this comment to see the full error message
      axis.categoryorder = "category descending";
    } else {
      // @ts-expect-error ts-migrate(2339) FIXME: Property 'categoryorder' does not exist on type '{... Remove this comment to see the full error message
      axis.categoryorder = "category ascending";
    }
  }

  if (!isUndefined(axisOptions.labels)) {
    // @ts-expect-error ts-migrate(2339) FIXME: Property 'showticklabels' does not exist on type '... Remove this comment to see the full error message
    axis.showticklabels = axisOptions.labels.enabled;
  }

  return axis;
}

function prepareYAxis(axisOptions: any) {
  return {
    title: getAxisTitle(axisOptions),
    type: getAxisScaleType(axisOptions),
    automargin: true,
    autorange: true,
    range: null,
    tickformat: axisOptions.tickFormat ?? null,
  };
}

function preparePieLayout(layout: any, options: any, data: any) {
  const hasName = /{{\s*@@name\s*}}/.test(options.textFormat);

  const { cellsInRow, cellWidth, cellHeight, xPadding } = getPieDimensions(data);

  if (hasName) {
    layout.annotations = [];
  } else {
    layout.annotations = filter(
      map(data, (series, index) => {
        const xPosition = ((index as number) % cellsInRow) * cellWidth;
        const yPosition = Math.floor((index as number) / cellsInRow) * cellHeight;
        return {
          x: xPosition + (cellWidth - xPadding) / 2,
          y: yPosition + cellHeight - 0.015,
          xanchor: "center",
          yanchor: "top",
          text: series.name,
          showarrow: false,
        };
      })
    );
  }

  return layout;
}

function prepareDefaultLayout(layout: any, options: any, data: any) {
  const y2Series = data.filter((s: any) => s.yaxis === "y2");
  const palette = getThemePalette();

  layout.xaxis = applyThemeToAxis(prepareXAxis(options.xAxis, options), palette);

  layout.yaxis = applyThemeToAxis(prepareYAxis(options.yAxis[0]), palette);
  if (y2Series.length > 0) {
    layout.yaxis2 = applyThemeToAxis(prepareYAxis(options.yAxis[1]), palette);
    layout.yaxis2.overlaying = "y";
    layout.yaxis2.side = "right";
  }

  if (options.series.stacking) {
    layout.barmode = "relative";
  }

  return layout;
}

function prepareBoxLayout(layout: any, options: any, data: any) {
  layout = prepareDefaultLayout(layout, options, data);
  layout.boxmode = "group";
  layout.boxgroupgap = 0.5;
  return layout;
}

export default function prepareLayout(element: any, options: any, data: any) {
  const palette = getThemePalette();
  const layout: any = {
    margin: { l: 10, r: 10, b: 5, t: 20, pad: 4 },
    // plot size should be at least 5x5px
    width: Math.max(5, Math.floor(element.offsetWidth)),
    height: Math.max(5, Math.floor(element.offsetHeight)),
    autosize: false,
    showlegend: options.legend.enabled,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: palette.text },
    legend: {
      traceorder: options.legend.traceorder,
      font: { color: palette.text },
      bgcolor: "rgba(0,0,0,0)",
    },
    hoverlabel: {
      namelength: -1,
      bordercolor: palette.border,
      font: { color: palette.text },
    },
  };

  if (["line", "area", "column"].includes(options.globalSeriesType)) {
    layout.hovermode = options.swappedAxes ? 'y' : 'x';
  }

  switch (options.globalSeriesType) {
    case "pie":
      return preparePieLayout(layout, options, data);
    case "box":
      return prepareBoxLayout(layout, options, data);
    default:
      return prepareDefaultLayout(layout, options, data);
  }
}
