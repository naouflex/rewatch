import { isNil, extend, map, filter, groupBy, omit } from "lodash";
import ColorPalette from "@/visualizations/ColorPalette";

const GROUP_COLORS = [
  ColorPalette.Cyan,
  ColorPalette["Light Blue"],
  ColorPalette.Indigo,
  ColorPalette.Forest,
  ColorPalette.Orange,
  ColorPalette.Red,
  ColorPalette.Pink,
  ColorPalette.Grape,
  ColorPalette.Amber,
  ColorPalette.Gray,
];

export default function prepareData(data: any, options: any) {
  const { classify, latColName, lonColName } = options;
  const pointGroups = classify ? groupBy(data.rows, classify) : { All: data.rows };
  let colorIndex = 0;

  return filter(
    map(pointGroups, (rows, name) => {
      const points = filter(
        map(rows, row => {
          const lat = row[latColName];
          const lon = row[lonColName];
          if (isNil(lat) || isNil(lon)) {
            return null;
          }
          return { lat, lon, row: omit(row, [latColName, lonColName]) };
        })
      );
      if (points.length === 0) {
        return null;
      }

      const result = extend({}, options.groups[name], { name, points });
      if (isNil(result.color)) {
        result.color = GROUP_COLORS[colorIndex % GROUP_COLORS.length];
        colorIndex += 1;
      }

      return result;
    })
  );
}
