import React, { useMemo } from "react";
import { ResponsiveSunburst } from "@nivo/sunburst";
import { RendererPropTypes } from "@/visualizations/prop-types";
import getNivoTheme from "@/visualizations/shared/nivo/theme";
import getThemePalette from "@/visualizations/shared/echarts/getThemePalette";
import { buildSunburstHierarchy, isSunburstDataValid } from "./prepareHierarchy";
import "./renderer.less";

export default function Renderer({ data }: any) {
  const hierarchy = useMemo(() => {
    if (!isSunburstDataValid(data)) {
      return null;
    }
    return buildSunburstHierarchy(data.rows);
  }, [data]);

  const palette = getThemePalette();
  const theme = getNivoTheme();

  if (!hierarchy) {
    return null;
  }

  return (
    <div className="sunburst-sequence-visualization-container" style={{ height: "100%", width: "100%" }}>
      <ResponsiveSunburst
        data={hierarchy}
        margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
        id="id"
        value="value"
        cornerRadius={2}
        borderWidth={1}
        borderColor={{ from: "color", modifiers: [["darker", 0.3]] }}
        colors={{ scheme: "nivo" }}
        childColor={{ from: "color", modifiers: [["brighter", 0.4]] }}
        enableArcLabels={true}
        arcLabelsSkipAngle={10}
        arcLabelsTextColor={{ from: "color", modifiers: [["darker", 2]] }}
        theme={theme}
        tooltip={({ id, value }) => (
          <div
            style={{
              padding: "8px 12px",
              background: palette.surface,
              border: `1px solid ${palette.border}`,
              borderRadius: 6,
              color: palette.text,
              fontFamily: palette.fontFamily,
              fontSize: 12,
            }}>
            <strong>{id}</strong>: {value}
          </div>
        )}
      />
    </div>
  );
}

Renderer.propTypes = RendererPropTypes;
