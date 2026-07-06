import React, { useMemo } from "react";
import { ResponsiveChoropleth } from "@nivo/geo";
import { RendererPropTypes } from "@/visualizations/prop-types";
import useLoadGeoJson from "../hooks/useLoadGeoJson";
import { prepareData } from "./utils";
import getNivoTheme from "@/visualizations/shared/nivo/theme";
import getThemePalette from "@/visualizations/shared/echarts/getThemePalette";
import "./renderer.less";

export default function Renderer({ data, options }: any) {
  const [geoJson] = useLoadGeoJson(options.mapType);
  const palette = getThemePalette();
  const theme = getNivoTheme();

  const valueData = useMemo(
    () => prepareData(data.rows, options.keyColumn, options.valueColumn),
    [data.rows, options.keyColumn, options.valueColumn]
  );

  const nivoData = useMemo(
    () =>
      Object.values(valueData).map((entry: any) => ({
        id: entry.code,
        value: entry.value ?? 0,
      })),
    [valueData]
  );

  const features = (geoJson as any)?.features ?? [];

  const values = nivoData.map(d => d.value).filter((v: number) => Number.isFinite(v));
  const domainMin = Number.isFinite(options.domainMin) ? options.domainMin : (values.length ? Math.min(...values) : 0);
  const domainMax = Number.isFinite(options.domainMax) ? options.domainMax : (values.length ? Math.max(...values) : 1);

  if (!geoJson || features.length === 0) {
    return (
      <div
        className="map-visualization-container choropleth-nivo-container"
        style={{ background: options.colors?.background ?? palette.surfaceAlt }}
      />
    );
  }

  return (
    <div
      className="map-visualization-container choropleth-nivo-container"
      style={{ background: options.colors?.background ?? palette.surfaceAlt, height: "100%", width: "100%" }}>
      <ResponsiveChoropleth
        features={features}
        data={nivoData}
        match={(feature: any) => feature.properties?.[options.targetField] ?? feature.id}
        margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
        colors={[options.colors?.min ?? "#deebf7", options.colors?.max ?? "#3182bd"]}
        domain={[domainMin, domainMax]}
        unknownColor={options.colors?.noValue ?? palette.divider}
        label="properties.name"
        valueFormat=".2s"
        projectionTranslation={[0.5, 0.5]}
        projectionRotation={[0, 0, 0]}
        enableGraticule={false}
        borderWidth={0.5}
        borderColor={palette.border}
        theme={theme}
        legends={[]}
        tooltip={({ feature }: any) => (
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
            <strong>{feature.properties?.name ?? feature.id}</strong>
          </div>
        )}
      />
    </div>
  );
}

Renderer.propTypes = RendererPropTypes;
