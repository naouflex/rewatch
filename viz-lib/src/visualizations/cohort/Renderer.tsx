import React, { useMemo } from "react";
import { RendererPropTypes } from "@/visualizations/prop-types";

import prepareData from "./prepareData";
import { resolveCohortOptions } from "./resolveCohortTheme";
import useThemeAttribute from "@/visualizations/shared/useThemeAttribute";
import "./renderer.less";

import Cornelius from "./Cornelius";

export default function Renderer({ data, options }: any) {
  const theme = useThemeAttribute();
  const themedOptions = useMemo(() => resolveCohortOptions(options), [options, theme]);
  const { data: cohortData, initialDate } = useMemo(() => prepareData(data, themedOptions), [data, themedOptions]);

  const corneliusOptions = useMemo(
    () => ({
      initialDate,
      timeInterval: themedOptions.timeInterval,

      noValuePlaceholder: themedOptions.noValuePlaceholder,
      rawNumberOnHover: themedOptions.showTooltips,
      displayAbsoluteValues: !themedOptions.percentValues,

      timeColumnTitle: themedOptions.timeColumnTitle,
      peopleColumnTitle: themedOptions.peopleColumnTitle,
      stageColumnTitle: themedOptions.stageColumnTitle,

      numberFormat: themedOptions.numberFormat,
      percentFormat: themedOptions.percentFormat,

      colors: themedOptions.colors,
    }),
    [themedOptions, initialDate]
  );

  if (cohortData.length === 0) {
    return (
      <div className="cohort-visualization-container">
        <div className="cohort-visualization-empty">No cohort data to display. Check column mappings and query results.</div>
      </div>
    );
  }

  return (
    <div className="cohort-visualization-container">
      <Cornelius data={cohortData} options={corneliusOptions} />
    </div>
  );
}

Renderer.propTypes = RendererPropTypes;
