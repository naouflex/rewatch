import { omit, noop } from "lodash";
import React, { useState, useEffect, useRef } from "react";
import { RendererPropTypes } from "@/visualizations/prop-types";
import useMemoWithDeepCompare from "@/lib/hooks/useMemoWithDeepCompare";

import useLoadGeoJson from "../hooks/useLoadGeoJson";
import initChoropleth from "./initChoropleth";
import { prepareData } from "./utils";
import { resolveChoroplethOptions } from "@/visualizations/shared/resolveMapTheme";
import useThemeAttribute from "@/visualizations/shared/useThemeAttribute";
import "./renderer.less";

export default function Renderer({ data, options, onOptionsChange }: any) {
  const [container, setContainer] = useState(null);
  const [geoJson] = useLoadGeoJson(options.mapType);
  const onBoundsChangeRef = useRef();
  // @ts-expect-error ts-migrate(2322) FIXME: Type '(...args: any[]) => void' is not assignable ... Remove this comment to see the full error message
  onBoundsChangeRef.current = onOptionsChange ? (bounds: any) => onOptionsChange({ ...options, bounds }) : noop;

  const optionsWithoutBounds = useMemoWithDeepCompare(() => omit(options, ["bounds"]), [options]);
  const theme = useThemeAttribute();
  const themedOptions = useMemoWithDeepCompare(
    () => resolveChoroplethOptions(optionsWithoutBounds),
    [optionsWithoutBounds, theme]
  );

  const [map, setMap] = useState(null);

  useEffect(() => {
    if (container) {
      // @ts-expect-error ts-migrate(7019) FIXME: Rest parameter 'args' implicitly has an 'any[]' ty... Remove this comment to see the full error message
      const _map = initChoropleth(container, (...args) => onBoundsChangeRef.current(...args));
      // @ts-expect-error ts-migrate(2345) FIXME: Argument of type '{ updateLayers: (geoJson: any, d... Remove this comment to see the full error message
      setMap(_map);
      return () => {
        _map.destroy();
      };
    }
  }, [container]);

  useEffect(() => {
    if (map) {
      // @ts-expect-error ts-migrate(2531) FIXME: Object is possibly 'null'.
      map.updateLayers(
        geoJson,
        // @ts-expect-error ts-migrate(2532) FIXME: Object is possibly 'undefined'.
        prepareData(data.rows, themedOptions.keyColumn, themedOptions.valueColumn),
        resolveChoroplethOptions(options)
      );
    }
  }, [map, geoJson, data.rows, themedOptions, theme]); // eslint-disable-line react-hooks/exhaustive-deps

  // This may come only from editor
  useEffect(() => {
    if (map) {
      // @ts-expect-error ts-migrate(2531) FIXME: Object is possibly 'null'.
      map.updateBounds(options.bounds);
    }
  }, [map, options, onOptionsChange]);

  const themedColors = resolveChoroplethOptions(options)?.colors;

  return (
    <div
      className="map-visualization-container choropleth-visualization-container"
      style={{ background: themedColors?.background }}
      // @ts-expect-error ts-migrate(2322) FIXME: Type 'Dispatch<SetStateAction<null>>' is not assignable to type 'LegacyRef<HTMLDivElement> | undefined'.
      ref={setContainer}
    />
  );
}

Renderer.propTypes = RendererPropTypes;
